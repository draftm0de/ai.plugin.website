"""The shared resolver entry point, started the way a skill starts it: from an extracted copy under a path with
spaces, without PYTHONPATH, with `python -I`, as one quoted argument."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import projects as P


def run(entry, *argv, env=None, flags=("-I", "-B")):
    done = subprocess.run([sys.executable, *flags, str(entry), *argv], capture_output=True, text=True,
                          env=env or P.clean_env(), cwd=tempfile.gettempdir())
    return done.returncode, done.stdout + done.stderr


class IsolatedCopyTests(unittest.TestCase):
    def setUp(self):
        self.copy_root, self.shared = P.copy_shared_to_spaced_dir()
        self.entry = self.shared / "scripts" / "which_site.py"
        self.project = P.make_project()

    def test_path_with_spaces_and_no_pythonpath(self):
        self.assertIn(" ", str(self.entry))
        code, out = run(self.entry, "first", "--root", str(self.project))
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertEqual((data["site"], data["type"], data["path"]), ("alpha.example", "astro-static", "sites/alpha.example"))

    def test_schema_resource_comes_from_the_copy_not_from_a_checkout(self):
        (self.shared / "resources" / "website.schema.json").unlink()
        code, out = run(self.entry, "first", "--root", str(self.project))
        self.assertEqual(code, 1, out)
        self.assertTrue(out.startswith("STOP:"), out)
        self.assertIn(str(self.shared / "resources"), out)
        self.assertIn("incomplete", out)

    def test_copy_is_not_written_to_when_started_with_the_conventional_flags(self):
        before = P.tree_snapshot(self.copy_root)
        run(self.entry, "first", "--root", str(self.project))
        run(self.entry, "--root", str(self.project))
        run(self.entry, "nope", "--root", str(self.project))
        self.assertEqual(P.tree_snapshot(self.copy_root), before)

    def test_bytecode_suppression_flag_is_what_keeps_the_copy_clean(self):
        """Without -B Python would write __pycache__ into the installed plugin: the invocation convention requires -B."""
        run(self.entry, "first", "--root", str(self.project), flags=("-I",))
        written = [k for k in P.tree_snapshot(self.copy_root) if "__pycache__" in k]
        self.assertTrue(written, "expected bytecode without -B; if this fails the convention text may be relaxed")

    def test_project_is_not_written_to(self):
        before = P.tree_snapshot(self.project)
        run(self.entry, "first", "--root", str(self.project))
        run(self.entry, "nope", "--root", str(self.project))
        self.assertEqual(P.tree_snapshot(self.project), before)

    def test_exit_codes_and_messages(self):
        self.assertEqual(run(self.entry, "--root", str(self.project))[0], 2)                  # ambiguous -> ASK
        code, out = run(self.entry, "--root", str(self.project))
        self.assertEqual(len(json.loads(out)["options"]), 2)
        code, out = run(self.entry, "nope", "--root", str(self.project))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP:"))
        (self.project / "sites" / "alpha.example").rmdir()
        code, out = run(self.entry, "alpha", "--root", str(self.project))
        self.assertEqual((code, "Site folder missing" in out), (1, True))

    def test_invalid_manifest_stops_before_reading_site_data(self):
        project = P.make_project({"version": 1, "components": [{**P.component("a.example"), "type": "astro"}]}, ("a.example",))
        code, out = run(self.entry, "--root", str(project))
        self.assertEqual(code, 1)
        self.assertIn("is invalid", out)

    def test_rules_and_brand_files_are_listed(self):
        rules = self.project / "sites" / "alpha.example" / "rules"
        rules.mkdir()
        (rules / "seo.md").write_text("x")
        (rules / "accessibility.md").write_text("x")
        brand = self.project / ".project" / "brand"
        brand.mkdir()
        (brand / "voice.md").write_text("x")
        data = json.loads(run(self.entry, "alpha", "--root", str(self.project))[1])
        self.assertEqual((data["rule_files"], data["brand_files"], data["has_node_modules"]),
                         (["accessibility.md", "seo.md"], ["voice.md"], False))

    def test_working_directory_selects_site(self):
        cwd = self.project / "sites" / "beta.example"
        data = json.loads(run(self.entry, "--root", str(self.project), "--cwd", str(cwd))[1])
        self.assertEqual((data["site"], data["reason"]), ("beta.example", "working directory"))


class ImportIsolationTests(unittest.TestCase):
    def test_shared_names_do_not_shadow_or_collide_with_flat_modules(self):
        """A skill that keeps its own flat `errors`/`manifest` (setup variants differ) must coexist with the shared package."""
        decoy = Path(tempfile.mkdtemp()) / "decoy dir"
        decoy.mkdir()
        (decoy / "errors.py").write_text("class Ask(Exception):\n    marker = 'decoy'\n")
        (decoy / "manifest.py").write_text("MARK = 'decoy'\n")
        (decoy / "schema.py").write_text("MARK = 'decoy'\n")
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(decoy)!r})\n"
            f"sys.path.insert(0, {str(P.SHARED / 'scripts')!r})\n"
            "import errors, manifest, schema\n"
            "from site_common import errors as e, manifest as m, schema as s\n"
            "assert errors.Ask.marker == 'decoy' and manifest.MARK == 'decoy' and schema.MARK == 'decoy'\n"
            "assert e.Ask is not errors.Ask and m.__name__ == 'site_common.manifest'\n"
            "assert e.Ask('q', [1]).options == [1]\n"
            "print('ok')\n")
        done = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env=P.clean_env())
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "ok"), done.stderr)

    def test_decoy_modules_on_pythonpath_do_not_change_the_entry_point(self):
        decoy = Path(tempfile.mkdtemp())
        for name in ("errors", "manifest", "schema", "sites", "site_common"):
            (decoy / f"{name}.py").write_text("raise SystemExit('decoy imported')\n")
        copy_root, shared = P.copy_shared_to_spaced_dir()
        project = P.make_project()
        code, out = run(shared / "scripts" / "which_site.py", "first", "--root", str(project),
                        env=P.clean_env(PYTHONPATH=str(decoy)), flags=("-B",))
        self.assertEqual(code, 0, out)
        self.assertNotIn("decoy", out)


if __name__ == "__main__":
    unittest.main()
