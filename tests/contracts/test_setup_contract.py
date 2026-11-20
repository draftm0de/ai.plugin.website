"""Contracts of the `setup` skill: project data names, skill text, narrow call patterns. Structural/text checks only: they prove no product behaviour."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "setup"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


class SchemaRenameTests(unittest.TestCase):
    NEW = ROOT / "skills/_shared/resources/website.schema.json"




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
        for needle in ("${CLAUDE_PLUGIN_ROOT}", "tests/setup", "unittest", "WEBSITE_MANAGER_REAL_NPM", "ZIP"):
            self.assertNotIn(needle, self.text, needle)

    def test_status_names_only_implemented_functions_as_available(self):
        status = re.search(r"\*\*Status \(local development\)\.\*\*(.*)", self.text).group(1)
        self.assertIn("Implemented: `create`", status)
        self.assertIn("**Not available (do not offer, do not work around):** `update`, `--add-missing`, `--regenerate`, `--adopt-edits`", status)

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
