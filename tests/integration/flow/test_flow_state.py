"""Guided flow acceptance (state contract, brief, design loop, approval, implementation record, checks, staleness, damage).
Fictional projects, fake npm (via setup), no network, no git. Structural checks: they prove no conversation behaviour or design quality."""
import json
import unittest
from pathlib import Path

from tests.support import flow_helpers as f
from tests.support import setup_helpers as h
from site_common import flowstate
from site_common.errors import Stop

SITE = f.SITE


def status(root):
    return flowstate.derive(root, SITE)


class EntryAndStatusTests(unittest.TestCase):
    def test_empty_project_asks_for_setup_and_status_writes_nothing(self):
        root = f.project(create=False)
        code, out = f.cli(root, "status")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["next_step"], "setup")
        self.assertEqual(h.snapshot(root), {})

    def test_existing_setup_goes_to_the_brief_and_status_is_idempotent(self):
        root = f.project()
        before = h.snapshot(root)
        first = status(root)
        self.assertEqual((first["setup"]["state"], first["next_step"], first["brief"]["state"]), ("complete", "brief", "missing"))
        self.assertEqual(status(root), first)
        self.assertEqual(h.snapshot(root), before)
        self.assertFalse((root / ".project/website").exists())

    def test_domainless_project_is_complete_and_continues(self):
        root = f.project(domain=None)
        self.assertEqual((status(root)["setup"]["state"], status(root)["next_step"]), ("complete", "brief"))

    def test_contradictory_setup_is_not_treated_as_empty(self):
        root = f.project()
        lib = root / "sites" / SITE / "src/lib/site.ts"
        lib.write_text(lib.read_text().replace("https://demo-a.com", "https://evil.example"))
        before = h.snapshot(root)
        derived = status(root)
        self.assertEqual((derived["setup"]["state"], derived["next_step"]), ("contradictory", "resolve-setup"))
        self.assertTrue(any("evil.example" in p for p in derived["setup"]["problems"]))
        self.assertEqual(h.snapshot(root), before)
        with self.assertRaises(Stop):
            flowstate.design_new(root, SITE)

    def test_version_1_manifest_is_contradictory_not_empty(self):
        root = f.project()
        file = root / ".project/specs/website.json"
        data = json.loads(file.read_text())
        data["version"] = 1
        file.write_text(json.dumps(data))
        self.assertEqual(status(root)["setup"]["state"], "contradictory")
        self.assertEqual(status(root)["next_step"], "resolve-setup")

    def test_unknown_site_is_missing_not_empty_project(self):
        root = f.project()
        derived = flowstate.derive(root, "other-site")
        self.assertEqual((derived["setup"]["state"], derived["next_step"]), ("missing", "setup"))


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.root = f.project()

    def test_incomplete_brief_is_resumed_after_answers(self):
        draft = f.brief(offer=f.field(None, "open"), tone=f.field("ruhig", "proposed"))
        draft["fields"]["offer"] = {"value": None, "status": "open"}
        self.assertEqual(flowstate.brief_save(self.root, SITE, draft)["state"], "saved")
        derived = status(self.root)
        self.assertEqual((derived["brief"]["state"], derived["next_step"]), ("in-progress", "brief"))
        self.assertEqual(sorted(derived["brief"]["open_items"]), ["offer: open", "tone: proposed"])
        with self.assertRaises(Stop):
            flowstate.brief_confirm(self.root, SITE, "ok")
        flowstate.brief_save(self.root, SITE, f.brief())                       # answers arrive
        self.assertEqual(status(self.root)["brief"]["revision"], 2)
        self.assertEqual(flowstate.brief_confirm(self.root, SITE, "Ja")["state"], "confirmed")
        self.assertEqual(status(self.root)["next_step"], "design")
        self.assertTrue((self.root / ".project/website" / SITE / "brief-history/r001.json").is_file())

    def test_confirmation_needs_an_explicit_statement(self):
        flowstate.brief_save(self.root, SITE, f.brief())
        for statement in ("", "   ", None):
            with self.assertRaises(Stop):
                flowstate.brief_confirm(self.root, SITE, statement)
        self.assertEqual(status(self.root)["brief"]["state"], "in-progress")

    def test_invalid_briefs_are_refused_and_write_nothing(self):
        before = h.snapshot(self.root)
        for bad in ({**f.brief(), "extra": 1}, f.brief(site_language=f.field("Deutsch")),
                    f.brief(palette=f.field({"name": "x", "colors": {"primary": "red", "background": "#ffffff"}})),
                    f.brief(unknown=f.field("x")), {**f.brief(), "schema_version": 2}):
            with self.assertRaises(Stop):
                flowstate.brief_save(self.root, SITE, bad)
        self.assertEqual(h.snapshot(self.root), before)

    def test_identical_save_does_not_create_a_revision(self):
        flowstate.brief_save(self.root, SITE, f.brief())
        self.assertEqual(flowstate.brief_save(self.root, SITE, f.brief())["state"], "unchanged")
        self.assertEqual(status(self.root)["brief"]["revision"], 1)

    def test_operator_language_and_website_language_are_separate(self):
        flowstate.brief_save(self.root, SITE, f.brief(site_language=f.field("en")))
        self.assertFalse((self.root / ".project/operator.json").exists())
        self.assertEqual(json.loads((self.root / ".project/website" / SITE / "brief.json").read_text())["fields"]["site_language"]["value"], "en")


class DesignTests(unittest.TestCase):
    def test_no_design_before_a_confirmed_brief(self):
        root = f.project()
        with self.assertRaises(Stop):
            flowstate.design_new(root, SITE)
        flowstate.brief_save(root, SITE, f.brief())
        with self.assertRaises(Stop):
            flowstate.design_new(root, SITE)

    def test_two_distinct_variants_register_and_leave_the_site_untouched(self):
        root = f.confirmed_project()
        site_before = h.sub(h.snapshot(root), "sites")
        self.assertEqual(flowstate.design_new(root, SITE)["state"], "created")
        f.write_variants(root, 1)
        result = flowstate.design_register(root, SITE, 1)
        self.assertEqual((result["state"], result["variants"]), ("registered", ["A", "B"]))
        self.assertEqual(h.sub(h.snapshot(root), "sites"), site_before)         # existing start page and site untouched
        folder = root / ".project/website" / SITE / "design/r001"
        self.assertTrue((folder / "index.html").is_file())
        self.assertIn('src="A.html"', (folder / "index.html").read_text())
        self.assertEqual(status(root)["next_step"], "design-choose")
        self.assertFalse(any(p.suffix == ".html" for p in (root / "sites" / SITE / "src").rglob("*") if "A" == p.stem or "B" == p.stem))

    def test_prototypes_live_outside_the_site_and_never_reach_a_build(self):
        root = f.with_variants()
        for p in (root / "sites" / SITE).rglob("*"):
            self.assertNotIn("design", p.relative_to(root / "sites" / SITE).parts[:1])
        self.assertNotIn("sites", (root / ".project/website" / SITE / "design/r001").relative_to(root).parts)

    def test_one_variant_or_a_colour_change_is_not_two_directions(self):
        root = f.confirmed_project()
        flowstate.design_new(root, SITE)
        f.write_variants(root, 1, names=("A",))
        with self.assertRaises(Stop) as one:
            flowstate.design_register(root, SITE, 1)
        self.assertIn("at least two", str(one.exception))
        f.write_variants(root, 1, a=f.page_a(), b=f.page_a(primary="#2f6f5e").replace("#f6f8f5", "#102030"))
        with self.assertRaises(Stop) as same:
            flowstate.design_register(root, SITE, 1)
        self.assertIn("same page structure", str(same.exception))
        self.assertEqual(status(root)["design"]["state"], "missing")

    def test_prototype_content_rules(self):
        root = f.confirmed_project()
        flowstate.design_new(root, SITE)
        cases = {
            "lorem": f.page_a(extra="<p>Lorem ipsum dolor sit amet</p>"),
            "price": f.page_a(extra="<section><h2>Preise</h2><p>Eine Stunde 80 €</p></section>"),
            "percentage": f.page_a(extra="<p>95 % erfolgreich</p>"),
            "qualification": f.page_a(extra="<p>Zertifizierte Therapeutin</p>"),
            "since": f.page_a(extra="<p>seit 1998 in Wien</p>"),
            "language": f.page_a(lang="en"),
            "external": f.page_a(extra='<img src="https://cdn.example/x.png" alt="">'),
            "script": f.page_a(extra="<script>1</script>"),
            "colour": f.page_a(primary="#111111"),
        }
        for name, page in cases.items():
            f.write_variants(root, 1, a=page)
            with self.assertRaises(Stop, msg=name):
                flowstate.design_register(root, SITE, 1)
        ok = f.page_a(extra="<section><h2>Preise</h2><p data-open-fact>Preis pro Stunde: offene Angabe</p></section>")
        f.write_variants(root, 1, a=ok)
        self.assertEqual(flowstate.design_register(root, SITE, 1)["state"], "registered")

    def test_feedback_loop_creates_new_revisions_and_keeps_old_ones(self):
        root = f.with_variants()
        before = (root / ".project/website" / SITE / "design/r001/B.html").read_bytes()
        with self.assertRaises(Stop):
            flowstate.design_new(root, SITE)                                  # a new revision needs feedback first
        flowstate.design_feedback(root, SITE, "B gefällt mir, aber die Navigation links ist zu dunkel.")
        self.assertEqual(status(root)["design"]["state"], "revising")
        self.assertEqual(status(root)["next_step"], "design-revise")
        self.assertEqual(flowstate.design_new(root, SITE, "Navigation heller")["revision"], 2)
        f.write_variants(root, 2, a=f.page_a(), b=f.page_b(extra="<aside><p>heller</p></aside>"))
        flowstate.design_register(root, SITE, 2)
        derived = status(root)
        self.assertEqual((derived["design"]["latest"], derived["design"]["revisions"], derived["next_step"]), (2, 2, "design-choose"))
        self.assertEqual((root / ".project/website" / SITE / "design/r001/B.html").read_bytes(), before)

    def test_repeated_registration_and_resume_do_not_duplicate(self):
        root = f.with_variants()
        self.assertEqual(flowstate.design_register(root, SITE, 1)["state"], "unchanged")
        self.assertEqual(len(status(root)["design"]["variants"]), 2)
        flowstate.design_feedback(root, SITE, "mehr Weißraum")
        first = flowstate.design_new(root, SITE)
        self.assertEqual(flowstate.design_new(root, SITE)["state"], "resumed")
        self.assertEqual(first["revision"], 2)

    def test_registered_variant_changed_afterwards_is_damage_not_a_silent_edit(self):
        root = f.with_variants()
        path = root / ".project/website" / SITE / "design/r001/A.html"
        path.write_text(path.read_text() + "<!-- edited -->")
        derived = status(root)
        self.assertEqual(derived["design"]["state"], "damaged")
        self.assertEqual(derived["next_step"], "report-damaged-state")
        with self.assertRaises(Stop):
            flowstate.design_approve(root, SITE, 1, "A", "ja")
        with self.assertRaises(Stop):
            flowstate.design_register(root, SITE, 1)


class ApprovalAndImplementationTests(unittest.TestCase):
    def test_a_preference_is_not_an_approval_and_nothing_is_implemented_before_it(self):
        root = f.with_variants()
        with self.assertRaises(Stop):
            flowstate.design_approve(root, SITE, 1, "B", "")
        with self.assertRaises(Stop):
            flowstate.implement_start(root, SITE)
        self.assertEqual(status(root)["design"]["state"], "variants")
        self.assertEqual(status(root)["implementation"]["state"], "missing")

    def test_approval_is_bound_to_the_shown_revision_and_variant(self):
        root = f.with_variants()
        with self.assertRaises(Stop):
            flowstate.design_approve(root, SITE, 2, "B", "ja")                # not a shown revision
        with self.assertRaises(Stop):
            flowstate.design_approve(root, SITE, 1, "C", "ja")                # no such variant
        self.assertEqual(flowstate.design_approve(root, SITE, 1, "B", "Ja, Revision 1 B")["state"], "approved")
        self.assertEqual(flowstate.design_approve(root, SITE, 1, "B", "Ja, Revision 1 B")["state"], "unchanged")
        self.assertEqual((status(root)["design"]["state"], status(root)["next_step"]), ("approved", "implement"))
        flowstate.design_feedback(root, SITE, "doch noch eine Änderung")
        flowstate.design_new(root, SITE)
        f.write_variants(root, 2, b=f.page_b(extra="<aside><p>neu</p></aside>"))
        flowstate.design_register(root, SITE, 2)
        derived = status(root)
        self.assertTrue(derived["design"]["approval"]["stale"])               # newer revision: the old approval no longer applies
        self.assertEqual((derived["design"]["state"], derived["next_step"]), ("variants", "design-choose"))
        with self.assertRaises(Stop):
            flowstate.implement_start(root, SITE)

    def test_implementation_records_checks_bound_to_the_content(self):
        root = f.approved_project()
        page = f.index_path(root)
        started = flowstate.implement_start(root, SITE)
        self.assertEqual(started["state"], "started")
        self.assertEqual(flowstate.implement_start(root, SITE)["state"], "resumed")      # idempotent re-entry
        with self.assertRaises(Stop):
            flowstate.implement_finish(root, SITE, f.edit_session(self, root, write=False))      # a session without a write proves nothing
        self.assertEqual(status(root)["implementation"]["state"], "started")
        folder = f.edit_session(self, root, "\n<!-- design B -->\n")
        self.assertEqual(flowstate.implement_finish(root, SITE, folder)["state"], "implemented")
        self.assertEqual(status(root)["implementation"]["state"], "done")
        self.assertEqual(status(root)["next_step"], "checks")
        sha = flowstate.sha256(page.read_bytes())
        good = {"state": "checked", "build": {"exit": 0}, "check": {"exit": 0}, "checked_sha": sha}
        with self.assertRaises(Stop):
            flowstate.record_checks(root, SITE, {**good, "checked_sha": "0" * 64})
        with self.assertRaises(Stop):
            flowstate.record_checks(root, SITE, good, "passed", "")
        flowstate.record_checks(root, SITE, good, "open")
        self.assertEqual(status(root)["checks"], {"technical": "passed", "visual": "open"})
        self.assertEqual(status(root)["next_step"], "checks")                   # the visual check is still open
        flowstate.record_checks(root, SITE, good, "passed", "Startseite im Browser angesehen")
        self.assertEqual(status(root)["next_step"], "done")
        self.assertEqual(flowstate.implement_start(root, SITE)["state"], "already-implemented")
        flowstate.record_checks(root, SITE, {**good, "state": "failed", "build": {"exit": 1}}, "passed", "gesehen")
        self.assertEqual(status(root)["checks"]["technical"], "failed")
        self.assertNotEqual(status(root)["next_step"], "done")

    def test_a_change_by_the_person_after_the_approval_is_a_conflict(self):
        root = f.approved_project()
        page = f.index_path(root)
        page.write_text(page.read_text() + "\n<!-- my own change -->\n")
        mine = page.read_bytes()
        with self.assertRaises(Stop) as error:
            flowstate.implement_start(root, SITE)
        self.assertIn("not overwritten", str(error.exception))
        self.assertEqual(page.read_bytes(), mine)
        self.assertEqual(flowstate.implement_start(root, SITE, accept_current_page=True)["state"], "started")

    def test_a_change_after_the_implementation_is_reported_and_checks_become_outdated(self):
        root = f.approved_project()
        page = f.index_path(root)
        flowstate.implement_start(root, SITE)
        flowstate.implement_finish(root, SITE, f.edit_session(self, root, "\n<!-- B -->\n"))
        sha = flowstate.sha256(page.read_bytes())
        flowstate.record_checks(root, SITE, {"state": "checked", "build": {"exit": 0}, "check": {"exit": 0}, "checked_sha": sha}, "passed", "gesehen")
        page.write_text(page.read_text() + "<!-- later -->\n")
        derived = status(root)
        self.assertEqual((derived["implementation"]["state"], derived["next_step"]), ("user-changed", "resolve-user-change"))
        with self.assertRaises(Stop):
            flowstate.implement_start(root, SITE)

    def test_brief_change_marks_everything_stale_and_deletes_nothing(self):
        root = f.approved_project()
        page = f.index_path(root)
        flowstate.implement_start(root, SITE)
        flowstate.implement_finish(root, SITE, f.edit_session(self, root, "\n<!-- B -->\n"))
        designs = {str(p): p.read_bytes() for p in (root / ".project/website" / SITE / "design").rglob("*") if p.is_file()}
        written = page.read_bytes()
        flowstate.brief_save(root, SITE, f.brief(tone=f.field("sachlich und knapp")))
        derived = status(root)
        self.assertEqual(derived["brief"]["state"], "in-progress")
        self.assertTrue(derived["brief"]["changed_since_confirmation"])
        self.assertEqual(derived["design"]["state"], "stale")
        self.assertEqual(set(derived["stale"]), {"design", "approval", "implementation"})
        self.assertEqual(derived["next_step"], "brief")
        self.assertEqual({str(p): p.read_bytes() for p in (root / ".project/website" / SITE / "design").rglob("*") if p.is_file()}, designs)
        self.assertEqual(page.read_bytes(), written)
        with self.assertRaises(Stop):
            flowstate.design_new(root, SITE)                                    # needs the changed brief to be confirmed again
        flowstate.brief_confirm(root, SITE, "Ja, so")
        self.assertEqual(status(root)["next_step"], "design")                   # old variants stay but are stale
        flowstate.design_feedback(root, SITE, "an das neue Briefing anpassen")
        self.assertEqual(flowstate.design_new(root, SITE)["revision"], 2)

    def test_exact_file_existence_proves_nothing(self):
        root = f.with_variants()
        folder = root / ".project/website" / SITE / "design"
        (folder / "r002").mkdir()
        (folder / "r002" / "A.html").write_text(f.page_a())
        (folder / "r002" / "B.html").write_text(f.page_b())
        self.assertEqual(status(root)["design"]["latest"], 1)                    # unregistered files are not a revision
        self.assertEqual(status(root)["design"]["revisions"], 1)


class DamageTests(unittest.TestCase):
    def test_damaged_unknown_or_foreign_records_block_writes_and_stay_unchanged(self):
        for label, content in (("invalid json", b"{not json"), ("unknown version", json.dumps({"schema_version": 9, "site": SITE}).encode()),
                               ("foreign site", json.dumps({"schema_version": 1, "site": "other", "brief": {}, "design": {"revisions": []}}).encode()),
                               ("not an object", b"[1]"), ("missing keys", json.dumps({"schema_version": 1, "site": SITE}).encode())):
            with self.subTest(label):
                root = f.project()
                path = root / ".project/website" / SITE / "flow.json"
                path.parent.mkdir(parents=True)
                path.write_bytes(content)
                derived = status(root)
                self.assertEqual((derived["state"], derived["next_step"]), ("unreadable", "report-damaged-state"))
                with self.assertRaises(Stop):
                    flowstate.brief_save(root, SITE, f.brief())
                self.assertEqual(path.read_bytes(), content)
                self.assertFalse((path.parent / "brief.json").exists())

    def test_brief_and_record_disagreeing_is_reported(self):
        root = f.confirmed_project()
        path = root / ".project/website" / SITE / "brief.json"
        path.unlink()
        self.assertEqual(status(root)["brief"]["state"], "damaged")
        self.assertEqual(status(root)["next_step"], "report-damaged-state")

    def test_symlinks_in_the_state_area_are_never_followed(self):
        root = f.project()
        outside = Path(f.tempfile.mkdtemp())
        (root / ".project/website").mkdir(parents=True)
        (root / ".project/website" / SITE).symlink_to(outside)
        with self.assertRaises(Stop):
            flowstate.brief_save(root, SITE, f.brief())
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(status(root)["state"], "unreadable")


class CliTests(unittest.TestCase):
    def test_exit_codes_and_json(self):
        root = f.project()
        code, out = f.cli(root, "design-new", "--site", SITE)
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(out)["message"].startswith("STOP:"))
        brief_file = Path(f.tempfile.mkdtemp()) / "brief.json"
        brief_file.write_text(json.dumps(f.brief()))
        self.assertEqual(f.cli(root, "brief-save", "--site", SITE, "--file", str(brief_file))[0], 0)
        self.assertEqual(f.cli(root, "brief-confirm", "--site", SITE, "--statement", "Ja")[0], 0)
        code, out = f.cli(root, "status")
        self.assertEqual((code, json.loads(out)["next_step"]), (0, "design"))


class PublishPlaceholderTests(unittest.TestCase):
    def test_publish_stays_a_placeholder(self):
        folder = f.sp.ROOT / "skills/publish"
        self.assertEqual([p.name for p in folder.iterdir()], ["SKILL.md"])


if __name__ == "__main__":
    unittest.main()
