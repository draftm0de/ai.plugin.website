"""Static adopt (S2, S5, S15) and protection of the project's schema copy (the plugin schema is the only supported one)."""
import json
import os
import unittest
from pathlib import Path

from tests.support import setup_paths as helpers  # noqa: F401  (sets up sys.path first)
import ownership
from tests.support import setup_helpers as h
import static_setup


def adopt(root, domain="adopted.example", runner=None, **kw):
    return static_setup.execute(h.opts("adopt", domain, root, **kw), runner or h.FakeRunner())


def levels(result, level):
    return [f["text"] for f in result["findings"] if f["level"] == level]


class AdoptTests(unittest.TestCase):
    def setUp(self):
        self.root = h.repo()

    def test_s2_adopt_without_docker_files_leaves_every_site_file_byte_identical(self):
        site = h.make_static_site(self.root, extra={"src/content/post.md": "# post\n", "public/logo.svg": "<svg/>"})
        (site / "package-lock.json").write_text("{}\n")
        before_site = h.sub(h.snapshot(self.root), "sites/adopted.example")
        self.assertEqual(static_setup.tree_hash(site), static_setup.tree_hash(site))
        result = adopt(self.root, title="Adopted", aliases=("ad",))
        self.assertEqual((result["state"], result["exit"]), ("adopted", 0), result)
        self.assertEqual(h.sub(h.snapshot(self.root), "sites/adopted.example"), before_site)
        self.assertEqual(h.manifest_of(self.root)["components"][0],
                         {"name": "adopted.example", "title": "Adopted", "aliases": ["ad"], "port": 4321,
                          "path": "sites/adopted.example", "type": "astro-static"})
        entry = h.record_of(self.root)["sites"]["adopted.example"]
        self.assertEqual((entry["mode"], entry["files"]), ("adopted", {}))
        for legacy in ("Dockerfile", "docker-compose.yml", "Caddyfile", "site.caddy", ".dockerignore"):
            self.assertFalse((self.root / "sites/adopted.example" / legacy).exists())
        self.assertTrue((self.root / ".tmp").is_dir())
        self.assertEqual([f for f in result["verification"].values() if f["ran"]], [])

    def test_adopt_changes_listing_names_only_non_site_files(self):
        h.make_static_site(self.root)
        result = static_setup.plan_only(h.opts("adopt", "adopted.example", self.root))
        paths = {c["path"]: c["action"] for c in result["changes"]}
        self.assertEqual(paths["sites/adopted.example"], "keep")
        self.assertFalse([p for p, a in paths.items() if p.startswith("sites/adopted.example/") and a != "keep"])

    def test_identical_repetition_is_unchanged_without_a_diff(self):
        h.make_static_site(self.root)
        adopt(self.root)
        before = h.snapshot(self.root)
        again = adopt(self.root)
        self.assertEqual(again["state"], "unchanged", again)
        self.assertEqual(h.snapshot(self.root), before)
        self.assertEqual(adopt(self.root, title="Other")["state"], "conflict")

    def test_automatic_port_stays_on_repetition(self):
        h.make_static_site(self.root, "a.example")
        h.make_static_site(self.root, "b.example")
        adopt(self.root, "a.example")
        adopt(self.root, "b.example")
        self.assertEqual(adopt(self.root, "b.example")["state"], "unchanged")
        self.assertEqual([c["port"] for c in h.manifest_of(self.root)["components"]], [4321, 4322])

    def test_adopt_of_a_site_created_by_setup_is_a_conflict_and_vice_versa(self):
        static_setup.execute(h.opts("create", root=self.root))
        self.assertEqual(adopt(self.root, "example.com")["state"], "conflict")
        h.make_static_site(self.root)
        adopt(self.root)
        r = static_setup.execute(h.opts("create", "adopted.example", self.root))
        self.assertEqual(r["state"], "conflict")           # existing folder / adopted mode: create never takes it over

    def test_s15_blocking_findings_stop_before_any_change(self):
        cases = {
            "no package.json": lambda s: (s / "package.json").unlink(),
            "invalid package.json": lambda s: (s / "package.json").write_text("{nope"),
            "no build script": lambda s: (s / "package.json").write_text(json.dumps({"scripts": {"check": "x"}})),
            "build output not ignored": lambda s: (s / ".gitignore").write_text("node_modules/\n"),
        }
        for label, break_it in cases.items():
            root = h.repo()
            site = h.make_static_site(root)
            break_it(site)
            before = h.snapshot(root)
            result = adopt(root)
            self.assertEqual((result["state"], result["exit"]), ("invalid", 1), (label, result))
            self.assertTrue(levels(result, "blocking"), label)
            self.assertEqual(h.snapshot(root), before, label)
            self.assertEqual(static_setup.plan_only(h.opts("adopt", "adopted.example", root))["state"], "invalid", label)

    def test_missing_folder_and_symlinked_folder_are_invalid(self):
        self.assertEqual(adopt(self.root, "absent.example")["state"], "invalid")
        outside = h.repo()
        (outside / "package.json").write_text('{"scripts": {"build": "x"}}')
        (self.root / "sites").mkdir()
        (self.root / "sites" / "adopted.example").symlink_to(outside)
        before = h.snapshot(self.root)
        result = adopt(self.root)
        self.assertEqual(result["state"], "invalid")
        self.assertIn("symlink", " ".join(result["problems"]))
        self.assertEqual(h.snapshot(self.root), before)
        self.assertEqual(adopt(self.root, sites_dir="../x")["state"], "invalid")

    def test_s15_warnings_are_listed_not_repaired(self):
        site = h.make_static_site(self.root, scripts={"build": "astro build"},
                                  extra={"Dockerfile": "FROM scratch\n", "site.caddy": "redir /a /b\n"})
        (site / "astro.config.mjs").write_text("import node from '@astrojs/node';\nexport default { output: 'server', adapter: node() };\n")
        before = h.sub(h.snapshot(self.root), "sites/adopted.example")
        result = adopt(self.root)
        self.assertEqual(result["state"], "adopted", result)
        text = " | ".join(levels(result, "warning"))
        for expected in ("no 'check' script", "package-lock.json", "rules/accessibility.md", "rules/seo.md", "seo-check.mjs", "a11y-check.mjs",
                         "non-static build", "legacy serving files present (Dockerfile, site.caddy)", "not lost, not moved"):
            self.assertIn(expected, text)
        self.assertEqual(h.sub(h.snapshot(self.root), "sites/adopted.example"), before)

    def test_adopt_with_build_runs_declared_steps_and_reports_exit_codes_without_repairing(self):
        h.make_static_site(self.root)
        runner = h.FakeRunner(check=(True, 1, "no audit"))
        result = adopt(self.root, runner=runner, build=True)
        self.assertEqual(result["state"], "failed-check")
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 0), "check": (True, 1)})
        self.assertIn("adopted.example", [c["name"] for c in h.manifest_of(self.root)["components"]])
        self.assertFalse((self.root / "sites/adopted.example/scripts").exists())      # no template repair
        ok = adopt(self.root, runner=h.FakeRunner(), build=True)
        self.assertEqual(ok["state"], "unchanged")

    def test_simulated_exit_codes_are_reported_per_step(self):
        """Fake npm with simulated exit codes (no real tool runs): check exits 4, a second project fails the build with 3."""
        h.make_static_site(self.root)
        result = static_setup.execute(h.opts("adopt", "adopted.example", self.root, build=True),
                                      h.FakeRunner(check=(True, 4, "audit failed")))
        self.assertEqual(result["state"], "failed-check", result)
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 0), "check": (True, 4)})
        self.assertEqual(result["lockfile"], "created")
        failing = h.repo()
        h.make_static_site(failing)
        result = static_setup.execute(h.opts("adopt", "adopted.example", failing, build=True), h.FakeRunner(build=(True, 3, "boom")))
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 3), "check": (False, None)})
        self.assertEqual(result["state"], "failed-build")

    def test_s5_foreign_site_content_survives_create_in_the_same_project(self):
        site = h.make_static_site(self.root, extra={"src/data/projects.json": "[1]\n", "rules/pages.md": "mine\n"})
        adopt(self.root)
        before = h.sub(h.snapshot(self.root), "sites/adopted.example")
        static_setup.execute(h.opts("create", "new.example", self.root))
        self.assertEqual(h.sub(h.snapshot(self.root), "sites/adopted.example"), before)


class SchemaProtectionTests(unittest.TestCase):
    """The project's schema copy: the plugin schema is the only supported one; foreign or modified copies are protected."""

    def project_with_schema(self, schema_bytes):
        root = h.repo()
        specs = root / ".project" / "specs"
        specs.mkdir(parents=True)
        (specs / "website.schema.json").write_bytes(schema_bytes)
        return root

    def test_foreign_older_schema_without_record_is_a_conflict_and_nothing_changes(self):
        root = self.project_with_schema(h.SCHEMA_FOREIGN.read_bytes())
        before = h.snapshot(root)
        plan = static_setup.plan_only(h.opts("create", "new.example", root))
        self.assertEqual(plan["state"], "conflict")
        result = static_setup.execute(h.opts("create", "new.example", root), h.FakeRunner())
        self.assertEqual(result["state"], "conflict")
        text = " ".join(result["problems"])
        self.assertIn("no ownership record", text)
        self.assertIn("never replaced automatically", text)
        self.assertEqual(h.snapshot(root), before)

    def test_modified_current_schema_is_a_conflict(self):
        root = self.project_with_schema(static_setup.load_schema_bytes().replace(b'"astro-static"', b'"astro-static", "other"'))
        before = h.snapshot(root)
        result = static_setup.execute(h.opts("create", "new.example", root), h.FakeRunner())
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(h.snapshot(root), before)

    def test_schema_that_setup_wrote_and_nobody_modified_is_replaced_by_the_current_one(self):
        root = h.repo()
        static_setup.execute(h.opts("create", "first.example", root), h.FakeRunner())
        schema = root / ".project/specs/website.schema.json"
        older = h.SCHEMA_FOREIGN.read_bytes()
        schema.write_bytes(older)                                                   # simulate: setup wrote this older copy itself
        record_file = root / ".project/specs/website.managed.json"
        record = json.loads(record_file.read_text())
        record["project_files"][".project/specs/website.schema.json"]["sha256"] = ownership.sha256(older)
        record_file.write_text(json.dumps(record, indent=2) + "\n")
        plan = static_setup.plan_only(h.opts("create", "second.example", root))
        change = next(c for c in plan["changes"] if c["path"].endswith("schema.json"))
        self.assertEqual(change["action"], "modify")
        self.assertIn("managed file, unmodified", change["reason"])
        result = static_setup.execute(h.opts("create", "second.example", root), h.FakeRunner())
        self.assertEqual(result["state"], "created", result)
        self.assertEqual(schema.read_bytes(), static_setup.load_schema_bytes())
        self.assertEqual(h.record_of(root)["project_files"][".project/specs/website.schema.json"]["sha256"],
                         ownership.sha256(static_setup.load_schema_bytes()))

    def test_project_written_by_setup_is_valid_for_the_current_validators(self):
        """Fictional replacement of the former test against a real website project: a project produced by setup itself."""
        root = h.repo()
        static_setup.execute(h.opts("create", "first.example", root), h.FakeRunner())
        schema_file = root / ".project/specs/website.schema.json"
        self.assertEqual(schema_file.read_bytes(), static_setup.load_schema_bytes())      # the project copy IS the plugin schema
        data = h.manifest_of(root)
        self.assertEqual(static_setup.manifest.problems(data, schema_file, ["astro-static"]), [])
        self.assertEqual({c["type"] for c in data["components"]}, {"astro-static"})
        for removed in ("registry", "retention"):
            self.assertNotIn(removed, data)
        self.assertTrue(all("serve" not in c for c in data["components"]))
        plan = static_setup.plan_only(h.opts("create", "new.example", root))
        self.assertEqual(plan["state"], "planned", plan)

    def test_a_manifest_with_the_removed_type_is_rejected_not_migrated(self):
        root = self.project_with_schema(static_setup.load_schema_bytes())
        old = {"version": 2, "components": [{"name": "old.example", "path": "sites/old.example", "type": "astro",
                                              "serve": {"mode": "behind-proxy", "network": "public"}}]}
        (root / ".project/specs/website.json").write_text(json.dumps(old, indent=2) + "\n")
        before = h.snapshot(root)
        result = static_setup.execute(h.opts("create", "new.example", root), h.FakeRunner())
        self.assertIn(result["state"], ("invalid", "conflict"))
        self.assertIn("existing manifest is invalid", " ".join(result["problems"]))
        self.assertEqual(h.snapshot(root), before)

    def test_static_only_project_validates_against_its_own_schema_copy(self):
        root = h.repo()
        static_setup.execute(h.opts("create", root=root), h.FakeRunner())
        schema = json.loads((root / ".project/specs/website.schema.json").read_text())
        self.assertEqual(static_setup.manifest.problems(h.manifest_of(root), schema, ["astro-static"]), [])
        self.assertNotIn("registry", h.manifest_of(root))


if __name__ == "__main__":
    unittest.main()
