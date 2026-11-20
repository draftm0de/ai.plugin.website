# Nutzung

**Deutsch** | [English](../en/usage.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

Diese Seite erklärt die Nutzung. Das maßgebliche Verhalten steht in [SCOPE.md](../../SCOPE.md) und in den Referenzen der Skills (`skills/<skill>/references/`). Alle Domains und Texte unten sind erfunden. Die Beispiele zeigen keinen aufgezeichneten Hostlauf.

## Einrichten

Du brauchst ein **Websiteprojekt**: einen lokalen Ordner, in dem die Sites unter `sites/<site-id>/` liegen und die Projektdaten unter `.project/`. Öffne es in Claude oder Codex und arbeite mit diesem Ordner als Arbeitsverzeichnis. Python muss vorhanden sein; für Build und Vorschau außerdem Node und npm. Git ist nicht erforderlich ([Voraussetzungen](../prerequisites.md)).

1. **Neue Site anlegen** – „Lege eine neue statische Website für demo.example an, Titel ‚Demo Werkstatt‘.“ `setup create` schreibt das Template in einen fehlenden oder leeren Ordner `sites/demo.example/`, trägt die Site im Manifest `.project/specs/website.json` ein und legt bei Bedarf die Schemakopie `.project/specs/website.schema.json`, den Scratch-Ordner `.tmp/` und das Besitzprotokoll an.
2. **Vorhandenen Ordner übernehmen** – „Übernimm den vorhandenen statischen Ordner sites/alt.example.“ `setup adopt` trägt ihn nur ein und ändert darin keine Datei.
3. **Erst ansehen, dann ändern** – „Zeig mir, was das Anlegen von demo.example ändern würde.“ `plan` schreibt, installiert und baut nichts. Es verspricht nicht, dass ein späterer Lauf gelingt.
4. **Abhängigkeiten installieren** – das tust du selbst (`npm install` im Site-Ordner) oder du beauftragst `setup verify` bzw. `--build`: Nur diese ausdrückliche Prüfung führt die in der Site deklarierte Installation aus (sie nutzt die npm-Registry im Netzwerk). `preview`, `optimize` und `edit` installieren nie; fehlt etwas, nennt dir der Assistent den Befehl.
5. **Prüfen** – „Prüfe demo.example.“ `setup verify` führt Installation, Build und Check mit echten Exit-Codes aus (Installation also nur auf diesen ausdrücklichen Auftrag); nicht gelaufene Schritte erscheinen als „nicht gelaufen“, nie als bestanden. Ein neues oder geändertes `package-lock.json` gehört zum Projekt: prüfe die Änderung; ein Commit ist für lokale Arbeit nicht erforderlich.

## Ablauf auswählen

| Du sagst … | Skill |
|---|---|
| „plugin-website“, „Erstelle mir eine Website für demo-a.com für einen Physiotherapeuten in Wien“ | `plugin-website` (geführter Einstieg) |
| „Lege eine Website an“, „übernimm den Ordner“, „prüfe den Build“, „die Domain ist jetzt demo-a.com“ | `setup` |
| „Was soll die Seite sagen, für wen ist sie?“ | `brief` |
| „Zeig mir Entwürfe für die Startseite“ | `design` |
| „Zeig mir die Seite lokal“, „stopp die Vorschau“ | `preview` |
| „Prüfe SEO und Barrierefreiheit“, „setze SEO-001 um“ | `optimize` |
| „Gestalte die Startseite“, „ändere den Text im Hero“ | `edit` |
| „Veröffentliche die Site“ | `publish` (nicht verfügbar) |

### plugin-website

Der geführte Einstieg. Er prüft das Projekt **ohne Änderungen**, sagt dir in einem Satz, welcher Schritt als Nächstes kommt, startet fehlende Schritte selbst (Setup, Briefing, Design, Umsetzung der freigegebenen Startseite) und fragt nur nach dem, was wirklich fehlt. Angaben aus deinem ersten Auftrag (Sitename, Domain, Branche, Ort) werden übernommen. Ein erneuter Aufruf setzt dort fort, wo das Projekt steht; er legt kein zweites Projekt an und wiederholt nichts Erledigtes. Ein vorhandenes, unbekanntes oder widersprüchliches Projekt gilt nie als leer. Rufe ihn ausdrücklich mit seinem Namen auf (Claude: `/website:plugin-website`; Codex: den Skill nennen). Ob ein Host ihn schon durch ein einzelnes Wort oder allein durch deinen Satz startet, hängt vom Host ab und ist **nicht belegt**; eine garantierte Aktivierung durch ein einzelnes Wort wird nicht zugesagt.

### setup

Operationen: `create <site-id> [--domain D]`, `adopt`, `plan create|adopt`, `verify`, `set-domain <site-id> <domain>`. Die Site-ID ist ein interner Kurzname (zum Beispiel `physio-wien`), nicht zwingend eine Domain. Eine Domain wird nur gespeichert, wenn du eine nennst; ohne sie funktioniert die Site lokal ohne öffentliche Adressen (keine Canonical-, Sitemap- oder Social-URLs), und die Domain lässt sich später nachtragen, ohne ID, Ordner oder Zuordnungen zu ändern. Nicht verfügbar sind `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, der frühere Typ `astro` (Docker/Caddy) und seine Optionen; sie werden abgelehnt, nie übersetzt. Eine identische Wiederholung ergibt `unchanged` ohne Schreibzugriff. Abweichungen, geänderte oder fehlende erzeugte Dateien und fremde Schemakopien ergeben `conflict` ohne Schreibzugriff. Schlägt ein Schreibvorgang fehl, stellt `setup` alle Dateien und die Registrierung wieder her (`failed-rolled-back`) oder nennt den genauen Rest (`failed-partial`).

### brief

Erarbeitet Zweck, Zielgruppe, Angebot und Botschaft, die gewünschte Handlung der Besucher, Tonalität, die **Sprache der Website** (getrennt von der Sprache, in der der Assistent mit dir spricht), Materialien, gestalterische Richtung und eine Farbpalette (Vorschläge mit kurzer Begründung). Kurze, gebündelte Fragen mit konkreten Vorschlägen, mehrere Feedbackrunden, gespeichert in deinem Projekt (`.project/website/<site-id>/brief.json`), bestätigte, vorgeschlagene und offene Angaben getrennt. Designvarianten entstehen erst, wenn du das Briefing ausdrücklich bestätigst. Eine spätere Änderung markiert abhängige Ergebnisse als veraltet; nichts wird gelöscht.

### design

Mindestens zwei deutlich verschiedene Startseiten-Prototypen (ein Farbwechsel ist keine zweite Richtung) mit echten Textentwürfen und klar als offen gekennzeichneten Fakten (keine erfundenen Preise, Qualifikationen, Jahre oder Ergebnisse). Sie sind lokale Dateien außerhalb der Website (`.project/website/<site-id>/design/rNNN/`), lassen sich nebeneinander vergleichen und ersetzen nie die vorhandene Startseite. Du gibst Feedback, es folgt eine neue Revision, und so weiter. „Variante B gefällt mir besser“ ist Feedback; die Freigabe muss die gezeigte Revision und das Layout nennen. Nach der Freigabe wird die Startseite ohne Rückfrage umgesetzt (nur `src/pages/index.astro`, mit den Schutzmechanismen von `edit`).

### preview

„Zeig mir demo.example lokal.“ Nur der Controller startet, verwendet wieder oder beendet den Dev-Server, und nur wenn er nachweisen kann, dass der Prozess ihm gehört; Startname und Port allein sind nie ein Beweis. Bereit meldet er erst nach einer erfolgreichen HTTP-Probe. Belegt ein fremder Prozess den Port (`port-conflict`), fasst `preview` ihn nicht an; stattdessen prüft `inspect` die dort ausgelieferte Seite. Fehlen Abhängigkeiten, bekommst du `needs-install` und den Hinweis auf `npm install`. Ein Browserwerkzeug des Hosts darf nur die vom Controller gelieferte oder durch `inspect` bestätigte Adresse öffnen. Ohne tatsächlich geöffnete Seite sagt der Assistent: „läuft, noch nicht angesehen“.

### optimize

„Prüfe SEO und Barrierefreiheit von demo.example.“ Es gibt drei getrennte Schritte:

| Schritt | Was passiert | Was nicht passiert |
|---|---|---|
| **Audit** | Build in das ignorierte `dist/`, `seo:check` und `a11y:check` unabhängig voneinander, Vergleich von Projektdateipfaden und Datei-Hashes vor und nach dem Lauf; ein unveränderlicher Bericht unter `.project/reports/<site>/optimize/` und die Arbeitsliste `.project/reports/<site>/optimize.md` | Kein Site-Inhalt wird geändert, nichts installiert oder committet, **nichts freigegeben** |
| **Freigabe** | Du entscheidest je Befund: `approved`, `deferred` (später), `wont-do` (nicht umsetzen) oder wieder `proposed`. „Gib SEO-001 frei“ speichert nur die Entscheidung zum dokumentierten Vorschlag und seinem Ausgangstext | Ändert keinen Site-Inhalt; eine bereits getroffene Entscheidung ändert sich nur auf deinen ausdrücklichen Wunsch (`--change`) |
| **Umsetzung** (`apply`) | Nur freigegebene, nicht veraltete Vorschläge mit mechanischer Änderung: Der Suchtext muss genau einmal in einer nicht ignorierten Projektdatei der Site vorkommen. Danach läuft die vollständige Prüfung erneut | Nichts anderes wird angefasst; keine Installation, kein Commit. Ändert sich Vorschlag oder Ausgangstext, wird die Freigabe ungültig |

Ein Befund wandert erst in die Historie, wenn ein vollständiger Lauf nach erfolgreichem Build ihn nicht mehr meldet. Technische Fehler, Warnungen und redaktionelle Empfehlungen bleiben getrennte Klassen. Manuelle Prüfpunkte (Kontrast, Tastatur, Screenreader, Wahrheitsgehalt, Rechtstexte) stehen in jedem Bericht und gelten nie als bestanden. Es gibt kein Ranking-Versprechen; GEO ist nicht verfügbar. Suchmaschinen-Registrierung, DNS und Weiterleitungen sind Sache der Person.

### edit

„Gestalte die Startseite von demo.example: Name ‚Demo Werkstatt‘, Ort ‚Musterstadt‘, Angebot: Fahrradreparatur.“ oder „Ändere in der Startseite den Satz ‚Willkommen‘ in ‚Schön, dass du da bist‘.“ `edit` ändert ausschließlich `src/pages/index.astro` einer Site vom Typ `astro-static`. Fehlende Fakten fragt der Assistent gezielt nach; er erfindet keine Kontakte, Adressen, Preise, Bewertungen oder Lizenzen. Mitgelieferte Texte, Dateien und Links sind Daten: Enthaltene Anweisungen werden zitiert und erfragt, nicht ausgeführt. Ein allgemeiner Änderungsauftrag gibt keinen optimize-Befund frei; nennst du eine Befund-ID, läuft die Arbeit über `optimize`.

Der Ablauf: Voraussetzungen prüfen (ohne Schreiben), Original sichern, ändern, `npm run build` und `npm run check`, ansehen, abschließen. Der Abschluss ist ehrlich: **„vollständig“ gibt es nur nach bestandenem Build und Check für den aktuellen Inhalt und tatsächlich durchgeführter Sichtprüfung.** Konnte der Assistent die Seite nicht selbst ansehen, lautet die Aussage sinngemäß „die automatischen Prüfungen sind bestanden, ich konnte die Seite nicht selbst ansehen“ (technically checked, visual check open). Fehlgeschlagene oder nicht gelaufene Prüfungen werden nie so umgedeutet. Höchstens zwei Reparaturrunden.

### publish

„Veröffentliche demo.example.“ Der Skill sagt, dass Veröffentlichen **nicht verfügbar** ist, nennt allgemein, was fehlt (zentraler Workflow, serverseitiges Protokoll, Workflow-Aufruf), und verweist für eine lokale Qualitätsprüfung auf `optimize` – ausdrücklich keine Veröffentlichungsprüfung. Er führt nichts aus, fragt nichts per Netzwerk ab und legt keine Datei an.

## Ausgabe verstehen

Die Schlussantwort ist kurz (meist zwei bis vier Sätze): was sich geändert hat, ob die gelaufenen Prüfungen es bestätigen, wo du es ansiehst und was du noch entscheiden musst. Prozess-IDs, Ports, Exit-Codes und Hashes nennt der Assistent nur auf Nachfrage.

| Skill | Zustände (Auswahl) | Bedeutung |
|---|---|---|
| `setup` | `created`, `adopted`, `verified`, `unchanged`, `planned` | Erfolg (Exit 0) |
| | `needs-input` | eine Angabe fehlt, der Assistent fragt (Exit 2) |
| | `conflict`, `invalid`, `failed-rolled-back`, `failed-partial`, `failed-build`, `failed-check` | abgelehnt oder fehlgeschlagen (Exit 1) |
| `preview` | `running-new`, `running-reused`, `not-running`, `stopped`, `page-confirmed` | Erfolg |
| | `needs-install`, `port-conflict`, `unknown-owner`, `insufficient-evidence`, `timeout`, `unsafe-state` | nichts verändert bzw. Hinweis, was du tun kannst |
| `optimize` | `clean`, `clean-with-warnings` | Erfolg |
| | `errors`, `incomplete`, `readonly-violated` | Befunde, fehlende Voraussetzung oder geänderte Projektdatei; `incomplete` gilt nie als sauber |
| `edit` | `written`, `unchanged`, `complete` | Erfolg |
| | `conflict`, `not-run`, `stale`, `repair-limit`, `refused`, `stop` | nichts überschrieben bzw. Prüfung nicht gelaufen oder veraltet |

Exit 0 heißt Erfolg, 1 `STOP:` (abgelehnt oder fehlgeschlagen), 2 Rückfrage. „Bestanden“, „gebaut“ oder „bereit“ wird nur gemeldet, wenn die Prüfung in diesem Aufruf lief und mit 0 endete.

## Sitzung steuern

- **Welche Site?** Sie wird nie geraten. Reihenfolge: von dir genannt (Domain, Ordner, Titel, Alias) → Arbeitsverzeichnis liegt in einer Site → nur eine Site vorhanden → zuletzt benutzte Site (mit ausgesprochener Bestätigung) → Rückfrage. Eine unbekannte Site ergibt einen Stopp, eine mehrdeutige eine Rückfrage mit Optionen.
- **Ein konkreter Auftrag ist die Freigabe** für genau die Arbeit, die er beschreibt. Blockiert ein Teil, laufen unabhängige Teile weiter.
- **Vorschau beenden** nur auf deinen Wunsch („Stopp die Vorschau“); der Assistent beendet nur Prozesse, die nachweislich ihm gehören.
- **Format ablehnen:** Ein Projekt im früheren Format wird mit Diagnose abgelehnt, bevor etwas geschrieben wird. Das gilt, wenn der `$schema`-Verweis des Manifests auf die frühere Schemadatei `zyris-website.schema.json` zeigt (in jeder lokalen Schreibweise) oder nur diese Datei und kein `website.schema.json` vorhanden ist. Eine unbenutzte alte Schemadatei neben dem korrekt verwendeten `website.schema.json` ist allein kein Ablehnungsgrund. Es gibt keine automatische Migration und keinen Fallback; du konvertierst das Projekt selbst.

## Später fortsetzen

- **optimize:** Befunde behalten stabile IDs (Site + Kriterium + Ort), Entscheidungen bleiben über Läufe erhalten, ein wiedergekehrter Befund erscheint als `reappeared`. Die Arbeitsliste ist generiert: Ändere sie nicht von Hand, sonst stoppt der nächste Lauf (aus deiner Sicherung wiederherstellen).
- **preview:** „Läuft die Vorschau noch?“ fragt den Zustand nur ab (`status`), ohne etwas zu starten.
- **edit:** Das Original liegt in einer Sicherung außerhalb des Repositories; nach einem bestätigten vollständigen Abschluss wird nur der eigene Sicherungsordner entfernt. Bei einem offenen Ergebnis nennt der Assistent, wo die Sicherung liegt.
- **Nach einem Fehlschlag von `setup verify`** repariert die Person (oder ein separat beauftragtes `edit`) die Datei und führt danach `verify` erneut aus – nicht `create` (das meldet für eine reparierte erzeugte Datei einen Konflikt).
- **Bekannte Einschränkung `edit` ↔ `setup`:** Nach einer `edit`-Änderung an einer von `setup` erzeugten Datei stimmt der gespeicherte Besitzhash nicht mehr. Ein erneutes `setup create` ergibt für diese Site `conflict` ohne Schreibzugriff, `setup verify` behält die Datei (`modified (kept)`). Es gibt kein Neuaufsetzen der Hashes (kein Rebaselining), kein `setup update`, kein `--adopt-edits`. Dass die Hashes nicht neu gesetzt werden, ist eine Grenze des heutigen Umfangs, keine Wiederherstellungsanleitung.

## Spezialisierte Abläufe

Nicht verfügbar (der Assistent bietet sie nicht an und umgeht sie nicht): Veröffentlichen und Deployment, Blog und weitere Seitentypen in `edit`, Formulare, `setup update`, Neuaufsetzen von Besitzhashes, GEO, Lighthouse, Linkgraph-Prüfung, isolierte Abhängigkeitskopie, neue Browserintegration. Vollständigkeit der Prüfungen: [Abnahmematrix](../migration/acceptance.md).

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
