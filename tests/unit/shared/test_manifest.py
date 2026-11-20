"""Manifest validation: plugin schema is binding, the project's schema copy never relaxes it."""
import copy
import json
import unittest

from tests.support import projects as P

P.use_shared_scripts()
from site_common import manifest, schema  # noqa: E402
from site_common.errors import Stop  # noqa: E402

SCHEMA = json.loads(P.SCHEMA_FILE.read_text())
GOOD = {"version": 2, "components": [P.component("a.example")]}


def changed(**change):
    data = copy.deepcopy(GOOD)
    for key, value in change.items():
        if value is None:
            data["components"][0].pop(key)
        else:
            data["components"][0][key] = value
    return data


class SchemaTests(unittest.TestCase):
    def test_valid_minimal_and_full(self):
        self.assertEqual(schema.validate(GOOD, SCHEMA), [])
        full = changed(port=4322, aliases=["x"], title="T", environment="production")
        self.assertEqual(schema.validate(full, SCHEMA), [])

    def test_each_rule_catches_its_error(self):
        cases = {"name": "A.example", "port": 80, "path": "../x", "type": "hugo", "serve": {"mode": "x"},
                 "dockerfile": "Dockerfile", "aliases": ["a", "a"], "title": "", "extra": 1, "environment": "bad env"}
        for key, value in cases.items():
            self.assertTrue(schema.validate(changed(**{key: value}), SCHEMA), key)
        self.assertTrue(schema.validate(changed(type="astro"), SCHEMA), "removed Docker type")
        self.assertTrue(schema.validate(changed(port="4321"), SCHEMA), "port as string")

    def test_removed_top_level_fields_and_missing_required(self):
        for field, value in (("registry", "ghcr.io"), ("retention", {"registry": 5})):
            self.assertTrue(schema.validate({**GOOD, field: value}, SCHEMA), field)
        self.assertTrue(schema.validate(changed(path=None), SCHEMA))
        self.assertTrue(schema.validate({"version": 2}, SCHEMA))
        self.assertTrue(schema.validate({"version": 3, "components": []}, SCHEMA))

    def test_bool_is_not_integer_and_unknown_keyword_is_an_error(self):
        self.assertTrue(schema.validate(changed(port=True), SCHEMA))
        with self.assertRaises(ValueError):
            schema.validate({}, {"type": "object", "oneOf": []})

    def test_only_astro_static_is_supported(self):
        self.assertEqual(SCHEMA["$defs"]["component"]["properties"]["type"]["enum"], ["astro-static"])


class ProblemsTests(unittest.TestCase):
    def setUp(self):
        self.copy = P.make_project(GOOD, ("a.example",)) / ".project" / "specs" / "website.schema.json"

    def test_semantic_duplicates(self):
        data = {"version": 2, "components": [P.component("a.example", port=4321), P.component("a.example", port=4321)]}
        text = " ".join(manifest.problems(data, self.copy))
        self.assertIn("duplicate name", text)
        self.assertIn("port 4321", text)

    def test_alias_collision_is_case_insensitive(self):
        data = {"version": 2, "components": [P.component("a.example", aliases=["x"]), P.component("b.example", aliases=["X"])]}
        self.assertTrue(any("already a name or alias" in e for e in manifest.problems(data, self.copy)))

    def test_valid_data_has_no_problems(self):
        self.assertEqual(manifest.problems(GOOD, self.copy), [])

    def test_loosened_project_copy_does_not_relax_the_contract(self):
        loose = json.loads(P.loosened_schema_text())
        cases = {"type astro": changed(type="astro"), "type hugo": changed(type="hugo"),
                 "serve": changed(serve={"mode": "x"}), "dockerfile": changed(dockerfile="D"),
                 "registry": {**GOOD, "registry": "ghcr.io"}, "retention": {**GOOD, "retention": {}}}
        for label, data in cases.items():
            self.assertEqual(schema.validate(data, loose), [], f"{label}: loosened copy would accept it (test not vacuous)")
            self.assertTrue(manifest.problems(data, self.copy), label)

    def test_older_foreign_project_copy_is_only_checked_for_existence(self):
        root = P.make_project(GOOD, ("a.example",), schema_text=P.OLDER_SCHEMA.read_text())
        self.assertEqual(manifest.problems(GOOD, root / ".project/specs/website.schema.json"), [])

    def test_missing_or_broken_project_copy_is_a_traceable_stop(self):
        for label, text in (("missing", None), ("not json", "{nope"), ("not an object", "[]\n")):
            root = P.make_project(GOOD, ("a.example",), schema_text=text)
            target = root / ".project/specs/website.schema.json"
            with self.assertRaises(Stop, msg=label) as ctx:
                manifest.problems(GOOD, target)
            self.assertIn("website.schema.json", str(ctx.exception), label)

    def test_invalid_json_manifest_is_a_stop(self):
        root = P.make_project(GOOD, ("a.example",))
        (root / ".project/specs/zyris-website.json").write_text("{broken")
        with self.assertRaises(Stop):
            manifest.load(root / ".project/specs/zyris-website.json")


if __name__ == "__main__":
    unittest.main()
