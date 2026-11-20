"""Manifest version 2 acceptance: site ID vs. domain, domainless projects, version-1 refusal, consistency at every runtime entry point,
later domain assignment. Fictional projects, fake npm, no network, no git."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import setup_paths as sp
from tests.support import setup_helpers as h
import static_setup

SKILLS = sp.ROOT / "skills"
RESOLVER = SKILLS / "_shared/scripts/which_site.py"
PREVIEW = SKILLS / "preview/scripts/preview.py"
CONTROL = SKILLS / "preview/scripts/control.py"
AUDIT = SKILLS / "optimize/scripts/audit.py"
EDIT = SKILLS / "edit/scripts/edit.py"
SETUP = SKILLS / "setup/scripts/site_setup.py"


def project():
    return Path(tempfile.mkdtemp()).resolve()          # a plain folder: no git needed for local work


def create(root, site="physio-wien", domain=None, **kw):
    return static_setup.execute(h.opts("create", site, root, domain=domain, **kw), h.FakeRunner())


def manifest(root):
    return h.manifest_of(root)["components"][0]


def run(script, *args, state=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    if state:
        env["ZYRIS_WEBSITE_STATE_DIR"] = str(state)
    done = subprocess.run([sys.executable, "-I", "-B", str(script), *args], capture_output=True, text=True, env=env, timeout=60)
    return done.returncode, done.stdout + done.stderr


ENTRIES = {
    "resolver": lambda root, state: run(RESOLVER, "--root", str(root)),
    "preview": lambda root, state: run(PREVIEW, "--root", str(root)),
    "control-start": lambda root, state: run(CONTROL, "start", "--root", str(root), "--timeout", "3", state=state),
    "optimize": lambda root, state: run(AUDIT, "audit", "--root", str(root), "--npm", "/nonexistent/npm"),
    "edit": lambda root, state: run(EDIT, "preflight", "--root", str(root)),
    "setup-verify": lambda root, state: run(SETUP, "verify", "physio-wien", "--root", str(root)),
}


class IdentityAndDomainTests(unittest.TestCase):
    def setUp(self):
        self.root = project()

    def test_explicit_domain_is_stored_and_used_everywhere(self):
        result = create(self.root, "physio-wien", domain="demo-a.com")
        self.assertEqual(result["state"], "created", result)
        comp = manifest(self.root)
        self.assertEqual((comp["name"], comp["domain"], comp["path"]), ("physio-wien", "demo-a.com", "sites/physio-wien"))
        self.assertEqual(h.manifest_of(self.root)["version"], 2)
        site = self.root / "sites/physio-wien"
        self.assertIn("site: 'https://demo-a.com',", (site / "astro.config.mjs").read_text())
        self.assertIn("export const SITE: string | null = \"https://demo-a.com\";", (site / "src/lib/site.ts").read_text())
        self.assertEqual(static_setup.consistency.check(self.root, comp), {"conflicts": [], "unverifiable": []})

    def test_without_domain_no_domain_no_invented_url(self):
        result = create(self.root, "physio-wien")
        self.assertEqual(result["state"], "created", result)
        comp = manifest(self.root)
        self.assertNotIn("domain", comp)
        site = self.root / "sites/physio-wien"
        self.assertNotIn("site:", (site / "astro.config.mjs").read_text())
        self.assertIn("SITE: string | null = null;", (site / "src/lib/site.ts").read_text())
        for path in site.rglob("*"):
            if path.is_file() and path.suffix not in {".png"}:
                text = path.read_text(encoding="utf-8")
                for forbidden in ("https://physio-wien", "http://physio-wien", "physio-wien.at", "example.com"):
                    self.assertNotIn(forbidden, text, f"{path.name}: {forbidden}")
        self.assertEqual(static_setup.consistency.check(self.root, comp), {"conflicts": [], "unverifiable": []})

    def test_site_id_is_independent_of_the_domain(self):
        create(self.root, "demo-a.com", domain="other.example")
        comp = manifest(self.root)
        self.assertEqual((comp["name"], comp["domain"]), ("demo-a.com", "other.example"))
        self.assertIn("'https://other.example'", (self.root / "sites/demo-a.com/astro.config.mjs").read_text())
        self.assertNotIn("https://demo-a.com", (self.root / "sites/demo-a.com/astro.config.mjs").read_text())

    def test_invalid_domain_is_refused_before_writing(self):
        before = h.snapshot(self.root)
        result = create(self.root, "physio-wien", domain="Not A Domain")
        self.assertEqual((result["state"], result["exit"]), ("invalid", 1))
        self.assertEqual(h.snapshot(self.root), before)

    def test_domain_of_another_site_is_a_conflict(self):
        create(self.root, "one", domain="a.example")
        before = h.snapshot(self.root)
        result = create(self.root, "two", domain="a.example")
        self.assertEqual(result["state"], "conflict", result)
        self.assertEqual(h.snapshot(self.root), before)

    def test_repeat_is_unchanged_and_a_changed_domain_is_a_conflict(self):
        create(self.root, "physio-wien", domain="demo-a.com")
        before = h.snapshot(self.root)
        self.assertEqual(create(self.root, "physio-wien", domain="demo-a.com")["state"], "unchanged")
        self.assertEqual(create(self.root, "physio-wien")["state"], "conflict")
        self.assertEqual(create(self.root, "physio-wien", domain="other.example")["state"], "conflict")
        self.assertEqual(h.snapshot(self.root), before)

    def test_plan_equals_the_run_and_writes_nothing(self):
        before = h.snapshot(self.root)
        plan = static_setup.plan_only(h.opts("create", "physio-wien", self.root, domain="demo-a.com"))
        self.assertEqual((plan["state"], plan["exit"]), ("planned", 0), plan)
        self.assertEqual(h.snapshot(self.root), before)


class SetDomainTests(unittest.TestCase):
    def setUp(self):
        self.root = project()
        create(self.root, "physio-wien")

    def set_domain(self, domain="demo-a.com", plan=False):
        return static_setup.set_domain(static_setup.Options("set-domain", "physio-wien", root=str(self.root), domain=domain), plan_only_mode=plan)

    def test_identity_path_port_and_record_keys_survive(self):
        before_comp = manifest(self.root)
        before_record = h.record_of(self.root)
        result = self.set_domain()
        self.assertEqual((result["state"], result["exit"]), ("updated", 0), result)
        comp = manifest(self.root)
        self.assertEqual({k: v for k, v in comp.items() if k != "domain"}, before_comp)
        self.assertEqual(comp["domain"], "demo-a.com")
        record = h.record_of(self.root)
        self.assertEqual(set(record["sites"]), set(before_record["sites"]))
        changed = {rel for rel, sha in record["sites"]["physio-wien"]["files"].items() if sha != before_record["sites"]["physio-wien"]["files"][rel]}
        self.assertEqual(changed, {"astro.config.mjs", "src/lib/site.ts"})
        self.assertEqual(static_setup.consistency.check(self.root, comp), {"conflicts": [], "unverifiable": []})
        self.assertEqual(self.set_domain()["state"], "unchanged")           # idempotent

    def test_plan_writes_nothing(self):
        before = h.snapshot(self.root)
        self.assertEqual(self.set_domain(plan=True)["state"], "planned")
        self.assertEqual(h.snapshot(self.root), before)

    def test_modified_generated_file_is_a_conflict_without_any_write(self):
        lib = self.root / "sites/physio-wien/src/lib/site.ts"
        lib.write_text(lib.read_text() + "// my edit\n")
        before = h.snapshot(self.root)
        result = self.set_domain()
        self.assertEqual(result["state"], "conflict", result)
        self.assertEqual(h.snapshot(self.root), before)

    def test_a_decided_domain_cannot_be_changed_here(self):
        self.set_domain("demo-a.com")
        before = h.snapshot(self.root)
        self.assertEqual(self.set_domain("other.example")["state"], "conflict")
        self.assertEqual(h.snapshot(self.root), before)

    def test_missing_or_invalid_domain(self):
        self.assertEqual(self.set_domain(None)["state"], "needs-input")
        self.assertEqual(self.set_domain("nope")["state"], "invalid")

    def test_write_failure_rolls_back_every_file(self):
        before = h.snapshot(self.root)
        calls = []
        real = static_setup._replace

        def failing(src, dst):
            calls.append(dst)
            if len(calls) == 3:
                raise OSError("disk full")
            return real(src, dst)
        static_setup._replace = failing
        try:
            result = self.set_domain()
        finally:
            static_setup._replace = real
        self.assertEqual(result["state"], "failed-rolled-back", result)
        self.assertEqual(h.snapshot(self.root), before)


class VersionOneTests(unittest.TestCase):
    def test_every_entry_refuses_version_1_without_side_effects(self):
        root = project()
        create(root, "physio-wien", domain="demo-a.com")
        file = root / ".project/specs/website.json"
        data = json.loads(file.read_text())
        data["version"] = 1
        file.write_text(json.dumps(data, indent=2) + "\n")
        state = Path(tempfile.mkdtemp()) / "state"
        before = h.snapshot(root)
        for name, call in ENTRIES.items():
            code, out = call(root, state)
            self.assertEqual(code, 1, (name, out))
            self.assertIn("version 1", out, name)
            self.assertIn("not migrated", out.replace("Version 1 is not migrated", "not migrated"), name)
            self.assertEqual(h.snapshot(root), before, name)
        self.assertFalse(state.exists())
        for args in (("create", "other", "--type", "astro-static"), ("adopt", "physio-wien"), ("set-domain", "physio-wien", "demo-a.com")):
            code, out = run(SETUP, *args, "--root", str(root))
            self.assertEqual(code, 1, (args, out))
            self.assertIn("version 1", out)
            self.assertEqual(h.snapshot(root), before, args)

    def test_no_value_is_taken_over_from_the_site_files(self):
        root = project()
        create(root, "physio-wien", domain="demo-a.com")
        file = root / ".project/specs/website.json"
        data = json.loads(file.read_text())
        data["version"] = 1
        data["components"][0].pop("domain")
        file.write_text(json.dumps(data, indent=2) + "\n")
        code, out = run(RESOLVER, "--root", str(root))
        self.assertEqual(code, 1)
        self.assertNotIn("domain", json.loads(file.read_text())["components"][0])


class ConsistencyAtEntryPointsTests(unittest.TestCase):
    def setUp(self):
        self.root = project()
        create(self.root, "physio-wien", domain="demo-a.com")
        self.lib = self.root / "sites/physio-wien/src/lib/site.ts"
        self.state = Path(tempfile.mkdtemp()) / "state"

    def test_contradiction_stops_every_entry_before_any_change(self):
        self.lib.write_text(self.lib.read_text().replace("https://demo-a.com", "https://evil.example"))
        before = h.snapshot(self.root)
        for name, call in ENTRIES.items():
            code, out = call(self.root, self.state)
            self.assertEqual(code, 1, (name, out))
            self.assertIn("contradict", out, name)
            self.assertIn("https://evil.example", out, name)
            self.assertEqual(h.snapshot(self.root), before, name)             # nothing written, nothing repaired
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / ".claude").exists())

    def test_manifest_without_domain_but_site_with_url_is_a_contradiction(self):
        file = self.root / ".project/specs/website.json"
        data = json.loads(file.read_text())
        data["components"][0].pop("domain")
        file.write_text(json.dumps(data, indent=2) + "\n")
        code, out = run(PREVIEW, "--root", str(self.root))
        self.assertEqual(code, 1, out)
        self.assertIn("no site URL", out)

    def test_dynamic_configuration_is_reported_as_not_checkable_and_does_not_stop_reading(self):
        self.lib.write_text(self.lib.read_text().replace("\"https://demo-a.com\"", "process.env.PUBLIC_SITE"))
        code, out = run(RESOLVER, "--root", str(self.root))
        self.assertEqual(code, 0, out)
        found = json.loads(out)
        self.assertTrue(any("not reliably checkable" in text for text in found["consistency_unverifiable"]), found)

    def test_consistent_project_passes_resolver_and_preview(self):
        code, out = run(RESOLVER, "--root", str(self.root))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["domain"], "demo-a.com")
        self.assertEqual(json.loads(out)["consistency_unverifiable"], [])
        self.assertEqual(run(PREVIEW, "--root", str(self.root))[0], 0)

    def test_stop_and_status_do_not_need_a_consistent_configuration(self):
        self.lib.write_text(self.lib.read_text().replace("https://demo-a.com", "https://evil.example"))
        code, out = run(CONTROL, "status", "--root", str(self.root), state=self.state)
        self.assertNotIn("contradict", out)


class DomainlessLocalWorkTests(unittest.TestCase):
    def test_domainless_project_works_at_every_entry_and_does_not_invent_addresses(self):
        root = project()
        create(root, "physio-wien")
        state = Path(tempfile.mkdtemp()) / "state"
        code, out = run(RESOLVER, "--root", str(root))
        self.assertEqual(code, 0, out)
        found = json.loads(out)
        self.assertIsNone(found["domain"])
        self.assertEqual(found["consistency_unverifiable"], [])
        code, out = run(PREVIEW, "--root", str(root))
        self.assertEqual(code, 0, out)
        code, out = run(EDIT, "preflight", "--root", str(root))      # stops only for the missing install, not for the missing domain
        self.assertNotIn("contradict", out)
        self.assertIn("node_modules missing", out)

    def test_setup_verify_runs_on_a_domainless_project(self):
        root = project()
        create(root, "physio-wien")
        result = static_setup.verify(static_setup.Options("verify", "physio-wien", root=str(root)), h.FakeRunner())
        self.assertEqual((result["state"], result["exit"]), ("verified", 0), result)


class AdoptWithDomainTests(unittest.TestCase):
    def test_adopt_refuses_a_requested_domain_that_the_folder_contradicts(self):
        root = project()
        site = h.make_static_site(root, "legacy-site")
        (site / "astro.config.mjs").write_text("export default defineConfig({ site: 'https://real.example' });\n")
        (site / "src/lib").mkdir(parents=True)
        (site / "src/lib/site.ts").write_text("export const SITE = 'https://real.example';\n")
        before = h.snapshot(root)
        result = static_setup.execute(h.opts("adopt", "legacy-site", root, domain="other.example"), h.FakeRunner())
        self.assertEqual(result["state"], "invalid", result)
        self.assertEqual(h.snapshot(root), before)
        result = static_setup.execute(h.opts("adopt", "legacy-site", root, domain="real.example"), h.FakeRunner())
        self.assertEqual(result["state"], "adopted", result)
        self.assertEqual(manifest(root)["domain"], "real.example")

    def test_adopt_without_a_domain_refuses_a_folder_that_already_has_a_site_address(self):
        root = project()
        site = h.make_static_site(root, "legacy-site")
        (site / "astro.config.mjs").write_text("export default { site: 'https://real.example' };\n")
        before = h.snapshot(root)
        result = static_setup.execute(h.opts("adopt", "legacy-site", root), h.FakeRunner())
        self.assertEqual(result["state"], "invalid", result)
        self.assertTrue(any("real.example" in text for text in result["problems"]), result)
        self.assertEqual(h.snapshot(root), before)                       # nothing derived, nothing written
        stray = "const unused = defineConfig({});\nexport default { site: 'https://real.example' };\n"
        (site / "astro.config.mjs").write_text(stray)
        result = static_setup.execute(h.opts("adopt", "legacy-site", root), h.FakeRunner())
        self.assertEqual(result["state"], "adopted", result)               # not reliably checkable: reported as finding, not a verdict
        self.assertTrue(any("not reliably checkable" in f["text"] for f in result["findings"]), result["findings"])


if __name__ == "__main__":
    unittest.main()
