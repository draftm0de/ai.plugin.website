"""Git-free ignore and snapshot acceptance, fictional files only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.support import setup_helpers
from site_common import project_files as pf
from site_common.errors import Stop


class ProjectFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, rel, text='fictional'):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_local_nested_patterns_negations_and_anchoring_without_git(self):
        self.put('.gitignore', '/root-only/\n*.log\ncache/\n!keep.log\nassets/**/draft?.[ab]\n\\#literal\n')
        self.put('site/.gitignore', '!local.log\n/build/\n')
        rules = pf.IgnoreRules(self.root)
        for rel in ['root-only/x', 'site/cache/x', 'a.log', 'site/x.log', 'assets/draft1.a', 'assets/a/b/draft2.b', '#literal', 'site/build/x']:
            self.assertTrue(rules.ignored(rel), rel)
        for rel in ['site/root-only/x', 'keep.log', 'site/local.log', 'assets/draft22.a', 'site/deep/build/x']:
            self.assertFalse(rules.ignored(rel), rel)

    def test_excluded_parent_cannot_be_reincluded_by_a_child(self):
        self.put('.gitignore', 'cache/\n!cache/keep.txt\n')
        self.assertTrue(pf.is_ignored(self.root, 'cache/keep.txt'))

    def test_snapshot_does_not_open_private_ignored_or_link_targets(self):
        self.put('.gitignore', 'personal/\n*.secret\n')
        self.put('source.txt')
        for rel in ['personal/note', '.env', '.aws/credentials', 'cert.key', 'x.secret']:
            self.put(rel)
        self.put('link').unlink()
        (self.root / 'link').symlink_to(self.root / 'personal/note')
        original = pf.read_regular
        seen = []
        def spy(path, **kwargs):
            seen.append(path.relative_to(self.root).as_posix())
            return original(path, **kwargs)
        with patch.object(pf, 'read_regular', side_effect=spy):
            state = pf.snapshot(self.root)
        self.assertEqual(set(state), {'.gitignore', 'source.txt', 'link'})
        self.assertEqual(set(seen), {'.gitignore', 'source.txt'})
        self.assertTrue(state['link'].startswith('LINK:'))

    def test_added_removed_changed_sources_detected_even_when_ignore_rules_change(self):
        self.put('.gitignore', '')
        self.put('change.txt'); self.put('remove.txt')
        before = pf.snapshot(self.root)
        self.put('change.txt', 'new'); (self.root / 'remove.txt').unlink(); self.put('added.txt')
        self.assertEqual(pf.changed(before, pf.snapshot(self.root)), ['added.txt', 'change.txt', 'remove.txt'])
        self.put('.gitignore', '*.txt\n.gitignore\n')
        self.assertIn('change.txt', pf.changed(before, pf.snapshot(self.root)))

    def test_linked_ignore_file_is_refused_without_reading_target(self):
        (self.root / '.gitignore').symlink_to('/not-a-real-fixture')
        with self.assertRaisesRegex(Stop, 'symbolic link'):
            pf.snapshot(self.root)

    def test_character_classes_and_escaped_spaces(self):
        self.put('.gitignore', '[!a]x\nfile[0-9].txt\n[]].txt\nspace\\ \n')
        rules = pf.IgnoreRules(self.root)
        for rel in ['bx', 'file2.txt', '].txt', 'space ']:
            self.assertTrue(rules.ignored(rel), rel)
        for rel in ['ax', 'filex.txt', 'space']:
            self.assertFalse(rules.ignored(rel), rel)

    def test_swapped_directory_cannot_be_followed_during_snapshot(self):
        from unittest.mock import patch
        self.put('source/file.txt')
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        external = Path(outside.name)
        (external / 'file.txt').write_text('must not read')
        original = os.open
        swapped = False
        def swap(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == 'source' and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                (self.root / 'source').rename(self.root / 'source-old')
                (self.root / 'source').symlink_to(external)
            return original(path, flags, *args, **kwargs)
        with patch.object(pf.os, 'open', side_effect=swap):
            with self.assertRaises(Stop):
                pf.snapshot(self.root)
        self.assertTrue(swapped)

    def test_unsupported_locale_class_stops_before_reading_sources(self):
        self.put('.gitignore', '[[:digit:]].txt\n')
        self.put('1.txt', 'must not read')
        with self.assertRaisesRegex(Stop, 'unsupported.*character class'):
            pf.snapshot(self.root)

    def test_source_permission_change_is_visible(self):
        p = self.put('script.sh')
        p.chmod(0o644)
        before = pf.snapshot(self.root)
        p.chmod(0o755)
        self.assertEqual(pf.changed(before, pf.snapshot(self.root)), ['script.sh'])
