"""edit enforces the plugin's manifest contract on EVERY command, also on follow-up commands of an open session: an invalid or
former project format stops with a diagnosis before any side effect (no file change, no state change, no npm call, no removal of
the backup), and is never recorded as a conflict. No migration, no fallback. A leftover old schema file next to the current
format is not an error."""
import json
from pathlib import Path

from tests.support import edit_helpers as t
from tests.support import manifest_contract as mc
from tests.support.contract_cases import BROKEN_SCHEMAS, NEEDLE
from tests.support.edit_helpers import EditCase, GOOD

NEW = GOOD.replace("Training twice a week.", "Training three times a week.")
OLD = "zyris-website.schema.json"
SPECS = ".project/specs"


class ManifestContract(EditCase):
    def set_project_format(self, manifest=None, schema_text="keep", old_schema=None, reference=None):
        specs = self.root / SPECS
        if manifest is not None:
            if reference:
                manifest = {**manifest, "$schema": reference}
            (specs / "website.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if schema_text is None:
            (specs / "website.schema.json").unlink()
        elif schema_text != "keep":
            (specs / "website.schema.json").write_text(schema_text)
        if old_schema is not None:
            (specs / OLD).write_text(old_schema)

    def commands(self, state):
        c = self.tmpdir / "content.astro"
        c.write_text(NEW)
        return [("preflight", ("preflight", "--root", str(self.root), self.DOMAIN)),
                ("preflight-no-site", ("preflight", "--root", str(self.root))),
                ("begin", ("begin", "--root", str(self.root), "--site", self.DOMAIN)),
                ("write", ("write", "--state", state, "--content-file", str(c))),
                ("replace", ("replace", "--state", state, "--find", "Sundays", "--replace", "Mondays")),
                ("check", ("check", "--state", state, "--npm", str(self.npm))),
                ("diff", ("diff", "--state", state)),
                ("finish", ("finish", "--state", state)),
                ("finish-visual", ("finish", "--state", state, "--visual-done"))]

    def assert_everything_refused(self, state, needle, label):
        project, area = self.snap(), self.state_files()
        state_bytes = {p.name: p.read_bytes() for p in Path(state).iterdir() if p.is_file()}
        for name, argv in self.commands(state):
            code, d = self.edit(*argv)
            self.assertEqual(code, 1, (label, name, d))
            self.assertNotIn("raw", d, (label, name))
            self.assertIn(d["state"], ("stop", "refused"), (label, name, d))
            self.assertNotEqual(d["state"], "conflict", (label, name))
            self.assertNotIn("Traceback", json.dumps(d))
            if needle:
                self.assertIn(needle, d["message"], (label, name))
            self.assertEqual(self.snap(), project, f"{label}/{name}: project files changed")
            self.assertEqual(self.state_files(), area, f"{label}/{name}: backup area changed")
            self.assertEqual({p.name: p.read_bytes() for p in Path(state).iterdir() if p.is_file()}, state_bytes, f"{label}/{name}: state changed")
        self.assertEqual(self.npm_calls(), [], label)
        self.assertEqual(self.index.read_text(), GOOD, label)

    def test_old_and_loosened_formats_are_refused_by_every_command_before_any_side_effect(self):
        for label, manifest, schema_text in mc.refusal_cases():
            with self.subTest(label):
                st = self.begin()                                   # an open session with a valid project ...
                self.set_project_format(manifest, schema_text)       # ... which then turns invalid
                self.assert_everything_refused(st, NEEDLE[label], label)
                self.restore_project()

    def restore_project(self):
        t.git(self.root, "checkout", "-q", "--", SPECS)

    def test_missing_or_broken_project_schema_copy_is_a_traceable_stop_for_every_command(self):
        for label, schema_text in BROKEN_SCHEMAS:
            with self.subTest(label):
                st = self.begin()
                self.set_project_format(schema_text=schema_text)
                self.assert_everything_refused(st, "website.schema.json", label)
                self.restore_project()

    def test_the_former_project_format_is_diagnosed_before_any_side_effect_in_every_spelling(self):
        for spelling in (OLD, "./" + OLD, "././" + OLD, ".//" + OLD, "a/../" + OLD):
            for with_new in (True, False):
                with self.subTest(spelling=spelling, with_new=with_new):
                    st = self.begin()
                    manifest = json.loads((self.root / SPECS / "website.json").read_text())
                    self.set_project_format(manifest, "keep" if with_new else None, old_schema='{"old": true}\n', reference=spelling)
                    self.assert_everything_refused(st, "old project format", spelling)
                    self.assertIn("no automatic migration", self.edit("preflight", "--root", str(self.root))[1]["message"])
                    self.assertEqual((self.root / SPECS / OLD).read_text(), '{"old": true}\n')        # never read as fallback, changed or removed
                    self.restore_project()
                    (self.root / SPECS / OLD).unlink()

    def test_old_schema_copy_alone_next_to_a_plain_manifest_is_the_old_format(self):
        st = self.begin()
        self.set_project_format(schema_text=None, old_schema=mc.CURRENT_SCHEMA.read_text())
        self.assert_everything_refused(st, "old project format", "old copy only")

    def test_a_leftover_old_schema_file_next_to_the_current_format_is_not_an_error(self):
        (self.root / SPECS / OLD).write_text('{"old": true}\n')
        old = (self.root / SPECS / OLD).read_bytes()
        code, d = self.preflight()
        self.assertEqual((code, d["state"]), (0, "ready"), d)
        st = self.begin()
        self.assertEqual(self.write(st, NEW)[1]["state"], "written")
        self.assertEqual(self.check(st)[1]["state"], "checked")
        self.assertEqual(self.finish(st, visual=True)[1]["outcome"], "complete")
        self.assertEqual((self.root / SPECS / OLD).read_bytes(), old)

    def test_the_manifest_and_the_schema_copy_are_never_written_by_a_full_run(self):
        names = ("website.json", "website.schema.json", "website.managed.json")
        before = {n: (self.root / SPECS / n).read_bytes() for n in names}
        st = self.begin()
        self.write(st, NEW)
        self.check(st)
        self.finish(st, visual=True)
        self.assertEqual({n: (self.root / SPECS / n).read_bytes() for n in names}, before)

    def test_a_valid_format_reaches_the_build_step(self):
        st = self.begin()
        self.write(st, NEW)
        self.assertEqual(self.check(st)[1]["state"], "checked")
        self.assertEqual(self.npm_calls(), ["run build", "run check"])


class FormatDiagnosisIsNotAConflict(EditCase):
    def test_a_manifest_that_turns_invalid_does_not_poison_the_session(self):
        st = self.begin()
        manifest = self.root / SPECS / "website.json"
        original = manifest.read_text()
        manifest.write_text("{broken")
        code, d = self.write(st, NEW)
        self.assertEqual((code, d["state"]), (1, "refused"))
        self.assertFalse(json.loads((Path(st) / "index.json").read_text())["conflict"])
        manifest.write_text(original)                                   # the person fixes the manifest: the same session continues
        self.assertEqual(self.write(st, NEW)[1]["state"], "written")
        self.assertEqual(self.check(st)[1]["state"], "checked")
        self.assertEqual(self.finish(st, visual=True)[1]["outcome"], "complete")

    def test_an_unknown_or_ambiguous_site_keeps_its_exit_codes(self):
        self.assertEqual(self.preflight("nope.example")[0], 1)
        self.make_site("other.test")
        code, d = self.preflight()
        self.assertEqual((code, "ask" in d), (2, True))


if __name__ == "__main__":
    import unittest
    unittest.main()
