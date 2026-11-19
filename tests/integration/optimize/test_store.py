"""Protection of the report area: exclusive snapshots, symlinks, damaged work lists, locks and concurrent updates.

Ported from the source suite; fixtures fictional."""
import hashlib
import os
import unittest
from pathlib import Path
from unittest import mock

from tests.support import optimize_helpers as h
import audit
import store
import worklist as wl
from site_common.errors import Stop


def tree(root: Path) -> dict:
    """Content hash of every file outside .git, build outputs and the report area."""
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_dir() or rel.startswith(".git/") or "/dist/" in rel or "/node_modules/" in rel or rel.startswith(".project/reports"):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class Protection(h.AuditCase):
    def rdir(self):
        return self.root / ".project" / "reports" / "fx.test"

    def test_audit_writes_only_the_report_area(self):
        before = tree(self.root)
        self.audit()
        self.audit(minutes=1)
        self.assertEqual(tree(self.root), before)
        names = sorted(p.name for p in self.rdir().rglob("*"))
        self.assertFalse([n for n in names if n.endswith(".tmp") or n == store.LOCK], names)

    def test_existing_report_with_same_timestamp_is_never_overwritten(self):
        d = self.rdir() / "optimize"
        d.mkdir(parents=True)
        (d / "20261117-144400.md").write_text("mine")
        r = self.audit()
        self.assertEqual((d / "20261117-144400.md").read_text(), "mine")
        self.assertTrue(r["report"].endswith("20261117-144400-2.md"))
        self.assertIn("optimize/20261117-144400-2.md", self.finding("SEO-001")["reports"])
        self.assertIn("20261117-144400-2.md", (self.root / r["report"]).read_text() + wl.render(self.state()))

    def test_collision_that_appears_during_the_run_gets_next_free_name(self):
        d = self.rdir() / "optimize"

        def appear(final):
            if final.name == "20261117-144400.md":
                final.write_text("raced")
        r = audit.do_audit(self.root, h.COMPONENT, npm=str(self.npm), now=self.now(), hooks={"before_link": appear})
        self.assertEqual((d / "20261117-144400.md").read_text(), "raced")
        self.assertTrue(r["report"].endswith("-2.md"))
        self.assertIn("-2.md", self.state()["last_run"]["report"])

    def test_dangling_symlink_as_report_name_is_not_followed(self):
        d = self.rdir() / "optimize"
        d.mkdir(parents=True)
        outside = self.tmp / "outside.txt"
        os.symlink(outside, d / "20261117-144400.md")
        r = self.audit()
        self.assertFalse(outside.exists())
        self.assertTrue(r["report"].endswith("-2.md"))

    def test_symlinked_report_folders_are_refused(self):
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        os.makedirs(self.root / ".project" / "reports")
        os.symlink(outside, self.rdir())
        with self.assertRaises(Stop) as ctx:
            self.audit()
        self.assertIn("symlink", str(ctx.exception))
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.npm_calls(), [])

    def test_symlinked_optimize_folder_and_worklist_are_refused(self):
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        self.rdir().mkdir(parents=True)
        os.symlink(outside, self.rdir() / "optimize")
        with self.assertRaises(Stop):
            self.audit()
        self.assertEqual(list(outside.iterdir()), [])
        os.unlink(self.rdir() / "optimize")
        target = self.tmp / "target.md"
        target.write_text("keep")
        os.symlink(target, self.rdir() / "optimize.md")
        with self.assertRaises(Stop):
            self.audit()
        self.assertEqual(target.read_text(), "keep")

    def test_symlinked_project_folder_is_refused(self):
        real = self.tmp / "real-project"
        (self.root / ".project" / "reports").mkdir(parents=True)
        os.rename(self.root / ".project" / "reports", real)
        os.symlink(real, self.root / ".project" / "reports")
        with self.assertRaises(Stop):
            self.audit()

    def test_site_name_cannot_traverse(self):
        for bad in ("../x", "a/b", "", ".hidden", "A B", "a..b"):
            with self.assertRaises(Stop, msg=bad):
                store.site_root(self.root, bad)

    def test_foreign_files_in_report_area_stay_untouched(self):
        d = self.rdir() / "optimize"
        d.mkdir(parents=True)
        (d / "notes.txt").write_text("foreign")
        (self.rdir() / "other.md").write_text("foreign too")
        self.audit()
        self.assertEqual((d / "notes.txt").read_text(), "foreign")
        self.assertEqual((self.rdir() / "other.md").read_text(), "foreign too")

    def test_interrupted_replace_keeps_old_worklist_and_leaves_no_temp(self):
        self.audit()
        path = self.rdir() / "optimize.md"
        old = path.read_text()
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.decide(["SEO-001"], "approved")
        self.assertEqual(path.read_text(), old)
        self.assertEqual([p.name for p in self.rdir().iterdir() if p.name.endswith(".tmp")], [])
        self.assertFalse((self.rdir() / store.LOCK).exists())
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")


class DamagedWorklist(h.AuditCase):
    def path(self):
        return self.root / ".project" / "reports" / "fx.test" / "optimize.md"

    def test_garbage_stops_before_anything_is_built_and_is_not_overwritten(self):
        self.path().parent.mkdir(parents=True)
        self.path().write_text("this is not a work list\n")
        with self.assertRaises(Stop) as ctx:
            self.audit()
        self.assertIn("no intact machine-readable state block", str(ctx.exception))
        self.assertEqual(self.path().read_text(), "this is not a work list\n")
        self.assertEqual(self.npm_calls(), [])
        self.assertEqual(self.reports(), [])

    def test_hand_edited_text_is_detected_and_decisions_are_not_overwritten(self):
        self.audit()
        text = self.path().read_text()
        edited = text.replace("### SEO-001 - meta description is short (warning) - proposed", "### SEO-001 - meta description is short (warning) - approved", 1)
        self.assertNotEqual(edited, text)
        self.path().write_text(edited)
        for call in (lambda: self.audit(minutes=1), lambda: self.decide(["SEO-002"], "wont-do")):
            with self.assertRaises(Stop) as ctx:
                call()
            self.assertIn("edited by hand", str(ctx.exception))
        self.assertEqual(self.path().read_text(), edited)

    def test_state_block_checksum_and_json_damage(self):
        self.audit()
        text = self.path().read_text()
        cut = text[: text.index("```json") + 40] + "\n```\n<!-- /zyris-optimize:state -->\n"
        self.path().write_text(cut)
        with self.assertRaises(Stop):
            self.audit(minutes=1)
        self.path().write_text(text.replace('"rev": 1', '"rev": 7'))
        with self.assertRaises(Stop) as ctx:
            self.audit(minutes=1)
        self.assertIn("checksum", str(ctx.exception))

    def test_worklist_of_another_site_is_refused(self):
        self.audit()
        text = self.path().read_text()
        state = self.state()
        state["site"] = "other.test"
        self.path().write_text(wl.render(state))
        with self.assertRaises(Stop) as ctx:
            self.audit(minutes=1)
        self.assertIn("belongs to site", str(ctx.exception))

    def test_decide_without_worklist_stops(self):
        with self.assertRaises(Stop):
            self.decide(["SEO-001"], "approved")


class Concurrency(h.AuditCase):
    def path(self):
        return self.root / ".project" / "reports" / "fx.test" / "optimize.md"

    def test_existing_lock_blocks_commit_and_names_the_file(self):
        self.audit()
        before = self.path().read_text()
        lock = self.path().parent / store.LOCK
        lock.write_text("pid=1")
        with self.assertRaises(store.Conflict) as ctx:
            self.audit(minutes=1)
        self.assertIn(str(lock), str(ctx.exception))
        self.assertEqual(self.path().read_text(), before)
        self.assertEqual(self.reports(), ["20261117-144400.md"])
        self.assertEqual(lock.read_text(), "pid=1")
        with self.assertRaises(store.Conflict):
            self.decide(["SEO-001"], "approved")

    def test_decision_made_while_the_audit_ran_is_merged_not_overwritten(self):
        self.audit()
        hook = lambda: self.decide(["SEO-001"], "wont-do", minutes=1, reason="decided meanwhile")
        r = audit.do_audit(self.root, h.COMPONENT, npm=str(self.npm), now=self.now(2), hooks={"before_commit": hook})
        self.assertTrue(r["rebased"])
        f = self.finding("SEO-001")
        self.assertEqual(f["status"], "wont-do")
        self.assertEqual(f["decision_log"][-1]["reason"], "decided meanwhile")
        self.assertIn("changed by someone else", (self.root / r["report"]).read_text())

    def test_change_between_snapshot_and_replace_is_a_conflict_and_nothing_is_overwritten(self):
        self.audit()

        def meddle():
            self.decide(["SEO-001"], "deferred", minutes=1)

        # hook runs while the lock is held by the audit: a second writer must be stopped by the lock
        with self.assertRaises(store.Conflict):
            audit.do_audit(self.root, h.COMPONENT, npm=str(self.npm), now=self.now(2), hooks={"before_replace": meddle})
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")
        self.assertFalse((self.path().parent / store.LOCK).exists())

    def test_outside_edit_at_write_time_is_detected(self):
        self.audit()
        marker = self.path().read_text() + "\nextra\n"

        def meddle():
            self.path().write_text(marker)

        with self.assertRaises(store.Conflict) as ctx:
            audit.do_audit(self.root, h.COMPONENT, npm=str(self.npm), now=self.now(2), hooks={"before_replace": meddle})
        self.assertIn("was written and is valid", str(ctx.exception))
        self.assertEqual(self.path().read_text(), marker)
        self.assertEqual(self.reports(), ["20261117-144400.md", "20261117-144600.md"])


if __name__ == "__main__":
    unittest.main()
