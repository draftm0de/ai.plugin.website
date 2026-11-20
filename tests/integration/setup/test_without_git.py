"""All setup operations in a plain folder, with Git forbidden."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tests.support import setup_helpers as h


class WithoutGit(unittest.TestCase):
    def test_plan_create_repeat_verify_and_adopt_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = h.FakeRunner()
            with patch('subprocess.run', side_effect=AssertionError('no Git or process expected with fake runner')):
                options = h.opts('create', root=root)
                plan = h.static_setup.make_plan(options)
                self.assertEqual(plan.state, 'ok')
                self.assertEqual(list(root.iterdir()), [])
                self.assertEqual(h.static_setup.execute(options, runner)['state'], 'created')
                self.assertEqual(h.static_setup.execute(options, runner)['state'], 'unchanged')
                self.assertEqual(h.static_setup.verify(h.opts('verify', root=root), runner)['state'], 'verified')
                h.make_static_site(root)
                self.assertEqual(h.static_setup.execute(h.opts('adopt', 'adopted.example', root), runner)['state'], 'adopted')
            self.assertFalse((root / '.git').exists())

    def test_cli_defaults_to_selected_working_directory_with_empty_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = Path(__file__).resolve().parents[3] / 'skills/setup/scripts/site_setup.py'
            env = {**os.environ, 'PATH': str(root)}
            for args, state in [(['plan', 'create'], 'planned'), (['create'], 'created')]:
                done = subprocess.run([sys.executable, '-B', str(script), *args, 'demo.test', '--type', 'astro-static', '--json'], cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(json.loads(done.stdout)['state'], state)
            self.assertTrue((root / 'sites/demo.test/src/pages/index.astro').is_file())
            self.assertFalse((root / '.git').exists())

    def test_unsupported_ignore_syntax_stops_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignore = root / '.gitignore'
            ignore.write_text('[[:digit:]].txt\n')
            before = h.snapshot(root)
            result = h.static_setup.execute(h.opts('create', root=root), h.FakeRunner())
            self.assertEqual(result['state'], 'invalid', result)
            self.assertEqual(h.snapshot(root), before)
