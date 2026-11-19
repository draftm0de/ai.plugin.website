# Migration: Plan Quelle → Ziel

Migrationsnachweis, keine zweite Produktdefinition. Anforderungen: [SCOPE.md](../../SCOPE.md). Entscheidungen und offene Punkte: [decisions.md](decisions.md). Stand: 2026-11-19, Etappe 0, überarbeitet nach Review 1 (Planung); Etappe 1 umgesetzt, siehe [changes.md](changes.md) und decisions.md Abschnitt 12; Etappe 2 (setup, Schemaumbenennung) umgesetzt, siehe decisions.md Abschnitt 13; Etappe 3 (preview) umgesetzt, siehe decisions.md Abschnitt 14 und changes.md; Etappe 4 (optimize) umgesetzt, siehe decisions.md Abschnitt 15 und changes.md. Offene Punkte sind in [decisions.md](decisions.md) nach Kategorie geordnet.

Quelle (nur lesen): `/Users/peterfux/PhpstormProjects/drafm0de/www.draftmode`, Plugin `.claude/plugins/zyris-website/`. Ziel: dieses Repository. Globale Regeln: `ai.plugins`. Strukturreferenz: `ai.plugin.interview-coach` (liefert Format, keine Website-Anforderungen).

## 1. Ausgangsbasis

| Repository | Zustand bei Etappe 0 |
|---|---|
| `www.draftmode` | Branch `main`, HEAD `8a08a8752d3e4dd1695d9cac0267182e756f613e`; 17 geänderte und 8 unversionierte Pfade; inventarisiert sind 130 relevante Dateien (105 unverändert, 16 geändert – davon 12 im Pluginordner –, 9 neu) |
| `ai.plugin.website` | Branch `main`, noch kein Commit; alle Dateien unversioniert (Skeleton aus `plugin-create`); 48 Dateien in `target-baseline.json` |
| `ai.plugins` | HEAD `07c52bd…`; `marketplace.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` geändert (Skeleton-Eintrag `website-manager`, unverändert gelassen) |
| `ai.plugin.interview-coach` | HEAD `47f45f2…`, sauber |

Nachweise: [source-inventory.json](source-inventory.json) (Pfad, Status tracked/modified/untracked, SHA-256, bei geänderten Dateien auch `head_sha256`, Baum-Digest `7344f315…`), [target-baseline.json](target-baseline.json) (Baum-Digest `c60417ff…`), [reference-baseline.json](reference-baseline.json) (Regeln und Vorlagen von `ai.plugins` und Coach).

### Drift-Erkennung vor jeder späteren Etappe

1. Quell-HEAD, `git status --porcelain` und jede Hash-Zeile von `source-inventory.json` müssen mit dem Arbeitsstand übereinstimmen; zusätzlich wird geprüft, ob unterhalb von `.claude/plugins/zyris-website/` Dateien hinzugekommen oder entfallen sind.
2. Dasselbe für `reference-baseline.json` (geänderte Regeln/Vorlagen vor der Etappe lesen).
3. Bei jeder Abweichung: stoppen, Abweichung berichten, keine andere Quelle still übernehmen. Eine neue Basis entsteht nur auf Weisung als zusätzliche Datei `source-inventory.<Datum>.json`; die alte bleibt erhalten.
4. Etappe 1 liefert dafür das lesende Entwicklungswerkzeug `scripts/migration_baseline.py` (nur Hashen und `git`-Lesebefehle; kein Zielcode). Bis dahin wird manuell geprüft.

Ausgeschlossen vom Inventar (Begründung in der JSON-Datei): `sites/`, `.project/`, Caches, generierte Dateien, README/AGENTS/`.github` des Website-Repositories.

## 2. Zielstruktur

```
plugin.json, .claude-plugin/plugin.json (abgeleitet), assets/, LICENSE, Makefile, install.sh
skills/
  _shared/                        kein SKILL.md
    scripts/                      which_site.py + Paket site_common/ (schema, errors, manifest, sites)
    resources/                    Manifest-Schema des Plugins (einzige Kopie)
    references/                   gemeinsame Regeln (communication, Schnittstellen, Standortwahl)
  setup/    SKILL.md  scripts/  templates/ (astro-static, _manifest/static, types.json)  references/
  preview/  SKILL.md  scripts/  templates/launch/  references/
  optimize/ SKILL.md  scripts/  references/
  edit/     SKILL.md  scripts/  references/
  publish/  SKILL.md                                      (keine references/)
scripts/    plugin.py verify.py run_tests.py + migration_baseline.py (Entwicklung)
tests/      unit/<skill>/  integration/<skill>/  contracts/  behavior/  native/  fixtures/  support/  (nur benötigte)
docs/       de/ en/ migration/ …
```
Ordner werden nur angelegt, wenn eine Etappe sie füllt. Kein Ziel erhält `contracts/` oder `tools/` aus der Quelle als Ordner; Verträge werden zu Skill-Referenzen (Q7), Packaging entfällt.

## 3. Zuordnung Quelle → Ziel

Quellpfade relativ zu `.claude/plugins/zyris-website/` (außer `tools/`, `docs/`, Wurzeldateien). „Etappe“ = wann migriert wird. Tests: Gruppe im Ziel; die Klassifikation unit/integration beruht auf Dateiname und Hilfsmitteln (fake npm, echte Git-Repos, echte lokale Prozesse) und wird in der jeweiligen Etappe bestätigt.

### 3.1 Gemeinsame Grundlagen und Identität (Etappe 1)

| Quelle | Ziel | Notwendige Anpassung | Betroffene Tests |
|---|---|---|---|
| `.claude-plugin/plugin.json` (Name `zyris-website`, `0.1.0-dev`) | — | nicht übernehmen; Ziel-`plugin.json` ist kanonisch, Host-Manifest daraus ableiten, keine Version | `tests/contracts` Identität |
| (neu) | `plugin.json`, `.claude-plugin/plugin.json`, `docs/documentation.json` | `name website`, Anzeigename „Website“, Beschreibung; `source_skill` verweist noch auf `skills/website-manager` → mit Manager-Vertrag klären | `scripts/plugin.py check`, `verify.py` |
| `skills/*/SKILL.md` ↔ `contracts/communication.md` (Block `user-communication`) | `skills/_shared/references/communication.md` (Etappe 1, byte-gleich); identischer Block in allen fünf `SKILL.md` mit den Skills (Etappen 2–5) | Block unverändert; Textgleichheitstest bleibt | `tools/test_skill_texts.py` → `tests/contracts` |
| `contracts/interfaces.md` | `skills/_shared/references/` (nur Regeln 1–9, Schreibinventar §3a, Vokabular) | Snapshot A/B, `draftmode.srv`-Tabellen (§1, §4, §5), §6 Ladetest, §7 nicht übernehmen (Q7, T-04) | Vertragstexte |
| `scripts/{setup,preview,optimize}/schema.py` | `skills/_shared/scripts/` (V3, nach Prüfschritten) | byte-gleich (`b4c2f9fa5438`) – Hinweis; zusätzlich Importkontext und Fehlerverhalten prüfen | Validator-Tests |
| `scripts/{preview,optimize}/{errors,manifest,sites}.py` | `skills/_shared/scripts/` (V3, nach Prüfschritten) | je byte-gleich zwischen preview und optimize (Hinweis); Importweg ohne Namenskollision, Ressourcenpfad (`parents[2]`), Fehlerklassen prüfen | Resolver-/Manifest-Tests |
| `scripts/setup/{errors,manifest}.py` | `skills/setup/scripts/` | **nicht gleich** zu den anderen (Ask-Optionen, Funktionssignaturen) → getrennt halten | setup-Tests |
| `scripts/optimize/which_site.py` | `skills/_shared/scripts/` (V3, nach Prüfschritten) | Importe/Selbsteinfügung in `sys.path` prüfen; `edit` ruft es per Prozess | `which_site`-Tests |
| `templates/setup/_manifest/root/zyris-website.schema.json` | `skills/_shared/resources/website.schema.json` | Pfad in vier `manifest.py`/`static_setup.py` und `tests/shared` ersetzen (derzeit `parents[2]/templates/setup/…`); Dateiname: ursprünglich unverändert (R4), seit Etappe 2 `website.schema.json` (D-17), Inhalt byte-gleich | `tests/shared/manifest_contract.py` |
| `tests/shared/{contract_cases,manifest_contract}.py`, drei `fixtures/zyris-website.schema.json` | `tests/support/`, Fixtures aus der einen Schema-Datei | drei Schema-Kopien in Fixtures ersetzen | Manifest-Vertragstests |

### 3.2 setup (Etappe 2)

| Quelle | Ziel | Anpassung | Tests |
|---|---|---|---|
| `skills/setup/SKILL.md` | `skills/setup/SKILL.md` | Namen (Q4), Aufrufpfade und `allowed-tools` gemeinsam neu (Hostplanung 5b), Testzeile entfällt (T-06), Statusabsätze aus SCOPE | `tests/contracts` |
| `scripts/setup/site_setup.py` (95), `static_setup.py` (802), `ownership.py`, `clone.py`, `gitinfo.py`, `scratch.py`, `validate.py` | `skills/setup/scripts/` | `RES = parents[2]/templates/setup` → skill-relativ; Schema aus `_shared`; Meldungen `/zyris-website:setup` (T-08) | `tests/{unit,integration}/setup/` |
| `templates/setup/astro-static/**` (Baum), `_manifest/static/zyris-website.json.tpl`, `types.json` | `skills/setup/templates/` | Unveränderte Templates byte-gleich (Hashgleichheit); absichtlich angepasste Texte (Treffer „zyris“ in `CLAUDE.md.tpl`, `rules/seo.md`: Skillnamen; Datenformatnamen bleiben) nur über die explizite Änderungsliste mit begrenztem Diff; vorher Prüfung auf reale Inhalte; `og-default.png` binär | Prüfplan 5a |
| `tests/setup/*` (13 Dateien inkl. Fixtures) | `tests/unit/setup`, `tests/integration/setup`, `tests/fixtures/setup` | `static_helpers.PROJECT_ROOT` (reale Website) entfernen; `test_static_adopt` Zeilen 205–206 durch fiktives Manifest ersetzen; `test_validator_copies` wird zum „keine Duplikate“-Test | — |
| `tests/setup/test_real_npm.py` | Einordnung nach Verhalten in Etappe 2 (decisions 5.4) | Netzwerk, `npm install`; Schalter `ZW_REAL_NPM`; kein nativer Hosttest, läuft nie im Standardlauf | `NOT RUN` |

### 3.3 preview (Etappe 3)

| Quelle | Ziel | Anpassung | Tests |
|---|---|---|---|
| `skills/preview/SKILL.md` | `skills/preview/SKILL.md` | wie 3.2; zusätzlich Claude-Browser-Werkzeuge und `.claude/launch.json` hostspezifisch benennen (Hostplanung 5b); `needs-install` ohne Installation durch den Skill formulieren | `tests/contracts` |
| `scripts/preview/{control (871), preview, sites, errors, manifest, schema}.py` | `skills/preview/scripts/{control,preview}.py` + `_shared` | `RES = parents[2]/templates/preview` → skill-relativ; `ZYRIS_WEBSITE_STATE_DIR`/Temp-Ordner (unverändert, Q5) | `tests/integration/preview/` |
| `templates/preview/launch/astro-static.json.tpl` | `skills/preview/templates/launch/` | `autoPort:false`-Wirkung ist ungeprüft (Vertrag §13) → Claude-Artefakt kennzeichnen | Template-/Launch-Tests |
| `tests/preview/{test_control (855), test_inspect, test_preview, test_sites, test_manifest_contract, helpers, fixtures}` | `tests/integration/preview/` (echte lokale Prozesse/HTTP-Server), `tests/unit/preview/` (Resolver, Manifest) | Loopback-Prozesstests im Rahmen von D-14 | — |

### 3.4 optimize (Etappe 4)

| Quelle | Ziel | Anpassung | Tests |
|---|---|---|---|
| `skills/optimize/SKILL.md` | `skills/optimize/SKILL.md` | T-01 (Satz zu `edit`), T-10 (Dependency-Text), Namen, Pfade | `tests/contracts` |
| `scripts/optimize/{audit (569), worklist (504), findings, store}.py` | `skills/optimize/scripts/` | Importe auf geteilte Module; Marker `zyris-optimize:*` in Berichten/Arbeitsliste bleiben (R4) | `tests/{unit,integration}/optimize/` |
| `tests/optimize/*` (+ `fixtures/`) | wie oben | `test_findings.py:98` liest Prüfskripte der realen Site → fiktive/mitgelieferte Referenz (decisions 5.4); `helpers.py` verweist auf nicht vorhandenes `templates/optimize` (prüfen) | — |

### 3.5 edit und publish (Etappe 5)

| Quelle | Ziel | Anpassung | Tests |
|---|---|---|---|
| `skills/edit/SKILL.md` | `skills/edit/SKILL.md` | Verweise auf optimize-/preview-Skripte neu auflösen (V3); Sichtprüfung je Host (Hostplanung 5b) | `tests/contracts` |
| `scripts/edit/edit.py` (430) | `skills/edit/scripts/edit.py` | `RESOLVER = parent/optimize/which_site.py` (Prozessaufruf mit `-I`) → geteilter Pfad; Temp-Ordner-Logik (kennt `ZYRIS_WEBSITE_STATE_DIR` nicht) angleichen oder belassen (Q5) | `tests/integration/edit/` |
| `tests/edit/{helpers,test_edit (533)}` | `tests/integration/edit/` | `helpers.py` bindet `tests/setup/static_helpers` und `scripts/setup` ein → über `tests/support/` lösen | — |
| `tests/behavior/cases.md` (B1–B11, manuell) | `tests/behavior/` bzw. `tests/native/` | nach Modellurteil/Hostverhalten je Fall; nichts als bestanden führen | `NOT RUN` |
| `skills/publish/SKILL.md` | `skills/publish/SKILL.md` | keine Verweise auf Geplantes (decisions 4.4); kein Skript; keine `allowed-tools` | `tests/contracts` |
| `contracts/publish.md`, `templates/github/workflows/README.md` | — (nicht übernommen) | geplantes Verhalten, außerhalb (D-05/D-06) | — |

### 3.6 Entwicklungs- und Packagingdateien der Quelle (nur Evidenz)

| Quelle | Behandlung |
|---|---|
| `tools/package_plugin.py`, `tools/test_package_plugin.py`, `Makefile` (Ziel `plugin`) | nicht migriert (ZIP-Weg, T-05); die Zusicherung „jede von einem Skill referenzierte Ressource liegt in der ausgelieferten Nutzlast“ wird als Vertragstest neu gefasst |
| `tools/test_plugin_paths.py` | Verhalten „Aufrufmuster laufen aus einem Pfad mit Leerzeichen, fehlender Pfad wird erkannt“ → `tests/integration`, gegen den Zielpfad statt ZIP |
| `tools/test_skill_texts.py` | → `tests/contracts` (Blockgleichheit, schmale Freigaben, Pflichtsätze); Textprüfung beweist kein Verhalten |
| `docs/website-plugin-development.md`, `CLAUDE.md` (Quelle) | Evidenz für Betrieb/Entscheidungen; Inhalte fließen nur über SCOPE und `docs/` des Ziels ein, nicht kopiert |

## 4. Querabhängigkeiten (belegt)

| ID | Abhängigkeit | Beleg | Folge im Ziel |
|---|---|---|---|
| X1 | Manifest-Schema des Plugins wird von setup (schreibt Projektkopie), preview, optimize (je `manifest.py`: `parents[2]/templates/setup/_manifest/root/…`) und den Tests gelesen; drei weitere Schema-Kopien liegen als Test-Fixtures | `manifest.py` Zeile 20/24, `static_setup.py:168`, `tests/shared/manifest_contract.py:17` | eine Datei unter `_shared`; Pfade und Fixtures ersetzen; relative Ressourcenpfade (`parents[2]`) sind Teil der V3-Prüfung |
| X2 | Resolver: `sites.py`+`manifest.py`+`errors.py` doppelt (preview, optimize), `which_site.py` nur in optimize; `edit.py` startet es per Prozess; `control.py`/`preview.py` importieren `sites` | Importgraph, `edit.py:37,173` | V3 (technische Entscheidung); `edit` darf nicht an einem Geschwister-Skillordner hängen |
| X3 | Flache Importe (`import errors`, `import schema`) mit `sys.path.insert` je Skriptordner; die Tests fügen mehrere Skriptordner in einen Prozess ein (`tests/edit/helpers.py:16–18`) | Quellen | Namenskollisionen zwischen `setup/errors.py` und `_shared`-Version möglich → Importweg in Etappe 1; Tests isolieren |
| X4 | Templates: setup rendert `templates/setup/**`; preview liest `templates/preview/launch`; `clone.py` rendert Platzhalter; `types.json` steuert Typ, Befehle und Ignore-Listen; Besitzprotokoll trägt `template_version` | `static_setup.py`, `preview.py:17–18` | Templates beim jeweiligen Skill; Prüfung nach Prüfplan 5a (unverändert = Hashgleichheit; absichtlich angepasst = begründeter, begrenzter Diff) |
| X5 | Zustand außerhalb des Repositories: preview-Besitzprotokoll und Log in `<TMP>/zyris-website/<Projekt-Hash>/` (mit `ZYRIS_WEBSITE_STATE_DIR`), `edit` legt Sicherungsordner im selben Basisordner an, ohne die Variable zu beachten | `control.py:79–80`, `edit.py:110` | Q5 (Vorgabe unverändert); Abweichung bewusst festhalten |
| X6 | Projektdateien als Schnittstelle: Manifest, Schema-Kopie, `*.managed.json` (nur setup schreibt; `edit` fasst nie an), `.project/reports/<site>/optimize*` (nur optimize; `edit` nie), `.claude/launch.json` (nur preview), `.tmp/`, `dist/`, `package-lock.json` (setup `--build`/`verify` können sie schreiben) | Skilltexte, Verträge | R4; keine Umbenennung |
| X7 | Skillübergreifende Aufrufe: `edit`→`optimize/which_site.py`, `edit`→`preview/control.py inspect|start`, Meldungen aller Skills nennen `setup`, `edit`↔`optimize` über Befund-IDs (`decide|apply`) | `edit/SKILL.md` | Aufrufpfade nach V3; Meldungstexte Q4 |
| X8 | Prüfskripte der Site (`seo-check.mjs`, `a11y-check.mjs`): Vorlage in `templates/setup/astro-static/scripts/`; `findings.py` ist an deren Ausgabeformat gebunden; ein Test liest die Kopien der realen Site | `test_findings.py:98` | Gleichheit Vorlage ↔ Site unbelegt (nicht untersucht); decisions 5.4 |
| X9 | Tests: `tests/edit/helpers` → `tests/setup/static_helpers` → `helpers` (+ `static_setup`); reale Website als Eingabe (`PROJECT_ROOT`) | Quellen | `tests/support/`, fiktive Fixtures |
| X10 | Packaging leitet benötigte Ressourcen aus `SKILL.md`-Verweisen und Importen ab (`SKILLS`-Tupel, `REMOVED_PATHS`) | `package_plugin.py` | entfällt; Vertragstest ersetzt |
| X11 | `edit.py` ruft den Resolver mit `python -I` auf; dieser fügt seinen Ordner selbst in `sys.path` ein | `edit.py:173`, `which_site.py:10` | Verhalten nach Verschieben erhalten |
| X12 | Voraussetzungen der Werkzeuge: `ps`, `lsof` (preview), `git`, `npm`/Node (setup, optimize, edit) | Verträge | `docs/prerequisites.md`, Tests mit Fake-Werkzeugen |

## 5. Etappen

Gemeinsam für alle Etappen: Vorab Drift-Prüfung (Abschnitt 1) und Lektüre geänderter Regeln. Erlaubte Aktionen: Dateien im Ziel nach der jeweiligen Liste, lesende Zugriffe auf die Quelle, deterministische Tests (D-10). Verboten: Änderungen an der Quelle, an Marketplace-Dateien (außer Etappe 6 auf Weisung), Installation, Commits, Pushes, Netzwerk, Modell-/Hosttests. Nach jeder Etappe Stopp und Übergabe an den unabhängigen Reviewer.

### Etappe 1 – Skeleton, gemeinsame Grundlagen, Verträge
- **Erlaubt:** `plugin.json` und abgeleitetes Host-Manifest, `docs/documentation.json`, `skills/_shared/**`, `scripts/migration_baseline.py`, `tests/support`, `tests/contracts`, `tests/unit` für geteilte Module, `AGENTS.md`/`docs/architecture.md` (websitebezogene Ergänzungen). Das Skeleton-Skill-Verzeichnis `skills/website-manager/` bleibt bis Etappe 2 bestehen (Zwischenzustand „in Migration“), damit `skills/*/SKILL.md` nie leer ist.
- **R-IDs:** R1 (Manifest-Teil), R2, R3, R4, R5, R6, R7, R17, R19.
- **Voraussetzungen:** Scope-Abnahme (erfolgt, D-12). Technische Entscheidungen werden in der Etappe selbst getroffen und dokumentiert: V3 (mit den drei Prüfschritten), gemeinsame Aufrufkonvention und Freigabemuster (Q1/Q2), Aufrufnamen (Q4), Testklassifikation (Q6), Mindestversionen (Q8).
- **Prüfungen:** `migration_baseline.py` gegen Inventare; `scripts/plugin.py check`; `scripts/verify.py --source .`; Unit-/Vertragstests der geteilten Module; Test „keine Duplikate/keine Verweise auf `www.draftmode`, `ai.plugins`, Coach, absolute Entwicklerpfade“; Import-Isolationstest.
- **Abbruch/Klärung:** Drift der Quelle; Importkollision oder abweichendes Fehlerverhalten nicht lösbar ohne Verhaltensänderung (dann Kopien beibehalten statt zusammenlegen).
- **Übergabe:** Liste geänderter Dateien, echte Testausgabe, `NOT RUN`-Liste, R-Status je Anforderung (`supported_by_source` / `missing_evidence` nur als Selbstauskunft), offene Punkte.

### Etappe 2 – setup
- **Stand:** umgesetzt (2026-11-19) einschließlich der beauftragten Schemaumbenennung (D-16 bis D-18); Details: decisions.md 13, changes.md „Etappe 2“. Skeleton `skills/website-manager/` entfernt. Offen bleiben Hostnachweise (NOT RUN) und der unabhängige Review.
- **Erlaubt:** `skills/setup/**`, `tests/{unit,integration,native}/setup`, `tests/fixtures/setup`; zusätzlich (Auftrag Etappe 2) die Schemaumbenennung in `skills/_shared/**`, `tests/support`, den gemeinsamen Tests und aktuellen Referenzen sowie das Entfernen des Skeleton-Skills.
- **R-IDs:** R4, R5, R7, R8, R9.
- **Voraussetzungen:** Etappe 1 abgenommen; Feldbelegung der Manifest-Initialisierung entschieden (D-16, `setup-init.md`); Prüfung der Templates auf reale Inhalte abgeschlossen; Änderungsliste der absichtlich angepassten Template-/Skilltexte erstellt.
- **Prüfungen:** Hashgleichheit aller unveränderten Templates/Ressourcen gegen das Quell-Inventar; für absichtlich geänderte Dateien Abgleich gegen die Änderungsliste (begrenzter Diff, keine Hashgleichheit gefordert); setup-Tests in isolierten Temp-Repos mit Fake-`npm`; Test-Matrix S1–S17 der Quelle als Rückverfolgung; `test_real_npm` bleibt `NOT RUN`.
- **Abbruch/Klärung:** reale Website-Inhalte oder private Daten in Templates gefunden; Schema/Manifest-Format müsste geändert werden (R4).
- **Übergabe:** wie Etappe 1; zusätzlich Hashnachweis der unveränderten Templates, Änderungsliste mit Diff.

### Etappe 3 – preview
- **Stand:** umgesetzt (2026-11-19); Details: decisions.md 14, changes.md „Etappe 3“. Offen bleiben Hostnachweise (NOT RUN) und der unabhängige Review.
- **Erlaubt:** `skills/preview/**`, `tests/{unit,integration}/preview`.
- **R-IDs:** R5, R6, R10, R11.
- **Voraussetzungen:** Etappe 2 abgenommen. Q10 ist beantwortet (D-14): eigene lokale Prozesse, `127.0.0.1`-Ports und das Beenden ausschließlich eigener, eindeutig identifizierter Testprozesse/-gruppen sind erlaubt, externes Netz nicht.
- **Prüfungen:** Preview-Tests mit Fake-`npm`, `ps`/`lsof`-Attrappen und freien lokalen Ports innerhalb der Grenze von D-14.
- **Abbruch/Klärung:** Hostverhalten (Claude/Codex) würde ohne Beleg behauptet; Sichtprüfung ohne tatsächliche Durchführung als bestanden geführt.
- **Übergabe:** wie oben; Hostmatrix (Abschnitt 6) aktualisiert.

### Etappe 4 – optimize
- **Stand:** umgesetzt (2026-11-19); Details: decisions.md 15, changes.md „Etappe 4“. Offen bleiben Hostnachweise (NOT RUN), echte `npm`/Node-Läufe und der unabhängige Review.
- **Erlaubt:** `skills/optimize/**`, `tests/{unit,integration}/optimize`.
- **R-IDs:** R12, R13, R4 (Berichtsformate), R7.
- **Voraussetzungen:** Etappe 3 abgenommen; Referenz für die Prüfskript-Katalogprüfung festgelegt (decisions 5.4).
- **Prüfungen:** Audit-/Store-/Worklist-Tests mit Fake-`npm` und Wegwerf-Git-Repos; Formatvergleich der erzeugten Berichte gegen Quellfixtures.
- **Abbruch/Klärung:** Berichts-/Arbeitslistenformat müsste geändert werden (R21).
- **Übergabe:** wie oben.

### Etappe 5 – edit und publish-Platzhalter
- **Erlaubt:** `skills/edit/**`, `skills/publish/SKILL.md`, `tests/{integration,behavior}/edit`, `tests/contracts` für publish.
- **R-IDs:** R14, R15, R16, R17.
- **Voraussetzungen:** Etappen 1–4 abgenommen.
- **Prüfungen:** Edit-Tests in Temp-Repos mit von setup erzeugter Fixture-Site; Test, dass `publish` kein Skript, keine Freigaben und keine verbotenen Aussagen enthält.
- **Abbruch/Klärung:** Auftrag würde `edit` über die Startseite hinaus erweitern.
- **Übergabe:** wie oben.

### Etappe 6 – Gesamtprüfung, Dokumentation, Marketplace
- **Erlaubt:** `README.md`, `README.en.md`, `docs/de|en`, `CHANGELOG.md`, `docs/prerequisites.md`, Gesamttests; ein lokaler Marketplace-Eintrag in `ai.plugins` nur auf ausdrückliche Weisung und ohne dessen vorhandene uncommittete Änderungen zu überschreiben (Skeleton-Eintrag `website-manager` → `website`).
- **R-IDs:** alle, R18, R19, R2.
- **Voraussetzungen:** Etappen 1–5 abgenommen.
- **Prüfungen:** `make test`; `verify.py --source . --review`; Rückverfolgung R↔Source/Test; Drift-Prüfung der Quelle; Abgleich Dokumentation (de/en) gegen SCOPE; Hostmatrix vollständig (nicht belegt = `NOT RUN`).
- **Abbruch/Klärung:** widersprüchliche Doku, nicht belegte Hostbehauptung.
- **Übergabe:** Abschlussbericht mit R-Tabelle, Testergebnissen, `NOT RUN`, Marketplace-Änderungen als Diff.

## 5a. Prüfplan (korrigiert)

- **Unveränderte Templates/Ressourcen:** Hashgleichheit gegen `source-inventory.json` (SHA-256 je Datei).
- **Absichtlich angepasste Texte und Pfade** (Skilltexte, Meldungen, Schema-/Template-Pfade, Namen): vorab eine explizite Änderungsliste (Datei, Zeilen/Muster, Grund) und ein auf diese Liste begrenzter Diff gegen die Quelle. Keine Hashgleichheit für absichtlich geänderte Dateien oder deren Renderausgaben; Renderausgaben von Templates werden dateiweise verglichen: unveränderte Dateien hashgleich, geänderte nur gemäß Änderungsliste.
- **Vollständigkeit (R26):** Jede Inventardatei ist übernommen (hashgleich), angepasst (Änderungsliste) oder bewusst nicht übernommen (Grund); Rest ist ein Fehler.
- **Testarten nach tatsächlichem Verhalten:** deterministisch lokal (Wegwerf-Git-Repos, Fake-`npm`, Fake-`ps`/`lsof`) → `unit`/`integration`; `npm install` mit Netzwerk → nicht deterministisch, nicht freigegeben, kein Hosttest, Einordnung mit ausdrücklichem Schalter in Etappe 2; Modell/GUI/Host → `behavior`/`native`, `NOT RUN`.
- **Freigabe:** D-10/D-15 (deterministische Tests in isolierten Verzeichnissen) und D-14 (lokale Prozesstests von `preview`, nur `127.0.0.1`, nur eigene Prozesse).
- **Evidenz in SCOPE:** vorhandene Belege werden als `Source:`/`Test:` verlinkt, fehlende als „Evidenzstatus: noch nicht vorhanden“ geführt; es entstehen keine Platzhalterdateien. `verify --review` darf die Lücken melden.

## 5b. Hostplanung

- **Q1/Q2 gemeinsam:** Die Aufrufmuster der Skilltexte und die Claude-Freigabemuster (`allowed-tools`) werden zusammen aus der neuen Struktur (`skills/<skill>/scripts/…`, `skills/_shared/…`) abgeleitet; alte Muster mit den Quellpfaden (`${CLAUDE_PLUGIN_ROOT}/scripts/<skill>/…`) werden nicht übernommen. Ein Vertragstest prüft, dass jedes Aufrufmuster von genau einem schmalen Muster gedeckt wird und umgekehrt. Für Codex wird keine Vorabfreigabe behauptet. Konventionen beider Hosts (Pfadvariable im Skilltext, Frontmatter-Felder, installiertes Layout einschließlich `skills/_shared/`) sind bis zur Prüfung gegen aktuelle maßgebliche Dokumentation *unverified*; diese Recherche ist ein eigener technischer Schritt in Etappe 1 und kein Test.
- **Prozesssteuerung** (`control.py`) und **Sichtprüfung** werden getrennt geplant und berichtet. Sichtprüfung: nur verfügbare, autorisierte Browserwerkzeuge des jeweiligen Hosts, nur auf die vom Controller gelieferte oder durch `inspect` bestätigte Adresse; kein Browserwerkzeug startet einen Dev-Server oder wechselt den Port. Ohne tatsächlich durchgeführte Sichtprüfung: „visual check open“. Keine neue Browserintegration.
- **Hostfähigkeit wird nie aus dem Fehlen eines Werkzeugnamens abgeleitet** (insbesondere nicht für Codex aus dem Fehlen von `mcp__Claude_Browser__*`): sie bleibt unbelegt, bis ausgeführt.
- `.claude/launch.json` bleibt als bestehende Claude-Desktop-Konfiguration erhalten und gekennzeichnet.

## 6. Hostnachweis-Matrix (Ausgangszustand; preview-Zeile Stand Etappe 3, optimize-Zeile Stand Etappe 4)

| Skill | Claude | Codex |
|---|---|---|
| setup | NOT RUN (nativ); Quelle: Claude-Terminal-/Desktop-Beobachtungen in der Quelle, nicht übernommen | NOT RUN |
| preview | NOT RUN (Skillladen, `${CLAUDE_SKILL_DIR}`, `allowed-tools`, Browser-Pane, `autoPort: false`-Wirkung); lokal belegt nur Controller/`inspect` deterministisch (Etappe 3). Quell-Beobachtungen 2026-11-17/18 nicht übernommen | NOT RUN (Skillpfad, Browserwerkzeug des Hosts unbelegt; `.claude/launch.json` ist ein Claude-Artefakt) |
| optimize | NOT RUN (Skillladen, `${CLAUDE_SKILL_DIR}`, `allowed-tools`-Muster mit `..`, Erreichbarkeit von `skills/_shared/`); lokal belegt nur Treiber, Berichte, Arbeitsliste und `apply` deterministisch mit Fake-`npm` (Etappe 4) | NOT RUN (Skillpfad, Erreichbarkeit von `skills/_shared/`) |
| edit | NOT RUN; GUI-Fall G1 der Quelle offen | NOT RUN |
| publish | NOT RUN | NOT RUN |

Strukturelle und deterministische Prüfungen werden getrennt von nativen Nachweisen geführt und ersetzen diese nie.

## 7. Prüfregeln und Risiken

- Zusammenlegung nur bei belegter semantischer Gleichheit; byte-gleiche Dateien sind der einzige bisher belegte Fall (V3).
- Mehrere Skriptordner dürfen in Tests nicht in denselben `sys.path` gelangen (X3).
- Wiederholte Pfade (`parents[2]/templates/…`) sind der häufigste Bruchpunkt beim Verschieben; ein Test startet jeden Einstiegspunkt aus einer extrahierten Kopie unter einem Pfad mit Leerzeichen.
- Preview-Zustand: Umbenennung von Temp-Ordner oder Umgebungsvariable macht laufende Instanzen unbekannt (Q5).
- Templates, Regeln und Texte, die nach dem Verschieben aus `www.draftmode` stammen, dürfen keine realen Website-Inhalte, Zugangsdaten oder privaten Daten enthalten.
- Die Quelle behauptet viele Tests als bestanden; im Ziel zählt nur, was in der jeweiligen Etappe tatsächlich lief.

## 8. Was Etappe 0 getan hat und nicht getan hat

Getan: Git-Zustände erfasst; 130 Quell-, 48 Ziel- und 81 Referenzdateien gehasht; Skills, Verträge, Dokumentation und Regeln gelesen; Importgraph, Pfadbezüge und Kopien per Hash verglichen; `SCOPE.md`, diese Datei, `decisions.md` und die drei Inventare geschrieben; websitebezogene Ergänzungen in `AGENTS.md` und `docs/architecture.md`.

Nicht getan: keine Runtime migriert oder ausgeführt, keine Tests gestartet, keine Quelle verändert, keine Marketplace-Dateien geändert, keine Installation, kein Netzwerk, kein Commit oder Push.
