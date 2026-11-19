"""S13/S14: the real entry-point scripts (run as processes) work together on a project that setup produced."""
import json
import subprocess
import sys
import unittest

from tests.support import setup_paths as helpers
from tests.support import setup_helpers as h

SETUP = helpers.SITE_SCRIPT
WHICH_SITE = helpers.ROOT / "skills" / "_shared" / "scripts" / "which_site.py"


def run(script, *argv, cwd=None):
    result = subprocess.run([sys.executable, "-B", str(script), *argv], cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


class EntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = h.repo()
        for domain, extra in (("second.example", ["--port", "4400", "--alias", "second"]), ("static.example", ["--alias", "stat"])):
            code, out = run(SETUP, "create", domain, "--type", "astro-static", *extra, "--root", str(cls.root))
            assert code == 0, out

    def test_site_setup_script_exit_codes_and_json(self):
        code, out = run(SETUP, "plan", "create", "x.example", "--type", "astro-static", "--json", "--root", str(self.root))
        self.assertEqual((code, json.loads(out)["state"]), (0, "planned"))
        self.assertEqual(run(SETUP, "update", "static.example")[0], 1)
        self.assertEqual(run(SETUP, "plan", "x.example", "--root", str(self.root))[0], 1)

    def test_removed_entry_points_do_not_exist(self):
        for name in ("init.py", "workflow.py", "verify.py"):
            self.assertFalse((helpers.PY / name).exists(), name)

    def test_old_type_and_old_options_are_rejected_and_nothing_is_written(self):
        before = h.snapshot(self.root)
        code, out = run(SETUP, "create", "n.example", "--type", "astro", "--root", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("Unsupported type 'astro'", out)
        for option in (["--legacy-docker"], ["--serve", "behind-proxy"], ["--network", "public"], ["--host", "a.example"], ["--email", "a@b.example"]):
            code, out = run(SETUP, "create", "n.example", "--type", "astro-static", *option, "--root", str(self.root))
            self.assertNotEqual(code, 0, option)
            self.assertIn("unrecognized arguments", out, option)
        self.assertEqual(h.snapshot(self.root), before)

    def test_not_available_functions_are_refused_without_writing(self):
        before = h.snapshot(self.root)
        for argv in (["update", "static.example"], ["verify", "static.example", "--adopt-edits"],
                     ["create", "n.example", "--type", "astro-static", "--add-missing"],
                     ["create", "n.example", "--type", "astro-static", "--regenerate", "x"]):
            code, out = run(SETUP, *argv, "--root", str(self.root)) if argv[0] != "update" else run(SETUP, *argv)
            self.assertEqual(code, 1, argv)
            self.assertIn("STOP:", out, argv)
        self.assertEqual(h.snapshot(self.root), before)

    def test_shared_resolver_resolves_a_setup_produced_site_by_name_alias_and_working_directory(self):
        for query in ("static.example", "stat"):
            code, out = run(WHICH_SITE, query, "--root", str(self.root))
            self.assertEqual((code, json.loads(out)["type"]), (0, "astro-static"), out)
        code, out = run(WHICH_SITE, "--cwd", str(self.root / "sites" / "static.example"), "--root", str(self.root))
        self.assertEqual(json.loads(out)["reason"], "working directory")
        self.assertEqual(run(WHICH_SITE, "nope", "--root", str(self.root))[0], 1)


if __name__ == "__main__":
    unittest.main()
