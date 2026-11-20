# Produktzielbild

Status: confirmed

Stand: 2026-11-20. Dieses Dokument beschreibt das bestätigte Soll des Plugins, keine Zusammenfassung des Codes. Der Nachweisstand steht nicht hier; offene, nicht belegte Punkte sind im Abschnitt „Nicht belegt (NOT RUN)“ benannt. Neue fachliche Details gelten erst nach ausdrücklicher Bestätigung als Soll.

## Zweck

Das Plugin **Website Manager** (Plugin-Name `website-manager`, Anzeigename „Website Manager“) erstellt, verwaltet und pflegt statische Astro-Websites in einem Website-Projekt (`sites/<site-id>/`) mit acht Skills:

- `plugin-website`: geführter Einstieg
- `setup`: anlegen, übernehmen, planen, prüfen, Domain nachtragen
- `brief`: inhaltliche Richtung
- `design`: Startseiten-Prototypen und Freigabe
- `preview`: lokal ansehen
- `optimize`: SEO- und Barrierefreiheits-Audit mit Berichten und Arbeitsliste
- `edit`: Startseite gestalten oder einen Text ändern
- `publish`: ehrlicher Platzhalter

Zielhosts sind Claude und Codex. Dieses Repository ist die alleinige Entwicklungsquelle.

## Nicht-Ziele

- Keine Erweiterung um geplante Funktionen: keine Blogbearbeitung, keine weiteren Seitentypen im `edit`, kein GEO, kein Lighthouse, keine Linkgraph-Prüfung, keine isolierte Abhängigkeitskopie mit `npm ci`, keine neue Browserintegration.
- Kein `setup update`, kein `--add-missing`, `--regenerate`, `--adopt-edits`, keine Rebaselining-Funktion für Besitz-Hashes, keine Erzeugung eines Workflow-Aufrufs.
- Keine Veröffentlichung, kein Deployment, keine Schnittstelle zu `draftmode.srv`, keine Formulare.
- Keine Kompatibilitätsaliases, keine Altformat-Unterstützung und keine automatische Migration von Projektdaten.
- Keine ZIP-/GUI-Upload-Verteilung, keine Marketplace-Kataloge im Plugin-Repository.
- Keine Installation, Commits, Pushes oder Veröffentlichung sowie keine Modelltests, nativen Hosttests, GUI-Abnahme, Netzwerkzugriffe für Tests oder Werkzeuginstallationen ohne eigene Freigabe.

## Identität, Auslieferung und Dokumentation

## R1: Plugin-Identität und Skills

Status: confirmed
Acceptance: `plugin.json` trägt den Namen `website-manager` und den Anzeigenamen „Website Manager“; unter `skills/` liegen genau die acht Skill-Ordner `plugin-website`, `setup`, `brief`, `design`, `preview`, `optimize`, `edit` und `publish`, jeder mit `SKILL.md`, dessen Frontmatter-Name dem Ordnernamen entspricht; `skills/_shared` hat keine `SKILL.md`.
Source: skills/setup/SKILL.md
Source: skills/preview/SKILL.md
Source: skills/optimize/SKILL.md
Source: skills/edit/SKILL.md
Source: skills/publish/SKILL.md
Test: tests/contracts/test_structure.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_documentation_contract.py

## R2: Zielhosts Claude und Codex

Status: confirmed
Acceptance: Claude und Codex sind Zielhosts; für jeden Host wird je Skill getrennt berichtet, was belegt ist; ein Nachweis für einen Host gilt nie für den anderen; ohne tatsächliche Ausführung wird der Hostnachweis als `NOT RUN` berichtet.
Source: skills/plugin-website/SKILL.md
Source: skills/setup/SKILL.md
Source: skills/brief/SKILL.md
Source: skills/design/SKILL.md
Source: skills/preview/SKILL.md
Source: skills/optimize/SKILL.md
Source: skills/edit/SKILL.md
Source: skills/publish/SKILL.md
Test: tests/contracts/test_documentation_contract.py

## R18: Dokumentation Deutsch und Englisch

Status: confirmed
Acceptance: Die Dokumentation liegt auf Deutsch und Englisch vor; Deutsch ist die Standardsprache.
Source: tests/contracts/test_documentation_contract.py
Test: tests/contracts/test_documentation_contract.py

## R25: Dokumentation im Einzelnen

Status: confirmed
Acceptance: `README.md` und `docs/de/` sowie `README.en.md` und `docs/en/` beschreiben dieselben Fakten ohne Widerspruch zu diesem Dokument und zum Code, nennen die Grenzen (Platzhalter `publish`, Startseitenumfang von `edit`, getrennte Hostnachweise, bekannte Einschränkung zwischen `edit` und `setup`), enthalten die Installation nach dem Manager-Vertrag und duplizieren keine maßgeblichen Produktfakten.
Source: tests/contracts/test_documentation_contract.py
Test: tests/contracts/test_documentation_contract.py

## R20: Verteilung nach Manager-Vertrag

Status: confirmed
Acceptance: `plugin.json` ist kanonisch und trägt keine Version; das Host-Manifest wird daraus abgeleitet und weist keinen Drift auf; das Repository enthält keine Marketplace-Kataloge und keine ZIP-Verteilung.
Source: scripts/plugin.py
Source: scripts/verify.py
Test: tests/contracts/test_structure.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/contracts/test_documentation_contract.py

## R34: Auslieferung benötigter Punkt-Vorlagen

Status: confirmed
Acceptance: Das erzeugte Plugin-Paket enthält die Skeleton-Vorlagen einschließlich `.gitignore.tpl` und `.gitkeep` (nur diese exakten Dateinamen, nur unterhalb eines `templates`-Ordners eines Skills); `.env*`, Schlüsseldateien, Punktordner und generierte Dateien bleiben ausgeschlossen; `setup` läuft aus dem erzeugten Paket (Claude- und Codex-Nutzlast) und erzeugt Skeleton, Ignore-Regeln und Manifest.
Source: scripts/plugin.py
Test: tests/integration/package/test_package_setup.py

## Runtime und übergreifende Regeln

## R3: Eigenständige Runtime

Status: confirmed
Acceptance: Die Runtime liegt unter `skills/<skill>/scripts/` bzw. `skills/_shared/` (ohne `SKILL.md`); sie enthält keine fest eingebauten Entwicklerpfade und keine Abhängigkeit zu fremden Checkouts, `ai.plugins` oder dem Wurzel-`scripts/`; im autorisierten Produktbetrieb liest und bearbeitet sie nur das ausdrücklich ausgewählte Websiteprojekt im Rahmen des jeweiligen Skill-Vertrags.
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
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/integration/optimize/test_isolated_copy.py

## R4: Nur aktuelle Formate

Status: confirmed
Acceptance: Es gibt nur das aktuelle Format: keine Aliase für Plugin- oder Skill-Namen, keine Altformat-Erkennung, keine Fallback-Suche und keine automatische Migration; nicht unterstützte Formen (Typ `astro`, entfernte Felder, ungültiges Manifest) werden mit konkretem Grund vor jedem Schreibzugriff, Build, Prozessstart und jeder Installation abgelehnt, Nutzerdaten bleiben byte-gleich.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/preview/test_manifest_contract.py
Test: tests/integration/optimize/test_manifest_contract.py
Test: tests/integration/edit/test_manifest_contract.py

## R7: Exit-Codes, Belegpflicht, Geheimnisse

Status: confirmed
Acceptance: Exit 0 bedeutet Erfolg, 1 STOP (Meldung beginnt mit `STOP:`), 2 ASK; „bestanden“, „gebaut“ oder „bereit“ wird nur gemeldet, wenn die Prüfung in diesem Aufruf lief und mit 0 endete (nicht gelaufene Schritte erscheinen als nicht gelaufen, nie als bestanden); Dateisystem- und Prozessfehler enden als `STOP:` statt Traceback; keine Geheimnisse in Dateien, Kommandozeilen, Berichten oder Ausgaben: Prüfausgaben werden als Textende (2000 Zeichen) wiedergegeben, bekannte Geheimnisfelder (Namen mit TOKEN, SECRET, PASSWORD, PASSWD, API_KEY, AUTH, auch `Authorization`/`Proxy-Authorization`) werden vor der Kürzung geschwärzt (quotierte Werte vollständig, andere Werte samt Schema bis Zeilenende); das ist eine Musterliste, keine vollständige Erkennung.
Source: skills/_shared/scripts/site_common/errors.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/preview/test_control.py
Test: tests/integration/optimize/test_audit.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/integration/edit/test_checks_and_finish.py

## R17: Kommunikation mit der Person

Status: confirmed
Acceptance: Der Block „Working with the person“ steht in allen fünf `SKILL.md` der Funktions-Skills (`setup`, `preview`, `optimize`, `edit`, `publish`) textgleich zur gemeinsamen Referenz; er verlangt Antwort in der Sprache der Person, eigenständiges Erledigen des Auftrags, Rückfragen nur bei ergebnisrelevanten Lücken, eine kurze Schlussantwort ohne technische Details (Prozess-IDs, Ports, Exit-Codes, Hashes, Diffs) und dass eine fehlende Pflichtprüfung nie nachträglich zu „optional“ umgedeutet wird.
Source: skills/_shared/references/communication.md
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/contracts/test_edit_contract.py
Test: tests/contracts/test_publish_contract.py

## R19: Tests und Nachweise

Status: confirmed
Acceptance: Deterministische Tests liegen unter `tests/unit/`, `tests/integration/`, `tests/contracts/` auf fiktiven Fixtures in isolierten Verzeichnissen; kein Test liest echte Website-Inhalte oder private Projektdaten; Tests werden nach tatsächlichem Verhalten klassifiziert (Netzwerk-/`npm`-Tests sind nicht automatisch native Hosttests); Preview-Tests dürfen eigene lokale Prozesse starten, `127.0.0.1`-Ports verwenden und ausschließlich eigene, eindeutig identifizierte Testprozesse beenden; echte `npm`-Tests liegen unter `tests/external/` und laufen nur nach gesonderter Freigabe; Tests mit Modell, GUI oder nativem Host liegen unter `tests/behavior/` bzw. `tests/native/` und laufen nie im Standardlauf; fehlende oder nicht gelaufene Suiten melden `NOT RUN`, nie Abnahme; strukturelle und Textprüfungen gelten nicht als Verhaltensnachweis.
Source: scripts/run_tests.py
Test: tests/contracts/test_external_separation.py
Test: tests/contracts/test_shared_runtime_contract.py
Test: tests/unit/shared/test_manifest.py
Test: tests/integration/shared/test_which_site_entry.py

## R24: Aufrufpfade und Auslieferung

Status: confirmed
Acceptance: Für Skills mit Runtime-Einstiegspunkt (`setup`, `preview`, `optimize`, `edit`; `publish` hat keinen) gilt: jeder Einstiegspunkt startet aus einer extrahierten Kopie unter einem Pfad mit Leerzeichen, anderem Arbeitsverzeichnis und ohne `PYTHONPATH`; die Aufrufmuster in den Skilltexten schreiben den Skriptpfad als ein Argument; der Skill prüft vor dem ersten Aufruf, ob sein Skript existiert, und stoppt mit Meldung, wenn der Pfad fehlt oder veraltet ist, ohne Skripte in das Websiteprojekt zu kopieren; Claude- und Codex-Pfadbehandlung sind getrennt; die `allowed-tools`-Muster decken genau die Aufrufmuster; die Runtime schreibt keinen Zustand in das installierte Plugin und nutzt nur die Python-Standardbibliothek; `publish` hat keine Skript-, Aufruf- oder Existenzprüfung.
Source: skills/_shared/scripts/which_site.py
Source: skills/setup/SKILL.md
Source: skills/preview/SKILL.md
Source: skills/optimize/SKILL.md
Source: skills/edit/SKILL.md
Source: skills/edit/scripts/edit.py
Source: skills/publish/SKILL.md
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_preview_contract.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/contracts/test_edit_contract.py
Test: tests/contracts/test_publish_contract.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/integration/optimize/test_isolated_copy.py
Test: tests/integration/edit/test_isolated_copy.py

## Projektformat und Zustand

## R5: Manifest-Vertrag

Status: confirmed
Acceptance: Jede Operation, die ein vorhandenes Websiteprojekt verwendet (`preview`, `optimize`, `edit`, `setup adopt|verify` sowie `setup create|plan` in einem Projekt mit Manifest), validiert `.project/specs/website.json` gegen das eigene Schema des Plugins (einziger Typ `astro-static`), nie gegen eine lockerere Projektkopie; die Schema-Kopie des Projekts muss existieren und gültiges JSON sein und wird von `preview`, `optimize`, `edit` und `setup verify` nicht verändert; ein ungültiges Manifest stoppt vor Build, Installation, Bericht, Launch-Eintrag und Prozessstart, auch bei Folgebefehlen; `setup create` für einen neuen Projektzustand legt die Schema-Kopie nur bei Fehlen an, legt ein fehlendes Manifest selbst an (nach dem aktuellen Plugin-Schema, ohne bestehende Dateien zu überschreiben und ohne unbekannte fachliche Angaben zu erfinden) und validiert es vor dem Schreiben; `publish` benötigt kein Projektmanifest. Feldbelegung von `setup create`: `$schema` = `./website.schema.json`, `version` = 2 (R29), eine Komponente mit `name` = Site-ID, `path` = angegebener Pfad, sonst `sites/<site-id>`, `type` = `astro-static`, `title` = angegebener Titel, sonst Site-ID, `aliases` = angegebene Aliase, sonst `[]`, `domain` nur bei ausdrücklicher Angabe, `port` = ausdrücklicher Port, sonst automatisch (4321 im leeren Projekt, sonst höchster effektiver Port + 1; effektiv = expliziter Port oder 4321 + Position; Kollisionen werden abgelehnt, ein automatischer Port außerhalb 1024–65535 stoppt mit dem Hinweis auf `--port`), `environment` nur bei ausdrücklicher Angabe; vorhandene Einträge werden nie umgeschrieben. Die Schemakopie des Projekts liegt unter `.project/specs/website.schema.json`.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/manifest.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_manifest.py
Test: tests/unit/setup/test_schema.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/integration/setup/test_manifest_contract.py
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/preview/test_manifest_contract.py
Test: tests/integration/optimize/test_manifest_contract.py
Test: tests/integration/edit/test_manifest_contract.py

## R29: Manifest Version 2, Site-ID und optionale Domain

Status: confirmed
Acceptance: Das Manifest hat `version` 2. `name` ist die stabile interne Site-ID (zugleich Ordnername und Besitzschlüssel), keine Domain; `domain` ist optional und enthält ausschließlich eine ausdrücklich angegebene Domain; fehlendes `domain` heißt „Domain noch nicht festgelegt“. Aus `name`, `site.ts` oder `astro.config.mjs` wird nie eine Domain abgeleitet oder übernommen. Ohne Domain entstehen keine absoluten Canonical-, Social-, Sitemap- oder robots-Adressen und keine Platzhalterdomain. `setup create|adopt <site-id> [--domain D]`; `setup set-domain <site-id> <domain>` trägt eine Domain später nach (ID, Pfad, Port und Zuordnungen bleiben; nur unveränderte erzeugte Dateien werden angepasst, sonst Konflikt ohne Schreibzugriff). Manifest und domainabhängige Konfiguration müssen übereinstimmen (`site_common/consistency.py`: Textprüfung ohne Ausführung von Code, Kommentare zählen nicht, Symlinks werden nie gefolgt; nicht erkennbare oder dynamische Konfiguration ist „nicht zuverlässig prüfbar“, nie „domainlos“); Widersprüche stoppen `setup` (Plan und `verify`), `preview` (Startpfade), `optimize`, `edit` und den Resolver vor Änderungen, Builds und Prozessen und werden konkret gemeldet, nie repariert.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/_shared/scripts/site_common/consistency.py
Source: skills/setup/scripts/static_setup.py
Test: tests/unit/shared/test_consistency.py
Test: tests/integration/setup/test_manifest_v2.py

## R21: Projektdatenformate

Status: confirmed
Acceptance: Das Manifest `.project/specs/website.json`, die Schemadatei (Plugin: `skills/_shared/resources/website.schema.json`, Projekt: `.project/specs/website.schema.json`, Verweis `"$schema": "./website.schema.json"`), das Besitzprotokoll `.project/specs/website.managed.json` sowie Berichte und Arbeitsliste unter `.project/reports/<site>/` samt Formatmarkern (`website-manager-optimize:*`) sind die einzigen Projektdatenformate; abgelehnt werden der Typ `astro` und die Felder `serve`, `registry`, `retention`, `dockerfile` mit konkretem Grund vor jedem Schreibzugriff, ohne Inferenz oder Migration; Manifest und Besitzprotokoll werden von `optimize` nie geschrieben, `edit` schreibt weder Manifest, Schemakopie, Besitzprotokoll noch Berichte.
Source: skills/_shared/scripts/site_common/manifest.py
Source: skills/setup/scripts/ownership.py
Test: tests/contracts/test_setup_contract.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/integration/edit/test_manifest_contract.py

## R6: Standortwahl

Status: confirmed
Acceptance: Die Website wird nie geraten; Reihenfolge: vom Nutzer genannt (Site-ID, Domain, Ordner, Titel, Alias) > Arbeitsverzeichnis liegt in einer Site > nur eine Site vorhanden > zuletzt in der Unterhaltung benutzte Site (mit ausgesprochener Bestätigung) > Rückfrage; eine unbekannte ausdrückliche Site ergibt STOP (Exit 1), eine mehrdeutige ASK (Exit 2) mit Optionen; `preview status` und `preview stop` verwenden die „zuletzt benutzt“-Regel nur nach Bestätigung; alle Skills mit Standortwahl verwenden denselben gemeinsamen Resolver.
Source: skills/_shared/scripts/site_common/sites.py
Test: tests/unit/shared/test_sites.py
Test: tests/integration/shared/test_which_site_entry.py
Test: tests/unit/preview/test_launch.py
Test: tests/integration/preview/test_control.py
Test: tests/integration/optimize/test_manifest_contract.py
Test: tests/integration/edit/test_prerequisites.py

## R27: Persistente Operatorsprache pro Projekt

Status: confirmed
Acceptance: Alle Skills lesen vor fachlichen Rückfragen oder Aktionen die Operatorsprache aus dem ausgewählten Projekt. Fehlt sie, wird zuerst allein nach der bevorzugten Sprache gefragt und die explizite Antwort persistiert. Spätere Aufrufe und neue Sitzungen verwenden diese Sprache ohne erneute Frage. Ein ausdrücklicher Änderungswunsch aktualisiert nur dieses Projekt. Website- und Dokumentationssprache bleiben unabhängig. Ungültige Formate werden ohne Überschreiben abgelehnt. Das bestimmt die Sprachauswahl von R17; der übrige Kommunikationsvertrag bleibt erhalten. Der `publish`-Platzhalter nutzt dafür ausschließlich den gemeinsamen Helper und den gewählten Projektordner und liest weder Manifest noch Site-Inhalte.
Source: skills/_shared/references/operator-language.md
Source: skills/_shared/scripts/operator_language.py
Source: skills/setup/SKILL.md
Test: tests/integration/shared/test_operator_language.py
Test: tests/behavior/operator_language_acceptance.md

## R28: Lokale Website-Arbeit ohne Git

Status: confirmed
Acceptance: `setup`, `preview`, `edit` und `optimize` benötigen weder Git-Programm noch Repository, Commit oder Remote und führen keine Git-Abfragen oder Initialisierung aus. Die Projektwurzel ist der ausdrücklich ausgewählte Ordner (`--root`, sonst Arbeitsverzeichnis), auch innerhalb eines übergeordneten Repositorys. Alle Setup-Operationen einschließlich `plan`, `adopt` und `verify` funktionieren damit. Projektlokale `.gitignore`-Regeln bestimmen weiterhin ignorierte Build-Ausgaben; globale Git-Konfiguration ist nicht erforderlich. `edit` sichert Original und Dateisnapshot, prüft erwartete Hashes und meldet Dateiänderungen. `optimize` erkennt hinzugefügte, entfernte und geänderte Quelldateien auch ohne Versionierung; `apply` darf freigegebene, nicht ignorierte Quelldateien bearbeiten. Snapshots folgen keinen Symlinks und lesen keine ignorierten oder privaten Dateien. Edit-Sitzungen ohne Dateisnapshot werden vor Änderungen mit Diagnose abgelehnt und bleiben erhalten. `publish` bleibt der Platzhalter ohne Git-Vorprüfung; eine Git-Pflicht gehört erst zu einer später separat spezifizierten Veröffentlichungsfunktion.
Source: skills/_shared/scripts/site_common/project_files.py
Source: skills/setup/scripts/static_setup.py
Source: skills/edit/scripts/edit.py
Source: skills/optimize/scripts/audit.py
Test: tests/unit/shared/test_project_files.py
Test: tests/integration/setup/test_without_git.py
Test: tests/integration/edit/test_without_git.py
Test: tests/integration/optimize/test_without_git.py

## R33: Zustandsvertrag und Wiederaufnahme

Status: confirmed
Acceptance: Der versionierte Projektzustand (`flow.json`, schema_version 1; `docs/development/guided-flow.md`) unterscheidet Setup fehlt/vollständig/widersprüchlich, Briefing fehlt/in Bearbeitung/bestätigt, Designvarianten fehlen/liegen vor/werden überarbeitet/freigegeben, Umsetzung fehlt/begonnen/abgeschlossen/veraltet/vom Nutzer geändert sowie technische und visuelle Prüfung offen/bestanden/fehlgeschlagen (gebunden an den Hash der aktuellen Startseite). Zustand und tatsächliche Artefakte (Hashes) werden gemeinsam geprüft. Änderungen am Briefing oder an einer freigegebenen Revision markieren abhängige Ergebnisse als veraltet; nichts wird gelöscht. Wiederholte Aufrufe erzeugen keine Duplikate und führen Erledigtes nicht erneut aus; beschädigte oder unbekannte Zustandsformate und Symlinks werden gemeldet und nie repariert, migriert oder überschrieben. Eine Änderung der Startseite durch die Person zwischenzeitlich wird erkannt (Verweigerung ohne Überschreiben).
Source: skills/_shared/scripts/site_common/flowstate.py
Source: skills/_shared/scripts/flow.py
Test: tests/integration/flow/test_flow_state.py
Test: tests/integration/flow/test_flow_review_regressions.py

## Skill setup

## R8: setup – anlegen, planen, Besitzprotokoll

Status: confirmed
Acceptance: `setup create <site-id> --type astro-static` schreibt in einen fehlenden oder leeren `sites/<site-id>/` das vollständige statische Template (keine Docker-/Caddy-/Workflow-Dateien), registriert die Komponente, legt die Schema-Kopie nur bei Fehlen an, ergänzt `.tmp/` samt `.gitignore`-Eintrag und schreibt das Besitzprotokoll; `plan create|adopt` schreibt, installiert und baut nichts und liefert dasselbe Urteil wie der echte Lauf; identische Wiederholung ergibt `unchanged` ohne Schreibzugriff; Abweichungen, geänderte oder fehlende erzeugte Dateien und fremde Schema-Kopien ergeben `conflict` ohne Schreibzugriff; ein Schreibfehler stellt alle Dateien und die Registrierung wieder her (`failed-rolled-back`, sonst `failed-partial` mit Rest); Zustände und Exit-Codes: `created|adopted|verified|unchanged|planned` = 0, `needs-input` = 2, alles andere = 1.
Source: skills/setup/scripts/site_setup.py
Source: skills/setup/scripts/static_setup.py
Source: skills/setup/scripts/ownership.py
Source: skills/setup/references/setup.md
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/setup/test_review_fixes.py
Test: tests/contracts/test_setup_contract.py
Test: tests/contracts/test_external_separation.py
Test: tests/external/website/test_real_tools.py

## R9: setup – übernehmen, prüfen, Ablehnungen

Status: confirmed
Acceptance: `setup adopt <site-id>` registriert einen vorhandenen statischen Ordner und ändert keine Datei darin (Baumhash vor und nach dem Lauf gleich); blockierende Befunde (fehlende oder ungültige `package.json`, kein `build`-Skript, nicht ignorierte Build-Ausgabe, fehlender Ordner oder Symlink) ergeben `invalid` ohne Änderung, Warnungen werden gemeldet und nicht repariert; `setup verify <site-id>` führt Installation, Build und Prüfung mit echten Exit-Codes aus, regeneriert und überschreibt keine Site-Datei und meldet geänderte erzeugte Dateien als `modified (kept)`; mit `--build` laufen dieselben drei Schritte; `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` ohne Operation sowie der Typ `astro` und die entfernten Docker-Optionen werden abgelehnt und nie übersetzt.
Source: skills/setup/scripts/static_setup.py
Test: tests/integration/setup/test_static_adopt.py
Test: tests/integration/setup/test_static_create.py
Test: tests/integration/setup/test_entrypoints.py

## Skill preview

## R10: preview – Prozesssteuerung

Status: confirmed
Acceptance: Nur `control.py start|status|stop` startet, nutzt wieder oder beendet den Dev-Server; ein Prozess gilt nur bei Besitzbeweis (Protokoll, Projektwurzel, Site, Arbeitsverzeichnis, Port, PID mit gleicher Startzeit und Prozessgruppe, alle Listener der Gruppe) als eigen – Startname und Port sind nie Beweis; `start` ergibt `running-new` oder `running-reused` (kein zweiter Server) erst nach erfolgreicher HTTP-Probe, bei fremdem Listener `port-conflict` ohne Signal oder Übernahme; bei fehlenden Abhängigkeiten `needs-install`, ohne dass der Skill selbst installiert (die Person wird auf `npm install` im Site-Ordner hingewiesen); `stop` signalisiert nur nachweislich eigene Prozessgruppen; fehlende Betriebssystem-Nachweise (`ps`, `lsof`) ergeben `insufficient-evidence` ohne Schreiben, Starten oder Signalisieren; `--timeout` ist endlich, größer 0 und höchstens 600; Zustandsdateien liegen außerhalb des Repositories (`<TMPDIR>/website-manager/`, überschreibbar mit `WEBSITE_MANAGER_STATE_DIR`) und werden sicher angelegt (exklusiv, ohne Symlinks, Modus 0600/0700); der Launch-Eintrag in `.claude/launch.json` heißt `website-manager-<site>`, folgt keinen Symlinks und lässt fremde Einträge unberührt.
Source: skills/preview/scripts/control.py
Source: skills/preview/scripts/preview.py
Source: skills/preview/references/preview.md
Test: tests/integration/preview/test_control.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/unit/preview/test_launch.py
Test: tests/unit/preview/test_launch_links.py
Test: tests/integration/preview/test_state_area_and_launch_links.py
Test: tests/external/website/test_real_tools.py

## R11: preview – Seitenprüfung und Zuständigkeit

Status: confirmed
Acceptance: `control.py inspect --expect <Text>` startet, signalisiert und übernimmt nichts, ändert Manifest und Port nicht und meldet `page-confirmed` nur, wenn kanonische Adresse und Seitenname der Site entsprechen und jeder erwartete sichtbare Text vorkommt; `page-other-site`, `page-stale`, `page-identity-only`, `page-identity-unknown` und `page-not-reachable` gelten nie als Beleg; Prozess- und Seitenergebnis werden getrennt berichtet; kein Browserwerkzeug startet einen zusätzlichen Dev-Server oder wechselt den Port, Browserwerkzeuge öffnen nur die vom Controller gelieferte oder bestätigte Adresse; ein visueller Erfolg wird nie ohne tatsächliche Sichtprüfung behauptet.
Source: skills/preview/scripts/control.py
Source: skills/preview/SKILL.md
Test: tests/integration/preview/test_inspect.py
Test: tests/integration/preview/test_side_effects_and_copy.py
Test: tests/contracts/test_preview_contract.py

## Skill optimize

## R12: optimize – Audit, Berichte, Arbeitsliste

Status: confirmed
Acceptance: `audit.py audit` baut in das ignorierte `dist/`, führt `seo:check` und `a11y:check` unabhängig voneinander aus, liest die echten Exit-Codes und vergleicht Pfade und Hashes der nicht ignorierten, nicht privaten Projektdateien vor und nach dem Lauf; Ergebnis ist `clean`, `clean-with-warnings`, `errors`, `incomplete` (fehlendes Werkzeug, Abhängigkeit, Lockfile, Build oder unlesbare Ausgabe, nie als sauber gemeldet) oder `readonly-violated`; der Lauf installiert nie (auch nicht in einer Kopie), committet nie und ändert keinen Site-Inhalt; geschrieben werden nur ein unveränderlicher Bericht unter `.project/reports/<site>/optimize/<Zeitstempel>.md` und die generierte Arbeitsliste `.project/reports/<site>/optimize.md`; Befundklassen (technischer Fehler, Warnung, redaktionelle Empfehlung) werden nie vermischt, redaktionelle Empfehlungen werden nie durch fehlende Prüfung geschlossen, manuelle Prüfpunkte stehen stets im Bericht und gelten nie als bestanden; Befunde behalten stabile IDs (Site + Kriterium + Ort), Entscheidungen bleiben über Läufe erhalten, wiedergekehrte Befunde erscheinen als `reappeared`; eine von Hand geänderte oder beschädigte Arbeitsliste stoppt jeden Befehl vor dem Bauen; Symlinks im Berichtsbereich und unsichere Sitenamen werden abgelehnt; Tokenmuster in Werkzeugausgaben werden im Bericht geschwärzt.
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
Test: tests/integration/optimize/test_isolated_copy.py
Test: tests/contracts/test_optimize_contract.py
Test: tests/external/website/test_real_tools.py

## R13: optimize – Entscheidungen und Umsetzung

Status: confirmed
Acceptance: Befundstatus sind genau `proposed`, `approved`, `deferred`, `wont-do`; `decide` ändert nur die Entscheidung (keinen Site-Inhalt, keinen Build), eine bereits entschiedene Sache nur mit `--change`; `apply` setzt nur freigegebene, nicht veraltete Vorschläge mit mechanischem `edit` um (Suchtext genau einmal, nur in einer nicht ignorierten Projektdatei der Site; Pfade außerhalb der Site, `..`, absolute Pfade und Symlinks werden abgelehnt), lehnt alles andere ab, installiert nie und führt die vollständige Neuprüfung selbst aus; ein geänderter Vorschlag oder Ausgangstext macht die Freigabe ungültig; ein Befund wandert nur in die Historie, wenn ein vollständiger Lauf nach erfolgreichem Build ihn nicht mehr meldet, bei Fehlschlag oder unvollständiger Prüfung bleibt er offen und freigegeben mit Grund; fremde Änderungen im Projekt bleiben erhalten; Vorschläge erfinden keine Fakten, Quellen, Bewertungen oder strukturierten Daten für nicht sichtbare Inhalte und versprechen kein Ranking.
Source: skills/optimize/scripts/audit.py
Source: skills/optimize/scripts/worklist.py
Source: skills/optimize/references/optimize.md
Source: skills/optimize/SKILL.md
Test: tests/integration/optimize/test_apply_scope.py
Test: tests/integration/optimize/test_audit.py
Test: tests/integration/optimize/test_report_and_guard.py
Test: tests/integration/optimize/test_source_state_links.py
Test: tests/contracts/test_optimize_contract.py

## Skill edit

## R14: edit – Umfang Startseite

Status: confirmed
Acceptance: `edit` ändert ausschließlich die Startseite `src/pages/index.astro` einer Site vom Typ `astro-static` auf konkreten Auftrag (Startseite gestalten oder genau einen benannten Text/Abschnitt ändern); Blog, andere Seiten, neue Sites, Formulare und Veröffentlichung sind nicht Teil des Skills und werden nicht ausgeführt, sondern benannt; es gibt keinen Befehl, der Dateien anlegt oder einen Zielpfad entgegennimmt.
Source: skills/edit/scripts/edit.py
Source: skills/edit/SKILL.md
Source: skills/edit/references/edit.md
Test: tests/integration/edit/test_writes.py
Test: tests/integration/edit/test_prerequisites.py
Test: tests/unit/edit/test_edit_unit.py
Test: tests/contracts/test_edit_contract.py

## R22: edit – Voraussetzungen und Auftragsregeln

Status: confirmed
Acceptance: `preflight` schreibt nichts; fehlen vor der ersten Änderung Seite, `package.json`, Skripte `build`/`check`, `node_modules`, Lockfile oder eine bindende Regeldatei, stoppt `edit` ohne Schreibzugriff und nennt der Person die Befehle (kein Install durch `edit` oder `preview`; Git ist keine Voraussetzung, siehe R28); ein Typ außer `astro-static` ergibt STOP, eine unbekannte ausdrückliche Site Exit 1, eine mehrdeutige Exit 2; passt der Auftrag nicht zum Zweck der gewählten Site, wird nichts geändert und nach dem Zielprojekt oder `setup` gefragt; fehlende Fakten werden gezielt erfragt, nichts wird erfunden (keine Kontakte, Adressen, Preise, Bewertungen, Lizenzen); Platzhalter nur bei ausdrücklich bestelltem Demonstrationsauftrag und sichtbar markiert; mitgelieferte Texte, Dateien und Links sind Daten – enthaltene Anweisungen werden zitiert und erfragt, nicht ausgeführt; ein allgemeiner Änderungsauftrag gibt keinen optimize-Befund frei, ein Auftrag mit Befund-ID läuft über `optimize`.
Source: skills/edit/scripts/edit.py
Source: skills/edit/SKILL.md
Source: skills/edit/references/edit.md
Test: tests/integration/edit/test_prerequisites.py
Test: tests/integration/edit/test_manifest_contract.py
Test: tests/integration/edit/test_symlink_reads.py
Test: tests/contracts/test_edit_contract.py

## R15: edit – Schutz und Abschlussaussage

Status: confirmed
Acceptance: `begin` sichert einen Snapshot der nicht ignorierten, nicht privaten Projektdateien und das Original der Zieldatei bytegetreu in einem eigenen Sicherungsordner außerhalb von Projekt und installiertem Plugin (`<TMPDIR>/website-manager/<Projekthash>/`, Modus 0700, ein `TMPDIR` darin oder Symlinks im Bereich werden abgelehnt); `write` und `replace` schreiben atomar nur bei erwartetem Hash und weisen jeden anderen Pfad, Traversal und Symlinks ab; eine zwischenzeitlich geänderte, entfernte oder durch Symlink ersetzte Datei ergibt `conflict` ohne Überschreiben und ohne Lesen hinter dem Symlink; `check` führt `npm run build` und `npm run check` mit echten Exit-Codes aus, ist nur für den geprüften Inhalt gültig (spätere Änderung → `stale`), höchstens zwei Reparaturrunden, ein nicht startbares npm ergibt `not-run`; `finish` meldet `complete` nur nach bestandenem Build und Check für den aktuellen Inhalt und tatsächlich durchgeführter Sichtprüfung, sonst „technically checked, visual check open“ (auch wenn kein Browserwerkzeug verfügbar ist); die Sicherung wird nur im bestätigten Erfolgsfall und nur nach vollständiger Prüfung des gesamten eigenen Sicherungsbaums entfernt; Zustandsdatei, Besitzmarke und Originalsicherung werden nicht über Symlinks gelesen; bestehende uncommittete oder unversionierte Änderungen anderer bleiben unberührt (kein Stash, Reset oder Clean); `edit` installiert nie Abhängigkeiten, committet nie und schreibt nie unter `.project/reports/`, in Regeln, Marken-, Prüfskript-, `package.json`-, Lockfile-, Manifest-, Schema- oder Besitzprotokolldateien.
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

## Skill publish

## R16: publish – ehrlicher Platzhalter

Status: confirmed
Acceptance: `publish` hat keine Veröffentlichungsfunktion; der Ordner enthält nur `SKILL.md` (für die Sprachpräferenz nach R27 nutzt der Skill ausschließlich den gemeinsamen Helper); der Skilltext sagt eindeutig, dass Veröffentlichen nicht verfügbar ist, und behauptet nie, eine Veröffentlichung sei möglich, vorbereitet oder erfolgt.
Source: skills/publish/SKILL.md
Test: tests/contracts/test_publish_contract.py

## R23: publish – Inhalt des Platzhalters

Status: confirmed
Acceptance: Der Skilltext benennt allgemein, was fehlt (zentraler Workflow und serverseitiges Protokoll, Workflow-Aufruf), verweist für eine lokale Qualitätsprüfung auf `optimize` mit dem Hinweis, dass dies keine Veröffentlichungsprüfung ist, verweist nicht auf geplantes Verhalten, deployt, pusht und committet nicht, fragt nichts per Netzwerk ab, erfindet keine Workflow-Namen, SHAs, Hosts oder Geheimnisse, legt keine Workflow-Datei an und gibt keine Befehlsvorabfreigabe.
Source: skills/publish/SKILL.md
Test: tests/contracts/test_publish_contract.py

## Geführter Ablauf

## R30: Zentraler Einstieg `plugin-website`

Status: confirmed
Acceptance: Der Skill `plugin-website` prüft den Projektzustand ohne Änderungen (`flow.py status`), erklärt den nächsten Schritt, startet fehlende Schritte, übernimmt Angaben aus dem ursprünglichen Auftrag, fragt nur nach Fehlendem und setzt bei späteren Aufrufen am passenden Punkt fort. Vorhandene, unbekannte oder widersprüchliche Zustände gelten nie als leeres Projekt. Aufruf ausdrücklich nach Skillname (`/website-manager:plugin-website`) und Aktivierung durch Beschreibung sind vorgesehen; eine garantierte Aktivierung durch ein einzelnes Wort wird nicht zugesagt.
Source: skills/plugin-website/SKILL.md
Source: skills/plugin-website/references/entry.md
Source: skills/_shared/scripts/flow.py
Test: tests/integration/flow/test_flow_state.py
Test: tests/contracts/test_guided_flow_contract.py

## R31: brief

Status: confirmed
Acceptance: `brief` erarbeitet Zweck, Zielgruppe, Angebot, Botschaft, gewünschte Handlung, Tonalität, Sprache der Website (getrennt von der Bedienersprache), Materialien, gestalterische Richtung und Farbpalette (Vorschläge mit Begründung, gewählte Palette gespeichert), nutzt Bekanntes, unterstützt mehrere Feedbackrunden und speichert das Briefing im Websiteprojekt (`.project/website/<site-id>/brief.json`, strenges Format, Feldstatus bestätigt/vorgeschlagen/offen, jede Revision erhalten). Designvarianten entstehen erst nach ausdrücklicher Bestätigung der Grundlage.
Source: skills/brief/SKILL.md
Source: skills/brief/references/brief.md
Source: skills/_shared/scripts/site_common/flowstate.py
Test: tests/integration/flow/test_flow_state.py

## R32: design und revisionsgebundene Freigabe

Status: confirmed
Acceptance: `design` erzeugt aus dem bestätigten Briefing mindestens zwei klar unterschiedliche Startseiten-Prototypen (ein bloßer Farbwechsel zählt nicht), mit Textentwürfen statt Lorem ipsum; Fakten wie Preise, Qualifikationen, Jahre, Zahlen und Ergebnisse stehen nur als gekennzeichnete offene Angaben. Prototypen liegen unter `.project/website/<site-id>/design/rNNN/` außerhalb von `sites/` (kein Teil der Website, die Startseite bleibt unberührt), sind lokal vergleichbar (Vergleichsseite) und unveränderlich je Revision. Feedback führt zu einer neuen Revision. Eine Freigabe bindet Revision, Variante, Variantenhash und Briefinghash und braucht die ausdrückliche Aussage der Person; eine bloße Präferenz ist keine Freigabe; eine neuere Revision macht eine ältere Freigabe veraltet. Nach der Freigabe setzt der Ablauf die Startseite ohne zweite Bestätigung um; der Schreibumfang bleibt `src/pages/index.astro` mit Originalsicherung, Hashprüfung und Konflikterkennung von `edit`; zusätzliche Schreibpfade sind nicht freigegeben.
Source: skills/design/SKILL.md
Source: skills/design/references/design.md
Source: skills/_shared/scripts/site_common/flowstate.py
Test: tests/integration/flow/test_flow_state.py

## Bekannte Einschränkung: edit und setup

Nach einer `edit`-Änderung an einer von `setup` erzeugten Datei stimmt der im Besitzprotokoll gespeicherte Hash nicht mehr. Dann ergibt `setup create` für diese Site `conflict` ohne Schreibzugriff, und `setup verify` behält die Datei (`modified (kept)`). `setup.md` und `edit.md` weisen die Zuständigkeit für die Koexistenz beide `setup` zu; eine Regel zum neuen Aufsetzen der Hashes (Rebaselining) ist nicht festgelegt, `setup update` und `--adopt-edits` sind nicht umgesetzt. Die Einschränkung ist dokumentiert (R25).

## Nicht belegt (NOT RUN)

Deterministische Tests (fiktive Fixtures, Fake-`npm`, lokale Prozesse) belegen Logik der Skripte, nicht das Verhalten eines Hosts oder Modells. Bis zur tatsächlichen Ausführung gilt `NOT RUN` für:

- Claude- und Codex-Verhalten je Skill, Installation und Import in einem Host, Aktivierung der Skills.
- Ersetzung von `${CLAUDE_PLUGIN_ROOT}`, Wirkung von `allowed-tools` (auch Muster mit `..` zum gemeinsamen Resolver bzw. zu `skills/preview/`) und ob beide Hosts `skills/_shared/` mitinstallieren.
- Verfügbarkeit von Browserwerkzeugen je Host, Wirkung von `"autoPort": false` in `.claude/launch.json` (Claude Desktop) und jede tatsächliche Sichtprüfung im Browser.
- Modellverhalten: Passung eines Auftrags, Rückfragen, keine erfundenen Fakten, Qualität von Vorschlägen und Designs.
- Echte `npm`/Node/Astro-Läufe: belegt nur für eine fiktive Site mit Node v26.12.1/npm 11.20.0 auf Darwin arm64; weitere Versionen und Plattformen sowie die Node-Untergrenze 22.23.4 von `optimize` sind offen.
