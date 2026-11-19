"""Every preview entry point enforces the plugin's manifest contract, whatever the project's schema copy allows, and stops
before any follow-up: no launch entry, no state directory or record, no process, no npm call, no file change."""
import json
import unittest

from tests.support import manifest_contract as mc
from tests.support.contract_cases import ContractMixin

SITE = mc.SITE
C = "preview/scripts/control.py"
P = "preview/scripts/preview.py"
ENTRIES = [
    (P, lambda r: [SITE, "--root", str(r)]),
    (C, lambda r: ["start", SITE, "--root", str(r)]),
    (C, lambda r: ["status", SITE, "--root", str(r)]),
    (C, lambda r: ["stop", SITE, "--root", str(r)]),
    (C, lambda r: ["inspect", SITE, "--expect", "x", "--root", str(r)]),
]


class PreviewManifestContract(ContractMixin, unittest.TestCase):
    FORBIDDEN = (".claude/launch.json", ".claude")

    def test_old_and_loosened_inputs_are_refused_by_every_preview_entry_before_any_follow_up(self):
        self.refusal_matrix(ENTRIES)

    def test_missing_or_broken_project_schema_is_a_traceable_stop(self):
        self.broken_schema_matrix(ENTRIES)

    def test_valid_current_manifest_and_schema_still_work(self):
        root = mc.make_project(mc.good_manifest(), mc.CURRENT_SCHEMA.read_text())
        code, out = self.sb.run(P, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["site"], SITE)
        launch = json.loads((root / ".claude" / "launch.json").read_text())["configurations"][0]
        self.assertEqual(launch["port"], 4500)

    def test_a_foreign_older_project_schema_is_left_alone_and_does_not_decide_the_contract(self):
        root = mc.make_project(mc.good_manifest(), mc.OLDER_SCHEMA.read_text())
        schema = root / ".project" / "specs" / "website.schema.json"
        before = schema.read_bytes()
        code, out = self.sb.run(P, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)                                 # judged by the plugin schema, not by the stale copy
        self.assertEqual(schema.read_bytes(), before)                  # never rewritten by preview


if __name__ == "__main__":
    unittest.main()
