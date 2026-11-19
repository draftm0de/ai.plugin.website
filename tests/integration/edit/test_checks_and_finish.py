"""edit: check, repair limit, evidence bound to content, finish states. Real process exit codes of fake npm processes.
A test with --visual-done proves the state logic only, never a real visual inspection."""
import json
import os
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support.edit_helpers import EditCase, GOOD, delta, sha

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")


class Checks(EditCase):
    def test_e12_failed_build_with_stale_dist_is_not_evidence(self):
        (self.site / "dist").mkdir(exist_ok=True)
        (self.site / "dist" / "index.html").write_text("stale but green")
        st = self.begin()
        self.write(st, NEW + "<!-- BREAK_BUILD -->\n")
        code, d = self.check(st)
        self.assertEqual((code, d["state"], d["build"]["exit"]), (1, "failed", 3))
        self.assertFalse(d["check"]["ran"])
        self.assertIn("build failed", d["check"]["reason"])
        self.assertEqual(self.npm_calls(), ["run build"])                                    # the check script never ran
        _, f = self.finish(st, visual=True)
        self.assertNotEqual(f["outcome"], "complete")
        self.assertEqual((f["technical"], f["backup"]), ("failed", "kept"))

    def test_exit_codes_of_the_processes_are_reported_as_they_are(self):
        st = self.begin()
        self.write(st, NEW + "<!-- BAD_CHECK -->\n")
        code, d = self.check(st)
        self.assertEqual((code, d["state"], d["build"]["exit"], d["check"]["exit"]), (1, "failed", 0, 1))
        self.assertIn("Errors (1)", d["check"]["tail"])
        odd = self.tmpdir / "bin" / "npm-odd"                                                # an exit code that is neither 0 nor 1
        odd.write_text('#!/bin/sh\necho "$*" >> "$FAKE_NPM_LOG"\n[ "$2" = build ] && exit 0\nexit 42\n')
        odd.chmod(0o755)
        self.write(st, NEW)
        code, d = self.check(st, npm=odd)
        self.assertEqual((code, d["state"], d["check"]["exit"]), (1, "failed", 42))

    def test_a_missing_npm_is_not_run_not_failed_and_not_passed(self):
        st = self.begin()
        self.write(st, NEW)
        code, d = self.check(st, npm=self.tmpdir / "bin" / "no-such-npm")
        self.assertEqual((code, d["state"]), (1, "not-run"), d)
        self.assertIsNone(d["build"]["exit"])
        self.assertFalse(d["build"]["ran"])
        self.assertIn("could not run", d["build"]["reason"])
        self.assertNotIn("Traceback", json.dumps(d))
        saved = json.loads((Path(st) / "index.json").read_text())
        self.assertFalse(saved["check_failed_since_write"])                                  # no repair round was consumed
        _, f = self.finish(st, visual=True)
        self.assertEqual(f["technical"], "not run: npm could not be started")
        self.assertIn("not complete", f["outcome"])
        self.assertNotEqual(f["outcome"], "technically checked, visual check open")
        self.assertTrue(Path(st).is_dir())

    def test_e14_repair_rounds_are_bounded_and_own_failure_repairable(self):
        st = self.begin()
        self.write(st, NEW + "<!-- BAD_CHECK -->\n")
        self.assertEqual(self.check(st)[1]["state"], "failed")
        code, d = self.write(st, NEW)                                                        # repair round 1: no false conflict
        self.assertEqual((code, d["state"], d["repair_rounds"]), (0, "written", 1))
        self.assertEqual(self.check(st)[1]["state"], "checked")
        st2 = self.begin()                                                                   # a run that never repairs stops after two rounds
        self.write(st2, NEW + "<!-- BAD_CHECK a -->\n")
        for i, mark in enumerate(("b", "c"), 1):
            self.assertEqual(self.check(st2)[1]["state"], "failed")
            self.assertEqual(self.write(st2, NEW + f"<!-- BAD_CHECK {mark} -->\n")[1]["repair_rounds"], i)
        self.assertEqual(self.check(st2)[1]["state"], "failed")
        before = self.snap()
        code, d = self.write(st2, NEW)
        self.assertEqual((code, d["state"]), (1, "repair-limit"))
        code, d = self.replace(st2, "Sundays", "Mondays")
        self.assertEqual((code, d["state"]), (1, "repair-limit"))
        self.assertEqual(delta(before, self.snap()), set())
        _, f = self.finish(st2, visual=True)
        self.assertEqual(f["technical"], "failed")
        self.assertIn("not complete", f["outcome"])
        self.assertEqual(f["backup"], "kept")

    def test_a_failure_caused_by_the_tool_is_not_a_repair_round(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st, npm=self.tmpdir / "bin" / "no-such-npm")
        code, d = self.write(st, NEW.replace("Sundays", "Mondays"))
        self.assertEqual((code, d["repair_rounds"]), (0, 0))


class Outcome(EditCase):
    def test_e17_outcome_wording_and_cleanup(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        _, f = self.finish(st)                                                               # no visual inspection
        self.assertEqual(f["outcome"], "technically checked, visual check open")
        self.assertEqual((f["visual"], f["backup"]), ("open", "kept"))
        self.assertTrue(Path(st).is_dir())
        _, f = self.finish(st, visual=True)
        self.assertEqual(f["outcome"], "complete")
        self.assertFalse(Path(st).exists())

    def test_failed_or_unrun_technique_is_never_reworded_as_visual_open(self):
        st = self.begin()
        self.write(st, NEW)
        _, f = self.finish(st)                                                               # nothing ran
        self.assertEqual(f["technical"], "not run")
        self.assertNotIn("technically checked", f["outcome"])
        self.write(st, NEW + "<!-- BAD_CHECK -->\n")
        self.check(st)
        _, f = self.finish(st)
        self.assertEqual(f["technical"], "failed")
        self.assertNotIn("technically checked", f["outcome"])
        self.assertEqual(f["visual"], "open")

    def test_finish_without_check_is_not_complete(self):
        st = self.begin()
        self.write(st, NEW)
        _, f = self.finish(st, visual=True)
        self.assertEqual(f["technical"], "not run")
        self.assertIn("not complete", f["outcome"])
        self.assertTrue(Path(st).is_dir())

    def test_substitutes_and_checks_not_done_are_reported_without_false_equivalence(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        code, f = self.edit("finish", "--state", st, "--visual-done", "--visual-substitute", "narrow window instead of browser zoom",
                            "--visual-not-done", "200 percent zoom")
        self.assertEqual((code, f["outcome"]), (0, "complete"))
        self.assertEqual(f["visual_substitutes"], ["narrow window instead of browser zoom"])
        self.assertEqual(f["visual_not_done"], ["200 percent zoom"])

    def test_open_visual_check_keeps_backup_and_lists_nothing_as_done(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        code, f = self.finish(st)
        self.assertEqual(f["outcome"], "technically checked, visual check open")
        self.assertEqual((f["visual_substitutes"], f["visual_not_done"]), ([], []))
        self.assertTrue(Path(st).is_dir())


class EvidenceBinding(EditCase):
    """A check result counts only for the content it was run on."""

    def checked(self):
        st = self.begin()
        self.write(st, NEW)
        self.assertEqual(self.check(st)[1]["state"], "checked")
        return st

    def test_own_write_after_green_check_invalidates_the_evidence(self):
        st = self.checked()
        self.write(st, NEW + "<!-- BREAK_BUILD -->\n")
        code, f = self.finish(st, visual=True)
        self.assertNotEqual(f["outcome"], "complete")
        self.assertIn("stale", f["technical"])
        self.assertEqual(f["backup"], "kept")
        self.assertTrue(Path(st).is_dir())
        self.write(st, NEW.replace("Sundays", "Sundays and Fridays"))                        # a new green check makes the end regular again
        self.assertEqual(self.check(st)[1]["state"], "checked")
        code, f = self.finish(st, visual=True)
        self.assertEqual((code, f["outcome"]), (0, "complete"))
        self.assertFalse(Path(st).exists())

    def test_foreign_change_after_green_check_is_a_conflict(self):
        st = self.checked()
        theirs = NEW + "<!-- foreign -->\n"
        self.index.write_text(theirs)
        code, f = self.finish(st, visual=True)
        self.assertEqual(code, 1)
        self.assertEqual(f["outcome"], "conflict: nothing complete")
        self.assertEqual(f["total_diff"].split(":")[0], "withheld")
        self.assertNotIn("foreign", json.dumps(f["total_diff"]))
        self.assertEqual(self.index.read_text(), theirs)
        self.assertTrue(Path(st).is_dir())
        self.assertEqual(self.edit("diff", "--state", st)[1]["state"], "conflict")
        self.assertEqual(self.write(st, NEW)[1]["state"], "conflict")                         # stays a conflict afterwards

    def test_change_during_the_checks_is_a_conflict(self):
        st = self.begin()
        self.write(st, NEW)
        racing = self.tmpdir / "bin" / "npm-mutating"
        racing.write_text(self.npm.read_text().replace("check) if", 'check) echo "<!-- raced -->" >> src/pages/index.astro; if'))
        racing.chmod(0o755)
        code, d = self.check(st, npm=racing)
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertIn("raced", self.index.read_text())
        code, f = self.finish(st, visual=True)
        self.assertEqual((code, f["outcome"]), (1, "conflict: nothing complete"))
        self.assertTrue(Path(st).is_dir())

    def test_foreign_change_before_the_checks_is_a_conflict_and_nothing_runs(self):
        st = self.begin()
        self.write(st, NEW)
        self.index.write_text(NEW + "<!-- foreign -->\n")
        code, d = self.check(st)
        self.assertEqual((code, d["state"]), (1, "conflict"))
        self.assertEqual(self.npm_calls(), [])

    def test_removal_or_symlink_before_finish_is_handled_without_traceback(self):
        victim = self.tmpdir / "victim.txt"
        victim.write_text("precious")
        for how in ("remove", "symlink"):
            with self.subTest(how):
                st = self.checked()
                self.index.unlink()
                if how == "symlink":
                    os.symlink(victim, self.index)
                code, f = self.finish(st, visual=True)
                self.assertEqual((code, f["outcome"]), (1, "conflict: nothing complete"), f)
                self.assertTrue(Path(st).is_dir())
                self.assertEqual(victim.read_text(), "precious")
                self.assertEqual(self.edit("diff", "--state", st)[1]["state"], "conflict")
                self.index.unlink(missing_ok=True)
                self.index.write_text(GOOD)

    def test_regular_end_with_unchanged_repeat_and_repair_still_succeeds(self):
        st = self.begin()
        self.write(st, NEW + "<!-- BAD_CHECK -->\n")
        self.assertEqual(self.check(st)[1]["state"], "failed")
        self.assertEqual(self.write(st, NEW)[1]["repair_rounds"], 1)
        self.assertEqual(self.write(st, NEW)[1]["state"], "unchanged")
        self.assertEqual(self.check(st)[1]["state"], "checked")
        code, f = self.finish(st, visual=True)
        self.assertEqual((code, f["outcome"], f["backup"]), (0, "complete", "removed (own folder only)"))

    def test_helper_never_calls_install_or_ci(self):
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        self.assertFalse([c for c in self.npm_calls() if "install" in c or c.startswith("ci")])
        self.assertEqual(self.npm_calls(), ["run build", "run check"])


class JudgementIsNotEvidencedHere(EditCase):
    def test_only_the_helper_level_guarantee_for_judgement_cases_is_tested(self):
        """Fit, missing facts, supplied instructions, optimize routing, demonstration placeholders and every real visual inspection
        need a model or a host. Here exists only the helper-level guarantee that preflight alone writes nothing."""
        before = self.snap()
        self.preflight()
        self.assertEqual(delta(before, self.snap()), set())


if __name__ == "__main__":
    import unittest
    unittest.main()
