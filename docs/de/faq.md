# Häufige Fragen

**Deutsch** | [English](../en/faq.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Produkt und Zugang

**Was ist das?** Das Plugin **Website Manager** (`website-manager`) mit fünf Skills für statische Astro-Websites: `setup`, `preview`, `optimize`, `edit`, `publish`. Es unterstützt Claude und Codex als Zielhosts; die Hostabnahme steht aus (NOT RUN).

**Kann ich damit veröffentlichen?** Nein. `publish` ist ein Platzhalter und sagt das ausdrücklich. Es gibt keine Veröffentlichung, kein Deployment und keine Formulare.

**Kann `edit` mein ganzes Websiteprojekt ändern?** Nein, ausschließlich die Startseite `src/pages/index.astro` einer Site vom Typ `astro-static`. Blog, weitere Seiten und neue Sites sind nicht Teil des Skills.

**Ist es installierbar?** Der Katalogeintrag `website` im Marketplace wurde lokal angepasst. Ob er veröffentlicht ist und ein Host ihn importiert, ist nicht belegt ([Installation](installation.md)).

**Gibt es Alias-Namen wie `zyris-website` oder den früheren Namen `website`?** Nein. Alte Plugin- und Skill-Namen werden nicht unterstützt.

## Voraussetzungen

Aus den verifizierten Quellen des Plugins (Details in den [Voraussetzungen](../prerequisites.md)):

- **Python 3.10 oder neuer**, nur Standardbibliothek, keine zusätzlichen Pakete. Lokal wurde nur Python 3.15 ausgeführt.
- **Kein Git erforderlich** für Setup, Vorschau, Bearbeitung oder Optimierung; weder Repository noch Commit oder Remote.
- **Node 22.23.4 oder neuer und npm** für Build und Prüfungen der Site (`engines` der erzeugten `package.json`). Die Abhängigkeiten der Site installierst du selbst (`npm install` bzw. `npm ci` im Site-Ordner) oder per ausdrücklichem `setup verify`.
- **`ps` und `lsof`** für `preview`. Fehlt eines oder sieht es seinen eigenen Prozess nicht, meldet `preview` `insufficient-evidence` und startet nichts.
- Ein **Browserwerkzeug des Hosts** ist für die Sichtprüfung nützlich, aber keine Voraussetzung. Ohne tatsächliche Ansicht bleibt die Sichtprüfung offen.

Kein Skill installiert Werkzeuge (Node, npm, Git). `preview`, `optimize` und `edit` installieren nie Abhängigkeiten; nur `setup verify` bzw. `--build` führt auf ausdrücklichen Auftrag die in der Site deklarierte Installation aus.

## Datenschutz und Speicherung

**Wo liegen meine Daten?** Websitedaten in deinem Projekt; Prozesszustand und Sicherungen im Temp-Bereich außerhalb des Repositories; nichts im installierten Plugin ([Speicherung](storage.md)).

**Werden Geheimnisse in Berichten oder im Chat gezeigt?** Die Skills legen keine Geheimnisse in Dateien, Befehlszeilen, Berichte oder Ausgaben. Bekannte Geheimnisfelder in Werkzeugausgaben werden musterbasiert geschwärzt; das ist keine vollständige Erkennung.

**Liest das Plugin andere private Daten?** Nur das ausdrücklich ausgewählte Websiteprojekt im Rahmen des jeweiligen Skills. Tests verwenden ausschließlich fiktive Fixtures.

## Fehlerbehebung

- **`conflict` bei `setup create`** für eine bestehende Site: Entweder weichen die Angaben ab, oder eine erzeugte Datei wurde geändert (etwa durch `edit`). Das ist die bekannte Einschränkung; es wird nichts überschrieben. Nutze `setup verify`, das die Datei behält (`modified (kept)`).
- **`needs-install`:** Führe `npm install` im Site-Ordner selbst aus und starte erneut.
- **`port-conflict`:** Ein Prozess, der nicht dem Plugin gehört, belegt den Port. `preview` beendet oder übernimmt ihn nicht; `inspect` prüft die dort ausgelieferte Seite.
- **`incomplete` bei `optimize`:** Ein Werkzeug, eine Abhängigkeit, das Lockfile, der Build oder lesbare Ausgabe fehlt. Der Assistent nennt den Befehl (z. B. `npm ci`). `incomplete` wird nie als sauber gemeldet.
- **Arbeitsliste stoppt den Lauf:** Sie wurde von Hand geändert oder beschädigt; aus deiner Sicherung wiederherstellen.
- **Projekt im früheren Format:** Abgelehnt wird, wenn das Manifest auf `zyris-website.schema.json` verweist oder nur diese Schemadatei vorhanden ist (ohne `website.schema.json`); konvertiere das Projekt selbst, es gibt keinen Fallback. Eine unbenutzte alte Schemadatei neben dem korrekt verwendeten `website.schema.json` ist allein kein Ablehnungsgrund.
- **Der Assistent sagt „Skill-Pfad nicht verfügbar“ oder „Plugin-Pfad fehlt oder veraltet“:** Aktualisiere das Plugin und öffne eine neue Unterhaltung. Der Assistent sucht dann nicht in Caches und kopiert keine Skripte in dein Projekt.

## Grenzen der Prüfung

Struktur- und Dokumentationsprüfungen belegen weder fachliches Verhalten noch Hostabnahme. Folgendes wurde **nicht** ausgeführt (NOT RUN):

- echte `npm`-/Node-Läufe auf weiteren Node-Versionen (Untergrenze 22.23.4 und Zwischenversionen) und Plattformen; geprüft wurde nur Node v26.12.1/npm 11.20.0 auf Darwin arm64 (siehe unten);
- native Claude- und Codex-Läufe je Skill, einschließlich Skillladen, `${CLAUDE_SKILL_DIR}`, `allowed-tools`-Wirkung und Erreichbarkeit von `skills/_shared/`;
- Modellverhalten (Passung des Auftrags, fehlende Fakten, mitgelieferte Anweisungen, Routing);
- jede tatsächliche Sichtprüfung im Browser, auch die Wirkung von `"autoPort": false` in Claude Desktop.

Ausgeführt wurden deterministische Tests mit fiktiven Fixtures, Fake-npm und lokalen Prozessen auf `127.0.0.1` sowie, getrennt davon, echte `npm`-/Astro-Läufe von `setup`, `optimize`, `edit` und `preview` an einer fiktiven Site (nur der genannte Werkzeugstand). Sie belegen die Logik der Skripte und der Werkzeugkette, nicht das Verhalten eines Hosts oder Modells und keine Sichtprüfung. Ein Nachweis für Claude gilt nie für Codex und umgekehrt.

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
