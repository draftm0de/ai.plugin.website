"""edit: backup and state area. Outside the website project and outside the installed plugin, original byte-exact, cleanup only
of the run's own folder and only for a confirmed end, protected project files untouched."""
import json
import os
import shutil
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, git, sha, tree

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")
PROTECTED = ("package.json", "package-lock.json", "src/styles/foundation/tokens.css", "rules/seo.md", "rules/accessibility.md", "scripts/seo-check.mjs",
             "scripts/a11y-check.mjs", "src/layouts/BaseLayout.astro", "src/lib/site.ts")


class BackupArea(EditCase):
    def test_backup_is_outside_project_and_plugin_and_holds_the_original_bytes(self):
        original = self.index.read_bytes()
        st = self.begin()
        folder = Path(st).resolve()
        self.assertEqual(folder.parent.parent, (self.tmpdir / "website-manager").resolve())
        for forbidden in (self.root.resolve(), t.PLUGIN.resolve()):
            self.assertNotIn(forbidden, [folder, *folder.parents])
        self.assertEqual(oct(folder.stat().st_mode & 0o777), "0o700")
        self.assertEqual((folder / "original" / "src/pages/index.astro").read_bytes(), original)
        self.write(st, NEW)
        self.write(st, NEW.replace("Sundays", "Fridays"))
        self.assertEqual((folder / "original" / "src/pages/index.astro").read_bytes(), original)    # never changed after the first write
        _, d = self.edit("diff", "--state", st)
        self.assertIn('-      <p class="page-header__lead">Training twice a week.</p>', d["diff"])
        self.assertIn('+      <p class="page-header__lead">Training three times a week.</p>', d["diff"])
        self.assertIn("Fridays", d["diff"])

    def test_the_project_gets_no_state_or_backup_file(self):
        before = self.snap()
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        self.finish(st, visual=True)
        self.assertEqual(delta(before, self.snap()), {f"{self.rel}/src/pages/index.astro"})
        self.assertEqual(t.git(self.root, "status", "--porcelain=v1", "--untracked-files=all").split(), ["M", f"{self.rel}/src/pages/index.astro"])

    def test_two_runs_get_distinct_folders(self):
        a, b = self.begin(), self.begin()
        self.assertNotEqual(a, b)
        self.assertTrue(Path(a).is_dir() and Path(b).is_dir())

    def test_a_backup_area_inside_the_website_project_is_refused_before_anything_is_written(self):
        inside = self.root / "scratch-tmp"
        inside.mkdir()
        before = self.snap()
        env = {**self.env, "TMPDIR": str(inside)}
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, env=env)
        self.assertEqual((code, d["state"]), (1, "refused"), d)
        self.assertIn("inside the website project", d["message"])
        self.assertEqual(delta(before, self.snap()), set())
        self.assertEqual(os.listdir(inside), [])

    def test_a_backup_area_inside_the_installed_plugin_is_refused(self):
        copy = self.tmpdir / "My Plugin" / "skills"
        copy.mkdir(parents=True)
        shutil.copytree(t.SKILL, copy / "edit", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(t.SHARED, copy / "_shared", ignore=shutil.ignore_patterns("__pycache__"))
        before_copy = tree(self.tmpdir / "My Plugin")
        env = {**self.env, "TMPDIR": str(self.tmpdir / "My Plugin" / "tmp")}
        os.mkdir(self.tmpdir / "My Plugin" / "tmp")
        before_copy = tree(self.tmpdir / "My Plugin")
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN, env=env, script=copy / "edit" / "scripts" / "edit.py")
        self.assertEqual((code, d["state"]), (1, "refused"), d)
        self.assertIn("inside the installed plugin", d["message"])
        self.assertEqual(tree(self.tmpdir / "My Plugin"), before_copy)

    def test_a_symlinked_backup_area_is_refused_and_nothing_is_followed(self):
        elsewhere = self.tmpdir / "elsewhere"
        elsewhere.mkdir()
        os.symlink(elsewhere, self.tmpdir / "website-manager")
        code, d = self.edit("begin", "--root", str(self.root), "--site", self.DOMAIN)
        self.assertEqual((code, d["state"]), (1, "refused"), d)
        self.assertIn("symlink", d["message"])
        self.assertEqual(os.listdir(elsewhere), [])

    def test_a_state_folder_of_another_project_is_not_ours(self):
        other = t.h.repo()
        self.addCleanup(shutil.rmtree, other, True)
        t.h.static_setup.execute(t.h.opts("create", "foreign.test", other), t.h.FakeRunner())
        (other / "sites/foreign.test/node_modules").mkdir()
        (other / "sites/foreign.test/package-lock.json").write_text("{}\n")
        git(other, "config", "user.email", "t@example.invalid")
        git(other, "config", "user.name", "t")
        git(other, "add", "-A")
        git(other, "commit", "-qm", "x")
        code, d = self.edit("begin", "--root", str(other), "--site", "foreign.test", check=True)
        foreign = d["state_folder"]
        foreign_before = tree(Path(foreign))
        c = self.tmpdir / "c"
        c.write_text(NEW)
        self.assertEqual(self.edit("write", "--state", foreign, "--content-file", str(c))[0], 0)       # its own project: allowed
        # the same folder presented with another project's state is not accepted: tamper the root, as a confused caller could
        idx = json.loads((Path(foreign) / "index.json").read_text())
        idx["root"] = str(self.root)
        (Path(foreign) / "index.json").write_text(json.dumps(idx))
        for command in (("write", "--content-file", str(c)), ("check",), ("diff",), ("finish", "--visual-done")):
            self.assertEqual(self.edit(command[0], "--state", foreign, *command[1:])[0], 1, command)
        self.assertEqual(self.index.read_text(), GOOD)
        self.assertTrue(Path(foreign).is_dir())
        self.assertNotEqual(foreign_before, {})


class Cleanup(EditCase):
    def test_e20_only_the_own_folder_is_removed_after_a_confirmed_end(self):
        st = self.begin()
        sibling = Path(st).parent / "edit-other-run"
        sibling.mkdir()
        (sibling / "keep.txt").write_text("x")
        other_project = self.tmpdir / "website-manager" / "aaaaaaaaaaaa" / "edit-x"
        other_project.mkdir(parents=True)
        (other_project / "keep.txt").write_text("y")
        self.write(st, NEW)
        self.check(st)
        _, f = self.finish(st, visual=True)
        self.assertEqual(f["backup"], "removed (own folder only)")
        self.assertFalse(Path(st).exists())
        self.assertEqual((sibling / "keep.txt").read_text(), "x")
        self.assertEqual((other_project / "keep.txt").read_text(), "y")
        self.assertTrue(Path(st).parent.is_dir())
        self.assertEqual(self.index.read_text(), NEW)

    def test_nothing_is_removed_unless_the_end_is_confirmed(self):
        for label, prepare in (("visual open", lambda st: (self.write(st, NEW), self.check(st))),
                               ("not checked", lambda st: self.write(st, NEW)),
                               ("failed check", lambda st: (self.write(st, NEW + "<!-- BAD_CHECK -->\n"), self.check(st)))):
            with self.subTest(label):
                st = self.begin()
                prepare(st)
                _, f = self.finish(st, visual=(label != "visual open"))
                self.assertEqual(f["backup"], "kept")
                self.assertTrue((Path(st) / "original").is_dir())
                self.assertEqual(f["backup_folder"], st)
                self.index.write_text(GOOD)

    def test_foreign_files_inside_the_own_folder_are_not_deleted(self):
        st = self.begin()
        (Path(st) / "notes-of-someone.txt").write_text("keep me")
        self.write(st, NEW)
        self.check(st)
        code, f = self.finish(st, visual=True)
        self.assertEqual(code, 0)
        self.assertEqual(f["outcome"], "complete")
        self.assertTrue(f["backup"].startswith("kept (nothing removed); cleanup refused"), f["backup"])
        self.assertEqual((Path(st) / "notes-of-someone.txt").read_text(), "keep me")
        self.assertTrue((Path(st) / "original").is_dir())

    def test_a_symlink_state_folder_is_never_removed(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        link = Path(st).parent / "edit-link"
        os.symlink(st, link)
        code, f = self.finish(str(link), visual=True)
        self.assertTrue(Path(st).is_dir())
        self.assertTrue(link.is_symlink())


class ProtectedProjectFiles(EditCase):
    def test_e15_e18_reports_ownership_record_and_protected_files_stay_untouched(self):
        rep = self.root / ".project" / "reports" / self.DOMAIN
        rep.mkdir(parents=True)
        (rep / "optimize.md").write_text("<!-- SEO-001 proposed -->\nSEO-002 proposed\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "reports")
        before = self.snap()
        managed = self.root / ".project/specs/website.managed.json"
        h_managed = sha(managed)
        schema, manifest = (self.root / ".project/specs/website.schema.json"), (self.root / ".project/specs/website.json")
        h_schema, h_manifest = sha(schema), sha(manifest)
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        self.finish(st, visual=True)
        self.assertEqual(delta(before, self.snap()), {f"{self.rel}/src/pages/index.astro"})
        self.assertEqual((sha(managed), sha(schema), sha(manifest)), (h_managed, h_schema, h_manifest))
        self.assertIn("SEO-001 proposed", (rep / "optimize.md").read_text())
        for rel in PROTECTED:
            self.assertEqual(sha(self.site / rel), before[f"{self.rel}/{rel}"], rel)
        self.assertFalse((self.root / ".claude").exists())

    def test_the_helper_cannot_be_pointed_at_protected_files(self):
        st = self.begin()
        before = self.snap()
        c = self.tmpdir / "c"
        c.write_text("overwritten")
        for flag, value in (("--file", "package.json"), ("--path", ".project/specs/website.json")):
            self.assertEqual(self.edit("write", "--state", st, "--content-file", str(c), flag, value)[0], 2)
        idx = json.loads((Path(st) / "index.json").read_text())
        for target in ("package.json", "rules/seo.md", ".project/specs/website.managed.json", "../../.project/specs/website.json"):
            (Path(st) / "index.json").write_text(json.dumps({**idx, "file": target}))
            self.assertEqual(self.write(st, NEW)[0], 1, target)
        self.assertEqual(delta(before, self.snap()), set())


if __name__ == "__main__":
    import unittest
    unittest.main()
