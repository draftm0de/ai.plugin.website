"""Contracts of the migrated `setup` skill: template identity against the source inventory (hash or explicit change list),
schema rename, skill text, narrow call patterns. Structural/text checks only: they prove no product behaviour."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "setup"
INVENTORY = json.loads((ROOT / "docs/migration/source-inventory.json").read_text())
PREFIX = INVENTORY["plugin_root"] + "/"
SOURCE = {e["path"][len(PREFIX):]: e["sha256"] for e in INVENTORY["files"] if e["path"].startswith(PREFIX)}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


# Deliberately adapted files: target -> (source path, [(new text, old text)]). Reversing the listed replacements must give back
# the recorded source bytes, i.e. the diff is exactly this list (docs/migration/changes.md).
ADAPTED_TEXT = {
    "templates/astro-static/CLAUDE.md.tpl": ("templates/setup/astro-static/CLAUDE.md.tpl", [
        ("the `preview` skill of the Website plugin", "`/zyris-website:preview`"),
        ("the `optimize` skill of the Website plugin", "`/zyris-website:optimize`"),
        ("# {{title}} (`{{name}}`)\n\n{{domain_line}}", "# {{title}} ({{domain}})"),
        ("`.project/specs/website.json`", "`.project/specs/zyris-website.json`")]),
    "templates/astro-static/rules/seo.md": ("templates/setup/astro-static/rules/seo.md", [
        ("the `optimize` skill of the Website plugin", "`/zyris-website:optimize`")]),
    "templates/_manifest/static/website.json.tpl": ("templates/setup/_manifest/static/zyris-website.json.tpl", [
        ("./website.schema.json", "./zyris-website.schema.json"), ('"version": 2', '"version": 1')]),
    "scripts/ownership.py": ("scripts/setup/ownership.py", [
        (".project/specs/website.schema.json", ".project/specs/zyris-website.schema.json"),
        (".project/specs/website.managed.json", ".project/specs/zyris-website.managed.json"),
        ('(see references/setup.md, section "Ownership record")', "(see contracts/setup.md section 4)"),
        # manifest version 2: site keys are site IDs (docs/development/manifest-v2-divergence.md)
        ('"<site-id>": {', '"<domain>": {'), ("site keys are site IDs (the manifest `name`)", "site keys are domain names"),
        ("SITE_ID_RE", "DOMAIN_RE"), ("is not a site ID", "is not a domain name")]),
}
# Adapted code files (imports, paths, port rule, legacy refusal): listed in changes.md, no hash identity expected.
ADAPTED_CODE = {"scripts/site_setup.py": "scripts/setup/site_setup.py", "scripts/static_setup.py": "scripts/setup/static_setup.py",
                "scripts/manifest.py": "scripts/setup/manifest.py"}
# Manifest version 2 (docs/development/manifest-v2-divergence.md): these files intentionally differ from the recorded source bytes.
# They must exist, really differ from the recorded hash (no silent identity claim) and be named in the divergence document.
V2_DIVERGED = {
    "templates/astro-static/astro.config.mjs.tpl", "templates/astro-static/scripts/seo-check.mjs",
    "templates/astro-static/src/layouts/BaseLayout.astro", "templates/astro-static/src/lib/site.ts.tpl",
    "templates/astro-static/src/pages/index.astro.tpl", "templates/astro-static/src/pages/robots.txt.ts",
    "templates/astro-static/src/pages/sitemap.xml.ts", "scripts/validate.py",
}
DIVERGENCE_DOC = (ROOT / "docs/development/manifest-v2-divergence.md").read_text(encoding="utf-8")
RENAMED = {"templates/setup/_manifest/static/zyris-website.json.tpl": "templates/setup/_manifest/static/website.json.tpl"}   # file name of the registry entry
NOT_MIGRATED_TEMPLATES = {"templates/setup/_manifest/root/zyris-website.schema.json"}   # moved to skills/_shared/resources/website.schema.json


class TemplateIdentityTests(unittest.TestCase):
    def test_every_inventoried_setup_template_is_identical_adapted_or_deliberately_moved(self):
        seen = 0
        for src, digest in SOURCE.items():
            if not src.startswith("templates/setup/"):
                continue
            if src in NOT_MIGRATED_TEMPLATES:
                continue
            target = SKILL / "templates" / RENAMED.get(src, src)[len("templates/setup/"):]
            self.assertTrue(target.is_file(), f"{src} missing in target")
            seen += 1
            if target.relative_to(SKILL).as_posix() in ADAPTED_TEXT:
                continue
            if target.relative_to(SKILL).as_posix() in V2_DIVERGED:
                self.assertNotEqual(sha(target), digest, f"{src}: listed as diverged but identical")
                continue
            self.assertEqual(sha(target), digest, f"{src} must be byte-identical")
        self.assertGreater(seen, 40)

    def test_adapted_files_differ_only_by_the_listed_replacements(self):
        for rel, (source, replacements) in ADAPTED_TEXT.items():
            text = (SKILL / rel).read_text(encoding="utf-8")
            for new, old in replacements:
                self.assertIn(new, text, (rel, new))
                text = text.replace(new, old)
            self.assertEqual(sha_bytes(text.encode()), SOURCE[source], f"{rel}: diff exceeds the change list")

    def test_diverged_files_differ_from_the_source_and_are_documented(self):
        for rel in sorted(V2_DIVERGED):
            source = SOURCE["templates/setup/" + rel[len("templates/"):]] if rel.startswith("templates/") else SOURCE["scripts/setup/" + rel[len("scripts/"):]]
            self.assertNotEqual(sha(SKILL / rel), source, rel)
            self.assertIn(Path(rel).name, DIVERGENCE_DOC, rel)

    def test_no_template_file_exists_in_the_target_that_the_source_did_not_have(self):
        known = {RENAMED.get(s, s)[len("templates/setup/"):] for s in SOURCE if s.startswith("templates/setup/")}
        for path in (SKILL / "templates").rglob("*"):
            if path.is_file():
                self.assertIn(path.relative_to(SKILL / "templates").as_posix(), known, path)

    def test_unchanged_runtime_modules_are_identical_to_the_source(self):
        for name in ("clone.py", "scratch.py", "errors.py"):
            self.assertEqual(sha(SKILL / "scripts" / name), SOURCE[f"scripts/setup/{name}"], name)

    def test_setup_scripts_that_were_not_migrated_are_recorded(self):
        migrated = {p.name for p in (SKILL / "scripts").glob("*.py")}
        for src in SOURCE:
            if src.startswith("scripts/setup/") and src.endswith(".py"):
                name = src.rsplit("/", 1)[1]
                if name in {"schema.py", "gitinfo.py"}:
                    self.assertNotIn(name, migrated, "shared project/manifest helpers replace this module")
                else:
                    self.assertIn(name, migrated, name)

    def test_adapted_code_files_are_in_the_change_list(self):
        changes = (ROOT / "docs/migration/changes.md").read_text()
        for target in list(ADAPTED_CODE) + list(ADAPTED_TEXT):
            self.assertIn(f"skills/setup/{target}", changes, target)

    def test_templates_carry_no_old_skill_call_names_or_old_schema_name(self):
        for path in (SKILL / "templates").rglob("*"):
            if path.is_file() and path.suffix not in {".png"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("/zyris-website:", text, path)
                self.assertNotIn("zyris-website.schema", text, path)


class SchemaRenameTests(unittest.TestCase):
    NEW = ROOT / "skills/_shared/resources/website.schema.json"

    def test_schema_deliberately_differs_from_the_recorded_source_for_version_2(self):
        self.assertNotEqual(sha(self.NEW), SOURCE["templates/setup/_manifest/root/zyris-website.schema.json"])
        self.assertIn("website.schema.json", (ROOT / "docs/development/manifest-v2-divergence.md").read_text(encoding="utf-8"))
        schema = json.loads(self.NEW.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["version"], {"const": 2})
        self.assertIn("domain", schema["$defs"]["component"]["properties"])

    def test_old_name_is_gone_from_the_plugin_payload_and_not_used_as_fallback(self):
        self.assertEqual(list((ROOT / "skills").rglob("zyris-website.schema.json")), [])
        self.assertFalse((SKILL / "templates/_manifest/root").exists())

    def test_old_schema_name_occurs_in_active_runtime_only_for_rejecting_the_old_format(self):
        allowed = {
            "skills/_shared/scripts/site_common/manifest.py",   # LEGACY_SCHEMA: recognised to refuse, never read
            "skills/setup/SKILL.md",                              # documents the refusal
            "skills/setup/references/setup.md",                   # documents the refusal
            "skills/optimize/SKILL.md",                           # documents the refusal (stage 4; optimize uses the shared detection)
            "skills/optimize/references/optimize.md",             # documents the refusal
            "skills/edit/SKILL.md",                               # documents the refusal (stage 5; edit uses the shared detection)
        }
        found = set()
        for path in (ROOT / "skills").rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".png":
                if "zyris-website.schema" in path.read_text(encoding="utf-8", errors="ignore"):
                    found.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(found, allowed)
        manifest_text = (ROOT / "skills/_shared/scripts/site_common/manifest.py").read_text()
        self.assertNotRegex(manifest_text, r"(read_text|read_bytes|open|load)\([^)]*LEGACY_SCHEMA")

    def test_unchanged_project_data_names(self):
        text = (SKILL / "scripts/ownership.py").read_text() + (SKILL / "scripts/manifest.py").read_text() + (ROOT / "skills/_shared/scripts/site_common/manifest.py").read_text()
        self.assertIn("website.managed.json", text)
        self.assertIn('FILE = "website.json"', text)


class SetupRuntimeContractTests(unittest.TestCase):
    def test_setup_scripts_import_only_stdlib_local_modules_and_site_common(self):
        stdlib = set(sys.stdlib_module_names)
        local = {p.stem for p in (SKILL / "scripts").glob("*.py")}
        for path in (SKILL / "scripts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                modules = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                          [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
                for module in modules:
                    top = module.split(".")[0]
                    self.assertTrue(top in stdlib or top in local or top == "site_common", f"{path.name}: {module}")

    def test_setup_does_not_depend_on_other_skills_or_the_repository_root(self):
        for path in (SKILL / "scripts").glob("*.py"):
            text = path.read_text()
            self.assertNotRegex(text, r"skills/(preview|optimize|edit|publish)", path.name)
            self.assertNotIn("parents[3]", text, path.name)
            self.assertNotRegex(text, r"ROOT / \"scripts\"", path.name)

    def test_setup_variants_of_errors_and_manifest_are_not_merged(self):
        self.assertNotEqual(sha(SKILL / "scripts/errors.py"), sha(ROOT / "skills/_shared/scripts/site_common/errors.py"))
        self.assertNotEqual(sha(SKILL / "scripts/manifest.py"), sha(ROOT / "skills/_shared/scripts/site_common/manifest.py"))

    def test_not_implemented_functions_have_no_implementation(self):
        scripts = "\n".join(p.read_text() for p in (SKILL / "scripts").glob("*.py"))
        for needle in ("def update", "def regenerate", "def add_missing", "def adopt_edits", "publish.yml", "workflow"):
            self.assertNotIn(needle, scripts.replace("workflow-call", ""), needle)


class SkillTextTests(unittest.TestCase):
    text = (SKILL / "SKILL.md").read_text()

    def frontmatter(self):
        match = re.match(r"---\n(.*?)\n---\n", self.text, re.S)
        self.assertIsNotNone(match)
        return match.group(1)

    def allowed(self):
        return re.findall(r"^  - '(Bash\(.*\))'$", self.frontmatter(), re.M)

    def test_frontmatter_name_matches_folder(self):
        self.assertIn("name: setup", self.frontmatter())
        self.assertEqual(SKILL.name, "setup")

    def test_communication_block_is_textually_identical_to_the_shared_reference(self):
        marker = re.compile(r"<!-- user-communication -->.*?<!-- /user-communication -->", re.S)
        reference = marker.search((ROOT / "skills/_shared/references/communication.md").read_text()).group(0)
        self.assertEqual(marker.search(self.text).group(0), reference)

    def test_allowed_tools_are_narrow_and_derived_from_the_call_patterns(self):
        patterns = self.allowed()
        self.assertEqual(patterns, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" *)',
                                    'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/site_setup.py")'])
        for pattern in patterns:
            self.assertNotIn("Bash(python3 *)", pattern)
            self.assertNotIn("Bash(*)", pattern)
        call_block = re.search(r"## Call\n\n```\n(.*?)```", self.text, re.S).group(1).strip().splitlines()
        prefix = 'python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" '
        self.assertEqual(len(call_block), 5)
        covered = set()
        for line in call_block:
            matching = [p for p in patterns if p.startswith("Bash(") and p.endswith(" *)") and line.startswith(p[len("Bash("):-len("*)")])]
            self.assertEqual(len(matching), 1, line)
            covered.add(matching[0])
            self.assertTrue(line.startswith(prefix))
        self.assertIn('test -f "${CLAUDE_SKILL_DIR}/scripts/site_setup.py"', self.text)
        self.assertEqual(covered, {patterns[0]})

    def test_host_paths_are_separated_and_stop_without_a_path(self):
        for needle in ("**Claude:**", "**Codex:**", "Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", "**No path, no run:**",
                       "Do not search caches", "never copy scripts into the website project", "`python3 -B`", "**one** quoted argument",
                       "no `PYTHONPATH`", "test -f"):
            self.assertIn(needle, self.text, needle)

    def test_no_old_names_paths_or_test_instructions(self):
        for needle in ("${CLAUDE_PLUGIN_ROOT}", "/zyris-website:", "tests/setup", "unittest", "ZW_REAL_NPM", "website-manager", "ZIP"):
            self.assertNotIn(needle, self.text, needle)

    def test_status_names_only_implemented_functions_as_available(self):
        status = re.search(r"\*\*Status \(local development\)\.\*\*(.*)", self.text).group(1)
        self.assertIn("Implemented: `create`", status)
        self.assertIn("**Not available (do not offer, do not work around):** `update`, `--add-missing`, `--regenerate`, `--adopt-edits`", status)
        self.assertIn("no migration and no fallback", status)

    def test_reference_is_linked_with_a_reading_instruction_and_resolves_from_the_skill_folder(self):
        self.assertIn("## Read first", self.text)
        for rel in ("references/setup.md", "../_shared/references/interfaces.md"):
            self.assertIn(f"`{rel}`", self.text, rel)
            self.assertTrue((SKILL / rel).is_file(), rel)
        self.assertNotIn("contracts/setup.md", self.text)

    def test_no_shipped_file_points_to_the_undelivered_source_contract(self):
        for path in (ROOT / "skills").rglob("*"):
            if path.is_file() and path.suffix != ".png" and "__pycache__" not in path.parts:
                self.assertNotIn("contracts/setup.md", path.read_text(encoding="utf-8", errors="ignore"), path.name)

    def test_path_option_and_scratch_wording(self):
        self.assertIn("`--path` names the sites folder", self.text)
        self.assertNotIn("`path` = `--path` or", self.text)
        self.assertNotIn("only place for temporary data of the skills", self.text)
        self.assertIn("outside the website repository", self.text)
        reference = (SKILL / "references/setup.md").read_text()
        self.assertIn("`--path P` is the **sites folder**", reference)
        self.assertIn("kept outside the website repository", reference)

    def test_reference_matches_the_confirmed_requirements_r5_r8_r9(self):
        """Content check against SCOPE R5/R8/R9 (not only existence): every confirmed behaviour is stated, nothing planned is offered."""
        ref = (SKILL / "references/setup.md").read_text()
        for needle in (
                # R8
                "absent or empty", "No Docker, Caddy, compose or workflow file", "writes, installs and builds nothing",
                "`unchanged`", "`conflict`", "`failed-rolled-back`", "`failed-partial`", "`needs-input`", "Exit `2`",
                "foreign even if it looks like the template", ".tmp/", "`.gitignore`",
                # R9
                "writes no file below the site folder", "Blocking findings", "build output paths not git-ignored", "folder missing or behind a symlink",
                "`modified (kept)`", "real exit code", "`update`, `--add-missing`, `--regenerate`, `--adopt-edits`", "Unsupported type 'astro'",
                "--serve", "`--build`", "nothing is regenerated",
                # R5
                "plugin schema", "never against a looser project copy", "project's schema copy must exist and be valid JSON",
                "existing entries are never edited", "validated against the plugin schema", "Unknown facts are never invented"):
            self.assertIn(needle, ref, needle)
        section = ref[ref.index("## 6. Not implemented"):]
        for planned in ("`update`", "`--regenerate`", "`--adopt-edits`", "`--add-missing`"):
            self.assertIn(planned, section)
        for historical in ("tests passed", "bestanden", "PLANNED", "HANDOVER", "owner decision", "2026-11-1"):
            self.assertNotIn(historical, ref, historical)

    def test_manifest_field_rules_are_documented(self):
        for needle in ("`$schema` `./website.schema.json`", "`version` 1", "4321 in an empty project", "highest effective port",
                       "`environment` only when given"):
            self.assertIn(needle, self.text, needle)


if __name__ == "__main__":
    unittest.main()
