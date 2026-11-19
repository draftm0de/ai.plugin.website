"""The setup entry point enforce the plugin's manifest contract, whatever the project's schema copy allows."""
import json
import sys
import unittest
from pathlib import Path

from tests.support import manifest_contract as mc
from tests.support.contract_cases import ContractMixin, NEEDLE

SITE = mc.SITE
S = "setup/scripts/site_setup.py"
ENTRIES = [
    (S, lambda r: ["verify", SITE, "--root", str(r)]),
    (S, lambda r: ["create", "other.example", "--type", "astro-static", "--root", str(r)]),
    (S, lambda r: ["plan", "create", "other.example", "--type", "astro-static", "--root", str(r)]),
    (S, lambda r: ["adopt", SITE, "--root", str(r)]),
]


class SetupManifestContract(ContractMixin, unittest.TestCase):
    START = "setup verify"
    FORBIDDEN = ("sites/other.example", ".project/specs/zyris-website.managed.json", ".tmp")

    def test_old_and_loosened_inputs_are_refused_by_every_setup_entry_before_install_build_or_write(self):
        for label, manifest, schema_text in mc.refusal_cases():
            root = mc.make_project(manifest, schema_text)
            before = mc.snapshot(root)
            for script, build in ENTRIES:
                code, out = self.sb.run(script, *build(root))
                # create/plan/adopt may name the schema conflict or the invalid manifest first; both are refusals with a cause
                self.assertEqual(code, 1, (script, build(root)[0], label, out))
                self.assertTrue(any(w in out for w in (NEEDLE[label], "conflict", "invalid")), (label, out))
                self.assertNotIn("Traceback", out)
                self.assertEqual(mc.snapshot(root), before, f"{build(root)[0]} / {label}: files changed")
                self.assertEqual(self.sb.npm_calls(), [], f"{build(root)[0]} / {label}: npm was called")
                for rel in self.FORBIDDEN:
                    self.assertFalse((root / rel).exists(), (label, rel))

    def test_verify_judges_by_the_plugin_schema_not_by_the_loosened_copy(self):
        for label, manifest, schema_text in mc.refusal_cases():
            if "loosened" not in label:
                continue
            root = mc.make_project(manifest, schema_text)
            code, out = self.sb.run(S, "verify", SITE, "--root", str(root))
            self.assertEqual(code, 1, label)
            self.assertIn("invalid", out, label)
            self.assertIn(NEEDLE[label], out, label)
            self.assertEqual(self.sb.npm_calls(), [], label)

    def test_missing_or_broken_project_schema_is_a_traceable_stop_for_verify(self):
        self.broken_schema_matrix([ENTRIES[0]])

    def test_existing_foreign_schema_is_a_conflict_for_create_and_is_never_changed(self):
        for label, schema_text in (("older foreign", mc.OLDER_SCHEMA.read_text()), ("not json", "{not json"), ("not an object", "[]\n"),
                                   ("loosened", mc.loosened_schema_text())):
            root = mc.make_project(mc.good_manifest(), schema_text)
            before = mc.snapshot(root)
            code, out = self.sb.run(S, "create", "other.example", "--type", "astro-static", "--root", str(root))
            self.assertEqual(code, 1, (label, out))
            self.assertIn("conflict", out, label)
            self.assertIn("never replaced automatically", out, label)
            self.assertEqual(mc.snapshot(root), before, label)

    def test_valid_current_manifest_and_schema_still_verify_and_plan(self):
        root = mc.make_project(mc.good_manifest(), mc.CURRENT_SCHEMA.read_text())
        code, out = self.sb.run(S, "plan", "create", "other.example", "--type", "astro-static", "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.sb.npm_calls(), [])
        code, out = self.sb.run(S, "verify", SITE, "--root", str(root), "--json")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["state"], "verified")
        self.assertTrue(any("build" in c for c in self.sb.npm_calls()))

    def test_verify_with_a_foreign_older_schema_copy_uses_the_plugin_schema_and_leaves_the_copy(self):
        root = mc.make_project(mc.good_manifest(), mc.OLDER_SCHEMA.read_text())
        schema = root / ".project" / "specs" / "website.schema.json"
        before = schema.read_bytes()
        code, out = self.sb.run(S, "verify", SITE, "--root", str(root), "--json")
        self.assertEqual(code, 0, out)
        self.assertEqual(schema.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
