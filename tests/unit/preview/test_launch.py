import io
import json
import unittest
from contextlib import redirect_stdout

from tests.support import preview_helpers as helpers
import preview


def call(root, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = preview.main(["--root", str(root), *argv])
    return code, out.getvalue()


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.root = helpers.make_repo()

    def test_named_site_writes_launch_entry(self):
        code, out = call(self.root, "first", "--page", "about.html")
        self.assertEqual(code, 0, out)
        result = json.loads(out)
        self.assertEqual(result["site"], "alpha.example")
        self.assertEqual(result["url"], "http://localhost:4321/about.html")
        self.assertEqual(result["launch_name"], "zyris-alpha.example")
        self.assertTrue(result["needs_install"])
        launch = json.loads((self.root / ".claude" / "launch.json").read_text())
        entry = launch["configurations"][0]
        self.assertEqual(entry["port"], 4321)
        self.assertIs(entry["autoPort"], False)      # a mistaken host start fails instead of moving to another port
        self.assertEqual(entry["runtimeArgs"][:2], ["--prefix", "sites/alpha.example"])

    def test_launch_json_is_merged_not_replaced(self):
        launch = self.root / ".claude" / "launch.json"
        launch.parent.mkdir()
        launch.write_text(json.dumps({"version": "0.0.1", "configurations": [{"name": "other", "port": 1}]}))
        call(self.root, "alpha")
        call(self.root, "alpha")
        names = [c["name"] for c in json.loads(launch.read_text())["configurations"]]
        self.assertEqual(names, ["other", "zyris-alpha.example"])

    def test_two_sites_without_hint_asks(self):
        code, out = call(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(len(json.loads(out)["options"]), 2)
        self.assertFalse((self.root / ".claude" / "launch.json").exists())

    def test_installed_site_needs_no_install(self):
        (self.root / "sites" / "alpha.example" / "node_modules").mkdir()
        self.assertFalse(json.loads(call(self.root, "alpha")[1])["needs_install"])

    def test_unknown_site_stops(self):
        code, out = call(self.root, "nope")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP"))

    def test_invalid_manifest_stops_with_reason(self):
        root = helpers.make_repo({**helpers.ONE_SITE, "components": [{**helpers.ONE_SITE["components"][0], "port": 80}]}, ("alpha.example",))
        code, out = call(root)
        self.assertEqual(code, 1)
        self.assertIn("port", out)

    def test_removed_docker_type_with_serve_is_rejected_not_translated(self):
        root = helpers.make_repo({"version": 1, "components": [helpers._removed_type_site("alpha.example")]}, ("alpha.example",))
        code, out = call(root)
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP"))
        self.assertIn("astro-static", out)
        self.assertFalse((root / ".claude" / "launch.json").exists())

    def test_unsupported_type_stops(self):
        root = helpers.make_repo({**helpers.ONE_SITE, "components": [{**helpers.ONE_SITE["components"][0], "type": "hugo"}]}, ("alpha.example",))
        code, out = call(root)
        self.assertEqual(code, 1)
        self.assertIn("type", out)


class StaticSiteTests(unittest.TestCase):
    def test_static_site_gets_a_valid_launch_entry_in_a_mixed_manifest(self):
        root = helpers.make_repo(helpers.MIXED, ("alpha.example", "static.example"))
        code, out = call(root, "stat", "--page", "about.html")
        self.assertEqual(code, 0, out)
        result = json.loads(out)
        self.assertEqual((result["site"], result["port"], result["url"]), ("static.example", 4322, "http://localhost:4322/about.html"))
        entry = json.loads((root / ".claude" / "launch.json").read_text())["configurations"][0]
        self.assertEqual(entry, {"name": "zyris-static.example", "runtimeExecutable": "npm",
                                 "runtimeArgs": ["--prefix", "sites/static.example", "run", "dev", "--", "--port", "4322"], "port": 4322, "autoPort": False})

    def test_second_site_of_the_same_type_is_resolved_by_alias(self):
        root = helpers.make_repo(helpers.MIXED, ("alpha.example", "static.example"))
        self.assertEqual(json.loads(call(root, "first")[1])["site"], "alpha.example")

    def test_static_only_manifest_resolves_as_single_site_and_by_cwd(self):
        root = helpers.make_repo(helpers.STATIC_ONLY, ("static.example",))
        result = json.loads(call(root)[1])
        self.assertEqual((result["site"], result["reason"]), ("static.example", "only site"))

    def test_mixed_manifest_asks_and_resolves_by_working_directory_and_last_used(self):
        root = helpers.make_repo(helpers.MIXED, ("alpha.example", "static.example"))
        self.assertEqual(call(root)[0], 2)
        by_cwd = json.loads(call(root, "--cwd", str(root / "sites" / "static.example" / "src"))[1])
        self.assertEqual((by_cwd["site"], by_cwd["reason"]), ("static.example", "working directory"))
        last = json.loads(call(root, "--last", "static.example")[1])
        self.assertEqual((last["site"], last["confirm"]), ("static.example", True))

    def test_static_component_with_a_serve_configuration_is_invalid(self):
        bad = {"version": 1, "components": [{**helpers._static("static.example"), "serve": {"mode": "behind-proxy", "network": "public"}}]}
        code, out = call(helpers.make_repo(bad, ("static.example",)))
        self.assertEqual(code, 1)
        self.assertIn("serve", out)

    def test_removed_type_without_serve_is_invalid(self):
        bad = {"version": 1, "components": [{"name": "alpha.example", "path": "sites/alpha.example", "type": "astro"}]}
        code, out = call(helpers.make_repo(bad, ("alpha.example",)))
        self.assertEqual(code, 1)
        self.assertIn("astro-static", out)

    def test_type_without_preview_template_keeps_the_existing_stop_message(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        root = helpers.make_repo(helpers.STATIC_ONLY, ("static.example",))
        with mock.patch.object(preview, "RES", Path(tempfile.mkdtemp())):
            code, out = call(root)
        self.assertEqual(code, 1)
        self.assertIn("No preview template for type 'astro-static'", out)


if __name__ == "__main__":
    unittest.main()
