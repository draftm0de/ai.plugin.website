"""Static create: S1 (offline part), S3, S5-S10, S12, S14. Real npm lives in tests/external/setup/test_real_npm.py (separate runner)."""
import io
import json
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.support import setup_paths as helpers  # noqa: F401  (sets up sys.path first)
import ownership
import site_setup
from tests.support import setup_helpers as h
import static_setup

DOCKER_FILES = ["Dockerfile", ".dockerignore", "docker-compose.yml", "Caddyfile", "site.caddy"]


def create(root, domain="example.com", runner=None, **kw):
    return static_setup.execute(h.opts("create", domain, root, **kw), runner or h.FakeRunner())


def cli(root, *argv, runner=None):
    out = io.StringIO()
    with redirect_stdout(out):
        code = site_setup.main([*argv, "--root", str(root)] if "--root" not in argv else list(argv), runner=runner or h.FakeRunner())
    return code, out.getvalue()


class CreateTests(unittest.TestCase):
    def setUp(self):
        self.root = h.repo()

    def test_new_site_without_origin_and_without_docker_files(self):          # S1 (offline)
        result = create(self.root)
        self.assertEqual((result["state"], result["exit"]), ("created", 0), result)
        site = self.root / "sites" / "example.com"
        for rel in DOCKER_FILES:
            self.assertFalse((site / rel).exists(), rel)
        for rel in ("package.json", "astro.config.mjs", "src/pages/index.astro", "scripts/seo-check.mjs", "rules/accessibility.md", ".gitignore"):
            self.assertTrue((site / rel).is_file(), rel)
        self.assertNotIn("caddy", (site / "CLAUDE.md").read_text().lower())
        self.assertNotIn("site.caddy", (site / "rules" / "seo.md").read_text())
        data = h.manifest_of(self.root)
        self.assertEqual(data, {"$schema": "./website.schema.json", "version": 2, "components": [
            {"name": "example.com", "title": "example.com", "aliases": [], "port": 4321, "path": "sites/example.com", "type": "astro-static"}]})
        self.assertNotIn("serve", data["components"][0])
        self.assertNotIn("registry", data)
        self.assertTrue((self.root / ".tmp").is_dir())
        self.assertIn(".tmp/", (self.root / ".gitignore").read_text())
        self.assertTrue(all(not s["ran"] and s["exit"] is None for s in result["verification"].values()))

    def test_template_ignores_the_build_output(self):
        create(self.root)
        for rel in static_setup.validate.load_config(static_setup.RES)["types"]["astro-static"]["ignored"]:
            self.assertTrue(static_setup.project_files.is_ignored(self.root, f"sites/example.com/{rel}"), rel)

    def test_options_title_alias_port_environment_path(self):
        result = create(self.root, title="Example Site", aliases=("ex", "demo"), port=4400, environment="staging", sites_dir="web/sites")
        self.assertEqual(result["state"], "created", result)
        self.assertEqual(h.manifest_of(self.root)["components"][0],
                         {"name": "example.com", "title": "Example Site", "aliases": ["ex", "demo"], "port": 4400,
                          "path": "web/sites/example.com", "type": "astro-static", "environment": "staging"})
        self.assertIn("Example Site", (self.root / "web/sites/example.com/CLAUDE.md").read_text())

    def test_second_site_appends_and_gets_the_next_free_port(self):
        create(self.root, "a.example")
        before = h.snapshot(self.root)
        create(self.root, "b.example")
        data = h.manifest_of(self.root)
        self.assertEqual([c["port"] for c in data["components"]], [4321, 4322])
        self.assertEqual(h.sub(h.snapshot(self.root), "sites/a.example"), h.sub(before, "sites/a.example"))

    def test_ownership_record_lists_every_generated_file_with_its_hash(self):
        create(self.root)
        record = h.record_of(self.root)
        entry = record["sites"]["example.com"]
        self.assertEqual((entry["mode"], entry["type"], entry["template_version"]), ("created", "astro-static", "static-1"))
        site = self.root / "sites" / "example.com"
        files = sorted(p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file())
        self.assertEqual(sorted(entry["files"]), files)
        for rel, sha in entry["files"].items():
            self.assertEqual(ownership.sha256((site / rel).read_bytes()), sha, rel)
        schema = ".project/specs/website.schema.json"
        self.assertEqual(record["project_files"][schema]["sha256"], ownership.sha256((self.root / schema).read_bytes()))

    def test_build_success_records_real_exit_codes(self):
        runner = h.FakeRunner()
        result = static_setup.execute(h.opts("create", root=self.root, build=True), runner)
        self.assertEqual((result["state"], result["exit"]), ("created", 0), result)
        self.assertEqual([c[0] for c in runner.calls], ["install", "build", "check"])
        self.assertEqual({n: (s["ran"], s["exit"]) for n, s in result["verification"].items()},
                         {"install": (True, 0), "build": (True, 0), "check": (True, 0)})
        self.assertEqual(result["lockfile"], "created")


class UnchangedTests(unittest.TestCase):                                      # S3
    def test_identical_repetition_changes_no_byte_and_no_timestamp(self):
        root = h.repo()
        create(root, aliases=("ex",), title="T")
        create(root, "other.example")
        before = h.snapshot(root)
        stamps = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}
        again = create(root, aliases=("ex",), title="T")
        self.assertEqual((again["state"], again["exit"]), ("unchanged", 0), again)
        self.assertEqual(h.snapshot(root), before)
        self.assertEqual({p: p.stat().st_mtime_ns for p in stamps}, stamps)

    def test_automatic_port_is_not_assigned_again_on_repetition(self):
        root = h.repo()
        create(root, "a.example")
        create(root, "b.example")                       # automatic port 4322
        again = create(root, "b.example")               # must reuse 4322, not look for a new free port
        self.assertEqual(again["state"], "unchanged", again)
        self.assertEqual([c["port"] for c in h.manifest_of(root)["components"]], [4321, 4322])

    def test_repetition_with_build_runs_the_checks_and_stays_unchanged_only_if_they_pass(self):
        root = h.repo()
        create(root)
        runner = h.FakeRunner()
        again = static_setup.execute(h.opts("create", root=root, build=True), runner)
        self.assertEqual(again["state"], "unchanged", again)
        self.assertEqual([c[0] for c in runner.calls], ["install", "build", "check"])
        failing = static_setup.execute(h.opts("create", root=root, build=True), h.FakeRunner(build=(True, 2, "boom")))
        self.assertEqual((failing["state"], failing["exit"]), ("failed-build", 1))


class ConflictTests(unittest.TestCase):                                       # S5, S6
    def setUp(self):
        self.root = h.repo()

    def assert_conflict(self, result, *words):
        self.assertEqual((result["state"], result["exit"]), ("conflict", 1), result)
        text = " ".join(result["problems"])
        for word in words:
            self.assertIn(word, text)

    def test_registered_domain_with_different_values(self):
        create(self.root, title="One")
        before = h.snapshot(self.root)
        self.assert_conflict(create(self.root, title="Two"), "different values", "title")
        self.assert_conflict(create(self.root, port=4999), "port")
        self.assert_conflict(create(self.root, aliases=("x",)), "aliases")
        self.assert_conflict(create(self.root, title="One", environment="production"), "environment")
        self.assertEqual(h.snapshot(self.root), before)

    def test_existing_unregistered_folder_is_never_written(self):
        site = self.root / "sites" / "example.com"
        site.mkdir(parents=True)
        (site / "mine.txt").write_text("keep")
        before = h.snapshot(self.root)
        self.assert_conflict(create(self.root), "adopt")
        self.assertEqual(h.snapshot(self.root), before)

    def test_empty_existing_folder_is_allowed_and_survives_rollback(self):
        (self.root / "sites" / "example.com").mkdir(parents=True)
        self.assertEqual(create(self.root)["state"], "created")

    def test_alias_name_and_port_collisions(self):
        create(self.root, "a.example", aliases=("shared",))
        before = h.snapshot(self.root)
        self.assert_conflict(create(self.root, "b.example", aliases=("SHARED",)), "already a name or alias of site 'a.example'")
        self.assert_conflict(create(self.root, "b.example", aliases=("a.example",)), "a.example")
        self.assert_conflict(create(self.root, "b.example", port=4321), "port 4321")
        self.assertEqual(h.snapshot(self.root), before)

    def test_modified_generated_file_makes_a_repeat_a_conflict_naming_verify(self):
        create(self.root)
        page = self.root / "sites/example.com/src/pages/index.astro"
        page.write_text("repaired\n")
        before = h.snapshot(self.root)
        result = create(self.root)
        self.assert_conflict(result, "managed file modified", "index.astro", "setup verify", "not available")
        self.assertEqual(h.snapshot(self.root), before)
        self.assertEqual(page.read_text(), "repaired\n")

    def test_missing_generated_file_is_a_conflict_not_a_silent_recreate(self):
        create(self.root)
        (self.root / "sites/example.com/tsconfig.json").unlink()
        self.assert_conflict(create(self.root), "managed file missing")
        self.assertFalse((self.root / "sites/example.com/tsconfig.json").exists())

    def test_site_without_ownership_record_is_not_taken_over_by_create(self):
        create(self.root)
        (self.root / ".project/specs/website.managed.json").unlink()
        before = h.snapshot(self.root)
        self.assert_conflict(create(self.root), "without an ownership record", "adopt")
        self.assertEqual(h.snapshot(self.root), before)

    def test_a_manifest_with_the_removed_type_is_rejected_and_left_untouched(self):
        root = h.repo()
        specs = root / ".project" / "specs"
        specs.mkdir(parents=True)
        (specs / "website.schema.json").write_bytes(static_setup.load_schema_bytes())
        old = {"version": 2, "components": [{"name": "example.com", "path": "sites/example.com", "type": "astro",
                                              "serve": {"mode": "behind-proxy", "network": "public"}}]}
        (specs / "website.json").write_text(json.dumps(old))
        (root / "sites" / "example.com").mkdir(parents=True)
        before = h.snapshot(root)
        result = create(root)
        self.assertEqual((result["state"], result["exit"]), ("invalid", 1), result)
        self.assertIn("existing manifest is invalid", " ".join(result["problems"]))
        self.assertEqual(h.snapshot(root), before)

    def test_other_site_content_is_never_touched(self):
        create(self.root, "a.example")
        (self.root / "sites/a.example/src/pages/extra.astro").write_text("mine\n")
        before = h.sub(h.snapshot(self.root), "sites/a.example")
        create(self.root, "b.example")
        self.assertEqual(h.sub(h.snapshot(self.root), "sites/a.example"), before)

    def test_custom_schema_copy_is_a_conflict_with_a_comparison(self):
        specs = self.root / ".project" / "specs"
        specs.mkdir(parents=True)
        (specs / "website.schema.json").write_text('{"type": "object", "custom": true}\n')
        before = h.snapshot(self.root)
        result = create(self.root)
        self.assert_conflict(result, "no ownership record", "never replaced automatically")
        self.assertEqual(h.snapshot(self.root), before)
        plan = static_setup.plan_only(h.opts("create", root=self.root))
        self.assertIn({"path": ".project/specs/website.schema.json", "action": "conflict",
                       "reason": "schema copy is custom, unknown or modified"}, plan["changes"])

    def test_schema_modified_after_setup_wrote_it_is_a_conflict(self):
        create(self.root, "a.example")
        schema = self.root / ".project/specs/website.schema.json"
        schema.write_text(schema.read_text() + "\n")
        before = h.snapshot(self.root)
        self.assert_conflict(create(self.root, "b.example"), "modified after setup wrote it")
        self.assertEqual(h.snapshot(self.root), before)


class InvalidTests(unittest.TestCase):                                        # S7
    def setUp(self):
        self.root = h.repo()

    def assert_invalid_and_untouched(self, result, text=None):
        self.assertEqual((result["state"], result["exit"]), ("invalid", 1), result)
        if text:
            self.assertIn(text, " ".join(result["problems"]))

    def test_bad_inputs_write_nothing(self):
        before = h.snapshot(self.root)
        cases = [({"domain": "Not A Domain"}, "not a valid site ID"), ({"port": 80}, "--port"), ({"title": "  "}, "--title"),
                 ({"aliases": ("a b ",)}, "--alias"), ({"aliases": ("x", "X")}, "unique"), ({"environment": "a b"}, "--environment"),
                 ({"site_type": "nope"}, "Unsupported type")]
        for kw, text in cases:
            kw = dict(kw)
            domain = kw.pop("domain", "example.com")
            self.assert_invalid_and_untouched(create(self.root, domain, **kw), text)
        self.assertEqual(h.snapshot(self.root), before)

    def test_missing_type_and_domain_ask(self):
        self.assertEqual(static_setup.execute(h.opts("create", root=self.root, site_type=None))["state"], "needs-input")
        self.assertEqual(static_setup.execute(h.opts("create", site=None, root=self.root))["exit"], 2)

    def test_path_escapes(self):
        outside = h.repo()
        for bad in ("../x", "/abs/path", "a/../b", "a//b", "./sites", "sites/", "..", "C:\\x", "a b"):
            before = h.snapshot(self.root)
            self.assert_invalid_and_untouched(create(self.root, sites_dir=bad), "--path")
            self.assertEqual(h.snapshot(self.root), before, bad)
        self.assertEqual(h.snapshot(outside), {})

    def test_symlinked_sites_folder_is_not_written_through(self):
        outside = h.repo()
        (self.root / "sites").symlink_to(outside)
        self.assert_invalid_and_untouched(create(self.root), "symlink")
        self.assertEqual(h.snapshot(outside), {})
        self.assertEqual(h.snapshot(self.root), {"sites": "link:" + str(outside)})

    def test_symlinked_target_folder_and_project_specs_and_gitignore(self):
        outside = h.repo()
        (self.root / "sites").mkdir()
        (self.root / "sites" / "example.com").symlink_to(outside)
        self.assert_invalid_and_untouched(create(self.root), "symlink")
        (self.root / "sites" / "example.com").unlink()
        (self.root / ".project").mkdir()
        (self.root / ".project" / "specs").symlink_to(outside)
        self.assert_invalid_and_untouched(create(self.root), "symlink")
        (self.root / ".project" / "specs").unlink()
        (self.root / ".gitignore").symlink_to(outside / "target")
        self.assert_invalid_and_untouched(create(self.root), "symlink")
        self.assertEqual(h.snapshot(outside), {})

    def test_selected_folder_works_without_git_and_inside_a_parent_repository(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp)
            self.assertEqual(create(plain)["state"], "created")
            self.assertFalse((plain / ".git").exists())
        sub = self.root / "inner"
        sub.mkdir()
        self.assertEqual(create(sub)["state"], "created")
        self.assertFalse((sub / ".git").exists())

    def test_invalid_manifest_json_schema_and_record_stop_before_writing(self):
        specs = self.root / ".project" / "specs"
        specs.mkdir(parents=True)
        manifest = specs / "website.json"
        for text, word in (("{not json", "not valid JSON"), ('{"version": 1, "components": []}', "version"),
                           ('{"version": 2, "components": [{"name": "x.at", "path": "../x", "type": "astro-static"}]}', "path"),
                           ('{"version": 2, "components": [{"name": "x.at", "path": "sites/x.at", "type": "astro-static", "serve": {"mode": "standalone"}}]}', "serve"),
                           ('{"version": 2, "registry": "ghcr.io", "components": []}', "registry"),
                           ('["a"]', "")):
            manifest.write_text(text)
            before = h.snapshot(self.root)
            self.assert_invalid_and_untouched(create(self.root), word or None)
            self.assertEqual(h.snapshot(self.root), before, text)
        manifest.write_text('{"version": 2, "components": []}')
        (specs / "website.managed.json").write_text("not json")
        before = h.snapshot(self.root)
        self.assert_invalid_and_untouched(create(self.root), "not valid JSON")
        self.assertEqual(h.snapshot(self.root), before)

    def test_unresolved_placeholder_in_the_title_is_invalid(self):
        self.assert_invalid_and_untouched(create(self.root, title="Bad {{thing}}"), "Unresolved placeholders")
        self.assertEqual(h.snapshot(self.root), {})

    def test_removed_type_is_rejected_and_not_translated(self):
        self.assert_invalid_and_untouched(create(self.root, site_type="astro"), "Unsupported type 'astro'")
        self.assertEqual(h.snapshot(self.root), {})


class PlanEqualsRunTests(unittest.TestCase):                                  # S10
    def prepare(self):
        root = h.repo()
        create(root, "a.example", aliases=("shared",))
        site = h.make_static_site(root, "adopt.example")
        (root / "sites" / "folder.example").mkdir()
        (root / "sites" / "folder.example" / "x").write_text("x")
        return root, site

    def cases(self):
        return [("create ok", "create", dict(domain="new.example")),
                ("create repeat", "create", dict(domain="a.example", aliases=("shared",))),
                ("create differing", "create", dict(domain="a.example", title="other")),
                ("create existing folder", "create", dict(domain="folder.example")),
                ("create alias collision", "create", dict(domain="new.example", aliases=("shared",))),
                ("create bad path", "create", dict(domain="new.example", sites_dir="../x")),
                ("create bad port", "create", dict(domain="new.example", port=1)),
                ("create missing type", "create", dict(domain="new.example", site_type=None)),
                ("adopt ok", "adopt", dict(domain="adopt.example")),
                ("adopt missing folder", "adopt", dict(domain="absent.example")),
                ("adopt registered other", "adopt", dict(domain="a.example"))]

    def test_plan_and_execution_give_the_same_verdict_and_changes_and_plan_writes_nothing(self):
        for label, operation, kw in self.cases():
            root, _ = self.prepare()
            domain = kw.pop("domain")
            kw.setdefault("site_type", "astro-static" if operation == "create" else None)
            options = static_setup.Options(operation=operation, site=domain, root=str(root), **kw)
            before = h.snapshot(root)
            with mock.patch.object(static_setup, "default_runner", h.NoRun()):
                planned = static_setup.plan_only(options)
            self.assertEqual(h.snapshot(root), before, f"plan wrote something: {label}")
            self.assertFalse(any(r["ran"] for r in planned["verification"].values()), label)
            ran = static_setup.execute(options, h.NoRun())
            expected = {"planned": "created" if operation == "create" else "adopted"}.get(planned["state"], planned["state"])
            self.assertEqual(ran["state"], expected, label)
            self.assertEqual(ran["changes"], planned["changes"], label)
            self.assertEqual(ran["problems"] if "problems" in ran else None, planned.get("problems"), label)
            self.assertEqual(ran["findings"], planned["findings"], label)
            if planned["state"] != "planned":
                self.assertEqual(h.snapshot(root), before, f"refused run wrote something: {label}")

    def test_plan_with_build_flag_still_runs_nothing(self):
        root = h.repo()
        before = h.snapshot(root)
        with mock.patch.object(static_setup, "default_runner", h.NoRun()):
            result = static_setup.plan_only(h.opts("create", root=root, build=True))
        self.assertEqual((result["state"], result["exit"]), ("planned", 0))
        self.assertEqual(h.snapshot(root), before)
        self.assertFalse((root / "sites").exists())


class RollbackTests(unittest.TestCase):                                       # S8
    def setUp(self):
        self.root = h.repo()
        (self.root / ".gitignore").write_text("existing/\n")
        create(self.root, "a.example")
        self.before = h.snapshot(self.root)

    def fail_nth_replace(self, n):
        real, calls = static_setup.os.replace, []

        def failing(src, dst):
            calls.append(dst)
            if len(calls) == n:
                raise OSError("injected rename failure")
            return real(src, dst)
        return mock.patch.object(static_setup, "_replace", failing)

    def test_rename_failure_at_every_position_restores_everything(self):
        writes = len(static_setup.make_plan(h.opts("create", "b.example", self.root)).writes)
        self.assertGreater(writes, 40)
        for position in (1, 2, 25, writes - 4, writes - 3, writes - 2, writes - 1):   # site file, .gitignore, schema? record, manifest
            with self.fail_nth_replace(position):
                result = create(self.root, "b.example")
            self.assertEqual((result["state"], result["exit"]), ("failed-rolled-back", 1), (position, result))
            self.assertIn("injected", result["error"])
            self.assertEqual(h.snapshot(self.root), self.before, f"position {position}")
            self.assertEqual(h.manifest_of(self.root)["components"][-1]["name"], "a.example")
        self.assertEqual(create(self.root, "b.example")["state"], "created")        # retry from scratch works

    def test_failure_on_the_manifest_rename_removes_the_registration(self):
        total = len(static_setup.make_plan(h.opts("create", "b.example", self.root)).writes)
        with self.fail_nth_replace(total - 1):         # last file write = manifest
            result = create(self.root, "b.example")
        self.assertEqual(result["state"], "failed-rolled-back")
        self.assertNotIn("b.example", [c["name"] for c in h.manifest_of(self.root)["components"]])
        self.assertNotIn("b.example", h.record_of(self.root)["sites"])
        self.assertFalse((self.root / "sites" / "b.example").exists())

    def test_first_ever_create_leaves_no_trace_after_a_failure(self):
        root = h.repo()
        with self.fail_nth_replace(10):
            result = create(root)
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual(h.snapshot(root), {})
        self.assertEqual(create(root)["state"], "created")

    def test_unwritable_target_rolls_back(self):
        site = self.root / "sites" / "b.example"
        original, seen = static_setup._write_all, []

        def failing(fd, data):
            seen.append(fd)
            if len(seen) == 7:
                raise PermissionError("injected: read-only")
            return original(fd, data)
        with mock.patch.object(static_setup, "_write", failing):
            result = create(self.root, "b.example")
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual(h.snapshot(self.root), self.before)
        self.assertFalse(site.exists())

    def test_verification_failure_before_the_build_rolls_back_and_runs_no_build(self):
        runner = h.FakeRunner()
        with mock.patch.object(static_setup, "verify_written", lambda plan: ["injected verification problem"]):
            result = static_setup.execute(h.opts("create", "b.example", self.root, build=True), runner)
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual(runner.calls, [])
        self.assertEqual(h.snapshot(self.root), self.before)

    def test_incomplete_rollback_is_failed_partial_with_the_exact_remainder(self):
        with self.fail_nth_replace(30), mock.patch.object(static_setup, "_unlink", side_effect=OSError("injected: cannot delete")):
            result = create(self.root, "b.example")
        self.assertEqual((result["state"], result["exit"]), ("failed-partial", 1), result)
        self.assertTrue(result["remaining"])
        self.assertTrue(result["rollback_errors"])
        left = {k for k in h.snapshot(self.root) if k not in self.before}
        for rel in left:
            if not rel.endswith("/") and (self.root / rel).is_file():
                self.assertTrue(any(rel in item for item in result["remaining"]), rel)
        text = static_setup.render_text(result)
        self.assertIn("remaining after the failed rollback", text)
        self.assertNotIn(": created", text)


class BuildFailureTests(unittest.TestCase):                                   # S9, S16 (offline variants)
    def setUp(self):
        self.root = h.repo()

    def build(self, **results):
        return static_setup.execute(h.opts("create", root=self.root, build=True), h.FakeRunner(**results))

    def steps(self, result):
        return {n: (s["ran"], s["exit"]) for n, s in result["verification"].items()}

    def test_failing_build(self):
        result = self.build(build=(True, 3, "line1\nERROR in page"))
        self.assertEqual((result["state"], result["exit"], result["failed_step"]), ("failed-build", 1, "build"))
        self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 3), "check": (False, None)})
        self.assertEqual(result["output_tail"], ["line1", "ERROR in page"])
        self.assertEqual(result["lockfile"], "created")
        self.assertIn("node_modules/", result["local_output"])
        text = static_setup.render_text(result)
        self.assertIn("package-lock.json: created (versioned file created by npm, review; no commit required for local work)", text)
        self.assertNotIn(": created\n", text.split("\n", 1)[0] + "\n")
        self.assertIn("failed-build", text.splitlines()[0])
        self.assertTrue((self.root / "sites/example.com/package.json").is_file())
        self.assertEqual([c["name"] for c in h.manifest_of(self.root)["components"]], ["example.com"])
        self.assertIn("example.com", h.record_of(self.root)["sites"])

    def test_failing_check(self):
        result = self.build(check=(True, 5, "a11y problem"))
        self.assertEqual((result["state"], result["exit"], result["failed_step"]), ("failed-check", 1, "check"))
        self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 0), "check": (True, 5)})

    def test_failing_install(self):
        result = self.build(install=(True, 1, "network down"))
        self.assertEqual(result["state"], "failed-build")
        self.assertEqual(self.steps(result), {"install": (True, 1), "build": (False, None), "check": (False, None)})

    def test_build_that_exits_zero_without_output_folder_is_not_a_success(self):
        class NoDist(h.FakeRunner):
            def __call__(self, argv, cwd):
                ran, code, out = super().__call__(argv, cwd)
                if argv[-1] == "build":
                    import shutil
                    shutil.rmtree(Path(cwd) / "dist")
                return ran, code, out
        result = static_setup.execute(h.opts("create", root=self.root, build=True), NoDist())
        self.assertEqual(result["state"], "failed-build")
        self.assertEqual(self.steps(result)["build"], (True, 0))
        self.assertIn("does not exist", " ".join(result["output_tail"]))

    def test_command_that_cannot_start_did_not_run(self):
        result = self.build(install=(False, None, "command not found: npm"))
        self.assertEqual(self.steps(result), {"install": (False, None), "build": (False, None), "check": (False, None)})
        self.assertEqual(result["state"], "failed-build")

    def test_without_build_nothing_is_claimed(self):
        result = create(self.root)
        self.assertTrue(all(not s["ran"] for s in result["verification"].values()))
        self.assertNotIn("builds", static_setup.render_text(result))

    def test_s16_repair_then_verify_keeps_the_repair_byte_identical(self):
        failed = self.build(build=(True, 1, "page broken"))
        self.assertEqual(failed["state"], "failed-build")
        repaired = self.root / "sites/example.com/src/pages/index.astro"
        repaired.write_text("---\n---\n<h1>repaired by a person</h1>\n")
        repair_hash = h.snapshot(self.root)["sites/example.com/src/pages/index.astro"]
        record_before = (self.root / ".project/specs/website.managed.json").read_bytes()
        before = h.snapshot(self.root)
        for _ in range(2):                                           # verify repeated: same result
            result = static_setup.verify(h.opts("verify", root=self.root), h.FakeRunner())
            self.assertEqual((result["state"], result["exit"]), ("verified", 0), result)
            self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 0), "check": (True, 0)})
            self.assertIn({"path": "sites/example.com/src/pages/index.astro", "action": "keep", "reason": "modified (kept)"}, result["changes"])
        after = h.snapshot(self.root)
        self.assertEqual(after["sites/example.com/src/pages/index.astro"], repair_hash)
        self.assertEqual((self.root / ".project/specs/website.managed.json").read_bytes(), record_before)
        changed = {k for k in after if before.get(k) != after[k]}
        self.assertTrue(all(k.startswith("sites/example.com/") and k.split("/")[2] in ("dist", "node_modules", "package-lock.json")
                            for k in changed), changed)
        again = create(self.root)                                    # create afterwards: conflict naming verify
        self.assertEqual(again["state"], "conflict")
        self.assertIn("setup verify", " ".join(again["problems"]))

    def test_verify_reports_check_and_build_failures_with_real_codes(self):
        create(self.root)
        result = static_setup.verify(h.opts("verify", root=self.root), h.FakeRunner(check=(True, 7, "x")))
        self.assertEqual((result["state"], result["exit"]), ("failed-check", 1))
        self.assertEqual(self.steps(result), {"install": (True, 0), "build": (True, 0), "check": (True, 7)})

    def test_verify_preconditions(self):
        r = static_setup.verify(h.opts("verify", root=self.root), h.NoRun())
        self.assertEqual(r["state"], "invalid")
        create(self.root)
        self.assertEqual(static_setup.verify(h.opts("verify", "other.example", self.root), h.NoRun())["state"], "invalid")
        self.assertEqual(static_setup.verify(h.opts("verify", None, self.root), h.NoRun())["state"], "needs-input")
        (self.root / "sites/example.com/package.json").unlink()
        self.assertEqual(static_setup.verify(h.opts("verify", root=self.root), h.NoRun())["state"], "invalid")
        import shutil
        shutil.rmtree(self.root / "sites/example.com")
        self.assertIn("folder missing", " ".join(static_setup.verify(h.opts("verify", root=self.root), h.NoRun())["problems"]))


class CliTests(unittest.TestCase):                                            # S12, S14, S11
    def setUp(self):
        self.root = h.repo()

    def test_create_json_output_shape(self):
        code, out = cli(self.root, "create", "example.com", "--type", "astro-static", "--json")
        data = json.loads(out)
        self.assertEqual((code, data["state"], data["operation"], data["site"]), (0, "created", "create", "example.com"))
        self.assertEqual(set(data), {"state", "operation", "site", "changes", "findings", "notes", "verification", "exit"})
        self.assertEqual(data["verification"]["build"], {"ran": False, "exit": None})
        self.assertEqual(set(data["changes"][0]), {"path", "action", "reason"})

    def test_plan_names_the_operation_and_writes_nothing(self):
        before = h.snapshot(self.root)
        code, out = cli(self.root, "plan", "create", "example.com", "--type", "astro-static")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("setup create example.com: planned"))
        self.assertEqual(h.snapshot(self.root), before)

    def test_plan_without_operation_is_not_available(self):
        before = h.snapshot(self.root)
        for argv in (("plan", "example.com"), ("plan",)):
            code, out = cli(self.root, *argv)
            self.assertEqual(code, 1)
            self.assertIn("needs the operation", out)
        self.assertEqual(h.snapshot(self.root), before)

    def test_unimplemented_commands_are_refused_clearly(self):
        for argv, word in ((("update", "example.com"), "setup update is not available"),
                           (("create", "example.com", "--type", "astro-static", "--add-missing"), "--add-missing is not available"),
                           (("verify", "example.com", "--adopt-edits"), "--adopt-edits is not available"),
                           (("update", "example.com", "--regenerate", "package.json"), "--regenerate is not available")):
            code, out = cli(self.root, *argv)
            self.assertEqual(code, 1, argv)
            self.assertIn("STOP:", out)
            self.assertIn(word, out) if "--regenerate" not in argv else self.assertIn("is not available", out)
        self.assertEqual(h.snapshot(self.root), {})

    def test_exit_codes(self):
        self.assertEqual(cli(self.root, "create", "example.com")[0], 2)                         # type missing -> ask
        self.assertEqual(cli(self.root, "create", "Bad", "--type", "astro-static")[0], 1)
        self.assertEqual(cli(self.root, "create", "example.com", "--type", "astro-static")[0], 0)
        self.assertEqual(cli(self.root, "create", "example.com", "--type", "astro-static")[0], 0)   # unchanged
        self.assertEqual(cli(self.root, "create", "example.com", "--type", "astro-static", "--title", "x")[0], 1)

    def test_options_of_the_removed_docker_path_are_argument_errors_and_write_nothing(self):
        for option in (["--legacy-docker"], ["--serve", "behind-proxy"], ["--network", "public"], ["--host", "a.example"], ["--email", "a@b.example"]):
            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                    site_setup.main(["create", "example.com", "--type", "astro-static", *option, "--root", str(self.root)])
            self.assertEqual(raised.exception.code, 2, option)
            self.assertEqual(h.snapshot(self.root), {}, option)

    def test_removed_type_is_rejected_by_create_and_plan_and_writes_nothing(self):
        for argv in (("create", "example.com", "--type", "astro"), ("plan", "create", "example.com", "--type", "astro")):
            code, out = cli(self.root, *argv)
            self.assertEqual(code, 1, argv)
            self.assertIn("Unsupported type 'astro'", out)
            self.assertEqual(h.snapshot(self.root), {})

    def test_two_sites_of_the_one_type_share_one_manifest(self):
        self.assertEqual(cli(self.root, "create", "first.example", "--type", "astro-static")[0], 0)
        code, out = cli(self.root, "create", "static.example", "--type", "astro-static")
        self.assertEqual(code, 0, out)
        self.assertEqual([c["type"] for c in h.manifest_of(self.root)["components"]], ["astro-static", "astro-static"])
        self.assertEqual(cli(self.root, "create", "static.example", "--type", "astro-static")[0], 0)      # identical repetition

    def test_no_option_accepts_a_secret_and_outputs_carry_no_token(self):
        for flag in ("--token", "--password", "--secret", "--key", "--ssh-key"):
            with self.assertRaises(SystemExit):
                with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                    site_setup.build_parser().parse_args(["create", "example.com", flag, "x"])
        outputs = [cli(self.root, "plan", "create", "example.com", "--type", "astro-static")[1],
                   cli(self.root, "create", "example.com", "--type", "astro-static", "--json")[1],
                   cli(self.root, "create", "example.com", "--type", "astro-static", "--build", runner=h.FakeRunner(build=(True, 1, "x")))[1],
                   cli(self.root, "verify", "example.com")[1]]
        shaped = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*KEY|xox[abp]-|\b[0-9a-f]{40,}\b)")
        for text in outputs:
            self.assertIsNone(shaped.search(text), text)


if __name__ == "__main__":
    unittest.main()
