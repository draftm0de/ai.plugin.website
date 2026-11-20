"""Text and structure contracts of the guided flow skills (plugin-website, brief, design). They prove no conversation behaviour."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
NEW = ("plugin-website", "brief", "design")
COMMUNICATION = r"<!-- user-communication -->.*?<!-- /user-communication -->"


def text(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_name_equals_folder_and_only_the_shared_helper_is_called(self):
        for name in NEW:
            body = text(name)
            self.assertTrue(body.startswith(f"---\nname: {name}\ndescription: "), name)
            for call in re.findall(r'python3 -B "([^"]+)"', body):
                self.assertTrue(call.startswith("${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py"), (name, call))
            self.assertEqual(sorted(p.name for p in (SKILLS / name).iterdir()), ["SKILL.md", "references"], name)

    def test_operator_language_gate_and_shared_communication_block(self):
        reference = re.search(COMMUNICATION, text("setup"), re.S).group(0)
        for name in NEW:
            self.assertIn("../_shared/references/operator-language.md", text(name), name)
            self.assertEqual(re.search(COMMUNICATION, text(name), re.S).group(0), reference, name)
            self.assertIn("is never derived from the operator language", text(name), name)

    def test_entry_does_not_promise_single_word_activation(self):
        entry = text("plugin-website") + (SKILLS / "plugin-website/references/entry.md").read_text(encoding="utf-8")
        self.assertIn("not guaranteed", entry)
        self.assertIn("**not verified**", entry)
        self.assertNotRegex(entry.lower(), r"always activat(es|ed) (the skill )?(on|by) (the )?word")

    def test_entry_never_treats_an_existing_project_as_empty_and_status_is_read_only(self):
        body = text("plugin-website")
        self.assertIn("`status` writes nothing", body)
        self.assertIn("only `setup.state` = `missing` means", body)

    def test_design_never_writes_into_the_site_and_preference_is_not_approval(self):
        body = text("design") + (SKILLS / "design/references/design.md").read_text(encoding="utf-8")
        self.assertIn("never writes into `sites/<id>/`", body)
        self.assertIn("not an approval", body)
        self.assertIn("at least two", body)

    def test_edit_scope_is_unchanged_and_publish_is_untouched(self):
        edit = (SKILLS / "edit/scripts/edit.py").read_text(encoding="utf-8")
        self.assertIn('ALLOWED = ("src/pages/index.astro",)', edit)
        self.assertEqual([p.name for p in (SKILLS / "publish").iterdir()], ["SKILL.md"])
        self.assertIn("publishing is not available", text("publish").lower())
        for name in NEW:
            self.assertNotRegex(text(name).lower(), r"publish(ing)? (is|has been) (possible|prepared|done)")


if __name__ == "__main__":
    unittest.main()
