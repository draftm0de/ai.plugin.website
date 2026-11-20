"""Acceptance: manifest initialisation (field values), port selection, schema copy states,
isolated plugin copy. Fictional fixtures in temporary git repositories; npm is always a fake."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import setup_paths as helpers
from tests.support import setup_helpers as h
import static_setup
from site_common import sites

NEW_SCHEMA = "website.schema.json"


def specs(root):
    return root / ".project" / "specs"


def write_manifest(root, data, schema="current"):
    specs(root).mkdir(parents=True, exist_ok=True)
    (specs(root) / "website.json").write_text(json.dumps(data, indent=2) + "\n")
    if schema == "current":
        (specs(root) / NEW_SCHEMA).write_bytes(helpers.SCHEMA_FILE.read_bytes())
    elif schema is not None:
        (specs(root) / schema[0]).write_bytes(schema[1])


def comp(name, **extra):
    return {"name": name, "path": f"sites/{name}", "type": "astro-static", **extra}


def create(root, domain="new.example", **kw):
    return static_setup.execute(h.opts("create", domain, root, **kw), h.FakeRunner())


class ManifestInitialisationTests(unittest.TestCase):
    def test_new_project_gets_the_confirmed_default_fields(self):
        root = h.repo()
        result = create(root, "alpha.example")
        self.assertEqual(result["state"], "created", result)
        self.assertEqual(h.manifest_of(root), {"$schema": "./website.schema.json", "version": 2, "components": [{
            "name": "alpha.example", "title": "alpha.example", "aliases": [], "port": 4321,
            "path": "sites/alpha.example", "type": "astro-static"}]})
        self.assertNotIn("environment", h.manifest_of(root)["components"][0])
        self.assertEqual((specs(root) / NEW_SCHEMA).read_bytes(), helpers.SCHEMA_FILE.read_bytes())
        record = h.record_of(root)
        self.assertIn(f".project/specs/{NEW_SCHEMA}", record["project_files"])

    def test_explicit_values_are_written_as_given(self):
        root = h.repo()
        create(root, "beta.example", sites_dir="web", title="Beta Site", aliases=("b", "bee"), port=5000, environment="staging")
        self.assertEqual(h.manifest_of(root)["components"][0], {
            "name": "beta.example", "title": "Beta Site", "aliases": ["b", "bee"], "port": 5000,
            "path": "web/beta.example", "type": "astro-static", "environment": "staging"})

    def test_existing_manifest_components_are_preserved_byte_for_byte_in_content(self):
        root = h.repo()
        first = comp("first.example", title="First", aliases=["f"], port=4500, environment="production")
        bare = comp("bare.example")                       # no port/title/aliases: must not be rewritten with derived values
        write_manifest(root, {"$schema": "./website.schema.json", "version": 2, "components": [first, bare]})
        self.assertEqual(create(root, "third.example")["state"], "created")
        data = h.manifest_of(root)
        self.assertEqual(data["components"][:2], [first, bare])
        self.assertEqual(data["components"][2]["name"], "third.example")
        self.assertEqual(data["$schema"], "./website.schema.json")

    def test_manifest_without_schema_reference_gets_no_reference_added(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("first.example", port=4321)]})
        create(root, "second.example")
        self.assertNotIn("$schema", h.manifest_of(root))


class PortSelectionTests(unittest.TestCase):
    def port_of(self, root, domain):
        return next(c["port"] for c in h.manifest_of(root)["components"] if c["name"] == domain)

    def test_empty_project_starts_at_4321_and_follows_the_highest_effective_port(self):
        root = h.repo()
        create(root, "a.example")
        create(root, "b.example")
        self.assertEqual([self.port_of(root, "a.example"), self.port_of(root, "b.example")], [4321, 4322])

    def test_automatic_port_follows_the_highest_explicit_port_and_does_not_rewrite_entries(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("a.example", port=4500), comp("b.example", port=4400)]})
        create(root, "c.example")
        self.assertEqual(self.port_of(root, "c.example"), 4501)
        self.assertEqual([c.get("port") for c in h.manifest_of(root)["components"][:2]], [4500, 4400])

    def test_components_without_explicit_port_count_with_their_derived_port(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("a.example"), comp("b.example"), comp("c.example")]})
        self.assertEqual([sites.BASE_PORT + i for i in range(3)], [4321, 4322, 4323])
        create(root, "d.example")
        self.assertEqual(self.port_of(root, "d.example"), 4324)

    def test_explicit_port_colliding_with_an_explicit_or_derived_port_is_a_conflict_without_writes(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("a.example", port=4400), comp("b.example")]})   # b derives 4322
        before = h.snapshot(root)
        for port, owner in ((4400, "a.example"), (4322, "b.example")):
            result = static_setup.plan_only(h.opts("create", "n.example", root, port=port))
            self.assertEqual(result["state"], "conflict", result)
            self.assertIn(owner, " ".join(result["problems"]))
            self.assertEqual(create(root, "n.example", port=port)["state"], "conflict")
        self.assertEqual(h.snapshot(root), before)

    def test_range_limits(self):
        root = h.repo()
        for bad in (1023, 65536, -1):
            self.assertEqual(create(root, "n.example", port=bad)["state"], "invalid", bad)
        self.assertFalse((root / "sites").exists())
        self.assertEqual(create(root, "low.example", port=1024)["state"], "created")
        self.assertEqual(create(root, "high.example", port=65535)["state"], "created")

    def test_automatic_port_never_overflows_silently(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("a.example", port=65535)]})
        before = h.snapshot(root)
        result = create(root, "b.example")
        self.assertEqual(result["state"], "invalid", result)
        self.assertIn("--port", " ".join(result["problems"]))
        self.assertEqual(h.snapshot(root), before)
        self.assertEqual(create(root, "b.example", port=4321)["state"], "created")      # an explicit choice still works

    def test_repetition_keeps_the_stored_port(self):
        root = h.repo()
        create(root, "a.example")
        create(root, "b.example")
        self.assertEqual(create(root, "a.example")["state"], "unchanged")
        self.assertEqual(self.port_of(root, "a.example"), 4321)

    def test_types_json_base_port_equals_the_resolver_base_port(self):
        defaults = json.loads((helpers.RES / "types.json").read_text())["defaults"]
        self.assertEqual(defaults["base_port"], sites.BASE_PORT)

    def test_name_and_alias_conflicts_are_refused_without_writes(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": [comp("a.example", aliases=["shared"], port=4321)]})
        before = h.snapshot(root)
        for kwargs in ({"aliases": ("shared",)}, {"aliases": ("A.EXAMPLE",)}):
            self.assertEqual(create(root, "n.example", **kwargs)["state"], "conflict", kwargs)
        self.assertEqual(h.snapshot(root), before)


class SchemaCopyStateTests(unittest.TestCase):
    def test_missing_copy_with_existing_valid_manifest_is_created_and_nothing_else_changes(self):
        root = h.repo()
        write_manifest(root, {"$schema": "./website.schema.json", "version": 2, "components": [comp("a.example", port=4321)]}, schema=None)
        self.assertEqual(create(root, "b.example")["state"], "created")
        self.assertEqual((specs(root) / NEW_SCHEMA).read_bytes(), helpers.SCHEMA_FILE.read_bytes())

    def test_identical_copy_is_kept_untouched(self):
        root = h.repo()
        write_manifest(root, {"version": 2, "components": []})
        stamp = (specs(root) / NEW_SCHEMA).stat().st_mtime_ns
        result = static_setup.plan_only(h.opts("create", "n.example", root))
        self.assertIn({"path": f".project/specs/{NEW_SCHEMA}", "action": "keep",
                       "reason": "equals the current plugin schema (no ownership record: not claimed as managed)"}, result["changes"])
        create(root, "n.example")
        self.assertEqual((specs(root) / NEW_SCHEMA).stat().st_mtime_ns, stamp)

    def test_foreign_or_damaged_copy_is_a_conflict_and_stays_byte_identical(self):
        for label, content in (("older foreign", h.SCHEMA_FOREIGN.read_bytes()), ("not json", b"{nope"), ("array", b"[]\n")):
            root = h.repo()
            write_manifest(root, {"version": 2, "components": []}, schema=(NEW_SCHEMA, content))
            before = h.snapshot(root)
            result = create(root, "n.example")
            self.assertEqual(result["state"], "conflict", (label, result))
            self.assertEqual(h.snapshot(root), before, label)
            self.assertEqual(h.snapshot(root), before)




class IsolatedPluginCopyTests(unittest.TestCase):
    """The shipped runtime works from an extracted copy (path with spaces, other cwd, no PYTHONPATH) and never writes into it."""

    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp()).resolve() / "My Plugin Copy"
        (cls.base / "skills").mkdir(parents=True)
        for name in ("setup", "_shared"):
            shutil.copytree(helpers.ROOT / "skills" / name, cls.base / "skills" / name, ignore=shutil.ignore_patterns("__pycache__"))
        cls.script = cls.base / "skills" / "setup" / "scripts" / "site_setup.py"

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
        env.update(extra)
        return env

    def snap(self):
        return h.snapshot(self.base)

    def test_create_from_the_copy_with_other_cwd_leaves_the_copy_unchanged_and_uses_only_the_copy(self):
        root = h.repo()
        elsewhere = Path(tempfile.mkdtemp())
        before = self.snap()
        proc = subprocess.run([sys.executable, "-B", str(self.script), "create", "copy.example", "--type", "astro-static",
                               "--root", str(root), "--json"], cwd=elsewhere, env=self.env(), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["state"], "created")
        self.assertEqual(self.snap(), before, "the installed plugin copy was written to")
        self.assertTrue((root / "sites/copy.example/package.json").is_file())
        self.assertTrue((root / "sites/copy.example/src/styles/foundation/tokens.css").is_file())
        self.assertEqual((specs(root) / NEW_SCHEMA).read_bytes(), (self.base / "skills/_shared/resources" / NEW_SCHEMA).read_bytes())

    def test_templates_are_read_from_the_copy_not_from_the_checkout(self):
        marker = Path(tempfile.mkdtemp()).resolve() / "Marker Copy"
        shutil.copytree(self.base, marker)
        (marker / "skills/setup/templates/astro-static/public/favicon.svg").write_text("<svg id='copy-only'/>\n")
        root = h.repo()
        proc = subprocess.run([sys.executable, "-B", str(marker / "skills/setup/scripts/site_setup.py"), "create", "m.example",
                               "--type", "astro-static", "--root", str(root)], env=self.env(), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("copy-only", (root / "sites/m.example/public/favicon.svg").read_text())

    def test_missing_template_or_schema_in_the_copy_stops_before_writing(self):
        for rel in ("skills/setup/templates/astro-static", "skills/_shared/resources/website.schema.json"):
            broken = Path(tempfile.mkdtemp()).resolve() / "Broken Copy"
            shutil.copytree(self.base, broken)
            target = broken / rel
            shutil.rmtree(target) if target.is_dir() else target.unlink()
            root = h.repo()
            before = h.snapshot(root)
            proc = subprocess.run([sys.executable, "-B", str(broken / "skills/setup/scripts/site_setup.py"), "create", "x.example",
                                   "--type", "astro-static", "--root", str(root)], env=self.env(), capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, (rel, proc.stdout, proc.stderr))
            self.assertNotIn("Traceback", proc.stdout + proc.stderr, rel)
            self.assertEqual(h.snapshot(root), before, rel)

    def test_without_the_bytecode_flag_nothing_is_required_but_with_it_nothing_is_written(self):
        before = self.snap()
        subprocess.run([sys.executable, "-I", "-B", str(self.script), "plan", "create", "p.example", "--type", "astro-static",
                        "--root", str(h.repo())], env=self.env(), capture_output=True, text=True)
        self.assertEqual(self.snap(), before)


class BuildGateTests(unittest.TestCase):
    def test_unsupported_type_and_missing_format_stop_before_install_or_build(self):
        root = h.repo()
        runner = h.NoRun()
        for kwargs in ({"site_type": "astro"}, {"site_type": "hugo"}, {"site_type": None}):
            result = static_setup.execute(h.opts("create", "n.example", root, build=True, **kwargs), runner)
            self.assertIn(result["state"], ("invalid", "needs-input"), kwargs)
            self.assertEqual(result["verification"], {n: {"ran": False, "exit": None} for n in ("install", "build", "check")})
        self.assertFalse((root / "sites").exists())


if __name__ == "__main__":
    unittest.main()
