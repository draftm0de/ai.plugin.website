# Migration: Änderungsliste und Übernahmenachweis (Stand Etappe 4)

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


# Etappe 4: optimize

Quellabgleich zu Beginn von Etappe 4 mit `python3 -B scripts/migration_baseline.py --inventory docs/migration/source-inventory.json --root <www.draftmode> --strict-git`: `files=130 changed=0 missing=0 unreadable=0 unsafe=0 new=0 new_symlinks=0 -> NO DRIFT`. Historische Inventare (`source-inventory.json`, `target-baseline.json`, `reference-baseline.json`) sind unverändert (Git-Status des Ziels zeigt keine Änderung an ihnen). Referenzabgleich (`reference-baseline.json`, lesend): **Manager `ai.plugins`** hat uncommittete Änderungen (neuer lokaler MCP-Einstieg für verify/update, `WORKFLOWS.md`, `verify.py` mit Parameter `include_local`); für `optimize` ohne Folge (kein Bezug zu Audit, Berichten oder Aufrufmustern), nicht bearbeitet. **Strukturreferenz Coach** (`SCOPE.md`, `docs/architecture.md`, `tests/README.md` uncommittet geändert, Coach wird auf fünf Skills mit `skills/_shared/` umgebaut): gelesen, nicht bearbeitet, ohne Folge für diese Etappe. Ein neuer Commit im Ziel ist kein Quelldrift.

## A. optimize: Zuordnung Quelle → Ziel

| Quelle (relativ zum Plugin) | Ziel | Status | Grund / Diff |
|---|---|---|---|
| `scripts/optimize/findings.py` | `skills/optimize/scripts/findings.py` | identisch | Hashgleichheit (`fe0f4b41…`); Adapter für die Ausgabe der Site-Prüfskripte, keine lokalen Importe |
| `scripts/optimize/{errors,manifest,schema,sites}.py` | — (`skills/_shared/scripts/site_common/…`) | nicht dupliziert | Etappe 1 (V3); der Skill importiert `site_common`; Test: kein weiteres `errors/manifest/schema/sites.py` im Skill |
| `scripts/optimize/which_site.py` | — (`skills/_shared/scripts/which_site.py`) | nicht dupliziert | Etappe 1; der Skilltext ruft den gemeinsamen Resolver |
| `scripts/optimize/audit.py` | `skills/optimize/scripts/audit.py` | angepasst | Migration: (1) Docstring (Skillname statt `/zyris-website:optimize`); (2) `sys.path`: eigener Ordner plus `../../_shared/scripts`; (3) `import sites`/`from errors import` → `from site_common import sites`/`from site_common.errors import`. Schutzkorrekturen BD-7 bis BD-11 (Abschnitt B). Sonst Logik, Zustände, Exit-Codes, CLI (`audit|propose|decide|apply|show` und Optionen) und Berichtstext unverändert |
| `scripts/optimize/store.py` | `skills/optimize/scripts/store.py` | angepasst | Migration: `from errors import Stop` → `from site_common.errors import Stop`. Schutzkorrektur BD-10 (unlesbare Arbeitsliste) |
| `scripts/optimize/worklist.py` | `skills/optimize/scripts/worklist.py` | angepasst | **nur** der Import `from site_common.errors import Stop`. Der erzeugte Text der Arbeitsliste (einschließlich eines Satzes, der noch den früheren Skillaufruf `/zyris-website:optimize` nennt) und die Formatmarker `zyris-optimize:*` bleiben **unverändert**, weil `parse` den gespeicherten Text mit dem neu erzeugten vergleicht (R21): jede Textänderung ließe vorhandene Arbeitslisten als „von Hand geändert“ gelten. Test: genau ein Hunk |
| `skills/optimize/SKILL.md` | `skills/optimize/SKILL.md` | angepasst (neu geschrieben) | Namen (Q4); Pfadbasis `${CLAUDE_SKILL_DIR}` (Claude) / Pfad der geladenen `SKILL.md` (Codex) getrennt; `allowed-tools` = vier Muster aus den Aufrufmustern (zwei Aufrufe, zwei `test -f`); T-01 (Satz zu `edit`/„Open“-Liste) und T-10 (Abhängigkeitstext) berichtigt: nichts wird installiert, nicht einmal bei `apply`; Status/Testzeile/Vertragsverweis entfernt; Abschnitt „draftmode.io“ (Bezug auf die echte Site der Quellentwicklung) nicht übernommen; Abschnitt „Read first“; Kommunikationsblock textgleich zu `setup`/`preview` |
| `contracts/optimize.md` | `skills/optimize/references/optimize.md` | angepasst (Teilübernahme, neu gefasst) | übernommen: §1, §2 (Modi, Freigabe), §4, §5 (ohne Kopie/`npm ci`), §6 (Klassen, Katalog, manuelle Punkte, Erfindungsverbot), §8, §9, §10, §12. **Nicht übernommen:** §3 (Evidenz/Abweichungstabelle), §7 GEO, §6.2-Zeilen „[PLANNED]“, Lighthouse, Linkgraph, isolierte Kopie, §11 Akzeptanzmatrix mit Testnamen und alle Aussagen über bestandene Läufe (`HANDOVER`, 20 Seiten), Aussagen zur echten Site `draftmode.io`. Ergänzt: Abschnitt „Not available“, Hinweis, dass der Treiber die Regeldateien der Site nicht selbst prüft (BD-12) |
| `contracts/interfaces.md`, `communication.md` (optimize-relevant) | `skills/_shared/references/` | bereits Etappe 1 | verlinkt aus `SKILL.md` |
| `tests/optimize/audit_helpers.py`, `helpers.py` | `tests/support/optimize_helpers.py` | angepasst | Pfade; Schema-Fixture entfällt (die eine Plugin-Datei); Projektschema heißt `website.schema.json`; fiktive Namen; Fake-`npm` protokolliert auch abgelehnte Aufrufe |
| `tests/optimize/test_findings.py` | `tests/unit/optimize/test_findings.py` | angepasst | Assertions unverändert; reale Seitennamen des Beispiels durch fiktive ersetzt; ergänzt (Klassen getrennt, leerer/undekodierbarer Text, `source_files`). **Ersetzt:** `test_catalog_matches_site_scripts_when_present` las die Prüfskripte der **echten Site** (`sites/draftmode.io/scripts`) und wurde bei Fehlen übersprungen → `test_findings_templates.py` |
| (neu) | `tests/unit/optimize/test_findings_templates.py` | neu | liest die **ausgelieferten setup-Templates** `seo-check.mjs`/`a11y-check.mjs` als Text (kein Node, keine Ausführung), leitet die Meldungsformate ab und prüft Adapter und Konsolenformate dagegen; zeigt Passung zu den Templates, **nicht** Gleichheit mit den Skripten einer echten Website |
| `tests/optimize/test_audit.py` | `tests/integration/optimize/test_audit.py` | angepasst | nur Importe/Hilfen; Assertions unverändert |
| `tests/optimize/test_store.py` | `tests/integration/optimize/test_store.py` | angepasst | nur Importe/Hilfen; Assertions unverändert |
| `tests/optimize/test_manifest_contract.py` | `tests/integration/optimize/test_manifest_contract.py` | angepasst | Pfade, Schemaname; zusätzlich `propose` und der gemeinsame Resolver als Einträge; unbekannte/mehrdeutige Site |
| `tests/optimize/test_sites.py`, `test_which_site.py` | — (`tests/unit/shared/test_sites.py`, `tests/integration/shared/test_which_site_entry.py`) | bereits Etappe 1 | |
| `tests/optimize/fixtures/zyris-website.schema.json` | — | nicht übernommen | Kopie der einen Plugin-Schemadatei (Etappe 1) |
| (neu) | `tests/integration/optimize/{test_apply_scope,test_report_and_guard,test_former_format,test_isolated_copy}.py`, `tests/contracts/test_optimize_contract.py` | neu | Freigabe/`apply`-Grenzen, Schreibschutz und Wächter, Ergebniszustände, Klassen, manuelle Punkte, `show`, beschädigte Arbeitslisten, Altformat vor Seiteneffekten, isolierte Kopie, Identität gegen Inventar, Aufrufmuster ↔ `allowed-tools`, Kommunikationsblock |
| `tools/test_package_plugin.py` (O17, ZIP) | — | nicht übernommen | ZIP-Weg entfällt (T-05) |

## B. Schutz- und Fehlerbehandlungskorrekturen (Bestandsdefekte der Quelle, nicht Migrationsfehler)

Alle fünf sind **belegt** (Charakterisierungsläufe vor der Korrektur, danach Regressionstests; ohne die Korrektur schlagen die Tests fehl) und **klein**: sie ändern weder Zustände, CLI, Berichtsformat noch Entscheidungslogik. Sie sind die einzigen Abweichungen von `audit.py`/`store.py` der Quelle jenseits der Migration (Vertragstest: umkehrbare Hunk-Liste `PROTECTION`; Reversion beider Listen ergibt die Quell-Hashes). Der Reviewer kann sie getrennt ablehnen.

| ID | Auslöser | Scope-Bezug | Korrektur | Tests |
|---|---|---|---|---|
| BD-7 | `apply` las und schrieb den Zieltext im Textmodus; eine freigegebene Änderung in einer CRLF-Datei machte daraus eine LF-Datei, die **gesamte Datei** änderte sich; der Bericht-Diff verbarg das, weil auch der Ausgangstext normalisiert war | R13 „nur die freigegebene Änderung“, `interfaces.md` Regel 6 | `_read_exact` liest Bytes (UTF-8), Schreiben und Rückstellen schreiben Bytes; Zeilenenden bleiben byte-gleich | `test_apply_scope.EditTarget.test_bd7_…` |
| BD-8 | `apply` auf eine versionierte Datei, die kein UTF-8 ist: `UnicodeDecodeError` als Traceback, kein `STOP:` (nichts geändert) | R7 (`STOP:`), R13 | `_read_exact` meldet `STOP: edit file … cannot be read as UTF-8 text` vor jedem Schreiben | `…test_bd8_…` |
| BD-9 | Schlägt `os.replace` in `apply` fehl, blieb die private Temp-Datei `.optimize-apply-*` im versionierten Siteordner liegen (die erste Datei wurde korrekt zurückgestellt) | R13 (keine Änderung außerhalb des Umfangs), R12 | Temp-Datei wird bei Fehler entfernt | `…test_bd9_…` (zweiter Austausch schlägt fehl; alle Dateien zurück, kein Rest) |
| BD-10 | Arbeitsliste, die kein UTF-8 ist: `UnicodeDecodeError` als Traceback statt kontrollierter Stopp (der Lauf endete zwar vor dem Build) | R12 „beschädigte Arbeitsliste stoppt vor dem Bauen“, R7 | `store.read_worklist` meldet `STOP:` mit Anleitung; Datei unverändert | `test_report_and_guard.DamagedWorklistStopsEveryCommandBeforeBuilding` (vier Schadensarten × vier Befehle) |
| BD-11 | Dateisystemfehler (z. B. nicht beschreibbarer Berichtsordner, `PermissionError`) endeten nach dem Build als Traceback ohne `STOP:` | R7, R12 „Schreibfehler kontrolliert“ | `main` fängt `OSError` und meldet `STOP: a file operation failed (…). Nothing is reported as done…`; Exit 1 | `…test_bd11_…` |

## B2. Korrekturauftrag nach unabhängigem Review (zwei weitere Bestandsdefekte)

Beide Defekte bestehen schon in der Quelle, sind belegt (Regressionstests schlagen ohne die Korrektur fehl: Mutationsprobe, 10 Fehlschläge und 2 Fehler) und begrenzt korrigiert; Hunk-Liste `PROTECTION` im Vertragstest. Berichts-/Arbeitslistenformate, Marker, Versionen und der historische Aufruftext sind unberührt; `website.schema.json` bleibt der Schemaname.

| ID | Auslöser | Scope-Bezug | Korrektur | Tests |
|---|---|---|---|---|
| BD-15 | `do_apply` prüfte die Eindeutigkeit jedes Suchtexts im Original, ersetzte aber nacheinander im bereits veränderten Text: Original `Alpha Beta`, Edit 1 `Alpha→Beta`, Edit 2 `Beta→Gamma` ergab `Gamma Beta` statt `Beta Gamma`. Überlappende Edits und doppelt genannte IDs wurden nicht erkannt | R13 „nur die freigegebene Änderung“, genau einmal | Alle Ersetzungsbereiche werden im Originalinhalt bestimmt und von hinten eingesetzt; Überlappung oder Widerspruch (auch derselbe Bereich zweimal) → `STOP` vor dem ersten Schreiben, auch dateiübergreifend; leerer Suchtext → `STOP`; doppelte IDs werden einmal angewendet; Zeilenenden bleiben (BD-7) | `test_apply_scope.EditsBindToTheOriginal` (Alpha/Beta in beiden ID-Reihenfolgen, mehrere unabhängige Edits in einer und mehreren Dateien, angrenzende Bereiche, erzeugter Text gleich späterem Suchtext, Überlappung, zweite Datei überlappt, gleicher Bereich, leerer Suchtext, wiederholte ID; bei Ablehnung: Dateien unverändert, kein Build, kein Bericht, kein Erfolg) |
| BD-16 | `source_state` nutzte `path.is_file()`/`read_bytes()` für versionierte Pfade und folgte Symlinks, auch aus dem Projekt hinaus (Lesen fremder Dateien; Linkaustausch bei gleichem Zielinhalt unsichtbar; Pfad unter ausgetauschtem Elternlink wurde gefolgt) | R12 Wächter, `interfaces.md` Regeln 4/6 (nichts außerhalb des gewählten Projekts) | `_entry_state`: `lstat` je Pfadkomponente, Link als `LINK:<Text>` ohne Zielzugriff, reguläre Datei per `O_NOFOLLOW`; Elternlink → `STOP` mit Diagnose (vor dem Build bzw. nach dem Lauf ohne Bericht), nichts aufgelöst oder repariert; Ablehnung von Links als `apply`-Ziel unverändert | `test_source_state_links` (Link auf externe Datei, hängender Link, Linktext-Änderung bei gleichem Zielinhalt, Austausch während des Laufs → `readonly-violated`, Ordner-Link, Elternlink vorher und währenddessen, CLI-`STOP`; Beleg des Nicht-Öffnens durch Access-Spy auf `os.open`, `open`, `io.open`, `os.stat` **und** Zugriffssperre Modus 000; ein unveränderter Hash genügt nicht) |

## B3. Korrekturauftrag BD-17 (Arbeitsliste bytegetreu lesen und schreiben)

Bestandsdefekt der Quelle, belegt (ohne die Korrektur schlagen 3 der neuen Tests fehl: Mutationsprobe). **Auslöser:** ein Vorschlag mit Wagenrücklauf im `find`/`replace` (mehrzeiliger Text einer CRLF-Datei). Der unveränderte Renderer schreibt das `\r` in den sichtbaren Text (`_code` ersetzt nur `\n` durch ein Leerzeichen) und in die Prüfsumme; `store.read_worklist` las mit `Path.read_text` (universelle Zeilenumwandlung: `\r` → `\n`), `render(state) != text` lieferte „von Hand geändert“, und alle Befehle stoppten. **Scope-Bezug:** R12 (eigene Arbeitsliste darf nicht als handverändert gelten), R13 (`apply` einer freigegebenen Änderung), R21 (Format unverändert).

**Korrektur** (`store.py`, zwei Stellen, Hunk-Liste `PROTECTION`): `read_worklist` liest Bytes und dekodiert strikt als UTF-8 (keine Zeilenumwandlung); `_private_tmp` schreibt Bytes (`"wb"`, `encode("utf-8")`), damit der gespeicherte Text bytegleich dem gerenderten ist (auch auf Plattformen mit Zeilenumwandlung im Textmodus; Berichte nutzen dieselbe Funktion, ihr Inhalt ist unverändert).

**Warum das gespeicherte Format unverändert bleibt:** Renderer (`worklist.py`, byte-gleich bis auf den Import), JSON-Block, Marker, Format/Version, SHA-256-Verfahren und der historische Aufruftext sind nicht angefasst. Auf POSIX sind die Bytes, die der bisherige Code schrieb, identisch mit denen des neuen (Test: vom Renderer erzeugte Liste mit Wagenrückläufen wird unverändert gelesen und nicht umgeschrieben). Es gibt keine Normalisierung vorhandener Dateien, keine Reparatur, Migration oder tolerante Ersatzprüfung. **Folge, bewusst:** eine Arbeitsliste, deren Zeilenenden von Hand oder durch ein Werkzeug (z. B. `autocrlf`) insgesamt umgewandelt wurden, gilt jetzt als geändert und stoppt (vorher wurde sie durch die Normalisierung zufällig akzeptiert); Wiederherstellung aus Git, wie für jede Handänderung.

**Tests** (`tests/integration/optimize/test_worklist_bytes.py`, 11): mehrzeiliger CRLF-Such- und Ersatztext durch audit → erneutes Lesen/`show` → `decide` → `apply` → Nachprüfung und weiteren Audit, exakt die freigegebenen Bytes geändert, übrige Bytes und Zeilenenden erhalten; wiederholtes Lesen stabil und nicht umgeschrieben; vom Renderer erzeugte Liste mit `\r` unverändert gelesen; LF-Liste unverändert funktionsfähig; bytegetreues Schreiben; abgelehnt und nicht überschrieben bleiben: echte Handänderung, Änderung nur eines `\r`, beschädigte Prüfsumme, insgesamt umgewandelte Zeilenenden, kein UTF-8, abgeschnittene Datei (je audit, show, decide, apply: `STOP:`, kein Traceback, kein Build).

## C. Bestandsbeobachtungen (nicht geändert)

- **BD-12** (Dokument/Code): Vertrag §4 sagt, der Audit stoppe, wenn `seo.md`/`accessibility.md` in `rule_files` fehlen. Der Treiber `audit.py` prüft das **nicht**; nur der Skilltext (Schritt 1, `which_site.py`) verlangt den Stopp. Ein direkter Aufruf von `audit.py` ohne den Resolverschritt läuft auch ohne Regeldateien. Die Referenz benennt das ausdrücklich; kein Eingriff (R12 verlangt die Prüfung nicht im Treiber).
- **BD-13** (Beobachtung): Der erzeugte Text der Arbeitsliste nennt noch `/zyris-website:optimize` (siehe Abschnitt A, `worklist.py`); aus Formatgründen unverändert. Die Referenz sagt es.
- **BD-14** (Beobachtung): `decide`/`apply`/`propose` legen über die Sperre den Ordner `.project/reports/<site>/` an, auch wenn danach „no work list yet“ gemeldet wird (leerer Ordner im Berichtsbereich; kein Site-Inhalt). Kein Eingriff.
- **BD-17** ist keine Beobachtung mehr, sondern in Abschnitt B3 begrenzt korrigiert.
- Die Prüfung der Voraussetzungen (`node_modules`, Lockfile, ignorierte Ausgabeordner, Node ≥ 22.23.4) wurde gegen Fakes, nicht gegen echtes Node/npm geprüft; die Node-Version wird nur ohne `--npm` über das echte `node --version` bestimmt (nicht getestet: NOT RUN).

## D. Aufrufmuster und Hostbehauptungen

Gemeinsam aus den neuen Pfaden abgeleitet (Konvention `host-conventions.md` §4/§5): `python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py" *`, `python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" *` und je ein `test -f`; keine pauschale Python-/Shellfreigabe. **Neu gegenüber `setup`/`preview`:** das Muster enthält `..` (Zugriff auf `skills/_shared/`); ob Claude eine Bash-Regel mit `..`, Anführungszeichen und Leerzeichen im expandierten Pfad deckt, ist **nicht dokumentiert** (host-conventions.md §3) und bleibt NOT RUN; ohne Deckung fragt Claude die Person. Codex: keine Vorabfreigabe behauptet. Ob beide Hosts `skills/_shared/` mitinstallieren, bleibt NOT RUN (R3/R24). Dokumentationsrecherche in dieser Etappe: keine neue (die Aussagen aus `host-conventions.md` §2–§8 gelten unverändert; kein Hosttest).

## D2. Geänderte Dateien früherer Etappen (nur Erweiterung)

| Datei | Änderung |
|---|---|
| `tests/contracts/test_setup_contract.py` | die exakte Dateimenge, in der der alte Schemaname (zur dokumentierten Ablehnung) vorkommen darf, enthält zusätzlich `skills/optimize/SKILL.md` und `skills/optimize/references/optimize.md` |
| `SCOPE.md`, `docs/migration/{plan,decisions,host-conventions}.md` | Etappe-4-Fortschreibung (Evidenzstatus R1, R3–R7, R12, R13, R17, R19, R21, R24; Hostmatrix; Entscheidungen E4-01 bis E4-07; Aufrufmuster-Konvention §10); keine Scope-Änderung, keine Änderung der Anforderungstexte (Acceptance) |

## E. Bewusst nicht Teil dieser Etappe

GEO, Lighthouse, Linkgraph-Prüfung, isolierte Kopie mit `npm ci`, Installation oder Aktualisierung von Abhängigkeiten, `edit`, `publish`, neue Reparaturklassen, Browserintegration, Deployment. Echte Läufe von `npm run build`, `seo:check`, `a11y:check`, `node` und der Template-Skripte: **NOT RUN** (nur Fakes und Textableitung).
