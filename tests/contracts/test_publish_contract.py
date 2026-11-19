"""Contract of the `publish` placeholder (R16, R23): a text-only skill that says plainly that publishing is not available. Structural
and text checks; they prove that the text and the absence of runtime, but not what a model does with the text."""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "publish"
TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
BODY = TEXT.split("---", 2)[2]
COMMUNICATION = r"<!-- user-communication -->.*?<!-- /user-communication -->"


class PublishPlaceholder(unittest.TestCase):
    def test_the_skill_is_one_text_file_without_runtime_references_templates_or_workflow_files(self):
        self.assertEqual([p.relative_to(SKILL).as_posix() for p in SKILL.rglob("*")], ["SKILL.md"])
        self.assertEqual(list(ROOT.glob("skills/**/publish*.py")), [])
        self.assertEqual(list((ROOT / "skills").rglob("*.yml")) + list((ROOT / "skills").rglob("*.yaml")), [])
        self.assertFalse((ROOT / ".github" / "workflows" / "publish.yml").exists())

    def test_frontmatter_has_only_name_and_description_and_no_command_pre_approval(self):
        front = TEXT.split("---")[1]
        self.assertEqual(re.findall(r"(?m)^([\w-]+):", front), ["name", "description"])
        self.assertRegex(front, r"(?m)^name: publish$")
        for word in ("allowed-tools", "Bash(", "python3", "test -f", "CLAUDE_SKILL_DIR", "CLAUDE_PLUGIN_ROOT"):
            self.assertNotIn(word, TEXT, word)

    def test_it_says_plainly_that_publishing_is_not_available_and_never_claims_otherwise(self):
        self.assertIn("publishing is not available", TEXT)
        self.assertIn("Never say a publication is possible, prepared or done", TEXT)
        for claim in ("ready to publish", "can be published", "can publish", "is published", "was published", "has been published", "prepared the release",
                      "release is prepared", "deployed successfully"):
            self.assertNotIn(claim, TEXT.lower(), claim)

    def test_it_names_the_missing_parts_in_general_terms(self):
        low = TEXT.lower()
        for part in ("central reusable workflow", "server-side deployment protocol", "workflow call"):
            self.assertIn(part, low, part)

    def test_it_points_to_optimize_for_local_quality_checks_and_says_that_is_no_publishing_check(self):
        self.assertIn("`optimize` skill", TEXT)
        self.assertIn("That is not a publishing check", TEXT)

    def test_it_refers_to_nothing_planned_or_unavailable_and_invents_nothing(self):
        for word in ("PLANNED", "planned", "contracts/", "templates/", "references/", "publish.md", "draftmode.srv", "ghcr", "/zyris-website:", "zyris-website",
                     "TODO", "http://", "https://", "../"):
            self.assertNotIn(word, TEXT, word)
        self.assertIsNone(re.search(r"\b[0-9a-f]{40}\b", TEXT))                 # no SHA
        self.assertIsNone(re.search(r"\b[\w-]+\.ya?ml\b", TEXT))                # no workflow file name

    def test_it_forbids_every_side_effect(self):
        must = ("Do not deploy, push, commit, trigger a workflow or query a remote or the network", "Do not run any script, check for any file or read the website project or its manifest",
                "Do not invent workflow names, SHAs, hosts, secrets or variables", "Do not create a workflow file or any other file")
        for sentence in must:
            self.assertIn(sentence, TEXT, sentence)

    def test_the_communication_block_is_textually_identical_to_the_shared_reference_and_to_edit(self):
        mine = re.findall(COMMUNICATION, TEXT, re.S)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0], re.search(COMMUNICATION, (ROOT / "skills/_shared/references/communication.md").read_text(), re.S).group(0))
        for other in ("setup", "preview", "optimize", "edit"):
            self.assertEqual(mine[0], re.search(COMMUNICATION, (ROOT / "skills" / other / "SKILL.md").read_text(), re.S).group(0), other)

    def test_the_skill_is_self_contained_and_needs_no_project_manifest_or_runtime(self):
        """Extracted alone into an empty plugin folder (no _shared, no other skill, no project): the text has nothing to resolve."""
        with tempfile.TemporaryDirectory() as tmp:
            alone = Path(tmp) / "My Plugin" / "skills" / "publish"
            alone.mkdir(parents=True)
            shutil.copy2(SKILL / "SKILL.md", alone / "SKILL.md")
            text = (alone / "SKILL.md").read_text()
            self.assertEqual(sorted(p.name for p in alone.parent.iterdir()), ["publish"])
            self.assertIsNone(re.search(r"`(?:\.\./|references/|scripts/)", text))
            self.assertNotRegex(text, r"\.project|sites/|manifest\.json|zyris-website\.json")
            self.assertIn("This skill needs no website project, no manifest and no installed script to give this answer.", text)

    def test_no_other_skill_offers_publishing(self):
        for name in ("setup", "preview", "optimize", "edit"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text()
            self.assertNotRegex(text, r"(?i)(can|will|to) (be )?publish(ed)? (a|the|your) (site|website)")
            self.assertNotIn("scripts/publish", text)


if __name__ == "__main__":
    unittest.main()
