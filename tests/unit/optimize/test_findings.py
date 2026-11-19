"""The evaluation adapter for the output of the site's check scripts: shape, exit-code agreement, classification, identity.

Output samples are fictional. The message formats of the real check scripts that `setup` ships are compared in
`test_findings_templates.py`; neither proves equality with any real website's scripts.
"""
import unittest

from tests.support import optimize_helpers  # noqa: F401  (puts the skill's scripts and site_common on sys.path)
import findings as fx


SEO_WARNINGS = """
> alpha-site@0.0.1 seo:check
> node scripts/seo-check.mjs

Checked 20 pages.

Warnings (2):
- /projects/alpha-metrics.html: description is short (67, aim for 120 to 160)
- /projects/beta-metrics.html: description is short (64, aim for 120 to 160)

No errors.
"""


class ParseTests(unittest.TestCase):
    def test_warning_output_with_exit_zero(self):
        p = fx.parse_output(SEO_WARNINGS, 0)
        self.assertEqual(p["status"], "ok")
        self.assertEqual(p["pages"], 20)
        self.assertEqual(len(p["warnings"]), 2)
        self.assertEqual(p["errors"], [])

    def test_errors_with_exit_one(self):
        out = "Checked 3 pages.\n\nErrors (1):\n- /a.html: missing meta description\n"
        p = fx.parse_output(out, 1)
        self.assertEqual(p["status"], "ok")
        self.assertEqual(p["errors"], ["/a.html: missing meta description"])

    def test_warnings_and_errors_in_one_output_stay_separate(self):
        out = "Checked 3 pages.\n\nWarnings (1):\n- /a.html: description is short (3, aim for 120 to 160)\n\nErrors (1):\n- /b.html: missing <title>\n"
        p = fx.parse_output(out, 1)
        self.assertEqual((p["status"], len(p["warnings"]), len(p["errors"])), ("ok", 1, 1))

    def test_unknown_shape_is_unparsed_not_clean(self):
        for text, code in [("all good\n", 0), ("", 0), ("Checked 1 pages.\n", 0)]:
            self.assertEqual(fx.parse_output(text, code)["status"], "unparsed", (text, code))

    def test_exit_code_must_agree_with_text(self):
        clean = "Checked 1 pages.\n\nNo errors.\n"
        self.assertEqual(fx.parse_output(clean, 1)["status"], "unparsed")      # exit 1 without listed errors
        bad = "Checked 1 pages.\n\nErrors (1):\n- /a: x\n"
        self.assertEqual(fx.parse_output(bad, 0)["status"], "unparsed")        # errors listed but exit 0
        self.assertEqual(fx.parse_output(clean, 2)["status"], "unparsed")      # undefined exit code
        self.assertEqual(fx.parse_output(clean, None)["status"], "unparsed")

    def test_announced_count_must_match(self):
        text = "Checked 1 pages.\n\nWarnings (3):\n- /a: x\n\nNo errors.\n"
        self.assertEqual(fx.parse_output(text, 0)["status"], "unparsed")

    def test_exit_zero_needs_the_no_errors_line(self):
        self.assertEqual(fx.parse_output("Checked 1 pages.\n", 0)["status"], "unparsed")

    def test_multiline_message_is_one_item(self):
        text = 'Checked 1 pages.\n\nErrors (1):\n- /a: image without alt: <img\n  src="x">\n'
        p = fx.parse_output(text, 1)
        self.assertEqual(p["status"], "ok")
        self.assertEqual(len(p["errors"]), 1)

    def test_undecodable_garbage_is_unparsed(self):
        self.assertEqual(fx.parse_output("���", 0)["status"], "unparsed")


class ClassifyTests(unittest.TestCase):
    def test_identity_ignores_numbers_in_message(self):
        a = fx.classify("seo", fx.WARNING, "/p.html: description is short (67, aim for 120 to 160)")
        b = fx.classify("seo", fx.WARNING, "/p.html: description is short (90, aim for 120 to 160)")
        self.assertEqual(fx.identity_key(a), fx.identity_key(b))
        self.assertEqual(a["criterion"], "seo.description-too-short")
        self.assertEqual(a["location"], "/p.html")

    def test_different_page_is_different_identity(self):
        a = fx.classify("seo", fx.WARNING, "/p.html: description is short (67, aim for 120 to 160)")
        b = fx.classify("seo", fx.WARNING, "/q.html: description is short (67, aim for 120 to 160)")
        self.assertNotEqual(fx.identity_key(a), fx.identity_key(b))

    def test_unknown_message_stays_visible(self):
        r = fx.classify("a11y", fx.ERROR, "/p.html: brand new rule 12 failed")
        self.assertEqual(r["criterion"], "a11y.unclassified")
        self.assertIn("brand new rule", r["message"])
        self.assertEqual(r["detail"], "brand new rule # failed")

    def test_global_and_duplicate_messages(self):
        r = fx.classify("seo", fx.ERROR, "missing /robots.txt")
        self.assertEqual((r["criterion"], r["location"], r["detail"]), ("seo.site-file-missing", fx.GLOBAL, "/robots.txt"))
        d = fx.classify("seo", fx.ERROR, 'duplicate title/description "Hi" on: /b.html, /a.html')
        self.assertEqual((d["criterion"], d["location"]), ("seo.duplicate-title-description", "/a.html, /b.html"))

    def test_same_identity_is_merged_with_count(self):
        parsed = {"errors": ["/p: button without accessible name", "/p: button without accessible name"], "warnings": []}
        merged = fx.collect("a11y", parsed)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["occurrences"], 2)

    def test_error_and_warning_classes_are_kept_apart(self):
        merged = fx.collect("seo", {"errors": ["/a: missing meta description"], "warnings": ["/a: description is short (3, aim for 120 to 160)"]})
        self.assertEqual({m["criterion"]: m["class"] for m in merged},
                         {"seo.description-missing": fx.ERROR, "seo.description-too-short": fx.WARNING})

    def test_every_pattern_criterion_has_catalog_entry(self):
        for _, _, criterion, _ in fx.PATTERNS:
            self.assertIn(criterion, fx.CATALOG)
        self.assertIn("seo.duplicate-title-description", fx.CATALOG)

    def test_the_adapter_adds_no_editorial_class_to_machine_output(self):
        parsed = fx.parse_output("Checked 1 pages.\n\nErrors (1):\n- /a: anything at all\n", 1)
        self.assertEqual({r["class"] for r in fx.collect("seo", parsed)}, {fx.ERROR})


class SourceFileTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.root = Path(tempfile.mkdtemp()).resolve()
        pages = self.root / "sites" / "s" / "src" / "pages"
        pages.mkdir(parents=True)
        (pages / "index.astro").write_text("x")
        (pages / "about.astro").write_text("x")
        self.addCleanup(__import__("shutil").rmtree, self.root, True)

    def test_only_existing_files_are_named(self):
        self.assertEqual(fx.source_files(self.root, "sites/s", "/"), ["sites/s/src/pages/index.astro"])
        self.assertEqual(fx.source_files(self.root, "sites/s", "/about.html"), ["sites/s/src/pages/about.astro"])
        self.assertEqual(fx.source_files(self.root, "sites/s", "/missing.html"), [])
        self.assertEqual(fx.source_files(self.root, "sites/s", fx.GLOBAL), [])


if __name__ == "__main__":
    unittest.main()
