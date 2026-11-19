"""The adapter against the message formats of the check scripts that `setup` ships (public format basis).

The templates `seo-check.mjs` and `a11y-check.mjs` are read as *text* (no Node, no execution). Every message template found in
them is turned into a sample message and must be classified by the adapter; every adapter pattern must match some template;
outputs assembled in the templates' own console formats must parse. This shows the adapter fits the shipped templates' formats.
It does NOT prove equality with the check scripts of any real website, and the templates were not executed (NOT RUN).
"""
import re
import unittest
from pathlib import Path

from tests.support import optimize_helpers as helpers
import findings as fx

TEMPLATES = helpers.ROOT / "skills" / "setup" / "templates" / "astro-static" / "scripts"
CALL = re.compile(r"\b(err|warn|errors\.push|warnings\.push)\((`(?:[^`\\]|\\.)*`|'(?:[^'\\]|\\.)*')\)")
EXPR = re.compile(r"\$\{([^}]*)\}")
SAMPLES = {"p": "og:title", "name": "/p.html", "rel(css)": "/assets/x.css", "m[1]": "12px"}


def messages(script, family):
    """(family, class, sample message) for every err/warn/push call in the script text."""
    text = (TEMPLATES / script).read_text(encoding="utf-8")
    out = []
    for call, literal in CALL.findall(text):
        body = literal[1:-1]
        if "${m}" in body:                      # the helper definitions `const err = (m) => errors.push(`${name}: ${m}`)`: no message of their own
            continue
        body = EXPR.sub(lambda m: SAMPLES.get(m.group(1).strip(), "7"), body)
        body = body.replace("\\n", "\n")
        if call in ("err", "warn"):
            body = f"/p.html: {body}"          # the helper prefixes the page name
        out.append((family, fx.WARNING if call.startswith("warn") else fx.ERROR, body))
    return out


class TemplateFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = messages("seo-check.mjs", "seo") + messages("a11y-check.mjs", "a11y")

    def test_the_templates_were_found_and_yield_messages(self):
        self.assertTrue((TEMPLATES / "seo-check.mjs").is_file() and (TEMPLATES / "a11y-check.mjs").is_file())
        self.assertGreaterEqual(len([i for i in self.items if i[0] == "seo"]), 18)
        self.assertGreaterEqual(len([i for i in self.items if i[0] == "a11y"]), 15)

    def test_every_template_message_is_classified_by_the_adapter(self):
        for family, cls, message in self.items:
            raw = fx.classify(family, cls, message)
            self.assertFalse(raw["criterion"].endswith("unclassified"), (family, message))
            self.assertTrue(raw["criterion"].startswith(family + "."), (family, message, raw["criterion"]))
            self.assertIn(raw["criterion"], fx.CATALOG, message)

    def test_every_adapter_pattern_matches_some_template_message(self):
        hit = set()
        for family, cls, message in self.items:
            hit.add(fx.classify(family, cls, message)["criterion"])
        for family, _, criterion, _ in fx.PATTERNS:
            self.assertIn(criterion, hit, f"adapter criterion {criterion} matches no message of the shipped template (stale pattern?)")
        self.assertIn("seo.duplicate-title-description", hit)

    def test_warning_and_error_classes_follow_the_templates(self):
        by = {fx.classify(f, c, m)["criterion"]: c for f, c, m in self.items}
        self.assertEqual(by["seo.description-too-short"], fx.WARNING)
        self.assertEqual(by["seo.page-not-in-sitemap"], fx.WARNING)
        self.assertEqual(by["seo.image-size-missing"], fx.WARNING)
        self.assertEqual(by["seo.title-missing"], fx.ERROR)
        self.assertEqual(by["a11y.image-size-missing"], fx.ERROR)       # an error in the accessibility template, a warning in the SEO one

    def test_console_formats_of_the_templates_parse(self):
        seo = (TEMPLATES / "seo-check.mjs").read_text(encoding="utf-8")
        a11y = (TEMPLATES / "a11y-check.mjs").read_text(encoding="utf-8")
        for needle in ("`Checked ${pages.length} pages.`", "`\\nWarnings (${warnings.length}):\\n- ${warnings.join('\\n- ')}`",
                       "`\\nErrors (${errors.length}):\\n- ${errors.join('\\n- ')}`", "'\\nNo errors.'"):
            self.assertIn(needle, seo, needle)
        for needle in ("`Checked ${pages.length} pages for accessibility.`", "`\\nErrors (${errors.length}):\\n- ${errors.join('\\n- ')}`",
                       "'\\nNo errors. (Contrast, keyboard use and screen reader output still need a manual check.)'"):
            self.assertIn(needle, a11y, needle)
        clean_seo = "Checked 2 pages.\n\nWarnings (1):\n- /a.html: description is short (3, aim for 120 to 160)\n\nNo errors.\n"
        self.assertEqual(fx.parse_output(clean_seo, 0)["status"], "ok")
        failing_seo = "Checked 2 pages.\n\nWarnings (1):\n- /a.html: title is very short (3)\n\nErrors (1):\n- /a.html: missing <title>\n"
        self.assertEqual(fx.parse_output(failing_seo, 1)["status"], "ok")
        clean_a11y = "Checked 2 pages for accessibility.\n\nNo errors. (Contrast, keyboard use and screen reader output still need a manual check.)\n"
        self.assertEqual(fx.parse_output(clean_a11y, 0)["status"], "ok")
        failing_a11y = "Checked 2 pages for accessibility.\n\nErrors (1):\n- /a.html: missing skip link\n"
        self.assertEqual(fx.parse_output(failing_a11y, 1)["status"], "ok")

    def test_the_configuration_error_of_the_seo_template_is_incomplete_never_clean(self):
        """astro.config.mjs without site: the template prints Errors (1) without 'Checked N pages' and exits 1."""
        self.assertIn("astro.config.mjs has no site", (TEMPLATES / "seo-check.mjs").read_text(encoding="utf-8"))
        out = 'Errors (1):\n- astro.config.mjs has no site: "https://..." entry\n'
        self.assertEqual(fx.parse_output(out, 1)["status"], "unparsed")

    def test_package_template_defines_the_separate_check_scripts_the_audit_runs(self):
        text = (helpers.ROOT / "skills" / "setup" / "templates" / "astro-static" / "package.json.tpl").read_text(encoding="utf-8")
        for script in ('"build":', '"seo:check":', '"a11y:check":'):
            self.assertIn(script, text)


if __name__ == "__main__":
    unittest.main()
