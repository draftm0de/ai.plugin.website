"""Audit result states, the read-only guard, the separation of finding classes, manual check points, `show` and damaged work lists.

Fictional repositories, fake npm. Complements the ported suites `test_audit.py` and `test_store.py`.
"""
import hashlib
import json
import os

from tests.support import optimize_helpers as h
from site_common.errors import Stop
import worklist as wl


def raw_tree(root):
    """Every byte outside .git (incl. build output): used to prove that a command wrote nothing."""
    out = {}
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            path = os.path.join(current, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, root)] = hashlib.sha256(handle.read()).hexdigest()
    return out


class ReadOnlyGuard(h.AuditCase):
    def test_a_new_untracked_file_created_by_the_build_is_a_violation_and_is_not_removed(self):
        (self.site / "src" / "CREATE").write_text("")                    # makes the fake build create src/created-by-build.txt (untracked)
        r = self.audit()
        self.assertEqual(r["status"], "readonly-violated", r)
        self.assertTrue(any("created-by-build.txt" in c for c in r["readonly_violations"]), r["readonly_violations"])
        self.assertTrue((self.site / "src" / "created-by-build.txt").exists(), "not silently reverted")
        self.assertEqual(r["exit_code"], 1)

    def test_a_modified_tracked_file_is_a_violation_and_closes_no_finding(self):
        self.audit()
        (self.site / "src" / "MUTATE").write_text("")
        r = self.audit(minutes=1)
        self.assertEqual(r["status"], "readonly-violated")
        self.assertIn("sites/fx.test/src/touched.txt", r["readonly_violations"])
        self.assertEqual({wl.section_of(f) for f in self.state()["findings"]}, {"open"})
        self.assertEqual(self.state()["last_run"]["status"], "readonly-violated")
        for fam in self.state()["last_run"]["families"].values():
            self.assertFalse(fam["complete"])

    def test_expected_ignored_build_output_is_no_violation(self):
        r = self.audit()
        self.assertTrue((self.site / "dist" / "content.json").is_file())
        self.assertEqual(r["readonly_violations"], [])
        self.assertEqual(r["status"], "clean-with-warnings")

    def test_expected_report_writes_are_no_violation(self):
        r = self.audit()
        r2 = self.audit(minutes=1)
        self.assertEqual((r["readonly_violations"], r2["readonly_violations"]), ([], []))

    def test_changes_that_existed_before_the_run_are_audited_as_they_were_and_survive(self):
        (self.site / "src" / "touched.txt").write_text("uncommitted edit of someone else\n")
        (self.site / "foreign.txt").write_text("untracked file of someone else\n")
        before = {p: (self.site / p).read_bytes() for p in ("src/touched.txt", "foreign.txt")}
        r = self.audit()
        self.assertEqual(r["status"], "clean-with-warnings", r)
        self.assertEqual({p: (self.site / p).read_bytes() for p in before}, before)
        self.assertIn("audited as they were", (self.root / r["report"]).read_text())

    def test_no_git_repository_still_builds_and_checks(self):
        import shutil
        shutil.rmtree(self.root / ".git")
        self.assertEqual(self.audit()["status"], "clean-with-warnings")
        self.assertEqual(len(self.npm_calls()), 3)


class ResultStates(h.AuditCase):
    def test_clean_run_has_no_findings_and_still_lists_the_manual_points(self):
        self.set_content([{"url": "/", "description": h.LONG}], commit=True)
        r = self.audit()
        self.assertEqual((r["status"], r["exit_code"]), ("clean", 0))
        text = (self.root / r["report"]).read_text()
        self.assertIn("No findings in this run", text)
        self.assertIn("Manual check points that no script marks as passed", text)

    def test_an_incomplete_run_is_never_called_clean_in_report_or_worklist(self):
        (self.site / "src" / "BREAK").write_text("")
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        report = (self.root / r["report"]).read_text()
        self.assertIn("| Result | `incomplete` |", report)
        self.assertNotIn("`clean`", report)
        self.assertNotIn("complete, ", report.replace("INCOMPLETE", ""))
        worklist = (self.root / r["worklist"]).read_text()
        self.assertIn("result `incomplete`", worklist)
        self.assertIn("INCOMPLETE", worklist)

    def test_checks_that_did_not_run_are_reported_as_not_run_with_a_dash_for_the_exit_code(self):
        (self.site / "src" / "BREAK").write_text("")
        report = (self.root / self.audit()["report"]).read_text()
        self.assertIn("| seo | `npm run seo:check` (not run) | - |", report)
        self.assertIn("| a11y | `npm run a11y:check` (not run) | - |", report)

    def test_unreadable_tool_output_of_one_family_does_not_hide_the_other(self):
        (self.site / "src" / "GARBLE_SEO").write_text("")
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        self.assertFalse(r["checks"]["seo"]["complete"])
        self.assertTrue(r["checks"]["a11y"]["complete"])

    def test_a_check_that_cannot_start_is_incomplete(self):
        (self.site / "fx" / "seo-check.sh").unlink()
        h.sh(self.root, "git", "commit", "-qam", "removed")
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["checks"]["seo"]["exit"], 127)                                 # the shell's "not found": not a defined check result
        self.assertFalse(r["checks"]["seo"]["complete"])
        self.assertTrue(r["checks"]["a11y"]["complete"])

    def test_the_real_exit_code_wins_over_the_words_of_the_output(self):
        # output claims "No errors." but the process exits 1: unreadable/inconsistent, not clean
        (self.site / "fx" / "a11y-check.sh").write_text('echo "Checked 1 pages for accessibility."; echo; echo "No errors."; exit 1\n')
        h.sh(self.root, "git", "commit", "-qam", "contradiction")
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["checks"]["a11y"]["exit"], 1)
        self.assertIn("output not evaluable", r["checks"]["a11y"]["reason"])

    def test_missing_node_modules_lockfile_and_package_json_are_listed_one_by_one_and_nothing_runs(self):
        os.rmdir(self.site / "node_modules")
        (self.site / "package-lock.json").unlink()
        r = self.audit()
        self.assertEqual(r["status"], "incomplete")
        reasons = r["checks"]["seo"]["reason"]
        self.assertIn("node_modules", reasons)
        self.assertIn("package-lock.json", reasons)
        self.assertEqual(self.npm_calls(), [])


class FindingClasses(h.AuditCase):
    def item(self):
        return {"criterion": "editorial.home-lead", "location": "/", "title": "Home lead could name the audience",
                "evidence": "reviewer reading of the page", "proposal": {"summary": "Name the audience", "kind": "opinion"}}

    def test_error_warning_and_editorial_are_three_separate_classes(self):
        self.set_content([{"url": "/", "description": ""}, {"url": "/a.html", "description": h.SHORT_A}], commit=True)
        self.audit(editorial=[self.item()])
        classes = {f["id"]: f["class"] for f in self.state()["findings"]}
        self.assertEqual(sorted(classes.values()), ["editorial-suggestion", "technical-error", "warning"])
        text = (self.root / ".project/reports/fx.test/optimize.md").read_text()
        self.assertIn("(technical error)", text)
        self.assertIn("(warning)", text)
        self.assertIn("(editorial suggestion)", text)

    def test_editorial_findings_are_never_closed_by_the_absence_of_a_check_and_carry_a_non_machine_method(self):
        self.audit(editorial=[self.item()])
        for i in (1, 2):
            self.audit(minutes=i)
        f = self.finding("ED-001")
        self.assertEqual(wl.section_of(f), "open")
        self.assertIn("not a machine check", f["method"])
        self.assertIn("not a machine check", f["limits"])

    def test_manual_check_points_are_listed_in_every_report_and_never_marked_passed(self):
        for mode in ("clean", "errors", "incomplete"):
            if mode == "clean":
                self.set_content([{"url": "/", "description": h.LONG}], commit=True)
            elif mode == "errors":
                self.set_content([{"url": "/", "description": ""}], commit=True)
            else:
                (self.site / "src" / "BREAK").write_text("")
            report = (self.root / self.audit(minutes=ord(mode[0])).get("report")).read_text()
            tail = report.split("## Limits of this run")[1]
            for point in ("colour contrast", "keyboard path", "screen-reader reading", "truthfulness of every claim", "legal pages"):
                self.assertIn(point, tail, (mode, point))
            self.assertIn("No Lighthouse", tail)
            lowered = tail.lower()
            self.assertNotIn("manual checks passed", lowered)
            self.assertNotRegex(lowered, r"(contrast|keyboard|screen-reader)[^\n]*\b(passed|ok|bestanden)\b")

    def test_proposals_state_their_limits_and_promise_no_ranking(self):
        self.audit()
        for f in self.state()["findings"]:
            self.assertNotRegex(json.dumps(f).lower(), r"rank(s|ing)? (higher|better)|more traffic|guarantee")
            self.assertTrue(f["limits"])


class ShowIsReadOnly(h.AuditCase):
    def test_show_lists_all_sections_and_writes_nothing(self):
        self.audit()
        self.decide(["SEO-001"], "deferred")
        before = raw_tree(self.root)
        code, out = self.cli("show")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([f["id"] for f in data["open"]], ["SEO-002"])
        self.assertEqual([f["id"] for f in data["parked"]], ["SEO-001"])
        self.assertEqual(data["history"], [])
        self.assertEqual(raw_tree(self.root), before)

    def test_show_without_a_worklist_says_so_and_writes_nothing(self):
        before = raw_tree(self.root)
        code, out = self.cli("show")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["worklist"], None)
        self.assertEqual(raw_tree(self.root), before)
        self.assertFalse((self.root / ".project" / "reports").exists())


class DamagedWorklistStopsEveryCommandBeforeBuilding(h.AuditCase):
    def path(self):
        return self.root / ".project" / "reports" / "fx.test" / "optimize.md"

    def damage(self, how):
        self.audit()
        text = self.path().read_text()
        if how == "hand-edit":
            self.path().write_text(text.replace("- proposed", "- approved", 1))
        elif how == "binary":
            self.path().write_bytes(b"\xff\xfe\x00 not text")
        elif how == "empty":
            self.path().write_text("")
        elif how == "directory":
            self.path().unlink()
            self.path().mkdir()
        return self.path().read_bytes() if self.path().is_file() else None

    def test_every_command_stops_and_leaves_the_file_and_the_site_alone(self):
        for how in ("hand-edit", "binary", "empty", "directory"):
            with self.subTest(how=how):
                self.setUp()
                kept = self.damage(how)
                calls = len(self.npm_calls())
                reports = self.reports()
                site_before = self.tracked_hashes()
                for args in (("audit", "--npm", str(self.npm)), ("show",), ("decide", "SEO-001", "--status", "approved"),
                             ("apply", "SEO-001", "--npm", str(self.npm))):
                    code, out = self.cli(*args)
                    self.assertEqual(code, 1, (how, args, out))
                    self.assertTrue(out.startswith("STOP:"), (how, args, out))
                    self.assertNotIn("Traceback", out, (how, args))
                self.assertEqual(len(self.npm_calls()), calls, f"{how}: a build ran although the work list is damaged")
                self.assertEqual(self.reports(), reports, how)
                self.assertEqual(self.tracked_hashes(), site_before, how)
                if kept is not None:
                    self.assertEqual(self.path().read_bytes(), kept, how)
                self.assertFalse((self.path().parent / ".optimize.lock").exists(), how)

    def test_the_work_list_of_a_different_site_and_a_future_format_version_are_refused(self):
        self.audit()
        state = self.state()
        state["version"] = 2
        self.path().write_text(wl.render(state))
        code, out = self.cli("audit", "--npm", str(self.npm))
        self.assertEqual(code, 1)
        self.assertIn("unsupported version", out)

    def test_the_work_list_format_markers_are_the_unchanged_project_data_format(self):
        self.audit()
        text = self.path().read_text()
        for marker in ("<!-- website-manager-optimize:worklist v1", "<!-- website-manager-optimize:state sha256=", "<!-- /website-manager-optimize:state -->"):
            self.assertIn(marker, text)
        self.assertEqual(self.state()["format"], "website-manager-optimize-worklist")
        self.assertIn("<!-- website-manager-optimize:report v1 site=fx.test -->", (self.root / ".project/reports/fx.test/optimize" / self.reports()[0]).read_text())
