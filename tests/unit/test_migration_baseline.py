"""scripts/migration_baseline.py on fictional inventories and trees: detects drift, never writes, never executes."""
import contextlib
import hashlib
import io
import os
from unittest import mock
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support import projects as P

_spec = importlib.util.spec_from_file_location("migration_baseline", P.ROOT / "scripts" / "migration_baseline.py")
mb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mb)


def h(text):
    return hashlib.sha256(text.encode()).hexdigest()


class Case(unittest.TestCase):
    PLUGIN = "plug"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "src"
        (self.root / self.PLUGIN / "a").mkdir(parents=True)
        self.files = {f"{self.PLUGIN}/a/one.txt": "one", f"{self.PLUGIN}/two.txt": "two"}
        for rel, text in self.files.items():
            (self.root / rel).write_text(text)
        self.inventory = self.tmp / "inv.json"
        self.write_inventory()

    def write_inventory(self, **extra):
        data = {"format": mb.SOURCE_FORMAT, "plugin_root": self.PLUGIN,
                "files": [{"path": rel, "sha256": h(text)} for rel, text in self.files.items()],
                "excluded": [{"pattern": f"{self.PLUGIN}/gen/*", "reason": "generated"}], **extra}
        self.inventory.write_text(json.dumps(data))

    def run_check(self, **kw):
        return mb.run(self.inventory, self.root, **kw)


class DriftTests(Case):
    def test_identical_tree_has_no_drift(self):
        code, lines = self.run_check()
        self.assertEqual(code, 0, lines)
        self.assertIn("NO DRIFT", lines[-1])

    def test_changed_file(self):
        (self.root / self.PLUGIN / "two.txt").write_text("changed")
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn(f"DRIFT changed: {self.PLUGIN}/two.txt", lines)

    def test_missing_file(self):
        (self.root / self.PLUGIN / "a" / "one.txt").unlink()
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn(f"DRIFT missing: {self.PLUGIN}/a/one.txt", lines)

    def test_new_relevant_file_is_drift_but_excluded_and_generated_files_are_not(self):
        (self.root / self.PLUGIN / "gen").mkdir()
        (self.root / self.PLUGIN / "gen" / "x.txt").write_text("x")
        (self.root / self.PLUGIN / "a" / "__pycache__").mkdir()
        (self.root / self.PLUGIN / "a" / "__pycache__" / "m.pyc").write_bytes(b"\0")
        (self.root / self.PLUGIN / ".DS_Store").write_text("")
        self.assertEqual(self.run_check()[0], 0)
        (self.root / self.PLUGIN / "a" / "new.py").write_text("print(1)")
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn(f"DRIFT new relevant file: {self.PLUGIN}/a/new.py", lines)

    def test_files_outside_the_plugin_root_are_not_scanned(self):
        (self.root / "other").mkdir()
        (self.root / "other" / "private.txt").write_text("x")
        self.assertEqual(self.run_check()[0], 0)


class SafetyTests(Case):
    def test_nothing_is_written_executed_or_imported(self):
        marker = self.tmp / "executed.marker"
        (self.root / self.PLUGIN / "evil.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n")
        self.files[f"{self.PLUGIN}/evil.py"] = (self.root / self.PLUGIN / "evil.py").read_text()
        self.write_inventory()
        before = P.tree_snapshot(self.tmp)
        code, _ = self.run_check()
        self.assertEqual(code, 0)
        self.assertFalse(marker.exists())
        self.assertEqual(P.tree_snapshot(self.tmp), before, "no baseline written, no cache created")

    def test_unsupported_or_unreadable_inventory_is_rejected(self):
        self.inventory.write_text(json.dumps({"format": "other/1", "files": []}))
        with self.assertRaises(mb.InventoryError):
            self.run_check()
        self.inventory.write_text("{broken")
        with self.assertRaises(mb.InventoryError):
            self.run_check()

    def test_cli_exit_codes(self):
        def main(*argv):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return mb.main(list(argv))
        self.assertEqual(main("--inventory", str(self.inventory), "--root", str(self.root)), 0)
        (self.root / self.PLUGIN / "two.txt").write_text("x")
        self.assertEqual(main("--inventory", str(self.inventory), "--root", str(self.root)), 1)
        self.assertEqual(main("--inventory", str(self.inventory), "--root", str(self.tmp / "nope")), 2)
        self.assertEqual(main("--inventory", str(self.tmp / "missing.json"), "--root", str(self.root)), 2)


class InventoryValidationTests(Case):
    def bad(self, **change):
        data = json.loads(self.inventory.read_text())
        data.update(change)
        self.inventory.write_text(json.dumps(data))
        with self.assertRaises(mb.InventoryError) as ctx:
            self.run_check()
        return str(ctx.exception)

    def entry(self, **kw):
        return {"path": f"{self.PLUGIN}/two.txt", "sha256": h("two"), **kw}

    def test_absolute_and_traversal_paths_are_rejected_before_any_read(self):
        for bad in ("/etc/hosts", "../outside.txt", f"{self.PLUGIN}/../../x", "a//b", "./a", "a/", "C:/x", "a\\b", ""):
            with mock.patch.object(mb.os, "open") as opened:
                msg = self.bad(files=[self.entry(path=bad)])
            self.assertIn("files[0]", msg, bad)
            opened.assert_not_called()

    def test_invalid_entries_are_diagnosed_not_crashed(self):
        for label, files in {"not an object": ["x"], "no path": [{"sha256": h("a")}], "path not a string": [{"path": 1, "sha256": h("a")}],
                             "no sha": [{"path": "a.txt"}], "short sha": [self.entry(sha256="abc")], "upper sha": [self.entry(sha256=h("two").upper())],
                             "sha not string": [self.entry(sha256=5)], "duplicate": [self.entry(), self.entry()]}.items():
            self.bad(files=files)

    def test_plugin_root_is_required_and_validated_and_never_replaced_by_the_whole_tree(self):
        for bad in ("/abs", "../up", "", None, 5, "a/../b"):
            data = json.loads(self.inventory.read_text())
            data["plugin_root"] = bad
            self.inventory.write_text(json.dumps(data))
            with self.assertRaises(mb.InventoryError, msg=repr(bad)):
                self.run_check()
        data = json.loads(self.inventory.read_text())
        del data["plugin_root"]
        self.inventory.write_text(json.dumps(data))
        with self.assertRaises(mb.InventoryError):
            self.run_check()

    def test_missing_plugin_root_directory_is_drift_and_scans_nothing(self):
        self.write_inventory(plugin_root="absent")
        (self.root / "stray.txt").write_text("x")
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertTrue(any("unsafe plugin root" in l and "nothing scanned" in l for l in lines), lines)
        self.assertFalse(any("stray.txt" in l for l in lines))

    def test_invalid_excluded_and_git_records_and_reference_repositories(self):
        self.bad(excluded=[{"reason": "no pattern"}])
        self.bad(excluded="x")
        self.bad(repository={"head": 5})
        self.bad(repository={"status_porcelain": "x"})
        ref = self.tmp / "ref.json"
        for repos in ({"/abs": {}}, {"../up": {}}, {"a/b": {}}, {"ok": []}):
            ref.write_text(json.dumps({"format": mb.REFERENCE_FORMAT, "repositories": repos, "files": []}))
            with self.assertRaises(mb.InventoryError, msg=str(repos)):
                mb.run(ref, self.tmp)

    def test_cli_reports_damaged_inventory_with_exit_2_and_diagnosis(self):
        self.inventory.write_text(json.dumps({"format": mb.SOURCE_FORMAT, "plugin_root": "plug", "files": [{"path": "/abs", "sha256": "x"}]}))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = mb.main(["--inventory", str(self.inventory), "--root", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("STOP: invalid inventory", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


class SymlinkTests(Case):
    def setUp(self):
        super().setUp()
        self.outside = self.tmp / "outside"
        self.outside.mkdir()

    def opened_paths(self, call):
        real_open, seen = os.open, []
        def spy(path, *a, **k):
            seen.append(str(path))
            return real_open(path, *a, **k)
        with mock.patch.object(mb.os, "open", spy):
            result = call()
        return result, seen

    def test_file_replaced_by_symlink_is_unsafe_even_with_identical_target_content(self):
        target = self.outside / "same.txt"
        target.write_text("two")                                     # identical bytes to the inventoried file
        (self.root / self.PLUGIN / "two.txt").unlink()
        (self.root / self.PLUGIN / "two.txt").symlink_to(target)
        (code, lines), opened = self.opened_paths(self.run_check)
        self.assertEqual(code, 1)
        self.assertTrue(any(l.startswith("DRIFT unsafe path") and "two.txt" in l and "symlink" in l for l in lines), lines)
        self.assertNotIn(str(target), opened)
        self.assertFalse(any(str(self.outside) in o for o in opened))

    def test_symlink_in_a_parent_component_is_not_followed(self):
        (self.outside / "one.txt").write_text("one")
        import shutil
        shutil.rmtree(self.root / self.PLUGIN / "a")
        (self.root / self.PLUGIN / "a").symlink_to(self.outside, target_is_directory=True)
        (code, lines), opened = self.opened_paths(self.run_check)
        self.assertEqual(code, 1)
        self.assertTrue(any("unsafe path" in l and "a/one.txt" in l and f"symlink at {self.PLUGIN}/a" in l for l in lines), lines)
        self.assertFalse(any(str(self.outside) in o for o in opened))
        self.assertFalse(any("new relevant file" in l for l in lines), "link target content is not listed")

    def test_plugin_root_itself_a_symlink_is_not_scanned(self):
        import shutil
        shutil.move(str(self.root / self.PLUGIN), str(self.outside / "moved"))
        (self.root / self.PLUGIN).symlink_to(self.outside / "moved", target_is_directory=True)
        code, lines = self.run_check()
        self.assertEqual(code, 1)
        self.assertTrue(any("unsafe plugin root" in l and "symlink" in l for l in lines), lines)
        self.assertTrue(any("unsafe path" in l for l in lines))

    def test_new_symlinks_file_dir_and_broken_are_reported_not_skipped(self):
        (self.outside / "f.txt").write_text("x")
        base = self.root / self.PLUGIN
        (base / "newfile").symlink_to(self.outside / "f.txt")
        (base / "newdir").symlink_to(self.outside, target_is_directory=True)
        (base / "broken").symlink_to(self.tmp / "does-not-exist")
        (code, lines), opened = self.opened_paths(self.run_check)
        self.assertEqual(code, 1)
        for name in ("newfile", "newdir", "broken"):
            self.assertIn(f"DRIFT new symlink: {self.PLUGIN}/{name}", lines)
        self.assertFalse(any(str(self.outside) in o for o in opened))
        self.assertFalse(any("f.txt" in l for l in lines), "content behind a directory link is not listed")

    def test_broken_symlink_at_an_inventoried_path_is_unsafe_not_missing(self):
        (self.root / self.PLUGIN / "two.txt").unlink()
        (self.root / self.PLUGIN / "two.txt").symlink_to(self.tmp / "gone")
        code, lines = self.run_check()
        self.assertTrue(any(l.startswith("DRIFT unsafe path") for l in lines), lines)

    def test_excluded_symlink_is_not_reported_and_inventoried_non_regular_file_is_unsafe(self):
        (self.root / self.PLUGIN / "gen").mkdir()
        (self.root / self.PLUGIN / "gen" / "l").symlink_to(self.outside)
        self.assertEqual(self.run_check()[0], 0)
        (self.root / self.PLUGIN / "two.txt").unlink()
        (self.root / self.PLUGIN / "two.txt").mkdir()
        code, lines = self.run_check()
        self.assertTrue(any("unsafe path" in l and "not a regular file" in l for l in lines), lines)

    def test_excluded_directories_are_not_listed(self):
        (self.root / self.PLUGIN / "gen").mkdir()
        listed = []
        real_walk = os.walk
        def spy(top, *a, **k):
            for current, dirs, files in real_walk(top, *a, **k):
                listed.append(current)
                yield current, dirs, files
        with mock.patch.object(mb.os, "walk", spy):
            self.run_check()
        self.assertFalse(any(c.endswith("/gen") for c in listed), listed)

    def test_regular_runs_still_work_with_links_present_but_excluded_or_known(self):
        self.assertEqual(self.run_check()[0], 0)


class GitAndReferenceTests(Case):
    def init_repo(self):
        for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                     ["-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(self.root), *args], check=True)
        head = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return head

    def test_git_differences_are_notes_unless_strict(self):
        head = self.init_repo()
        self.write_inventory(repository={"head": head, "status_porcelain": []})
        self.assertEqual(self.run_check()[0], 0)
        (self.root / "unrelated.txt").write_text("elsewhere")                    # outside the plugin root
        code, lines = self.run_check()
        self.assertEqual(code, 0)
        self.assertTrue(any("status line added (outside plugin)" in l for l in lines), lines)
        self.assertEqual(self.run_check(strict_git=True)[0], 1)

    def test_changed_head_is_reported(self):
        head = self.init_repo()
        self.write_inventory(repository={"head": "0" * 40, "status_porcelain": []})
        code, lines = self.run_check()
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith("NOTE git: HEAD differs") for l in lines))
        self.assertNotEqual(head, "0" * 40)

    def test_reference_baseline_format(self):
        (self.tmp / "refrepo").mkdir()
        (self.tmp / "refrepo" / "rules.md").write_text("rule")
        ref = self.tmp / "ref.json"
        ref.write_text(json.dumps({"format": mb.REFERENCE_FORMAT, "repositories": {},
                                   "files": [{"path": "refrepo/rules.md", "sha256": h("rule")}]}))
        self.assertEqual(mb.run(ref, self.tmp)[0], 0)
        (self.tmp / "refrepo" / "rules.md").write_text("changed rule")
        code, lines = mb.run(ref, self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("DRIFT changed: refrepo/rules.md", lines)


if __name__ == "__main__":
    unittest.main()
