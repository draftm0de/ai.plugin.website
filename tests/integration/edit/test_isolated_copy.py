"""The edit runtime started the way a host starts it: from an extracted copy (only skills/edit and skills/_shared) under a path with
spaces, from another working directory, `python3 -B` / `-I -B`, without PYTHONPATH and without any checkout of the development
repository. The copy stays byte-identical and gets no bytecode; state lives in the backup area and the website project only."""
import json
import shutil
import tempfile
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, tree

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")


class IsolatedCopy(EditCase):
    def setUp(self):
        super().setUp()
        base = Path(tempfile.mkdtemp()).resolve() / "My Plugin Copy" / "skills"
        base.mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(t.SKILL, base / "edit", ignore=ignore)
        shutil.copytree(t.SHARED, base / "_shared", ignore=ignore)
        self.addCleanup(shutil.rmtree, base.parent.parent, True)
        self.copy = base.parent
        self.skills = base
        self.SCRIPT = base / "edit" / "scripts" / "edit.py"
        self.elsewhere = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.elsewhere, True)
        self.assertIn(" ", str(self.SCRIPT))

    def test_full_cycle_from_the_copy_with_another_working_directory_leaves_the_copy_unchanged(self):
        copy_before = tree(self.copy)
        before = self.snap()
        out = lambda *a, **kw: self.edit(*a, cwd=self.elsewhere, **kw)
        code, d = out("preflight", "--root", str(self.root), check=True)
        self.assertEqual((d["state"], d["site"]), ("ready", self.DOMAIN))
        code, d = out("begin", "--root", str(self.root), "--site", self.DOMAIN, check=True)
        st = d["state_folder"]
        self.assertTrue(st.startswith(str(self.tmpdir)) or st.startswith(str(self.tmpdir.resolve())))
        self.assertNotIn(str(self.copy), st)
        content = self.elsewhere / "content.astro"
        content.write_text(NEW)
        self.assertEqual(out("write", "--state", st, "--content-file", str(content))[1]["state"], "written")
        self.assertEqual(out("replace", "--state", st, "--find", "Sundays", "--replace", "Fridays")[1]["state"], "written")
        self.assertEqual(out("check", "--state", st, "--npm", str(self.npm))[1]["state"], "checked")
        self.assertIn("Fridays", out("diff", "--state", st)[1]["diff"])
        code, f = out("finish", "--state", st, "--visual-done")
        self.assertEqual((code, f["outcome"]), (0, "complete"))
        self.assertEqual(delta(before, self.snap()), {f"{self.rel}/src/pages/index.astro"})
        self.assertEqual(tree(self.copy), copy_before, "the installed copy must stay byte-identical")
        self.assertEqual(list(self.copy.rglob("__pycache__")) + list(self.copy.rglob("*.pyc")), [])
        self.assertEqual(list(self.elsewhere.iterdir()), [content], "nothing is written to the working directory")

    def test_the_website_project_as_working_directory_works_without_root_for_preflight(self):
        code, d = self.edit("preflight", cwd=self.root)
        self.assertEqual((code, d["state"]), (0, "ready"), d)

    def test_no_bytecode_even_when_the_caller_forgets_dash_B(self):
        """edit.py starts the shared resolver as a child process; that child must not write bytecode into the installed plugin."""
        copy_before = tree(self.copy)
        code, d = self.edit("preflight", "--root", str(self.root), flags=("-I",), cwd=self.elsewhere)
        self.assertEqual(code, 0, d)
        code, d = self.edit("preflight", "--root", str(self.root), flags=("-I",), cwd=self.elsewhere)
        self.assertEqual(tree(self.copy), copy_before)
        self.assertEqual(list(self.copy.rglob("__pycache__")), [])

    def test_decoy_modules_on_pythonpath_do_not_shadow_the_runtime(self):
        decoy = self.elsewhere / "decoy"
        decoy.mkdir()
        for name in ("edit.py", "which_site.py", "errors.py", "sites.py", "manifest.py", "schema.py"):
            (decoy / name).write_text("raise RuntimeError('decoy imported')\n")
        (decoy / "site_common").mkdir()
        (decoy / "site_common" / "__init__.py").write_text("raise RuntimeError('decoy package imported')\n")
        env = t.clean_env(PYTHONPATH=str(decoy), TMPDIR=str(self.tmpdir), FAKE_NPM_LOG=str(self.tmpdir / "npm.log"))
        code, d = self.edit("preflight", "--root", str(self.root), flags=("-B",), env=env, cwd=self.elsewhere)
        self.assertEqual((code, d.get("state")), (0, "ready"), d)

    def test_a_missing_resolver_is_a_stop_not_an_ask_and_nothing_is_written(self):
        (self.skills / "_shared" / "scripts" / "which_site.py").unlink()
        before = self.snap()
        for argv in (("preflight", "--root", str(self.root)), ("begin", "--root", str(self.root), "--site", self.DOMAIN)):
            code, d = self.edit(*argv, cwd=self.elsewhere)
            self.assertEqual((code, d["state"]), (1, "stop"), d)
            self.assertIn("resolver is missing", d["message"])
        self.assertEqual(self.snap(), before)
        self.assertEqual(self.state_files(), {})

    def test_the_plugin_schema_comes_from_the_copy_and_a_missing_one_stops_before_any_side_effect(self):
        (self.skills / "_shared" / "resources" / "website.schema.json").unlink()
        before = self.snap()
        for argv in (("preflight", "--root", str(self.root)), ("begin", "--root", str(self.root), "--site", self.DOMAIN)):
            code, d = self.edit(*argv, cwd=self.elsewhere)
            self.assertEqual(code, 1, d)
            self.assertNotIn("Traceback", json.dumps(d))
            self.assertIn("website.schema.json", d["message"])
        self.assertEqual(self.snap(), before)
        self.assertEqual(self.state_files(), {})

    def test_a_missing_shared_package_is_an_error_not_a_fallback_to_a_checkout(self):
        shutil.rmtree(self.skills / "_shared" / "scripts" / "site_common")
        code, d = self.edit("preflight", "--root", str(self.root), cwd=self.elsewhere)
        self.assertEqual(code, 1, d)
        self.assertNotEqual(d.get("state"), "ready")
        self.assertEqual(self.state_files(), {})

    def test_the_runtime_names_no_developer_checkout_and_no_environment_hint(self):
        text = (t.PY / "edit.py").read_text()
        for word in ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "PYTHONPATH", "ZYRIS_WEBSITE_STATE_DIR"):
            self.assertNotIn(word, text, word)


if __name__ == "__main__":
    import unittest
    unittest.main()
