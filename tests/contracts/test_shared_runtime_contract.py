"""Contracts of the shared runtime: self-contained, standard library only, current formats, byte-identical where claimed."""
import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "skills" / "_shared"
INVENTORY = json.loads((ROOT / "docs/migration/source-inventory.json").read_text())
PREFIX = INVENTORY["plugin_root"] + "/"
RUNTIME_SUFFIXES = {".py", ".json", ".md"}
FORBIDDEN = ("www.draftmode", "ai.plugins", "ai.plugin.interview-coach", "/Users/", "PhpstormProjects")


def recorded_hash(source_path):
    for entry in INVENTORY["files"]:
        if entry["path"] == PREFIX + source_path:
            return entry["sha256"]
    raise AssertionError(source_path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shipped_files():
    return [p for p in (ROOT / "skills").rglob("*") if p.is_file() and "__pycache__" not in p.parts]


class SharedLayoutTests(unittest.TestCase):
    def test_shared_folder_is_not_a_skill(self):
        self.assertFalse((SHARED / "SKILL.md").exists())
        self.assertTrue(SHARED.is_dir())

    def test_runtime_and_resources_live_inside_skills_only(self):
        self.assertTrue((SHARED / "resources" / "website.schema.json").is_file())
        self.assertTrue((SHARED / "scripts" / "which_site.py").is_file())
        self.assertFalse((ROOT / "scripts" / "site_common").exists(), "root scripts/ holds development tools only")
        self.assertFalse(list(ROOT.glob("scripts/*schema*")))

    def test_exactly_one_copy_of_each_shared_module_and_the_schema(self):
        """Shared modules exist once. The setup variants of errors.py/manifest.py are deliberately separate (other signatures,
        Ask without options, own error classes) and may live only in skills/setup/scripts; they must not be byte copies."""
        setup_variants = {"errors.py", "manifest.py"}
        for name in ("schema.py", "errors.py", "manifest.py", "sites.py", "which_site.py", "website.schema.json"):
            found = [p for p in (ROOT / "skills").rglob(name) if "__pycache__" not in p.parts]
            allowed = {SHARED / "scripts" / "site_common" / name, SHARED / "scripts" / name, SHARED / "resources" / name}
            if name in setup_variants:
                variant = ROOT / "skills" / "setup" / "scripts" / name
                self.assertIn(variant, found, name)
                self.assertNotEqual(sha(variant), sha(SHARED / "scripts" / "site_common" / name), f"{name}: setup copy is a byte duplicate")
                found.remove(variant)
            self.assertEqual(len(found), 1, (name, found))
            self.assertIn(found[0], allowed, name)
        self.assertEqual(list((ROOT / "skills").rglob("zyris-website.schema.json")), [], "old schema name must not exist in the plugin")
        self.assertEqual(list((ROOT / "skills").rglob("schema.py")), [SHARED / "scripts" / "site_common" / "schema.py"],
                         "setup uses the shared validator; no setup copy of schema.py")


class DeveloperIndependenceTests(unittest.TestCase):
    def test_shipped_files_name_no_developer_path_or_foreign_checkout(self):
        for path in shipped_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in FORBIDDEN:
                self.assertNotIn(needle, text, f"{path.relative_to(ROOT)} mentions {needle}")

    def test_runtime_modules_import_only_stdlib_and_the_shared_package(self):
        stdlib = set(sys.stdlib_module_names)
        for path in (SHARED / "scripts").rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module]
                for module in modules:
                    top = module.split(".")[0]
                    self.assertTrue(top in stdlib or top == "site_common", f"{path.name}: {module}")

    def test_no_relative_import_reaches_outside_the_package(self):
        for path in (SHARED / "scripts" / "site_common").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.level:
                    self.assertEqual(node.level, 1, path.name)

    def test_runtime_never_writes_into_the_plugin(self):
        for path in (SHARED / "scripts").rglob("*.py"):
            text = path.read_text()
            for pattern in (r"\.write_text\(", r"\.write_bytes\(", r"open\([^)]*['\"][wax]", r"\.mkdir\(", r"\.unlink\("):
                self.assertIsNone(re.search(pattern, text), f"{path.name}: {pattern}")


class ByteIdentityTests(unittest.TestCase):
    """Files claimed as unchanged carry the recorded source hash (inventory); adapted ones are listed in docs/migration/changes.md."""

    def test_unchanged_files_match_the_recorded_hashes(self):
        pairs = {
            "skills/_shared/resources/website.schema.json": "templates/setup/_manifest/root/zyris-website.schema.json",
            "skills/_shared/references/communication.md": "contracts/communication.md",
            "skills/_shared/scripts/site_common/errors.py": "scripts/optimize/errors.py",
            "tests/fixtures/shared/schema-foreign-older.json": "tests/setup/fixtures/schema-foreign-older.json",
        }
        for target, source in pairs.items():
            self.assertEqual(sha(ROOT / target), recorded_hash(source), target)

    def test_adapted_files_are_recorded_as_adapted(self):
        changes = (ROOT / "docs/migration/changes.md").read_text()
        for name in ("site_common/schema.py", "site_common/manifest.py", "site_common/sites.py", "which_site.py", "references/interfaces.md"):
            self.assertIn(name, changes)


class ReferenceScopeTests(unittest.TestCase):
    def test_edit_is_limited_to_the_start_page_in_the_shared_references(self):
        for path in (SHARED / "references").glob("*.md"):
            text = path.read_text()
            self.assertNotIn("directly affected", text, path.name)
        inventory = (SHARED / "references" / "interfaces.md").read_text()
        row = next(l for l in inventory.splitlines() if l.startswith("| edit change"))
        self.assertIn("exactly `src/pages/index.astro`", row)
        self.assertEqual(row.count("src/"), 1)

    def test_host_convention_does_not_assume_codex_interprets_claude_placeholders(self):
        text = (ROOT / "docs/migration/host-conventions.md").read_text()
        self.assertIn("Die Codex-Dokumentation nennt `${CLAUDE_SKILL_DIR}` nicht", text)
        self.assertNotIn("ohne Wirkung", text)         # 'not documented' is never turned into 'has no effect'
        self.assertIn("Pfad nicht verfügbar", text)
        self.assertIn("Keine Suche in Caches", text)


class IdentityTests(unittest.TestCase):
    def test_canonical_and_derived_manifest(self):
        portable = json.loads((ROOT / "plugin.json").read_text())
        host = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        self.assertEqual((portable["name"], host["name"]), ("website", "website"))
        self.assertEqual(portable["extensions"]["com.openai"]["interface"]["displayName"], "Website")
        self.assertEqual(host["displayName"], "Website")
        self.assertNotIn("version", portable)
        self.assertNotIn("version", host)
        self.assertEqual(portable["author"], host["author"])
        self.assertEqual((portable["license"], portable["repository"]), (host["license"], host["repository"]))

    def test_no_aliases_for_old_names_in_the_manifests(self):
        text = (ROOT / "plugin.json").read_text() + (ROOT / ".claude-plugin/plugin.json").read_text()
        self.assertNotIn("zyris-website", text)
        self.assertNotIn("website-manager", text)

    def test_skeleton_skill_is_gone_and_not_aliased(self):
        self.assertFalse((ROOT / "skills" / "website-manager").exists())
        for path in (ROOT / "skills").glob("*/SKILL.md"):
            self.assertNotIn("plugin-skeleton", path.read_text(), path)
            self.assertNotEqual(path.parent.name, "website-manager")

    def test_documentation_source_skill_exists(self):
        config = json.loads((ROOT / "docs/documentation.json").read_text())
        self.assertTrue((ROOT / config["source_skill"] / "SKILL.md").is_file())

    def test_documentation_languages(self):
        doc = json.loads((ROOT / "docs/documentation.json").read_text())["documentation"]
        self.assertEqual((doc["languages"], doc["default_language"]), (["de", "en"], "de"))

    def test_no_marketplace_catalog_or_version(self):
        for name in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "marketplace.json"):
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
