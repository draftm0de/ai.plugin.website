"""Etappe 6 (R18, R20, R25, R26): documentation, metadata and completeness mapping.

Deterministic text/structure checks on repository files only. They find broken internal links, missing DE/EN counterparts,
unassigned inventory files and stale metadata. They do not review the prose, do not prove any behaviour of a host or a model and
do not replace the documentation review.
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MIGRATION = DOCS / "migration"
USER_PAGES = ["README.md", "README.en.md"] + sorted(
    p.relative_to(ROOT).as_posix() for lang in ("de", "en") for p in (DOCS / lang).glob("*.md"))
PAGE_NAMES = ["README.md", "development.md", "faq.md", "installation.md", "screens.md", "storage.md", "usage.md"]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
IMG = re.compile(r"<img[^>]*src=\"([^\"]+)\"")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def headings(text):
    return [line for line in text.splitlines() if line.startswith("## ")]


def normalised_links(rel):
    """Link targets of a page with the language folder and the README spelling normalised."""
    targets = []
    for target in LINK.findall(read(rel)) + IMG.findall(read(rel)):
        if re.match(r"(https?:|mailto:|#)", target):
            continue
        target = target.replace("README.en.md", "README.md").replace("docs/en/", "docs/de/").replace("../en/", "../de/")
        targets.append(target)
    return sorted(targets)


class Metadata(unittest.TestCase):
    def test_plugin_description_states_the_actual_scope_without_outdated_or_inflated_claims(self):
        portable = json.loads(read("plugin.json"))
        self.assertEqual(portable["name"], "website")
        self.assertNotIn("version", portable)
        text = portable["description"].lower()
        for word in ("work in progress", "no skill is functional", "skeleton", "production ready", "fully supported", "production-ready"):
            self.assertNotIn(word, text)
        for word in ("setup", "preview", "optimize", "edit", "publish", "brief", "design", "plugin-website"):
            self.assertIn(word, text)
        self.assertIn("not available", text)

    def test_host_manifest_is_derived_without_drift_and_there_are_no_aliases_or_catalogs(self):
        portable = json.loads(read("plugin.json"))
        host = json.loads(read(".claude-plugin/plugin.json"))
        self.assertEqual(host["description"], portable["description"])
        self.assertEqual(host["name"], "website")
        self.assertEqual(host["displayName"], "Website")
        for name in ("zyris-website", "website-manager"):
            self.assertNotIn(name, json.dumps(portable) + json.dumps(host))
        self.assertEqual(sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()),
                         ["brief", "design", "edit", "optimize", "plugin-website", "preview", "publish", "setup"])
        for catalog in ("marketplace.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
            self.assertFalse((ROOT / catalog).exists(), catalog)

    def test_documentation_manifest_uses_only_supported_fields_with_existing_relative_sources(self):
        data = json.loads(read("docs/documentation.json"))
        self.assertLessEqual(set(data), {"schema_version", "source_skill", "extra_sources", "open_questions", "documentation"})
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["documentation"], {"languages": ["de", "en"], "default_language": "de"})
        self.assertTrue((ROOT / data["source_skill"] / "SKILL.md").is_file())
        sources = data["extra_sources"]
        self.assertEqual(len(sources), len(set(sources)))
        for rel in sources + [data["source_skill"]]:
            self.assertFalse(Path(rel).is_absolute() or ".." in Path(rel).parts, rel)
            self.assertTrue((ROOT / rel).exists(), rel)
        # all five skills and the canonical definition are reachable as sources (no second product definition is created)
        covered = " ".join(sources + [data["source_skill"]])
        for skill in ("setup", "preview", "optimize", "edit", "publish", "plugin-website", "brief", "design"):
            self.assertIn(f"skills/{skill}", covered)
        self.assertIn("SCOPE.md", sources)


class UserDocumentation(unittest.TestCase):
    def test_every_german_page_has_an_english_counterpart_and_the_other_way_round(self):
        self.assertEqual(sorted(p.name for p in (DOCS / "de").glob("*.md")), PAGE_NAMES)
        self.assertEqual(sorted(p.name for p in (DOCS / "en").glob("*.md")), PAGE_NAMES)
        self.assertTrue((ROOT / "README.md").is_file() and (ROOT / "README.en.md").is_file())

    def test_paired_pages_carry_the_same_structure_commands_and_links(self):
        pairs = [("README.md", "README.en.md")] + [(f"docs/de/{n}", f"docs/en/{n}") for n in PAGE_NAMES]
        for de, en in pairs:
            with self.subTest(page=de):
                self.assertEqual(len(headings(read(de))), len(headings(read(en))), "level-two headings")
                self.assertEqual(normalised_links(de), normalised_links(en), "link targets")
                shell = lambda t: [re.sub(r"[ \t]+#.*", "", block) for block in re.findall(r"```(?:sh|bash)\n(.*?)```", t, re.S)]  # noqa: E731
                self.assertEqual(shell(read(de)), shell(read(en)), "shell commands")
                if not de.endswith("screens.md"):
                    block = lambda t: re.findall(r"```text\n(.*?)```", t, re.S)  # noqa: E731
                    self.assertEqual(block(read(de)), block(read(en)), "text command blocks")
                self.assertEqual(read(de).count("NOT RUN"), read(en).count("NOT RUN"), "NOT RUN statements")

    def test_the_structural_headings_of_the_manager_outline_are_kept_in_order(self):
        german = {"README.md": ["Für wen ist das gedacht?", "So sieht es aus", "Funktionen und Modi", "Schnellstart", "Nutzung",
                                "Speicherung und Datenschutz", "Projektstatus", "Entwicklung"],
                  "docs/de/installation.md": ["Plattform auswählen", "Installieren", "Aktualisieren", "Entfernen", "Erste Nutzung prüfen"],
                  "docs/de/usage.md": ["Einrichten", "Ablauf auswählen", "Ausgabe verstehen", "Sitzung steuern", "Später fortsetzen", "Spezialisierte Abläufe"],
                  "docs/de/storage.md": ["Speichermodell", "Einrichtung und Konfiguration", "Speichern und fortsetzen", "Fehler und Wiederherstellung", "Einschränkungen"],
                  "docs/de/faq.md": ["Produkt und Zugang", "Voraussetzungen", "Datenschutz und Speicherung", "Fehlerbehebung", "Grenzen der Prüfung"],
                  "docs/de/screens.md": ["Vorschau", "Beispielablauf", "Echte Screenshots", "Aufnahmecheckliste"],
                  "docs/de/development.md": ["Kanonische Quelle", "Prüfungen", "Paketierung", "CI und Releases", "Dokumentation pflegen"]}
        for rel, expected in german.items():
            self.assertEqual([h[3:] for h in headings(read(rel))], expected, rel)

    def test_internal_links_and_images_resolve(self):
        pages = USER_PAGES + ["CHANGELOG.md", "docs/migration/acceptance.md"]
        broken = []
        for rel in pages:
            page = ROOT / rel
            for target in LINK.findall(read(rel)) + IMG.findall(read(rel)):
                if re.match(r"(https?:|mailto:)", target) or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0]
                if path and not (page.parent / path).resolve().exists():
                    broken.append(f"{rel}: {target}")
        self.assertEqual(broken, [])

    def test_user_pages_have_no_developer_paths_template_comments_skeleton_wording_or_inflated_claims(self):
        for rel in USER_PAGES + ["CHANGELOG.md"]:
            text = read(rel)
            low = text.lower()
            with self.subTest(page=rel):
                for bad in ("/Users/", "/home/", "www.draftmode", "peterfux", "C:\\"):
                    self.assertNotIn(bad, text)
                self.assertNotIn("<!--", text, "leftover template instruction comment")
                for bad in ("plugin-skeleton", "nicht funktionsfähig", "not functional yet", "work in progress"):
                    self.assertNotIn(bad, low)
                for bad in ("production ready", "production-ready", "produktionsreif", "fully supported", "vollständig unterstützt",
                            "host acceptance passed", "hostabnahme bestanden"):
                    self.assertNotIn(bad, low)

    def test_open_evidence_and_the_main_limits_are_stated_in_both_languages(self):
        required = {
            "de": ["NOT RUN", "publish", "src/pages/index.astro", "modified (kept)", "conflict", "BD-28", "musterbasiert"],
            "en": ["NOT RUN", "publish", "src/pages/index.astro", "modified (kept)", "conflict", "BD-28", "pattern-based"],
        }
        for lang, words in required.items():
            text = "\n".join(read(f"docs/{lang}/{n}") for n in PAGE_NAMES) + read("README.md" if lang == "de" else "README.en.md")
            for word in words:
                self.assertIn(word, text, f"{lang}: {word}")
        for lang, visual in (("de", "technically checked, visual check open"), ("en", "technically checked, visual check open")):
            self.assertIn(visual, read(f"docs/{lang}/usage.md"))
        for name in ("website.schema.json", "website.json", "website.manage.json"):
            for lang in ("de", "en"):
                self.assertIn(name, read(f"docs/{lang}/storage.md"), (lang, name))

    def test_screens_pages_state_that_no_real_screenshots_exist(self):
        for lang in ("de", "en"):
            text = read(f"docs/{lang}/screens.md")
            self.assertFalse(list((DOCS / "assets").glob("**/*screenshot*")))
            self.assertIn("NOT RUN", text)
            self.assertIn("demo.example", text)

    def test_installation_pages_name_the_manager_contract_marketplace_and_the_plugin_and_do_not_claim_an_import(self):
        for lang in ("de", "en"):
            text = read(f"docs/{lang}/installation.md")
            for needle in ("https://github.com/draftm0de/ai.plugins", "website@draftmode-ai-plugins", "draftmode-ai-plugins"):
                self.assertIn(needle, text)
            for heading in ("### Claude", "### Codex"):
                self.assertIn(heading, text)
            self.assertNotIn("zyris-website@", text)
            self.assertNotIn("website-manager", text)


class Completeness(unittest.TestCase):
    """R26: every inventory file has exactly one resolvable treatment."""

    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(read("docs/migration/source-inventory.json"))
        cls.mapping = json.loads(read("docs/migration/completeness.json"))

    def test_every_inventory_file_is_assigned_exactly_once_and_nothing_else(self):
        inventory = [f["path"] for f in self.inventory["files"]]
        assigned = [e["source"] for e in self.mapping["files"]]
        self.assertEqual(len(inventory), 130)
        self.assertEqual(sorted(assigned), sorted(inventory))
        self.assertEqual(len(assigned), len(set(assigned)))
        sha_by_path = {f["path"]: f["sha256"] for f in self.inventory["files"]}
        for entry in self.mapping["files"]:
            self.assertEqual(entry["source_sha256"], sha_by_path[entry["source"]], entry["source"])

    def test_counts_add_up_and_each_entry_has_one_known_treatment_with_its_required_evidence(self):
        counts = {"identical": 0, "adapted": 0, "not-adopted": 0}
        for entry in self.mapping["files"]:
            kind = entry["treatment"]
            self.assertIn(kind, counts, entry["source"])
            counts[kind] += 1
            if kind == "identical":
                self.assertEqual(set(entry) - {"note"}, {"source", "source_sha256", "treatment", "target", "target_sha256"}, entry["source"])
            elif kind == "adapted":
                self.assertEqual(set(entry), {"source", "source_sha256", "treatment", "targets", "changes", "evidence"}, entry["source"])
                self.assertGreaterEqual(len(entry["changes"].split()), 2, entry["source"])
                self.assertTrue((ROOT / entry["evidence"]).is_file(), entry["source"])
            else:
                self.assertLessEqual({"source", "source_sha256", "treatment", "reason", "basis"}, set(entry), entry["source"])
                self.assertGreaterEqual(len(entry["reason"].split()), 4, entry["source"])
                self.assertGreaterEqual(len(entry["basis"].split()), 2, entry["source"])
                for vague in ("later", "später", "misc", "sonstiges", "other", "tests"):
                    self.assertNotEqual(entry["reason"].strip().lower(), vague, entry["source"])
        self.assertEqual(counts, self.mapping["counts"])
        self.assertEqual(sum(counts.values()), 130)

    def test_identical_targets_have_the_recorded_hash_and_adapted_targets_exist_and_really_differ(self):
        for entry in self.mapping["files"]:
            if entry["treatment"] == "identical":
                target = ROOT / entry["target"]
                self.assertTrue(target.is_file(), entry["target"])
                self.assertEqual(sha(target), entry["source_sha256"], entry["target"])
                self.assertEqual(entry["target_sha256"], entry["source_sha256"])
            elif entry["treatment"] == "adapted":
                for rel in entry["targets"]:
                    path = ROOT / rel
                    self.assertTrue(path.is_file(), f"{entry['source']} -> {rel}")
                    self.assertNotEqual(sha(path), entry["source_sha256"], f"{rel} is byte-equal: classify as identical")
            else:
                for rel in entry.get("covered_by", []):
                    self.assertTrue((ROOT / rel).exists(), f"{entry['source']} covered_by {rel}")
            for rel in ([entry["target"]] if "target" in entry else entry.get("targets", [])):
                self.assertFalse(Path(rel).is_absolute() or ".." in Path(rel).parts, rel)

    def test_no_planned_or_ex_packaging_function_has_a_target_runtime(self):
        by_source = {e["source"].split("zyris-website/", 1)[-1]: e for e in self.mapping["files"]}
        for planned in ("contracts/publish.md", "templates/github/workflows/README.md", "tools/package_plugin.py", "tools/test_package_plugin.py"):
            self.assertEqual(by_source[planned]["treatment"], "not-adopted", planned)
        self.assertFalse(list((ROOT / "skills").rglob("*.yml")))
        self.assertFalse((ROOT / "tools").exists())
        self.assertEqual(sorted(p.name for p in (ROOT / "skills" / "publish").iterdir()), ["SKILL.md"])


class LaunchJsonIgnoreStatement(unittest.TestCase):
    """The plugin adds no ignore rule for .claude/launch.json, so the texts must not claim the file is git-ignored."""

    FILES = ("skills/_shared/references/interfaces.md", "skills/preview/references/preview.md")

    def test_no_blanket_claim_that_launch_json_is_git_ignored(self):
        for rel in self.FILES:
            for line in read(rel).splitlines():
                if "launch.json" in line:
                    self.assertNotRegex(line, r"(?i)\bno \(ignored|git-ignored,", rel)
                    self.assertNotRegex(line, r"(?i)launch\.json`? is git-ignored", rel)

    def test_texts_say_it_depends_on_the_project_and_the_plugin_adds_no_rule(self):
        for rel in self.FILES:
            text = read(rel)
            self.assertRegex(text, r"(?i)depends on the website project", rel)
            self.assertRegex(text, r"(?i)plugin adds no|adds none", rel)

    def test_setup_and_templates_really_add_no_launch_json_ignore_rule(self):
        for path in list((ROOT / "skills" / "setup").rglob("*")):
            if path.is_file() and path.suffix in (".py", ".tpl", ".json", ".md", ".mjs") and "references" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                if ".gitignore" in path.name or "gitignore" in text.lower():
                    self.assertNotIn(".claude/launch.json", text, path.as_posix())


class AcceptanceMatrix(unittest.TestCase):
    """The matrix may not turn missing evidence into acceptance."""

    @classmethod
    def setUpClass(cls):
        cls.text = read("docs/migration/acceptance.md")

    def rows(self, first_cell_pattern):
        return [[c.strip() for c in line.strip().strip("|").split("|")] for line in self.text.splitlines()
                if re.match(r"\|\s*" + first_cell_pattern + r"\s*\|", line)]

    def test_all_requirements_of_scope_appear_once_in_the_matrix_with_a_known_status(self):
        scope_ids = re.findall(r"(?m)^## (R[0-9]+):", read("SCOPE.md"))
        self.assertEqual(sorted(scope_ids, key=lambda r: int(r[1:])), [f"R{i}" for i in range(1, 35)])
        rows = self.rows(r"R[0-9]+")
        self.assertEqual(sorted((r[0] for r in rows), key=lambda r: int(r[1:])), [f"R{i}" for i in range(1, 35)])
        for row in rows:
            self.assertEqual(len(row), 7, row[0])
            self.assertIn(row[5].split(" ")[0], {"teilbelegt", "strukturell", "offen"}, row)
            self.assertNotRegex(row[5].lower(), r"abgenommen|accepted|bestanden", row)
            self.assertTrue(row[6], f"{row[0]} has no remaining gap")

    def test_every_skill_is_listed_separately_for_claude_and_codex_and_unrun_categories_stay_not_run(self):
        rows = self.rows(r"(?:plugin-website|brief|design|setup|preview|optimize|edit|publish)")
        self.assertEqual(sorted((r[0], r[1]) for r in rows),
                         sorted((s, h) for s in ("plugin-website", "brief", "design", "setup", "preview", "optimize", "edit", "publish") for h in ("Claude", "Codex")))
        for row in rows:
            self.assertEqual(len(row), 8, row[:2])
            for cell in (row[5], row[6], row[7]):  # native host, model judgement, visual check
                self.assertRegex(cell, r"^(NOT RUN|n/a)", row[:2])
            if row[0] == "publish":                 # no runtime, no tool run
                self.assertRegex(row[4], r"^n/a", row[:2])
            else:                                   # real tools: only a stated, bounded run counts (report in docs/migration)
                self.assertRegex(row[4], r"^(NOT RUN|ausgeführt \(Etappe 7, hostunabhängig)", row[:2])
                if row[4].startswith("ausgeführt"):
                    self.assertIn("NOT RUN", row[4], row[:2])   # the limits of the run are named, never an unbounded success

    def test_the_completeness_numbers_in_the_matrix_document_equal_the_mapping(self):
        counts = json.loads(read("docs/migration/completeness.json"))["counts"]
        for kind, label in (("identical", "bytegleich übernommen"), ("adapted", "absichtlich angepasst"), ("not-adopted", "bewusst nicht übernommen")):
            row = [r for r in self.rows(r"[^|]*" + label + r"[^|]*")]
            self.assertEqual(len(row), 1, label)
            self.assertEqual(row[0][1], str(counts[kind]), label)
        self.assertIn("**130**", self.text)
        self.assertIn("**0 unzugeordnet**", self.text)

    def test_stage_six_stays_review_pending_and_local_state_is_separated_from_host_and_publication(self):
        self.assertIn("Review ausstehend", self.text)
        for heading in ("## Lokale Migration", "## Hostabnahme", "## Veröffentlichung"):
            self.assertIn(heading, self.text)


if __name__ == "__main__":
    unittest.main()
