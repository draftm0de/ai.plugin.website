# Entwicklung

**Deutsch** | [English](../en/development.md)

[Start](../../README.md) · [Übersicht](README.md) · [Installation](installation.md) · [Nutzung](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Kanonische Quelle

- Das Produktzielbild ist [SCOPE.md](../../SCOPE.md) (R1–R25, R29–R34). Es trennt das bestätigte Soll vom Implementierungsbeleg. Entwicklungsregeln: [AGENTS.md](../../AGENTS.md) und [Architektur](../architecture.md). Lies beides vor jeder Änderung; fachliche Lücken werden nicht durch nachträgliche Soll-Änderungen versteckt.
- Die Plugin-Identität steht in `plugin.json` (Name `website-manager`, Anzeigename „Website Manager“, keine Version). `.claude-plugin/plugin.json` wird daraus abgeleitet (`make sync-plugin`, Kontrolle mit `make check-plugin`). Das Plugin-Repository besitzt **keine** Marketplace-Kataloge; sie gehören dem Marketplace-Repository `ai.plugins`.
- Die Skills liegen unter `skills/<skill>/` (`SKILL.md`, `scripts/`, `references/`, `templates/`); gemeinsame Laufzeit und das Manifest-Schema unter `skills/_shared/` (ohne `SKILL.md`). Das Wurzelverzeichnis `scripts/` enthält nur Entwicklungswerkzeuge.
- Die ausgelieferte Laufzeit enthält keine Entwicklerpfade und hängt nicht vom früheren Quellcheckout, von `ai.plugins` oder vom Coach-Checkout ab.
- Voraussetzungen: [Voraussetzungen](../prerequisites.md) (Website-Laufzeit; für dieses Repository Git und Python 3.10+, nur Standardbibliothek; Make ist optional). Globale Verwaltungsregeln gehören dem Plugin Manager.

## Prüfungen

Struktur, Quellreview und Tests sind getrennte Schritte:

```sh
python3 -B scripts/verify.py --source . --kind plugin            # Struktur, lesend
python3 -B scripts/verify.py --source . --kind plugin --review   # Scope-/Source-Review, lesend
python3 -B scripts/plugin.py check                               # Host-Manifest ohne Drift
python3 -B scripts/run_tests.py --kind deterministic             # Unit-, Integrations- und Vertragstests
```

- `make verify` und `make verify REVIEW=1` entsprechen den ersten beiden Befehlen. Der Review startet keine Zielruntime. Meldet er offene Hostnachweise (`needs_attention`), werden Scope, Regeln oder Prüfer nicht abgeschwächt.
- `make test` (Ebenen `tests/unit`, `tests/integration`, `tests/contracts`) verwendet ausschließlich fiktive Fixtures und ein Fake-`npm`; Netzwerk und echtes Node werden nicht benutzt. Die Preview-Tests starten eigene lokale Prozesse auf `127.0.0.1` und beenden nur eigene, eindeutig identifizierte Testprozesse. Übersprungene Tests gelten nie als bestanden.
- `tests/external/` (echtes `npm`, Netzwerk) gehört zu keiner Standardebene und läuft nur über `scripts/run_external_tests.py --approved` nach gesonderter Freigabe; ohne Freigabe meldet es `NOT RUN`. Geerbte Umgebungsvariablen schalten es nicht frei.
- `tests/native/` und `tests/behavior/` (Host- und Modelltests) laufen nie im Standardlauf; es gibt keine ausgeführte Suite (`NOT RUN`). `tests/behavior/edit_cases.md` ordnet die manuellen Fälle der Quelle ein, ohne sie auszuführen.
- Neue Tests sollen tatsächliche Risiken abdecken (defekte Links, Manifestdrift) und ersetzen keinen Dokumentationsreview. Strukturprüfungen belegen kein Produktverhalten.

## Paketierung

Es gibt keine ZIP-Verteilung und keinen Paketbau. Lokale Tests ohne GitHub:

```sh
make update-local TARGET=claude DRY_RUN=1
```

- `install-local`/`update-local` (`TARGET=claude|codex`) legen Snapshots des aktuellen Checkouts einschließlich uncommitteter Änderungen an und setzen die gewählte Host-CLI voraus (`DRY_RUN=1` erzeugt nur den Snapshot). Nach Änderungen oder Branchwechseln `update-local` ausführen und eine neue Host-Sitzung öffnen. Kein Commit, Push oder PR ist dafür nötig. Kopiere nie in Host-Caches.
- Marketplace-Verwaltung (Kataloge, lokale Zuordnungen, Veröffentlichung) gehört ausdrücklich dem Plugin Manager (`/plugin-manager`); das Website-Plugin bietet dafür keine Funktion. Lokale Zuordnungen stehen in der ignorierten Datei `.local/marketplace.json` (reguläre Einrichtung über `configure` des Plugin Managers). Vor der Katalogänderung dieser Etappe meldete `make verify` unter `local_development`, das Plugin sei im gewählten Marketplace nicht registriert; nach der Umbenennung des Katalogeintrags auf `website` meldet es `complete`. Das ist eine Strukturprüfung der lokalen Konfiguration (die Datei wurde in dieser Etappe nicht angelegt oder verändert), kein Nachweis einer Installation oder eines Hostimports.

## CI und Releases

Die vorbereitete CI führt `make test` und `make check-plugin` aus; ihre Existenz belegt keinen erfolgreichen Lauf. Es gibt keine Release-Actions, manuell gepflegten Versionen, Tags oder Plugin-ZIPs. Veröffentlichung läuft nur nach konkreter Freigabe über Feature-Branch, Commit, Push, PR, Checks und Merge (siehe Plugin Manager). Diese Etappe führte keinen Commit, Push, Tag, Release oder Deployment aus. Der lokal angepasste Katalogeintrag in `ai.plugins` beweist weder einen Push noch die Erreichbarkeit des Plugin-Repositories noch einen Hostimport.

## Dokumentation pflegen

Deutsch ist die Standardsprache, Englisch gleichwertig: Aussagen, Befehle, Grenzen und Status müssen in beiden Sprachen übereinstimmen und werden gemeinsam geändert. Die Seiten erklären das Verhalten und verlinken [SCOPE.md](../../SCOPE.md), statt Verträge zu duplizieren. `docs/documentation.json` verweist mit den vom Plugin Manager unterstützten Feldern (`source_skill`, `extra_sources`) auf die kanonischen Quellen. Beispiele sind als erfunden zu kennzeichnen; echte Screenshots nur mit Host, Sprache und Datum. Keine absoluten Entwicklerpfade in Nutzerseiten. Ein Vertragstest prüft interne Links, die Entsprechung von `docs/de` und `docs/en` und die Vollständigkeitszuordnung; er ersetzt den fachlichen Review nicht.

---

Dokumentation erstellt mit Plugin Manager. Die Urheberschaft des beschriebenen Produkts bleibt unverändert.
