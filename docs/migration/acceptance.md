# Abnahmematrix und Abschlussnachweis (Etappe 6)

Migrationsnachweis, keine Produktdefinition. Maßgeblich: [SCOPE.md](../../SCOPE.md) (R1–R26 mit Akzeptanzkriterien und Evidenzstatus je Anforderung). Plan: [plan.md](plan.md); Änderungsliste: [changes.md](changes.md); Zuordnung der Quelldateien: [completeness.json](completeness.json).

Stand: 2026-11-19. Etappen 1–5 sind nach unabhängigem Source-Review für die Fortsetzung abgenommen. **Etappe 6 ist umgesetzt: Review ausstehend.** Diese Datei trennt drei Zustände, die nicht ineinander übergehen: lokale Migration, Hostabnahme und Veröffentlichung.

## Lokale Migration

Umgesetzt und lokal geprüft (deterministisch, ohne Netzwerk, ohne Host, ohne echtes npm/Node):

- fünf Skills `setup`, `preview`, `optimize`, `edit`, `publish` mit gemeinsamer Laufzeit `skills/_shared/`;
- Dokumentation Deutsch (Standard) und Englisch, CHANGELOG, Voraussetzungen, `plugin.json` mit aktueller Beschreibung und abgeleitetes Host-Manifest ohne Drift;
- Vollständigkeitszuordnung aller 130 Quelldateien (Abschnitt unten);
- lokaler Marketplace-Eintrag `website` in `ai.plugins` (Abschnitt „Marketplace“).

Das beweist **keine** Produktionsreife und keine Hostunterstützung.

## Hostabnahme

Offen. Für jeden Skill und jeden Host getrennt gilt: Ein Nachweis für Claude gilt nie für Codex und umgekehrt. Die deterministische Prüfung läuft in Python ohne Host und belegt deshalb für keinen Host Verhalten; sie steht in beiden Zeilen eines Skills nur zur Information. Kategorien:

- **Struktur/Text:** Textprüfung von `SKILL.md`, Referenzen und Verträge; kein Verhalten eines Modells.
- **Deterministisch:** Runtime-Prüfung mit Fakes (Fake-`npm`, Fake-`ps`/`lsof`, lokale Fake-Dev-Server auf 127.0.0.1, Wegwerf-Git-Repositories, fiktive Fixtures).
- **Werkzeuge:** echte Werkzeugausführung (`npm`, Node, Astro).
- **Hostlauf:** nativer Lauf im Host (Skill laden, Pfadvariable, `allowed-tools`, Erreichbarkeit von `skills/_shared/`).
- **Modell:** Modellurteil (Passung, fehlende Fakten, mitgelieferte Anweisungen, Routing, Vorschlagsqualität).
- **Sicht:** tatsächliche Sichtprüfung im Browser/GUI.

| Skill | Host | Struktur/Text | Deterministisch | Werkzeuge | Hostlauf | Modell | Sicht |
|---|---|---|---|---|---|---|---|
| setup | Claude | ausgeführt (Skilltext, `${CLAUDE_SKILL_DIR}`/`allowed-tools` nur als Text) | ausgeführt (hostunabhängig, Fake-npm) | NOT RUN (echtes npm install/build/check; `tests/external`) | NOT RUN (Skillladen, `allowed-tools`) | NOT RUN (Operationswahl, Rückfragen) | n/a (kein Sichtanteil) |
| setup | Codex | ausgeführt (Pfad der geladenen SKILL.md als Text, keine Vorabfreigabe behauptet) | ausgeführt (hostunabhängig, kein Codex-Nachweis) | NOT RUN (echtes npm install/build/check) | NOT RUN (Skillpfad, Erreichbarkeit `_shared`) | NOT RUN (Operationswahl, Rückfragen) | n/a (kein Sichtanteil) |
| preview | Claude | ausgeführt (Text; `.claude/launch.json` als Claude-Artefakt gekennzeichnet) | ausgeführt (hostunabhängig, Fake-Dev-Server auf 127.0.0.1, Fake-ps/lsof) | NOT RUN (echtes npm/Astro-Dev-Server) | NOT RUN (Skillladen, `allowed-tools`, Browser-Pane, Wirkung von `autoPort: false`) | NOT RUN (Browserwerkzeug nur auf Controller-Adresse) | NOT RUN (Seite nie in einem Browser geöffnet) |
| preview | Codex | ausgeführt (Pfadregel als Text) | ausgeführt (hostunabhängig, kein Codex-Nachweis) | NOT RUN (echtes npm/Astro-Dev-Server) | NOT RUN (Skillpfad; Browserfähigkeit des Hosts unbelegt) | NOT RUN (Browserwerkzeug, falls vorhanden) | NOT RUN (Seite nie in einem Browser geöffnet) |
| optimize | Claude | ausgeführt (Text; vier `allowed-tools`-Muster inkl. `..` als Text) | ausgeführt (hostunabhängig, Fake-npm, Wegwerf-Git) | NOT RUN (echtes `npm run build`/`seo:check`/`a11y:check`, Node-Versionsprüfung) | NOT RUN (Skillladen, Deckung des Musters mit `..`, `_shared`) | NOT RUN (Vorschlagstexte, keine erfundenen Fakten) | n/a (manuelle Prüfpunkte liegen bei der Person) |
| optimize | Codex | ausgeführt (Pfadregel als Text) | ausgeführt (hostunabhängig, kein Codex-Nachweis) | NOT RUN (echtes `npm run build`/`seo:check`/`a11y:check`) | NOT RUN (Skillpfad, Erreichbarkeit `_shared`) | NOT RUN (Vorschlagstexte, keine erfundenen Fakten) | n/a (manuelle Prüfpunkte liegen bei der Person) |
| edit | Claude | ausgeführt (Text; vier `allowed-tools`-Muster, Nachbarskill `preview` als Text) | ausgeführt (hostunabhängig, Fake-npm, Zugriffsspion) | NOT RUN (echtes `npm run build`/`check`) | NOT RUN (Skillladen, Muster mit `..` zu `preview`, `_shared`) | NOT RUN (Passung, fehlende Fakten, mitgelieferte Anweisungen, optimize-Routing) | NOT RUN (`--visual-done` ist nur die Aussage des Aufrufers; GUI-Fall G1) |
| edit | Codex | ausgeführt (Pfadregel als Text) | ausgeführt (hostunabhängig, kein Codex-Nachweis) | NOT RUN (echtes `npm run build`/`check`) | NOT RUN (Skillpfad, Erreichbarkeit `_shared`/`preview`) | NOT RUN (Passung, fehlende Fakten, mitgelieferte Anweisungen, optimize-Routing) | NOT RUN (Browserfähigkeit des Hosts unbelegt) |
| publish | Claude | ausgeführt (Text- und Strukturprüfung: nur `SKILL.md`, kein Skript) | n/a (keine Runtime) | n/a (keine Werkzeugausführung) | NOT RUN (Skillladen) | NOT RUN (Textprüfung ist kein Modellverhalten) | n/a (kein Sichtanteil) |
| publish | Codex | ausgeführt (Text- und Strukturprüfung: nur `SKILL.md`, kein Skript) | n/a (keine Runtime) | n/a (keine Werkzeugausführung) | NOT RUN (Skillladen) | NOT RUN (Textprüfung ist kein Modellverhalten) | n/a (kein Sichtanteil) |

Weitere Hostpunkte (NOT RUN): ob beide Hosts `skills/_shared/` mitinstallieren; ob ein Claude-Bash-Muster mit `..`, Anführungszeichen und Leerzeichen greift; Browserwerkzeuge je Host; Installation des Plugins über den Marketplace; Update und Entfernen. Quelle der Konventionen: [host-conventions.md](host-conventions.md). Die manuellen Modell-/Hostfälle der Quelle sind in `tests/behavior/edit_cases.md` eingeordnet und nicht ausgeführt.

## Veröffentlichung

Nicht erfolgt und nicht behauptet: kein Commit, Push, Tag, Release, Deployment, keine Installation, keine Netzwerkabfrage. `publish` ist ein Platzhalter. Der lokal angepasste Katalogeintrag beweist weder einen Push noch die Erreichbarkeit des Plugin-Repositories noch einen erfolgreichen Hostimport. Die maschinenlokale Zuordnung des Plugins zu einem Marketplace (`.local/marketplace.json`, ignoriert) wurde in dieser Etappe nicht angelegt, geändert oder von Hand gelesen. `verify` meldete sie vor der Katalogänderung als nicht registriert und meldet nach der Umbenennung auf `website` `local_development: complete` (Strukturprüfung der lokalen Konfiguration; kein Nachweis einer Installation oder eines Hostimports).

## Anforderungsmatrix R1–R26

Kriterium: bestätigt in [SCOPE.md](../../SCOPE.md) (Abschnitt `R<n>`, Akzeptanzkriterium und Evidenzstatus); die `Source:`/`Test:`-Verweise stehen dort und werden nicht dupliziert. Status: **strukturell** = nur Struktur-/Textprüfung oder Dateinachweis; **teilbelegt** = deterministisch belegt, aber Werkzeug-, Host-, Modell- oder Sichtnachweis fehlt; **offen** = kein Nachweis möglich ohne Hostlauf. Kein Status bedeutet Abnahme. „Ausgeführt“ bezieht sich auf die im Abschnitt „Prüfläufe“ genannten Läufe.

| ID | Kriterium (SCOPE) | Source/Test | Ausgeführt | Fehlt | Status | Lücke |
|---|---|---|---|---|---|---|
| R1 | Identität `website`, genau fünf Skills mit `SKILL.md` | SCOPE R1 | Vertragstests aller Skills, Metadatentest | Laden durch einen Host | strukturell | Kein Host hat die Skills geladen (NOT RUN) |
| R2 | Zielhosts Claude und Codex, Nachweis je Host | SCOPE R2, Hostmatrix oben | Test, dass Hostzellen nur `NOT RUN`/`n/a` führen | jeder Hostlauf | offen | Alle Hostnachweise NOT RUN |
| R3 | Eigenständige Runtime, keine Entwicklerpfade | SCOPE R3 | Kopie-Tests je Skill (Leerzeichen, ohne PYTHONPATH, Kopie unverändert) | Erreichbarkeit von `_shared`/`preview` im Host | teilbelegt | Installiertes Layout beider Hosts unbelegt |
| R4 | Aktuelle Formate, keine Aliase, keine Migration | SCOPE R4 | Altformat-Tests je Einstiegspunkt, Alias-Strukturtest | echte Nutzerprojekte | teilbelegt | Nur fiktive Fixtures; Hostverhalten unbelegt |
| R5 | Manifest-Vertrag, Stopp vor Seiteneffekten | SCOPE R5 | Einstiegspunkt-Tests setup/preview/optimize/edit | echter Build mit npm | teilbelegt | Kein echter npm-/Node-Lauf |
| R6 | Standortwahl nie raten | SCOPE R6 | Resolver- und Einstiegstests | Modell hält die Reihenfolge im Chat ein | teilbelegt | Modellverhalten NOT RUN |
| R7 | Exit-Codes, Belegpflicht, Geheimnisse | SCOPE R7 | Exit-/Zustandstests, Schwärzungstests | vollständige Geheimniserkennung | teilbelegt | Schwärzung nur musterbasiert (Grenze, kein Defekt) |
| R8 | setup create/plan, Besitzprotokoll, Rollback | SCOPE R8 | Fake-npm-Tests, Rollback an jeder Position | echtes `npm install`/Build | teilbelegt | `tests/external` nicht ausgeführt |
| R9 | setup adopt/verify, Ablehnungen | SCOPE R9 | adopt-/verify-Tests mit Fake-npm | echtes npm | teilbelegt | wie R8 |
| R10 | preview Prozesssteuerung, Besitzbeweis | SCOPE R10 | Prozess-Tests mit Fake-Dev-Servern auf 127.0.0.1 | echter Astro-Dev-Server, andere Plattformen, Host | teilbelegt | Nur lokale Darwin-/Python-Umgebung |
| R11 | preview Seitenprüfung `inspect` | SCOPE R11 | alle sechs `inspect`-Zustände gegen lokale HTTP-Server | Browserdarstellung | teilbelegt | Sichtprüfung NOT RUN |
| R12 | optimize Audit, Berichte, Arbeitsliste | SCOPE R12 | Audit-/Store-/Worklist-Tests mit Fake-npm, Wegwerf-Git | echte Prüfskripte mit Node, Passung zu echten Sites | teilbelegt | Echte npm-/Node-Läufe NOT RUN |
| R13 | optimize Entscheidungen, `apply` | SCOPE R13 | Freigabe-/Apply-Tests | Qualität von Vorschlagstexten | teilbelegt | Modellurteil NOT RUN |
| R14 | edit nur Startseite | SCOPE R14 | Schreib-/Pfad-Tests, Vertragstest | Modellurteil Passung | teilbelegt | Modell-/Hostverhalten NOT RUN |
| R15 | edit Schutz und Abschlussaussage | SCOPE R15 | Sicherungs-, Konflikt-, Check-/Finish-Tests, Zugriffsspion | tatsächliche Sichtprüfung, Race-Fenster | teilbelegt | BD-28 offen, Sichtprüfung NOT RUN |
| R16 | publish ehrlicher Platzhalter | SCOPE R16 | Strukturtest (nur `SKILL.md`) | Modellverhalten | strukturell | Text, kein Verhalten |
| R17 | Kommunikationsblock in allen fünf Skills | SCOPE R17 | Textgleichheitstests | Modellverhalten | strukturell | Text, kein Verhalten |
| R18 | Dokumentation Deutsch und Englisch | SCOPE R18, README, `docs/de`, `docs/en` | Dokumentationsvertragstest (Paarung, Struktur, Links) | Dokumentationsreview | strukturell | Review ausstehend; Inhalt nicht maschinell prüfbar |
| R19 | Tests und Nachweise, Klassifikation | SCOPE R19 | Gesamtlauf deterministisch | native/behavior/external | teilbelegt | Diese Suiten NOT RUN |
| R20 | Verteilung nach Manager-Vertrag | SCOPE R20 | `scripts/plugin.py check`, Strukturtests, `marketplace.py check` | Push, Hostimport | strukturell | Remote/Hostimport nicht belegt |
| R21 | Projektdatenformate unverändert | SCOPE R21 | Format-/Pfad-Tests je Skill | echte Projekte | teilbelegt | Nur fiktive Fixtures |
| R22 | edit Voraussetzungen und Auftragsregeln | SCOPE R22 | `preflight`-Tests | Modellurteile (Fakten, Anweisungen, Routing) | teilbelegt | Modellurteil NOT RUN |
| R23 | publish Inhalt des Platzhalters | SCOPE R23 | Textmuster-Tests | Modellverhalten | strukturell | Text, kein Verhalten |
| R24 | Aufrufpfade und Auslieferung | SCOPE R24 | Kopie-Tests, Aufrufmuster ↔ `allowed-tools` als Text | Hostdeckung, Installation | teilbelegt | Hostabhängige Punkte NOT RUN |
| R25 | Dokumentation im Einzelnen, Grenzen, Installation | SCOPE R25, `docs/*/installation.md` | Dokumentationsvertragstest (Pflichtaussagen DE/EN) | Review; Installation an einem Host | strukturell | Installation nie ausgeführt |
| R26 | Vollständigkeit der Migration | SCOPE R26, completeness.json | maschinelle Zuordnungsprüfung, Quellabgleich ohne Drift | fachlicher Review der Änderungslisten | strukturell | Existenz/Zuordnung/Hashes, kein Review |

## Vollständigkeit der Quelle (R26)

[completeness.json](completeness.json) ordnet jede Datei von [source-inventory.json](source-inventory.json) genau einer Behandlung zu; der Test `tests/contracts/test_documentation_contract.py` (Klasse `Completeness`) löst sie maschinell auf.

| Behandlung | Anzahl | Beleg |
|---|---|---|
| bytegleich übernommen (`identical`) | 55 | Zielpfad und SHA-256, gleich dem Inventar |
| absichtlich angepasst (`adapted`) | 60 | Zielpfade, Änderungsliste, Verweis auf [changes.md](changes.md); Ziel ist nicht bytegleich |
| bewusst nicht übernommen (`not-adopted`) | 15 | konkreter Grund, Scope-/Planbezug, ersetzende Ziele |
| **Summe** | **130** | **0 unzugeordnet** |

Mehrfachquellen: `errors.py`, `manifest.py`, `schema.py`, `sites.py` von `preview` und `optimize` (je byte-gleich zueinander) sind in je einem Modul unter `skills/_shared/scripts/site_common/` zusammengeführt; beide Quellen tragen denselben Zielpfad und sind als `identical` bzw. `adapted` mit dem Hinweis „Multi-source“ geführt. Die drei Schema-Kopien der Quelle (`setup/schema.py`, Testfixtures) sind auf genau eine Datei reduziert (`skills/_shared/resources/website.schema.json`).

Getrennt dargestellt (nicht vermischt):

- **Migrationsanpassungen:** Namen, Pfade, Importe, Skilltexte, Schemaname (D-17); Details je Datei in [changes.md](changes.md).
- **Schutzkorrekturen an Bestandsdefekten der Quelle** (belegt, klein, getrennt ablehnbar): BD-5, BD-6 (preview); BD-7 bis BD-11, BD-15 bis BD-17 (optimize); BD-18 bis BD-25, BD-31, BD-32 (edit). Die Quelle behauptet diese nicht als Erfolge; sie zählen als Zielnachweis nur über die Regressionstests im Ziel.
- **Bestandsbeobachtungen ohne Eingriff:** BD-1 bis BD-4, BD-12 bis BD-14, BD-26 bis BD-30; BD-28 (Race-Fenster) bleibt offen.
- **Ausgeschlossene Funktionen:** Veröffentlichung/Workflow-Vorlagen (`contracts/publish.md`, `templates/github/workflows/README.md`), ZIP-Packaging (`tools/*`, Quell-`Makefile`), GEO, Lighthouse, Linkgraph, isolierte Abhängigkeitskopie, Rebaselining, `setup update`.
- **Historische Quellerfolge** („implementiert“/„bestanden“ in den Quellverträgen, Akzeptanzberichte, Beobachtungen an der echten Site) wurden nicht als Zielnachweis übernommen.

### Zurückgestellte Einträge früherer Etappen – Auflösung

| Eintrag (zurückgestellt in) | Auflösung |
|---|---|
| Kommunikationsblock in den `SKILL.md` (Etappe 1) | in allen fünf Skills textgleich (Etappen 2–5), Test je Skill |
| Prüfung „vor Build/Bericht/Prozessstart/npm“ je Einstiegspunkt (Etappe 1) | `setup` (2), `preview` (3), `optimize` (4), `edit` (5), je mit Einstiegspunkttests |
| Kopplung `types.json` ↔ Schema, Verdiktvergleich setup ↔ gemeinsam (Etappe 1) | `tests/unit/setup/test_schema.py` |
| Teile von `test_entrypoints` für `preview.py` (Etappe 2) | `tests/integration/preview/test_manifest_contract.py` und `test_side_effects_and_copy.py` |
| `tests/behavior/cases.md` B1–B11 (Etappe 5) | eingeordnet in `tests/behavior/edit_cases.md`, nicht ausgeführt (NOT RUN) |
| `tests/run_all.sh` (nicht einzeln aufgeführt) | in Etappe 6 erstmals ausdrücklich zugeordnet: nicht übernommen, ersetzt durch `scripts/run_tests.py`; im Review nachvollzogen, keine weitere Freigabe offen |

Planbezogen geprüft: geteilte Module und Mehrfachquellen (oben), geplante publish-Verträge/Workflow-Dateien (nicht übernommen), alte Packaging-Werkzeuge (nicht übernommen, Verhalten als Tests neu gefasst), historische Akzeptanzberichte (nicht übernommen), manuelle Modell-/Hostfälle (NOT RUN).

## Marketplace (lokal)

Änderung in `ai.plugins`, begrenzt auf den vorhandenen Eintrag des Website-Plugins: `name` `website-manager` → `website`, `displayName` „Website Manager“ → „Website“, Beschreibung auf den heutigen Umfang, `repository` unverändert (`https://github.com/draftm0de/ai.plugin.website.git`). Die beiden Hostkataloge wurden mit `python3 -B scripts/marketplace.py sync` abgeleitet; vorher und nachher `check` ohne Drift. Alle übrigen vorher uncommitteten Änderungen in `ai.plugins` waren unmittelbar nach der Ableitung byte-gleich zu vorher (Hashvergleich der 22 anderen Dateien). Spätere Veränderungen dieses Arbeitsstands außerhalb des Auftrags sind in [changes.md](changes.md) Etappe 6, Abschnitt C beschrieben. Kein zweiter Eintrag, kein Alias für `website-manager`. Dass der Eintrag in ai.plugins noch nicht committet oder gepusht ist, bleibt so.

## Prüfläufe

Alle Läufe am 2026-11-19 im Arbeitsverzeichnis `ai.plugin.website` (Wurzel dieses Repositories), Python 3.15.0 auf Darwin. Historische Zahlen früherer Etappen (774 Tests) sind keine Sollwerte.

### A. Testausführung durch Claude (deterministisch)

**Finaler Gesamtlauf** (Stand: nach allen Änderungen von Etappe 6 mit Ausnahme der Abschlusskorrektur, die nur Dokumentation und Nachweise betraf):

| Kommando | Exitcode | Ergebnis |
|---|---|---|
| `python3 -B scripts/run_tests.py --kind deterministic` | 0 | 793 Tests, `OK`, 0 Skips, 0 Fehler, 0 Fehlschläge, Laufzeit rund 278 s |

Der Lauf deckt `tests/unit`, `tests/integration` und `tests/contracts` ab (fiktive Fixtures, Fake-`npm`, lokale Prozesse auf 127.0.0.1). Ein vorheriger Zwischenlauf mit 789 Tests endete mit 2 Fehlern, weil `docs/migration/acceptance.md` noch fehlte; er zählt nicht als Ergebnis. Nicht ausgeführt: `tests/external` (`run_external_tests.py`), `tests/native`, `tests/behavior`.

**Nach der Abschlusskorrektur** (nur Dokumentation) wurde kein erneuter Gesamtlauf gestartet; der Gesamtlauf oben gilt für den Stand davor. Stattdessen:

| Kommando | Exitcode | Ergebnis |
|---|---|---|
| `python3 -B -m unittest tests.contracts.test_documentation_contract tests.contracts.test_structure tests.contracts.test_shared_runtime_contract` | 0 | 38 Tests, `OK` |

### B. Lesende Prüfwerkzeuge (ebenfalls von Claude ausgeführt, kein Testlauf, kein Zielcode)

| Kommando | Exitcode | Ergebnis |
|---|---|---|
| `python3 -B scripts/migration_baseline.py --inventory docs/migration/source-inventory.json --root <www.draftmode> --strict-git` (Beginn, Ende, nach Abschlusskorrektur) | 0 | `files=130 changed=0 missing=0 new=0` → NO DRIFT |
| `python3 -B scripts/plugin.py check` | 0 | Host-Manifest ohne Drift |
| `python3 -B scripts/verify.py --source . --kind plugin` | 0 | `valid`, `structure_valid`, `local_development: complete` |
| `python3 -B scripts/verify.py --source . --kind plugin --review` | 1 | `needs_attention`: 3× `missing_sources` (R2, R18, R25), `test_execution: not_run`, `target_code_executed: false` |
| `python3 -B scripts/marketplace.py check` (in `ai.plugins`, nur lesend; `sync` einmalig nach der autorisierten Eintragsänderung) | 0 | kein Drift |

### C. Unabhängiger Review

Der unabhängige Review von Etappe 6 ist ein getrennter Schritt der Person und kein Teil der obigen Läufe. Etappe 6 bleibt bis zu seinem Abschluss **Review ausstehend**. Das Ergebnis von `verify --review` (B) ist ein lesender Belegsammler und ersetzt ihn nicht.

## Offene Nachweise und nächste Schritte (nicht ausgeführt)

1. Review von Etappe 6 (unabhängig).
2. Echte npm-/Node-Läufe: `python3 -B scripts/run_external_tests.py --approved` nach gesonderter Freigabe; echter `npm run build`/`seo:check`/`a11y:check` an einer fiktiven Site.
3. Pro Skill nativer Lauf in Claude und in Codex (Skill laden, Pfadvariable, `allowed-tools`, Erreichbarkeit von `skills/_shared/` und `skills/preview/`), mit Datum, Version und Ergebnis.
4. Modellfälle `tests/behavior/edit_cases.md` und Sichtprüfung mit Browserwerkzeug je Host.
5. `update-local` und Hostimport des Marketplace-Eintrags in einem Host prüfen (nicht ausgeführt); Commit/Push des Katalogs und des Plugin-Repositories nur nach Freigabe.
