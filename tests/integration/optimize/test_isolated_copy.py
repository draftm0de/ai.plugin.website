"""The optimize runtime started the way a host starts it: from an extracted copy (only skills/optimize and skills/_shared)
under a path with spaces, from another working directory, `python3 -B`/`-I`, without PYTHONPATH. Resources (the plugin schema)
come from the copy; the copy stays byte-identical; no state is written into it. Fictional project, fake npm."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.support import optimize_helpers as h
from tests.support.projects import tree_snapshot


class IsolatedCopy(h.AuditCase):
    def setUp(self):
        super().setUp()
        base = Path(tempfile.mkdtemp()).resolve() / "My Plugin Copy" / "skills"
        base.mkdir(parents=True)
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(h.SKILL, base / "optimize", ignore=ignore)
        shutil.copytree(h.SHARED, base / "_shared", ignore=ignore)
        self.addCleanup(shutil.rmtree, base.parent.parent, True)
        self.copy = base.parent
        self.script = base / "optimize" / "scripts" / "audit.py"
        self.resolver = base / "_shared" / "scripts" / "which_site.py"
        self.elsewhere = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.elsewhere, True)
        self.assertIn(" ", str(self.script))

    def call(self, *argv, entry=None, cwd=None, flags=("-I", "-B"), env=None):
        done = subprocess.run([sys.executable, *flags, str(entry or self.script), *argv], capture_output=True, text=True,
                              cwd=cwd or self.elsewhere, env=env or h.clean_env(FAKE_NPM_LOG=str(self.log)))
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            return done.returncode, done.stdout + done.stderr

    def test_full_cycle_from_the_copy_with_another_working_directory_leaves_the_copy_unchanged(self):
        copy_before = tree_snapshot(self.copy)
        proposals = self.elsewhere / "proposals.json"
        proposals.write_text(json.dumps({"seo.description-too-short|/a.html|": self.proposal_for(h.GOOD_A)}))
        code, first = self.call("audit", "--root", str(self.root), "--npm", str(self.npm), "--proposals", str(proposals))
        self.assertEqual((code, first["status"]), (0, "clean-with-warnings"), first)
        code, out = self.call("decide", "SEO-001", "--status", "approved", "--root", str(self.root))
        self.assertEqual(code, 0, out)
        code, shown = self.call("show", "--root", str(self.root))
        self.assertEqual((code, [f["status"] for f in shown["open"]]), (0, ["approved", "proposed"]), shown)
        code, applied = self.call("apply", "SEO-001", "--root", str(self.root), "--npm", str(self.npm))
        self.assertEqual((code, applied["status"], applied["changes"]["resolved"]), (0, "clean-with-warnings", ["SEO-001"]), applied)
        self.assertEqual([p["description"] for p in json.loads((self.site / "src" / "content.json").read_text())], [h.LONG, h.GOOD_A, h.SHORT_B])
        self.assertEqual(self.npm_calls(), ["run build", "run seo:check", "run a11y:check"] * 2)
        self.assertEqual(tree_snapshot(self.copy), copy_before, "the installed copy must stay byte-identical")
        self.assertEqual(list(self.copy.rglob("__pycache__")), [])
        self.assertEqual([p for p in self.elsewhere.iterdir() if p.name != "proposals.json"], [], "nothing is written to the working directory")

    def test_the_website_project_as_working_directory_works_without_root_argument(self):
        code, out = self.call("show", cwd=self.root)
        self.assertEqual((code, out["worklist"]), (0, None), out)
        code, out = self.call("audit", "--npm", str(self.npm), cwd=self.root)
        self.assertEqual(code, 0, out)

    def test_the_shared_resolver_is_called_from_the_copy_too(self):
        code, out = self.call("fx.test", "--root", str(self.root), entry=self.resolver)
        self.assertEqual((code, out["site"], out["path"]), (0, "fx.test", "sites/fx.test"), out)
        self.assertEqual(out["rule_files"], [])

    def test_decoy_modules_on_pythonpath_do_not_shadow_the_runtime(self):
        decoy = self.elsewhere / "decoy"
        decoy.mkdir()
        for name in ("audit.py", "findings.py", "store.py", "worklist.py", "errors.py", "sites.py", "manifest.py", "schema.py"):
            (decoy / name).write_text("raise RuntimeError('decoy imported')\n")
        (decoy / "site_common").mkdir()
        (decoy / "site_common" / "__init__.py").write_text("raise RuntimeError('decoy package imported')\n")
        code, out = self.call("show", "--root", str(self.root), flags=("-B",), env=h.clean_env(PYTHONPATH=str(decoy)))
        self.assertEqual(code, 0, out)

    def test_the_plugin_schema_comes_from_the_copy_and_a_missing_one_stops_before_any_side_effect(self):
        (self.copy / "skills" / "_shared" / "resources" / "website.schema.json").unlink()
        before = tree_snapshot(self.root)
        for argv in (("audit", "--root", str(self.root), "--npm", str(self.npm)), ("show", "--root", str(self.root))):
            code, out = self.call(*argv)
            self.assertEqual(code, 1, out)
            self.assertTrue(out.startswith("STOP:"), out)
            self.assertIn(str(self.copy / "skills" / "_shared" / "resources"), out)
            self.assertNotIn("Traceback", out)
        self.assertEqual(tree_snapshot(self.root), before)
        self.assertEqual(self.npm_calls(), [])

    def test_a_missing_shared_package_is_an_error_not_a_fallback_to_a_checkout(self):
        shutil.rmtree(self.copy / "skills" / "_shared" / "scripts" / "site_common")
        code, out = self.call("show", "--root", str(self.root))
        self.assertNotEqual(code, 0)
        self.assertIn("site_common", out)
        self.assertEqual(tree_snapshot(self.root).get(".project/reports"), None)

    def test_python_without_dash_B_would_write_bytecode_into_the_copy_which_is_why_the_call_form_requires_it(self):
        self.call("show", "--root", str(self.root), flags=("-I",))
        self.assertTrue(list(self.copy.rglob("__pycache__")), "expected bytecode without -B; if this fails the -B requirement may be relaxed")
