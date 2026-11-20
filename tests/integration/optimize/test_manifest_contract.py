"""Every optimize entry point enforces the plugin's manifest contract, whatever the project's schema copy allows, and stops
before any follow-up: no build, no report, no work list, no lock, no npm call, no file change."""
import json
import unittest

from tests.support import manifest_contract as mc
from tests.support.contract_cases import ContractMixin

SITE = mc.SITE
A = "optimize/scripts/audit.py"
W = "_shared/scripts/which_site.py"


def entries(sb):
    npm = str(sb.bin / "npm")
    dummy = str(sb.dir / "proposals.json")
    (sb.dir / "proposals.json").write_text("{}\n")
    return [
        (W, lambda r: [SITE, "--root", str(r)]),
        (A, lambda r: ["audit", "--site", SITE, "--root", str(r), "--npm", npm]),
        (A, lambda r: ["show", "--site", SITE, "--root", str(r)]),
        (A, lambda r: ["decide", "SEO-001", "--status", "approved", "--site", SITE, "--root", str(r)]),
        (A, lambda r: ["apply", "SEO-001", "--site", SITE, "--root", str(r), "--npm", npm]),
        (A, lambda r: ["propose", "--proposals", dummy, "--site", SITE, "--root", str(r)]),
    ]


class OptimizeManifestContract(ContractMixin, unittest.TestCase):
    FORBIDDEN = (".project/reports", "sites/site.example/dist")

    def test_old_and_loosened_inputs_are_refused_by_every_optimize_entry_before_build_or_report(self):
        self.refusal_matrix(entries(self.sb))

    def test_missing_or_broken_project_schema_is_a_traceable_stop(self):
        self.broken_schema_matrix(entries(self.sb))

    def test_valid_current_manifest_and_schema_still_work(self):
        root = mc.make_project(mc.good_manifest(), mc.CURRENT_SCHEMA.read_text())
        code, out = self.sb.run(W, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["type"], "astro-static")
        code, out = self.sb.run(A, "audit", "--site", SITE, "--root", str(root), "--npm", str(self.sb.bin / "npm"))
        self.assertNotIn("is invalid", out)                           # the manifest passed; what the fake npm yields is not the point here
        self.assertTrue(self.sb.npm_calls(), "a valid manifest must reach the build step")

    def test_a_foreign_older_project_schema_is_left_alone_and_does_not_decide_the_contract(self):
        root = mc.make_project(mc.good_manifest(), mc.OLDER_SCHEMA.read_text())
        schema = root / ".project" / "specs" / "website.schema.json"
        before = schema.read_bytes()
        code, out = self.sb.run(W, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        code, out = self.sb.run(A, "show", "--site", SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(schema.read_bytes(), before)

    def test_an_unknown_explicit_site_is_a_stop_and_an_ambiguous_one_asks(self):
        root = mc.make_project(mc.good_manifest(), mc.CURRENT_SCHEMA.read_text())
        code, out = self.sb.run(A, "show", "--site", "nope.example", "--root", str(root))
        self.assertEqual(code, 1, out)
        self.assertTrue(out.startswith("STOP:"), out)
        two = {"version": 2, "components": [mc.good_manifest()["components"][0], {**mc.good_manifest()["components"][0], "name": "other.example", "path": "sites/other.example", "port": 4501}]}
        root = mc.make_project(two, mc.CURRENT_SCHEMA.read_text())
        code, out = self.sb.run(A, "show", "--root", str(root))
        self.assertEqual(code, 2, out)
        self.assertEqual({o["name"] for o in json.loads(out)["options"]}, {SITE, "other.example"})
        self.assertEqual(self.sb.npm_calls(), [])


if __name__ == "__main__":
    unittest.main()
