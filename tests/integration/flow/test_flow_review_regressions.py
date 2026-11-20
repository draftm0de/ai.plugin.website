"""Regression tests for the independent review of the guided flow: nested state validation, history safety, new vs. incomplete projects,
safe resumption of an implementation, integrity of the comparison page. Fictional projects, no network."""
import json
import tempfile
import unittest
from pathlib import Path

from tests.support import flow_helpers as f
from tests.support import setup_helpers as h
from site_common import flowstate
from site_common.errors import Stop

SITE = f.SITE


def status(root):
    return flowstate.derive(root, SITE)


def record_path(root):
    return root / ".project/website" / SITE / "flow.json"


def mutate(root, fn):
    path = record_path(root)
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data, indent=2))
    return path.read_bytes()


class NestedStateValidationTests(unittest.TestCase):
    def check_unreadable(self, root, raw):
        derived = status(root)
        self.assertEqual((derived["state"], derived["next_step"]), ("unreadable", "report-damaged-state"), derived)
        before = h.snapshot(root)
        for call in (lambda: flowstate.brief_save(root, SITE, f.brief(tone=f.field("anders"))),
                     lambda: flowstate.design_new(root, SITE), lambda: flowstate.design_feedback(root, SITE, "x"),
                     lambda: flowstate.design_approve(root, SITE, 1, "A", "ja"), lambda: flowstate.implement_start(root, SITE)):
            with self.assertRaises(Stop):
                call()
        self.assertEqual(h.snapshot(root), before)
        self.assertEqual(record_path(root).read_bytes(), raw)

    def test_damaged_nested_values_are_diagnosed_and_kept(self):
        cases = {
            "brief revision is a string": lambda d: d["brief"].update(revision="1"),
            "confirmed is a list": lambda d: d["brief"].update(confirmed=[]),
            "confirmed revision above brief revision": lambda d: d["brief"]["confirmed"].update(revision=9),
            "confirmed sha not a sha": lambda d: d["brief"]["confirmed"].update(sha256="zz"),
            "revisions not numbered": lambda d: d["design"]["revisions"][0].update(revision=3),
            "variants is a list": lambda d: d["design"]["revisions"][0].update(variants=[]),
            "variant file mismatch": lambda d: d["design"]["revisions"][0]["variants"]["A"].update(file="evil.html"),
            "variant without hash": lambda d: d["design"]["revisions"][0]["variants"]["B"].pop("sha256"),
            "comparison hash missing": lambda d: d["design"]["revisions"][0].pop("comparison_sha256"),
            "unknown key": lambda d: d["design"]["revisions"][0].update(extra=1),
            "approval of a missing revision": lambda d: d["design"].update(approval={
                "revision": 5, "variant": "A", "variant_sha256": "0" * 64, "brief_sha256": "0" * 64, "statement": "ja", "index_sha256_at_approval": None}),
            "approval hash differs": lambda d: d["design"].update(approval={
                "revision": 1, "variant": "A", "variant_sha256": "1" * 64, "brief_sha256": d["design"]["revisions"][0]["brief_sha256"],
                "statement": "ja", "index_sha256_at_approval": None}),
            "implementation of a missing variant": lambda d: d.update(implementation={
                "status": "started", "approval_revision": 1, "variant": "Z", "variant_sha256": "0" * 64, "base_sha256": None, "result_sha256": None}),
            "done without result": lambda d: d.update(implementation={
                "status": "done", "approval_revision": 1, "variant": "A", "variant_sha256": d["design"]["revisions"][0]["variants"]["A"]["sha256"],
                "base_sha256": None, "result_sha256": None}),
            "checks without implementation": lambda d: d.update(checks={"for_sha256": "0" * 64, "technical": "passed", "visual": "passed", "visual_note": "x"}),
            "checks with an invalid word": lambda d: d.update(checks="done"),
        }
        for label, change in cases.items():
            with self.subTest(label):
                root = f.with_variants()
                raw = mutate(root, change)
                self.check_unreadable(root, raw)

    def test_non_integer_numbers_booleans_nulls_and_wrong_containers_are_diagnosed(self):
        revision_cases = {}
        for label, bad in (("float", 1.0), ("boolean", True), ("null", None), ("string", "1"), ("list", [1]), ("object", {"n": 1})):
            revision_cases[f"revisions[0].revision {label}"] = (lambda b: lambda d: d["design"]["revisions"][0].update(revision=b))(bad)
            revision_cases[f"revisions[0].brief_revision {label}"] = (lambda b: lambda d: d["design"]["revisions"][0].update(brief_revision=b))(bad)
            revision_cases[f"brief.revision {label}"] = (lambda b: lambda d: d["brief"].update(revision=b))(bad)
            revision_cases[f"confirmed.revision {label}"] = (lambda b: lambda d: d["brief"]["confirmed"].update(revision=b))(bad)
            revision_cases[f"schema_version {label}"] = (lambda b: lambda d: d.update(schema_version=b))(bad)
        revision_cases.update({
            "brief is a list": lambda d: d.update(brief=[]), "design is a list": lambda d: d.update(design=[]),
            "revisions is an object": lambda d: d["design"].update(revisions={}), "revisions entry is a list": lambda d: d["design"].update(revisions=[[]]),
            "variants is a string": lambda d: d["design"]["revisions"][0].update(variants="AB"),
            "confirmed is a string": lambda d: d["brief"].update(confirmed="yes"), "site is a number": lambda d: d.update(site=3)})
        for label, change in revision_cases.items():
            with self.subTest(label):
                root = f.with_variants()
                raw = mutate(root, change)
                self.check_unreadable(root, raw)

    def test_float_revision_one_point_zero_in_particular(self):
        root = f.with_variants()
        raw = mutate(root, lambda d: d["design"]["revisions"][0].update(revision=1.0))
        self.assertIn(b'"revision": 1.0', raw)
        derived = status(root)
        self.assertEqual(derived["state"], "unreadable")
        self.assertTrue(any("revision" in p and "integer" in p for p in derived["problems"]) or "1.0" in " ".join(derived["problems"]) or "revision" in " ".join(derived["problems"]))
        self.check_unreadable(root, raw)

    def test_numeric_fields_of_approval_and_implementation_are_integers(self):
        for label, change in (("approval.revision", lambda d: d["design"]["approval"].update(revision=1.0)),
                              ("implementation.approval_revision", lambda d: d["implementation"].update(approval_revision=1.0))):
            with self.subTest(label):
                root = f.approved_project()
                flowstate.implement_start(root, SITE)
                raw = mutate(root, change)
                self.check_unreadable(root, raw)

    def test_a_brief_with_non_integer_revision_or_schema_version_is_damaged(self):
        root = f.project()
        flowstate.brief_save(root, SITE, f.brief())
        path = root / ".project/website" / SITE / "brief.json"
        for label, change in (("revision float", {"revision": 1.0}), ("revision bool", {"revision": True}), ("schema_version float", {"schema_version": 1.0}),
                              ("schema_version bool", {"schema_version": True}), ("revision null", {"revision": None})):
            with self.subTest(label):
                data = json.loads(path.read_text())
                data.update(change)
                path.write_text(json.dumps(data))
                raw = path.read_bytes()
                self.assertEqual(status(root)["brief"]["state"], "damaged")
                with self.assertRaises(Stop):
                    flowstate.brief_save(root, SITE, f.brief(tone=f.field("anders")))
                self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(status(root)["next_step"], "report-damaged-state")

    def test_a_float_manifest_version_is_refused(self):
        root = f.project()
        file = root / ".project/specs/website.json"
        file.write_text(file.read_text().replace('"version": 2', '"version": 2.0'))
        derived = status(root)
        self.assertEqual((derived["setup"]["state"], derived["next_step"]), ("contradictory", "resolve-setup"))
        self.assertTrue(any("integer 2" in p for p in derived["setup"]["problems"]), derived["setup"]["problems"])

    def test_valid_records_stay_valid(self):
        for build in (f.project, f.confirmed_project, f.with_variants, f.approved_project):
            root = build()
            self.assertNotEqual(status(root)["state"], "unreadable")
        root = f.approved_project()
        flowstate.implement_start(root, SITE)
        self.assertNotEqual(status(root)["state"], "unreadable")


class BriefAndHistoryTests(unittest.TestCase):
    def setUp(self):
        self.root = f.project()
        flowstate.brief_save(self.root, SITE, f.brief())
        self.folder = self.root / ".project/website" / SITE

    def test_damaged_existing_brief_is_diagnosed_and_not_overwritten(self):
        brief_file = self.folder / "brief.json"
        for label, content in (("array", b"[]"), ("string", b'"x"'), ("bad field", json.dumps({"schema_version": 1, "revision": 1, "fields": {"purpose": 3}}).encode()),
                               ("wrong revision", json.dumps({**json.loads(brief_file.read_text()), "revision": 7}).encode()), ("not json", b"{")):
            with self.subTest(label):
                brief_file.write_bytes(content)
                derived = status(self.root)
                self.assertEqual(derived["brief"]["state"], "damaged")
                self.assertEqual(derived["next_step"], "report-damaged-state")
                snapshot = h.snapshot(self.root)
                with self.assertRaises(Stop):
                    flowstate.brief_save(self.root, SITE, f.brief(tone=f.field("anders")))
                with self.assertRaises(Stop):
                    flowstate.brief_confirm(self.root, SITE, "ja")
                self.assertEqual(h.snapshot(self.root), snapshot)
                self.assertEqual(brief_file.read_bytes(), content)

    def test_missing_brief_file_with_a_recorded_revision_is_not_recreated(self):
        (self.folder / "brief.json").unlink()
        with self.assertRaises(Stop):
            flowstate.brief_save(self.root, SITE, f.brief())
        self.assertFalse((self.folder / "brief.json").exists())

    def test_existing_history_is_never_overwritten_after_an_interrupted_write(self):
        orphan = self.folder / "brief-history/r002.json"
        orphan.write_text("interrupted: foreign content\n")
        before = orphan.read_bytes()
        with self.assertRaises(Stop) as error:
            flowstate.brief_save(self.root, SITE, f.brief(tone=f.field("anders")))
        self.assertIn("never overwritten", str(error.exception))
        self.assertEqual(orphan.read_bytes(), before)
        self.assertEqual(json.loads((self.folder / "flow.json").read_text())["brief"]["revision"], 1)
        self.assertEqual(json.loads((self.folder / "brief.json").read_text())["revision"], 1)

    def test_identical_orphan_history_completes_the_interrupted_save(self):
        candidate = f.brief(tone=f.field("anders"))
        candidate = {**candidate, "revision": 2}
        (self.folder / "brief-history/r002.json").write_bytes(flowstate.dumps(candidate))
        result = flowstate.brief_save(self.root, SITE, f.brief(tone=f.field("anders")))
        self.assertEqual((result["state"], result["revision"]), ("saved", 2))
        self.assertEqual(json.loads((self.folder / "brief.json").read_text())["revision"], 2)

    def test_brief_json_ahead_of_the_record_is_reported_not_repaired(self):
        data = json.loads((self.folder / "brief.json").read_text())
        data["revision"] = 2
        (self.folder / "brief.json").write_bytes(flowstate.dumps(data))
        self.assertEqual(status(self.root)["brief"]["state"], "damaged")
        raw = (self.folder / "brief.json").read_bytes()
        with self.assertRaises(Stop):
            flowstate.brief_save(self.root, SITE, f.brief())
        self.assertEqual((self.folder / "brief.json").read_bytes(), raw)

    def test_orphan_design_manifest_blocks_registration_without_overwriting(self):
        flowstate.brief_confirm(self.root, SITE, "ja")
        flowstate.design_new(self.root, SITE)
        folder = f.write_variants(self.root, 1)
        (folder / "manifest.json").write_text("orphan\n")
        with self.assertRaises(Stop):
            flowstate.design_register(self.root, SITE, 1)
        self.assertEqual((folder / "manifest.json").read_text(), "orphan\n")


class NewVersusIncompleteProjectTests(unittest.TestCase):
    def test_a_really_new_project_goes_to_setup(self):
        root = f.project(create=False)
        self.assertEqual(status(root)["next_step"], "setup")
        code, out = f.cli(root, "status")
        self.assertEqual((code, json.loads(out)["next_step"]), (0, "setup"))
        self.assertEqual(h.snapshot(root), {})

    def test_leftover_artifacts_without_a_manifest_are_not_a_new_project(self):
        leftovers = {
            "flow state": lambda r: (r / ".project/website" / SITE).mkdir(parents=True),
            "site folder": lambda r: (r / "sites" / SITE / "src").mkdir(parents=True),
            "ownership record": lambda r: ((r / ".project/specs").mkdir(parents=True), (r / ".project/specs/website.managed.json").write_text("{}")),
            "schema copy only": lambda r: ((r / ".project/specs").mkdir(parents=True), (r / ".project/specs/website.schema.json").write_text("{}")),
            "reports": lambda r: (r / ".project/reports/x").mkdir(parents=True),
        }
        for label, create in leftovers.items():
            with self.subTest(label):
                root = f.project(create=False)
                create(root)
                before = h.snapshot(root)
                for site_args in ((), ("--site", SITE)):
                    code, out = f.cli(root, "status", *site_args)
                    data = json.loads(out)
                    self.assertEqual(code, 0, out)
                    self.assertEqual((data["setup"]["state"], data["next_step"]), ("contradictory", "resolve-setup"), (site_args, data))
                    self.assertTrue(data["setup"]["problems"])
                self.assertEqual(h.snapshot(root), before)

    def test_manifest_removed_after_setup_is_reported_not_set_up_again(self):
        root = f.project()
        (root / ".project/specs/website.json").unlink()
        before = h.snapshot(root)
        derived = status(root)
        self.assertEqual((derived["setup"]["state"], derived["next_step"]), ("contradictory", "resolve-setup"))
        self.assertEqual(h.snapshot(root), before)

    def test_manifest_without_this_site_but_with_its_artifacts_is_contradictory(self):
        root = f.project()
        other = f.project(create=False)
        import static_setup
        static_setup.execute(h.opts("create", "other-site", other), h.FakeRunner())
        (root / ".project/specs/website.json").write_text((other / ".project/specs/website.json").read_text())
        derived = status(root)
        self.assertEqual((derived["setup"]["state"], derived["next_step"]), ("contradictory", "resolve-setup"))


class ImplementationResumptionTests(unittest.TestCase):
    def setUp(self):
        self.root = f.approved_project()
        self.page = f.index_path(self.root)
        self.started = flowstate.implement_start(self.root, SITE)

    def test_nothing_written_yet_resumes_cleanly(self):
        self.assertEqual(flowstate.implement_start(self.root, SITE)["state"], "resumed")
        self.assertEqual(status(self.root)["next_step"], "implement")

    def test_manual_change_then_a_new_edit_session_with_only_a_check_is_no_proof(self):
        self.page.write_text(self.page.read_text() + "\n<!-- written by the person -->\n")
        mine = self.page.read_bytes()
        derived = status(self.root)
        self.assertEqual((derived["implementation"]["state"], derived["next_step"]), ("started", "resolve-implementation-conflict"))
        check_only = f.edit_session(self, self.root, write=False, check=True)        # begin + check, no write
        with self.assertRaises(Stop) as error:
            flowstate.implement_finish(self.root, SITE, check_only)
        self.assertIn("no write of its own", str(error.exception))
        self.assertIn("not started from the recorded start state", str(error.exception))
        self.assertEqual(status(self.root)["implementation"]["state"], "started")
        self.assertEqual(self.page.read_bytes(), mine)
        self.assertEqual(flowstate.implement_start(self.root, SITE)["state"], "resumed-changed")
        self.assertEqual(self.page.read_bytes(), mine)
        self.assertEqual(status(self.root)["design"]["state"], "approved")           # the design approval is not asked again

    def test_a_new_session_that_writes_over_the_persons_change_still_does_not_prove_the_original_start(self):
        self.page.write_text(self.page.read_text() + "\n<!-- mine -->\n")
        later = f.edit_session(self, self.root, "\n<!-- B -->\n")                   # a complete session, but started from the person's page
        with self.assertRaises(Stop) as error:
            flowstate.implement_finish(self.root, SITE, later)
        self.assertIn("recorded start state", str(error.exception))

    def test_evidence_of_another_project_site_or_a_foreign_folder_is_rejected(self):
        folder = f.edit_session(self, self.root, "\n<!-- B -->\n")
        other = f.approved_project()                      # a second project with its own approval and implementation
        flowstate.implement_start(other, SITE)
        f.index_path(other).write_text(f.index_path(other).read_text() + "\n<!-- changed -->\n")
        with self.assertRaises(Stop) as error:
            flowstate.implement_finish(other, SITE, folder)
        self.assertIn("does not belong to this project", str(error.exception))
        for bad in (str(Path(f.tempfile.mkdtemp())), "relative/path", str(self.root)):
            with self.assertRaises(Stop):
                flowstate.implement_finish(self.root, SITE, bad)
        with self.assertRaises(Stop):
            flowstate.implement_finish(self.root, SITE, None)
        self.assertEqual(status(self.root)["implementation"]["state"], "started")

    def test_a_tampered_session_record_is_rejected(self):
        folder = f.edit_session(self, self.root, "\n<!-- B -->\n")
        index = Path(folder) / "index.json"
        original = index.read_bytes()
        for label, change in (("other site", lambda d: d.update(site="other")), ("other file", lambda d: d.update(file="src/pages/404.astro")),
                              ("no writes", lambda d: d.update(writes=[])), ("other start", lambda d: d.update(original_sha="0" * 64)),
                              ("last write differs", lambda d: d.update(expected_sha="0" * 64, writes=["0" * 64]))):
            with self.subTest(label):
                data = json.loads(original)
                change(data)
                index.write_text(json.dumps(data))
                with self.assertRaises(Stop):
                    flowstate.implement_finish(self.root, SITE, folder)
        index.write_bytes(original)
        self.assertEqual(flowstate.implement_finish(self.root, SITE, folder)["state"], "implemented")

    def test_real_edit_write_then_resumption_after_an_interruption(self):
        folder = f.edit_session(self, self.root, "\n<!-- design B -->\n")           # edit wrote the page, the flow was interrupted before finishing
        self.assertNotEqual(flowstate.sha256(self.page.read_bytes()), self.started["base_sha256"])
        derived = status(self.root)                                                  # a later call: the change is not yet attributed
        self.assertEqual(derived["next_step"], "resolve-implementation-conflict")
        resumed = flowstate.implement_start(self.root, SITE)
        self.assertEqual(resumed["state"], "resumed-changed")
        self.assertIn("edit session", resumed["message"])
        done = flowstate.implement_finish(self.root, SITE, folder)                    # fresh call with the surviving edit session
        self.assertEqual(done["state"], "implemented")
        self.assertEqual(done["edit_session"]["writes"], 1)
        self.assertEqual(done["edit_session"]["original_sha256"], self.started["base_sha256"])
        self.assertEqual(flowstate.implement_finish(self.root, SITE, folder)["state"], "unchanged")      # idempotent
        record = json.loads(record_path(self.root).read_text())
        self.assertEqual(record["implementation"]["edit_session"]["folder"], Path(folder).name)
        self.assertEqual((status(self.root)["implementation"]["state"], status(self.root)["next_step"]), ("done", "checks"))

    def test_the_person_can_accept_the_current_page_as_the_new_starting_point(self):
        self.page.write_text(self.page.read_text() + "\n<!-- mine -->\n")
        result = flowstate.implement_start(self.root, SITE, accept_current_page=True)
        self.assertEqual((result["state"], result["rebased"]), ("started", True))
        self.assertEqual(status(self.root)["design"]["state"], "approved")
        folder = f.edit_session(self, self.root, "\n<!-- design B -->\n")           # a session started after the rebase is valid
        self.assertEqual(flowstate.implement_finish(self.root, SITE, folder)["state"], "implemented")

    def test_an_unchanged_page_is_never_recorded_as_done(self):
        with self.assertRaises(Stop):
            flowstate.implement_finish(self.root, SITE, f.edit_session(self, self.root, write=False))

    def test_cli_requires_the_edit_session(self):
        code, out = f.cli(self.root, "implement-finish", "--site", SITE)
        self.assertEqual(code, 2)            # argparse: --edit-state is required
        code, out = f.cli(self.root, "implement-finish", "--site", SITE, "--edit-state", str(f.tempfile.mkdtemp()))
        self.assertEqual(code, 1, out)
        folder = f.edit_session(self, self.root, "\n<!-- B -->\n")
        code, out = f.cli(self.root, "implement-finish", "--site", SITE, "--edit-state", folder, tmp=f.use_edit_tmp(self))
        self.assertEqual(code, 0, out)


class RegisteredArtifactIntegrityTests(unittest.TestCase):
    def folder(self, root):
        return root / ".project/website" / SITE / "design/r001"

    def test_changed_or_missing_comparison_page_or_manifest_blocks_everything(self):
        for label, name in (("comparison page", "index.html"), ("revision manifest", "manifest.json")):
            for how in ("changed", "missing"):
                with self.subTest(f"{label} {how}"):
                    root = f.with_variants()
                    path = self.folder(root) / name
                    if how == "changed":
                        path.write_text(path.read_text() + " ")
                    else:
                        path.unlink()
                    derived = status(root)
                    self.assertEqual((derived["design"]["state"], derived["next_step"]), ("damaged", "report-damaged-state"))
                    self.assertTrue(any(name in p for p in derived["problems"]), derived["problems"])
                    with self.assertRaises(Stop):
                        flowstate.design_approve(root, SITE, 1, "A", "ja")
                    with self.assertRaises(Stop):
                        flowstate.design_register(root, SITE, 1)

    def test_a_manipulated_comparison_page_after_the_approval_blocks_status_and_implementation(self):
        root = f.approved_project()
        self.assertEqual(status(root)["design"]["state"], "approved")
        page = self.folder(root) / "index.html"
        page.write_text(page.read_text().replace("Variante B", "Variante X"))
        derived = status(root)
        self.assertEqual(derived["design"]["state"], "damaged")
        self.assertEqual(derived["next_step"], "report-damaged-state")
        with self.assertRaises(Stop):
            flowstate.implement_start(root, SITE)

    def test_a_started_implementation_is_blocked_when_a_registered_artifact_changes(self):
        root = f.approved_project()
        flowstate.implement_start(root, SITE)
        (self.folder(root) / "index.html").unlink()
        derived = status(root)
        self.assertEqual((derived["implementation"]["state"], derived["next_step"]), ("blocked", "report-damaged-state"))
        with self.assertRaises(Stop):
            flowstate.implement_finish(root, SITE, None)
        record = json.loads(record_path(root).read_text())
        self.assertEqual(record["implementation"]["status"], "started")           # the record is kept


if __name__ == "__main__":
    unittest.main()
