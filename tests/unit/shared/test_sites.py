"""Site selection: never guessed; unknown = STOP, ambiguous = ASK with options."""
import unittest
from pathlib import Path
import tempfile

from tests.support import projects as P

P.use_shared_scripts()
from site_common import sites  # noqa: E402
from site_common.errors import Ask, Stop  # noqa: E402


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.root = P.make_project()
        self.components = sites.load(self.root)

    def name(self, **kw):
        return sites.resolve(self.components, self.root, **kw)["component"]["name"]

    def test_defaults_filled(self):
        second = self.components[1]
        self.assertEqual((second["title"], second["port"], second["aliases"]), ("beta.example", 4322, []))

    def test_named_by_exact_alias_title_and_prefix(self):
        for q in ["alpha.example", "first", "Alpha Example", "ALPHA.EXAMPLE"]:
            self.assertEqual(self.name(query=q), "alpha.example", q)
        self.assertEqual(self.name(query="beta"), "beta.example")

    def test_unknown_explicit_site_stops(self):
        with self.assertRaises(Stop):
            self.name(query="nope")

    def test_ambiguous_explicit_site_asks_with_options(self):
        with self.assertRaises(Ask) as ctx:
            self.name(query=".example")
        self.assertEqual(len(ctx.exception.options), 2)

    def test_working_directory_inside_site(self):
        cwd = self.root / "sites" / "beta.example" / "src"
        cwd.mkdir()
        self.assertEqual(self.name(cwd=cwd), "beta.example")

    def test_query_beats_working_directory(self):
        self.assertEqual(self.name(query="alpha", cwd=self.root / "sites" / "beta.example"), "alpha.example")

    def test_last_used_needs_confirmation(self):
        self.assertTrue(sites.resolve(self.components, self.root, last="alpha.example")["confirm"])

    def test_nothing_known_asks_with_all_sites(self):
        with self.assertRaises(Ask) as ctx:
            self.name()
        self.assertEqual([o["name"] for o in ctx.exception.options], ["alpha.example", "beta.example"])

    def test_single_site_needs_no_question(self):
        root = P.make_project(P.ONE_SITE, ("alpha.example",))
        result = sites.resolve(sites.load(root), root)
        self.assertEqual((result["component"]["name"], result["reason"], result["confirm"]), ("alpha.example", "only site", False))

    def test_missing_manifest_stops_and_names_the_setup_skill(self):
        with self.assertRaises(Stop) as ctx:
            sites.load(Path(tempfile.mkdtemp()))
        self.assertIn("setup", str(ctx.exception))
        self.assertNotIn("zyris-website:", str(ctx.exception))

    def test_invalid_manifest_stops_before_any_selection(self):
        root = P.make_project({"version": 1, "components": [{**P.component("a.example"), "type": "astro"}]}, ("a.example",))
        with self.assertRaises(Stop) as ctx:
            sites.load(root)
        self.assertIn("invalid", str(ctx.exception))

    def test_empty_component_list_stops(self):
        root = P.make_project({"version": 1, "components": []}, ())
        with self.assertRaises(Stop):
            sites.load(root)


class ErrorClassTests(unittest.TestCase):
    def test_ask_carries_options_and_defaults_to_empty(self):
        self.assertEqual(Ask("q").options, [])
        self.assertEqual(Ask("q", [{"name": "x"}]).options, [{"name": "x"}])

    def test_stop_and_ask_are_distinct_exceptions(self):
        self.assertFalse(issubclass(Stop, Ask) or issubclass(Ask, Stop))
        from site_common import errors
        self.assertEqual((errors.EXIT_OK, errors.EXIT_STOP, errors.EXIT_ASK), (0, 1, 2))


if __name__ == "__main__":
    unittest.main()
