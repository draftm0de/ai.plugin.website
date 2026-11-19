# Voraussetzungen / Prerequisites

Diese Datei beschreibt die Voraussetzungen des **Website-Plugins**. Globale Verwaltungsregeln, Voraussetzungen der Verwaltungswerkzeuge, Marketplace-Verwaltung und Veröffentlichung gehören dem Plugin Manager (`/plugin-manager`) und stehen nicht hier.

This file describes the prerequisites of the **Website plugin**. Global management rules, prerequisites of the management tools, marketplace management and publication belong to the Plugin Manager (`/plugin-manager`) and are not listed here.

## Deutsch

### Laufzeit der Skills

Belegt aus den Skills und ihren Referenzen (`skills/*/SKILL.md`, `skills/*/references/`), den Templates und `docs/migration/host-conventions.md`; die Wirkung auf Claude und Codex ist nicht per Hostlauf belegt (NOT RUN).

- **Python 3.10 oder neuer**, nur Standardbibliothek, keine zusätzlichen Pakete. Aufruf als `python3 -B` mit dem Skriptpfad als einem Argument, ohne `PYTHONPATH`. Lokal ausgeführt wurde nur Python 3.15; echte Node-/npm-Läufe nur mit Node v26.12.1/npm 11.20.0.
- **Git** mit mindestens einem Commit im Websiteprojekt (`optimize`, `edit`).
- **Node 22.23.4 oder neuer und npm** für Build und Prüfungen der Site; die Abhängigkeiten (`node_modules/`, `package-lock.json`) installiert die Person im Site-Ordner selbst (`npm install` bzw. `npm ci`). `preview`, `optimize` und `edit` installieren nie; `setup verify` bzw. `--build` führt die in der Site deklarierte Installation (Netzwerk, npm-Registry) nur auf ausdrücklichen Auftrag aus; Werkzeuge installiert kein Skill.
- **`ps` und `lsof`** für `preview` (Besitznachweis); fehlen sie, startet und signalisiert `preview` nichts.
- **Browserwerkzeug des Hosts** (optional) für die Sichtprüfung; ohne tatsächliche Ansicht bleibt sie offen.
- Zugriff nur auf das ausdrücklich gewählte Websiteprojekt; Zustand außerhalb des Repositories im Temp-Bereich. Keine Netzwerkzugriffe der Skills außer lokal auf `127.0.0.1` (Preview) und den npm-Läufen der Site.

### Entwicklung dieses Repositories

Für `scripts/verify.py`, `scripts/plugin.py` und `scripts/run_tests.py` genügen Git und Python 3.10 oder neuer (nur Standardbibliothek); Make ist optional ([Entwicklung](de/development.md)). Alles Weitere zu Verwaltungswerkzeugen und Marketplaces regelt der Plugin Manager.

## English

### Skill runtime

Evidenced by the skills and their references (`skills/*/SKILL.md`, `skills/*/references/`), the templates and `docs/migration/host-conventions.md`; the effect on Claude and Codex is not evidenced by a host run (NOT RUN).

- **Python 3.10 or newer**, standard library only, no additional packages. Invoked as `python3 -B` with the script path as one argument, without `PYTHONPATH`. Only Python 3.15 was run locally; real Node/npm runs only with Node v26.12.1/npm 11.20.0.
- **Git** with at least one commit in the website project (`optimize`, `edit`).
- **Node 22.23.4 or newer and npm** for the site's build and checks; the person installs the dependencies (`node_modules/`, `package-lock.json`) in the site folder themselves (`npm install` or `npm ci`). `preview`, `optimize` and `edit` never install; `setup verify` or `--build` runs the site's declared install (network, npm registry) only on explicit order; no skill installs tools.
- **`ps` and `lsof`** for `preview` (ownership proof); if missing, `preview` starts and signals nothing.
- **Host browser tool** (optional) for the visual check; without an actual view it stays open.
- Access only to the explicitly selected website project; state outside the repository in the temp area. No network access by the skills except locally on `127.0.0.1` (preview) and the site's npm runs.

### Developing this repository

`scripts/verify.py`, `scripts/plugin.py` and `scripts/run_tests.py` need only Git and Python 3.10 or newer (standard library only); Make is optional ([Development](en/development.md)). Everything else about management tools and marketplaces is governed by the Plugin Manager.
