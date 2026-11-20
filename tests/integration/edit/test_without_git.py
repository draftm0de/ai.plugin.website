"""Git-independent edit, conflicts and old-session refusal."""
import json
from pathlib import Path
import shutil
from tests.support.edit_helpers import EditCase, GOOD


class WithoutGit(EditCase):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.root / '.git')
        # Any accidental Git call is visible even during subprocess execution.
        git = self.tmpdir / 'bin/git'
        git.write_text('#!/bin/sh\necho called > "' + str(self.tmpdir / 'git-called') + '"\nexit 99\n')
        git.chmod(0o755)
        self.env['PATH'] = str(git.parent) + ':' + self.env['PATH']

    def test_full_edit_and_original_backup_without_a_repository(self):
        state = self.begin()
        self.assertEqual((Path(state) / 'original/src/pages/index.astro').read_text(), GOOD)
        self.assertEqual(self.replace(state, 'twice a week', 'three times a week')[0], 0)
        self.assertEqual(self.check(state)[0], 0)
        code, result = self.finish(state, visual=True)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['outcome'], 'complete')
        self.assertEqual(result['source_changes_since_begin'], [self.rel + '/src/pages/index.astro'])
        self.assertFalse((self.tmpdir / 'git-called').exists())
        self.assertFalse((self.root / '.git').exists())

    def test_foreign_change_is_not_overwritten(self):
        state = self.begin()
        self.index.write_text('foreign change')
        code, result = self.write(state, GOOD)
        self.assertEqual(code, 1, result)
        self.assertEqual(result['state'], 'conflict')
        self.assertEqual(self.index.read_text(), 'foreign change')

    def test_session_without_snapshot_is_refused_before_writes_and_backup_kept(self):
        state = self.begin()
        index = Path(state) / 'index.json'
        data = json.loads(index.read_text()); del data['source_snapshot']
        index.write_text(json.dumps(data))
        before = index.read_bytes()
        code, result = self.write(state, 'changed')
        self.assertEqual(code, 1, result)
        self.assertIn('unsupported edit session', result['message'])
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual(self.index.read_text(), GOOD)
        self.assertTrue((Path(state) / 'original/src/pages/index.astro').exists())
