# Speicherung und Wiederherstellung

**Deutsch** | [English](../en/storage.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

Diese Seite beschreibt, wo Daten liegen und welche Schutzgrenzen gelten. Die verbindlichen Regeln stehen in [SCOPE.md](../../SCOPE.md) (R5, R7, R15, R21) und in `skills/_shared/references/interfaces.md`.

## Speichermodell

Es gibt drei getrennte Orte. **Im installierten Plugin wird nichts gespeichert**; die Skripte laufen mit `python3 -B` und schreiben keinen Zustand und keinen Bytecode dorthin.

| Ort | Inhalt | Geschrieben von |
|---|---|---|
| **Websiteprojekt** (dein Git-Repository) | Sites unter `sites/<domain>/`; Manifest `.project/specs/zyris-website.json`; Schemakopie `.project/specs/website.schema.json`; Besitzprotokoll `.project/specs/zyris-website.managed.json`; Berichte und Arbeitsliste unter `.project/reports/<site>/`; Launch-Eintrag `zyris-<site>` in `.claude/launch.json`; Scratch-Ordner `.tmp/` | je nur der benannte Skill (siehe unten) |
| **Außerhalb des Repositories** (Temp-Bereich, `<TMPDIR>/zyris-website/…`) | Besitzprotokoll und Log des Dev-Servers (`preview`); Sicherungen und Sitzungszustand von `edit` | `preview`, `edit` |
| **Installiertes Plugin** | nichts | niemand |

Die internen Namen `zyris-website`, `zyris-optimize:*` und `ZYRIS_WEBSITE_STATE_DIR` stammen aus dem früheren Plugin und bleiben unverändert: Websiteprojekt-Datenformate sind eine eigene Schnittstelle und werden wegen des Plugin-Namens nie umbenannt oder konvertiert. Eine Ausnahme ist die Schemadatei (`website.schema.json`).

## Einrichtung und Konfiguration

Für Nutzer gibt es keine Plugin-Konfiguration. Die Site-Konfiguration liegt im Manifest deines Projekts. `setup create` belegt es so: `$schema` = `./website.schema.json`, `version` = 1, je Site `name` = Domain, `path` = `sites/<domain>`, `type` = `astro-static`, `title` (Angabe oder Domain), `aliases` (Angaben oder leer), `port` (Angabe oder automatisch) und `environment` nur auf ausdrücklichen Wunsch. Vorhandene Einträge werden nie umgeschrieben. Jede Operation, die ein vorhandenes Projekt verwendet, prüft das Manifest gegen das Schema **des Plugins**, nie gegen eine lockerere Projektkopie.

Wer am Plugin entwickelt, nutzt zusätzlich die ignorierte Datei `.local/marketplace.json` für lokale Marketplace-Zuordnungen; sie wird nicht committed ([Entwicklung](development.md)).

## Speichern und fortsetzen

| Skill | Schreibt | Schreibt nie |
|---|---|---|
| `setup` | Site-Ordner, Manifest-Eintrag, Schemakopie (nur bei Fehlen), `.tmp/` samt `.gitignore`-Eintrag, Besitzprotokoll; bei `verify` die npm-Nebenwirkungen `node_modules/`, `dist/`, `.astro/` und ggf. `package-lock.json` | Dateien bestehender Sites bei `adopt`; erzeugte Dateien bei `verify` |
| `preview` | eigener Eintrag in `.claude/launch.json`; Besitzprotokoll und Log im Temp-Bereich | Manifest, Port, Schemakopie |
| `optimize` | unveränderliche Berichte, Arbeitsliste; bei `apply` nur die freigegebene Stelle einer versionierten Datei | Site-Inhalt bei Audit und Entscheidung; Manifest; Besitzprotokoll |
| `edit` | ausschließlich `src/pages/index.astro`; Sicherung und Zustand im Temp-Bereich | Berichte, Regeln, Marken-, Prüfskript-, `package.json`-, Lockfile-, Manifest-, Schema- und Besitzprotokolldateien |
| `publish` | nichts | alles |

Fortsetzen: `optimize` knüpft über die Arbeitsliste und stabile Befund-IDs an frühere Läufe an; `preview` erkennt einen eigenen laufenden Server am Besitzprotokoll; `edit` arbeitet mit einer Sitzung, die auf die Sicherung verweist. Ein Chatverlauf ist kein Speicher.

## Fehler und Wiederherstellung

- **Nichts wird überschrieben, um zu „reparieren“.** Nicht unterstützte Formate (früheres Schemaformat, Typ `astro`, entfernte Felder) werden mit Diagnose abgelehnt, bevor etwas geschrieben wird. Es gibt keine automatische Migration, keinen Fallback und keine Wiederherstellung, die Nutzerdaten überschreibt.
- **setup:** Ein Schreibfehler stellt alle Dateien und die Registrierung wieder her (`failed-rolled-back`), sonst nennt der Assistent den Rest (`failed-partial`). Nach `failed-build`/`failed-check` bleiben Dateien und Registrierung; repariere die Datei und führe `verify` aus.
- **optimize:** Eine von Hand geänderte oder beschädigte Arbeitsliste stoppt alle Befehle vor dem Bauen, ohne sie zu ändern. Stelle sie aus Git wieder her. Auch eine insgesamt umgewandelte Zeilenendung (z. B. durch `autocrlf`) gilt als Änderung. Ein Bericht wird nie überschrieben.
- **edit:** Wurde die Zieldatei zwischenzeitlich geändert, entfernt oder durch einen Symlink ersetzt, ergibt das `conflict` ohne Überschreiben; die neuere Fassung bleibt. Die Sicherung (HEAD, `git status` und das Original, bytegetreu) liegt in einem Ordner mit Modus 0700 außerhalb von Projekt und Plugin. Ein `TMPDIR` innerhalb des Projekts oder Plugins sowie Symlinks im Bereich werden abgelehnt. Bereinigt wird nur der eigene Ordner, nur nach bestätigtem Erfolg und erst, nachdem der gesamte Baum gegen die erwarteten Objekte geprüft wurde; findet sich eine fremde Datei, wird nichts entfernt.
- **preview:** Ist der Zustandsbereich unsicher (z. B. ein Symlink), meldet `start`/`status`/`stop` `unsafe-state` und signalisiert nichts.
- Bestehende uncommittete Änderungen anderer bleiben in allen Skills unberührt (kein Stash, Reset oder Clean).

## Einschränkungen

Die folgenden Grenzen sind bekannt und **nicht** geschlossen; die Schutzmaßnahmen decken nur die in den Tests belegten Fälle ab.

- **Race-Fenster bei `edit`:** Zwischen der Hashprüfung und dem atomaren Austausch (`os.replace`) liegt ein kurzes Fenster. Eine fremde Änderung genau in diesem Moment würde überschrieben; es gibt keine Dateisystemsperre (BD-28).
- **Symlink-Schutz:** `O_NOFOLLOW` schützt nur die letzte Pfadkomponente beim Öffnen. Das Austauschen eines Elternordners zwischen Prüfung und Öffnen ist nicht pauschal ausgeschlossen.
- **Zustandsbereich von `preview`:** Vorfahren des Basisverzeichnisses (der Systemtemp-Ordner, unter macOS z. B. `/var` → `/private/var`) werden nicht geprüft; ein böswilliger Prozess desselben Benutzers liegt außerhalb des Schutzes.
- **Geheimnisschwärzung ist musterbasiert:** `edit` schwärzt in der npm-Ausgabe Werte bekannter Felder (Namen mit TOKEN, SECRET, PASSWORD, PASSWD, API_KEY oder AUTH, auch `Authorization`) vor der Kürzung auf 2000 Zeichen; unquotierte Werte reichen bis zum Zeilenende, harmlose Namen wie „author“ werden mitgeschwärzt. `optimize` schwärzt Tokenmuster in der Prüfausgabe. Geheimnisse ohne solches Muster bleiben unerkannt. Es gibt keine vollständige Erkennung.
- **`--visual-done`** ist die Aussage des Aufrufers; der Helfer kann eine tatsächliche Sichtprüfung nicht nachprüfen.
- **`edit` und `setup`:** Nach einer `edit`-Änderung an einer erzeugten Datei stimmt der Besitzhash nicht mehr (`conflict` bei erneutem `create`, `modified (kept)` bei `verify`); kein Neuaufsetzen der Hashes.
- Die Prozesstests von `preview` belegen das Verhalten der lokalen Python-/macOS-Umgebung, nicht anderer Plattformen.

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
