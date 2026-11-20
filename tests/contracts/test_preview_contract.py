"""Contracts of the `preview` skill: skill text,
call patterns and pre-approvals derived from each other, communication block, shipped-runtime hygiene. Structural/text checks
only: they prove no product behaviour and no host acceptance."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "preview"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()




class RuntimeHygieneTests(unittest.TestCase):
    def test_scripts_import_only_standard_library_and_the_shared_package(self):
        local = {"preview", "site_common"}
        for path in (SKILL / "scripts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                for name in names:
                    top = name.split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top in local, (path.name, name))
                    self.assertNotIn(top, {"errors", "sites", "manifest", "schema"}, (path.name, "flat shared import"))

    def test_no_developer_paths_source_checkout_or_old_names_in_the_skill_payload(self):
        bad = ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "templates/setup", "contracts/")
        for path in SKILL.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for word in bad:
                    self.assertNotIn(word, text, (path.relative_to(ROOT), word))

    def test_no_state_or_bytecode_in_the_installed_skill(self):
        self.assertEqual(list(SKILL.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL.rglob("*.pyc")), [])


class SkillTextTests(unittest.TestCase):
    def front(self):
        head = TEXT.split("---")[1]
        return head

    def test_frontmatter_name_matches_the_folder_and_has_a_description(self):
        self.assertRegex(self.front(), r"(?m)^name: preview$")
        self.assertRegex(self.front(), r"(?m)^description: \S")

    def test_allowed_tools_are_exactly_the_narrow_patterns_of_the_call_forms(self):
        tools = re.findall(r"(?m)^  - '(.+)'$", self.front())
        self.assertEqual(tools, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" *)',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/control.py")'])
        for tool in tools:
            self.assertNotRegex(tool, r"python3 \*|python3:\*|Bash\(\*\)|Bash\(sh|Bash\(bash")
        calls = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/scripts/(\w+\.py)" (\S+)', TEXT)
        self.assertTrue(calls)
        self.assertEqual({c[0] for c in calls}, {"control.py"})         # every call is covered by exactly the one python pattern
        self.assertIn('test -f "${CLAUDE_SKILL_DIR}/scripts/control.py"', TEXT)
        self.assertEqual(len(re.findall(r"python3 -B", self.front())), 1)

    def test_every_call_form_writes_the_script_path_as_one_quoted_argument_with_python3_dash_B(self):
        for line in TEXT.splitlines():
            if "scripts/control.py" in line and line.startswith("python3"):
                self.assertTrue(line.startswith('python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" '), line)
        self.assertNotIn("PYTHONPATH=", TEXT)

    def test_claude_and_codex_path_handling_are_separated(self):
        self.assertIn("Claude:", TEXT)
        self.assertIn("Codex:", TEXT)
        self.assertIn("Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", TEXT)
        self.assertIn("No path, no run", TEXT)
        self.assertIn("never copy scripts into the website project", TEXT)

    def test_communication_block_is_identical_to_the_other_skills_and_present_once(self):
        pat = r"<!-- user-communication -->.*?<!-- /user-communication -->"
        mine = re.findall(pat, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0], re.search(pat, (ROOT / "skills/setup/SKILL.md").read_text(), re.S).group(0))

    def test_read_first_links_resolve(self):
        self.assertIn("`references/preview.md`", TEXT)
        self.assertIn("`../_shared/references/interfaces.md`", TEXT)
        self.assertTrue((SKILL / "references/preview.md").is_file())
        self.assertTrue((SKILL / ".." / "_shared/references/interfaces.md").resolve().is_file())

    def test_skill_never_installs_and_keeps_the_three_facts_apart(self):
        self.assertIn("never installs dependencies", TEXT)
        self.assertIn("needs-install", TEXT)
        self.assertIn("Only `page-confirmed` is evidence", TEXT)
        self.assertIn("do not claim a visual result", TEXT)
        self.assertIn("Claude-desktop artifact", TEXT)
        self.assertNotIn("preview_start", TEXT.replace("no host preview/start tool", ""))

    def test_reference_states_the_process_page_visual_separation_and_the_launch_artifact_status(self):
        ref = (SKILL / "references/preview.md").read_text()
        for needle in ("Claude-desktop-specific artifact", "not a Codex integration", "page-identity-only", "visibility_checked",
                       "at most 600", "insufficient-evidence", "never by name, port or guessed pid"):
            self.assertIn(needle.lower(), ref.lower(), needle)
        self.assertNotIn("PLANNED", ref)
        self.assertNotIn("passed", ref.lower().replace("passed to", ""))


if __name__ == "__main__":
    unittest.main()
