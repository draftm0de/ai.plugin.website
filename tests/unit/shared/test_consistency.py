"""Unit tests of the version-2 consistency contract (site_common/consistency.py): reads text only, never executes code."""
import tempfile
import unittest
from pathlib import Path

from tests.support import setup_paths  # noqa: F401  (sys.path)
from site_common import consistency as c


class AstroConfigTests(unittest.TestCase):
    def test_site_present_absent_and_comments_are_not_configuration(self):
        self.assertEqual(c.astro_site("export default defineConfig({ site: 'https://a.example', });"), ("site", "https://a.example"))
        self.assertEqual(c.astro_site('export default defineConfig({\n  site: "https://a.example"\n});'), ("site", "https://a.example"))
        self.assertEqual(c.astro_site("export default defineConfig({\n});\n"), ("site", None))
        text = "// site: 'https://old.example'\n/* site: 'https://x.example', */\nexport default defineConfig({\n  // site: 'https://y.example',\n});\n"
        self.assertEqual(c.astro_site(text), ("site", None))

    def test_slashes_inside_strings_are_not_comments(self):
        self.assertEqual(c.astro_site("export default defineConfig({ site: 'https://a.example//x', });"), ("site", "https://a.example//x"))

    def test_dynamic_or_unrecognised_configuration_is_unchecked_not_domainless(self):
        for text in ("export default defineConfig({ site: process.env.SITE });",
                     "export default defineConfig({ site: `https://${host}` });",
                     "export default defineConfig({ ...base });",
                     "export default defineConfig(base);",
                     "const a = defineConfig({}); export default defineConfig({});",
                     "export default defineConfig({ site: 'https://a.example', site: 'https://b.example' });",
                     "export default defineConfig({ site: 'https://a' + '.example' });",
                     "export default defineConfig({ site: 'a\\x62' });"):
            self.assertEqual(c.astro_site(text)[0], "unchecked", text)

    def test_the_exported_object_is_judged_not_a_stray_defineconfig(self):
        stray = "const unused = defineConfig({ site: 'https://stray.example' });\n"
        self.assertEqual(c.astro_site(stray + "export default { site: 'https://real.example' };")[0], "unchecked")
        self.assertEqual(c.astro_site(stray + "export default defineConfig({});")[0], "unchecked")      # two calls: not told apart
        self.assertEqual(c.astro_site("export default { site: 'https://real.example' };"), ("site", "https://real.example"))
        self.assertEqual(c.astro_site("export default {};"), ("site", None))

    def test_named_export_is_resolved_only_when_unambiguous(self):
        self.assertEqual(c.astro_site("const cfg = defineConfig({ site: 'https://a.example' });\nexport default cfg;"), ("site", "https://a.example"))
        self.assertEqual(c.astro_site("const cfg = { site: 'https://a.example' };\nexport default cfg;"), ("site", "https://a.example"))
        for text in ("const cfg = defineConfig({});\nexport default other;",
                     "const cfg = defineConfig({});\ncfg = {};\nexport default cfg;",
                     "const cfg = defineConfig({});\nconst cfg = {};\nexport default cfg;",
                     "export default makeConfig(defineConfig({}));",
                     "const cfg = load();\nexport default cfg;",
                     "export default defineConfig({});\nexport default defineConfig({ site: 'https://z.example' });",
                     "const cfg = defineConfig({});\nexport { cfg as default };",
                     "module.exports = defineConfig({ site: 'https://a.example' });"):
            self.assertEqual(c.astro_site(text)[0], "unchecked", text)

    def test_mutations_of_the_exported_object_are_never_reliably_domainless(self):
        for body in ("cfg.site = 'https://other.example';", "cfg['site'] = 'https://other.example';", "cfg[\"si\" + \"te\"] = 'https://other.example';",
                     "Object.assign(cfg, { site: 'https://other.example' });", "Object.defineProperty(cfg, 'site', { value: 'https://other.example' });",
                     "({ ...cfg, site: 'x' });", "setSite(cfg);", "[cfg].forEach((c) => (c.site = 'u'));", "with (cfg) { site = 'u'; }",
                     "const { site } = cfg;", "cfg.site ??= 'https://other.example';"):
            text = f"const cfg = {{}};\n{body}\nexport default cfg;\n"
            self.assertEqual(c.astro_site(text)[0], "unchecked", body)
            text = f"const cfg = defineConfig({{}});\n{body}\nexport default cfg;\n"
            self.assertEqual(c.astro_site(text)[0], "unchecked", body)

    def test_expressions_after_the_object_literal_make_it_unverifiable(self):
        for text in ("export default defineConfig({}).site;", "export default defineConfig({}), other();", "export default {}.site;",
                     "export default {} || { site: 'https://other.example' };", "export default defineConfig({}) ?? other;",
                     "const cfg = defineConfig({}).extend({ site: 'u' });\nexport default cfg;",
                     "const cfg = {}\n(function () {})();\nexport default cfg;", "export default {} + 1;"):
            self.assertEqual(c.astro_site(text)[0], "unchecked", text)
        for text in ("export default {};", "export default {}\n", "export default defineConfig({})\nconst later = 1;\n",
                     "export default defineConfig({});\ncfg.site = 'unrelated';"):
            self.assertEqual(c.astro_site(text), ("site", None), text)

    def test_nested_site_keys_are_not_the_top_level_site(self):
        self.assertEqual(c.astro_site("export default defineConfig({ vite: { site: 'https://z.example' } });"), ("site", None))


class LibSiteTests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(c.lib_site("export const SITE: string | null = null;"), ("site", None))
        self.assertEqual(c.lib_site("export const SITE = 'https://a.example';"), ("site", "https://a.example"))
        self.assertEqual(c.lib_site('export const SITE: string | null = "https://a.example";'), ("site", "https://a.example"))
        self.assertEqual(c.lib_site("// export const SITE = 'https://x.example';\nexport const SITE = null;"), ("site", None))

    def test_unrecognised_is_unchecked(self):
        for text in ("export const SITE = process.env.X;", "export const SITE = `https://${h}`;", "const X = 1;",
                     "export const SITE = 'https://a.example';\nSITE = 'https://b.example';",
                     "export const SITE = null; export const SITE = null;"):
            self.assertEqual(c.lib_site(text)[0], "unchecked", text)


class CheckTextsTests(unittest.TestCase):
    CONFIG_WITH = "export default defineConfig({ site: 'https://a.example', });"
    LIB_WITH = "export const SITE: string | null = 'https://a.example';"

    def test_match_and_conflicts(self):
        self.assertEqual(c.check_texts("a.example", self.CONFIG_WITH, self.LIB_WITH), {"conflicts": [], "unverifiable": []})
        self.assertEqual(c.check_texts(None, "export default defineConfig({});", "export const SITE = null;"), {"conflicts": [], "unverifiable": []})
        found = c.check_texts(None, self.CONFIG_WITH, self.LIB_WITH)
        self.assertEqual(len(found["conflicts"]), 2)
        self.assertIn("no site URL", found["conflicts"][0])
        found = c.check_texts("b.example", self.CONFIG_WITH, self.LIB_WITH)
        self.assertEqual(len(found["conflicts"]), 2)
        self.assertIn("'https://b.example'", found["conflicts"][0])

    def test_unchecked_is_neither_conflict_nor_match(self):
        found = c.check_texts("a.example", "export default defineConfig({ site: process.env.S });", self.LIB_WITH)
        self.assertEqual(found["conflicts"], [])
        self.assertEqual(len(found["unverifiable"]), 1)


class MutatedConfigFileTests(unittest.TestCase):
    def test_a_mutated_config_is_neither_domainless_nor_a_match_for_a_domain(self):
        root = Path(tempfile.mkdtemp()).resolve()
        site = root / "sites" / "s"
        (site / "src" / "lib").mkdir(parents=True)
        (site / "astro.config.mjs").write_text("const cfg = {};\ncfg.site = 'https://other.example';\nexport default cfg;\n")
        lib = site / "src" / "lib" / "site.ts"
        for comp, value in (({"name": "s", "path": "sites/s", "type": "astro-static"}, "null"),
                            ({"name": "s", "path": "sites/s", "type": "astro-static", "domain": "demo-a.com"}, "'https://demo-a.com'")):
            lib.write_text(f"export const SITE: string | null = {value};\n")
            found = c.check(root, comp)
            self.assertEqual(found["conflicts"], [], found)
            self.assertEqual(len(found["unverifiable"]), 1, found)
            self.assertIn("not reliably checkable", found["unverifiable"][0])


class FileAccessTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.outside = Path(tempfile.mkdtemp()).resolve()
        self.site = self.root / "sites" / "s"
        (self.site / "src" / "lib").mkdir(parents=True)
        self.comp = {"name": "s", "path": "sites/s", "type": "astro-static"}

    def test_missing_files_are_unverifiable_not_domainless(self):
        found = c.check(self.root, {**self.comp, "domain": "a.example"})
        self.assertEqual(found["conflicts"], [])
        self.assertEqual(len(found["unverifiable"]), 2)

    def test_symlinked_file_is_not_read(self):
        (self.outside / "site.ts").write_text("export const SITE = 'https://evil.example';\n")
        (self.site / "src" / "lib" / "site.ts").symlink_to(self.outside / "site.ts")
        found = c.check(self.root, {**self.comp})
        self.assertEqual(found["conflicts"], [])                     # had it been read, 'evil.example' would contradict "no domain"
        self.assertTrue(any("symlink" in text for text in found["unverifiable"]), found)
        self.assertEqual((self.outside / "site.ts").read_text(), "export const SITE = 'https://evil.example';\n")

    def test_symlinked_parent_directories_are_not_followed(self):
        real = self.outside / "lib"
        real.mkdir()
        (real / "site.ts").write_text("export const SITE = 'https://evil.example';\n")
        (self.site / "src" / "lib").rmdir()
        (self.site / "src" / "lib").symlink_to(real)
        self.assertEqual(c.check(self.root, self.comp)["conflicts"], [])
        # and a symlinked site folder / sites folder
        other = self.root / "linked"
        other.symlink_to(self.outside)
        (self.outside / "src" / "lib").mkdir(parents=True)
        (self.outside / "src" / "lib" / "site.ts").write_text("export const SITE = 'https://evil.example';\n")
        found = c.check(self.root, {**self.comp, "path": "linked"})
        self.assertEqual(found["conflicts"], [])
        self.assertTrue(any("symlink" in text for text in found["unverifiable"]))

    def test_oversized_and_non_regular_files_are_not_read(self):
        big = self.site / "src" / "lib" / "site.ts"
        big.write_text("export const SITE = null;\n" + " " * (c.MAX_BYTES + 1))
        found = c.check(self.root, self.comp)
        self.assertTrue(any("1 MiB" in text for text in found["unverifiable"]), found)


if __name__ == "__main__":
    unittest.main()
