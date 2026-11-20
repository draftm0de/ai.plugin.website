"""`decide` and `apply`: what an approval releases and what is refused, and the protection of the files `apply` may touch.

All on fictional throw-away repositories with the fake npm of `tests/support/optimize_helpers.py`; nothing is installed.
Cases marked BD-n cover protection corrections to the source behaviour (docs/migration/changes.md, Etappe 4, section B).
"""
import os
from unittest import mock

from tests.support import optimize_helpers as h
from site_common.errors import Stop
import worklist as wl


def tree_state(case):
    """Content hash of every tracked file plus the raw git status without the report area."""
    status = [l for l in h.sh(case.root, "git", "status", "--porcelain", "--untracked-files=all").splitlines() if ".project/reports" not in l]
    return case.tracked_hashes(), status


class ApprovalBinding(h.AuditCase):
    def setUp(self):
        super().setUp()
        self.audit(proposals={"seo.description-too-short|/a.html|": self.proposal_for(h.GOOD_A)})

    def test_decide_changes_no_site_content_in_any_status(self):
        before = tree_state(self)
        for status in ("approved", "deferred", "wont-do", "proposed"):
            self.decide(["SEO-001"], status, change=True)
            self.assertEqual(tree_state(self), before, status)
        self.assertEqual(self.npm_calls(), ["run build", "run seo:check", "run a11y:check"])          # decide ran nothing

    def test_proposed_deferred_and_wont_do_are_never_applied(self):
        for status in ("proposed", "deferred", "wont-do"):
            if status != "proposed":
                self.decide(["SEO-001"], status, change=True)
            before = tree_state(self)
            with self.assertRaises(Stop) as ctx:
                self.apply(["SEO-001"], minutes=1)
            self.assertIn("not approved", str(ctx.exception), status)
            self.assertEqual(tree_state(self), before, status)
        self.assertEqual(self.npm_calls().count("run build"), 1)                                      # the refused applies built nothing

    def test_audit_alone_never_authorises_apply(self):
        for i in (1, 2):
            self.audit(minutes=i)
        self.assertEqual(self.finding("SEO-001")["status"], "proposed")
        self.assertEqual(json_descriptions(self.site)[1], h.SHORT_A)

    def test_approved_and_unchanged_applies_exactly_the_released_change(self):
        self.decide(["SEO-001"], "approved")
        before, _ = tree_state(self)
        self.apply(["SEO-001"], minutes=1)
        after, status = tree_state(self)
        self.assertEqual({k for k in after if after[k] != before[k]}, {"sites/fx.test/src/content.json"})
        self.assertEqual(status, [" M sites/fx.test/src/content.json"])
        self.assertEqual(json_descriptions(self.site), [h.LONG, h.GOOD_A, h.SHORT_B])

    def test_the_recheck_runs_the_full_audit_after_apply_and_nothing_is_installed(self):
        self.decide(["SEO-001"], "approved")
        self.apply(["SEO-001"], minutes=1)
        self.assertEqual(self.npm_calls(), ["run build", "run seo:check", "run a11y:check"] * 2)
        self.assertEqual(self.finding("SEO-001")["resolution"]["via"], "apply")

    def test_an_approval_of_one_finding_does_not_release_another(self):
        self.decide(["SEO-001"], "approved")
        with self.assertRaises(Stop):
            self.apply(["SEO-001", "SEO-002"], minutes=1)           # SEO-002 is not approved: the whole call is refused first
        self.assertEqual(json_descriptions(self.site), [h.LONG, h.SHORT_A, h.SHORT_B])

    def test_a_done_finding_cannot_be_applied_again(self):
        self.decide(["SEO-001"], "approved")
        self.apply(["SEO-001"], minutes=1)
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=2)
        self.assertIn("already done", str(ctx.exception))

    def test_unknown_id_is_refused(self):
        with self.assertRaises(Stop):
            self.apply(["SEO-404"], minutes=1)


def json_descriptions(site):
    import json
    return [p["description"] for p in json.loads((site / "src" / "content.json").read_text())]


class EditTarget(h.AuditCase):
    """The search text, the file and the path of the mechanical edit."""

    def propose_edit(self, file, find="Short one.", replace="A rewritten description that is clearly different from the former one."):
        proposal = {"summary": "edit", "kind": "draft", "proposed": replace, "edit": {"file": file, "find": find, "replace": replace}}
        self.audit(proposals={"seo.description-too-short|/a.html|": proposal})
        self.decide(["SEO-001"], "approved")

    def refused(self, needle, minutes=5):
        before = tree_state(self)
        calls = len(self.npm_calls())
        with self.assertRaises(Stop) as ctx:
            self.apply(["SEO-001"], minutes=minutes)
        self.assertIn(needle, str(ctx.exception))
        self.assertEqual(tree_state(self), before)
        self.assertEqual(len(self.npm_calls()), calls, "a refused apply must not build")
        self.assertEqual(self.finding("SEO-001")["status"], "approved")           # a refusal changes no decision
        return str(ctx.exception)

    def test_search_text_must_occur_exactly_once(self):
        (self.site / "src" / "two.json").write_text('"Short one." and again "Short one."\n')
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "two")
        self.propose_edit("sites/fx.test/src/two.json")
        self.assertIn("occurs 2 times", self.refused("needs exactly 1"))

    def test_missing_search_text_changes_nothing(self):
        self.propose_edit("sites/fx.test/src/content.json", find="Not there at all.")
        self.assertIn("occurs 0 times", self.refused("needs exactly 1"))

    def test_an_edit_that_changes_nothing_is_refused(self):
        self.propose_edit("sites/fx.test/src/content.json", find="Short one.", replace="Short one.")
        self.refused("does not change anything")

    def test_untracked_source_file_can_be_changed_when_approved(self):
        (self.site / "src" / "untracked.json").write_text("Short one.\n")
        self.propose_edit("sites/fx.test/src/untracked.json")
        self.apply(["SEO-001"], minutes=5)
        self.assertEqual((self.site / "src/untracked.json").read_text(), "A rewritten description that is clearly different from the former one.\n")

    def test_missing_file_is_refused(self):
        self.propose_edit("sites/fx.test/src/gone.json")
        self.refused("does not exist")

    def test_paths_outside_the_site_traversal_and_absolute_paths_are_refused(self):
        (self.root / "sites" / "fx.test2").mkdir()
        (self.root / "sites" / "fx.test2" / "x.json").write_text("Short one.\n")
        (self.root / "README.txt").write_text("Short one.\n")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "other files")
        outside = self.tmp / "outside.txt"
        outside.write_text("Short one.\n")
        cases = [("README.txt", "outside the site folder"), ("sites/fx.test2/x.json", "outside the site folder"),
                 ("sites/fx.test/../fx.test2/x.json", "relative and inside the site"), ("sites/fx.test/../../README.txt", "relative and inside the site"),
                 (str(outside), "relative and inside the site"), (".project/specs/website.json", "outside the site folder")]
        for i, (rel, needle) in enumerate(cases):
            self.propose_edit(rel) if i == 0 else self.repropose(rel)
            self.refused(needle, minutes=10 + i)
        self.assertEqual(outside.read_text(), "Short one.\n")
        self.assertEqual((self.root / "README.txt").read_text(), "Short one.\n")

    def repropose(self, file):
        proposal = {"summary": "edit", "kind": "draft", "proposed": "A rewritten description that is clearly different from the former one.",
                    "edit": {"file": file, "find": "Short one.", "replace": "A rewritten description that is clearly different from the former one."}}
        self.decide(["SEO-001"], "proposed", change=True)
        import audit
        audit.do_propose(self.root, h.COMPONENT, {"SEO-001": proposal}, now=self.now(3))
        self.decide(["SEO-001"], "approved")

    def test_a_symlinked_file_is_refused_and_the_target_behind_it_stays_unchanged(self):
        outside = self.tmp / "outside.json"
        outside.write_text('"Short one."\n')
        os.symlink(outside, self.site / "src" / "linked.json")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "link")
        self.propose_edit("sites/fx.test/src/linked.json")
        self.assertIn("symlink", self.refused("symlink"))
        self.assertEqual(outside.read_text(), '"Short one."\n')

    def test_a_file_below_a_symlinked_folder_is_refused(self):
        real = self.site / "src" / "realdir"
        real.mkdir()
        (real / "inner.json").write_text('"Short one."\n')
        os.symlink("realdir", self.site / "src" / "linkdir")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "linkdir")
        self.propose_edit("sites/fx.test/src/linkdir/inner.json")
        self.refused("symlink")
        self.assertEqual((real / "inner.json").read_text(), '"Short one."\n')

    def test_bd7_line_endings_of_the_edited_file_stay_byte_exact(self):
        raw = ('[\r\n {"url": "/", "description": "%s"},\r\n {"url": "/a.html", "description": "Short one."}\r\n]\r\n' % h.LONG).encode()
        (self.site / "src" / "content.json").write_bytes(raw)
        h.sh(self.root, "git", "commit", "-qam", "crlf")
        self.propose_edit("sites/fx.test/src/content.json")
        self.apply(["SEO-001"], minutes=5)
        after = (self.site / "src" / "content.json").read_bytes()
        self.assertEqual(after, raw.replace(b"Short one.", b"A rewritten description that is clearly different from the former one."))
        self.assertNotIn(b"\n", after.replace(b"\r\n", b""))

    def test_bd8_a_file_that_is_not_utf8_text_is_refused_with_a_controlled_stop(self):
        (self.site / "src" / "bin.dat").write_bytes(b"\xff\xfe\x00 Short one. \xff")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "bin")
        self.propose_edit("sites/fx.test/src/bin.dat")
        self.refused("cannot be read as UTF-8 text")
        code, out = self.cli("apply", "SEO-001", "--npm", str(self.npm))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP:"), out)
        self.assertNotIn("Traceback", out)

    def test_bd9_a_failed_replace_restores_the_files_and_leaves_no_temp_file_in_the_site(self):
        (self.site / "src" / "second.json").write_text('{"d": "Also short text here."}\n')
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "second")
        second = {"summary": "s", "kind": "draft", "proposed": "Another description sentence.",
                  "edit": {"file": "sites/fx.test/src/second.json", "find": "Also short text here.", "replace": "Another description sentence."}}
        self.audit(proposals={"seo.description-too-short|/a.html|": self.proposal_for(h.GOOD_A), "seo.description-too-short|/b.html|": second})
        self.decide(["SEO-001", "SEO-002"], "approved")
        before = tree_state(self)
        real, calls = os.replace, []

        def second_replace_fails(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError("disk full (simulated)")
            return real(src, dst)

        with mock.patch("os.replace", side_effect=second_replace_fails):
            with self.assertRaises(OSError):
                self.apply(["SEO-001", "SEO-002"], minutes=5)
        self.assertEqual(tree_state(self), before, "the first file must be restored byte for byte")
        self.assertEqual([p.name for p in self.site.rglob(".optimize-apply-*")], [], "no temp file may remain in the versioned site")
        self.assertEqual(self.finding("SEO-001")["status"], "approved")
        self.assertIsNone(self.finding("SEO-001")["resolution"])

    def test_bd11_a_file_system_error_ends_as_a_stop_message_not_a_traceback(self):
        self.audit()
        folder = self.root / ".project" / "reports" / "fx.test" / "optimize"
        os.chmod(folder, 0o500)
        self.addCleanup(os.chmod, folder, 0o700)
        if os.access(folder, os.W_OK):
            self.skipTest("directory permissions are not enforced for this user")
        code, out = self.cli("audit", "--npm", str(self.npm))
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOP:"), out)
        self.assertNotIn("Traceback", out)
        self.assertFalse((folder.parent / ".optimize.lock").exists())


class IndependentChangesSurvive(h.AuditCase):
    def test_uncommitted_and_untracked_changes_of_others_are_kept_by_audit_decide_and_apply(self):
        self.audit(proposals={"seo.description-too-short|/a.html|": self.proposal_for(h.GOOD_A)})
        self.decide(["SEO-001"], "approved")
        (self.site / "src" / "touched.txt").write_text("someone else's uncommitted edit\n")                  # tracked, modified
        (self.site / "notes.txt").write_text("someone else's untracked note\n")                              # untracked
        (self.site / "src" / "content.json").write_text((self.site / "src" / "content.json").read_text() + "\n")   # their edit in the target file
        mine = ((self.site / "src" / "touched.txt").read_bytes(), (self.site / "notes.txt").read_bytes())
        r = self.apply(["SEO-001"], minutes=1)
        self.assertEqual(r["status"], "clean-with-warnings", r)             # their edits existed before the run: no read-only violation
        self.assertEqual(((self.site / "src" / "touched.txt").read_bytes(), (self.site / "notes.txt").read_bytes()), mine)
        text = (self.site / "src" / "content.json").read_text()
        self.assertIn(h.GOOD_A, text)
        self.assertTrue(text.endswith("]\n\n"), "their trailing edit in the target file is kept")
        report = (self.root / r["report"]).read_text()
        self.assertIn("audited as they were", report)




class EditsBindToTheOriginal(h.AuditCase):
    """All replacement spans of one apply are located in the ORIGINAL content, never in text produced by an earlier edit."""
    A, B = "sites/fx.test/src/words.txt", "sites/fx.test/src/more.txt"

    def setUp(self):
        super().setUp()
        (self.site / "src" / "words.txt").write_bytes(b"Alpha Beta\r\nkeep one\r\nDelta\r\n")
        (self.site / "src" / "more.txt").write_text("Epsilon\n")
        h.sh(self.root, "git", "add", "-A")
        h.sh(self.root, "git", "commit", "-qm", "words")

    def edit(self, find, replace, file=None):
        return {"file": file or self.A, "find": find, "replace": replace}

    def prepare(self, first, second, approve=True):
        def proposal(edits):
            return {"summary": "multi", "kind": "draft", "proposed": "x", "edits": edits}
        self.audit(proposals={"seo.description-too-short|/a.html|": proposal(first), "seo.description-too-short|/b.html|": proposal(second)})
        if approve:
            self.decide(["SEO-001", "SEO-002"], "approved")

    def words(self):
        return (self.site / "src" / "words.txt").read_bytes()

    def test_alpha_beta_example_in_both_id_orders(self):
        for order in (["SEO-001", "SEO-002"], ["SEO-002", "SEO-001"]):
            with self.subTest(order=order):
                self.setUp()
                self.prepare([self.edit("Alpha", "Beta")], [self.edit("Beta", "Gamma")])
                self.apply(order, minutes=1)
                self.assertEqual(self.words(), b"Beta Gamma\r\nkeep one\r\nDelta\r\n")         # not "Gamma Beta"; CRLF kept

    def test_several_independent_edits_in_one_file_and_across_files(self):
        self.prepare([self.edit("Alpha", "A1"), self.edit("Delta", "D1")], [self.edit("Beta", "B1"), self.edit("Epsilon", "E1", self.B)])
        self.apply(["SEO-001", "SEO-002"], minutes=1)
        self.assertEqual(self.words(), b"A1 B1\r\nkeep one\r\nD1\r\n")
        self.assertEqual((self.site / "src" / "more.txt").read_text(), "E1\n")

    def test_adjacent_but_not_overlapping_spans_are_applied(self):
        self.prepare([self.edit("Alpha", "X")], [self.edit(" Beta", "Y")])
        self.apply(["SEO-001", "SEO-002"], minutes=1)
        self.assertEqual(self.words(), b"XY\r\nkeep one\r\nDelta\r\n")

    def test_edits_that_produce_the_text_of_a_later_search_do_not_confuse_the_location(self):
        self.prepare([self.edit("Delta", "Alpha Beta")], [self.edit("Alpha Beta", "Q")])       # the second search text also occurs once in the original
        self.apply(["SEO-001", "SEO-002"], minutes=1)
        self.assertEqual(self.words(), b"Q\r\nkeep one\r\nAlpha Beta\r\n")

    def rejected(self, needle, ids=("SEO-001", "SEO-002")):
        before = tree_state(self)
        calls = len(self.npm_calls())
        reports = self.reports()
        with self.assertRaises(Stop) as ctx:
            self.apply(list(ids), minutes=3)
        self.assertIn(needle, str(ctx.exception))
        self.assertEqual(tree_state(self), before)
        self.assertEqual(self.words(), b"Alpha Beta\r\nkeep one\r\nDelta\r\n")
        self.assertEqual(len(self.npm_calls()), calls, "no build for a rejected request")
        self.assertEqual(self.reports(), reports, "no report, no success message")
        self.assertEqual([f["resolution"] for f in self.state()["findings"]], [None, None])
        self.assertEqual([p.name for p in self.site.rglob(".optimize-apply-*")], [])

    def test_overlapping_spans_are_refused_before_any_write(self):
        self.prepare([self.edit("Alpha Beta", "X")], [self.edit("Beta", "Y")])
        self.rejected("overlapping text")

    def test_overlap_in_the_second_file_does_not_leave_the_first_file_changed(self):
        self.prepare([self.edit("Alpha", "A1"), self.edit("Epsilon", "E1", self.B)], [self.edit("Epsilon", "E2", self.B)])
        before_more = (self.site / "src" / "more.txt").read_text()
        with self.assertRaises(Stop):
            self.apply(["SEO-001", "SEO-002"], minutes=3)
        self.assertEqual(self.words(), b"Alpha Beta\r\nkeep one\r\nDelta\r\n")
        self.assertEqual((self.site / "src" / "more.txt").read_text(), before_more)

    def test_the_same_span_requested_twice_is_a_contradiction(self):
        self.prepare([self.edit("Alpha", "X")], [self.edit("Alpha", "Y")])
        self.rejected("overlapping text")

    def test_an_empty_search_text_is_refused(self):
        self.prepare([self.edit("", "X")], [self.edit("Beta", "Y")])
        self.rejected("is empty")

    def test_a_repeated_id_is_applied_once(self):
        self.prepare([self.edit("Alpha", "Beta")], [self.edit("Beta", "Gamma")])
        self.apply(["SEO-001", "SEO-001", "SEO-002", "SEO-001"], minutes=1)
        self.assertEqual(self.words(), b"Beta Gamma\r\nkeep one\r\nDelta\r\n")
        self.assertEqual(self.npm_calls().count("run build"), 2)                              # first audit + one recheck
