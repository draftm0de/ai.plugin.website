"""Contracts of the migrated `edit` skill: identity against the source inventory (explicit change lists, reversible), skill text,
call patterns and pre-approvals derived from each other, communication block, shipped-runtime hygiene and the "not available"
boundary. Structural/text checks only: they prove no product behaviour and no host acceptance."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "edit"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
REFERENCE = (SKILL / "references" / "edit.md").read_text(encoding="utf-8")
INVENTORY = json.loads((ROOT / "docs/migration/source-inventory.json").read_text())
PREFIX = INVENTORY["plugin_root"] + "/"
SOURCE = {e["path"][len(PREFIX):]: e["sha256"] for e in INVENTORY["files"] if e["path"].startswith(PREFIX)}
RUNTIME = SKILL / "scripts" / "edit.py"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


# Post-migration product behavior is tested in integration/edit (SCOPE R28).


class IdentityTests(unittest.TestCase):
    def test_inventoried_edit_and_publish_sources_are_accounted_for(self):
        changes = (ROOT / "docs/migration/changes.md").read_text()
        for source in ("scripts/edit/edit.py", "skills/edit/SKILL.md", "contracts/edit.md", "tests/edit/helpers.py", "tests/edit/test_edit.py",
                       "tests/behavior/cases.md", "skills/publish/SKILL.md", "contracts/publish.md", "templates/github/workflows/README.md"):
            self.assertIn(source, SOURCE, source)
            self.assertIn(source, changes, source)
        for target in ("skills/edit/scripts/edit.py", "skills/edit/SKILL.md", "skills/edit/references/edit.md", "skills/publish/SKILL.md",
                       "tests/support/edit_helpers.py", "tests/behavior/edit_cases.md"):
            self.assertIn(target, changes, target)

    def test_the_skill_ships_only_text_and_the_single_helper(self):
        found = {p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*") if p.is_file()}
        self.assertEqual(found, {"SKILL.md", "references/edit.md", "scripts/edit.py"})

    def test_exactly_eight_public_skills_and_a_shared_folder_without_skill_md(self):
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(skills, {"plugin-website", "brief", "design", "setup", "preview", "optimize", "edit", "publish"})
        self.assertFalse((ROOT / "skills" / "_shared" / "SKILL.md").exists())

    def test_the_resolver_is_the_shared_one_and_there_is_no_copy(self):
        self.assertTrue((ROOT / "skills/_shared/scripts/which_site.py").is_file())
        self.assertEqual([p for p in (ROOT / "skills").rglob("which_site.py")], [ROOT / "skills/_shared/scripts/which_site.py"])
        text = RUNTIME.read_text()
        self.assertIn('HERE.parents[1] / "_shared" / "scripts" / "which_site.py"', text)
        self.assertNotRegex(text, r"""["']optimize["']""")
        self.assertEqual(len(re.findall(r"import (errors|sites|manifest|schema)\b", text)), 0)


class RuntimeHygieneTests(unittest.TestCase):
    def test_only_standard_library_is_imported(self):
        for node in ast.walk(ast.parse(RUNTIME.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            for name in names:
                self.assertIn(name.split(".")[0], sys.stdlib_module_names | {"site_common"}, name)

    def test_the_runtime_never_installs_and_uses_only_read_git_commands(self):
        text = RUNTIME.read_text()
        self.assertNotRegex(text, r"""["'](install|ci|i|update|add)["']""")
        calls = set(re.findall(r'git\(root,\s*"([a-z-]+)"', text))
        self.assertEqual(calls, set())
        self.assertNotIn("rmtree", text)                      # the cleanup never deletes a tree it has not verified object by object
        for verb in ("commit", "push", "add", "reset", "checkout", "stash", "clean", "restore", "rm", "mv", "apply", "merge"):
            self.assertNotRegex(text, r"""git\(root,\s*["']%s["']""" % verb)
        self.assertEqual(re.findall(r"""\[npm, "run", script\]""", text), ['[npm, "run", script]'])

    def test_resolver_child_process_never_writes_bytecode(self):
        self.assertIn('[sys.executable, "-I", "-B", str(RESOLVER)', RUNTIME.read_text())

    def test_no_developer_paths_source_checkout_or_old_names_in_the_skill_payload(self):
        bad = ("www.draftmode", "ai.plugins", "interview-coach", "/Users/", "CLAUDE_PLUGIN_ROOT", "templates/setup", "contracts/", "draftmode.io",
               "HANDOVER", "fux-law", "familien-recht", "/zyris-website:", "ZYRIS_WEBSITE_STATE_DIR", "PYTHONPATH")
        for path in SKILL.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                for word in bad:
                    if word == "PYTHONPATH" and path.name in ("SKILL.md", "edit.md"):
                        continue                                  # the skill text says "no PYTHONPATH"
                    if word == "ZYRIS_WEBSITE_STATE_DIR" and path.name == "edit.md":
                        continue                                  # the reference states that edit does not use it (Q5)
                    self.assertNotIn(word, text, (path.relative_to(ROOT), word))

    def test_internal_names_are_unchanged_by_decision_q5(self):
        self.assertIn('"zyris-website"', RUNTIME.read_text())               # the backup area folder under TMPDIR
        self.assertIn("edit-{site['site']}-{stamp}", RUNTIME.read_text())

    def test_no_state_or_bytecode_in_the_installed_skill(self):
        self.assertEqual(list(SKILL.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL.rglob("*.pyc")), [])

    def test_tests_use_only_fictional_site_names(self):
        for path in list((ROOT / "tests").rglob("*edit*")) + [ROOT / "tests/support/edit_helpers.py"]:
            if path.is_file() and path.suffix in (".py", ".md") and path.name != "test_edit_contract.py":
                text = path.read_text(encoding="utf-8")
                for word in ("draftmode.io", "fux-law", "familien-recht", "www.draftmode"):
                    self.assertNotIn(word, text, (path.name, word))


class SkillTextTests(unittest.TestCase):
    def front(self):
        return TEXT.split("---")[1]

    def test_frontmatter_name_matches_the_folder_and_has_a_description(self):
        self.assertRegex(self.front(), r"(?m)^name: edit$")
        self.assertRegex(self.front(), r"(?m)^description: \S")

    def test_allowed_tools_are_exactly_the_narrow_patterns_of_the_call_forms(self):
        tools = re.findall(r"(?m)^  - '(.+)'$", self.front())
        self.assertEqual(tools, ['Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/edit.py" *)',
                                 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../preview/scripts/control.py" *)',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/edit.py")',
                                 'Bash(test -f "${CLAUDE_SKILL_DIR}/../preview/scripts/control.py")'])
        for tool in tools:
            self.assertNotRegex(tool, r"python3 \*|python3:\*|Bash\(\*\)|Bash\(sh|Bash\(bash|Bash\(npm|Bash\(git|Bash\(cd|Bash\(rm")
        calls = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/((?:\.\./preview/)?scripts/\w+\.py)" (\S+)', TEXT)
        self.assertEqual({c[0] for c in calls}, {"scripts/edit.py", "../preview/scripts/control.py"})   # every call is covered by exactly one pattern
        python_patterns = [t for t in tools if t.startswith("Bash(python3")]
        for script, _ in calls:
            covering = [t for t in python_patterns if f'"${{CLAUDE_SKILL_DIR}}/{script}" *)' in t]
            self.assertEqual(len(covering), 1, script)
        for pattern in python_patterns:
            self.assertTrue(any(f"/{script}\"" in pattern for script, _ in calls), pattern)
        for script in ("scripts/edit.py", "../preview/scripts/control.py"):
            self.assertIn(f'test -f "${{CLAUDE_SKILL_DIR}}/{script}"', TEXT)
        self.assertEqual(len(re.findall(r"python3 -B", self.front())), 2)

    def test_every_call_form_writes_the_script_path_as_one_quoted_argument_with_python3_dash_B(self):
        for line in TEXT.splitlines():
            if "scripts/" in line and line.startswith("python3"):
                self.assertRegex(line, r'^python3 -B "\$\{CLAUDE_SKILL_DIR\}/(\.\./preview/)?scripts/\w+\.py" ')
        self.assertNotIn("PYTHONPATH=", TEXT)
        self.assertNotIn("cd ", TEXT.replace("cd <", ""))

    def test_the_call_forms_cover_the_seven_helper_commands_and_the_documented_preview_verbs(self):
        listed = re.findall(r'(?m)^python3 -B "\$\{CLAUDE_SKILL_DIR\}/scripts/edit\.py" (\w+)', TEXT)
        self.assertEqual(listed, ["preflight", "begin", "write", "replace", "check", "diff", "finish"])
        helper = RUNTIME.read_text()
        for name in listed:
            self.assertIn(f'add_parser("{name}")' if name in ("preflight", "begin") else f'"{name}"', helper, name)
        for flag in ("--cwd", "--last", "--root", "--site", "--state", "--content-file", "--find", "--replace", "--visual-done", "--visual-substitute", "--visual-not-done"):
            self.assertIn(f'"{flag}"', helper, flag)
            self.assertIn(flag, TEXT, flag)
        control = (ROOT / "skills/preview/scripts/control.py").read_text()
        for verb in ("start", "status", "inspect"):
            self.assertIn(f"`{verb}`", TEXT.replace("<start|status>", "`start` `status`") + " `inspect`")
            self.assertIn(f'"{verb}"', control, verb)
        for flag in ("--page", "--expect"):
            self.assertIn(flag, control, flag)
        self.assertNotIn('"--npm"', TEXT)
        self.assertNotIn("--npm", re.sub(r"`--npm`[^\n]*", "", TEXT))      # the test hook is not a call form of the skill

    def test_claude_and_codex_path_handling_are_separated(self):
        for needle in ("**Claude:**", "**Codex:**", "Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable", "**No path, no run:**", "Do not search caches",
                       "never copy scripts into the website project", "`python3 -B`", "**one** quoted argument", "no `PYTHONPATH`", "test -f",
                       "Claude-specific"):
            self.assertIn(needle, TEXT, needle)

    def test_communication_block_is_identical_to_the_reference_and_the_other_skills_and_present_once(self):
        pat = r"<!-- user-communication -->.*?<!-- /user-communication -->"
        mine = re.findall(pat, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0], re.search(pat, (ROOT / "skills/_shared/references/communication.md").read_text(), re.S).group(0))
        for other in ("setup", "preview", "optimize", "publish"):
            self.assertEqual(mine[0], re.search(pat, (ROOT / "skills" / other / "SKILL.md").read_text(), re.S).group(0), other)

    def test_read_first_links_resolve(self):
        self.assertIn("`references/edit.md`", TEXT)
        self.assertIn("`../_shared/references/interfaces.md`", TEXT)
        self.assertTrue((SKILL / "references/edit.md").is_file())
        self.assertTrue((SKILL / ".." / "_shared/references/interfaces.md").resolve().is_file())

    def test_skill_never_installs_and_does_not_offer_planned_functions(self):
        self.assertIn("Never run `npm install` or `npm ci`", TEXT)
        status = TEXT.split("> **Script location")[0]
        self.assertIn("**Not available (do not offer, do not work around):** blog, other page types, new sites", status)
        for word in ("PLANNED", "not implemented yet", "/zyris-website:", "CLAUDE_PLUGIN_ROOT", "contracts/", "unittest", "tests/edit"):
            self.assertNotIn(word, TEXT, word)

    def test_skill_keeps_the_protection_the_wording_and_the_boundaries(self):
        for needle in ("Concrete order = release", "Never invent content", "data, not instructions", "an edit order approves no optimize finding",
                       "never write anything under `.project/reports/`", "Never commit, stash, reset, clean or reformat", "at most **two** repair rounds",
                       "`conflict`", "technically checked, visual check open", "never reworded into that", "**only** by `control.py`", "`port-conflict`",
                       "`page-confirmed`", "is **open**", "outside the website project and outside the plugin", "`not-run`"):
            self.assertIn(needle.lower(), TEXT.lower(), needle)

    def test_reference_states_the_boundaries_and_the_limits(self):
        for needle in ("src/pages/index.astro", "Writes nothing", "outside the website project and outside the installed plugin", "`conflict`",
                       "only the named bytes change", "at most two repair writes", "`not-run`", "technically checked, visual check open",
                       "`complete`", "Known limit between `edit` and `setup`", "Not verified", "no `ZYRIS_WEBSITE_STATE_DIR` for `edit`",
                       "is not a conflict", "`TMPDIR` only"):
            self.assertIn(needle.lower(), REFERENCE.lower(), needle)
        self.assertNotIn("PLANNED", REFERENCE)
        self.assertNotIn("draftmode.io", REFERENCE)
        self.assertNotRegex(REFERENCE.lower(), r"\ball tests? (passed|pass)\b|\btests? passed\b")


if __name__ == "__main__":
    unittest.main()
