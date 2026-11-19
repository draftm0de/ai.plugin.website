# Product scope / Produktzielbild

Status: confirmed

Stand: 2026-11-19 (Etappe 2). Der Nutzer hat nach den Reviews von Etappe 0 den konkretisierten Scope einschließlich der Präzisierungen zu Manifestvalidierung (R5), `publish`-Platzhalter (R23) und Runtime-Aufrufprüfungen (R24) ausdrücklich bestätigt (D-12, `docs/migration/decisions.md`); alle Anforderungen R1–R26 sind damit `confirmed`. Zusätzlich hat der Nutzer in Etappe 2 ausdrücklich bestätigt (D-16 bis D-18): die Manifestfeldbelegung von `setup create`, die begrenzte Umbenennung der Schemadatei auf `website.schema.json` und die Ablehnung des alten Formats ohne Migration oder Fallback. Neue fachliche Details, die sich später ergeben (z. B. die offenen Felder in `docs/migration/setup-init.md`), sind nicht mitbestätigt und werden vor Verwendung ausdrücklich vorgelegt. / The user explicitly confirmed the concretized scope including the last precisions (D-12); R1–R26 are `confirmed`. Details that arise later are not covered by this confirmation.

Dieses Dokument beschreibt das Soll, keine Zusammenfassung des Codes. Belege aus der Quelle stehen getrennt im Abschnitt „Implementierungsbelege“. Migrationsnachweise unter `docs/migration/` sind keine zweite Produktdefinition. / This document is the desired behavior, not a summary of the code.

## Zweck / Purpose

Das Plugin **Website** (Plugin-Name `website`, Anzeigename „Website“) verwaltet statische Astro-Websites in einem Website-Projekt (`sites/<domain>/`) mit fünf Skills: `setup` (anlegen, übernehmen, planen, prüfen), `preview` (lokal ansehen), `optimize` (SEO- und Barrierefreiheits-Audit mit Berichten und Arbeitsliste), `edit` (Startseite gestalten oder einen Text ändern) und `publish` (ehrlicher Platzhalter). Zielhosts sind Claude und Codex. Bestehende Funktionen der Quelle (`www.draftmode`, Plugin `zyris-website`, Arbeitsstand einschließlich uncommitteter Änderungen) werden erhalten und an die globale Struktur angepasst; nach der Abnahme ist dieses Repository die alleinige Entwicklungsquelle.

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
Acceptance: `plugin.json` trägt den Namen `website` und den Anzeigenamen „Website“; unter `skills/` liegen genau die fünf Skill-Ordner `setup`, `preview`, `optimize`, `edit` und `publish`, jeder mit `SKILL.md`, dessen Frontmatter-Name dem Ordnernamen entspricht; die Skeleton-Identität `website-manager` und der Skeleton-Marker sind entfernt.
Source: skills/setup/SKILL.md
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_setup_contract.py
Evidenzstatus: Teilbeleg (Etappe 1): Pluginname `website`, Anzeigename „Website“ im kanonischen und abgeleiteten Manifest. Von den fünf Skills ist `setup` vorhanden; Etappe 2: `skills/setup/SKILL.md` ist der erste echte Skill (Frontmatter-Name `setup`); das Skeleton `skills/website-manager/` ist entfernt (kein Alias). `preview`, `optimize`, `edit`, `publish` fehlen (Etappen 3–5).

## R2: Zielhosts Claude und Codex

Status: confirmed
Basis: D-02
Acceptance: Claude und Codex sind Zielhosts; für jeden Host liegt je Skill ein getrennter Nachweis vor, was belegt ist; ein Nachweis für einen Host gilt nie für den anderen; ohne tatsächliche Ausführung wird der Hostnachweis als `NOT RUN` berichtet.
Evidenzstatus: Source und Test noch nicht vorhanden; Hostnachweise stehen aus (siehe „Fehlende Ausführungs- und Hostnachweise“).

## R3: Eigenständige Runtime

Status: confirmed
Basis: D-07, Auftrag Etappe 0 Abschnitt C, Architekturregel
Acceptance: Die Runtime liegt unter `skills/<skill>/scripts/` bzw. `skills/_shared/` (ohne `SKILL.md`); sie enthält keine fest eingebauten Entwicklerpfade und keine Abhängigkeit zu `www.draftmode`, `ai.plugins`, dem Coach-Checkout oder dem Wurzel-`scripts/`; im autorisierten Produktbetrieb liest und bearbeitet sie nur das ausdrücklich ausgewählte Websiteprojekt im Rahmen des jeweiligen Skill-Vertrags.
Source: skills/_shared/scripts/which_site.py
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/site_setup.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_setup_contract.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/setup/test_init_ports_legacy.py
Evidenzstatus: Etappe 1 belegt deterministisch nur die gemeinsamen Module (keine Entwicklerpfade, nur Standardbibliothek, Start aus Kopie mit Leerzeichen ohne `PYTHONPATH`, kein Schreiben in die Kopie mit `-B`). Etappe 2: `setup` läuft aus einer isolierten Kopie unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis und ohne `PYTHONPATH`; die Kopie bleibt unverändert (Test unten). Runtime von `preview`, `optimize`, `edit` fehlt (Etappen 3–5); Hostnachweis NOT RUN.

## R4: Aktuelle Formate, keine Aliase, keine automatische Migration

Status: confirmed
Basis: D-08, globale Regel „Nur aktuelle Formate“
Acceptance: Bestehende Website-Projektdatenformate werden nicht wegen des Plugin- oder Skill-Namens umbenannt oder migriert; für alte Plugin- und Skill-Namen gibt es keine Aliase; nicht unterstützte Formen werden mit konkretem Grund vor Schreibzugriffen abgelehnt, Nutzerdaten bleiben unverändert.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Evidenzstatus: Teilbeleg. Etappe 1: Typ `astro` und entfernte Felder werden vom gemeinsamen Manifestvalidator abgelehnt. Etappe 2 für `setup`: Typ `astro`, entfernte Felder und das alte Schemaformat (Verweis auf die alte Schemadatei in lokaler Schreibweise mit oder ohne `./`, oder nur die alte Schemadatei) werden vor jedem Schreibzugriff und vor Installation/Build abgelehnt, Dateien und die alte Schemadatei bleiben byte-gleich; kein Fallback auf die alte Datei, keine Migration (D-18). Für `preview`, `optimize`, `edit` gilt dasselbe über den gemeinsamen Validator (Test `which_site`/Manifest); Einstiegspunkttests und Aliasfreiheit der übrigen Skills fehlen (Etappen 3–5).

## R14: edit – Umfang Startseite

Status: confirmed
Basis: D-06
Acceptance: `edit` ändert ausschließlich die Startseite `src/pages/index.astro` einer Site vom Typ `astro-static` auf konkreten Auftrag (Startseite gestalten oder genau einen benannten Text/Abschnitt ändern); Blog, andere Seiten, neue Sites, Formulare und Veröffentlichung sind nicht Teil des Skills und werden nicht ausgeführt, sondern benannt.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 5).

## R16: publish – ehrlicher Platzhalter

Status: confirmed
Basis: D-06
Acceptance: `publish` hat kein Skript und keine Veröffentlichungsfunktion; der Skilltext sagt eindeutig, dass Veröffentlichen nicht verfügbar ist, und behauptet nie, eine Veröffentlichung sei möglich, vorbereitet oder erfolgt.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 5).

## R18: Dokumentation Deutsch und Englisch

Status: confirmed
Basis: D-11
Acceptance: Die Dokumentation liegt auf Deutsch und Englisch vor; Deutsch ist die Standardsprache.
Evidenzstatus: Das Gerüst `README.md`, `README.en.md`, `docs/de/`, `docs/en/` aus dem Skeleton ist inhaltlich nicht angepasst; Source und Test noch nicht vorhanden (Etappe 6).

## R20: Verteilung nach Manager-Vertrag

Status: confirmed
Basis: D-07, `AGENTS.md`/`docs/architecture.md`
Acceptance: `plugin.json` ist kanonisch und trägt keine Version; das Host-Manifest wird daraus abgeleitet und weist keinen Drift auf; das Repository enthält keine Marketplace-Kataloge und keine ZIP-Verteilung.
Source: scripts/plugin.py
Source: scripts/verify.py
Test: tests/contracts/test_structure.py
Test: tests/contracts/test_shared_runtime_contract.py
Evidenzstatus: Belege sind Strukturprüfungen (Identität `website`, keine Version, abgeleitetes Host-Manifest ohne Drift laut `scripts/plugin.py check`, keine Kataloge); sie belegen keine Produktabnahme und keinen Hostimport.

## R5: Manifest-Vertrag

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regel 8), D-05, D-12
Acceptance: Jede Operation, die ein vorhandenes Websiteprojekt verwendet (`preview`, `optimize`, `edit`, `setup adopt|verify` und `setup create|plan` in einem Projekt mit Manifest), validiert `.project/specs/zyris-website.json` gegen das eigene Schema des Plugins (einziger Typ `astro-static`), nie gegen eine lockerere Projektkopie; dort muss die Schema-Kopie des Projekts existieren und gültiges JSON sein und wird von `preview`, `optimize`, `edit` und `setup verify` nicht verändert, und ein ungültiges Manifest stoppt vor Build, Installation, Bericht, Launch-Eintrag und Prozessstart; `setup create` für einen neuen Projektzustand (kein Manifest und/oder keine Schema-Kopie) legt die Schema-Kopie nur bei Fehlen an, **legt ein fehlendes Manifest selbst an** (nach dem aktuellen Plugin-Schema, mit den bestätigten Angaben der neuen Site, ohne bestehende Dateien zu überschreiben und ohne unbekannte fachliche Angaben zu erfinden) und validiert das entstehende Manifest gegen das Plugin-Schema, bevor geschrieben wird; `publish` benötigt kein Projektmanifest und führt keine Projektprüfung aus.
Initialisierungsregel (D-13, Feldbelegung D-16): `setup create` schreibt `$schema` = `./website.schema.json`, `version` = 1 und eine Komponente mit `name` = Domain, `path` = angegebener Pfad, sonst `sites/<domain>`, `type` = `astro-static`, `title` = angegebener Titel, sonst Domain, `aliases` = angegebene Aliase, sonst `[]`, `port` = ausdrücklicher Port, sonst automatisch (4321 im leeren Projekt, sonst höchster effektiver Port + 1; effektiv = expliziter Port oder 4321 + Position; Kollisionen werden abgelehnt, ein automatischer Port außerhalb 1024–65535 stoppt mit dem Hinweis auf `--port`), `environment` nur bei ausdrücklicher Angabe. Vorhandene Einträge werden nie umgeschrieben. Schemakopie des Projekts: `.project/specs/website.schema.json` (D-17). Herleitung: `docs/migration/setup-init.md`.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/unit/setup/test_schema.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Evidenzstatus (das Plugin-Schema `skills/_shared/resources/website.schema.json` ist Ressource, kein Code, und steht deshalb nicht als `Source:`): Etappe 2 ergänzt für `setup`: Initialisierung eines neuen Projekts mit Feldbelegung, explizite und automatische Ports (leer, höchster expliziter, abgeleiteter Port, Kollision mit abgeleitetem Port, Bereichsgrenzen, kein stiller Überlauf), Erhalt vorhandener Komponenten, Schemakopie fehlt/identisch/fremd/beschädigt, Stopp ungültiger Manifeste vor Installation/Build/Schreiben in `setup`. Fehlend: Stopp je Einstiegspunkt in `preview`, `optimize`, `edit` (Etappen 3–5). Teilbeleg aus Etappe 1: Validierung gegen das Plugin-Schema (gelockerte oder fremde Projektkopie bestimmt den Vertrag nicht, fehlende/kaputte Kopie ergibt STOP, Resolver stoppt bei ungültigem Manifest). Fehlend: Stopp vor Build/Bericht/Launch/Prozessstart je Einstiegspunkt (Etappen 2–4) und `setup create` mit Manifest-Initialisierung (Etappe 2, Vorbereitung `docs/migration/setup-init.md`).

## R6: Standortwahl

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regel 1), D-05, D-12
Acceptance: Die Website wird nie geraten; Reihenfolge: vom Nutzer genannt (Domain, Ordner, Titel, Alias) > Arbeitsverzeichnis liegt in einer Site > nur eine Site vorhanden > zuletzt in der Unterhaltung benutzte Site (mit ausgesprochener Bestätigung) > Rückfrage; eine unbekannte ausdrückliche Site ergibt STOP (Exit 1), eine mehrdeutige ASK (Exit 2) mit Optionen; `preview status` und `preview stop` verwenden die „zuletzt benutzt“-Regel nur nach Bestätigung.
Source: skills/_shared/scripts/site_common/sites.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Evidenzstatus: Resolver belegt deterministisch (Reihenfolge, unbekannt = STOP/Exit 1, mehrdeutig = ASK/Exit 2 mit Optionen, „zuletzt“ nur mit Bestätigung). Fehlend: Verwendung durch `preview status|stop` und die Skilltexte (Etappen 3–5).

## R7: Exit-Codes, Belegpflicht, Geheimnisse

Status: confirmed
Basis: Skill-Vertrag (`interfaces.md` Regeln 2–4), D-05, D-12
Acceptance: Exit 0 bedeutet Erfolg, 1 STOP (Meldung beginnt mit `STOP:`), 2 ASK; „bestanden“, „gebaut“ oder „bereit“ wird nur gemeldet, wenn die Prüfung in diesem Aufruf lief und mit 0 endete (nicht gelaufene Schritte erscheinen als nicht gelaufen, nie als bestanden); keine Geheimnisse in Dateien, Kommandozeilen, Berichten oder Ausgaben.
Source: skills/_shared/scripts/site_common/errors.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Evidenzstatus: Teilbeleg (Etappe 1): Exit-Codes und Fehlerklassen des gemeinsamen Resolvers. Belegpflicht („bestanden“ nur bei gelaufener Prüfung) und Geheimnisfreiheit je Skill fehlen (Etappen 2–5).

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
Evidenzstatus: Etappe 2: deterministisch auf fiktiven Fixtures mit Fake-`npm` belegt (create, `unchanged`, `conflict` ohne Schreiben, `plan` = Urteil des Laufs ohne Seiteneffekte, Rollback an jeder Rename-Position, `failed-partial` mit Rest, Exit-Codes, Besitzprotokoll); Template-Identität gegen das Inventar (Hashgleichheit bzw. explizite Änderungsliste). Echte `npm install`-/Build-Läufe: `tests/external/setup/test_real_npm.py`, außerhalb der Standardschichten, nur über `scripts/run_external_tests.py --approved` nach gesonderter Freigabe (NOT RUN); geerbte Umgebungsvariablen aktivieren sie nicht (Test `tests/contracts/test_external_separation.py`). Hostnachweis NOT RUN.

## R9: setup – übernehmen, prüfen, Ablehnungen

Status: confirmed
Basis: D-04, D-05, D-06, D-12
Acceptance: `setup adopt <domain>` registriert einen vorhandenen statischen Ordner und ändert keine Datei darin (Baumhash vor und nach dem Lauf gleich); blockierende Befunde (fehlende oder ungültige `package.json`, kein `build`-Skript, nicht ignorierte Build-Ausgabe, fehlender Ordner oder Symlink) ergeben `invalid` ohne Änderung, Warnungen werden gemeldet und nicht repariert; `setup verify <domain>` führt Installation, Build und Prüfung mit echten Exit-Codes aus, regeneriert und überschreibt keine Site-Datei und meldet geänderte erzeugte Dateien als `modified (kept)`; mit `--build` laufen dieselben drei Schritte; `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` ohne Operation sowie der Typ `astro` und die entfernten Docker-Optionen werden abgelehnt und nie übersetzt.
Source: skills/setup/scripts/static_setup.py
Test: tests/integration/setup/test_static_adopt.py
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/setup/test_entrypoints.py
Evidenzstatus: Etappe 2: adopt (Baumhash gleich, blockierende Befunde, Warnungen), `verify`/`--build` mit Fake-`npm` und simulierten Exit-Codes (`ran:false` für nicht gelaufene Schritte), `modified (kept)`, abgelehnte Funktionen und Optionen ohne Schreiben. Echtes `npm`: NOT RUN (siehe R8). Hostnachweis NOT RUN.

## R10: preview – Prozesssteuerung

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: Nur `control.py start|status|stop` startet, nutzt wieder oder beendet den Dev-Server; ein Prozess gilt nur bei Besitzbeweis (Protokoll, Projektwurzel, Site, Arbeitsverzeichnis, Port, PID mit gleicher Startzeit und Prozessgruppe, alle Listener der Gruppe) als eigen – Startname und Port sind nie Beweis; `start` ergibt `running-new` oder `running-reused` (kein zweiter Server) erst nach erfolgreicher HTTP-Probe, bei fremdem Listener `port-conflict` ohne Signal oder Übernahme; bei fehlenden Abhängigkeiten `needs-install`, ohne dass der Skill selbst installiert (die Person wird auf `npm install` im Site-Ordner hingewiesen); `stop` signalisiert nur nachweislich eigene Prozessgruppen; fehlende Betriebssystem-Nachweise (`ps`, `lsof`) ergeben `insufficient-evidence` ohne Schreiben, Starten oder Signalisieren; `--timeout` ist endlich, größer 0 und höchstens 600; Zustandsdateien liegen außerhalb des Repositories und werden sicher angelegt (exklusiv, ohne Symlinks, Modus 0600/0700).
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 3).

## R11: preview – Seitenprüfung und Zuständigkeit

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: `control.py inspect --expect <Text>` startet, signalisiert und übernimmt nichts, ändert Manifest und Port nicht und meldet `page-confirmed` nur, wenn kanonische Adresse und Seitenname der Site entsprechen und jeder erwartete sichtbare Text vorkommt; `page-other-site`, `page-stale`, `page-identity-only`, `page-identity-unknown` und `page-not-reachable` gelten nie als Beleg; Prozess- und Seitenergebnis werden getrennt berichtet; kein Browserwerkzeug startet einen zusätzlichen Dev-Server oder wechselt den Port, Browserwerkzeuge öffnen nur die vom Controller gelieferte oder bestätigte Adresse.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 3).

## R12: optimize – Audit, Berichte, Arbeitsliste

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: `audit.py audit` baut in das git-ignorierte `dist/`, führt `seo:check` und `a11y:check` unabhängig voneinander aus, liest die echten Exit-Codes und vergleicht `git status` und Hashes aller versionierten Dateien vor und nach dem Lauf; Ergebnis ist `clean`, `clean-with-warnings`, `errors`, `incomplete` (fehlendes Werkzeug, Abhängigkeit, Lockfile, Build oder unlesbare Ausgabe, nie als sauber gemeldet) oder `readonly-violated`; der Lauf installiert nie (auch nicht in einer Kopie), committet nie und ändert keinen Site-Inhalt; geschrieben werden nur ein unveränderlicher Bericht unter `.project/reports/<site>/optimize/<Zeitstempel>.md` und die generierte Arbeitsliste `.project/reports/<site>/optimize.md`; Befundklassen (technischer Fehler, Warnung, redaktionelle Empfehlung) werden nie vermischt, redaktionelle Empfehlungen werden nie durch fehlende Prüfung geschlossen, manuelle Prüfpunkte stehen stets im Bericht und gelten nie als bestanden; Befunde behalten stabile IDs (Site + Kriterium + Ort), Entscheidungen bleiben über Läufe erhalten, wiedergekehrte Befunde erscheinen als `reappeared`; eine von Hand geänderte oder beschädigte Arbeitsliste stoppt den Lauf vor dem Bauen.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 4).

## R13: optimize – Entscheidungen und Umsetzung

Status: confirmed
Basis: D-04, D-05, D-12
Acceptance: Befundstatus sind genau `proposed`, `approved`, `deferred`, `wont-do`; `decide` ändert nur die Entscheidung, eine bereits entschiedene Sache nur mit `--change`; `apply` setzt nur freigegebene, nicht veraltete Vorschläge mit mechanischem `edit` um (Suchtext genau einmal, nur in einer versionierten Datei der Site), lehnt alles andere ab, installiert nie und führt die Neuprüfung selbst aus; ein Befund wandert nur in die Historie, wenn ein vollständiger Lauf nach erfolgreichem Build ihn nicht mehr meldet; bei Fehlschlag oder unvollständiger Prüfung bleibt er offen und freigegeben mit Grund; Vorschläge erfinden keine Fakten, Quellen, Bewertungen oder strukturierten Daten für nicht sichtbare Inhalte und versprechen kein Ranking.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 4).

## R15: edit – Schutz und Abschlussaussage

Status: confirmed
Basis: D-04, D-05, D-06, D-12
Acceptance: `begin` sichert HEAD, `git status` mit unversionierten Dateien und das Original der Zieldatei in einem eigenen Sicherungsordner außerhalb des Repositories; `write` und `replace` schreiben atomar nur bei erwartetem Hash und weisen jeden anderen Pfad, Traversal und Symlinks ab; eine zwischenzeitlich geänderte, entfernte oder durch Symlink ersetzte Datei ergibt `conflict` ohne Überschreiben; `check` führt `npm run build` und `npm run check` mit echten Exit-Codes aus, ist nur für den geprüften Inhalt gültig, höchstens zwei Reparaturrunden; `finish` meldet `complete` nur nach bestandenem Build und Check und tatsächlich durchgeführter Sichtprüfung, sonst „technically checked, visual check open“ (auch wenn kein Browserwerkzeug verfügbar ist); bestehende uncommittete Änderungen anderer bleiben unberührt; `edit` installiert nie Abhängigkeiten, committet nie und schreibt nie unter `.project/reports/`, in Regeln, Marken-, Prüfskript-, `package.json`-, Lockfile-, Manifest- oder Besitzprotokolldateien.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 5).

## R17: Kommunikation mit der Person

Status: confirmed
Basis: D-04, D-05 (`communication.md`), D-12
Acceptance: Der Block „Working with the person“ steht in allen fünf `SKILL.md` textgleich; er verlangt Antwort in der Sprache der Person, eigenständiges Erledigen des Auftrags, Rückfragen nur bei ergebnisrelevanten Lücken, eine kurze Schlussantwort ohne technische Details (Prozess-IDs, Ports, Exit-Codes, Hashes, Diffs) und dass eine fehlende Pflichtprüfung nie nachträglich zu „optional“ umgedeutet wird.
Source: skills/_shared/references/communication.md
Test: tests/contracts/test_setup_contract.py
Evidenzstatus: Die Referenz (Block `user-communication`) ist byte-gleich übernommen (Hash gegen Inventar geprüft); der Block steht seit Etappe 2 textgleich in `skills/setup/SKILL.md` (Textgleichheitstest); die übrigen vier `SKILL.md` fehlen (Etappen 3–5); eine Textprüfung beweist kein Modellverhalten.

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
Evidenzstatus: Test-Runner vorhanden; Etappe 2 ergänzt `setup`-Tests (unit/integration/contracts, fiktive Fixtures, Fake-`npm`); die echten npm-Tests liegen separat und sind im Standardlauf ausgeschlossen. Etappe 1 liefert deterministische Tests für gemeinsame Module und das Basiswerkzeug auf fiktiven Fixtures in Temp-Verzeichnissen. Tests der Skills, `behavior`/`native` fehlen (NOT RUN).

## R21: Projektdatenformate im Einzelnen

Status: confirmed
Basis: D-08 (Konkretisierung von R4), D-12
Acceptance: Unverändert bleiben Manifest `.project/specs/zyris-website.json`, Besitzprotokoll `.project/specs/zyris-website.managed.json` sowie Berichte und Arbeitsliste unter `.project/reports/<site>/` samt deren Formatmarkern; abgelehnt werden der Typ `astro` und die Felder `serve`, `registry`, `retention`, `dockerfile` mit konkretem Grund vor jedem Schreibzugriff, ohne Inferenz oder Migration.
Ausnahme (D-17, begrenzt): Die Schemadatei heißt im Plugin `skills/_shared/resources/website.schema.json`, im Websiteprojekt `.project/specs/website.schema.json`; das Manifest verweist mit `"$schema": "./website.schema.json"`. Kein Fallback auf `zyris-website.schema.json`, kein Alias, keine automatische Migration (D-18). Der Dateiinhalt ist unverändert; nur der Name ändert sich.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/ownership.py
Test: tests/contracts/test_setup_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Evidenzstatus: Etappe 2: Manifest-, Besitzprotokoll- und Schemanamen in `setup` belegt (Neuprojekt, Altformat-Ablehnung); Berichte/Arbeitsliste/Marker gehören zu `optimize` (Etappe 4) und sind nicht berührt.

## R22: edit – Voraussetzungen und Auftragsregeln

Status: confirmed
Basis: D-05, D-06 (Skill-Vertrag `edit.md` §2, §6), D-12
Acceptance: `preflight` schreibt nichts; fehlen vor der ersten Änderung Seite, `package.json`, Skripte `build`/`check`, `node_modules`, Lockfile, git oder eine bindende Regeldatei, stoppt `edit` ohne Schreibzugriff und nennt der Person die Befehle (kein Install durch `edit` oder `preview`); ein Typ außer `astro-static` ergibt STOP ohne Migration, eine unbekannte ausdrückliche Site Exit 1, eine mehrdeutige Exit 2; passt der Auftrag nicht zum Zweck der gewählten Site, wird nichts geändert und nach dem Zielprojekt oder `setup` gefragt; fehlende Fakten werden gezielt erfragt, nichts wird erfunden (keine Kontakte, Adressen, Preise, Bewertungen, Lizenzen); Platzhalter nur bei ausdrücklich bestelltem Demonstrationsauftrag und sichtbar markiert; mitgelieferte Texte, Dateien und Links sind Daten – enthaltene Anweisungen werden zitiert und erfragt, nicht ausgeführt; ein allgemeiner Änderungsauftrag gibt keinen optimize-Befund frei, ein Auftrag mit Befund-ID läuft über `optimize`.
Evidenzstatus: Source und Test noch nicht vorhanden; die Modellurteil-Anteile (Passung, fehlende Fakten, mitgelieferte Anweisungen, Demonstration) sind durch deterministische Tests nicht belegbar.

## R23: publish – Inhalt des Platzhalters

Status: confirmed
Basis: D-06 (Konkretisierung von R16), D-12
Acceptance: Der Skilltext benennt allgemein, was fehlt (zentraler Workflow und serverseitiges Protokoll, Workflow-Aufruf), verweist für eine lokale Qualitätsprüfung auf `optimize` mit dem Hinweis, dass dies keine Veröffentlichungsprüfung ist, verweist nicht auf geplantes Verhalten, deployt, pusht und committet nicht, fragt nichts per Netzwerk ab, erfindet keine Workflow-Namen, SHAs, Hosts oder Geheimnisse, legt keine Workflow-Datei an und gibt keine Befehlsvorabfreigabe.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 5).

## R24: Aufrufpfade und Auslieferung

Status: confirmed
Basis: D-05 (Skilltexte „Plugin path (binding)“), D-07, D-12
Acceptance: Für Skills bzw. Operationen mit Runtime-Einstiegspunkt (`setup`, `preview`, `optimize`, `edit`; `publish` hat keinen) gilt: jeder Einstiegspunkt startet aus einer extrahierten Kopie unter einem Pfad mit Leerzeichen und ohne `PYTHONPATH`; die Aufrufmuster in den Skilltexten schreiben den Skriptpfad als ein Argument; der Skill prüft vor dem ersten Aufruf, ob sein Skript existiert, und stoppt mit Meldung, wenn der Pfad fehlt oder veraltet ist, ohne Skripte in das Websiteprojekt zu kopieren; für `publish` gibt es keine Skript-, Aufruf- oder Existenzprüfung; die Runtime schreibt keinen Zustand in das installierte Plugin; nur Python-Standardbibliothek.
Source: skills/_shared/scripts/which_site.py
Test: tests/integration/shared/test_which_site_entry.py
Source: skills/setup/SKILL.md
Source: skills/setup/references/setup.md
Test: tests/contracts/test_setup_contract.py
Test: tests/integration/setup/test_init_ports_legacy.py
Evidenzstatus: Teilbeleg. Etappe 1: gemeinsamer Resolver. Etappe 2: `setup` startet aus einer Kopie mit Leerzeichen, anderem Arbeitsverzeichnis und ohne `PYTHONPATH`, Templates und Schema kommen aus der Kopie, fehlende Ressourcen stoppen vor dem Schreiben, die Kopie bleibt unverändert; der Skilltext schreibt den Skriptpfad als ein Argument (`python3 -B`), prüft `test -f` vor dem ersten Aufruf, trennt Claude (`${CLAUDE_SKILL_DIR}`) und Codex (Pfad der geladenen `SKILL.md`), `allowed-tools` sind aus dem Aufrufmuster abgeleitet (Textprüfung, kein Hostnachweis). Fehlend: Einstiegspunkte und Aufrufmuster von `preview`, `optimize`, `edit`; Konvention: `docs/migration/host-conventions.md`; Hostdeckung NOT RUN.

## R25: Dokumentation im Einzelnen

Status: confirmed
Basis: D-11 (Konkretisierung von R18), D-12
Acceptance: `README.md` und `docs/de/` sowie `README.en.md` und `docs/en/` beschreiben dieselben Fakten ohne Widerspruch zu SCOPE und Quelltext, nennen die Grenzen (Platzhalter `publish`, Startseitenumfang von `edit`, getrennte Hostnachweise, bekannte Einschränkung zwischen `edit` und `setup`), enthalten die Installation nach dem Manager-Vertrag und duplizieren keine maßgeblichen Produktfakten.
Evidenzstatus: Source und Test noch nicht vorhanden (Etappe 6).

## R26: Vollständigkeit der Migration

Status: confirmed
Basis: D-03, D-04, D-12
Acceptance: Jede Datei von `docs/migration/source-inventory.json` ist im Ziel entweder byte-gleich übernommen (Hashgleichheit), absichtlich angepasst (in einer expliziten Änderungsliste mit begrenztem Diff) oder bewusst nicht übernommen (mit Grund); die Quelle `www.draftmode` bleibt unverändert; Abweichungen der Quelle von der Basis werden vor jeder Etappe gemeldet, nicht still übernommen.
Source: scripts/migration_baseline.py
Test: tests/unit/test_migration_baseline.py
Evidenzstatus: Prüfwerkzeug und Änderungsliste (`docs/migration/changes.md`) vorhanden; Vollständigkeit über alle Inventardateien ist erst nach Etappe 6 prüfbar (Rest zurückgestellt).

## Bekannte Einschränkung: edit und setup

Nach einer `edit`-Änderung an einer von `setup` erzeugten Datei stimmt der im Besitzprotokoll gespeicherte Hash nicht mehr. Heute ergibt dann `setup create` für diese Site `conflict` ohne Schreibzugriff, und `setup verify` behält die Datei (`modified (kept)`). `setup.md` §5 und `edit.md` §4.6/§12 weisen die Zuständigkeit für die Koexistenz beide `setup` zu; eine zukünftige Regel zum neuen Aufsetzen der Hashes (Rebaselining) ist dort nicht festgelegt, `setup update` und `--adopt-edits` sind nicht umgesetzt. Diese Migration führt keine solche Regel ein; die Einschränkung wird dokumentiert (R25).

## Offene Punkte nach Kategorie

Details, Fundstellen und Begründungen: `docs/migration/decisions.md`.

- **Durch Nutzerentscheidung oder explizite Vertragsstatus bereits beantwortet:** V1 (preview: spätere, als implementiert markierte Abschnitte §11–13 gelten; das Host-Tool-Zielmodell ist geplant und ausgeschlossen), V2 (optimize: isolierte Kopie ist geplant und ausgeschlossen; `apply` und Audit installieren nie), V4 (publish bleibt Platzhalter), V5 (siehe „Bekannte Einschränkung“), Q7 (nur normatives Verhalten wird übernommen).
- **Technische Implementierungsentscheidungen** (ohne Nutzerentscheidung): V3 gemeinsame Module (in Etappe 1 entschieden: Paket `site_common`, `docs/migration/changes.md`), Q1/Q2 Aufrufpfade und Claude-Freigabemuster (Konvention in Etappe 1 festgelegt, Einzelmuster mit den Skills: `docs/migration/host-conventions.md`), Q4 neutrale Meldungen (umgesetzt in den gemeinsamen Modulen), Q5 interne Zustandsnamen (unverändert), Q6 Testklassifikation, Q8 Mindestversionen (Python ≥ 3.10).
- **Echte fachliche Unklarheit / Nutzerentscheidung:** keine offene Freigabefrage. Q10 ist durch D-14 beantwortet: Preview-Tests dürfen eigene lokale Prozesse starten, `127.0.0.1`-Ports verwenden und ausschließlich eigene, eindeutig identifizierte Testprozesse bzw. Prozessgruppen beenden; externe Netzwerkzugriffe für Tests bleiben ausgeschlossen. Die Felder der Manifest-Initialisierung sind durch D-16 entschieden (`docs/migration/setup-init.md`).
- **Fehlende Ausführungs- und Hostnachweise** (bis zur Ausführung `NOT RUN`): Claude- und Codex-Verhalten je Skill; Ersetzung von `${CLAUDE_PLUGIN_ROOT}` und Wirkung von `allowed-tools`; Verfügbarkeit von Browserwerkzeugen je Host; ob beide Hosts `skills/_shared/` mitinstallieren.

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
