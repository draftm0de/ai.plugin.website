"""The former project format (schema file `zyris-website.schema.json`) is refused by every optimize entry point with a concrete
diagnosis BEFORE any side effect (build, report, work list, lock, npm). No migration, no fallback, no reading, changing or
removing of the old file. A leftover old file next to the correct new format is not an error. The detection is the shared one."""
import unittest

from tests.support import manifest_contract as mc
from tests.support.contract_cases import ContractMixin
from tests.integration.optimize.test_manifest_contract import A, W, SITE, entries

OLD = "zyris-website.schema.json"
SPELLINGS = (OLD, "./" + OLD, "././" + OLD, ".//" + OLD, "a/../" + OLD)


def project(reference, with_new=True, with_old=False):
    root = mc.make_project({**mc.good_manifest(), "$schema": reference}, mc.CURRENT_SCHEMA.read_text() if with_new else None)
    if with_old:
        (root / ".project" / "specs" / OLD).write_text('{"old": true}\n')
    return root


class FormerFormat(ContractMixin, unittest.TestCase):
    FORBIDDEN = (".project/reports", "sites/site.example/dist")

    def refused(self, root):
        before = mc.snapshot(root)
        for script, build in entries(self.sb):
            code, out = self.sb.run(script, *build(root))
            self.assertEqual(code, 1, (script, build(root)[0], out))
            self.assertTrue(out.lstrip().startswith("STOP"), out)
            self.assertIn("old project format", out)
            self.assertIn("no automatic migration", out)
            self.assertNotIn("Traceback", out)
            self.assertEqual(mc.snapshot(root), before)
            self.assertEqual(self.sb.npm_calls(), [])
            for rel in self.FORBIDDEN:
                self.assertFalse((root / rel).exists(), rel)

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
        code, out = self.sb.run(A, "audit", "--site", SITE, "--root", str(root), "--npm", str(self.sb.bin / "npm"))
        self.assertEqual(code, 1, out)
        self.assertIn("old project format", out)
        self.assertEqual(mc.snapshot(root), before)
        self.assertEqual(self.sb.npm_calls(), [])

    def test_leftover_old_file_next_to_the_current_format_is_untouched_and_not_an_error(self):
        root = project("./website.schema.json", with_new=True, with_old=True)
        old = root / ".project" / "specs" / OLD
        before = old.read_bytes()
        code, out = self.sb.run(W, SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        code, out = self.sb.run(A, "show", "--site", SITE, "--root", str(root))
        self.assertEqual(code, 0, out)
        self.assertEqual(old.read_bytes(), before)

    def test_other_references_are_not_mistaken_for_the_old_one(self):
        for ref in ("./website.schema.json", "https://example.invalid/" + OLD, "../" + OLD, "sub/" + OLD):
            root = project(ref, with_new=True)
            code, out = self.sb.run(A, "show", "--site", SITE, "--root", str(root))
            self.assertNotIn("old project format", out, ref)

    def test_no_second_detection_exists_in_the_optimize_skill(self):
        from tests.support import optimize_helpers as h
        for path in (h.SKILL / "scripts").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("zyris-website.schema", text, path.name)
            self.assertNotIn("legacy", text.lower(), path.name)


if __name__ == "__main__":
    unittest.main()
