"""Fictional projects only; persistence is not model-interaction acceptance."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT/'skills/_shared/scripts/operator_language.py'
spec = importlib.util.spec_from_file_location('operator_language', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OperatorLanguage(unittest.TestCase):
    def test_session_restart_and_project_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory).resolve()/'first'; first.mkdir()
            second = Path(directory).resolve()/'second'; second.mkdir()
            self.assertTrue(module.preference(first)['needs_choice'])
            self.assertFalse((first/'.project').exists())
            plugin_before = {str(p): p.read_bytes() for p in (ROOT/'skills').rglob('*') if p.is_file()}
            module.preference(first, 'de')
            result = subprocess.run([sys.executable, '-B', str(HELPER), '--root', str(first)],
                                    capture_output=True, text=True, check=True)
            self.assertEqual('de', json.loads(result.stdout)['operator_language'])
            self.assertTrue(module.preference(second)['needs_choice'])
            module.preference(first, 'pt-BR')
            self.assertEqual('pt-BR', module.preference(first)['operator_language'])
            self.assertEqual(plugin_before, {str(p): p.read_bytes() for p in (ROOT/'skills').rglob('*') if p.is_file()})

    def test_rejects_invalid_state_without_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            module.preference(root, 'de')
            path = root/'.project/operator.json'
            for invalid in ('{', '{}', '{"schema_version": 2, "operator_language": "en"}',
                            '{"schema_version": 1, "operator_language": null}'):
                path.write_text(invalid)
                with self.assertRaises(ValueError): module.preference(root, 'en')
                self.assertEqual(invalid, path.read_text())

    def test_symlinks_and_unrelated_data_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            module.preference(root, 'de')
            other = root/'.project/website.json'; other.write_text('fictional website data')
            with self.assertRaises(ValueError): module.preference(root, '../bad')
            module.preference(root, 'en')
            self.assertEqual('fictional website data', other.read_text())
            preference = root/'.project/operator.json'
            preference.unlink(); preference.symlink_to(other)
            with self.assertRaises(ValueError): module.preference(root, 'de')
            self.assertEqual('fictional website data', other.read_text())

    def test_all_public_skills_load_language_gate(self):
        for name in ('plugin-website', 'brief', 'design', 'setup', 'preview', 'optimize', 'edit', 'publish'):
            text = (ROOT/'skills'/name/'SKILL.md').read_text()
            self.assertIn('../_shared/references/operator-language.md', text)
