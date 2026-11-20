# Lokale Website-Arbeit ohne Git

Bestätigte Änderung vom 2026-11-20: SCOPE R28. Dies ist Produktentwicklung nach
der Migration; der historische Quellcheckout wurde weder gelesen noch verändert.
Die bereits vorhandenen Änderungen zur Bedienersprache bleiben erhalten.

## Umsetzung

- Setup verwendet den ausgewählten Ordner (`--root`, sonst Arbeitsverzeichnis),
  unabhängig von übergeordneten Repositorys. Kein `git init`, Remote oder Commit.
- Gemeinsame projektlokale Ignore-Auswertung für Setup und Optimize; kein Git-Index,
  keine globalen Ignore-Dateien. Build-Ausgaben müssen weiterhin deklariert sein.
- Dateisnapshots schützen Edit und Optimize, auch für nicht versionierte Dateien.
  Hinzugefügte, gelöschte und geänderte Quellen sind sichtbar. Symlinks werden als
  Linkobjekt erfasst und niemals verfolgt; ignorierte/private Daten werden ausgelassen.
- Edit behält Original-Backup, erwarteten Hash und atomare Schreibvorgänge. Alte
  Sitzungen ohne Dateisnapshot werden vor Schreibzugriff abgelehnt, nicht migriert.
- Optimize-Apply benötigt eine freigegebene, unveränderte mechanische Änderung in
  einer nicht ignorierten Projektdatei. Manifest, Besitzprotokoll, Worklist und
  Bericht-Formatkennungen bleiben unverändert; neue Berichte nennen Dateihashes
  statt eines nicht vorhandenen Commits. Bestehende Berichte werden nicht geändert.
- Preview hatte keine Git-Pflicht. Publish bleibt ohne Git-Vorprüfung ein Platzhalter.

Die historischen Byte-Identitätsprüfungen für `edit.py` und `audit.py` beschrieben
nur den Migrationsstand und sind durch diese bestätigte Weiterentwicklung überholt.
Für unveränderte Module bleiben sie erhalten. Verhalten wird durch Akzeptanztests
und Schutztests nachgewiesen, nicht durch aktualisierte Soll-Hashes. Die aktuelle
Vollständigkeitszuordnung führt den entfernten Git-Helper beim gemeinsamen Modul.

## Nachweise

Am 2026-11-20 bestanden:

- `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_tests.py --kind deterministic`:
  **830 Tests, OK** (249,419 Sekunden). Die lokalen Preview-Testserver benötigten
  Loopback-/Prozesszugriff außerhalb der Sandbox; keine Netzwerkdownloads.
- Zusätzlicher Wiederholungslauf für die abschließend angepassten Lockfile-Meldungen
  und ihre Verträge: **112 Tests, OK**.
- Dokumentationsverträge nach der Anpassung von README, FAQ und Voraussetzungen:
  **22 Tests, OK**.
- Die Git-freien Akzeptanzfälle decken Setup-Plan/Create/Adopt/Verify, Wiederholung,
  Auswahl eines Ordners innerhalb eines übergeordneten Repositorys, fehlendes Git
  auf PATH, Edit-Backup/Konflikte/Abschluss, Ablehnung alter Sessions, Optimize-Audit/
  Decide/Apply und neue/geänderte/entfernte Quellen ab. Die Snapshot-Tests prüfen
  Ignore-Regeln, private Daten, Symlinks einschließlich Austausch während des Laufs
  und Dateirechte. Preview verwendet weiterhin fiktive Projekte ohne Repository.

Frühere Läufe fanden gesperrte Loopback-Sockets sowie überholte Git-Erwartungen.
Der erste vollständige Lauf außerhalb der Sandbox meldete zwei Cache-Fehler:
Edit importierte das neue gemeinsame Modul bei Aufrufen ohne `-B` mit aktivierter
Bytecode-Erzeugung. Das wurde korrigiert, die erzeugten Cachedateien entfernt und
sowohl die betroffenen Tests als auch die komplette Suite anschließend erfolgreich
wiederholt.

Lesender Abschlussreview: `scripts/verify.py --review` bestätigt die Struktur und
führt keinen Zielcode aus. Er meldet weiterhin die bereits vorhandenen fehlenden
`Source:`-Verweise bei R2, R18 und R25; das sind Nachweislücken, keine neu behauptete
Produktabnahme. R28 hat Source- und Testverweise. `git diff --check` ist fehlerfrei.

Keine echten Website-Inhalte, Downloads, Installationen oder echten npm-Aufrufe.
Das im Auftrag erwähnte Websiteprojekt wurde nicht geöffnet oder verändert.
Host-/Modell-/Browsernachweis: NOT RUN.
