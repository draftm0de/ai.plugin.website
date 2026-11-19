# Migration: Änderungsliste und Übernahmenachweis (Stand Etappe 3)

Migrationsnachweis, keine Produktdefinition. Maßgeblich: [SCOPE.md](../../SCOPE.md), Plan: [plan.md](plan.md). Quelle: `www.draftmode/.claude/plugins/zyris-website/` (Pfade unten relativ dazu). Hashes: [source-inventory.json](source-inventory.json) (unverändert). Quellabgleich zu Beginn von Etappe 1 mit `scripts/migration_baseline.py`: 130 Dateien, 0 geändert, 0 fehlend, 0 neu (Ausgabe in der Übergabe).

Status je Datei: **identisch** (Hashgleichheit, im Test `tests/contracts/test_shared_runtime_contract.py` gegen das Inventar geprüft) · **angepasst** (begrenzter Diff, Grund) · **nicht übernommen** (Grund) · **zurückgestellt** (spätere Etappe laut plan.md §3).

## Etappe 1: bearbeitete Quelldateien

| Quelle | Ziel | Status | Grund / Diff |
|---|---|---|---|
| `contracts/communication.md` | `skills/_shared/references/communication.md` | identisch | enthält keine Quell-, Plugin- oder Pfadnamen |
| `contracts/interfaces.md` | `skills/_shared/references/interfaces.md` | angepasst (Teilübernahme) | übernommen: Regeln 1–9, Schreibinventar §3a (Pfade auf `skills/_shared/…` umgestellt, ADR-/`draftmode.srv`-Bezüge in Regel 5 entfernt). **Nicht übernommen:** §1 Snapshots A/B, §4 externe Schnittstellentabelle, §5 Koordinationspunkte, §6 Ladetest, §7 `edit`-Platzierung, Vorbereitungsschritt „isolierte Kopie / `npm ci`“ (geplant, ausgeschlossen: T-10, V2), Vokabeltabelle verkürzt. Grund: D-04/D-05/Q7 |
| `templates/setup/_manifest/root/zyris-website.schema.json` | `skills/_shared/resources/zyris-website.schema.json` | identisch | einzige Kopie; Dateiname bleibt (R4/R21) |
| `scripts/{setup,preview,optimize}/schema.py` | `skills/_shared/scripts/site_common/schema.py` | identisch (3→1) | keine lokalen Importe, nur `re`; Fehlerverhalten (Liste von Fehlertexten, `ValueError` bei unbekanntem Schlüsselwort) für alle drei Aufrufer gleich |
| `scripts/{preview,optimize}/errors.py` | `skills/_shared/scripts/site_common/errors.py` | identisch (2→1) | `Stop`/`Ask` müssen im Prozess dieselben Klassen sein; `setup/errors.py` ist **nicht** gleich (Ask ohne Optionen) und wird nicht zusammengelegt (→ Etappe 2) |
| `scripts/{preview,optimize}/manifest.py` | `skills/_shared/scripts/site_common/manifest.py` | angepasst (2→1) | (1) Importe `import schema as schemalib` / `from errors import Stop` → paketrelativ `from . import schema as schemalib` / `from .errors import Stop`; (2) `PLUGIN_SCHEMA`: `parents[2]/templates/setup/_manifest/root/…` → `parents[2]/resources/zyris-website.schema.json`; (3) Meldung „run /zyris-website:setup“ → „run the `setup` skill of the Website plugin“ (T-08/Q4); (4) Docstring. Logik, Fehlerklassen und übrige Meldungen unverändert. `setup/manifest.py` (andere Signatur, `files()`, Schema-Dict, Typprüfung) nicht zusammengelegt (→ Etappe 2) |
| `scripts/{preview,optimize}/sites.py` | `skills/_shared/scripts/site_common/sites.py` | angepasst (2→1) | paketrelative Importe; zwei Meldungen „run /zyris-website:setup first“ → „run the `setup` skill of the Website plugin first“. Logik unverändert |
| `scripts/optimize/which_site.py` | `skills/_shared/scripts/which_site.py` | angepasst | `import sites` / `from errors import …` → `from site_common import sites` / `from site_common.errors import …`; Selbsteinfügung des eigenen Ordners in `sys.path` bleibt (läuft auch unter `python -I`). Ausgabeformat unverändert |
| `.claude-plugin/plugin.json` (Quelle) | — | nicht übernommen | Ziel-`plugin.json` ist kanonisch, keine Version (T-07) |
| `tests/setup/fixtures/schema-foreign-older.json` | `tests/fixtures/shared/schema-foreign-older.json` | identisch | fremde ältere Projekt-Schemakopie als Testeingabe |
| `tests/{optimize,preview}/fixtures/zyris-website.schema.json`, `tests/shared/*` | — | nicht übernommen / ersetzt | drei Schema-Kopien sind hashgleich mit der Schemadatei; Tests lesen die eine Datei (`tests/support/projects.py`) |
| `tests/{optimize,preview}/test_sites.py` (hashgleich) | `tests/unit/shared/test_sites.py` | angepasst | Assertions übernommen (Defaults, Name/Alias/Titel/Präfix, STOP bei unbekannt, ASK bei mehrdeutig, cwd, Vorrang, „zuletzt“ mit Bestätigung, Einzelsite, fehlendes Manifest); echte Domänen-/Titelnamen der Quelle durch fiktive (`alpha.example`) ersetzt; ergänzt: ungültiges Manifest, leere Komponentenliste, Fehlerklassen |
| `tests/optimize/test_which_site.py` | `tests/integration/shared/test_which_site_entry.py` | angepasst | Assertions (Pfade, Regeln, Brand-Dateien, ASK, cwd, STOP, fehlender Ordner) übernommen, aber als Prozessaufruf aus isolierter Kopie mit Leerzeichen, ohne `PYTHONPATH`, mit `-I -B` |
| `tests/shared/{contract_cases,manifest_contract}.py`, `tests/{setup,preview,optimize}/test_manifest_contract.py` | `tests/unit/shared/test_manifest.py` (Teil) | angepasst (Teilübernahme) | übernommen: Ablehnung von alter Fassung, Typ `astro`, `hugo`, `serve`, `dockerfile`, `registry`, `retention` auch bei gelockerter Projektkopie (mit Nicht-Leer-Beleg), kaputte/fehlende Projektkopie, fremde ältere Kopie bestimmt den Vertrag nicht. **Zurückgestellt:** die Prüfung „vor Build/Bericht/Prozessstart/npm-Aufruf“ je Einstiegspunkt gehört zu den Einstiegspunkten (Etappen 2–4) |
| `tests/setup/test_schema.py` | `tests/unit/shared/test_manifest.py` (Teil) | angepasst (Teilübernahme) | Schemaregeln, Entfernte Felder, `bool` ≠ `integer`, unbekanntes Schlüsselwort; **zurückgestellt:** Kopplung `types.json` ↔ Schema und `static`-Typliste (setup, Etappe 2) |
| `tests/setup/test_validator_copies.py` | — | ersetzt | Gleichheit dreier Kopien entfällt durch genau eine Kopie (Vertragstest „exactly one copy“); der Verhaltensvergleich der **setup**-Variante bleibt Etappe 2 |
| `skills/*/SKILL.md` Block `user-communication` | — | zurückgestellt | Block und Textgleichheitstest (R17) mit den Skills in Etappe 2/5; hier nur die Referenz |

## Zusammenlegung (V3): Ergebnis der drei Prüfschritte

1. **Importkontext:** Die Quelle importiert flach (`import errors`, `import manifest`) über `sys.path.insert(0, <Skriptordner>)`. `setup` hat abweichende `errors.py`/`manifest.py`; ein gemeinsamer Ordner auf `sys.path` würde diese Namen kollidieren lassen. Lösung: Paket `site_common` (Namensraum) unter `skills/_shared/scripts/`; flache Namen bleiben frei. Belegt durch `ImportIsolationTests` (Decoy-Module `errors`/`manifest`/`schema` auf `sys.path` und `PYTHONPATH`).
2. **Ressourcenpfade:** `parents[2]` zeigt jetzt auf `skills/_shared`; Schema unter `resources/`. Belegt durch Test mit entferntem Schema in der Kopie (Ressource wird aus der Kopie gelesen) und Start aus Kopie mit Leerzeichen.
3. **Fehlerklassen und Aufrufer:** `Stop`/`Ask`/Exit-Codes identisch mit preview/optimize (Hash). Aufrufer `which_site.py` fängt `Ask`, `Stop`; `setup` nutzt die gemeinsame `errors.py` **nicht** (Etappe 2).

Beobachtung (kein Bestandsfehler): Beim Start ohne `-B` schreibt Python `__pycache__` in die installierte Kopie (Test `test_bytecode_suppression_flag_…`). Die Aufrufkonvention verlangt deshalb `python3 -B` (siehe [host-conventions.md](host-conventions.md)).

## Noch nicht bearbeitet (Stand Etappe 1, durch den Abschnitt „Etappe 2“ unten für `setup` überholt)

Alle übrigen Inventardateien (setup-, preview-, optimize-, edit-Runtime, Templates, Skilltexte, deren Tests, Verträge außer `communication.md`/`interfaces.md`, Packaging-Evidenz) sind **zurückgestellt** auf die Etappen laut plan.md §3 oder dort als nicht übernommen vorgesehen; keine ist in Etappe 1 verändert oder verworfen worden. R26 ist damit offen.

# Etappe 2: setup und Schemaumbenennung

Quellabgleich zu Beginn von Etappe 2 mit `python3 -B scripts/migration_baseline.py --inventory docs/migration/source-inventory.json --root <www.draftmode> --strict-git`: `files=130 changed=0 missing=0 unreadable=0 unsafe=0 new=0 new_symlinks=0 -> NO DRIFT`. Historische Inventare (`source-inventory.json`, `target-baseline.json`, `reference-baseline.json`) sind unverändert und enthalten daher weiterhin den alten Schema- und Skeleton-Pfad.

## A. Schemaumbenennung (D-17), getrennt nach Datei und Inhalt

| Was | Alt | Neu | Inhalt |
|---|---|---|---|
| Schemadatei im Plugin | `skills/_shared/resources/zyris-website.schema.json` | `skills/_shared/resources/website.schema.json` | **Bytes unverändert**, SHA-256 gleich dem Inventareintrag `templates/setup/_manifest/root/zyris-website.schema.json` (Test `SchemaRenameTests`) |
| Projektkopie | `.project/specs/zyris-website.schema.json` | `.project/specs/website.schema.json` | Kopie des Plugin-Schemas |
| Manifestverweis | `"$schema": "./zyris-website.schema.json"` | `"$schema": "./website.schema.json"` | Template `_manifest/static/zyris-website.json.tpl` |

Verbraucher angepasst (nur Name/Pfad): `skills/_shared/scripts/site_common/manifest.py` (`SCHEMA`, `PLUGIN_SCHEMA`), `skills/_shared/scripts/site_common/schema.py` (nur Docstring; deshalb nicht mehr hashgleich zur Quelle, in `ByteIdentityTests` nicht mehr als identisch geführt, Eintrag in der Liste der angepassten Dateien), `skills/_shared/references/interfaces.md` (Regel 8), `skills/setup/scripts/ownership.py` (nur Docstring), `tests/support/projects.py`, `tests/unit/shared/test_manifest.py`, `tests/integration/shared/test_which_site_entry.py`, `tests/contracts/test_shared_runtime_contract.py`, `SCOPE.md`, `AGENTS.md`, `docs/migration/{setup-init,plan,decisions,host-conventions}.md`.

**Inhaltliche Ergänzung (kein Teil der Umbenennung):** `site_common.manifest` bekommt `LEGACY_SCHEMA` und `legacy_problem(...)`, das den alten Namen nur erkennt, um das alte Format abzulehnen (D-18), und `problems()` ruft es vor der Prüfung der Projektkopie auf (wirkt auf alle gemeinsamen Verbraucher).

**Klassifikation aller verbleibenden Treffer des alten Namens `zyris-website.schema` im Ziel** (Prüfung: `grep -rIl "zyris-website\.schema" . --exclude-dir=.git --exclude-dir=.idea --exclude-dir=.tmp`):

| Treffer | Klasse |
|---|---|
| `skills/_shared/scripts/site_common/manifest.py` (`LEGACY_SCHEMA`, Docstring) | aktive Runtime: nur Erkennung zur Ablehnung, die Datei wird nie gelesen (Test: erlaubte Dateimenge exakt) |
| `skills/setup/SKILL.md` (2×) | normative Anweisung: dokumentiert die Ablehnung des alten Formats |
| `tests/contracts/test_setup_contract.py`, `tests/contracts/test_shared_runtime_contract.py`, `tests/integration/setup/test_init_ports_legacy.py`, `tests/unit/setup/test_schema.py` | negative Tests / Rückwärtsersetzung zum Beleg der Änderungsliste |
| `docs/migration/source-inventory.json` | historisches Inventar (Quellpfad), unverändert |
| `docs/migration/{changes,plan,setup-init,decisions}.md`, `SCOPE.md`, `AGENTS.md` | historische Zuordnung (Quellpfad → Ziel), Entscheidungsdokumentation, Abgrenzung (alter Name als abgelehntes Format) |

## B. setup: Zuordnung Quelle → Ziel

| Quelle (relativ zum Plugin) | Ziel | Status | Grund / Diff |
|---|---|---|---|
| `scripts/setup/errors.py`, `clone.py`, `gitinfo.py`, `scratch.py`, `validate.py` | `skills/setup/scripts/` | identisch | Hashgleichheit (`test_unchanged_runtime_modules_are_identical_to_the_source`) |
| `scripts/setup/schema.py` | — | nicht übernommen | byte-gleich zur gemeinsamen Variante; setup importiert `site_common.schema` (Test: kein weiteres `schema.py`) |
| `scripts/setup/ownership.py` | `skills/setup/scripts/ownership.py` | angepasst | nur Docstring-Pfad der Schemakopie (`website.schema.json`); Rückwärtsersetzung ergibt Quellhash |
| `scripts/setup/manifest.py` | `skills/setup/scripts/manifest.py` | angepasst (getrennt von der gemeinsamen Variante) | (1) Importe: `from errors import Stop` bleibt flach, Validator `from site_common import schema`; (2) `SPECS/FILE/SCHEMA/PLUGIN_SCHEMA` aus `site_common.manifest`, Meldung „run /zyris-website:setup“ → „run the `setup` skill of the Website plugin“; (3) neu `legacy_problem` (Re-Export), `effective_ports`, `next_port` (D-16); Logik von `files`, `load`, `plugin_schema`, `project_schema_copy`, `problems` unverändert |
| `scripts/setup/site_setup.py` | `skills/setup/scripts/site_setup.py` | angepasst | Docstring; `sys.path` um `../../_shared/scripts` ergänzt; Argumente, Ausgabe und Exit-Codes unverändert |
| `scripts/setup/static_setup.py` | `skills/setup/scripts/static_setup.py` | angepasst | (1) `PLUGIN_ROOT/RES` → `SKILL_DIR`, `RES = skills/setup/templates`; (2) Import des gemeinsamen Validators statt `schema`; (3) `load_schema_bytes` liest `manifest.PLUGIN_SCHEMA` und stoppt bei fehlender Datei (B-1); (4) Planreihenfolge: Manifest laden und Altformat prüfen **vor** dem Planen der Schemakopie (D-18); (5) automatischer Port über `manifest.next_port` (D-16), Kollisionsprüfung gegen effektive Ports (B-2); (6) Konfliktmeldung nennt den Schemapfad im Plugin; (7) `verify`: Altformatprüfung vor der Manifestprüfung. Restliche Logik (Planer, Schreiben, Rollback, Build, Ergebnisse) unverändert |
| `templates/setup/astro-static/**` (außer unten), `types.json`, `_manifest/component-static.json.tpl` | `skills/setup/templates/…` | identisch | Hashgleichheit gegen das Inventar (`test_every_inventoried_setup_template_is_identical_adapted_or_deliberately_moved`); `og-default.png` binär identisch |
| `templates/setup/astro-static/CLAUDE.md.tpl` | `skills/setup/templates/astro-static/CLAUDE.md.tpl` | angepasst | zwei Verweise `/zyris-website:preview|optimize` → „the `preview|optimize` skill of the Website plugin“ (Q4/T-08); Registry-Pfad `.project/specs/zyris-website.json` bleibt (Datenformat) |
| `templates/setup/astro-static/rules/seo.md` | `skills/setup/templates/astro-static/rules/seo.md` | angepasst | ein Verweis `/zyris-website:optimize` → „the `optimize` skill of the Website plugin“ |
| `templates/setup/_manifest/static/zyris-website.json.tpl` | `skills/setup/templates/_manifest/static/zyris-website.json.tpl` | angepasst | `$schema` → `./website.schema.json` (D-17); Dateiname der Vorlage bleibt (Name des Manifests) |
| `templates/setup/_manifest/root/zyris-website.schema.json` | `skills/_shared/resources/website.schema.json` | verschoben und umbenannt | siehe A |
| `skills/setup/SKILL.md` | `skills/setup/SKILL.md` | angepasst | neu geschrieben aus Quelltext und Scope: Namen, Pfade (`${CLAUDE_SKILL_DIR}` für Claude, Pfad der geladenen `SKILL.md` für Codex), `allowed-tools` aus dem Aufrufmuster, Statusabsatz ohne Verträge/Testzeile (T-06), Manifestfelder, Altformat, bestätigter Kommunikationsblock textgleich |
| `contracts/setup.md` | — | nicht als Datei übernommen | Vertragsinhalt fließt über `SCOPE.md` R8/R9 und den Skilltext ein (Q7); Plan §3.2 |
| `tests/setup/test_clone.py` | `tests/unit/setup/test_clone.py` | angepasst | nur Importe |
| `tests/setup/test_validate.py` | `tests/unit/setup/test_validate.py` | angepasst | Importe; echte Domänennamen durch fiktive ersetzt |
| `tests/setup/test_schema.py` | `tests/unit/setup/test_schema.py` | angepasst | Schemapfad, Import `site_common.schema`; ergänzt: Verdiktvergleich setup ↔ gemeinsam, Portfunktionen, `legacy_problem` |
| `tests/setup/test_static_create.py`, `test_static_adopt.py`, `test_review_fixes.py` | `tests/integration/setup/…` | angepasst | Importe, Skriptpfade, Schemaname; in `test_static_adopt` der echte-`npm`-Test durch Fake-Runner ersetzt, der echte nach `test_real_npm.py` verschoben; der Test gegen das echte Websiteprojekt durch einen Test auf einem von setup erzeugten fiktiven Projekt ersetzt |
| `tests/setup/test_real_npm.py` | `tests/external/setup/test_real_npm.py` | übernommen, im Standardlauf ausgeschlossen | `ZW_REAL_NPM=1`; NOT RUN |
| `tests/setup/test_entrypoints.py` | `tests/integration/setup/test_entrypoints.py` | angepasst (Teil) | setup-Skript und gemeinsamer Resolver `which_site.py`; Teile für `preview.py` zurückgestellt (Etappe 3), `optimize/which_site.py` → gemeinsamer Pfad |
| `tests/setup/test_manifest_contract.py` + `tests/shared/{manifest_contract,contract_cases}.py` | `tests/integration/setup/test_manifest_contract.py`, `tests/support/{manifest_contract,contract_cases}.py` | angepasst | Pfade, Schemaname, Skriptpfad; Vertragsfälle unverändert |
| `tests/setup/helpers.py`, `static_helpers.py` | `tests/support/setup_paths.py`, `setup_helpers.py` | angepasst | Pfade; `PROJECT_ROOT` (echte Website) entfernt |
| `tests/setup/fixtures/schema-foreign-older.json` | `tests/fixtures/setup/schema-foreign-older.json` | identisch | zweite Kopie neben `tests/fixtures/shared/` (Etappe 1); Test-Fixture, keine Plugin-Nutzlast |
| `tests/setup/test_validator_copies.py` | — | ersetzt | Verdiktvergleich in `tests/unit/setup/test_schema.py::SetupAndSharedValidatorTests`; Gleichheit der Schemakopien entfällt (genau eine) |
| (neu) | `tests/integration/setup/test_init_ports_legacy.py`, `tests/contracts/test_setup_contract.py` | neu | Etappe-2-Anforderungen (Feldbelegung, Ports, Altformat, Schemakopie-Zustände, isolierte Kopie, Template-Identität, Skilltext) |
| `skills/website-manager/` (Ziel-Skeleton) | — | entfernt | enthielt nur die bekannte `SKILL.md` mit Skeleton-Marker; kein Alias |

## C. Weitere Änderungen

`docs/documentation.json` (`source_skill` → `skills/setup`), `docs/migration/host-conventions.md` (Korrektur „nicht dokumentiert ≠ keine Wirkung“, Abschnitt 8 Gegenlesen), `SCOPE.md`, `AGENTS.md`, `docs/migration/{decisions,plan,setup-init}.md`. Marketplace und Quelle unverändert.

## D. Korrekturen nach unabhängigem Review von Etappe 2

| Befund | Änderung |
|---|---|
| Geerbtes `ZW_REAL_NPM=1` aktivierte die echten npm-Tests im Standardlauf | `tests/integration/setup/test_real_npm.py` → `tests/external/setup/test_real_npm.py` (außerhalb der Standardschichten); Freischaltung nur durch das Modulflag `tests.external.ENABLED`, gesetzt von `scripts/run_external_tests.py --approved`; Variable `ZW_REAL_NPM` entfällt; neuer Regressionstest `tests/contracts/test_external_separation.py` (mit vergiftetem Environment: nichts gesammelt, alles übersprungen, kein Prozess gestartet, Runner ohne `--approved` = NOT RUN); `tests/README.md` trennt beide Wege |
| Altformat-Verweis ohne `./` nicht erkannt | `site_common.manifest.is_legacy_reference` (Textnormalisierung, nur lokale Schreibweisen); `legacy_problem` nutzt es; Regressionen in `FormerFormatTests` (alle Schreibweisen × neue Kopie vorhanden/fehlt × create/adopt/plan/verify/Resolver, Dateien unverändert, Nicht-Treffer, korrektes Format, Altlast neben neuer Kopie) |
| Referenz fehlte, aktive Verweise auf `contracts/setup.md` | neu `skills/setup/references/setup.md`; `SKILL.md` mit Abschnitt „Read first“ (Referenz und `../_shared/references/interfaces.md`); Verweise in `ownership.py`, `static_setup.py` (Docstrings) und `site_setup.py` (Meldungen der nicht verfügbaren Funktionen) ersetzt (`ownership.py` steht weiter in der Rückwärtsersetzungsliste des Vertragstests) |
| `--path` in der Manifestbeschreibung | `<sites folder>/<domain>`; `--path` = Sites-Ordner |
| `.tmp` als einziger Speicherort | `.tmp/` ist der Scratch-Ordner von `setup`; Preview-Zustand und Edit-Sicherungen liegen außerhalb des Repositories |


# Etappe 3: preview

Quellabgleich zu Beginn von Etappe 3 mit `python3 -B scripts/migration_baseline.py --inventory docs/migration/source-inventory.json --root <www.draftmode> --strict-git`: `files=130 changed=0 missing=0 unreadable=0 unsafe=0 new=0 new_symlinks=0 -> NO DRIFT`. Historische Inventare unverändert. Referenzabgleich (`reference-baseline.json`): Manager `ai.plugins` ohne Änderung der inventarisierten Regeln; **fremde, uncommittete Arbeit** im Coach-Checkout (`SCOPE.md`, `docs/architecture.md`, `tests/README.md` weichen vom Inventar ab, Coach wird dort auf fünf Skills mit `skills/_shared/` umgebaut). Gelesen, nicht bearbeitet; für `preview` ohne Folge (kein Vorbild für Prozesssteuerung; bestätigt das Muster gemeinsamer Ordner `skills/_shared/`).

## A. preview: Zuordnung Quelle → Ziel

| Quelle (relativ zum Plugin) | Ziel | Status | Grund / Diff |
|---|---|---|---|
| `scripts/preview/{errors,manifest,schema,sites}.py` | — (`skills/_shared/scripts/site_common/…`) | nicht dupliziert | Etappe 1 (V3); das Skript importiert `site_common`; Test: kein weiteres `errors/manifest/schema/sites.py` im Skill |
| `scripts/preview/control.py` | `skills/preview/scripts/control.py` | angepasst | (1) Docstring (Skillname, `inspect`, `page-confirmed`); (2) `sys.path`: eigener Ordner plus `../../_shared/scripts`; (3) `import sites`/`from errors import` → `from site_common import sites`/`from site_common.errors import`; (4) **Schutzkorrektur BD-6:** neue lesende Prüfung `check_state_area` (lstat, legt nichts an) vor jedem Zugriff auf Records/Logs in `read_record`, `check_target` (damit `write_record`), `_unlink_if_same`, `remove_own`, `own_log_path`, `log_tail`. Sonst Logik, Zustände, Exit-Codes, Zustandsnamen (`zyris-website`, `ZYRIS_WEBSITE_STATE_DIR`) unverändert (Q5) |
| `scripts/preview/preview.py` | `skills/preview/scripts/preview.py` | angepasst | (1) Docstring (Claude-Artefakt `.claude/launch.json`); (2) `sys.path`/Importe wie oben; (3) `RES = skills/preview/templates` statt `<Plugin>/templates/preview`; (4) **Schutzkorrektur BD-5:** `write_launch` prüft `.claude` und `launch.json` per `lstat` (Symlink, auch defekt, und nicht unterstützte Dateitypen → `STOP` mit Diagnose), liest mit `O_NOFOLLOW` und schreibt mit `O_NOFOLLOW` statt `Path.read_text/write_text`. Launch-Name `zyris-<site>` unverändert; unabhängige Einträge bleiben, ein identischer eigener Eintrag wird nicht geschrieben |
| `templates/preview/launch/astro-static.json.tpl` | `skills/preview/templates/launch/astro-static.json.tpl` | identisch | Hashgleichheit (`autoPort: false` unverändert) |
| `skills/preview/SKILL.md` | `skills/preview/SKILL.md` | angepasst (neu geschrieben) | Namen; Pfadbasis `${CLAUDE_SKILL_DIR}` (Claude) / Pfad der geladenen `SKILL.md` (Codex) getrennt; `allowed-tools` = die zwei Aufrufmuster; Claude-Werkzeugnamen und Host-Start entfernt, Browserregeln hostneutral; `needs-install` ohne Installation; Statuszeile/Testzeile/Vertragsverweis entfernt; Abschnitt „Read first“; Kommunikationsblock textgleich zu `setup` |
| `contracts/preview.md` | `skills/preview/references/preview.md` | angepasst (Teilübernahme, neu gefasst) | übernommen: §1, §5.1 (nur Ownership-Begriffe), §6 Zustände, §11.1 (Controller), §12 (`inspect`), §13 (Zuständigkeit, Launch-Eintrag). **Nicht übernommen:** Host-Tool-Modell (§4, §5.2 mit `preview_*`, §11.2), geplante Teile, Abweichungsliste D1–D6, Akzeptanzmatrix und alle „passed“-/Beobachtungsaussagen (§2.2 Evidenz, §10, §11.3, §11.4 Ladetest, E2E), Datum-/GUI-Beobachtungen |
| `contracts/interfaces.md`, `communication.md` (preview-relevant) | `skills/_shared/references/` | bereits Etappe 1 | verlinkt aus `SKILL.md` |
| `tests/preview/test_control.py` | `tests/integration/preview/test_control.py` + Basis in `tests/support/preview_process.py` | angepasst | Importe; fiktive Namen (`alpha.example`, `beta.example`); Basisklasse/Fake-npm in `support` ausgelagert (vorher Querimport zwischen Testdateien). Assertions unverändert (52 Tests) |
| `tests/preview/test_inspect.py` | `tests/integration/preview/test_inspect.py` | angepasst | nur Importe (20 Tests); lokale HTTP-Server auf 127.0.0.1 |
| `tests/preview/test_preview.py` | `tests/unit/preview/test_launch.py` | angepasst | Importe, fiktive Namen (15 Tests); Launch-Konfiguration |
| `tests/preview/test_manifest_contract.py` | `tests/integration/preview/test_manifest_contract.py` | angepasst | Pfade, Schemaname; zusätzlich Einträge `status`, `stop`, `inspect` |
| `tests/preview/test_sites.py` | — (`tests/unit/shared/test_sites.py`) | bereits Etappe 1 | Resolver-Tests liegen gemeinsam vor |
| `tests/preview/helpers.py`, `fixtures/zyris-website.schema.json` | `tests/support/preview_helpers.py` | ersetzt | fiktive Fixtures; die Projektkopie des Schemas stammt aus der einen Plugin-Datei |
| (neu) | `tests/integration/preview/test_former_format.py`, `test_side_effects_and_copy.py`, `test_state_area_and_launch_links.py`, `tests/unit/preview/test_launch_links.py`, `tests/contracts/test_preview_contract.py` | neu | Altformat vor Seiteneffekten; `status`/`stop`/`inspect`/`needs-install` ohne Prozess-, Konfigurations- oder Zustandsänderung; isolierte Plugin-Kopie (Leerzeichen, anderes Arbeitsverzeichnis, kein `PYTHONPATH`, Decoys, Template/Schema aus der Kopie, Kopie unverändert); Identität gegen Inventar, Aufrufmuster ↔ `allowed-tools`, Textgleichheit des Kommunikationsblocks |

## B. Bestandsdefekte und Beobachtungen (nicht still geändert)

- **BD-1** (Bestand, nicht behoben): Der Quellvertrag ist in sich widersprüchlich (§2–§10 beschreiben das frühere Host-Tool-Modell als Ziel); die Referenz übernimmt nur die als implementiert markierten Teile (V1).
- **BD-2** (Beobachtung): `cmd_start` legt Zustandsverzeichnis an, bevor das Launch-Template gelesen wird; fehlt das Template, bleibt ein leeres Zustandsverzeichnis, aber kein Record, Log, Launch-Eintrag oder Prozess (Test `test_missing_template_in_the_copy_...`). Kein Eingriff.
- **BD-5** (Bestandsdefekt, **behoben**): `write_launch` der Quelle folgte Symlinks (`.claude` als Verzeichnis-Link, `launch.json` als Datei-Link, defekter Link) beim Lesen und Schreiben und endete bei einem Verzeichnis oder Spezialtyp als `launch.json` im Traceback. Korrigiert in `skills/preview/scripts/preview.py` (`_checked_launch_file`, `write_launch`); greift beim Generatoraufruf und über `control.py start`, bevor ein Dev-Server startet. Tests: `tests/unit/preview/test_launch_links.py`, `tests/integration/preview/test_state_area_and_launch_links.py` (Zugriffsspy: Inhalte hinter dem Link werden nicht geöffnet, geändert oder entfernt; Hash allein reicht nicht als Beleg).
- **BD-6** (Bestandsdefekt, **behoben**): Die Quelle prüfte nur die letzte Pfadkomponente einer Zustandsdatei (`O_NOFOLLOW`); ein Symlink im Basis- oder Projekt-Zustandsverzeichnis wurde verfolgt, sodass `status`/`stop`/`inspect` und das Aufräumen Records und Logs außerhalb lesen, entfernen und als Besitznachweis (samt Signal an die dort genannte Prozessgruppe) verwenden konnten. Korrigiert in `skills/preview/scripts/control.py` (`check_state_area`). Fehlender Bereich bleibt Normalfall (nichts wird angelegt); unsicherer Bereich: `status`/`stop`/`start` → `unsafe-state` ohne Signal, `inspect` setzt die Seitenprüfung fort (`process: unknown`). Grenze: Vorfahren des Basisverzeichnisses (Systemtemp, z. B. `/var` → `/private/var`) werden nicht geprüft; ein bösartiger Prozess desselben Benutzers bleibt außerhalb des Schutzes. Tests: `tests/integration/preview/test_state_area_and_launch_links.py` (Signale per Spy abgefangen, Bystander-Prozess des Tests, Mutationsprobe: ohne die Prüfung schlagen 15 Teilfälle fehl).
- **BD-3** (Beobachtung): Beim Zusammenspiel mit Python 3.15 melden die Prozesstests `ResourceWarning`-Zeilen (nicht gewartete `Popen`-Objekte der Fake-Dev-Server); keine Testfehler, Aufräumen ist identitätsgeprüft.
- **BD-4** (offen, NOT RUN): Wirkung von `"autoPort": false` in der Claude-Desktop-Anwendung; die Dokumentation beschreibt sie (siehe host-conventions.md Abschnitt 9), beobachtet wurde sie nicht.
- Kein **Migrationsfehler** gefunden: Fehlerklassen (`Stop`/`Ask`), Importe und Ressourcenpfade stimmen mit den gemeinsamen Modulen überein (Tests: Prozessaufruf aus Kopie, Decoys auf `PYTHONPATH`).
