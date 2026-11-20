import json
import unittest
from pathlib import Path

from tests.support import setup_paths as helpers
import manifest
import validate
from site_common import schema

SKILL = helpers.RES
PLUGIN_SCHEMA_FILE = helpers.SCHEMA_FILE
SCHEMA = json.loads(PLUGIN_SCHEMA_FILE.read_text())
GOOD = {"version": 2, "components": [{"name": "a.at", "path": "sites/a.at", "type": "astro-static"}]}


def bad(**change):
    data = json.loads(json.dumps(GOOD))
    for key, value in change.items():
        if value is None:
            data["components"][0].pop(key)
        else:
            data["components"][0][key] = value
    return data


class SchemaTests(unittest.TestCase):
    def test_good(self):
        self.assertEqual(schema.validate(GOOD, SCHEMA), [])

    def test_each_rule_catches_its_error(self):
        cases = {
            "name": "A.at", "port": 80, "port ": "4321", "path": "../x", "type": "hugo",
            "type ": "astro", "serve": {"mode": "behind-proxy", "network": "public"}, "dockerfile": "Dockerfile",
            "aliases": ["a", "a"], "title": "", "extra": 1, "environment": "bad env",
        }
        for key, value in cases.items():
            data = bad(**{key.strip(): value})
            self.assertTrue(schema.validate(data, SCHEMA), key)

    def test_removed_top_level_fields_are_rejected(self):
        for field, value in (("registry", "ghcr.io"), ("retention", {"registry": 5}), ("retention ", {})):
            self.assertTrue(schema.validate({**GOOD, field.strip(): value}, SCHEMA), field)

    def test_environment_stays_an_optional_valid_field(self):
        self.assertEqual(schema.validate(bad(environment="production"), SCHEMA), [])

    def test_missing_required(self):
        self.assertTrue(schema.validate(bad(path=None), SCHEMA))

    def test_bool_is_not_integer(self):
        self.assertTrue(schema.validate(bad(port=True), SCHEMA))

    def test_unknown_schema_keyword_is_an_error(self):
        with self.assertRaises(ValueError):
            schema.validate({}, {"type": "object", "oneOf": []})

    def test_schema_types_match_types_json(self):
        enum = SCHEMA["$defs"]["component"]["properties"]["type"]["enum"]
        self.assertEqual(sorted(enum), validate.supported_types(validate.load_config(SKILL)))


class SemanticTests(unittest.TestCase):
    def check(self, data):
        return manifest.problems(data, PLUGIN_SCHEMA_FILE, ["astro-static"])

    def test_duplicate_name_and_port(self):
        data = json.loads(json.dumps(GOOD))
        data["components"][0]["port"] = 4321
        second = json.loads(json.dumps(data["components"][0]))
        data["components"].append(second)
        text = " ".join(self.check(data))
        self.assertIn("duplicate name", text)
        self.assertIn("port 4321", text)

    def test_alias_collision(self):
        data = json.loads(json.dumps(GOOD))
        other = {"name": "b.at", "path": "sites/b.at", "type": "astro-static", "aliases": ["a.at"]}
        data["components"].append(other)
        self.assertTrue(any("already a name or alias" in e for e in self.check(data)))

    def test_unsupported_type(self):
        self.assertTrue(manifest.problems(GOOD, PLUGIN_SCHEMA_FILE, ["x"]))


class SetupAndSharedValidatorTests(unittest.TestCase):
    """The setup variant keeps its own signature but must judge the same cases like the shared validator (no drift after the rename)."""

    def test_same_verdicts_for_the_same_manifests(self):
        from site_common import manifest as shared
        import tempfile
        specs = Path(tempfile.mkdtemp()) / "website.schema.json"
        specs.write_text("{}\n")
        base = {"name": "a.at", "path": "sites/a.at", "type": "astro-static"}
        cases = [GOOD, bad(port=4321), bad(type="astro"), bad(serve={"mode": "x"}), bad(port=80), bad(aliases=["a", "a"]),
                 {"version": 2, "components": [base, {**base, "path": "sites/b"}]},
                 {"version": 2, "components": [{**base, "port": 4321}, {**base, "name": "b.at", "port": 4321}]},
                 {"version": 2, "components": [base, {**base, "name": "b.at", "aliases": ["a.at"]}]}]
        for index, data in enumerate(cases):
            ours = manifest.problems(json.loads(json.dumps(data)), specs, ["astro-static"])
            theirs = shared.problems(json.loads(json.dumps(data)), specs)
            self.assertEqual(bool(ours), bool(theirs), index)

    def test_both_use_the_one_plugin_schema_file(self):
        from site_common import manifest as shared
        self.assertEqual(manifest.PLUGIN_SCHEMA, shared.PLUGIN_SCHEMA)
        self.assertEqual(manifest.PLUGIN_SCHEMA.name, "website.schema.json")
        self.assertEqual((manifest.SPECS, manifest.FILE, manifest.SCHEMA), (shared.SPECS, shared.FILE, shared.SCHEMA))

    def test_effective_ports_and_next_port(self):
        components = [{"name": "a"}, {"name": "b", "port": 4400}, {"name": "c"}]
        self.assertEqual(manifest.effective_ports(components), [4321, 4400, 4323])
        self.assertEqual(manifest.next_port(components), 4401)
        self.assertEqual(manifest.next_port([]), 4321)
        from errors import Stop
        with self.assertRaises(Stop):
            manifest.next_port([{"name": "x", "port": 65535}])

    def test_legacy_problem_detection(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.assertIsNone(manifest.legacy_problem(d, {"version": 2}))
        self.assertIn("old project format", manifest.legacy_problem(d, {"$schema": "./zyris-website.schema.json"}))
        (d / "zyris-website.schema.json").write_text("{}")
        self.assertIn("old project format", manifest.legacy_problem(d, None))
        (d / "website.schema.json").write_text("{}")
        self.assertIsNone(manifest.legacy_problem(d, {"$schema": "./website.schema.json"}))
        self.assertTrue((d / "zyris-website.schema.json").exists())


if __name__ == "__main__":
    unittest.main()
