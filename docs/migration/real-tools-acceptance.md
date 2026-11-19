# Bericht: echte Werkzeugabnahme (npm / Node / Astro) – Etappe 7

Migrationsnachweis, keine Produktdefinition. Maßgeblich bleibt [SCOPE.md](../../SCOPE.md). Gesamtmatrix: [acceptance.md](acceptance.md). **Review ausstehend.**

Diese Etappe belegt ausschließlich **echte Werkzeugläufe** (npm, Node, Astro) an einer fiktiven Site. Sie belegt weder das Laden eines Skills noch `allowed-tools` in Claude oder Codex (Hostabnahme offen), kein Modellverhalten und keine Sichtprüfung im Browser. Veröffentlicht, committet oder gepusht wurde nichts.

## 1. Umgebung

| Punkt | Wert |
|---|---|
| Datum | 2026-11-19 (UTC 17:00–17:10; lokale Zeit +01:00) |
| Betriebssystem | Darwin 27.2.0, arm64 (macOS) |
| Python | 3.15.0 |
| Node | v26.12.1 (`/opt/homebrew/bin/node`) |
| npm | 11.20.0 |
| Registry | `https://registry.npmjs.org/` (öffentlich, keine Tokens) |
| Runtime-Kopie | `skills/` und `plugin.json` des Repositories (HEAD `2c4a800`, Arbeitsbaum sauber), kopiert nach `<Arbeitsbereich>/plugin copy/`; 82 Dateien, SHA-256-Liste vor dem Lauf, nach den Läufen 0 Abweichungen, kein `__pycache__` |
| Quellabgleich | `python3 -B scripts/migration_baseline.py --inventory docs/migration/source-inventory.json --root <www.draftmode> --strict-git`: `files=130 changed=0 missing=0 … -> NO DRIFT`, Exit 0 (vor den Läufen). Die Quelle wurde nicht ausgeführt und nicht verändert. |

**Versionsspanne.** Templates und Runtime verlangen Node `>=22.23.4` (`package.json.tpl` `engines`, Prüfung in `optimize`); die aufgelösten Pakete verlangen u. a. `astro` `>=22.23.4`, `vite` `^20.19.0 || >=22.12.0`, `sharp` `>=20.9.0`. Geprüft wurde **nur Node v26.12.1 / npm 11.20.0**. Das belegt nicht die Untergrenze 22.23.4 und keine Zwischenversion; andere Betriebssysteme und Architekturen sind nicht geprüft. Ein Werkzeug wurde weder installiert noch aktualisiert.

**Isolierung (Arbeitsbereich mit Leerzeichen im Pfad:** `…/scratchpad/real npm run/`). Eigene Verzeichnisse für `HOME`, `TMPDIR` (Prozess-/Sicherungszustand), npm-Cache, leere `userconfig`/`globalconfig` (keine persönliche npm-Konfiguration, keine Tokens), eigene Git-Konfiguration (`GIT_CONFIG_GLOBAL`), `ASTRO_TELEMETRY_DISABLED=1`; `PYTHONPATH`, `NODE_OPTIONS`, npm-Tokens und `ZYRIS_WEBSITE_STATE_DIR` entfernt. Das fiktive Website-Repository (`fictional site/`, Domain `demo.example`) liegt im selben Bereich, außerhalb des Plugin-Repositories und ohne Symlinks zu echten Projekten. Es wurden nur die mit `setup` ausgelieferten Templates verwendet. Lokale Fixture-Commits (ausschließlich dort): initial, `setup create`, Testaufbau (doppeltes `<h1>`), `optimize apply`.

Der Hostprozess hatte `NODE_USE_SYSTEM_CA` gesetzt (unverändert übernommen, keine TLS-Prüfung abgeschaltet).

## 2. Vorabprüfung des externen Runners

Gelesen vor der Ausführung: `scripts/run_external_tests.py`, `tests/external/__init__.py`, `tests/external/setup/test_real_npm.py`.

- **Befehle:** `npm install`, `npm run build`, `npm run check` (über `static_setup`, `--build`); `npm` ohne Abhängigkeiten mit `node -e`-Skripten (Exitcodes 0/3/4).
- **Netzwerk:** nur die npm-Registry (Abhängigkeitsbaum von `astro`); keine anderen Ziele im Testcode.
- **Schreiben:** nur in `tempfile.mkdtemp()` (hier durch `TMPDIR` in den Arbeitsbereich gelenkt); `-B`/`PYTHONDONTWRITEBYTECODE`, kein Schreiben ins Repository. Die Temp-Ordner der Tests werden von den Tests selbst nicht gelöscht; ich habe sie nach dem Lauf entfernt.
- **Prozesse:** keine Dauerprozesse; nur kurzlebige npm-/Node-Aufrufe.
- **Aktivierung:** per Modulflag `tests.external.ENABLED` durch `--approved`; Umgebungsvariablen aktivieren nichts (`tests/contracts/test_external_separation.py`: 3 Tests OK, vor und nach der Ergänzung).

## 3. Schritte, Befehle, Ergebnisse

Alle Läufe aus dem Arbeitsverzeichnis `…/fictional site/` (Website-Projekt), Skripte aus `…/plugin copy/skills/<skill>/scripts/`, immer `python3 -B <Skriptpfad>` als ein Argument. Die Rohausgaben (stdout, stderr, Meta mit Befehl/Exit/Dauer) liegen unter `…/real npm run/logs/`.

### 3.1 Externer Runner (vorhanden)

| Lauf | Befehl (Arbeitsverzeichnis: Plugin-Repository) | Exit | Dauer | Ergebnis |
|---|---|---|---|---|
| 1. Versuch | `python3 -B scripts/run_external_tests.py --approved` | 1 | 1 s | **Umgebungsfehler, von mir verursacht:** `npm_config_userconfig` und `npm_config_globalconfig` zeigten auf dieselbe Datei (`double-loading config … as "global", previously loaded as "user"`); 3 Tests scheiterten mit Install-Exit 1. Kein Produktbefund. Konfiguration korrigiert, Log unter `logs/attempt1-misconfig/`. |
| 2. Versuch | derselbe Befehl | 0 | 23 s | `Ran 3 tests … OK`, 0 Skips, 0 Fehler (kalter npm-Cache: der erste echte Registry-Lauf) |
| nach Ergänzung | derselbe Befehl | 0 | 24 s | `Ran 4 tests … OK`, 0 Skips, 0 Fehler (3 vorhandene + neuer Test, siehe 3.6) |

Abdeckung des vorhandenen Runners: `setup create --build` (Install/Build/Check mit Exit 0, `package-lock.json` angelegt, Wiederholung `unchanged`), Fehlerfall Build (kaputte Seite → `failed-build`, Check nicht gelaufen) mit anschließendem `verify`, `adopt` mit echten Prozess-Exitcodes ohne Abhängigkeiten (Check 4 → `failed-check`, Build 3 → `failed-build`). **Nicht abgedeckt** waren `optimize`, `edit`, `preview` und der Echtlauf von `setup verify` mit Dokumentation von Lockfile/Versionen; diese wurden einmal manuell (3.2–3.5) und dann als wiederholbarer externer Test ergänzt (3.6).

### 3.2 setup

| Schritt | Befehl | Exit | Dauer | Ergebnis |
|---|---|---|---|---|
| create | `site_setup.py create demo.example --type astro-static --title "Demo Example" --port 4399 --build --json` | 0 | 4 s (Cache warm) | `created`; install 0, build 0, check 0; `lockfile: created` |
| verify | `site_setup.py verify demo.example --json` | 0 | 1 s | `verified`; install/build/check 0; `lockfile: unchanged` |

Der Port 4399 wurde gewählt, weil auf 4321 und 4331 **fremde** Dev-Server liefen (siehe 5); sie wurden nicht berührt.

Belegt: `.project/specs/zyris-website.json` (Manifest: `$schema` `./website.schema.json`, `version` 1, eine Komponente `demo.example`, `astro-static`, Port 4399); `.project/specs/website.schema.json` byte-gleich der Plugin-Schemadatei; Besitzprotokoll `.project/specs/zyris-website.managed.json` mit Hashes aller geschriebenen Dateien (Schemakopie, 43 Site-Dateien); `.gitignore` (`.tmp/`) und Site-`.gitignore` (`node_modules/`, `dist/`, `.astro/` git-ignoriert bestätigt); Artefakt `sites/demo.example/dist/` mit `index.html` (`<title>Demo Example</title>`, Canonical `https://demo.example/`), `404.html`, `sitemap.xml`, `robots.txt`.

**`package-lock.json`:** durch `create` neu angelegt (npm), `lockfileVersion` 3, 312 Pakete, SHA-256 `4f3320eb…06f7a`; `verify` änderte sie nicht (identischer Hash nach `verify` und nach `edit`). Wurzelabhängigkeit `astro ^7.4.10`, aufgelöst: **astro 7.4.13**, vite 8.3.8, sharp 0.35.5, zod 4.6.7. (Die Auflösung ist ein Zeitpunktnachweis der Registry vom Prüftag.) Das Lockfile gehört in das Versionsmanagement der Person; in der Fixture wurde es lokal committet.

### 3.3 optimize (echtes npm, kein Fake-npm-Schalter)

| Schritt | Befehl | Exit | Dauer | Ergebnis |
|---|---|---|---|---|
| audit (sauber) | `audit.py audit --site demo.example` | 0 | 1 s | `clean-with-warnings`; build 0, seo 0, a11y 0; Befund SEO-001 (`seo.title-too-short`, Titel „Demo Example“ = 12 Zeichen) |
| Testaufbau | In `src/pages/index.astro` den Lead-Absatz durch `<h1 class="page-header__lead">Fixture duplicate heading</h1>` ersetzt, lokal committet | – | – | **Manipulation der Fixture**, kein Produktbefund |
| audit (Fehler) | derselbe Befehl | 1 | 1 s | `errors`; build 0, **seo 1**, a11y 0; neuer Befund SEO-002 (`seo.h1-count`, „expected exactly one <h1>, found 2“); `readonly_violations: []` |
| direkt, getrennt | `npm run build` / `npm run seo:check` / `npm run a11y:check` in der Site | 0 / **1** / 0 | je ≤ 1 s | Exitcodes stimmen mit denen im Bericht überein |
| propose | `audit.py propose --site demo.example --proposals proposals.json` | 0 | 0 s | konkreter mechanischer Vorschlag für SEO-002 (Datei, `find`, `replace`) |
| decide | `audit.py decide SEO-002 --status approved --reason … --site demo.example` | 0 | 0 s | genau SEO-002 freigegeben; SEO-001 bleibt `proposed` |
| apply (falscher Befund) | `audit.py apply SEO-001 --site demo.example` | 1 | 0 s | `STOP: SEO-001 is proposed, not approved: nothing is changed` |
| apply | `audit.py apply SEO-002 --site demo.example` | 0 | 2 s | `clean-with-warnings`; build 0, seo 0, a11y 0; SEO-002 → `resolved`; `readonly_violations: []` |

Erwartete und tatsächliche Dateiänderung: erwartet genau eine Ersetzung in `sites/demo.example/src/pages/index.astro`; tatsächlich `git diff` mit genau dieser einen Zeile, die Datei ist nach `apply` **byte-gleich** der Fassung vor dem Testaufbau; sonst nur neue Dateien unter `.project/reports/demo.example/` (drei Schnappschussberichte `optimize/<Zeitstempel>.md`, Arbeitsliste `optimize.md`: SEO-001 offen, SEO-002 unter „Done“ mit Evidenz). `package-lock.json`, `rules/`, `package.json` unverändert. Der Adapter verarbeitete die tatsächliche Ausgabe der ausgelieferten Prüfskripte (Warnung und Fehler richtig klassifiziert, Exitcodes aus den Prozessen). Kein Prüfskript, keine Regel und kein Kriterium wurde verändert. Nicht freigegeben und nicht angewendet: SEO-001.

### 3.4 edit

| Schritt | Befehl | Exit | Dauer | Ergebnis |
|---|---|---|---|---|
| preflight | `edit.py preflight demo.example --root <Projekt>` | 0 | 1 s | `ready`, Ziel `src/pages/index.astro` |
| begin | `edit.py begin --root <Projekt> --site demo.example` | 0 | 0 s | Sitzung in `<TMPDIR>/zyris-website/<hash>/edit-demo.example-<UTC>/` (außerhalb von Projekt und Plugin) |
| replace | `edit.py replace --state … --find '<p class="page-header__lead">demo.example</p>' --replace '<p class="page-header__lead">Edited fictional lead EDITMARKER7431 for demo.example</p>'` | 0 | 0 s | `written`, neuer Hash `a8c63a5a…` |
| check | `edit.py check --state …` | 0 | 1 s | `checked`; build 0, check 0 (echtes npm); `checked_sha` = Hash der geschriebenen Datei |
| diff | `edit.py diff --state …` | 0 | 0 s | eine Zeile geändert |
| finish (ohne `--visual-done`) | `edit.py finish --state …` | 0 | 0 s | `outcome: "technically checked, visual check open"`, `technical: passed`, **`visual: open`** |

Belegt: Hashbindung (`original_sha` `cc5315e3…` = Hash der committeten Fassung; `checked_sha` = Hash der Datei nach Schreiben); die Sicherung `original/src/pages/index.astro` ist byte-gleich der committeten Fassung; `git status` zeigt nur `src/pages/index.astro` als geändert; `package-lock.json` unverändert. Die Sichtprüfung wurde nicht durchgeführt und nicht simuliert.

**Bekannte Besitzhash-Abweichung nach `edit`:** `setup verify` nach der Änderung: Exit 0, `verified`, `lockfile: unchanged`, Änderung `sites/demo.example/src/pages/index.astro` → `keep`, „modified (kept)“; das Besitzprotokoll blieb byte-gleich (SHA-256 vor/nach gleich). Kein Rebaselining, kein erneutes `create`. Das entspricht dem dokumentierten Verhalten.

### 3.5 preview (echter Astro-Dev-Server)

| Schritt | Befehl | Exit | Dauer | Ergebnis |
|---|---|---|---|---|
| Port vorab | `lsof -nP -iTCP:4399 -sTCP:LISTEN` | – | – | frei |
| start | `control.py start demo.example --root <Projekt> --timeout 90` | 0 | 1 s | `running-new`, Port 4399, PID 79440 (Prozessgruppenleiter), Listener `127.0.0.1:4399` (IPv4), Ownership-Beweis (`matched_on` u. a. pid, pgid, process_start_time, port_listener_in_group) |
| status | `control.py status demo.example --root <Projekt>` | 0 | 0 s | `running-reused` |
| inspect | `control.py inspect demo.example --root <Projekt> --expect EDITMARKER7431` | 0 | 0 s | `page-confirmed`, `process: ours`, `visibility_checked: false` |
| inspect (Gegenprobe) | `… --expect NOT-ON-PAGE-9999` | 1 | 1 s | `page-stale` |
| HTTP-Gegenprobe | `curl http://127.0.0.1:4399/` | – | – | HTTP 200, Text `EDITMARKER7431 for demo.example` im ausgelieferten HTML |
| stop | `control.py stop demo.example --root <Projekt>` | 0 | 0 s | `stopped` |
| danach | `status` / `lsof` / `ps` | 0 | – | `not-running`; kein Listener auf 4399; 0 Prozesse mit dem Arbeitsbereich im Befehl |

Das ist HTTP-/Runtime-Evidenz, **keine Browser-Sichtprüfung**. Der Dev-Server wurde nur über die preview-Runtime gestartet und beendet. Die Fremdprozesse auf 4321 und 4331 liefen unverändert weiter.

### 3.6 Ergänzter externer Test

`tests/external/website/test_real_tools.py` (neu, mit `__init__.py`): wiederholt in einer temporären Struktur mit Leerzeichen (Kopie von `skills/`, fiktives Git-Repository, privates `TMPDIR`, freier Port) die Folge setup (create/verify) → optimize (audit mit Testaufbau, propose/decide/apply, Wiederholung) → edit (begin/replace/check/finish ohne `--visual-done`) → preview (start/inspect/stale/stop/status) mit echtem npm. Aktiviert nur über `run_external_tests.py --approved`; ohne Freigabe `skipped`, von den Standardschichten nicht erfasst. Er läuft mit der Umgebung des Aufrufers (eigene npm-Konfiguration/Cache sind Sache des Aufrufers; für diese Abnahme wie in Abschnitt 1). Ein erster Versuch scheiterte an einem Fehler im Test selbst (falsche Auswahl der Befund-ID, weil im Test kein Vor-Audit lief); Auswahl nach Kriterium `seo.h1-count` korrigiert, danach Lauf OK (Log `logs/runner2-attempt-testbug.err`).

## 4. Nicht ausgeführt

- `publish`: keine Ausführung (Platzhalter ohne Runtime) – **NOT RUN / n/a**.
- Hostläufe in Claude/Codex (Skillladen, Pfadvariable, `allowed-tools`, Erreichbarkeit von `_shared`/`preview`): **NOT RUN**.
- Modellurteile und Sichtprüfung im Browser: **NOT RUN**.
- Weitere Node-/npm-Versionen und Plattformen: **NOT RUN**.
- Negativfälle mit echtem npm jenseits der unter 3.1 genannten (z. B. optimize mit fehlgeschlagenem Build, Registry-Ausfall, TLS-/Proxy-Fehler): **NOT RUN**; die Schutzlogik außerhalb der Ausgabeorte (verbotene Dateien, Pfade außerhalb der Site) ist weiter nur deterministisch belegt; im Echtlauf belegt: `readonly_violations: []`, nur die genehmigte Datei geändert.

## 5. Befunde

Keine Produktdefekte in Runtime, Templates oder Prüfskripten gefunden. Beobachtungen für den Review (nicht repariert, nichts abgeschwächt):

1. **Dokumentation ↔ Verhalten (`.claude/launch.json`) – Text korrigiert (Nachkorrektur).** Die Texte nannten die Datei pauschal „git-ignored“; in der frischen Fixture erscheint `.claude/` nach `preview start` als `?? .claude/` (`setup` ergänzt nur `.tmp/`). Korrigiert in `skills/_shared/references/interfaces.md` und `skills/preview/references/preview.md`: `preview` erzeugt und pflegt seinen Eintrag; ob die Datei git-ignoriert ist, hängt von den Regeln des Websiteprojekts ab, das Plugin ergänzt keine Ignore-Regel. Keine Änderung an `setup`, Templates oder `.gitignore`-Verhalten.
2. **Fremde Dev-Server auf Standardports.** Während der Läufe lauschten fremde Prozesse auf `127.0.0.1:4321` (Dev-Server der echten Quellsite) und `:4331` (anderes Testprojekt außerhalb dieses Auftrags). Sie wurden weder inspiziert noch beendet; der Port der Fixture wurde auf 4399 gelegt. Der Standardport 4321 wäre ein `port-conflict` gewesen (dieser Fall wurde mit echtem Prozess **nicht** ausgeführt).
3. **Hinweis:** Die `launch.json`-URL und die `preview`-Meldung nennen `http://localhost:4399/`; der Listener war tatsächlich `127.0.0.1:4399` (IPv4). Kein Defekt, aber „localhost“ ist nicht „127.0.0.1“ im Wortlaut.

## 6. Zustand nach den Läufen

- **Testprozesse:** keine. Der eigene Dev-Server wurde mit `stop` beendet; kein Listener auf 4399; `ps` zeigt keinen Prozess mit dem Arbeitsbereich im Befehl. Nur Prozesse, die die Runtime selbst gestartet hatte, wurden beendet; fremde Prozesse nicht angefasst.
- **Fixture-Verzeichnisse:** Arbeitsbereich `/private/tmp/claude-501/-Users-peterfux--claude-spares-spare-I2Ca3d/1ba40765-81dd-4cfb-96fb-c70382d6d38e/scratchpad/real npm run/` (≈ 439 MB: `fictional site/` mit `node_modules`, `npm-cache/`, `plugin copy/`, `logs/`, `tmp/zyris-website/…/edit-demo.example-…` als erhaltene Sicherung der edit-Sitzung). Er wurde für den Review nicht gelöscht; er liegt im sitzungsgebundenen Scratchpad und kann bei Bereinigung verschwinden. Die vom externen Runner erzeugten Temp-Ordner (`tmp*`) wurden nach den Läufen entfernt. Die vom externen Test erzeugte Struktur (`website real tools …`) wird nach der Nachkorrektur nur nach bestandenem Test und bestätigtem Ende der eigenen Prozesse gelöscht (siehe Abschnitt 7); sonst bleibt sie erhalten und ihr Pfad wird ausgegeben.
- **Plugin-Repository:** keine Änderung an Produkt-Runtime, Templates, Skillumfang, Marketplace oder SCOPE-Acceptance; kein `__pycache__`, kein `node_modules`, keine Build-Ausgabe, kein Cache im Repository. Keine Commits, kein Push, keine Veröffentlichung.
- **Fixture-Git:** vier lokale Commits im Fixture-Repository (nur dort), nicht im Plugin-Repository.

## 7. Nachkorrektur (Test-Aufräumlogik, Dokumentation)

Die Läufe oben bleiben als begrenzte Evidenz unverändert; es gab keinen erneuten echten npm-Lauf.

- **Aufräumlogik** (`tests/external/website/test_real_tools.py`, Regeln in `tests/support/external_cleanup.py`): Das Aufräumen wird in `setUp` vor dem ersten Aufruf registriert und prüft den Preview-Zustand immer über den Controller (`control.py status`; bei eigenem laufenden/startenden Server `stop`, danach erneut `status`). Bei Timeout, `TimeoutExpired`, unlesbarer Ausgabe, unklarem Besitz (`unknown-owner`, `insufficient-evidence`, unbekannter Zustand) wird nichts signalisiert. Nie nach Port oder vermuteter PID. Die Fixture wird nur nach bestandenem Test **und** bestätigtem Ende der eigenen Prozesse gelöscht (`rmtree` ohne `ignore_errors`); sonst bleiben Fixture, Logs und Zustandsdaten erhalten und der Pfad wird ausgegeben. Ein Testfehler wird nicht durch einen Cleanup-Fehler verdrängt; nur bei bestandenem Test mit ungeklärtem Prozesszustand schlägt das Aufräumen selbst fehl.
- **Regressionsnachweis (deterministisch, Fakes):** `tests/unit/external_cleanup/test_real_tools_cleanup.py` (16 Tests): Startaufruf mit Timeout bei weiterlaufendem eigenem Server, `TimeoutExpired`, unlesbare Ausgabe, fehlschlagender oder zeitüberschreitender `stop`, `stop` ohne Wirkung, unklarer Besitz, Erhalt der Fixture, Pfadausgabe, Löschfehler nicht verborgen, Registrierung vor dem ersten Aufruf, keine Signale nach Port/PID.
- **Dokumentation `.claude/launch.json`:** siehe Abschnitt 5, Punkt 1 und [changes.md](changes.md) (Nachkorrektur Etappe 7). Vertragstest `LaunchJsonIgnoreStatement` in `tests/contracts/test_documentation_contract.py`.
- **Nachweiskonsistenz:** pauschale NOT-RUN-Aussagen zu echten Werkzeugläufen in `README.md`, `README.en.md`, `docs/de|en/faq.md`, `docs/prerequisites.md` und `SCOPE.md` auf den tatsächlich geprüften Stand begrenzt (Node v26.12.1/npm 11.20.0, Darwin arm64, fiktive Site); weitere Versionen und Plattformen, Hostläufe, Modell und Sicht bleiben offen.
