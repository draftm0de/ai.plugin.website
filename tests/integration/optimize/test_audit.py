"""Audit, decisions, bounded apply and recheck, on fictional throw-away repositories with a fake npm (no install, no network).

Ported from the source suite; assertions kept, fixtures fictional. Behaviour evidence only for the fake-driven pipeline."""
import json
import os
import subprocess
import unittest
from unittest import mock

from tests.support import optimize_helpers as h
import audit
import store
import worklist as wl
from site_common.errors import Stop

GOOD_B = "Metrics for service B: exposes runtime state so monitoring systems can collect it and dashboards can chart it over time."


class FirstAndRepeatedAudit(h.AuditCase):
    def test_first_audit_creates_report_and_worklist_without_touching_the_site(self):
        before = self.tracked_hashes()
        r = self.audit()
        self.assertEqual((r["status"], r["exit_code"]), ("clean-with-warnings", 0))
        self.assertEqual(self.reports(), ["20261117-144400.md"])
        self.assertEqual([f["id"] for f in self.state()["findings"]], ["SEO-001", "SEO-002"])
        self.assertEqual(self.tracked_hashes(), before)
        status = h.sh(self.root, "git", "status", "--porcelain")
        self.assertEqual([l for l in status.splitlines() if ".project/reports" not in l], [])
        self.assertNotIn("package-lock", status)
        self.assertEqual(self.npm_calls(), ["run build", "run seo:check", "run a11y:check"])
        for f in self.state()["findings"]:
            self.assertEqual(f["status"], "proposed")
            self.assertEqual(f["class"], "warning")

    def test_report_documents_time_mode_source_exit_codes_limits(self):
        r = self.audit()
        text = (self.root / r["report"]).read_text()
        for needle in ["+0100", "UTC 2026-11-17T13:44:00Z", "`audit`", "source-files digest `", "| seo | `npm run seo:check` | 0 |", "| a11y |",
                       "Read-only guard | passed", "Manual check points", "No Lighthouse", "SEO-001"]:
            self.assertIn(needle, text)

    def test_identical_second_audit_gives_new_report_same_ids_no_duplicates(self):
        self.audit()
        self.decide(["SEO-001"], "approved")
        self.audit(minutes=1)
        self.assertEqual(self.reports(), ["20261117-144400.md", "20261117-144500.md"])
        s = self.state()
        self.assertEqual([f["id"] for f in s["findings"]], ["SEO-001", "SEO-002"])
        self.assertEqual(len(self.finding("SEO-001")["reports"]), 2)
        self.assertEqual(s["last_run"]["changes"]["unchanged"], ["SEO-001", "SEO-002"])
        self.assertEqual(self.finding("SEO-001")["first_found"]["report"], "optimize/20261117-144400.md")
        self.assertEqual(self.finding("SEO-001")["last_checked"]["report"], "optimize/20261117-144500.md")

    def test_decisions_survive_further_runs(self):
        self.audit()
        self.decide(["SEO-001"], "approved", reason="ok")
        self.decide(["SEO-002"], "wont-do", reason="intentional")
        for i in (1, 2):
            self.audit(minutes=i, proposals={"SEO-002": {"summary": "new idea", "proposed": "x"}})
        a, b = self.finding("SEO-001"), self.finding("SEO-002")
        self.assertEqual((a["status"], b["status"]), ("approved", "wont-do"))
        self.assertEqual(b["proposal"]["summary"], "Rewrite the description as one concrete sentence of 120-160 characters from facts already on the page; do not add keywords.")
        self.assertEqual(a["decision_log"][-1]["reason"], "ok")
        sections = wl.render(self.state())
        self.assertIn("## Deferred and rejected", sections)

    def test_deferred_is_kept_and_wont_do_is_not_reproposed(self):
        self.audit()
        self.decide(["SEO-001"], "deferred")
        self.decide(["SEO-002"], "wont-do")
        self.audit(minutes=1)
        s = {f["id"]: f for f in self.state()["findings"]}
        self.assertEqual((s["SEO-001"]["status"], s["SEO-002"]["status"]), ("deferred", "wont-do"))
        self.assertEqual({wl.section_of(f) for f in s.values()}, {"parked"})


class DecisionRules(h.AuditCase):
    def setUp(self):
        super().setUp()
        self.audit()

    def test_same_decision_is_idempotent_and_changes_need_explicit_flag(self):
        self.decide(["SEO-001"], "approved")
        self.assertIn("already approved", self.decide(["SEO-001"], "approved")["messages"][0])
        with self.assertRaises(Stop) as ctx:
            self.decide(["SEO-001"], "deferred")
        self.assertIn("--change", str(ctx.exception))
        self.assertEqual(self.finding("SEO-001")["status"], "approved")
        self.decide(["SEO-001"], "deferred", change=True, reason="later")
        self.assertEqual(self.finding("SEO-001")["status"], "deferred")
        self.assertEqual([e["status"] for e in self.finding("SEO-001")["decision_log"]], ["proposed", "approved", "deferred"])

    def test_unknown_id_and_unknown_status(self):
        with self.assertRaises(Stop):
            self.decide(["SEO-999"], "approved")
        with self.assertRaises(Stop):
            self.decide(["SEO-001"], "implemented")
        with self.assertRaises(Stop):
            self.decide(["SEO-001"], "verified")
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")

    def test_failed_batch_changes_nothing(self):
        with self.assertRaises(Stop):
            self.decide(["SEO-001", "SEO-999"], "approved")
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")


class ApplyAndRecheck(h.AuditCase):
    def setUp(self):
        super().setUp()
        self.audit(proposals={"seo.description-too-short|/a.html|": self.proposal_for(h.GOOD_A)})

    def test_apply_refuses_unapproved_and_changes_nothing(self):
        before = self.tracked_hashes()
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=1)
        self.assertIn("not approved", str(ctx.exception))
        self.assertEqual(self.tracked_hashes(), before)

    def test_concurrent_wont_do_before_apply_blocks_the_source_change(self):
        self.decide(["SEO-001"], "approved")
        before = self.tracked_hashes()

        def rival():
            self.decide(["SEO-001"], "wont-do", minutes=1, change=True)

        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=2, hooks={"before_apply": rival})
        self.assertIn("not approved", str(ctx.exception))
        self.assertEqual(self.tracked_hashes(), before)                       # no source change from the stale approval
        self.assertEqual(self.finding("SEO-001")["status"], "wont-do")        # the rival decision survived
        self.assertEqual(self.npm_calls().count("run build"), 1)              # only the first audit built

    def test_decision_during_the_recheck_is_not_overwritten(self):
        self.decide(["SEO-001"], "approved")
        rival = lambda: self.decide(["SEO-001"], "wont-do", minutes=1, change=True)
        r = self.apply(["SEO-001"], minutes=2, hooks={"before_commit": rival})
        f = self.finding("SEO-001")
        self.assertEqual(f["status"], "wont-do")
        self.assertIsNone(f["applied"])

    def test_apply_is_limited_to_the_approved_proposal_and_recheck_closes_it(self):
        self.decide(["SEO-001"], "approved")
        before = self.tracked_hashes()
        r = self.apply(["SEO-001"], minutes=1)
        changed = {k for k in self.tracked_hashes() if self.tracked_hashes()[k] != before[k]}
        self.assertEqual(changed, {"sites/fx.test/src/content.json"})
        data = json.loads((self.site / "src" / "content.json").read_text())
        self.assertEqual([p["description"] for p in data], [h.LONG, h.GOOD_A, h.SHORT_B])    # SEO-002 page untouched
        self.assertEqual((r["status"], r["exit_code"]), ("clean-with-warnings", 0))
        self.assertEqual(r["changes"]["resolved"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertEqual(wl.section_of(f), "history")
        self.assertEqual(f["status"], "approved")                                              # decision kept
        self.assertEqual(f["resolution"]["via"], "apply")
        self.assertIn("exit 0", f["resolution"]["evidence"])
        self.assertEqual(f["resolution"]["changed_files"], ["sites/fx.test/src/content.json"])
        self.assertEqual(wl.section_of(self.finding("SEO-002")), "open")
        report = (self.root / r["report"]).read_text()
        self.assertIn("## Applied changes", report)
        self.assertIn("Short one.", report)
        text = (self.root / ".project/reports/fx.test/optimize.md").read_text()
        open_part = text.split("## Done")[0]
        self.assertNotIn("### SEO-001", open_part)
        self.assertIn("### SEO-001", text.split("## Done")[1])

    def test_apply_does_not_run_on_other_ids_or_without_a_mechanical_edit(self):
        self.decide(["SEO-001", "SEO-002"], "approved")
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-002"], minutes=1)           # approved, but its proposal has no edit
        self.assertIn("no mechanical edit", str(ctx.exception))
        self.assertEqual(json.loads((self.site / "src" / "content.json").read_text())[2]["description"], h.SHORT_B)

    def test_changed_proposal_voids_approval_and_apply_refuses(self):
        self.decide(["SEO-001"], "approved")
        r = self.audit(minutes=1, proposals={"SEO-001": self.proposal_for("Another draft text that is clearly different from the one that was approved earlier, "
                                                                           "and that therefore needs a fresh decision from the owner.")})
        self.assertEqual(r["changes"]["approval_void"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertEqual(f["status"], "proposed")
        self.assertIn("approval void", f["attention"])
        with self.assertRaises(Stop):
            self.apply(["SEO-001"], minutes=2)

    def test_changed_starting_point_voids_approval(self):
        self.decide(["SEO-001"], "approved")
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": "Shorter."}, {"url": "/b.html", "description": h.SHORT_B}], commit=True)
        r = self.audit(minutes=1)
        self.assertEqual(r["changes"]["approval_void"], ["SEO-001"])
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")

    def test_failed_edit_target_changes_nothing(self):
        self.decide(["SEO-001"], "approved")
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": h.SHORT_A + "x"}], commit=True)
        before = self.tracked_hashes()
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=1)
        self.assertIn("occurs 0 times", str(ctx.exception))
        self.assertEqual(self.tracked_hashes(), before)

    def test_edit_outside_site_or_through_symlink_is_refused(self):
        bad = self.proposal_for(h.GOOD_A)
        bad["edit"]["file"] = ".project/specs/zyris-website.json"
        self.audit(minutes=1, proposals={"SEO-001": bad})
        self.decide(["SEO-001"], "approved")
        before = self.tracked_hashes()
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=2)
        self.assertIn("outside the site folder", str(ctx.exception))
        self.assertEqual(self.tracked_hashes(), before)

    def test_recheck_with_build_failure_closes_nothing_and_keeps_approval(self):
        self.decide(["SEO-001"], "approved")
        (self.site / "src" / "BREAK").write_text("")
        r = self.apply(["SEO-001"], minutes=1)
        self.assertEqual((r["status"], r["exit_code"], r["build_exit"]), ("incomplete", 1, 3))
        f = self.finding("SEO-001")
        self.assertIsNone(f["resolution"])
        self.assertEqual(f["status"], "approved")
        self.assertIn("recheck of seo incomplete", f["attention"])
        self.assertEqual(r["changes"]["recheck_incomplete"], ["SEO-001"])
        # the old dist/ (built before the edit) would not report the finding any more, but must not count
        (self.site / "src" / "BREAK").unlink()
        r2 = self.audit(minutes=2)
        self.assertEqual(r2["changes"]["resolved"], ["SEO-001"])
        self.assertEqual(self.finding("SEO-001")["resolution"]["via"], "apply")      # applied earlier, evidenced now

    def test_recheck_that_still_reports_the_problem_stays_open(self):
        self.audit(minutes=1, proposals={"SEO-001": self.proposal_for("Still short.")})    # proposed: replaced silently
        self.decide(["SEO-001"], "approved", minutes=2)
        r = self.apply(["SEO-001"], minutes=3)
        self.assertEqual(r["changes"]["recheck_failed"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertIsNone(f["resolution"])
        self.assertEqual(f["status"], "approved")
        self.assertIn("still reports it", f["attention"])
        self.assertEqual(wl.section_of(f), "open")

    def test_manual_applied_flag_requires_approved_open_finding(self):
        with self.assertRaises(Stop):
            self.audit(minutes=1, applied=("SEO-001",))
        self.decide(["SEO-001"], "approved")
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": h.GOOD_A}, {"url": "/b.html", "description": h.SHORT_B}])
        r = self.audit(minutes=2, applied=("SEO-001",))
        self.assertEqual(r["changes"]["resolved"], ["SEO-001"])
        self.assertEqual(self.finding("SEO-001")["resolution"]["via"], "apply")


class ExternalFixAndReappearance(h.AuditCase):
    def test_fix_outside_optimize_is_taken_over_only_with_complete_evidence(self):
        self.audit()
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": h.GOOD_A}, {"url": "/b.html", "description": h.SHORT_B}], commit=True)
        (self.site / "src" / "BREAK").write_text("")
        r = self.audit(minutes=1)
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(wl.section_of(self.finding("SEO-001")), "open")          # absence in an incomplete run is no evidence
        self.assertEqual(r["changes"].get("kept"), ["SEO-001", "SEO-002"])
        (self.site / "src" / "BREAK").unlink()
        r = self.audit(minutes=2)
        self.assertEqual(r["changes"]["resolved"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertEqual(f["resolution"]["via"], "external")
        self.assertEqual(f["status"], "proposed")

    def test_reappearance_is_shown_and_returned_for_a_new_decision(self):
        self.audit()
        self.decide(["SEO-001"], "approved")
        good = [{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": h.GOOD_A}, {"url": "/b.html", "description": h.SHORT_B}]
        self.set_content(good, commit=True)
        self.audit(minutes=1)
        self.assertEqual(wl.section_of(self.finding("SEO-001")), "history")
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": "Short again."}, {"url": "/b.html", "description": h.SHORT_B}], commit=True)
        r = self.audit(minutes=2)
        self.assertEqual(r["changes"]["reappeared"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertEqual(f["id"], "SEO-001")
        self.assertEqual((f["status"], f["reappeared"], len(f["resolved_before"])), ("proposed", 1, 1))
        self.assertEqual(wl.section_of(f), "open")
        self.assertIn("reappeared", f["attention"])
        self.assertEqual(len(self.state()["findings"]), 2)
        self.assertTrue(any(e["status"] == "approved" for e in f["decision_log"]))     # earlier decision preserved in the log

    def test_parked_finding_that_disappears_keeps_its_decision(self):
        self.audit()
        self.decide(["SEO-001"], "wont-do", reason="no")
        self.set_content([{"url": "/", "description": h.LONG}, {"url": "/a.html", "description": h.GOOD_A}, {"url": "/b.html", "description": h.SHORT_B}], commit=True)
        r = self.audit(minutes=1)
        self.assertEqual(r["changes"]["not_observed"], ["SEO-001"])
        f = self.finding("SEO-001")
        self.assertEqual((f["status"], f["not_observed"], wl.section_of(f)), ("wont-do", True, "parked"))


class ErrorsAndIncompleteRuns(h.AuditCase):
    def test_seo_error_does_not_suppress_accessibility_run(self):
        self.set_content([{"url": "/", "description": ""}, {"url": "/b.html", "description": h.LONG, "alt_missing": True}], commit=True)
        r = self.audit()
        self.assertEqual((r["status"], r["exit_code"]), ("errors", 1))
        self.assertEqual((r["checks"]["seo"]["exit"], r["checks"]["a11y"]["exit"]), (1, 1))
        ids = {f["id"]: f for f in self.state()["findings"]}
        self.assertEqual(sorted(ids), ["A11Y-001", "SEO-001"])
        self.assertEqual(ids["SEO-001"]["class"], "technical-error")
        self.assertEqual(ids["SEO-001"]["priority"]["level"], "high")
        self.assertEqual(self.npm_calls(), ["run build", "run seo:check", "run a11y:check"])

    def test_build_failure_propagates_exit_code_and_skips_checks(self):
        self.audit()
        (self.site / "src" / "BREAK").write_text("")
        r = self.audit(minutes=1)
        self.assertEqual((r["status"], r["exit_code"], r["build_exit"]), ("incomplete", 1, 3))
        self.assertEqual(self.npm_calls()[3:], ["run build"])                      # checks never ran on the stale dist/
        report = (self.root / r["report"]).read_text()
        self.assertIn("| build | `npm run build` | 3 | FAILED |", report)
        self.assertIn("stale dist/", report)
        self.assertIn("build exploded", report)
        self.assertNotIn("`clean`", report)
        self.assertEqual({wl.section_of(f) for f in self.state()["findings"]}, {"open"})   # nothing closed

    def test_missing_dependencies_are_reported_not_installed(self):
        os.rmdir(self.site / "node_modules")
        r = self.audit()
        self.assertEqual((r["status"], r["exit_code"]), ("incomplete", 1))
        self.assertEqual(self.npm_calls(), [])
        report = (self.root / r["report"]).read_text()
        self.assertIn("never installs", report)
        self.assertIn("npm ci", report)

    def test_missing_lockfile_and_unignored_outputs_are_incomplete(self):
        (self.site / "package-lock.json").unlink()
        self.assertEqual(self.audit()["status"], "incomplete")
        (self.site / "package-lock.json").write_text("{}\n")
        (self.site / ".gitignore").write_text("")
        r = self.audit(minutes=1)
        self.assertEqual(r["status"], "incomplete")
        self.assertIn("not git-ignored", (self.root / r["report"]).read_text())
        self.assertEqual(self.npm_calls(), [])

    def test_missing_check_script_is_incomplete_not_clean(self):
        (self.site / "package.json").write_text(json.dumps({"scripts": {"build": "x", "seo:check": "x"}}))
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        self.assertFalse(r["checks"]["a11y"]["complete"])
        self.assertTrue(r["checks"]["seo"]["complete"])
        self.assertIn("no 'a11y:check' script", r["checks"]["a11y"]["reason"])

    def test_unparsable_output_is_incomplete_not_clean(self):
        (self.site / "src" / "GARBLE_SEO").write_text("")
        r = self.audit()
        self.assertEqual((r["status"], r["checks"]["seo"]["exit"]), ("incomplete", 0))
        self.assertIn("output not evaluable", r["checks"]["seo"]["reason"])
        self.assertEqual(self.state()["findings"], [])

    def test_missing_npm_is_incomplete(self):
        import audit as a
        with mock.patch("shutil.which", return_value=None):
            r = a.do_audit(self.root, h.COMPONENT, now=self.now())
        self.assertEqual(r["status"], "incomplete")
        self.assertIn("npm not found", (self.root / r["report"]).read_text())

    def test_readonly_violation_is_detected_listed_and_not_reverted(self):
        (self.site / "src" / "MUTATE").write_text("")
        self.audit()
        r = self.audit(minutes=1)
        self.assertEqual((r["status"], r["exit_code"]), ("readonly-violated", 1))
        self.assertIn("sites/fx.test/src/touched.txt", r["readonly_violations"])
        self.assertTrue((self.site / "src" / "touched.txt").read_text())            # not silently reverted
        report = (self.root / r["report"]).read_text()
        self.assertIn("VIOLATED", report)
        self.assertTrue(all(wl.section_of(f) == "open" for f in self.state()["findings"]))

    def test_secrets_in_output_are_redacted(self):
        (self.site / "src" / "LEAK").write_text("")
        r = self.audit()
        text = (self.root / r["report"]).read_text()
        self.assertNotIn("abc123secret", text)
        self.assertIn("TOKEN=<redacted>", text)

    def test_audit_never_runs_install_or_ci(self):
        self.audit()
        self.audit(minutes=1)
        self.assertTrue(all(c.startswith("run ") for c in self.npm_calls()))


class Editorial(h.AuditCase):
    def item(self):
        return {"criterion": "editorial.home-lead", "location": "/", "title": "Home lead could name the audience",
                "evidence": "reviewer reading of the page", "proposal": {"summary": "Name the audience in the first sentence", "kind": "opinion",
                "verify": {"file": "sites/fx.test/src/content.json", "present": "for operators"}}}

    def test_editorial_is_separate_not_closed_by_absence_and_verifiable_by_source_text(self):
        self.audit(editorial=[self.item()])
        f = self.finding("ED-001")
        self.assertEqual(f["class"], "editorial-suggestion")
        r = self.audit(minutes=1)                                      # not supplied again: stays open
        self.assertEqual(wl.section_of(self.finding("ED-001")), "open")
        self.set_content([{"url": "/", "description": h.LONG + " for operators"}, {"url": "/a.html", "description": h.SHORT_A}, {"url": "/b.html", "description": h.SHORT_B}])
        r = self.audit(minutes=2)
        self.assertIn("ED-001", r["changes"]["resolved"])
        self.assertIn("not any effect on rankings", self.finding("ED-001")["resolution"]["evidence"])


    def _approved_editorial_with_source_fix(self):
        self.audit(editorial=[self.item()])
        self.decide(["ED-001"], "approved")
        self.set_content([{"url": "/", "description": h.LONG + " for operators"}, {"url": "/a.html", "description": h.SHORT_A}, {"url": "/b.html", "description": h.SHORT_B}])

    def _assert_stays_open_and_approved(self, r, reason_part):
        f = self.finding("ED-001")
        self.assertEqual((wl.section_of(f), f["status"], f["resolution"]), ("open", "approved", None))
        self.assertNotIn("ED-001", r["changes"].get("resolved", []))
        return f

    def test_editorial_stays_open_when_build_fails_then_closes_on_a_valid_recheck(self):
        self._approved_editorial_with_source_fix()
        (self.site / "src" / "BREAK").write_text("")
        r = self.audit(minutes=1, applied=("ED-001",))
        self.assertEqual(r["status"], "incomplete")
        f = self._assert_stays_open_and_approved(r, "build")
        self.assertIn("ED-001", r["changes"]["recheck_incomplete"])
        self.assertIn("fix the build", f["attention"])
        (self.site / "src" / "BREAK").unlink()
        r = self.audit(minutes=2)
        self.assertIn("ED-001", r["changes"]["resolved"])
        self.assertEqual(self.finding("ED-001")["resolution"]["via"], "apply")

    def test_editorial_stays_open_when_prerequisites_are_missing(self):
        self._approved_editorial_with_source_fix()
        os.rmdir(self.site / "node_modules")
        r = self.audit(minutes=1)
        self.assertEqual(r["status"], "incomplete")
        self._assert_stays_open_and_approved(r, "prerequisites")
        self.assertIn("ED-001", r["changes"]["kept"])

    def test_editorial_stays_open_when_the_read_only_guard_is_violated(self):
        self._approved_editorial_with_source_fix()
        (self.site / "src" / "MUTATE").write_text("")
        r = self.audit(minutes=1, applied=("ED-001",))
        self.assertEqual(r["status"], "readonly-violated")
        f = self._assert_stays_open_and_approved(r, "guard")
        self.assertIn("readonly-violated", f["attention"])
        (self.site / "src" / "MUTATE").unlink()
        (self.site / "src" / "touched.txt").unlink(missing_ok=True)
        r = self.audit(minutes=2)
        self.assertIn("ED-001", r["changes"]["resolved"])


class CliTests(h.AuditCase):
    def run_cli(self, *args):
        code, out = self.cli(*args)
        return code, out

    def test_audit_decide_show_via_cli(self):
        code, out = self.run_cli("audit", "--npm", str(self.npm))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["counts"], {"open": 2, "parked": 0, "history": 1 - 1})
        code, out = self.run_cli("decide", "SEO-001", "--status", "approved", "--reason", "go")
        self.assertEqual(code, 0, out)
        code, out = self.run_cli("decide", "SEO-001", "--status", "wont-do")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP:"))
        code, out = self.run_cli("show")
        self.assertEqual(json.loads(out)["open"][0]["status"], "approved")
        code, out = self.run_cli("apply", "SEO-002", "--npm", str(self.npm))
        self.assertEqual(code, 1)

    def test_errors_exit_one(self):
        self.set_content([{"url": "/", "description": ""}], commit=True)
        code, out = self.run_cli("audit", "--npm", str(self.npm))
        self.assertEqual((code, json.loads(out)["status"]), (1, "errors"))


if __name__ == "__main__":
    unittest.main()


class Propose(h.AuditCase):
    def test_propose_stores_drafts_without_a_new_audit_and_voids_changed_approvals(self):
        self.audit()
        import audit as a
        r = a.do_propose(self.root, h.COMPONENT, {"SEO-001": self.proposal_for(h.GOOD_A)}, now=self.now(1))
        self.assertEqual(r["changes"]["proposal_changed"], ["SEO-001"])
        self.assertEqual(self.reports(), ["20261117-144400.md"])
        self.assertEqual(self.finding("SEO-001")["proposal"]["proposed"], h.GOOD_A)
        self.decide(["SEO-001"], "approved")
        r = a.do_propose(self.root, h.COMPONENT, {"seo.description-too-short|/a.html|": self.proposal_for("A different text.")}, now=self.now(2))
        self.assertEqual(r["changes"]["approval_void"], ["SEO-001"])
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")
        with self.assertRaises(Stop):
            a.do_propose(self.root, h.COMPONENT, {"SEO-404": {"summary": "x"}}, now=self.now(3))

    def test_propose_ignores_wont_do(self):
        self.audit()
        self.decide(["SEO-002"], "wont-do")
        import audit as a
        r = a.do_propose(self.root, h.COMPONENT, {"SEO-002": self.proposal_for(h.GOOD_A, h.SHORT_B)}, now=self.now(1))
        self.assertEqual(r["changes"], {"ignored": ["SEO-002"]})
        self.assertNotEqual(self.finding("SEO-002")["proposal"]["proposed"], h.GOOD_A)
