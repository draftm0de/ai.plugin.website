# Product scope / Produktzielbild

Status: confirmed

Stand: 2026-11-20 (geführter Ablauf R29–R34 umgesetzt, Review ausstehend; zuvor Etappe 6, Review ausstehend; Etappen 1–5 sind nach unabhängigem Review für die Fortsetzung abgenommen). Der Nutzer hat nach den Reviews von Etappe 0 den konkretisierten Scope einschließlich der Präzisierungen zu Manifestvalidierung (R5), `publish`-Platzhalter (R23) und Runtime-Aufrufprüfungen (R24) ausdrücklich bestätigt (D-12, `docs/migration/decisions.md`); alle Anforderungen R1–R26 sind damit `confirmed`. Zusätzlich hat der Nutzer in Etappe 2 ausdrücklich bestätigt (D-16 bis D-18): die Manifestfeldbelegung von `setup create`, die begrenzte Umbenennung der Schemadatei auf `website.schema.json` und die Ablehnung des alten Formats ohne Migration oder Fallback. Neue fachliche Details, die sich später ergeben (z. B. die offenen Felder in `docs/migration/setup-init.md`), sind nicht mitbestätigt und werden vor Verwendung ausdrücklich vorgelegt. / The user explicitly confirmed the concretized scope including the last precisions (D-12); R1–R26 are `confirmed`. Details that arise later are not covered by this confirmation.

Dieses Dokument beschreibt das Soll, keine Zusammenfassung des Codes. Belege aus der Quelle stehen getrennt im Abschnitt „Implementierungsbelege“. Migrationsnachweise unter `docs/migration/` sind keine zweite Produktdefinition. / This document is the desired behavior, not a summary of the code.

## Zweck / Purpose

Das Plugin **Website** (Plugin-Name `website`, Anzeigename „Website“) verwaltet statische Astro-Websites in einem Website-Projekt (`sites/<domain>/`) mit acht Skills: `plugin-website` (geführter Einstieg), `setup` (anlegen, übernehmen, planen, prüfen, Domain nachtragen), `brief` (inhaltliche Richtung), `design` (Startseiten-Prototypen und Freigabe), `preview` (lokal ansehen), `optimize` (SEO- und Barrierefreiheits-Audit mit Berichten und Arbeitsliste), `edit` (Startseite gestalten oder einen Text ändern) und `publish` (ehrlicher Platzhalter). Zielhosts sind Claude und Codex. Bestehende Funktionen der Quelle (`www.draftmode`, Plugin `zyris-website`, Arbeitsstand einschließlich uncommitteter Änderungen) werden erhalten und an die globale Struktur angepasst; nach der Abnahme ist dieses Repository die alleinige Entwicklungsquelle.

## Nicht-Ziele / Non-goals

Bestätigt (D-04 bis D-10):

- Keine Erweiterung um geplante Funktionen: keine Blogbearbeitung, keine weiteren Seitentypen im `edit`, kein GEO, kein Lighthouse, keine Linkgraph-Prüfung, keine isolierte Abhängigkeitskopie mit `npm ci`, keine neue Browserintegration.
- Kein `setup update`, kein `--add-missing`, `--regenerate`, `--adopt-edits`, keine Rebaselining-Funktion für Besitz-Hashes, keine Erzeugung eines Workflow-Aufrufs.
- Keine Veröffentlichung, kein Deployment, keine Schnittstelle zu `draftmode.srv`, keine Formulare.
- Keine Kompatibilitätsaliases für `zyris-website`, `website-manager` oder alte Skill-Aufrufe; keine automatische Umbenennung oder Migration bestehender Website-Projektdaten wegen des Plugin-Namens.
- Keine ZIP-/GUI-Upload-Verteilung, keine Marketplace-Kataloge im Plugin-Repository.
- Keine Bereinigung, Änderung oder Löschung in `www.draftmode`.
- Keine Installation, Commits, Pushes oder Veröffentlichung; keine Modelltests, nativen Hosttests, GUI-Abnahme, Netzwerkzugriffe für Tests oder Werkzeuginstallationen ohne eigene Freigabe.

## R1: Plugin-Identität und Skills

Status: confirmed
Basis: D-01
Acceptance: `plugin.json` trägt den Namen `website` und den Anzeigenamen „Website“; unter `skills/` liegen genau die acht Skill-Ordner `plugin-website`, `setup`, `brief`, `design`, `preview`, `optimize`, `edit` und `publish` (die Ergänzung um `plugin-website`, `brief` und `design` ist vom Nutzer bestätigt, R29–R33), jeder mit `SKILL.md`, dessen Frontmatter-Name dem Ordnernamen entspricht; die Skeleton-Identität `website-manager` und der Skeleton-Marker sind entfernt.
Source: skills/setup/SKILL.md
Source: skills/preview/SKILL.md
Source: skills/optimize/SKILL.md
Source: skills/edit/SKILL.md
Source: skills/publish/SKILL.md
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/contracts/test_edit_contract.py
Test: tests/contracts/test_publish_contract.py
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Teilbeleg (Etappe 1): Pluginname `website`, Anzeigename „Website“ im kanonischen und abgeleiteten Manifest. Von den fünf Skills ist `setup` vorhanden; Etappe 2: `skills/setup/SKILL.md` ist der erste echte Skill (Frontmatter-Name `setup`); das Skeleton `skills/website-manager/` ist entfernt (kein Alias). Etappe 3: `skills/preview/SKILL.md` (Frontmatter-Name `preview`). Etappe 4: `skills/optimize/SKILL.md` (Frontmatter-Name `optimize`). Etappe 5: `skills/edit/SKILL.md` (Frontmatter-Name `edit`) und `skills/publish/SKILL.md` (Frontmatter-Name `publish`); damit liegen genau die fünf Skill-Ordner mit `SKILL.md` vor, `skills/_shared` hat keine (Test `test_edit_contract.test_exactly_five_public_skills…`). Etappe 5 ist als „Review ausstehend“ gekennzeichnet. Etappe 6 (Review ausstehend): die Beschreibung in `plugin.json` nennt den heutigen Umfang statt des Skeleton-Wortlauts, das abgeleitete Host-Manifest hat keinen Drift (`scripts/plugin.py check`), es gibt keine Aliase und keine Kataloge im Plugin-Repository (Strukturprüfung, `test_documentation_contract.Metadata`). Das beweist keinen Hostimport.

## R2: Zielhosts Claude und Codex

Status: confirmed
Basis: D-02
Acceptance: Claude und Codex sind Zielhosts; für jeden Host liegt je Skill ein getrennter Nachweis vor, was belegt ist; ein Nachweis für einen Host gilt nie für den anderen; ohne tatsächliche Ausführung wird der Hostnachweis als `NOT RUN` berichtet.
Source: skills/plugin-website/SKILL.md
Source: skills/setup/SKILL.md
Source: skills/brief/SKILL.md
Source: skills/design/SKILL.md
Source: skills/preview/SKILL.md
Source: skills/optimize/SKILL.md
Source: skills/edit/SKILL.md
Source: skills/publish/SKILL.md
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Die Nachweislage je Skill und Host (Claude/Codex getrennt, je Kategorie Struktur/Text, deterministisch, echte Werkzeuge, Hostlauf, Modell, Sicht) steht in `docs/migration/acceptance.md`; der Test verhindert, dass die Kategorien Hostlauf, Modell und Sicht dort als etwas anderes als `NOT RUN` bzw. `n/a` geführt werden; die Kategorie Werkzeuge darf nur als begrenzter Lauf („ausgeführt (Etappe 7 …)“ mit benannten `NOT RUN`-Grenzen) erscheinen. Es wurde kein Hostlauf ausgeführt: alle Hostnachweise sind `NOT RUN` (siehe „Fehlende Ausführungs- und Hostnachweise“).

## R3: Eigenständige Runtime

Status: confirmed
Basis: D-07, Auftrag Etappe 0 Abschnitt C, Architekturregel
Acceptance: Die Runtime liegt unter `skills/<skill>/scripts/` bzw. `skills/_shared/` (ohne `SKILL.md`); sie enthält keine fest eingebauten Entwicklerpfade und keine Abhängigkeit zu `www.draftmode`, `ai.plugins`, dem Coach-Checkout oder dem Wurzel-`scripts/`; im autorisierten Produktbetrieb liest und bearbeitet sie nur das ausdrücklich ausgewählte Websiteprojekt im Rahmen des jeweiligen Skill-Vertrags.
Source: skills/_shared/scripts/which_site.py
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/site_setup.py
Source: skills/preview/scripts/control.py
Source: skills/optimize/scripts/audit.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/integration/optimize/test_isolated_copy.py
Evidenzstatus: Etappe 1 belegt deterministisch nur die gemeinsamen Module (keine Entwicklerpfade, nur Standardbibliothek, Start aus Kopie mit Leerzeichen ohne `PYTHONPATH`, kein Schreiben in die Kopie mit `-B`). Etappe 2: `setup` läuft aus einer isolierten Kopie unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis und ohne `PYTHONPATH`; die Kopie bleibt unverändert (Test unten). Etappe 3: `preview` startet aus einer isolierten Kopie (nur `skills/preview` und `skills/_shared`) unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis, ohne `PYTHONPATH` (auch mit Decoy-Modulen darauf); Template und Schema kommen aus der Kopie; die Kopie bleibt byte-gleich; Zustand liegt außerhalb. Etappe 4: `optimize` startet aus einer isolierten Kopie (nur `skills/optimize` und `skills/_shared`) unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis, mit `-I -B` und ohne `PYTHONPATH` (auch mit Decoy-Modulen darauf); das Plugin-Schema kommt aus der Kopie (fehlt es dort, stoppt der Lauf vor jedem Seiteneffekt mit dem Pfad der Kopie); der vollständige Ablauf audit → decide → show → apply (Fake-`npm`) läuft aus der Kopie, die Kopie bleibt byte-gleich, ohne `__pycache__`, der Zustand liegt im Websiteprojekt; der Resolver wird ebenfalls aus der Kopie gestartet. Runtime von `edit` fehlt (Etappe 5); Hostnachweis NOT RUN.

## R4: Aktuelle Formate, keine Aliase, keine automatische Migration

Status: confirmed
Basis: D-08, globale Regel „Nur aktuelle Formate“
Acceptance: Bestehende Website-Projektdatenformate werden nicht wegen des Plugin- oder Skill-Namens umbenannt oder migriert; für alte Plugin- und Skill-Namen gibt es keine Aliase; nicht unterstützte Formen werden mit konkretem Grund vor Schreibzugriffen abgelehnt, Nutzerdaten bleiben unverändert.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/integration/preview/test_former_format.py
Test: tests/integration/optimize/test_former_format.py
Evidenzstatus: Teilbeleg. Etappe 1: Typ `astro` und entfernte Felder werden vom gemeinsamen Manifestvalidator abgelehnt. Etappe 2 für `setup`: Typ `astro`, entfernte Felder und das alte Schemaformat (Verweis auf die alte Schemadatei in lokaler Schreibweise mit oder ohne `./`, oder nur die alte Schemadatei) werden vor jedem Schreibzugriff und vor Installation/Build abgelehnt, Dateien und die alte Schemadatei bleiben byte-gleich; kein Fallback auf die alte Datei, keine Migration (D-18). Etappe 3: jeder `preview`-Einstieg (`preview.py`, `control.py start|status|stop|inspect`) lehnt Altformat (alle lokalen Schreibweisen des Verweises, nur alte Schemadatei, mit und ohne neue Kopie) mit Diagnose vor Launch-Eintrag, Zustandsverzeichnis, Prozess und npm ab; Dateien bleiben byte-gleich; eine Altlast-Datei neben dem neuen Format ist kein Fehler. Etappe 4: jeder `optimize`-Einstieg (`audit.py audit|show|decide|apply|propose` und der gemeinsame Resolver) lehnt Altformat (alle lokalen Schreibweisen, nur alte Schemadatei, mit und ohne neue Kopie) mit Diagnose vor Build, Bericht, Arbeitsliste, Sperre und npm ab, Dateien bleiben byte-gleich; das Altformat wird ausschließlich durch die gemeinsame Erkennung festgestellt (Test: keine zweite Erkennung im Skill). Etappe 5: für `edit` gilt dasselbe über den gemeinsamen Validator; jeder Befehl lehnt das Altformat in jeder lokalen Schreibweise ohne Seiteneffekt ab (`tests/integration/edit/test_manifest_contract.py`). Etappe 6: keine Aliase für `zyris-website` oder `website-manager` in den Plugin-Manifesten und unter `skills/` (Strukturprüfung, `test_documentation_contract.Metadata`); der Nachweis betrifft Dateien, keine Hostlisten.

## R14: edit – Umfang Startseite

Status: confirmed
Basis: D-06
Acceptance: `edit` ändert ausschließlich die Startseite `src/pages/index.astro` einer Site vom Typ `astro-static` auf konkreten Auftrag (Startseite gestalten oder genau einen benannten Text/Abschnitt ändern); Blog, andere Seiten, neue Sites, Formulare und Veröffentlichung sind nicht Teil des Skills und werden nicht ausgeführt, sondern benannt.
Source: skills/edit/scripts/edit.py
Source: skills/edit/SKILL.md
Source: skills/edit/references/edit.md
Test: tests/integration/edit/test_writes.py
Test: tests/integration/edit/test_prerequisites.py
Test: tests/unit/edit/test_edit_unit.py
Test: tests/contracts/test_edit_contract.py
Evidenzstatus: Etappe 5 (Review ausstehend), deterministisch auf fiktiven Wegwerf-Projekten mit einer von `setup` erzeugten Site, Wegwerf-Git-Repositories und Fake-`npm`. Belegt: erlaubte Startseitenänderung (`write`, `replace`) ändert nur `src/pages/index.astro` (Hashvergleich aller Projektdateien); die Erlaubnisliste hat genau diesen Pfad, andere Pfade, Traversal, absolute Pfade und Nachbarseiten werden abgewiesen; es gibt keinen Befehl, der Dateien anlegt oder einen Zielpfad entgegennimmt; Typ außer `astro-static` → STOP. Die Abgrenzung (Blog, weitere Seiten, neue Sites, Formulare, Veröffentlichung) steht im Skilltext und in der Referenz (Textprüfung, kein Modellverhalten). Nicht belegt: Modellurteil (Passung, Auftrag konkret genug), Host- und Modellverhalten (NOT RUN).

## R16: publish – ehrlicher Platzhalter

Status: confirmed
Basis: D-06
Acceptance: `publish` hat kein Skript und keine Veröffentlichungsfunktion; der Skilltext sagt eindeutig, dass Veröffentlichen nicht verfügbar ist, und behauptet nie, eine Veröffentlichung sei möglich, vorbereitet oder erfolgt.
Source: skills/publish/SKILL.md
Test: tests/contracts/test_publish_contract.py
Evidenzstatus: Etappe 5 (Review ausstehend), Text- und Strukturprüfung: der Ordner enthält nur `SKILL.md` (kein Skript, keine Vorlage, keine Workflow-Datei), das Frontmatter hat nur `name` und `description` (keine `allowed-tools`), der Text sagt „publishing is not available“, verbietet jede Zusicherung „möglich, vorbereitet oder erfolgt“ und enthält keine Verweise auf Geplantes. Das beweist die Abwesenheit von Runtime und den Text, nicht das Verhalten eines Modells (NOT RUN).

## R18: Dokumentation Deutsch und Englisch

Status: confirmed
Basis: D-11
Acceptance: Die Dokumentation liegt auf Deutsch und Englisch vor; Deutsch ist die Standardsprache.
Source: tests/contracts/test_documentation_contract.py
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Die Dokumente selbst (`README*.md`, `docs/de|en/`) liegen außerhalb der vom Verifikator zugelassenen Source-Pfade (`skills/`, `scripts/`, `tests/`); als Source ist deshalb die prüfende Vertragsimplementierung genannt, nicht die Dokumente. Der Verifikator wurde nicht angepasst. Etappe 6 (Review ausstehend): `README.md`, `README.en.md`, `docs/de/` und `docs/en/` sind Website-spezifisch geschrieben (gleiche sieben Seiten, gleiche Überschriften, Befehle und Links; Deutsch ist Standardsprache laut `docs/documentation.json`). Der Test prüft Paarung, Struktur, Befehlsgleichheit, interne Links und Abwesenheit von Skeleton-Wortlaut; ob beide Sprachen inhaltlich dasselbe sagen und fachlich stimmen, belegt nur der Dokumentationsreview.

## R20: Verteilung nach Manager-Vertrag

Status: confirmed
Basis: D-07, `AGENTS.md`/`docs/architecture.md`
Acceptance: `plugin.json` ist kanonisch und trägt keine Version; das Host-Manifest wird daraus abgeleitet und weist keinen Drift auf; das Repository enthält keine Marketplace-Kataloge und keine ZIP-Verteilung.
Source: scripts/plugin.py
Source: scripts/verify.py
Test: tests/contracts/test_structure.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Belege sind Strukturprüfungen (Identität `website`, keine Version, abgeleitetes Host-Manifest ohne Drift laut `scripts/plugin.py check`, keine Kataloge); sie belegen keine Produktabnahme und keinen Hostimport.

## R5: Manifest-Vertrag

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regel 8), D-05, D-12
Acceptance: Jede Operation, die ein vorhandenes Websiteprojekt verwendet (`preview`, `optimize`, `edit`, `setup adopt|verify` und `setup create|plan` in einem Projekt mit Manifest), validiert `.project/specs/website.json` gegen das eigene Schema des Plugins (einziger Typ `astro-static`), nie gegen eine lockerere Projektkopie; dort muss die Schema-Kopie des Projekts existieren und gültiges JSON sein und wird von `preview`, `optimize`, `edit` und `setup verify` nicht verändert, und ein ungültiges Manifest stoppt vor Build, Installation, Bericht, Launch-Eintrag und Prozessstart; `setup create` für einen neuen Projektzustand (kein Manifest und/oder keine Schema-Kopie) legt die Schema-Kopie nur bei Fehlen an, **legt ein fehlendes Manifest selbst an** (nach dem aktuellen Plugin-Schema, mit den bestätigten Angaben der neuen Site, ohne bestehende Dateien zu überschreiben und ohne unbekannte fachliche Angaben zu erfinden) und validiert das entstehende Manifest gegen das Plugin-Schema, bevor geschrieben wird; `publish` benötigt kein Projektmanifest und führt keine Projektprüfung aus.
Initialisierungsregel (D-13, Feldbelegung D-16): `setup create` schreibt `$schema` = `./website.schema.json`, `version` = 2 (R29; Version 1 ist abgelöst) und eine Komponente mit `name` = Domain, `path` = angegebener Pfad, sonst `sites/<domain>`, `type` = `astro-static`, `title` = angegebener Titel, sonst Domain, `aliases` = angegebene Aliase, sonst `[]`, `port` = ausdrücklicher Port, sonst automatisch (4321 im leeren Projekt, sonst höchster effektiver Port + 1; effektiv = expliziter Port oder 4321 + Position; Kollisionen werden abgelehnt, ein automatischer Port außerhalb 1024–65535 stoppt mit dem Hinweis auf `--port`), `environment` nur bei ausdrücklicher Angabe. Vorhandene Einträge werden nie umgeschrieben. Schemakopie des Projekts: `.project/specs/website.schema.json` (D-17). Herleitung: `docs/migration/setup-init.md`.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/unit/setup/test_schema.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/integration/preview/test_manifest_contract.py
Test: tests/integration/optimize/test_manifest_contract.py
Test: tests/integration/edit/test_manifest_contract.py
Evidenzstatus (das Plugin-Schema `skills/_shared/resources/website.schema.json` ist Ressource, kein Code, und steht deshalb nicht als `Source:`): Etappe 2 ergänzt für `setup`: Initialisierung eines neuen Projekts mit Feldbelegung, explizite und automatische Ports (leer, höchster expliziter, abgeleiteter Port, Kollision mit abgeleitetem Port, Bereichsgrenzen, kein stiller Überlauf), Erhalt vorhandener Komponenten, Schemakopie fehlt/identisch/fremd/beschädigt, Stopp ungültiger Manifeste vor Installation/Build/Schreiben in `setup`. Etappe 3: Stopp je Einstiegspunkt von `preview` (`preview.py`, `control.py` mit allen vier Verben) vor Launch-Eintrag, Zustandsverzeichnis/Record und Prozess, mit gelockerter/fehlender/kaputter Projektkopie; die Projektkopie wird von `preview` nie verändert. Etappe 4: Stopp je Einstiegspunkt von `optimize` (`audit.py audit|show|decide|apply|propose`, Resolver) vor Build, Bericht, Arbeitsliste, Sperre, npm-Aufruf und Dateiänderung, mit gelockerter/fehlender/kaputter Projektkopie; die Projektkopie wird von `optimize` nie verändert. Etappe 5: Stopp je Einstiegspunkt von `edit` vor Schreiben, Zustand und npm-Aufruf, auch bei Folgebefehlen (`tests/integration/edit/test_manifest_contract.py`). Teilbeleg aus Etappe 1: Validierung gegen das Plugin-Schema (gelockerte oder fremde Projektkopie bestimmt den Vertrag nicht, fehlende/kaputte Kopie ergibt STOP, Resolver stoppt bei ungültigem Manifest). Die früher als fehlend geführten Punkte (Stopp je Einstiegspunkt, `setup create` mit Manifest-Initialisierung) sind durch die Etappen 2–5 oben belegt (Stand Etappe 6, Review ausstehend); echte npm-/Node-Läufe und Hostverhalten bleiben NOT RUN.

## R6: Standortwahl

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regel 1), D-05, D-12
Acceptance: Die Website wird nie geraten; Reihenfolge: vom Nutzer genannt (Domain, Ordner, Titel, Alias) > Arbeitsverzeichnis liegt in einer Site > nur eine Site vorhanden > zuletzt in der Unterhaltung benutzte Site (mit ausgesprochener Bestätigung) > Rückfrage; eine unbekannte ausdrückliche Site ergibt STOP (Exit 1), eine mehrdeutige ASK (Exit 2) mit Optionen; `preview status` und `preview stop` verwenden die „zuletzt benutzt“-Regel nur nach Bestätigung.
Source: skills/_shared/scripts/site_common/sites.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/unit/preview/test_launch.py
Test: tests/integration/preview/test_control.py
Test: tests/integration/optimize/test_manifest_contract.py
Evidenzstatus: Resolver belegt deterministisch (Reihenfolge, unbekannt = STOP/Exit 1, mehrdeutig = ASK/Exit 2 mit Optionen, „zuletzt“ nur mit Bestätigung). Etappe 5: `edit preflight` reicht Name, Arbeitsverzeichnis, „zuletzt“ (mit `confirm`), unbekannt und mehrdeutig unverändert durch (`tests/integration/edit/test_prerequisites.py`). Etappe 3: `preview` verwendet den gemeinsamen Resolver (benannt, Alias, cwd, `--last` mit Bestätigung, ASK/Exit 2; `stop --last` ohne Bestätigung ergibt ASK). Etappe 4: `optimize` verwendet den gemeinsamen Resolver (`--site`, unbekannte Site = STOP/Exit 1, mehrdeutig = ASK/Exit 2 mit Optionen; der Skilltext ruft den gemeinsamen `which_site.py` zuerst). Verwendung durch `edit` siehe Etappe 5 oben; der Skilltext von `edit` ist nur als Text geprüft (kein Modell- oder Hostverhalten, NOT RUN).

## R7: Exit-Codes, Belegpflicht, Geheimnisse

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regeln 2–4), D-05, D-12
Acceptance: Exit 0 bedeutet Erfolg, 1 STOP (Meldung beginnt mit `STOP:`), 2 ASK; „bestanden“, „gebaut“ oder „bereit“ wird nur gemeldet, wenn die Prüfung in diesem Aufruf lief und mit 0 endete (nicht gelaufene Schritte erscheinen als nicht gelaufen, nie als bestanden); keine Geheimnisse in Dateien, Kommandozeilen, Berichten oder Ausgaben.
Source: skills/_shared/scripts/site_common/errors.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/preview/test_control.py
Test: tests/integration/optimize/test_audit.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/integration/edit/test_checks_and_finish.py
Evidenzstatus: Teilbeleg (Etappe 1): Exit-Codes und Fehlerklassen des gemeinsamen Resolvers. Etappe 3: `preview` Exit 0/1/2 und `STOP:`-Meldungen je Verb; „running“ nur nach erfolgreicher HTTP-Probe mit Zuordnung (Tests, Abschnitt R10). Etappe 4: `optimize` meldet Exit 0 nur für `clean`/`clean-with-warnings` (aus den echten Prozess-Exitcodes, nicht aus Ausgabeworten), nicht gelaufene Prüfungen erscheinen als `not run` mit `-` statt Exitcode, Tokenmuster in der Werkzeugausgabe werden im Bericht geschwärzt (`TOKEN=<redacted>`; Muster, keine Vollständigkeit), Dateisystemfehler enden als `STOP:` statt Traceback (BD-11). Etappe 5: `edit` hält die Exit-Codes (0 ok, 1 STOP als JSON mit `state`, 2 ASK nur mit Frage; Kommandozeilenfehler enden ebenfalls mit 2, siehe `changes.md` BD-29); Belegpflicht: `complete` nur aus echten Prozess-Exitcodes für den aktuellen Inhalt plus gemeldeter Sichtprüfung, ein nicht startbares npm ergibt `not-run`, nie „bestanden“; Dateisystem- und Prozessfehler enden als `STOP` statt Traceback (BD-23). Die Prüfausgabe wird als Textende (2000 Zeichen) wiedergegeben, bekannte Geheimnisfelder (Namen mit TOKEN, SECRET, PASSWORD, PASSWD, API_KEY, AUTH, auch `Authorization`/`Proxy-Authorization`) werden **vor** der Kürzung geschwärzt: quotierte Werte vollständig, andere Werte samt Schema bis Zeilenende (Tests mit fiktiven Werten in stdout und stderr, Erfolg und Fehlschlag, über der Kürzungsgrenze, Prüfung auf jedes Teilstück); eine Musterliste, keine vollständige Erkennung (`changes.md` B2/B3, BD-31).

## R8: setup – anlegen, planen, Besitzprotokoll

Status: confirmed
Basis: D-01, D-04, D-05, D-06, D-12
Acceptance: `setup create <domain> --type astro-static` schreibt in einen fehlenden oder leeren `sites/<domain>/` das vollständige statische Template (keine Docker-/Caddy-/Workflow-Dateien), registriert die Komponente, legt die Schema-Kopie nur bei Fehlen an, ergänzt `.tmp/` samt `.gitignore`-Eintrag und schreibt das Besitzprotokoll; `plan create|adopt` schreibt, installiert und baut nichts und liefert dasselbe Urteil wie der echte Lauf; identische Wiederholung ergibt `unchanged` ohne Schreibzugriff; Abweichungen, geänderte oder fehlende erzeugte Dateien und fremde Schema-Kopien ergeben `conflict` ohne Schreibzugriff; ein Schreibfehler stellt alle Dateien und die Registrierung wieder her (`failed-rolled-back`, sonst `failed-partial` mit Rest); Zustände und Exit-Codes: `created|adopted|verified|unchanged|planned` = 0, `needs-input` = 2, alles andere = 1.
Source: skills/setup/scripts/site_setup.py
Source: skills/setup/scripts/static_setup.py
Source: skills/setup/scripts/ownership.py
Source: skills/setup/references/setup.md
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/setup/test_review_fixes.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_external_separation.py
Test: tests/external/website/test_real_tools.py
Evidenzstatus: Etappe 2: deterministisch auf fiktiven Fixtures mit Fake-`npm` belegt (create, `unchanged`, `conflict` ohne Schreiben, `plan` = Urteil des Laufs ohne Seiteneffekte, Rollback an jeder Rename-Position, `failed-partial` mit Rest, Exit-Codes, Besitzprotokoll); Template-Identität gegen das Inventar (Hashgleichheit bzw. explizite Änderungsliste). Echte `npm install`-/Build-Läufe: `tests/external/setup/test_real_npm.py`, außerhalb der Standardschichten, nur über `scripts/run_external_tests.py --approved` nach gesonderter Freigabe (NOT RUN); geerbte Umgebungsvariablen aktivieren sie nicht (Test `tests/contracts/test_external_separation.py`). Hostnachweis NOT RUN. Etappe 7 (nur Werkzeuglauf, kein Host): echtes `npm install`/Build/`check` einer fiktiven `astro-static`-Site mit Node v26.12.1/npm 11.20.0 auf Darwin arm64 über den externen Runner und `tests/external/website/test_real_tools.py`; Bericht [docs/migration/real-tools-acceptance.md](docs/migration/real-tools-acceptance.md). Nur eine Node-/npm-Version belegt; Hostnachweis NOT RUN.

## R9: setup – übernehmen, prüfen, Ablehnungen

Status: confirmed
Basis: D-04, D-05, D-06, D-12
Acceptance: `setup adopt <domain>` registriert einen vorhandenen statischen Ordner und ändert keine Datei darin (Baumhash vor und nach dem Lauf gleich); blockierende Befunde (fehlende oder ungültige `package.json`, kein `build`-Skript, nicht ignorierte Build-Ausgabe, fehlender Ordner oder Symlink) ergeben `invalid` ohne Änderung, Warnungen werden gemeldet und nicht repariert; `setup verify <domain>` führt Installation, Build und Prüfung mit echten Exit-Codes aus, regeneriert und überschreibt keine Site-Datei und meldet geänderte erzeugte Dateien als `modified (kept)`; mit `--build` laufen dieselben drei Schritte; `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` ohne Operation sowie der Typ `astro` und die entfernten Docker-Optionen werden abgelehnt und nie übersetzt.
Source: skills/setup/scripts/static_setup.py
Test: tests/integration/setup/test_static_adopt.py
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/setup/test_entrypoints.py
Evidenzstatus: Etappe 2: adopt (Baumhash gleich, blockierende Befunde, Warnungen), `verify`/`--build` mit Fake-`npm` und simulierten Exit-Codes (`ran:false` für nicht gelaufene Schritte), `modified (kept)`, abgelehnte Funktionen und Optionen ohne Schreiben. Echtes `npm`: NOT RUN (siehe R8). Hostnachweis NOT RUN. Etappe 7: `setup verify` mit echtem npm auf der fiktiven Site (vor und nach einer `edit`-Änderung: `modified (kept)`, Exit 0), siehe [docs/migration/real-tools-acceptance.md](docs/migration/real-tools-acceptance.md). `adopt` mit echtem npm: `tests/external/setup/test_real_npm.py`.

## R10: preview – Prozesssteuerung

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: Nur `control.py start|status|stop` startet, nutzt wieder oder beendet den Dev-Server; ein Prozess gilt nur bei Besitzbeweis (Protokoll, Projektwurzel, Site, Arbeitsverzeichnis, Port, PID mit gleicher Startzeit und Prozessgruppe, alle Listener der Gruppe) als eigen – Startname und Port sind nie Beweis; `start` ergibt `running-new` oder `running-reused` (kein zweiter Server) erst nach erfolgreicher HTTP-Probe, bei fremdem Listener `port-conflict` ohne Signal oder Übernahme; bei fehlenden Abhängigkeiten `needs-install`, ohne dass der Skill selbst installiert (die Person wird auf `npm install` im Site-Ordner hingewiesen); `stop` signalisiert nur nachweislich eigene Prozessgruppen; fehlende Betriebssystem-Nachweise (`ps`, `lsof`) ergeben `insufficient-evidence` ohne Schreiben, Starten oder Signalisieren; `--timeout` ist endlich, größer 0 und höchstens 600; Zustandsdateien liegen außerhalb des Repositories und werden sicher angelegt (exklusiv, ohne Symlinks, Modus 0600/0700).
Source: skills/preview/scripts/control.py
Source: skills/preview/scripts/preview.py
Source: skills/preview/references/preview.md
Test: tests/integration/preview/test_control.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/unit/preview/test_launch.py
Test: tests/unit/preview/test_launch_links.py
Test: tests/integration/preview/test_state_area_and_launch_links.py
Test: tests/external/website/test_real_tools.py
Evidenzstatus: Etappe 3, deterministisch mit eigenen lokalen Fake-Dev-Servern auf 127.0.0.1, Fake-`npm`, Fake-`ps`/`lsof` und privatem Zustandsverzeichnis je Test: Start und Bereitschaft erst nach HTTP-Probe mit Zuordnung, Wiederverwendung ohne zweiten Server, `status` ohne Start, `stop` nur bei Besitznachweis, fremder Listener bleibt unverändert (`port-conflict`, kein Signal), veraltete/abweichende Nachweise und recycelte PID, fehlende/verweigerte/blinde `ps`/`lsof` (`insufficient-evidence`), Timeout-Grenzen, fehlende Abhängigkeiten ohne npm-Aufruf, Zustandsdateien (Symlink/FIFO/Fremdbesitz als letzte Komponente; seit der Schutzkorrektur BD-6 auch Symlinks im Basis- und im Projekt-Zustandsverzeichnis für `start`, `status`, `stop`, `inspect` und das Aufräumen, mit Zugriffsspy und abgefangenen Signalen; fehlender Zustand wird nicht angelegt; Vorfahren des Basisverzeichnisses sind nicht geprüft), Launch-Datei als Symlink (auch defekt, auch `.claude` als Link) oder unsupportierter Dateityp (BD-5: `STOP`, kein Dev-Server, nichts hinter dem Link geöffnet), Fehler nach dem Start mit Aufräumen, Zwei-Projekte-Fall, unabhängige Launch-Einträge. Quell-Behauptungen über echtes Astro (`--ignore-lock`, Detach) sind nur mit einem Fake-Detach geprüft; echtes `npm`/Astro NOT RUN; Hostnachweis NOT RUN. Die Prozesstests sind Verhaltensbelege der lokalen Python-/macOS-Umgebung (Darwin, Python 3.15), nicht anderer Plattformen. Etappe 7: echter Astro-Dev-Server über `control.py` (`start`, `status`, `inspect` mit eindeutigem Text, `stop`) auf 127.0.0.1 einer fiktiven Site, danach kein eigener Prozess und kein Listener; HTTP-/Runtime-Evidenz, keine Browser-Sichtprüfung; siehe [docs/migration/real-tools-acceptance.md](docs/migration/real-tools-acceptance.md).

## R11: preview – Seitenprüfung und Zuständigkeit

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: `control.py inspect --expect <Text>` startet, signalisiert und übernimmt nichts, ändert Manifest und Port nicht und meldet `page-confirmed` nur, wenn kanonische Adresse und Seitenname der Site entsprechen und jeder erwartete sichtbare Text vorkommt; `page-other-site`, `page-stale`, `page-identity-only`, `page-identity-unknown` und `page-not-reachable` gelten nie als Beleg; Prozess- und Seitenergebnis werden getrennt berichtet; kein Browserwerkzeug startet einen zusätzlichen Dev-Server oder wechselt den Port, Browserwerkzeuge öffnen nur die vom Controller gelieferte oder bestätigte Adresse.
Source: skills/preview/scripts/control.py
Source: skills/preview/SKILL.md
Test: tests/integration/preview/test_inspect.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/contracts/test_preview_contract.py
Evidenzstatus: Etappe 3: alle sechs `inspect`-Zustände gegen lokale HTTP-Server (Identität per kanonischer Adresse und Seitenname, sichtbarer Text, `page-identity-only` ohne `--expect`, strukturierter Adressvergleich); `inspect` startet/signalisiert nichts, schreibt weder Zustand, Launch-Eintrag noch Manifest und trennt Prozess- und Seitenergebnis. Der Skilltext verlangt Browserzugriff nur auf die Controller-/`inspect`-Adresse und keinen visuellen Erfolg ohne tatsächliche Sichtprüfung (Textprüfung, kein Modell- oder Hostverhalten). Eine statische HTML-Prüfung ist kein Nachweis der Browserdarstellung; die Sichtprüfung im Browser ist NOT RUN.

## R12: optimize – Audit, Berichte, Arbeitsliste

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: `audit.py audit` baut in das git-ignorierte `dist/`, führt `seo:check` und `a11y:check` unabhängig voneinander aus, liest die echten Exit-Codes und vergleicht Pfade und Hashes der nicht ignorierten, nicht privaten Projektdateien vor und nach dem Lauf; Ergebnis ist `clean`, `clean-with-warnings`, `errors`, `incomplete` (fehlendes Werkzeug, Abhängigkeit, Lockfile, Build oder unlesbare Ausgabe, nie als sauber gemeldet) oder `readonly-violated`; der Lauf installiert nie (auch nicht in einer Kopie), committet nie und ändert keinen Site-Inhalt; geschrieben werden nur ein unveränderlicher Bericht unter `.project/reports/<site>/optimize/<Zeitstempel>.md` und die generierte Arbeitsliste `.project/reports/<site>/optimize.md`; Befundklassen (technischer Fehler, Warnung, redaktionelle Empfehlung) werden nie vermischt, redaktionelle Empfehlungen werden nie durch fehlende Prüfung geschlossen, manuelle Prüfpunkte stehen stets im Bericht und gelten nie als bestanden; Befunde behalten stabile IDs (Site + Kriterium + Ort), Entscheidungen bleiben über Läufe erhalten, wiedergekehrte Befunde erscheinen als `reappeared`; eine von Hand geänderte oder beschädigte Arbeitsliste stoppt den Lauf vor dem Bauen.
Source: skills/optimize/scripts/audit.py
Source: skills/optimize/scripts/findings.py
Source: skills/optimize/scripts/worklist.py
Source: skills/optimize/scripts/store.py
Source: skills/optimize/references/optimize.md
Source: skills/optimize/SKILL.md
Test: tests/integration/optimize/test_audit.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/integration/optimize/test_source_state_links.py
Test: tests/integration/optimize/test_worklist_bytes.py
Test: tests/integration/optimize/test_store.py
Test: tests/unit/optimize/test_findings.py
Test: tests/unit/optimize/test_findings_templates.py
Test: tests/integration/optimize/test_manifest_contract.py
Test: tests/integration/optimize/test_isolated_copy.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/external/website/test_real_tools.py
Evidenzstatus: Etappe 4, deterministisch auf fiktiven Wegwerf-Git-Repositories mit einer fiktiven Site, deren `build`, `seo:check` und `a11y:check` kleine Shell-Skripte im Ausgabeformat der setup-Templates sind, und einem Fake-`npm`, das jeden Aufruf protokolliert und alles außer `run` ablehnt; kein echtes `npm`, `node`, Netzwerk oder Websiteprojekt. Belegt: erster und wiederholter Audit (Bericht, Arbeitsliste, stabile IDs `SEO-001…`, keine doppelten Befunde, kein versionierter Dateiinhalt und kein Lockfile geändert, Git-Status nur im Berichtsbereich), `clean`, `clean-with-warnings`, `errors`, `incomplete` (Buildfehler mit echtem Exitcode und übersprungenen Prüfungen, fehlende `node_modules`/Lockfile/nicht ignorierte Ausgabeordner/fehlendes `npm`/fehlendes Prüfskript/Prüfung startet nicht/unlesbare oder dem Exitcode widersprechende Ausgabe, getrennt je SEO und A11y), `readonly-violated` (geänderte versionierte Datei und von der Build-Phase neu angelegte unversionierte Datei, nicht zurückgesetzt, nichts geschlossen; versionierte Symlinks werden als Linkobjekt ohne Zugriff auf das Ziel erfasst, ein Linkaustausch ist sichtbar, ein Elternlink stoppt den Lauf; Access-Spy plus Zugriffssperre belegen, dass externe Dateien nicht geöffnet werden), vorher vorhandene fremde Änderungen werden „as they were“ geprüft und bleiben erhalten, erwartete ignorierte Build-Ausgabe und Berichtsschreiben sind keine Verletzung, unveränderliche Berichte mit Kollisionsbehandlung (auch Race, hängender Symlink), Symlinks im Berichtsbereich (Ordner, `optimize`, Arbeitsliste, `.project/reports`), unsichere Sitenamen, fremde Dateien bleiben, abgebrochener Austausch, beschädigte Arbeitsliste (Text, von Hand geändert, Prüfsumme, anderer Site, fremde Formatversion, leer, kein UTF-8, Verzeichnis) stoppt **alle** Befehle vor dem Bauen ohne Änderung der Datei, Sperre und gleichzeitige Änderung, Befundklassen getrennt (technischer Fehler, Warnung, redaktionelle Empfehlung), manuelle Prüfpunkte in jedem Bericht und nie als bestanden, kein Ranking-Versprechen in den Katalogtexten, Geheimnisse geschwärzt, `show` schreibt nichts. Adapter gegen die Meldungsformate der **ausgelieferten setup-Templates** (nur Text, Node nicht ausgeführt); das beweist keine Gleichheit mit den Prüfskripten einer echten Website. Nicht belegt: echte `npm`/Node-Läufe, die Node-Versionsprüfung (nur ohne `--npm`), reale Astro-Builds, Hostverhalten (NOT RUN). Belegte Bestandsdefekte (BD-7 bis BD-11) und Beobachtungen (BD-12 bis BD-14) stehen in `docs/migration/changes.md` Etappe 4. Etappe 7: echtes `audit` (Build, `seo:check`, `a11y:check` mit eigenen Exitcodes), kontrollierter Fixture-Befund, `propose`/`decide`/`apply` und echte Wiederholungsprüfung an einer fiktiven Site; Adapter verarbeitet die Ausgabe der ausgelieferten Prüfskripte; siehe [docs/migration/real-tools-acceptance.md](docs/migration/real-tools-acceptance.md). Modellurteil NOT RUN.

## R13: optimize – Entscheidungen und Umsetzung

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: Befundstatus sind genau `proposed`, `approved`, `deferred`, `wont-do`; `decide` ändert nur die Entscheidung, eine bereits entschiedene Sache nur mit `--change`; `apply` setzt nur freigegebene, nicht veraltete Vorschläge mit mechanischem `edit` um (Suchtext genau einmal, nur in einer nicht ignorierten Projektdatei der Site), lehnt alles andere ab, installiert nie und führt die Neuprüfung selbst aus; ein Befund wandert nur in die Historie, wenn ein vollständiger Lauf nach erfolgreichem Build ihn nicht mehr meldet; bei Fehlschlag oder unvollständiger Prüfung bleibt er offen und freigegeben mit Grund; Vorschläge erfinden keine Fakten, Quellen, Bewertungen oder strukturierten Daten für nicht sichtbare Inhalte und versprechen kein Ranking.
Source: skills/optimize/scripts/audit.py
Source: skills/optimize/scripts/worklist.py
Source: skills/optimize/references/optimize.md
Source: skills/optimize/SKILL.md
Test: tests/integration/optimize/test_apply_scope.py
Test: tests/integration/optimize/test_audit.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/integration/optimize/test_source_state_links.py
Test: tests/contracts/test_optimize_contract.py
Evidenzstatus: Etappe 4, deterministisch (Fixtures und Fakes wie R12). Belegt: genau vier Status; `decide` ändert keinen Site-Inhalt in keinem Status (Hashes und Git-Status unverändert, kein Build), eine entschiedene Sache nur mit `--change`, Sammelaufruf mit unbekannter ID ändert nichts; `proposed`, `deferred`, `wont-do` werden nie umgesetzt (Ablehnung `not approved`, nichts geändert, kein Build); ein bloßer Audit gibt nichts frei; `approved` und unveränderter Ausgangstext ändern genau die freigegebene Datei und nur die freigegebene Stelle, danach läuft die vollständige Neuprüfung selbst (Build und beide Prüfungen), nichts wird installiert (alle Aufrufe sind `run …`); geänderter Vorschlag oder Ausgangstext macht die Freigabe ungültig und `apply` lehnt ab; Suchtext fehlt (0×) oder mehrfach (2×) vorhanden: keine Änderung; unversionierte oder fehlende Datei, Pfad außerhalb der Site (auch Geschwisterordner mit gleichem Präfix), `..`, absoluter Pfad, Symlink als Datei und Symlink als Elternordner: kontrollierte Ablehnung ohne Änderung (auch des Ziels hinter dem Link) und ohne Build; fremde uncommittete und unversionierte Änderungen (auch in der Zieldatei) bleiben erhalten; Neuprüfung bei Buildfehler, unvollständiger Prüfung oder fortbestehendem Befund schließt nichts und lässt den Befund offen und freigegeben mit Grund; ein Befund wechselt erst nach vollständigem Lauf in die Historie; `reappeared`; Entscheidungen bleiben über mehrere Läufe und bei gleichzeitiger Entscheidung erhalten. Schutzkorrekturen zum Bestand (BD-7 CRLF, BD-8 kein UTF-8, BD-9 Temp-Datei nach fehlgeschlagenem Austausch, BD-10 unlesbare Arbeitsliste, BD-11 Dateisystemfehler, BD-15 Mehrfachersetzung im Original statt im veränderten Text mit Ablehnung überlappender Bereiche und doppelter IDs vor dem Schreiben, BD-16 Wächter folgt keinen Symlinks, BD-17 Arbeitsliste wird bytegetreu gelesen und geschrieben, sodass Wagenrückläufe in Vorschlagstexten sie nicht als handverändert erscheinen lassen; Format unverändert) mit Regressionstests; Details `docs/migration/changes.md` Etappe 4. Nicht belegt: die inhaltliche Qualität von Vorschlägen („keine erfundenen Fakten“ ist eine Modellvorgabe im Skilltext und nur als Text geprüft), Hostverhalten (NOT RUN).

## R15: edit – Schutz und Abschlussaussage

Status: confirmed
Basis: D-04, D-05, D-06, D-12
Acceptance: `begin` sichert einen Snapshot der nicht ignorierten, nicht privaten Projektdateien und das Original der Zieldatei in einem eigenen Sicherungsordner außerhalb des Repositories; `write` und `replace` schreiben atomar nur bei erwartetem Hash und weisen jeden anderen Pfad, Traversal und Symlinks ab; eine zwischenzeitlich geänderte, entfernte oder durch Symlink ersetzte Datei ergibt `conflict` ohne Überschreiben; `check` führt `npm run build` und `npm run check` mit echten Exit-Codes aus, ist nur für den geprüften Inhalt gültig, höchstens zwei Reparaturrunden; `finish` meldet `complete` nur nach bestandenem Build und Check und tatsächlich durchgeführter Sichtprüfung, sonst „technically checked, visual check open“ (auch wenn kein Browserwerkzeug verfügbar ist); bestehende uncommittete Änderungen anderer bleiben unberührt; `edit` installiert nie Abhängigkeiten, committet nie und schreibt nie unter `.project/reports/`, in Regeln, Marken-, Prüfskript-, `package.json`-, Lockfile-, Manifest- oder Besitzprotokolldateien.
Source: skills/edit/scripts/edit.py
Source: skills/edit/SKILL.md
Source: skills/edit/references/edit.md
Test: tests/integration/edit/test_writes.py
Test: tests/integration/edit/test_checks_and_finish.py
Test: tests/integration/edit/test_backup_and_state.py
Test: tests/integration/edit/test_symlink_reads.py
Test: tests/integration/edit/test_manifest_contract.py
Test: tests/unit/edit/test_edit_unit.py
Test: tests/external/website/test_real_tools.py
Evidenzstatus: Etappe 5 (Review ausstehend), deterministisch mit Fake-`npm`-Prozessen (echte Prozess-Exitcodes), Wegwerf-Git-Repositories und Zugriffsspion. Belegt: `begin` sichert HEAD, `git status` mit unversionierten Dateien und das Original bytegetreu (auch Nicht-UTF-8, CRLF) in einem Ordner mit Modus 0700 außerhalb von Projekt und installiertem Plugin (ein `TMPDIR` darin oder ein Symlink im Bereich wird abgelehnt); `write`/`replace` atomar (Rechte bleiben, Temp-Datei entfernt, Schreibfehler ohne Erfolgsmeldung) nur bei erwartetem Hash; geänderte, entfernte oder durch Symlink ersetzte Zieldatei (auch Elternverzeichnis, Site-Ordner) → `conflict` ohne Überschreiben und ohne Lesen hinter dem Symlink (Zugriffsspion auf jeden `open`/Verzeichnislisting); fremde uncommittete und unversionierte Änderungen bleiben (kein Stash/Reset/Clean); CRLF und mehrzeilige Ersetzung ohne Normalisierung; `check` mit echten Exitcodes (0, 1, 3, 42), Build-Fehler → Check „nicht gelaufen“, fehlendes npm → `not-run`, Ergebnis nur für den geprüften Inhalt (Änderung während der Prüfung → `conflict`, spätere Änderung → `stale`), höchstens zwei Reparaturrunden; `finish`: `complete` nur nach bestandener Technik für den aktuellen Inhalt **und** gemeldeter Sichtprüfung, sonst „technically checked, visual check open“, fehlgeschlagene/nicht gelaufene Technik nie so umgedeutet; Sicherungsbereinigung nur im bestätigten Erfolgsfall, nur der eigene Ordner, und erst nachdem der **gesamte** Sicherungsbaum rekursiv gegen die exakt erwarteten Objekte, Typen und den Originalinhalt geprüft wurde (fremde Datei oder Ordner auf jeder Ebene, ersetztes Objekt oder Link → nichts wird entfernt, Ausgabe nennt den Zustand); Zustandsdatei, `.owner` und Originalsicherung werden geprüft (`lstat` des Sitzungsordners, Link vor dem Öffnen abgelehnt, `O_NOFOLLOW` für die letzte Komponente) und nicht über Symlinks gelesen; ein Austausch eines Elternordners zwischen Prüfung und Öffnen ist damit nicht pauschal ausgeschlossen, die temporäre Zustandsdatei ist exklusiv erzeugt (Zugriffsspion, `changes.md` B2, BD-24, BD-32); keine Schreibzugriffe auf Berichte, Regeln, Marken-, Prüfskript-, `package.json`-, Lockfile-, Manifest-, Schema- oder Besitzprotokolldateien; nie Install, nie Commit. Nicht belegt: eine **tatsächliche** Sichtprüfung (`--visual-done` ist die Aussage des Aufrufers; Tests damit belegen nur die Zustandslogik), echte `npm`/Node-Läufe, Host- und Modellverhalten (NOT RUN). Schutzkorrekturen an Bestandsdefekten der Quelle: `changes.md` Etappe 5 B (BD-18 bis BD-25, BD-31, BD-32). Etappe 7: echtes `edit check` (Build, `check`), Hashbindung, Sicherung und `finish` ohne `--visual-done` (`technically checked, visual check open`) an einer fiktiven Site; Sichtprüfung bleibt offen (NOT RUN); siehe [docs/migration/real-tools-acceptance.md](docs/migration/real-tools-acceptance.md).

## R17: Kommunikation mit der Person

Status: confirmed
Basis: D-04, D-05 (`communication.md`), D-12
Acceptance: Der Block „Working with the person“ steht in allen fünf `SKILL.md` textgleich; er verlangt Antwort in der Sprache der Person, eigenständiges Erledigen des Auftrags, Rückfragen nur bei ergebnisrelevanten Lücken, eine kurze Schlussantwort ohne technische Details (Prozess-IDs, Ports, Exit-Codes, Hashes, Diffs) und dass eine fehlende Pflichtprüfung nie nachträglich zu „optional“ umgedeutet wird.
Source: skills/_shared/references/communication.md
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/contracts/test_edit_contract.py
Test: tests/contracts/test_publish_contract.py
Evidenzstatus: Die Referenz (Block `user-communication`) ist byte-gleich übernommen (Hash gegen Inventar geprüft); der Block steht textgleich in `skills/setup/SKILL.md` (Etappe 2) und `skills/preview/SKILL.md` (Etappe 3, Textgleichheitstest) und `skills/optimize/SKILL.md` (Etappe 4, Textgleichheit zu `setup` und `preview`); Etappe 5: derselbe Block steht textgleich in `skills/edit/SKILL.md` und `skills/publish/SKILL.md` (Textgleichheit zur Referenz und zu allen übrigen vier Skills); damit stehen alle fünf textgleich; eine Textprüfung beweist kein Modellverhalten.

## R19: Tests und Nachweise

Status: confirmed
Basis: D-10, `tests/README.md`, D-12
Acceptance: Deterministische Tests liegen unter `tests/unit/`, `tests/integration/`, `tests/contracts/` auf fiktiven Fixtures in isolierten Verzeichnissen; kein Test liest `www.draftmode`, echte Website-Inhalte oder private Projektdaten; Tests werden nach tatsächlichem Verhalten klassifiziert (Netzwerk-/`npm`-Tests sind nicht automatisch native Hosttests); Tests mit Modell, GUI oder nativem Host liegen unter `tests/behavior/` bzw. `tests/native/` und laufen nie im Standardlauf; fehlende oder nicht gelaufene Suiten melden `NOT RUN`, nie Abnahme; strukturelle und Textprüfungen gelten nicht als Verhaltensnachweis.
Source: scripts/run_tests.py
Test: tests/unit/test_migration_baseline.py
Test: tests/unit/shared/test_manifest.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_setup_contract.py
Test: tests/unit/setup/test_schema.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/unit/preview/test_launch.py
Test: tests/integration/preview/test_control.py
Test: tests/integration/optimize/test_audit.py
Test: tests/unit/optimize/test_findings.py
Test: tests/integration/edit/test_writes.py
Test: tests/integration/edit/test_symlink_reads.py
Test: tests/contracts/test_edit_contract.py
Evidenzstatus: Test-Runner vorhanden; Etappe 2 ergänzt `setup`-Tests (unit/integration/contracts, fiktive Fixtures, Fake-`npm`); die echten npm-Tests liegen separat (`tests/external/`, ausgeführt in Etappe 7 über `run_external_tests.py --approved`) und sind im Standardlauf ausgeschlossen; die Aufräumlogik des externen Tests ist deterministisch mit Fakes belegt (`tests/unit/external_cleanup/`). Etappe 1 liefert deterministische Tests für gemeinsame Module und das Basiswerkzeug auf fiktiven Fixtures in Temp-Verzeichnissen. Etappe 3 ergänzt `preview`-Tests (fiktive Fixtures, lokale Prozesse nur auf 127.0.0.1 im Rahmen von D-14). Etappe 4 ergänzt `optimize`-Tests (unit/integration/contracts, fiktive Git-Repositories, Fake-`npm`; der Quelltest mit Zugriff auf die Prüfskripte der echten Site ist durch einen Test gegen die ausgelieferten setup-Templates ersetzt). Etappe 5 ergänzt `edit`-Tests (unit/integration/contracts, von `setup` erzeugte fiktive Site, Wegwerf-Git-Repositories, Fake-`npm`, Zugriffsspion) und `publish`-Vertragstests; die manuellen Modell-/Hostfälle des Quellprojekts sind in `tests/behavior/edit_cases.md` eingeordnet, ausdrücklich nicht ausgeführt und `NOT RUN`; `native` fehlt (NOT RUN). Etappe 6 ergänzt `tests/contracts/test_documentation_contract.py` (Dokumentation, Metadaten, Vollständigkeitszuordnung, Matrixgrenzen); der Gesamtlauf mit Ergebnis steht in `docs/migration/acceptance.md`.

## R21: Projektdatenformate im Einzelnen

Status: confirmed
Basis: D-08 (Konkretisierung von R4), D-12
Acceptance: Unverändert bleiben Manifest `.project/specs/website.json`, Besitzprotokoll `.project/specs/website.manage.json` sowie Berichte und Arbeitsliste unter `.project/reports/<site>/` samt deren Formatmarkern; abgelehnt werden der Typ `astro` und die Felder `serve`, `registry`, `retention`, `dockerfile` mit konkretem Grund vor jedem Schreibzugriff, ohne Inferenz oder Migration.
Ausnahme (D-17, begrenzt): Die Schemadatei heißt im Plugin `skills/_shared/resources/website.schema.json`, im Websiteprojekt `.project/specs/website.schema.json`; das Manifest verweist mit `"$schema": "./website.schema.json"`. Kein Fallback auf `zyris-website.schema.json`, kein Alias, keine automatische Migration (D-18). Der Dateiinhalt ist unverändert; nur der Name ändert sich.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/ownership.py
Test: tests/contracts/test_setup_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/integration/edit/test_manifest_contract.py
Evidenzstatus: Etappe 2: Manifest-, Besitzprotokoll- und Schemanamen in `setup` belegt (Neuprojekt, Altformat-Ablehnung). Etappe 4: Berichts- und Arbeitslistenpfade, Formatmarker (`zyris-optimize:worklist v1`, `state`, `report v1`, Format `zyris-optimize-worklist`) und der erzeugte Arbeitslistentext sind unverändert (Test: `worklist.py` unterscheidet sich von der Quelle nur im Import; der Text nennt dabei noch den früheren Skillaufruf, siehe `changes.md` BD-13); Manifest und Besitzprotokoll werden von `optimize` nie geschrieben. Etappe 5: `edit` schreibt weder Manifest, Schemakopie, Besitzprotokoll noch Berichte (Hashvergleich über einen ganzen Lauf); Altformat und ungültige Manifeste werden an jedem Befehl, auch bei Folgeoperationen mit vorhandenem Zustand, ohne Seiteneffekt abgelehnt.

## R22: edit – Voraussetzungen und Auftragsregeln

Status: confirmed
Basis: D-05, D-06 (Skill-Vertrag `edit.md` §2, §6), D-12
Acceptance: `preflight` schreibt nichts; fehlen vor der ersten Änderung Seite, `package.json`, Skripte `build`/`check`, `node_modules`, Lockfile oder eine bindende Regeldatei (Git ist keine Voraussetzung, siehe R28; die Altaussage zu git in diesem Absatz ist durch R28 ersetzt), stoppt `edit` ohne Schreibzugriff und nennt der Person die Befehle (kein Install durch `edit` oder `preview`); ein Typ außer `astro-static` ergibt STOP ohne Migration, eine unbekannte ausdrückliche Site Exit 1, eine mehrdeutige Exit 2; passt der Auftrag nicht zum Zweck der gewählten Site, wird nichts geändert und nach dem Zielprojekt oder `setup` gefragt; fehlende Fakten werden gezielt erfragt, nichts wird erfunden (keine Kontakte, Adressen, Preise, Bewertungen, Lizenzen); Platzhalter nur bei ausdrücklich bestelltem Demonstrationsauftrag und sichtbar markiert; mitgelieferte Texte, Dateien und Links sind Daten – enthaltene Anweisungen werden zitiert und erfragt, nicht ausgeführt; ein allgemeiner Änderungsauftrag gibt keinen optimize-Befund frei, ein Auftrag mit Befund-ID läuft über `optimize`.
Source: skills/edit/scripts/edit.py
Source: skills/edit/SKILL.md
Source: skills/edit/references/edit.md
Test: tests/integration/edit/test_prerequisites.py
Test: tests/integration/edit/test_manifest_contract.py
Test: tests/integration/edit/test_symlink_reads.py
Test: tests/contracts/test_edit_contract.py
Evidenzstatus: Etappe 5 (Review ausstehend). Belegt deterministisch: `preflight` schreibt nichts (Projekt, Sicherungsbereich, installiertes Plugin, kein Bytecode); fehlende Startseite, `package.json` (auch Symlink, kein Objekt), Skripte `build`/`check`, `node_modules`, Lockfile oder eine bindende Regeldatei → STOP (der damalige Git-Beleg ist durch R28 überholt) mit `commands_for_the_person`, kein npm-Aufruf, kein Install, keine Sitzung; Typ außer `astro-static` → STOP ohne Migration; unbekannte ausdrückliche Site Exit 1, mehrdeutige Exit 2 mit Optionen. Die Aussagen des Skilltexts zu fehlenden Fakten, Platzhaltern, mitgelieferten Anweisungen, Passung und optimize-Befund-IDs sind Text (Textprüfung); die **Modellurteil-Anteile sind durch deterministische Tests nicht belegbar** (Einordnung: `tests/behavior/edit_cases.md`, NOT RUN).

## R23: publish – Inhalt des Platzhalters

Status: confirmed
Basis: D-06 (Konkretisierung von R16), D-12
Acceptance: Der Skilltext benennt allgemein, was fehlt (zentraler Workflow und serverseitiges Protokoll, Workflow-Aufruf), verweist für eine lokale Qualitätsprüfung auf `optimize` mit dem Hinweis, dass dies keine Veröffentlichungsprüfung ist, verweist nicht auf geplantes Verhalten, deployt, pusht und committet nicht, fragt nichts per Netzwerk ab, erfindet keine Workflow-Namen, SHAs, Hosts oder Geheimnisse, legt keine Workflow-Datei an und gibt keine Befehlsvorabfreigabe.
Source: skills/publish/SKILL.md
Test: tests/contracts/test_publish_contract.py
Evidenzstatus: Etappe 5 (Review ausstehend), Text- und Strukturprüfung: benennt allgemein den zentralen Workflow, das serverseitige Protokoll und den Workflow-Aufruf als fehlend; verweist für die lokale Qualitätsprüfung auf `optimize` mit dem Satz „That is not a publishing check“; kein Verweis auf Geplantes, keine Netzwerk-/Deploy-/Commit-/Push-Aktion, keine erfundenen Workflow-Namen, SHAs, Hosts oder Geheimnisse (Muster geprüft), keine Workflow-Datei, keine Befehlsfreigabe; der Text steht allein (aus einem leeren Pluginordner ohne Projekt, Manifest und `_shared` auflösbar). Kein Modellverhalten belegt (NOT RUN).

## R24: Aufrufpfade und Auslieferung

Status: confirmed
Basis: D-05 (Skilltexte „Plugin path (binding)“), D-07, D-12
Acceptance: Für Skills bzw. Operationen mit Runtime-Einstiegspunkt (`setup`, `preview`, `optimize`, `edit`; `publish` hat keinen) gilt: jeder Einstiegspunkt startet aus einer extrahierten Kopie unter einem Pfad mit Leerzeichen und ohne `PYTHONPATH`; die Aufrufmuster in den Skilltexten schreiben den Skriptpfad als ein Argument; der Skill prüft vor dem ersten Aufruf, ob sein Skript existiert, und stoppt mit Meldung, wenn der Pfad fehlt oder veraltet ist, ohne Skripte in das Websiteprojekt zu kopieren; für `publish` gibt es keine Skript-, Aufruf- oder Existenzprüfung; die Runtime schreibt keinen Zustand in das installierte Plugin; nur Python-Standardbibliothek.
Source: skills/_shared/scripts/which_site.py
Test: tests/integration/shared/test_which_site_entry.py
Source: skills/setup/SKILL.md
Source: skills/setup/references/setup.md
Source: skills/preview/SKILL.md
Source: skills/preview/references/preview.md
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Source: skills/optimize/SKILL.md
Source: skills/optimize/references/optimize.md
Test: tests/contracts/test_optimize_contract.py
Test: tests/integration/optimize/test_isolated_copy.py
Source: skills/edit/SKILL.md
Source: skills/edit/scripts/edit.py
Source: skills/publish/SKILL.md
Test: tests/contracts/test_edit_contract.py
Test: tests/contracts/test_publish_contract.py
Test: tests/integration/edit/test_isolated_copy.py
Evidenzstatus: Teilbeleg. Etappe 1: gemeinsamer Resolver. Etappe 2: `setup` startet aus einer Kopie mit Leerzeichen, anderem Arbeitsverzeichnis und ohne `PYTHONPATH`, Templates und Schema kommen aus der Kopie, fehlende Ressourcen stoppen vor dem Schreiben, die Kopie bleibt unverändert; der Skilltext schreibt den Skriptpfad als ein Argument (`python3 -B`), prüft `test -f` vor dem ersten Aufruf, trennt Claude (`${CLAUDE_SKILL_DIR}`) und Codex (Pfad der geladenen `SKILL.md`), `allowed-tools` sind aus dem Aufrufmuster abgeleitet (Textprüfung, kein Hostnachweis). Etappe 3: `preview` analog (Aufrufmuster als ein Argument mit `python3 -B`, `test -f` vor dem ersten Aufruf, Claude-/Codex-Pfadbehandlung getrennt, `allowed-tools` genau die beiden Muster; Ableitung als Textprüfung). Etappe 4: `optimize` analog (zwei Aufrufmuster `scripts/audit.py` und gemeinsamer `../_shared/scripts/which_site.py`, je ein `test -f`, vier `allowed-tools`-Muster; jedes Aufrufmuster wird von genau einem Muster gedeckt und umgekehrt; Ableitung als Textprüfung). Ob Claude ein Bash-Muster mit `..`, Anführungszeichen und Leerzeichen deckt, ist nicht dokumentiert (NOT RUN). Etappe 5: `edit` analog (zwei Aufrufmuster `scripts/edit.py` und `../preview/scripts/control.py`, je ein `test -f`, vier `allowed-tools`-Muster, kein Muster für den Resolver, den nur `edit.py` aufruft; jedes Aufrufmuster wird von genau einem Muster gedeckt und umgekehrt; Textprüfung); `edit.py` startet aus einer Kopie (nur `skills/edit`, `skills/_shared`) unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis, `-I -B`, ohne `PYTHONPATH` (Decoys), die Kopie bleibt byte-identisch und ohne `__pycache__` (auch ohne `-B` des Aufrufers: der Resolver-Kindprozess läuft mit `-B`), ein fehlender Resolver oder ein fehlendes Schema stoppt vor jedem Schreiben; `publish` hat keinen Einstiegspunkt, keine Prüfung, keine Freigabe. Die Deckung eines Musters mit `..` zum Nachbarskill `preview` und die Erreichbarkeit von `skills/preview/` und `skills/_shared/` bei Claude und Codex sind nicht dokumentiert (NOT RUN). Konvention: `docs/migration/host-conventions.md`; Hostdeckung NOT RUN.

## R25: Dokumentation im Einzelnen

Status: confirmed
Basis: D-11 (Konkretisierung von R18), D-12
Acceptance: `README.md` und `docs/de/` sowie `README.en.md` und `docs/en/` beschreiben dieselben Fakten ohne Widerspruch zu SCOPE und Quelltext, nennen die Grenzen (Platzhalter `publish`, Startseitenumfang von `edit`, getrennte Hostnachweise, bekannte Einschränkung zwischen `edit` und `setup`), enthalten die Installation nach dem Manager-Vertrag und duplizieren keine maßgeblichen Produktfakten.
Source: tests/contracts/test_documentation_contract.py
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Die Dokumente selbst liegen außerhalb der vom Verifikator zugelassenen Source-Pfade; als Source ist die prüfende Vertragsimplementierung genannt. Der Verifikator wurde nicht angepasst. Etappe 6 (Review ausstehend): die Seiten nennen die Grenzen (Platzhalter `publish`, Startseitenumfang von `edit`, getrennte Hostnachweise, die Einschränkung zwischen `edit` und `setup` mit `conflict` und `modified (kept)`, Race-Fenster und musterbasierte Schwärzung), enthalten die Installation nach dem Manager-Vertrag getrennt nach Host und verweisen für Einzelheiten auf SCOPE.md. Der Test sichert Pflichtaussagen in beiden Sprachen; Widerspruchsfreiheit zu SCOPE und Quelltext ist nur durch den Review prüfbar. Die Installation ist **nicht** an einem Host ausgeführt (NOT RUN).

## R26: Vollständigkeit der Migration

Status: confirmed
Basis: D-03, D-04, D-12
Acceptance: Jede Datei von `docs/migration/source-inventory.json` ist im Ziel entweder byte-gleich übernommen (Hashgleichheit), absichtlich angepasst (in einer expliziten Änderungsliste mit begrenztem Diff) oder bewusst nicht übernommen (mit Grund); die Quelle `www.draftmode` bleibt unverändert; Abweichungen der Quelle von der Basis werden vor jeder Etappe gemeldet, nicht still übernommen.
Source: scripts/migration_baseline.py
Test: tests/unit/test_migration_baseline.py
Test: tests/contracts/test_documentation_contract.py
Evidenzstatus: Etappe 6 (Review ausstehend): `docs/migration/completeness.json` ordnet jede der 130 Inventardateien genau einer Behandlung zu (`identical` mit Zielpfad und Hashbeleg, `adapted` mit Zielpfaden und Änderungsliste, `not-adopted` mit Grund und Scope-/Planbezug); der Test prüft Vollständigkeit, Eindeutigkeit, Hashes und Zielexistenz maschinell. Das belegt Existenz, Zuordnung und Hashes, keine fachliche Richtigkeit der Änderungslisten. Zurückgestellte Einträge früherer Etappen sind aufgelöst (`docs/migration/acceptance.md`). Der Quellabgleich zu Beginn und am Ende der Etappe ergab keinen Drift.

## Bekannte Einschränkung: edit und setup

Nach einer `edit`-Änderung an einer von `setup` erzeugten Datei stimmt der im Besitzprotokoll gespeicherte Hash nicht mehr. Heute ergibt dann `setup create` für diese Site `conflict` ohne Schreibzugriff, und `setup verify` behält die Datei (`modified (kept)`). `setup.md` §5 und `edit.md` §4.6/§12 weisen die Zuständigkeit für die Koexistenz beide `setup` zu; eine zukünftige Regel zum neuen Aufsetzen der Hashes (Rebaselining) ist dort nicht festgelegt, `setup update` und `--adopt-edits` sind nicht umgesetzt. Diese Migration führt keine solche Regel ein; die Einschränkung wird dokumentiert (R25).

## Offene Punkte nach Kategorie

Details, Fundstellen und Begründungen: `docs/migration/decisions.md`.

- **Durch Nutzerentscheidung oder explizite Vertragsstatus bereits beantwortet:** V1 (preview: spätere, als implementiert markierte Abschnitte §11–13 gelten; das Host-Tool-Zielmodell ist geplant und ausgeschlossen), V2 (optimize: isolierte Kopie ist geplant und ausgeschlossen; `apply` und Audit installieren nie), V4 (publish bleibt Platzhalter), V5 (siehe „Bekannte Einschränkung“), Q7 (nur normatives Verhalten wird übernommen).
- **Technische Implementierungsentscheidungen** (ohne Nutzerentscheidung): V3 gemeinsame Module (in Etappe 1 entschieden: Paket `site_common`, `docs/migration/changes.md`), Q1/Q2 Aufrufpfade und Claude-Freigabemuster (Konvention in Etappe 1 festgelegt, Einzelmuster mit den Skills: `docs/migration/host-conventions.md`), Q4 neutrale Meldungen (umgesetzt in den gemeinsamen Modulen), Q5 interne Zustandsnamen (unverändert), Q6 Testklassifikation, Q8 Mindestversionen (Python ≥ 3.10).
- **Echte fachliche Unklarheit / Nutzerentscheidung:** keine offene Freigabefrage. Q10 ist durch D-14 beantwortet: Preview-Tests dürfen eigene lokale Prozesse starten, `127.0.0.1`-Ports verwenden und ausschließlich eigene, eindeutig identifizierte Testprozesse bzw. Prozessgruppen beenden; externe Netzwerkzugriffe für Tests bleiben ausgeschlossen. Die Felder der Manifest-Initialisierung sind durch D-16 entschieden (`docs/migration/setup-init.md`).
- **Fehlende Ausführungs- und Hostnachweise** (bis zur Ausführung `NOT RUN`): Claude- und Codex-Verhalten je Skill; Ersetzung von `${CLAUDE_PLUGIN_ROOT}` und Wirkung von `allowed-tools`; Verfügbarkeit von Browserwerkzeugen je Host; Wirkung von `"autoPort": false` in `.claude/launch.json` (Claude Desktop; dokumentiert, nicht beobachtet); tatsächliche Sichtprüfung im Browser; ob beide Hosts `skills/_shared/` mitinstallieren; ob ein Claude-`allowed-tools`-Muster mit `..` (gemeinsamer Resolver aus `optimize`) greift; echte `npm run build`/`seo:check`/`a11y:check`-Läufe auf weiteren Node-Versionen und Plattformen und die Node-Untergrenze 22.23.4 von `optimize` (ausgeführt ist nur Node v26.12.1/npm 11.20.0 auf Darwin arm64, Etappe 7).

## Implementierungsbelege (Quelle, keine Anforderungen)

Pfade in `www.draftmode/.claude/plugins/zyris-website/` (Inventar: `docs/migration/source-inventory.json`). Aussagen der Verträge, etwas sei „implementiert“ oder ein Test „bestanden“, sind **nicht geprüft** und kein Nachweis; die Quelle wurde nie ausgeführt.

| Anforderung | Fundstellen in der Quelle |
|---|---|
| R3, R5, R6, R7, R24 | `contracts/interfaces.md` §3; `scripts/*/{errors,manifest,schema,sites}.py`; `scripts/optimize/which_site.py`; Skilltexte „Plugin path (binding)“ |
| R8, R9 | `contracts/setup.md`; `scripts/setup/*.py`; `tests/setup/` |
| R10, R11 | `contracts/preview.md` §11–13; `scripts/preview/{control,preview}.py`; `tests/preview/` |
| R12, R13 | `contracts/optimize.md`; `scripts/optimize/{audit,findings,worklist,store}.py`; `tests/optimize/` |
| R14, R15, R22 | `contracts/edit.md` §2, §5–9, §14; `scripts/edit/edit.py`; `tests/edit/` |
| R16, R23 | `skills/publish/SKILL.md`; `contracts/publish.md` (geplantes Verhalten, außerhalb der Migration) |
| R17 | `contracts/communication.md`; `tools/test_skill_texts.py` |

## Current formats only / Nur aktuelle Formate

No legacy layouts, compatibility aliases, fallback discovery or automatic migrations.
Reject unsupported formats explicitly before writes; preserve all existing user data.
Changes to rules may make an existing plugin fail verification. Update it only under
an explicit implementation request; never weaken scope to accept outdated content.
Keine Altformat-Unterstützung oder stillen Migrationen. Nicht unterstützte Daten
mit konkretem Grund ablehnen, niemals löschen oder überschreiben.

## R27: Persistente Operatorsprache pro Projekt

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: Alle fünf Skills lesen vor fachlichen Rückfragen/Aktionen die Operatorsprache aus dem ausgewählten Projekt. Fehlt sie, wird zuerst allein nach der bevorzugten Sprache gefragt und die explizite Antwort persistiert. Spätere Aufrufe und neue Sitzungen verwenden diese Sprache ohne erneute Frage. Ein ausdrücklicher Änderungswunsch aktualisiert nur dieses Projekt. Website- und Dokumentationssprache bleiben unabhängig. Ungültige Formate werden ohne Überschreiben abgelehnt. Diese Präzisierung bestimmt die Sprachauswahl von R17; der übrige Kommunikationsvertrag bleibt erhalten.
Source: skills/_shared/references/operator-language.md
Source: skills/_shared/scripts/operator_language.py
Source: skills/setup/SKILL.md
Test: tests/integration/shared/test_operator_language.py
Test: tests/behavior/operator_language_acceptance.md

R27 präzisiert auch R16/R23: Der publish-Platzhalter benötigt nun ausschließlich für die gemeinsame Sprachpräferenz den Shared-Helper und den gewählten Projektordner. Website-Manifest und Site-Inhalte werden dabei nicht gelesen; Veröffentlichung bleibt unverändert nicht verfügbar. Frühere Nachweise zur vollständigen Datei-/Runtime-Freiheit beschreiben den Stand vor R27.

## R28: Lokale Website-Arbeit ohne Git

Status: confirmed
Basis: Nutzerauftrag und Abstimmung 2026-11-20 („ja“ zur vorgeschlagenen Variante)
Acceptance: `setup`, `preview`, `edit` und `optimize` benötigen weder Git-Programm noch Repository, Commit oder Remote und führen keine Git-Abfragen oder Initialisierung aus. Die Projektwurzel ist der ausdrücklich ausgewählte Ordner (`--root`, sonst Arbeitsverzeichnis), auch innerhalb eines übergeordneten Repositorys. Alle Setup-Operationen einschließlich `plan`, `adopt` und `verify` funktionieren damit. Projektlokale `.gitignore`-Regeln bestimmen weiterhin ignorierte Build-Ausgaben; globale Git-Konfiguration ist nicht erforderlich. `edit` sichert Original und Dateisnapshot, prüft weiterhin erwartete Hashes und meldet Dateiänderungen. `optimize` erkennt hinzugefügte, entfernte und geänderte Quelldateien auch ohne Versionierung; `apply` darf freigegebene, nicht ignorierte Quelldateien bearbeiten. Snapshots folgen keinen Symlinks und lesen keine ignorierten oder privaten Dateien. Alte Edit-Sessions ohne Dateisnapshot werden vor Änderungen mit Diagnose abgelehnt und bleiben erhalten. Manifest, Besitzprotokoll und Optimize-Formatkennungen bleiben unverändert. `publish` bleibt der bisherige Platzhalter ohne Git-Vorprüfung; eine Git-Pflicht gehört erst zur später separat spezifizierten Veröffentlichungsfunktion.
Source: skills/_shared/scripts/site_common/project_files.py
Source: skills/setup/scripts/static_setup.py
Source: skills/edit/scripts/edit.py
Source: skills/optimize/scripts/audit.py
Test: tests/unit/shared/test_project_files.py
Test: tests/integration/setup/test_without_git.py
Test: tests/integration/edit/test_without_git.py
Test: tests/integration/optimize/test_without_git.py
Evidenzstatus: Umsetzung und deterministische Nachweise werden in docs/development/git-independent-local-work.md getrennt vom Soll dokumentiert. Historische Git-bezogene Migrationsbelege zu R12/R15 beschreiben den damaligen Stand; sie belegen R28 nicht.

## R29: Manifest Version 2, Site-ID und optionale Domain

Status: confirmed
Basis: Nutzerentscheidung 2026-11-20 (Variante a; Version 2 ausdrücklich bestätigt; Platzhalterdomains ausgeschlossen)
Acceptance: Das Manifest hat `version` 2. `name` ist die stabile interne Site-ID (zugleich Ordnername und Besitzschlüssel), keine Domain; `domain` ist optional und enthält ausschließlich eine ausdrücklich angegebene Domain; fehlendes `domain` heißt „Domain noch nicht festgelegt“. Aus `name`, `site.ts` oder `astro.config.mjs` wird nie eine Domain abgeleitet oder übernommen. Ohne Domain entstehen keine absoluten Canonical-, Social-, Sitemap- oder robots-Adressen und keine Platzhalterdomain. `setup create|adopt <site-id> [--domain D]`; `setup set-domain <site-id> <domain>` trägt eine Domain später nach (ID, Pfad, Port und Zuordnungen bleiben; nur unveränderte erzeugte Dateien werden angepasst, sonst Konflikt ohne Schreibzugriff). Version 1 wird vor jeder projektverändernden Aktion und jedem Runtime-Aufruf mit Diagnose abgelehnt; keine Migration, kein Fallback, kein Migrationswerkzeug. Manifest und domainabhängige Konfiguration müssen übereinstimmen (`site_common/consistency.py`: Textprüfung ohne Ausführung von Code, Kommentare zählen nicht, Symlinks werden nie gefolgt; nicht erkennbare oder dynamische Konfiguration ist „nicht zuverlässig prüfbar“, nie „domainlos“); Widersprüche stoppen `setup` (Plan und `verify`), `preview` (Startpfade), `optimize`, `edit` (über den Resolver) und den Resolver vor Änderungen, Builds und Prozessen und werden konkret gemeldet, nie repariert.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/_shared/scripts/site_common/consistency.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_consistency.py
Test: tests/integration/setup/test_manifest_v2.py
Evidenzstatus: Das Plugin-Schema `skills/_shared/resources/website.schema.json` ist Ressource, kein Code, und steht deshalb (wie in R5) nicht als `Source:`; es wird von `tests/unit/shared/test_manifest.py` und den Vertragstests gelesen. deterministisch belegt (fiktive Projekte, Fake-npm); die bewusste Abweichung von den historischen Quell-Hashes steht in docs/development/manifest-v2-divergence.md, das Quelleninventar ist unverändert. Echtes npm/Astro mit Version-2-Skeleton, Hostverhalten: NOT RUN.

## R30: Zentraler Einstieg `plugin-website`

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: Der Skill `plugin-website` (Plugin-Identität bleibt `website`; kein Alias entfernter Namen) prüft den Projektzustand ohne Änderungen (`flow.py status`), erklärt den nächsten Schritt, startet fehlende Schritte, übernimmt Angaben aus dem ursprünglichen Auftrag, fragt nur nach Fehlendem und setzt bei späteren Aufrufen am passenden Punkt fort. Vorhandene, unbekannte oder widersprüchliche Zustände gelten nie als leeres Projekt. Aktivierung: expliziter Aufruf nach Skillname und Aktivierung durch Beschreibung sind strukturell vorgesehen; eine garantierte Aktivierung durch ein einzelnes Wort wird nicht zugesagt und ist ohne echten Hosttest nicht belegt.
Source: skills/plugin-website/SKILL.md
Source: skills/plugin-website/references/entry.md
Source: skills/_shared/scripts/flow.py
Test: tests/integration/flow/test_flow_state.py
Test: tests/contracts/test_guided_flow_contract.py
Evidenzstatus: Zustandsableitung und Skilltext strukturell/deterministisch; Gesprächsverhalten, Hostaktivierung (Claude/Codex): NOT RUN.

## R31: brief

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: `brief` erarbeitet Zweck, Zielgruppe, Angebot, Botschaft, gewünschte Handlung, Tonalität, Sprache der Website (getrennt von der Bedienersprache), Materialien, gestalterische Richtung und Farbpalette (Vorschläge mit Begründung, gewählte Palette gespeichert), nutzt Bekanntes, unterstützt mehrere Feedbackrunden und speichert das Briefing im Websiteprojekt (`.project/website/<site-id>/brief.json`, strenges Format, Feldstatus bestätigt/vorgeschlagen/offen, jede Revision erhalten). Designvarianten entstehen erst nach ausdrücklicher Bestätigung der Grundlage.
Source: skills/brief/SKILL.md
Source: skills/brief/references/brief.md
Source: skills/_shared/scripts/site_common/flowstate.py
Test: tests/integration/flow/test_flow_state.py
Evidenzstatus: Format, Bestätigungsbindung und Veraltung deterministisch; das Fragen und Vorschlagen selbst ist Modellverhalten (NOT RUN).

## R32: design und revisionsgebundene Freigabe

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: `design` erzeugt aus dem bestätigten Briefing mindestens zwei klar unterschiedliche Startseiten-Prototypen (strukturelle Prüfung: ein bloßer Farbwechsel zählt nicht), mit Textentwürfen statt Lorem ipsum; Fakten wie Preise, Qualifikationen, Jahre, Zahlen und Ergebnisse stehen nur als gekennzeichnete offene Angaben. Prototypen liegen unter `.project/website/<site-id>/design/rNNN/` außerhalb von `sites/` (kein Teil der Website, die Startseite bleibt unberührt), sind lokal vergleichbar (Vergleichsseite) und unveränderlich je Revision. Feedback führt zu einer neuen Revision. Eine Freigabe bindet Revision, Variante, Variantenhash und Briefinghash und braucht die ausdrückliche Aussage der Person; eine bloße Präferenz ist keine Freigabe; eine neuere Revision macht eine ältere Freigabe veraltet. Nach der Freigabe setzt der Ablauf die Startseite ohne zweite Bestätigung um; der Schreibumfang bleibt `src/pages/index.astro` mit Originalsicherung, Hashprüfung und Konflikterkennung von `edit`.
Source: skills/design/SKILL.md
Source: skills/design/references/design.md
Source: skills/_shared/scripts/site_common/flowstate.py
Test: tests/integration/flow/test_flow_state.py
Evidenzstatus: Strukturprüfungen der Prototypen sind kein Nachweis von Designqualität oder freiem Fehlen erfundener Aussagen (Mustererkennung). Hosts, Modell, Sicht: NOT RUN. Zusätzliche `edit`-Schreibpfade sind nicht freigegeben (offener Vorschlag).

## R33: Zustandsvertrag und Wiederaufnahme

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: Der versionierte Projektzustand (`flow.json`, schema_version 1; `docs/development/guided-flow.md`) unterscheidet Setup fehlt/vollständig/widersprüchlich, Briefing fehlt/in Bearbeitung/bestätigt, Designvarianten fehlen/liegen vor/werden überarbeitet/freigegeben, Umsetzung fehlt/begonnen/abgeschlossen/veraltet/vom Nutzer geändert sowie technische und visuelle Prüfung offen/bestanden/fehlgeschlagen (gebunden an den Hash der aktuellen Startseite). Zustand und tatsächliche Artefakte (Hashes) werden gemeinsam geprüft. Änderungen am Briefing oder an einer freigegebenen Revision markieren abhängige Ergebnisse als veraltet; nichts wird gelöscht. Wiederholte Aufrufe erzeugen keine Duplikate und führen Erledigtes nicht erneut aus; beschädigte oder unbekannte Zustandsformate und Symlinks werden gemeldet und nie repariert, migriert oder überschrieben. `publish` bleibt unverändert ein Platzhalter.
Source: skills/_shared/scripts/site_common/flowstate.py
Source: skills/_shared/scripts/flow.py
Test: tests/integration/flow/test_flow_state.py
Evidenzstatus: deterministisch belegt auf fiktiven Projekten; Konflikt mit zwischenzeitlichen Nutzeränderungen an der Startseite wird erkannt (Verweigerung ohne Überschreiben).

## R34: Auslieferung benötigter Punkt-Vorlagen

Status: confirmed
Basis: Nutzerauftrag 2026-11-20
Acceptance: Das erzeugte Plugin-Paket enthält die Skeleton-Vorlagen einschließlich `.gitignore.tpl` und `.gitkeep` (nur diese exakten Dateinamen, nur unterhalb eines `templates`-Ordners eines Skills); `.env*`, Schlüsseldateien, Punktordner und generierte Dateien bleiben ausgeschlossen; `setup` läuft aus dem erzeugten Paket (Claude- und Codex-Nutzlast) und erzeugt Skeleton, Ignore-Regeln und Manifest.
Source: scripts/plugin.py
Test: tests/integration/package/test_package_setup.py
Evidenzstatus: Paketinhalt und Setup-Lauf aus dem Paket (Fake-npm) deterministisch; Marketplace-Paketierer im Repository ai.plugins gleichartig angepasst und dort getestet. Installation in einem Host: NOT RUN.
