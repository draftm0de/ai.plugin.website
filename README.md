# Website

**Deutsch** | [English](README.en.md)

<img src="docs/assets/zyris-icon.png" alt="ZYRIS" width="32">

[Dokumentation](docs/de/README.md) · [Installation](docs/de/installation.md) · [Nutzung](docs/de/usage.md) · [Screens](docs/de/screens.md) · [FAQ](docs/de/faq.md)

**Website** hilft dir, statische Astro-Websites in einem Websiteprojekt anzulegen, lokal anzusehen, auf SEO und Barrierefreiheit zu prüfen und ihre Startseite zu gestalten. Es besteht aus fünf Skills für Claude und Codex: `setup`, `preview`, `optimize`, `edit` und `publish`. Das Veröffentlichen ist **nicht verfügbar**; `publish` ist ein ehrlicher Platzhalter.

Stand: lokale Migration abgeschlossen, **Review ausstehend**. Die Hostabnahme (Claude, Codex), Modellverhalten und jede tatsächliche Sichtprüfung stehen aus und sind **NOT RUN**; echte npm-/Node-/Astro-Läufe sind nur für Node v26.12.1/npm 11.20.0 auf Darwin arm64 an einer fiktiven Site belegt (weitere Versionen und Plattformen offen). Das Plugin ist nicht veröffentlicht; Produktreife oder vollständige Hostunterstützung wird nicht behauptet. Das maßgebliche Produktzielbild ist [SCOPE.md](SCOPE.md).

Lizenz: MIT. Siehe [Lizenzentscheidung](docs/license.md).

## Für wen ist das gedacht?

Für Menschen, die mehrere kleine statische Websites in einem lokalen Websiteprojekt (`sites/<domain>/`) pflegen und dabei einen Assistenten einsetzen wollen, der Dateien nur im vereinbarten Rahmen ändert und nur das als geprüft meldet, was wirklich gelaufen ist. Du brauchst kein Wissen über Astro; für das Bauen und Prüfen müssen aber Node und npm auf deinem Rechner vorhanden sein ([Voraussetzungen](docs/prerequisites.md)).

## So sieht es aus

Du schreibst im Chat, was du willst, zum Beispiel: „Lege eine neue statische Website für demo.example an.“ Der Skill legt den Ordner an, trägt die Site im Projekt ein und nennt dir das Ergebnis in zwei bis vier Sätzen. Beispiele findest du unter [Screens und Beispiele](docs/de/screens.md). Es gibt **keine** echten Screenshots aus Claude oder Codex; die dortigen Textbeispiele sind erfunden und zeigen keinen Hostlauf.

## Funktionen und Modi

| Skill | Was er tut | Grenze |
|---|---|---|
| `setup` | Site anlegen (`create`), vorhandenen statischen Ordner übernehmen (`adopt`), Vorschau der Änderungen (`plan`), Installation, Build und Prüfung wiederholen (`verify`) | Kein `update`, kein Neuaufsetzen erzeugter Dateien; nur Typ `astro-static` |
| `preview` | Dev-Server einer Site lokal starten, wiederverwenden, abfragen, beenden; ausgelieferte Seite getrennt prüfen (`inspect`) | Installiert nie Abhängigkeiten; nur eigene, nachweislich zugehörige Prozesse |
| `optimize` | SEO- und Barrierefreiheits-Audit, datierte Berichte, Arbeitsliste, Entscheidungen, Umsetzung freigegebener Vorschläge | Kein GEO, kein Ranking-Versprechen; Audit gibt nichts frei |
| `edit` | Ausschließlich die Startseite `src/pages/index.astro` gestalten oder einen Text ändern | Kein Blog, keine anderen Seiten, keine Formulare |
| `publish` | Sagt, dass Veröffentlichen nicht verfügbar ist | Kein Skript, keine Veröffentlichung |

`optimize` trennt drei Dinge: **Audit** (Befunde finden), **Freigabe** (du entscheidest je Befund) und **Umsetzung** (nur freigegebene Vorschläge). Details: [Nutzung](docs/de/usage.md).

## Schnellstart

1. Installiere das Plugin über den Marketplace deines Hosts ([Installation](docs/de/installation.md)). Der lokal angepasste Katalogeintrag ist weder veröffentlicht noch per Hostlauf geprüft.
2. Öffne dein Websiteprojekt (ein lokaler Ordner; Git ist nicht erforderlich) in Claude oder Codex.
3. Bitte um eine Site: „Lege eine neue statische Website für demo.example an.“
4. Installiere die Abhängigkeiten selbst (`npm install` im Site-Ordner) oder lass sie ausdrücklich von `setup verify` installieren. `preview`, `optimize` und `edit` installieren nie.
5. Bitte um die Vorschau: „Zeig mir demo.example lokal.“

## Nutzung

Ein konkreter Auftrag gilt als Freigabe für genau die Arbeit, die er beschreibt. Rückfragen stellt der Assistent nur, wenn etwas Ergebnisrelevantes fehlt. `preview`, `optimize` und `edit` installieren nie automatisch; fehlt etwas, nennt der Assistent den Befehl, den du selbst ausführst. `edit` meldet „vollständig“ nur nach bestandenem Build und Check **und** tatsächlich durchgeführter Sichtprüfung; sonst lautet die Aussage „technically checked, visual check open“. Mehr in der [Nutzungsanleitung](docs/de/usage.md).

## Speicherung und Datenschutz

Websitedaten (Sites, Manifest `.project/specs/website.json`, Besitzprotokoll, Berichte, Arbeitsliste) liegen in deinem Websiteprojekt. Prozesszustand von `preview` und Sicherungen von `edit` liegen außerhalb des Repositories im Temp-Bereich. Im installierten Plugin wird nichts gespeichert. Ausgaben werden musterbasiert von bekannten Geheimnisfeldern bereinigt; das ist keine vollständige Erkennung. Details und bekannte Schutzgrenzen: [Speicherung](docs/de/storage.md).

## Projektstatus

- Etappen 1–5 der Migration sind nach unabhängigem Review für die Fortsetzung abgenommen; Etappe 6 (Gesamtprüfung, Dokumentation, lokale Marketplace-Anpassung) ist umgesetzt, **Review ausstehend**.
- Deterministisch geprüft (fiktive Fixtures, Fake-npm): Runtime-Logik der Skills. Nicht ausgeführt: echte npm-/Node-Läufe, native Claude-/Codex-Läufe, Modellurteile, Sichtprüfung.
- Bekannte Einschränkung zwischen `edit` und `setup`: Nach einer Änderung an einer von `setup` erzeugten Datei stimmt der gespeicherte Besitzhash nicht mehr. Ein erneutes `create` ergibt dann `conflict`, `verify` behält die Datei (`modified (kept)`); es gibt kein Neuaufsetzen der Hashes.
- Die Abnahmematrix (R1–R26, je Skill und Host) steht in [acceptance.md](docs/migration/acceptance.md).

## Entwicklung

Regeln: [AGENTS.md](AGENTS.md), [Architektur](docs/architecture.md), [SCOPE.md](SCOPE.md). Tests laufen mit `make test`; Struktur- und Quellprüfung mit `make verify`. Mehr in der [Entwicklungsanleitung](docs/de/development.md).

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
