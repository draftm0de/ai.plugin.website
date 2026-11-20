"""Contracts of the `optimize` skill: skill text,
call patterns and pre-approvals derived from each other, communication block, shipped-runtime hygiene and the
"not available" boundary. Structural/text checks only: they prove no product behaviour and no host acceptance."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "optimize"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL / "references" / "optimize.md").read_text(encoding="utf-8")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


class IdentityTests(unittest.TestCase):




    def test_the_skill_ships_no_templates_and_no_contract_or_test_files(self):
        found = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*") if p.is_file()}
        self.assertEqual(found, {"SKILL.md", "references/optimize.md", "scripts/audit.py", "scripts/findings.py", "scripts/store.py", "scripts/worklist.py"})


    def test_work_list_text_and_format_markers_are_project_data(self):
        """worklist.py renders the generated work list and compares it with the stored text. Its wording is part of the project data format (R21)."""
        text = (SKILL / "scripts/worklist.py").read_text(encoding="utf-8")
        for marker in ('FORMAT = "website-manager-optimize-worklist"', "<!-- website-manager-optimize:state sha256=", "<!-- website-manager-optimize:worklist v1",
                       "authoritative status source for `/website-manager:optimize`"):
            self.assertIn(marker, text)
        self.assertIn("<!-- website-manager-optimize:report v1 site=", (SKILL / "scripts/audit.py").read_text(encoding="utf-8"))


class RuntimeHygieneTests(unittest.TestCase):
    def test_scripts_import_only_standard_library_the_skill_modules_and_the_shared_package(self):
        local = {"findings", "store", "worklist", "site_common"}
        for path in (SKILL / "scripts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                for name in names:
                    top = name.split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top in local, (path.name, name))
                    self.assertNotIn(top, {"errors", "sites", "manifest", "schema"}, (path.name, "flat shared import"))

    def test_the_runtime_never_runs_an_install_or_a_git_write_command(self):
        text = "\n".join(p.read_text() for p in (SKILL / "scripts").glob("*.py"))
        self.assertNotRegex(text, r"""["']npm["']\s*,\s*["'](install|ci|i|update|add)["']""")
        self.assertNotRegex(text, r"""["'](install|ci)["']\s*\]""")
        for verb in ("commit", "push", "add", "reset", "checkout", "stash", "clean", "restore", "rm", "mv", "apply", "merge"):
            self.assertNotRegex(text, r"""git\(root,\s*["']%s["']""" % verb)
        calls = set(re.findall(r"git\(root,\s*\"([a-z-]+)\"", text))
        self.assertEqual(calls, set())

    def test_no_developer_paths_source_checkout_or_old_names_in_the_skill_payload(self):
        bad = ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "templates/setup", "contracts/",
               "draftmode.io", "HANDOVER", "fux-law", "familien-recht")
        for path in SKILL.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for word in bad:
                    self.assertNotIn(word, text, (path.relative_to(ROOT), word))
        # the skill call name appears exactly once in the runtime: inside the generated work-list text (data format, see above)
        for path in SKILL.rglob("*"):
            if path.is_file():
                n = path.read_text(encoding="utf-8").count("/website-manager:")
                self.assertEqual(n, 1 if path.name == "worklist.py" else 0, path.relative_to(ROOT))

    def test_no_state_or_bytecode_in_the_installed_skill(self):
        self.assertEqual(list(SKILL.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL.rglob("*.pyc")), [])

    def test_tests_use_only_fictional_site_names(self):
        for path in (ROOT / "tests").rglob("*optimize*"):
            if path.is_file() and path.suffix == ".py" and path.name != "test_optimize_contract.py":      # this file lists the words
                text = path.read_text(encoding="utf-8")
                for word in ("draftmode.io", "fux-law", "familien-recht", "www.draftmode"):
                    self.assertNotIn(word, text, (path.name, word))


class SkillTextTests(unittest.TestCase):
    def front(self):
        return TEXT.split("---")[1]

    def test_frontmatter_name_matches_the_folder_and_has_a_description(self):
        self.assertRegex(self.front(), r"(?m)^name: optimize$")
        self.assertRegex(self.front(), r"(?m)^description: \S")

    def test_allowed_tools_are_exactly_the_narrow_patterns_of_the_call_forms(self):
        tools = re.findall(r"(?m)^  - '(.+)'$", self.front())
        self.assertEqual(tools, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py" *)',
                                 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" *)',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py")',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/audit.py")'])
        for tool in tools:
            self.assertNotRegex(tool, r"python3 \*|python3:\*|Bash\(\*\)|Bash\(sh|Bash\(bash|Bash\(npm|Bash\(git")
        calls = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/((?:\.\./_shared/)?scripts/\w+\.py)" (\S+)', TEXT)
        self.assertEqual({c[0] for c in calls}, {"../_shared/scripts/which_site.py", "scripts/audit.py"})   # every call is covered by exactly one python pattern
        python_patterns = [t for t in tools if t.startswith("Bash(python3")]
        for script, _ in calls:
            covering = [t for t in python_patterns if f'"${{CLAUDE_SKILL_DIR}}/{script}" *)' in t]
            self.assertEqual(len(covering), 1, script)
        for pattern in python_patterns:
            self.assertTrue(any(f"/{script}\"" in pattern for script, _ in calls), pattern)
        for script in ("../_shared/scripts/which_site.py", "scripts/audit.py"):
            self.assertIn(f'test -f "${{CLAUDE_SKILL_DIR}}/{script}"', TEXT)
        self.assertEqual(len(re.findall(r"python3 -B", self.front())), 2)

    def test_every_call_form_writes_the_script_path_as_one_quoted_argument_with_python3_dash_B(self):
        for line in TEXT.splitlines():
            if "scripts/" in line and line.startswith("python3"):
                self.assertRegex(line, r'^python3 -B "\$\{CLAUDE_SKILL_DIR\}/(\.\./_shared/)?scripts/\w+\.py" ')
        self.assertNotIn("PYTHONPATH=", TEXT)
        self.assertNotIn("cd ", TEXT.replace("cd <", ""))

    def test_audit_call_forms_cover_the_five_cli_commands_and_no_other_mode(self):
        listed = set(re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/scripts/audit\.py" (<?[\w|]+>?)', TEXT))
        self.assertEqual(listed, {"<audit|show>", "propose", "decide", "apply"})
        driver = (SKILL / "scripts/audit.py").read_text()
        self.assertIn('choices=["audit", "propose", "decide", "apply", "show"]', driver)
        for flag in ("--site", "--cwd", "--last", "--root", "--status", "--reason", "--change", "--proposals", "--editorial", "--applied", "--npm"):
            self.assertIn(f'"{flag}"', driver, flag)

    def test_claude_and_codex_path_handling_are_separated(self):
        self.assertIn("Claude:", TEXT)
        self.assertIn("Codex:", TEXT)
        self.assertIn("Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", TEXT)
        self.assertIn("No path, no run", TEXT)
        self.assertIn("never copy scripts into the website project", TEXT)
        self.assertIn("Claude-specific", TEXT)

    def test_communication_block_is_identical_to_the_other_skills_and_present_once(self):
        pat = r"<!-- user-communication -->.*?<!-- /user-communication -->"
        mine = re.findall(pat, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        for other in ("setup", "preview"):
            self.assertEqual(mine[0], re.search(pat, (ROOT / "skills" / other / "SKILL.md").read_text(), re.S).group(0), other)
        ref = (ROOT / "skills/_shared/references/communication.md").read_text()
        self.assertIn("Language and tone", ref)
        self.assertIn("Language and tone", mine[0])

    def test_read_first_links_resolve(self):
        self.assertIn("`references/optimize.md`", TEXT)
        self.assertIn("`../_shared/references/interfaces.md`", TEXT)
        self.assertTrue((SKILL / "references/optimize.md").is_file())
        self.assertTrue((SKILL / ".." / "_shared/references/interfaces.md").resolve().is_file())

    def test_skill_never_installs_and_does_not_offer_planned_functions(self):
        self.assertIn("never installs dependencies", TEXT)
        self.assertIn("not even for `apply`", TEXT)
        self.assertIn("this skill does not install", TEXT)
        status = TEXT.split("> **Script location")[0]
        self.assertIn("**Not available (do not offer, do not work around):** GEO, Lighthouse, link-graph checks", status)
        for word in ("PLANNED", "not implemented yet", "edit` is", "/website-manager:"):
            self.assertNotIn(word, TEXT, word)

    def test_skill_keeps_the_statuses_the_classes_and_the_manual_points(self):
        for needle in ("`proposed`, `approved`, `deferred`, `wont-do`", "Audit and decision never authorise `apply`", "readonly-violated", "incomplete",
                       "**never** reported as clean", "reappeared", "are never reported as passed", "exactly once", "no symbolic link",
                       "no unversioned file", "Do not commit"):
            self.assertIn(needle, TEXT, needle)

    def test_reference_states_the_boundaries(self):
        for needle in ("Audit and decide never authorise apply", "exactly `proposed`, `approved`, `deferred`, `wont-do`", "Nothing is ever installed",
                       "**never** marked as passed", "No invention", "## 10. Not available", "GEO criteria, Lighthouse, link-graph checks",
                       "project data format", "byte-exact", "exactly once"):
            self.assertIn(needle, REFERENCE, needle)
        self.assertNotIn("PLANNED", REFERENCE)
        self.assertNotIn("draftmode.io", REFERENCE)
        self.assertNotRegex(REFERENCE.lower(), r"\ball tests? (passed|pass)\b|\btests? passed\b")


if __name__ == "__main__":
    unittest.main()
