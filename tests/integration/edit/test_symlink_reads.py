"""edit refuses symbolic links in the target, in every path component and in package.json AND does not read anything behind them.
An unchanged external file hash cannot prove the second part, so the helper runs under an access spy (tests/support/edit_spy.py:
audit hook on every `open` and directory listing of the process). The shared resolver, git and npm run as child processes and are
not covered by the spy."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, tree

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")
SECRET = "EXTERNAL SECRET CONTENT\n"


class SpiedCase(EditCase):
    def setUp(self):
        super().setUp()
        self.external = self.tmpdir / "external"
        self.external.mkdir()
        self.external_before = None

    def spy(self, *args):
        log = self.tmpdir / "spy.json"
        p = subprocess.run([sys.executable, "-I", "-B", str(t.SPY), str(log), str(t.EDIT), *args], capture_output=True, text=True, env=self.env)
        try:
            data = json.loads(p.stdout)
        except ValueError:
            data = {"raw": p.stdout + p.stderr}
        return p.returncode, data, json.loads(log.read_text())

    def reads_of(self, records, folder):
        folder = os.path.realpath(folder)
        return [r for r in records if r["real"] == folder or r["real"].startswith(folder + os.sep)]

    def assert_no_external_access(self, records, label):
        self.assertEqual(self.reads_of(records, self.external), [], label)

    def commands(self, state=None):
        c = self.tmpdir / "content.astro"
        c.write_text(NEW)
        base = [("preflight", ("preflight", "--root", str(self.root), self.DOMAIN)),
                ("begin", ("begin", "--root", str(self.root), "--site", self.DOMAIN))]
        if state:
            base = [("write", ("write", "--state", state, "--content-file", str(c))),
                    ("replace", ("replace", "--state", state, "--find", "Sundays", "--replace", "Mondays")),
                    ("check", ("check", "--state", state, "--npm", str(self.npm))),
                    ("diff", ("diff", "--state", state)),
                    ("finish", ("finish", "--state", state, "--visual-done"))]
        return base


class SpyWorks(SpiedCase):
    def test_the_spy_records_the_files_the_helper_really_reads(self):
        st = self.begin()
        code, d, records = self.spy("diff", "--state", st)
        self.assertEqual(code, 0, d)
        reals = [r["real"] for r in records]
        self.assertIn(os.path.realpath(self.index), reals)
        self.assertIn(os.path.realpath(Path(st) / "original" / "src/pages/index.astro"), reals)
        code, d, records = self.spy("preflight", "--root", str(self.root))
        self.assertIn(os.path.realpath(self.site / "package.json"), [r["real"] for r in records])


class SymlinksAtBegin(SpiedCase):
    def check_refusal(self, label, expect_in_message=None):
        project = self.snap()
        for name, argv in self.commands():
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 1, (label, name, d))
            self.assertNotIn("raw", d, (label, name))
            self.assertNotIn("Traceback", json.dumps(d))
            self.assert_no_external_access(records, f"{label}/{name}")
            if expect_in_message:
                self.assertIn(expect_in_message, d["message"], (label, name))
        self.assertEqual(self.snap(), project, label)
        self.assertEqual(self.state_files(), {}, label)
        self.assertEqual(tree(self.external), self.external_before, label)

    def test_symlinked_target_file(self):
        (self.external / "index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        self.index.unlink()
        os.symlink(self.external / "index.astro", self.index)
        self.check_refusal("target", "symlink")

    def test_symlinked_pages_directory(self):
        (self.external / "index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        pages = self.site / "src" / "pages"
        shutil.rmtree(pages)
        os.symlink(self.external, pages)
        self.check_refusal("pages dir", "symlink")

    def test_symlinked_src_directory(self):
        (self.external / "pages").mkdir()
        (self.external / "pages" / "index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        shutil.rmtree(self.site / "src")
        os.symlink(self.external, self.site / "src")
        self.check_refusal("src dir", "symlink")

    def test_symlinked_site_folder(self):
        shutil.copytree(self.site, self.external / "site", symlinks=True)
        (self.external / "site" / "src/pages/index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        shutil.rmtree(self.site)
        os.symlink(self.external / "site", self.site)
        self.check_refusal("site dir", "symlink")

    def test_symlinked_package_json_is_not_read(self):
        (self.external / "package.json").write_text(json.dumps({"scripts": {"build": "x", "check": "x"}, "secret": SECRET}))
        self.external_before = tree(self.external)
        (self.site / "package.json").unlink()
        os.symlink(self.external / "package.json", self.site / "package.json")
        self.check_refusal("package.json", "not a regular file")

    def test_a_symlinked_lockfile_or_node_modules_is_only_looked_at_never_read(self):
        (self.external / "lock").write_text(SECRET)
        (self.external / "nm").mkdir()
        (self.external / "nm" / "x").write_text(SECRET)
        self.external_before = tree(self.external)
        (self.site / "package-lock.json").unlink()
        os.symlink(self.external / "lock", self.site / "package-lock.json")
        shutil.rmtree(self.site / "node_modules")
        os.symlink(self.external / "nm", self.site / "node_modules")
        for name, argv in self.commands():
            code, d, records = self.spy(*argv)
            self.assert_no_external_access(records, name)
        self.assertEqual(tree(self.external), self.external_before)


class SymlinksAfterBegin(SpiedCase):
    def refused_everywhere(self, st, label):
        project = self.snap()
        for name, argv in self.commands(st):
            code, d, records = self.spy(*argv)
            self.assertEqual(code, 1, (label, name, d))
            kind = d.get("state") or ("conflict" if str(d.get("outcome", "")).startswith("conflict") else None)     # finish reports an outcome
            self.assertEqual(kind, "conflict", (label, name, d))
            self.assertNotIn("Traceback", json.dumps(d))
            self.assert_no_external_access(records, f"{label}/{name}")
        self.assertEqual(self.snap(), project, label)
        self.assertEqual(tree(self.external), self.external_before, label)
        self.assertTrue(Path(st).is_dir())
        self.assertEqual(self.npm_calls(), [])

    def test_target_replaced_by_a_symlink(self):
        (self.external / "index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        st = self.begin()
        self.index.unlink()
        os.symlink(self.external / "index.astro", self.index)
        self.refused_everywhere(st, "target")

    def test_pages_directory_replaced_by_a_symlink(self):
        (self.external / "index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        st = self.begin()
        pages = self.site / "src" / "pages"
        shutil.rmtree(pages)
        os.symlink(self.external, pages)
        self.refused_everywhere(st, "pages dir")

    def test_site_folder_replaced_by_a_symlink(self):
        shutil.copytree(self.site, self.external / "site", symlinks=True)
        (self.external / "site" / "src/pages/index.astro").write_text(SECRET)
        self.external_before = tree(self.external)
        st = self.begin()
        shutil.rmtree(self.site)
        os.symlink(self.external / "site", self.site)
        self.refused_everywhere(st, "site dir")

    def test_a_removed_target_is_a_conflict_without_any_external_access(self):
        self.external_before = tree(self.external)
        st = self.begin()
        self.index.unlink()
        self.refused_everywhere(st, "removed")


if __name__ == "__main__":
    import unittest
    unittest.main()
