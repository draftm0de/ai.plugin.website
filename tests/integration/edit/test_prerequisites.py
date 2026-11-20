"""edit: site selection, ASK/STOP and prerequisites. `preflight` writes nothing (project, backup area, installed plugin).
Fictional site created by the real `setup`, throw-away git repository, fake npm."""
import json
import shutil
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, delta

import edit as edit_mod  # noqa: E402  (importable once edit_helpers has put the skill's scripts on sys.path)


class SiteAndStops(EditCase):
    def test_e0_unsupported_type_stops_without_writing(self):
        d, code = edit_mod.check_site(self.root, {"site": "x", "path": self.rel, "type": "astro", "rules": "r", "rule_files": []})
        self.assertEqual(code, 1)
        self.assertIn("astro", d["message"])
        # and through the real resolver: a manifest still holding the removed type is invalid for everybody
        mf = self.root / ".project/specs/zyris-website.json"
        data = json.loads(mf.read_text())
        data["components"][0]["type"] = "astro"
        data["components"][0]["serve"] = {"mode": "behind-proxy", "network": "public"}
        mf.write_text(json.dumps(data))
        before = self.snap()
        code, d = self.preflight()
        self.assertEqual(code, 1)
        self.assertEqual(d["state"], "stop")
        self.assertEqual(delta(before, self.snap()), set())

    def test_e6_site_selection(self):
        self.make_site("other.test")
        code, d = self.preflight(self.DOMAIN)
        self.assertEqual((code, d["site"], d["reason"]), (0, self.DOMAIN, "named"))
        self.assertEqual(self.preflight("CLUB.TEST")[1]["site"], self.DOMAIN)           # case-insensitive domain
        self.assertEqual(self.preflight("--cwd", str(self.site))[1]["site"], self.DOMAIN)  # working directory
        code, d = self.preflight()                                                       # two sites, nothing named
        self.assertEqual(code, 2)
        self.assertIn("ask", d)
        self.assertEqual({o["name"] for o in d["options"]}, {self.DOMAIN, "other.test"})
        code, d = self.preflight("--last", "other.test")                                  # last used: named, confirm
        self.assertEqual(d["site"], "other.test")
        self.assertTrue(d["confirm"])
        code, d = self.preflight("nope.example")
        self.assertEqual(code, 1)
        self.assertIn("No site matches", d["message"])

    def test_e6_only_site_and_wrong_root(self):
        code, d = self.preflight()
        self.assertEqual((code, d["site"], d["reason"]), (0, self.DOMAIN, "only site"))
        code, d = self.edit("preflight", "--root", str(self.tmpdir))                      # not a project root
        self.assertEqual(code, 1)
        self.assertIn("not found", d["message"])

    def test_e9_missing_rules_file_stops(self):
        (self.site / "rules" / "seo.md").unlink()
        before = self.snap()
        code, d = self.preflight()
        self.assertEqual(code, 1)
        self.assertIn("seo.md", d["message"])
        self.assertEqual(delta(before, self.snap()), set())

    def test_missing_start_page_names_setup(self):
        self.index.unlink()
        code, d = self.preflight()
        self.assertEqual(code, 1)
        self.assertIn("setup", d["message"])
        self.assertNotIn("/zyris-website:", d["message"])


class Prerequisites(EditCase):
    def test_e13_missing_prerequisites_stop_before_any_write(self):
        for what in ("node_modules", "lock", "build", "check"):
            with self.subTest(what):
                backup = None
                if what == "node_modules":
                    shutil.move(self.site / "node_modules", self.tmpdir / "nm")
                elif what == "lock":
                    (self.site / "package-lock.json").rename(self.tmpdir / "lock")
                else:
                    pkg = json.loads((self.site / "package.json").read_text())
                    backup = (self.site / "package.json").read_text()
                    del pkg["scripts"][what]
                    (self.site / "package.json").write_text(json.dumps(pkg))
                before = self.snap()
                code, d = self.preflight()
                self.assertEqual(code, 1, d)
                self.assertTrue(d["commands_for_the_person"])
                self.assertEqual(delta(before, self.snap()), set())
                self.assertEqual(self.npm_calls(), [])                                      # no install, no ci, nothing
                self.assertEqual(self.state_files(), {})             # no backup area was created
                if what == "node_modules":
                    shutil.move(self.tmpdir / "nm", self.site / "node_modules")
                elif what == "lock":
                    (self.tmpdir / "lock").rename(self.site / "package-lock.json")
                else:
                    (self.site / "package.json").write_text(backup)
        self.assertEqual(self.preflight()[0], 0)

    def test_package_json_that_is_not_an_object_is_a_stop_not_a_traceback(self):
        for text in ("[]", '"x"', "{not json", '{"scripts": []}'):
            with self.subTest(text):
                original = (self.site / "package.json").read_text()
                (self.site / "package.json").write_text(text)
                code, d = self.preflight()
                self.assertEqual(code, 1, d)
                self.assertNotIn("raw", d)
                (self.site / "package.json").write_text(original)

    def test_missing_git_is_not_a_missing_prerequisite(self):
        empty = self.tmpdir / "empty-path"
        empty.mkdir()
        env = {**self.env, "PATH": str(empty)}
        before = self.snap()
        code, d = self.edit("preflight", "--root", str(self.root), env=env)
        self.assertEqual(code, 0, d)
        self.assertEqual(delta(before, self.snap()), set())
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, env=env)
        self.assertEqual(code, 0, d)

    def test_a_repository_without_a_commit_can_start_a_session(self):
        shutil.rmtree(self.root / ".git")
        t.git(self.root, "init", "-q", "-b", "main")
        code, d = self.preflight()
        self.assertEqual(code, 0, d)


class PreflightWritesNothing(EditCase):
    def test_project_backup_area_and_installed_plugin_are_unchanged(self):
        installed = {p: t.tree(p) for p in (t.SKILL, t.SHARED)}
        before = self.snap()
        for args in ((), (self.DOMAIN,), ("nope.example",), ("--cwd", str(self.site))):
            self.preflight(*args)
        self.assertEqual(delta(before, self.snap()), set())
        self.assertEqual(self.state_files(), {})
        self.assertEqual(self.npm_calls(), [])
        self.assertEqual({p: t.tree(p) for p in (t.SKILL, t.SHARED)}, installed)
        self.assertEqual(list(t.SKILL.rglob("__pycache__")) + list(t.SHARED.rglob("__pycache__")), [])
        self.assertEqual(t.git(self.root, "status", "--porcelain=v1", "--untracked-files=all"), "")
