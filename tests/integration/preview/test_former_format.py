"""The former project format (schema file `zyris-website.schema.json`) is refused by every preview entry point with a concrete
diagnosis BEFORE any side effect (launch entry, state directory, record, process, npm). No migration, no fallback, no reading,
changing or removing of the old file. A leftover old file next to the correct new format is not an error."""
import json
import unittest

from tests.support import manifest_contract as mc
from tests.support.contract_cases import ContractMixin

SITE = mc.SITE
C = "preview/scripts/control.py"
P = "preview/scripts/preview.py"
OLD = "zyris-website.schema.json"
ENTRIES = [
    (P, lambda r: [SITE, "--root", str(r)]),
    (C, lambda r: ["start", SITE, "--root", str(r)]),
    (C, lambda r: ["status", SITE, "--root", str(r)]),
    (C, lambda r: ["stop", SITE, "--root", str(r)]),
    (C, lambda r: ["inspect", SITE, "--expect", "x", "--root", str(r)]),
]
SPELLINGS = (OLD, "./" + OLD, "././" + OLD, ".//" + OLD, "a/../" + OLD)


def project(reference, with_new=True, with_old=False):
    root = mc.make_project({**mc.good_manifest(), "$schema": reference}, mc.CURRENT_SCHEMA.read_text() if with_new else None)
    specs = root / ".project" / "specs"
    if with_old:
        (specs / OLD).write_text('{"old": true}\n')
    return root


class FormerFormat(ContractMixin, unittest.TestCase):
    FORBIDDEN = (".claude",)

    def refused(self, root):
        before = mc.snapshot(root)
        for script, build in ENTRIES:
            code, out = self.sb.run(script, *build(root))
            self.assertEqual(code, 1, (script, build(root)[0], out))
            self.assertTrue(out.lstrip().startswith("STOP"), out)
            self.assertIn("old project format", out)
            self.assertIn("no automatic migration", out)
            self.assertNotIn("Traceback", out)
            self.assertEqual(mc.snapshot(root), before)
            self.assertEqual(self.sb.npm_calls(), [])
            self.assertEqual(self.sb.state_files(), [])
            self.assertFalse((root / ".claude").exists())

    def test_every_local_spelling_of_the_old_reference_is_refused_by_all_entries_with_or_without_the_new_copy(self):
        for spelling in SPELLINGS:
            for with_new in (True, False):
                with self.subTest(spelling=spelling, with_new=with_new):
                    self.refused(project(spelling, with_new=with_new, with_old=True))

    def test_old_schema_copy_alone_is_the_old_format_even_with_a_plain_manifest(self):
        root = mc.make_project(mc.good_manifest(), None)
        (root / ".project" / "specs" / OLD).write_text(mc.CURRENT_SCHEMA.read_text())
        self.refused(root)

    def test_the_old_file_is_never_used_as_fallback_for_a_missing_new_copy(self):
        root = mc.make_project({**mc.good_manifest(), "$schema": "./website.schema.json"}, None)
        (root / ".project" / "specs" / OLD).write_text(mc.CURRENT_SCHEMA.read_text())
        before = mc.snapshot(root)
        code, out = self.sb.run(C, "start", SITE, "--root", str(root))
        self.assertEqual(code, 1, out)
        self.assertIn("old project format", out)
        self.assertEqual(mc.snapshot(root), before)

    def test_leftover_old_file_next_to_the_current_format_is_untouched_and_not_an_error(self):
        root = project("./website.schema.json", with_new=True, with_old=True)
        old = root / ".project" / "specs" / OLD
        before = old.read_bytes()
        code, out = self.sb.run(P, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(old.read_bytes(), before)

    def test_other_references_are_not_mistaken_for_the_old_one(self):
        for ref in ("./website.schema.json", "https://example.invalid/" + OLD, "../" + OLD, "sub/" + OLD):
            root = project(ref, with_new=True)
            code, out = self.sb.run(P, SITE, "--root", str(root))
            self.assertNotIn("old project format", out, ref)


if __name__ == "__main__":
    unittest.main()
