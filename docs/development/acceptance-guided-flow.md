# Abnahmematrix: geführter Website-Ablauf

Stand: 2026-11-20, nur Quellstand. Diese Matrix ist keine Abnahme. Sie trennt, was deterministisch belegt ist, von dem, was eine Host-,
Gesprächs-, Astro- oder Sichtabnahme noch braucht. Maßgeblich bleiben SCOPE.md (R29 bis R34) und `guided-flow.md`.
Alle Namen und Inhalte sind fiktiv: Firma „Praxis Beispiel“ (fiktive Physiotherapie, Wien), Site-ID `physio-wien`, Domain `demo-a.com`
(nur als Testwert; kein echtes Projekt, keine echten Inhalte).

## Vorab: Stand der Belege (heute tatsächlich gelaufen)
| Prüfung | Ergebnis |
|---|---|
| Gesamtlauf `scripts/run_tests.py` (Unit, Integration, Vertrag; Fake-npm, kein Netz) | 944 Tests, OK |
| Für die Matrix einzeln wiederholt: `test_without_git` 3, `test_manifest_v2` 24, `test_package_setup` 5, `test_flow_state` 31, `test_flow_review_regressions` 29, `test_consistency` 17, `test_guided_flow_contract` 6, `edit/test_writes` 27 | alle OK |
| `verify --review` | `ready_for_source_review`, 0 Befunde (Evidenzzeiger, kein inhaltlicher Review) |
| Werkzeuge auf diesem Rechner (nur gelesen) | Node v26.12.1, npm 11.20.0, Python 3.15.0 |

Nicht gelaufen: alles in der Spalte „Fehlt“ unten. Die früheren echten npm/Astro-Läufe (Etappe 7) betreffen das Skeleton vor Version 2 und gelten dafür nicht.

## Matrix
Abkürzungen: **Det** = deterministischer Nachweis vorhanden (Datei · Klasse), **Host** = Claude/Codex-Lauf, **Gespr** = Gesprächsverhalten des Modells,
**Astro** = echtes npm/Astro, **Sicht** = Blick in einen Browser.

| # | Fall | Det (vorhanden) | Fehlt |
|---|---|---|---|
| 1 | Neues Projekt ohne Git, ohne Domain | `test_manifest_v2` (`IdentityAndDomainTests`: ohne Domain kein `domain`, kein `site`, `SITE = null`, keine erfundene URL; `DomainlessLocalWorkTests`: Resolver, preview, edit-Preflight, verify), `test_without_git` (kein `.git`), `test_flow_state` (`EntryAndStatusTests`: leeres Projekt → `setup`, `status` schreibt nichts, domainloses Projekt → `brief`), `test_package_setup` (Setup aus dem erzeugten Claude- und Codex-Paket), `NewVersusIncompleteProjectTests` (Reste ohne Manifest ≠ neues Projekt) | Host, Gespr, Astro |
| 2 | Einstieg mit Domain und Firmenbeschreibung | `test_manifest_v2` (`--domain` wird gespeichert, `astro.config`/`site.ts` konsistent, `set-domain` später), `test_flow_state` (Status mit Domain), `test_guided_flow_contract` (Skilltext: Angaben übernehmen, keine Domain erfinden, keine Ein-Wort-Garantie) | Host (Aktivierung, Skill laden), Gespr (Übernahme aus dem Satz, keine Doppelfragen), Astro |
| 3 | Briefing mit Rückfragen, iterative Farbwahl | `test_flow_state` (`BriefTests`: unvollständig → Wiederaufnahme, Bestätigung nur mit Aussage, strenges Format, Palette, identisch = keine neue Revision, Website- ≠ Bedienersprache), `BriefAndHistoryTests` (History nie überschrieben) | Gespr (gebündelte Fragen, Palettenvorschläge mit Begründung, mehrere Runden), Host |
| 4 | ≥ 2 unterschiedliche Prototypen | `test_flow_state` (`DesignTests`: eine Variante/Farbwechsel abgelehnt, Lorem/Preise/Zahlen/Qualifikationen nur als `data-open-fact`, Sprache, Palette, kein Script/extern, Vergleichsseite, Ablage außerhalb von `sites/`, Startseite unverändert) | Sicht (wirklich verschieden und brauchbar?), Gespr (Textqualität, keine erfundenen Tatsachen jenseits der Muster) |
| 5 | Feedback, neue Revision, ausdrückliche Freigabe | `test_flow_state` (Feedbackschleife, alte Revisionen bleiben, Präferenz ≠ Freigabe, Freigabe an Revision/Variante gebunden, neuere Revision macht alte Freigabe veraltet, Briefingänderung → veraltet, nichts gelöscht), `RegisteredArtifactIntegrityTests` (geänderte Vergleichsseite blockiert) | Gespr (Freigabefrage nennt Revision und Variante; „B gefällt mir“ wird nicht als Freigabe gewertet) |
| 6 | Umsetzung ohne zweite Designfreigabe | `ImplementationResumptionTests` (echtes `edit.py begin` und `write` → `implement-finish --edit-state` ohne neue Freigabe; Schreibumfang nur `index.astro`, `test_guided_flow_contract`) | Gespr (Entwurf wird sinnvoll in `index.astro` übersetzt), Astro (Seite baut), Sicht |
| 7 | Wiederaufnahme und Konflikt bei Nutzeränderung | `ImplementationResumptionTests` (Abbruch nach `write` → Wiederaufnahme, idempotent; Nutzeränderung nach `implement-start` → Konflikt; nur `check` ohne `write` abgelehnt; `--accept-current-page`), `test_flow_state` (Änderung nach Abschluss → `user-changed`), Beschädigung/History in `NestedStateValidationTests` und `BriefAndHistoryTests` | Host (neue Sitzung wirklich am passenden Punkt), Gespr (gezielte Nachfrage statt Überschreiben) |
| 8 | Technische und visuelle Prüfung der Startseite | `test_flow_state` (Prüfergebnis gebunden an den Hash der aktuellen Seite, `visual` ohne Notiz nicht `passed`, veraltet nach Änderung), `edit/test_writes` und `edit`-Tests (Fake-npm: `build`/`check`, Exitcodes) | Astro (echter Build und `check` des Version-2-Skeletons, mit und ohne Domain), Sicht (Seite im Browser, Prototyp vs. Umsetzung) |

## Vorhandene externe Tests: was sie abdecken und was nicht
`tests/external/` läuft nur über `python3 -B scripts/run_external_tests.py --approved` (echtes npm, Netz). Lauf heute: **nicht ausgeführt (NOT RUN)**.
| Test | Deckt ab (Fall) | Deckt nicht ab |
|---|---|---|
| `external/setup/test_real_npm.py` `test_s1_...` | Fall 1/8 technisch: echtes `npm install`, Build und `check` einer neuen Site, Lockfile angelegt, identische Wiederholung | Domain, Flow, Git-Freiheit (die Fixture ist ein Git-Repository) |
| `external/setup/test_real_npm.py` `test_s16_...` | Fall 7 nur für `setup`: defekte erzeugte Datei, Reparatur, `verify`, `create` danach = Konflikt | Flow-Konflikte (Briefing, Design, Umsetzung) |
| `external/setup/test_real_npm.py` `RealNpmProcessTests` | Exitcodes von npm ohne Netz | alles Fachliche |
| `external/website/test_real_tools.py` `test_end_to_end` | Fall 6/8 technisch am Rand: echtes `setup create/verify`, `optimize`, eine `edit`-Sitzung (`begin`, `replace`, `check`, `finish`), `preview start/inspect/stop` mit echtem Astro | Flow (`flow.py`), Briefing, Design, Freigabe, `implement-finish`, `set-domain`, Domain-Fälle, Sichtprüfung |

Einschränkungen, die ausdrücklich gelten:
- **Git:** beide Tests benutzen ein Git-Repository (`git init`, Commits) als Fixture. Das belegt **keinen** gitlosen Ablauf. Fall 1 (ohne Git) bleibt deshalb eine eigene manuelle Abnahme (Schritt A.1, Pfad ohne `git`).
- **Version 2:** beide Tests entstanden vor Manifest Version 2. `test_real_tools.py` nutzt `demo.example` als Site-ID ohne `--domain` und ersetzt danach `<p class="page-header__lead">demo.example</p>`. Dieses Element erzeugt das Version-2-Skeleton ohne Domain nicht mehr. Der Test würde dort sehr wahrscheinlich am `replace` scheitern und müsste vor einem Lauf angepasst werden (Folge: Änderung der Testdatei, nicht Teil dieser Vorbereitung). Bis dahin zählen die externen Tests **nicht** als Nachweis für den Version-2-Stand.
- Die manuellen Fälle A bis D unten bleiben auch nach einem späteren Lauf der externen Tests bestehen; sie decken Flow, Domain, Gitfreiheit und Sicht ab.

## Offene Abnahmefälle: Schritte und erwartetes Ergebnis
Reihenfolge so gewählt, dass jeder Schritt auf dem vorherigen aufbaut. Alles in Wegwerf-Ordnern, fiktive Inhalte.

### A. Astro-Abnahme (Fälle 1, 2, 6, 7, 8) mit Befehlen
**Voraussetzungen:** Node ≥ 22.23.4 (hier v26.12.1) und npm (hier 11.20.0) vorhanden; Netzwerkzugang zur npm-Registry (Download von Astro) und die Freigabe unten; Python 3; Schreibrecht im Wegwerf-Ordner. Der Quellstand muss die Prüfung bestanden haben (`scripts/run_tests.py`). Es wird das **erzeugte Paket** getestet, nicht der Quellordner.

**Ordner und Weiterverwendung** (alles unter einem Parent `ACC`):
| Ordner | Zweck | Wird verwendet in |
|---|---|---|
| `$ACC/package/` | aus dem Quellstand erzeugtes Website-Paket (nur Lesen) | alle Schritte (Scriptpfade) |
| `$ACC/tmp/` | eigenes `TMPDIR`; hier legen `edit` und `preview` ihren Zustand ab | alle Schritte; muss für `edit.py` und `flow.py` **gleich** sein |
| `$ACC/p-domainless/` | Projekt 1: ohne Git, ohne Domain; durchläuft den ganzen Flow (A.2, A.3, **A.4b**, A.5), am Ende `set-domain` (A.7) | Fälle 1, 3 bis 8 |
| `$ACC/p-domain/` | Projekt 2: von Anfang an mit Domain; nur Setup, Build, Prüfung der erzeugten Adressen (A.8) | Fall 2 |
| `$ACC/p-probe/` | Kopie von Projekt 1 nach der Freigabe (A.3); nur für die technische Schreibprobe A.4; wird danach **nicht** für Design- oder Sichtabnahme verwendet | A.4 |
| `$ACC/p-conflict/` | zweite Kopie von Projekt 1 nach der Freigabe (A.3); hier wird der Nutzerkonflikt erzeugt (A.6), damit Projekt 1 sauber bleibt | Fall 7 |

**A.0 Paket erzeugen und Umgebung** (schreibt nur nach `$ACC`; nutzt das eigene `scripts/plugin.py` des Website-Plugins, nicht das Marketplace-Werkzeug)
```bash
export PLUGIN=/Users/peterfux/PhpstormProjects/drafm0de/ai.plugin.website
export ACC="$(mktemp -d)"; export TMPDIR="$ACC/tmp"; mkdir -p "$TMPDIR"
python3 -B - <<PY
import importlib.util, os
from pathlib import Path
spec = importlib.util.spec_from_file_location("t", "$PLUGIN/scripts/plugin.py"); t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
_v, portable, claude = t.payload()
for name, data in claude.items():          # Claude-Nutzlast; für Codex t.codex_payload(portable)
    p = Path("$ACC/package") / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
PY
export PKG="$ACC/package"
export SETUP="$PKG/skills/setup/scripts/site_setup.py" FLOW="$PKG/skills/_shared/scripts/flow.py" EDIT="$PKG/skills/edit/scripts/edit.py" CONTROL="$PKG/skills/preview/scripts/control.py"
test -f "$SETUP" && test -f "$FLOW" && test -f "$EDIT" && test -f "$CONTROL" && test -f "$PKG/skills/setup/templates/astro-static/.gitignore.tpl"
```
Erwartet: alle `test -f` Exit 0 (auch die Punkt-Vorlage `.gitignore.tpl` ist im Paket).

**A.1 Fall 1: Setup ohne Git und ohne Domain** (Projekt 1)
Zwei verschiedene Dinge, die beide gelten müssen und getrennt geprüft werden: **„Git nicht verfügbar“** (das Programm `git` ist auf dem Suchpfad der Abnahme nicht auffindbar) und **„kein Git-Repository“** (weder das Projekt noch ein übergeordneter Ordner hat ein `.git`). „Kein Repository“ allein beweist keinen gitlosen Ablauf, weil ein vorhandenes `git` trotzdem aufgerufen werden könnte; „Git nicht verfügbar“ allein genügt nicht, wenn man versehentlich in einem Repository arbeitet.

Umgebung: ein eigener Werkzeugordner mit Verweisen nur auf die benötigten Programme (kein `git`), und **alle** Schritte A.1 bis A.8 laufen danach in derselben Shell mit diesem Suchpfad.
```bash
export P1="$ACC/p-domainless"; mkdir -p "$P1"; export S=physio-wien
mkdir -p "$ACC/nogit-bin"
for t in node npm python3 shasum grep cat cp mkdir head sed env mktemp dirname find tr sleep sh test ls rm; do
  ln -sf "$(command -v "$t")" "$ACC/nogit-bin/$t" 2>/dev/null || echo "ABBRUCH: Werkzeug fehlt: $t"
done
export NOGIT_PATH="$ACC/nogit-bin"
precheck() {                                   # Rückgabe 0 nur, wenn alles zutrifft; sonst Meldung "ABBRUCH" und Rückgabe 1
  local t d ok=0
  for t in node npm python3; do PATH="$NOGIT_PATH" command -v "$t" >/dev/null || { echo "ABBRUCH: $t ist auf dem Abnahme-Suchpfad nicht verfügbar"; ok=1; }; done
  PATH="$NOGIT_PATH" node --version >/dev/null 2>&1 && PATH="$NOGIT_PATH" npm --version >/dev/null 2>&1 && PATH="$NOGIT_PATH" python3 --version >/dev/null 2>&1 \
    || { echo "ABBRUCH: node, npm oder python3 laufen auf dem Abnahme-Suchpfad nicht"; ok=1; }
  if PATH="$NOGIT_PATH" command -v git >/dev/null 2>&1; then echo "ABBRUCH: Git ist verfügbar (Git nicht verfügbar ist Voraussetzung)"; ok=1; fi
  d="$P1"; while [ "$d" != "/" ]; do [ -e "$d/.git" ] && { echo "ABBRUCH: $d enthält .git (kein Git-Repository ist Voraussetzung)"; ok=1; }; d="$(dirname "$d")"; done
  return $ok
}
precheck && echo "VORPRÜFUNG BESTANDEN: Git nicht verfügbar und kein Git-Repository"
```
Bei jeder Ausgabe `ABBRUCH` (oder fehlender Zeile „VORPRÜFUNG BESTANDEN“): **sofort abbrechen**, keine weiteren Schritte ausführen, A.1 bis A.8 gelten als **NOT RUN (Umgebung)**; die Ursache beheben oder festhalten, nicht umgehen. Erst nach bestandener Vorprüfung:
```bash
export PATH="$NOGIT_PATH"                       # ab hier gilt für diese Shell: kein git
python3 -B "$SETUP" create "$S" --type astro-static --root "$P1" --build --json
test ! -e "$P1/.git"
```
Erwartet: `state: created`; `install`, `build`, `check` je Exit 0; `package-lock.json` angelegt; kein `.git`. Im Manifest `.project/specs/zyris-website.json` `version` 2 und **kein** `domain`; `astro.config.mjs` ohne `site`, `src/lib/site.ts` mit `SITE ... = null`; `.gitignore` der Site vorhanden. Das beweist auch den `.gitignore.tpl`-Weg aus dem Paket mit echtem npm.
Domainlose Ausgabe prüfen:
```bash
D="$P1/sites/$S/dist"
! grep -rl 'rel="canonical"' "$D"                                # keine Canonical-Adressen
python3 -c "import sys,xml.dom.minidom as m; d=m.parse(sys.argv[1]); print(len(d.getElementsByTagName('loc')), d.documentElement.tagName)" "$D/sitemap.xml"
! grep -i sitemap "$D/robots.txt"
```
Erwartet: kein Treffer für Canonical; `sitemap.xml` ist **gültiges XML** mit Wurzel `urlset` und **0** `loc`-Einträgen (leere Sitemap, kein 404, keine erfundene Adresse); `robots.txt` ohne `Sitemap:`-Zeile. `check` meldet nur die Warnung „no domain configured“, keinen Fehler.

**A.2 Briefing bestätigen** (Fall 3, technisch; die Gesprächsführung gehört zu C)
```bash
cat > "$ACC/brief.json" <<'JSON'
{"schema_version": 1, "fields": {
 "purpose": {"value": "Praxis-Website mit Terminanfrage (fiktiv)", "status": "confirmed"},
 "audience": {"value": "Berufstätige mit Rückenschmerzen in Wien (fiktiv)", "status": "confirmed"},
 "offer": {"value": "Physiotherapie und Rückenkurse", "status": "confirmed"},
 "message": {"value": "Beweglich bleiben, im eigenen Tempo", "status": "confirmed"},
 "visitor_action": {"value": "Termin anfragen", "status": "confirmed"},
 "tone": {"value": "ruhig, klar, persönlich", "status": "confirmed"},
 "site_language": {"value": "de", "status": "confirmed"},
 "design_direction": {"value": "hell, großzügig", "status": "confirmed"},
 "palette": {"value": {"name": "Salbei", "colors": {"primary": "#2f6f5e", "background": "#f6f8f5"}, "rationale": "ruhig, guter Kontrast"}, "status": "confirmed"}}}
JSON
python3 -B "$FLOW" status --root "$P1"
python3 -B "$FLOW" brief-save --site "$S" --file "$ACC/brief.json" --root "$P1"
python3 -B "$FLOW" brief-confirm --site "$S" --statement "Ja, das Briefing passt (Abnahmelauf)" --root "$P1"
```
Erwartet: erstes `status`: `setup.state: complete`, `next_step: brief`; danach `saved` (Revision 1) und `confirmed`.

**A.3 Prototypen, Feedback, Freigabe** (Fälle 4, 5, technisch). Die zwei Prototypen stammen aus den Test-Fixtures; ihre inhaltliche Qualität prüft erst die Gesprächs- und Sichtabnahme (C, D).
```bash
python3 -B "$FLOW" design-new --site "$S" --root "$P1"
python3 -B - <<PY
import sys; sys.path.insert(0, "$PLUGIN")
from pathlib import Path
from tests.support import flow_helpers as f
d = Path("$P1/.project/website/$S/design/r001"); (d/"A.html").write_text(f.page_a()); (d/"B.html").write_text(f.page_b())
PY
python3 -B "$FLOW" design-register --site "$S" --revision 1 --root "$P1"
python3 -B "$FLOW" design-feedback --site "$S" --text "B gefällt mir, Navigation heller (Abnahmelauf)" --root "$P1"
```
Erwartet: `registered` mit Vergleichsseite `design/r001/index.html`; nach dem Feedback ist `design.state: revising` und es gibt noch **keine** Freigabe. (`design-approve` prüft die Aussage nur auf Vorhandensein; ob eine bloße Präferenz als Freigabe gewertet wird, entscheidet allein die Gesprächsabnahme C.3, deshalb wird hier keine Revision 1 freigegeben.) Nun Revision 2 anlegen und freigeben:
```bash
python3 -B "$FLOW" design-new --site "$S" --root "$P1"          # Revision 2 (nach Feedback erlaubt)
python3 -B - <<PY
import sys; sys.path.insert(0, "$PLUGIN")
from pathlib import Path
from tests.support import flow_helpers as f
d = Path("$P1/.project/website/$S/design/r002"); (d/"A.html").write_text(f.page_a()); (d/"B.html").write_text(f.page_b(extra="<aside><p>heller</p></aside>"))
PY
python3 -B "$FLOW" design-register --site "$S" --revision 2 --root "$P1"
python3 -B "$FLOW" design-approve --site "$S" --revision 2 --variant B --statement "Ja, Revision 2 Variante B setzen wir um (Abnahmelauf)" --root "$P1"
python3 -B "$FLOW" status --root "$P1"
cp -R "$P1" "$ACC/p-conflict"; cp -R "$P1" "$ACC/p-probe"     # zwei Kopien nach der Freigabe: A.4 (Schreibprobe) und A.6 (Konflikt)
```
Erwartet nach der Freigabe: `design.state: approved`, `next_step: implement`; die Startseite `src/pages/index.astro` ist byteweise unverändert (Hash vor/nach vergleichen: `shasum -a 256 "$P1/sites/$S/src/pages/index.astro"`).

**A.4 Technische Schreibprobe in `p-probe` (Edit-Session, Flow-Abschlussmechanik). Das ist KEINE Designabnahme.**
Zweck: den Weg `implement-start` → echte Edit-Session mit Schreibvorgang → echte Checks → `implement-finish` → `record-checks` technisch zu belegen. Die Beispielseite unten setzt die freigegebene **Variante B nicht um** (andere Struktur, keine Palette, keine Seitenleiste). Ausdrücklich **nicht** zu folgern: „Design umgesetzt“, bestandene Design-Sichtabnahme (Fälle 4/6/8 visuell) oder ein vollständig abgenommener Flow. Der Zustand von `p-probe` (`implementation: done`, `technical: passed`) beweist nur den Mechanismus; `p-probe` wird nicht für `visual: passed` verwendet.
Voraussetzung für `implement-finish`: bestätigtes Briefing, registriertes **und** freigegebenes Design, `implement-start`, eine echte Edit-Sitzung mit eigenem Schreibvorgang; `node_modules` und Lockfile existieren durch A.1 (Kopie).
```bash
export PRB="$ACC/p-probe"
python3 -B "$FLOW" implement-start --site "$S" --root "$PRB"
python3 -B "$EDIT" preflight --root "$PRB"
STATE="$(python3 -B "$EDIT" begin --root "$PRB" --site "$S" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state_folder"])')"; echo "$STATE"
cat > "$ACC/probe-index.astro" <<'ASTRO'
---
import BaseLayout from '../layouts/BaseLayout.astro';
import { SITE_NAME } from '../lib/site';
---

<BaseLayout title={SITE_NAME} description="Technische Schreibprobe einer fiktiven Praxis: kein Entwurf der freigegebenen Variante, nur ein Test des Schreibwegs und der Prüfungen." current="home">
  <div class="container">
    <header class="page-header">
      <h1 class="page-header__title">{SITE_NAME}</h1>
      <p class="page-header__lead">Technische Schreibprobe.</p>
    </header>
  </div>
</BaseLayout>
ASTRO
python3 -B "$EDIT" write --state "$STATE" --content-file "$ACC/probe-index.astro"
python3 -B "$EDIT" check --state "$STATE" > "$ACC/probe-check.json"; echo "check exit $?"
python3 -B "$FLOW" implement-finish --site "$S" --edit-state "$STATE" --root "$PRB"
python3 -B "$FLOW" record-checks --site "$S" --technical-evidence "$ACC/probe-check.json" --visual open --root "$PRB"
python3 -B "$FLOW" status --root "$PRB"
python3 -B "$EDIT" finish --state "$STATE"
```
Reihenfolge ist Pflicht: `implement-finish` **vor** `edit.py finish`. Ohne `--visual-done` behält `finish` den Sitzungsordner; mit `--visual-done` am Ende eines vollständig geprüften Laufs entfernt es ihn, und der Beleg wäre weg.
Erwartet: `check` Exit 0 mit echtem Build und `check` (meldet der echte Lauf SEO- oder Barrierefreiheitsbefunde, den Text anpassen und das dokumentieren); `implemented` mit `edit_session.writes: 1`; `record-checks`: `technical: passed`, `visual: open`; `status`: `implementation: done`, `next_step: checks`. Selbst mit `visual: passed` wäre die Designabnahme damit nicht erbracht. Ergebnis im Protokoll: „technische Schreibprobe bestanden/nicht bestanden“, nie „Flow abgenommen“.

**A.4b Übergang zur tatsächlichen Umsetzung der freigegebenen Variante B in `p-domainless` (Voraussetzung für Design-Sichtabnahme und vollständigen Flow)**
Die Umsetzung ist inhaltliche Arbeit (Übersetzung von `design/r002/B.html` in `src/pages/index.astro`). Im Hostlauf führt die Gesprächsabnahme C.3 sie; im Handlauf gilt dieselbe Mechanik wie in A.4, aber mit dem **echten Seiteninhalt**:
1. `python3 -B "$FLOW" implement-start --site "$S" --root "$P1"` (Projekt 1, nicht `p-probe`).
2. Neue Edit-Session (`edit.py begin`, `STATE` merken); Seite aus `B.html` aufbauen und mit `edit.py write` bzw. `replace` schreiben: Seitenleiste links, Artikel „Rückenkurse und Physiotherapie in Wien“, „Termin“ (Formular nur als Platzhalter), „Über die Praxis“ mit der offenen Angabe, Bild-Platzhalter, Primärfarbe `#2f6f5e` über Styles dieser Seite. Offene Fakten bleiben als „offene Angabe“ sichtbar; nichts erfinden. Geschrieben wird nur `index.astro`.
3. **Erneute, zum Seiteninhalt passende technische Checks** nach dem **letzten** Schreibvorgang: `python3 -B "$EDIT" check --state "$STATE" > "$ACC/check-b.json"`. Der Beleg ist an den Hash der aktuellen Seite gebunden; jede spätere Änderung macht ihn veraltet (`checks.outdated`) und verlangt einen neuen `check` mit neuer Datei.
4. `python3 -B "$FLOW" implement-finish --site "$S" --edit-state "$STATE" --root "$P1"` (vor `edit.py finish`), dann `python3 -B "$FLOW" record-checks --site "$S" --technical-evidence "$ACC/check-b.json" --visual open --root "$P1"`.
Erwartet: `implemented`, `technical: passed`, `visual: open`, `next_step: checks`. **Noch nicht abgenommen**: erst A.5 kann `visual` bestehen lassen.

**A.5 Fall 8 visuell: Sichtprüfung der umgesetzten Variante B** (`p-domainless` nach A.4b; nicht `p-probe`)
```bash
python3 -B "$CONTROL" start "$S" --root "$P1" --timeout 120
python3 -B "$CONTROL" inspect "$S" --root "$P1" --expect "Rückenkurse und Physiotherapie in Wien"
```
Erwartet: `running-new`, `page-confirmed` (domainlos: `identity_basis: site name only`). `page-confirmed` ist HTTP-Evidenz, keine Sichtprüfung. Dann die Seite im Browser öffnen (Adresse aus der Controller-Ausgabe) und neben `design/r002/B.html` legen. Prüfpunkte, je mit Ja/Nein zu protokollieren: Seitenleiste links wie in B; Reihenfolge der Artikel wie in B; Primärfarbe erkennbar; Text lesbar (Kontrast); offene Angaben sichtbar als „offene Angabe“; keine erfundenen Tatsachen; Layout bricht auf schmaler Breite nicht. Nur wenn alle Punkte „Ja“ sind:
```bash
python3 -B "$FLOW" record-checks --site "$S" --technical-evidence "$ACC/check-b.json" --visual passed --visual-note "B.html und Startseite nebeneinander verglichen: <Ergebnis je Prüfpunkt>" --root "$P1"
python3 -B "$FLOW" status --root "$P1"
python3 -B "$CONTROL" stop "$S" --root "$P1"
```
Erwartet: `technical: passed`, `visual: passed`, `next_step: done`. Gilt ein Prüfpunkt nicht, bleibt `visual` offen oder `failed`, der Flow ist nicht abgenommen; es folgt eine Rückfrage und gegebenenfalls eine neue Revision oder Umsetzung. Wurde die Seite nach `check-b.json` noch geändert, zuerst `edit.py check` erneut und die neue Datei verwenden (sonst „does not belong to the current content“). Erst nach `visual passed` darf `edit.py finish --state "$STATE" --visual-done` laufen (entfernt den Sitzungsordner).

**A.6 Fall 7: Konflikt und Wiederaufnahme** (in `p-conflict`, Kopie nach der Freigabe; `P1` bleibt unberührt; das Verzeichnis `$ACC/p-conflict` hat denselben Site-Namen)
```bash
export PC="$ACC/p-conflict"
python3 -B "$FLOW" implement-start --site "$S" --root "$PC"
echo '<!-- eigene Änderung der Person -->' >> "$PC/sites/$S/src/pages/index.astro"
python3 -B "$FLOW" status --root "$PC"                                 # next_step: resolve-implementation-conflict
STATE2="$(python3 -B "$EDIT" begin --root "$PC" --site "$S" | python3 -c 'import sys,json; print(json.load(sys.stdin)["state_folder"])')"
python3 -B "$EDIT" check --state "$STATE2" > /dev/null
python3 -B "$FLOW" implement-finish --site "$S" --edit-state "$STATE2" --root "$PC"      # muss abgelehnt werden
shasum -a 256 "$PC/sites/$S/src/pages/index.astro"                      # Nutzeränderung unverändert
python3 -B "$FLOW" implement-start --site "$S" --accept-current-page --root "$PC"       # nur nach Zustimmung der Person
```
Erwartet: `status` zeigt `resolve-implementation-conflict`; `implement-finish` mit der reinen Check-Sitzung wird mit der Begründung „no write of its own“ und „not started from the recorded start state“ abgelehnt (Exit 1), die Nutzeränderung bleibt byteweise erhalten, die Designfreigabe bleibt `approved`. Mit `--accept-current-page` wird der aktuelle Seitenstand neuer Ausgangspunkt; danach eine neue `edit`-Sitzung mit `write` und `implement-finish` wie in A.4 → `implemented`.
Wiederaufnahme nach Abbruch: in `PC` nach dem `write` den Befehl `implement-finish` weglassen (Sitzung abbrechen); später `implement-start` meldet `resumed-changed`; `implement-finish --edit-state "$STATE3"` mit dem **erhaltenen** Sitzungsordner schließt ab (`implemented`), ein zweiter Aufruf `unchanged`.

**A.7 Domain später nachtragen** (Projekt 1 nach A.4b)
```bash
python3 -B "$SETUP" set-domain "$S" demo-a.com --plan --root "$P1"
python3 -B "$SETUP" set-domain "$S" demo-a.com --root "$P1"
python3 -B "$SETUP" verify "$S" --root "$P1" --json
```
Erwartet: `planned`, `updated`, `verified` (install, build, check Exit 0). Manifest: `domain: demo-a.com`; Name, Pfad, Port und Besitzschlüssel unverändert; `astro.config.mjs` und `site.ts` tragen `https://demo-a.com`; die umgesetzte `index.astro` bleibt unberührt. In `dist/`: Canonical, `og:url`, `og:image` und `sitemap.xml` mit `https://demo-a.com/`-Adressen.

**A.8 Fall 2 mit Domain von Anfang an** (Projekt 2)
```bash
export P2="$ACC/p-domain"; mkdir -p "$P2"
python3 -B "$SETUP" create "$S" --type astro-static --domain demo-a.com --root "$P2" --build --json
python3 -B "$FLOW" status --root "$P2"
grep -rl 'rel="canonical"' "$P2/sites/$S/dist" | head -3
python3 -c "import sys,xml.dom.minidom as m; print(len(m.parse(sys.argv[1]).getElementsByTagName('loc')))" "$P2/sites/$S/dist/sitemap.xml"
```
Erwartet: `created`, alle drei Exit 0, Canonical vorhanden, Sitemap mit mindestens einem `loc` auf `https://demo-a.com/`; `status`: `setup complete`, `next_step: brief`. Kontrolle des Widerspruchs: `site.ts` von Hand auf eine andere Adresse ändern und `python3 -B "$FLOW" status` bzw. `control.py start` aufrufen → Stopp mit konkretem Widerspruch, nichts repariert.

**Aufräumen:** `$ACC` ist ein Wegwerf-Ordner; der Lauf endet mit `control.py stop` (kein eigener Dev-Server mehr, nur über den Controller beendet). Kein Eingriff in fremde Prozesse.

### B. Host-Abnahme je Host getrennt (Fälle 1, 2, 3, 5, 6, 7)
**Was der vorhandene Weg tatsächlich tut** (aus dem Quelltext gelesen, nichts ausgeführt): `scripts/plugin.py install-local|update-local` ruft den Helfer `scripts/local_plugins.py` des gewählten Marketplace-Repos auf. Dieser bereitet Snapshots für **alle** Plugins des dortigen Katalogs vor und schreibt sie nach `dist/local-development/<host>-marketplace/` **im Marketplace-Repo**, auch bei `--dry-run` (dort werden nur die Host-Befehle ausgelassen). Danach führt er aus: `<host> plugin marketplace add <Ordner>` und je Plugin `claude plugin install|update <plugin>@<marketplace> --scope user` bzw. `codex plugin add <plugin>@<marketplace> --json`. Das ist also **nicht auf das Website-Plugin begrenzt**, installiert in den Benutzerbereich (bei Claude ausdrücklich `--scope user`, bei Codex in das Standardprofil) und ändert damit die echten Hostprofile. Es setzt außerdem eine lokale Zuordnung in der ignorierten persönlichen Konfiguration des Marketplace-Repos voraus (nicht gelesen, nicht verändert). Dieser Weg ist für die Abnahme **nicht geeignet** und wird nicht ausgeführt.

**Isolierte Profile (tests/README.md: „isolated host profiles“): tatsächlich verfügbare Möglichkeiten, geprüft nur über `--help`/Binärtext**
| Host | Möglichkeit | Beleg |
|---|---|---|
| Claude Code 2.1.319 | `CLAUDE_CONFIG_DIR=<leerer Ordner>` verlegt das Benutzerprofil (Binärtext nennt `$CLAUDE_CONFIG_DIR` als Konfigurationsordner); `claude --plugin-dir <Ordner>` lädt ein Plugin nur für diese Sitzung, ohne Installation und ohne Marketplace | `claude --help` (nur gelesen) |
| Codex 0.165.0 | `CODEX_HOME=<leerer Ordner>` verlegt das Profil (Hilfetext zu `--profile` nennt `$CODEX_HOME`); es gibt keine Option „Plugin aus Ordner laden“; Weg: lokales Ein-Plugin-Marketplace und `codex plugin marketplace add <Ordner>` plus `codex plugin add website@<name>` im isolierten Profil | `codex plugin --help` (nur gelesen) |
Grenzen, nicht verifiziert: ob das jeweilige Werkzeug die Variable in allen Unterbefehlen beachtet (Probe nötig, siehe unten); ein isoliertes Profil ist **nicht angemeldet** – die Anmeldung (Login oder Schlüssel) muss die Person selbst im isolierten Profil vornehmen, ich gebe keine Zugangsdaten ein; ohne isoliertes Profil bliebe bei `--plugin-dir` das echte Profil mit seinen übrigen Plugins aktiv.

**Lücke im vorhandenen Werkzeug:** `install-local` kennt weder eine Plugin-Auswahl (`--plugin website`) noch einen Scope (`--scope`) noch ein Profilverzeichnis; es installiert den ganzen Katalog in den Benutzerbereich. Ein begrenzter Weg ist damit nur über die Umgehung unten möglich, nicht über das Werkzeug.

**Vorbereiteter, auf das Website-Plugin begrenzter Weg (nicht ausgeführt)**
1. Paket wie in A.0 erzeugen (`$PKG`).
2. Claude, isoliert und ohne Installation:
```bash
export HOSTPROFILE="$(mktemp -d)"
CLAUDE_CONFIG_DIR="$HOSTPROFILE/claude" claude --plugin-dir "$PKG"        # neue Sitzung; Anmeldung im isolierten Profil durch die Person
```
Erwartet in der Sitzung: die acht Skills des Plugins `website` (`/website:plugin-website` usw.). Ob keine Skills oder Einstellungen des echten Profils sichtbar sind, ist Teil des Isolationsnachweises unten und hier **nicht** vorausgesetzt.
3. Codex, isoliert (Ein-Plugin-Marketplace; Katalogformat entspricht dem, was das Marketplace-Werkzeug für Codex erzeugt, hier ungeprüft):
```bash
export CODEX_HOME="$HOSTPROFILE/codex"; mkdir -p "$HOSTPROFILE/market/plugins/website" "$CODEX_HOME"
python3 -B - <<PY
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location("t", "$PLUGIN/scripts/plugin.py"); t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
_v, portable, _c = t.payload()
for name, data in t.codex_payload(portable).items():
    p = Path("$HOSTPROFILE/market/plugins/website") / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
cat = {"name": "website-dev", "interface": {"displayName": "Website (Development)"}, "plugins": [{"name": "website", "source": {"source": "local", "path": "./plugins/website"}, "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}]}
Path("$HOSTPROFILE/market/.agents/plugins").mkdir(parents=True, exist_ok=True); Path("$HOSTPROFILE/market/.agents/plugins/marketplace.json").write_text(json.dumps(cat, indent=2))
PY
CODEX_HOME="$CODEX_HOME" codex plugin marketplace add "$HOSTPROFILE/market"
CODEX_HOME="$CODEX_HOME" codex plugin add website@website-dev --json
CODEX_HOME="$CODEX_HOME" codex                                                # neue Sitzung, Anmeldung im isolierten Profil
```
**Isolation: Stand und offener Bedarf**
- *Stand:* Separates Testprofil vorgesehen; tatsächliche Isolation noch nicht verifiziert. Die Umgebungsvariablen `CLAUDE_CONFIG_DIR`, `CODEX_HOME` und `HOME` sind der vorgesehene Mechanismus, aber kein Beleg, dass der Host alle Lese- und Schreibpfade (Konfiguration, Caches, gemeinsame Anmeldeablage) daran bindet.
- *Vorprüfung, kein Beweis:* `CODEX_HOME="$HOSTPROFILE/codex" codex plugin list` und `CLAUDE_CONFIG_DIR="$HOSTPROFILE/claude" claude plugin list`. Eine leere Liste zeigt nur, dass dort nichts Installiertes gefunden wurde; sie beweist weder die Beachtung der Variablen noch etwas über Schreibpfade.
- *Teilnachweis:* Dateien im eigenen Wegwerfprofil (`find "$HOSTPROFILE" -type f`, eigene Namen dürfen gelesen werden) zeigen nur, dass der Host dort geschrieben hat. Sie schließen nicht aus, dass er zusätzlich anderswo schreibt. Dateizählungen (auch über `find -newer`) belegen keine vollständige Isolation und werden hier nicht als Beleg verwendet.
- *Verboten in dieser Abnahme:* die echten privaten Profilverzeichnisse (`~/.claude`, `~/.codex`, Schlüsselbund, Zugangsdaten) werden weder durchsucht noch gelesen noch gezählt. Anmeldung im Testprofil macht die Person selbst.
- *Offener Bedarf:* Ist eine vollständig isolierte Hostabnahme erforderlich, muss dafür eine separate Testumgebung bereitgestellt werden (zum Beispiel ein eigenes Benutzerkonto oder eine eigene Maschine bzw. VM ohne private Profile und Zugangsdaten). Sie liegt außerhalb dieses Plugins und dieser Anleitung; hier wird dafür keine Trace-Infrastruktur und keine Marketplace-Erweiterung entwickelt.
- *Aussage im Protokoll:* bis dahin „Isolation nicht verifiziert“. Es gilt `tests/README.md`: Hostabnahme mit isolierten Profilen. Solange die geeignete Testumgebung fehlt, bleibt die Hostabnahme NOT RUN. Eine Ausnahme wäre eine separate, ausdrückliche Nutzerentscheidung; sie ist derzeit nicht erteilt.
4. Fälle prüfen: Schritte B.1 bis B.4 aus der bisherigen Planung (Skills sichtbar, Auftrag in leerem fiktiven Ordner ohne Git, Aktivierung separat für Wort und Satz, erneuter Aufruf). Nach der Abnahme: `$HOSTPROFILE` löschen.
5. **Konkreter Vorschlag zur Werkzeuglücke (erfordert Änderung im Marketplace-Repo, nicht freigegeben):** `install-local` um `--plugin NAME` (nur dieses Plugin vorbereiten und installieren), `--scope` (statt fest `user`) und eine Prüfung ergänzen, die bei `--isolated` nur läuft, wenn `CLAUDE_CONFIG_DIR` bzw. `CODEX_HOME` gesetzt und leer sind. Bis dahin gilt die Umgehung oben.

### C. Gesprächsabnahme (Fälle 2 bis 7; Host nötig, kein Download)
1. Briefing: Erwartet höchstens vier gebündelte Fragen je Runde mit Vorschlag, bestätigt/vorgeschlagen/offen getrennt, 2 bis 3 Paletten mit Begründung, Websitesprache getrennt von der Bedienersprache; ohne ausdrückliches Ja keine Varianten.
2. Design: Erwartet ≥ 2 deutlich verschiedene Layouts, offene Fakten sichtbar als „offene Angabe“, nichts Erfundenes (Preise, Qualifikationen, Jahre, Ergebnisse); die gewählte Palette erkennbar genutzt.
3. Antwort „Variante B gefällt mir besser“. Erwartet: als Feedback behandelt, neue Revision, keine Umsetzung. Danach „Ja, Revision 2, Variante B“. Erwartet: Freigabe, sofort Umsetzung ohne Wiederholungsfrage, in der Reihenfolge von A.4 (Abschluss vor `edit.py finish`).
4. Umsetzung unterbrechen (Sitzung beenden nach dem Schreiben), neue Sitzung. Erwartet: Fortsetzung mit dem erhaltenen Edit-Zustand oder gezielte Nachfrage, nichts überschrieben.
5. Zwischen `implement-start` und Schreiben die Seite von Hand ändern. Erwartet: Konflikt gemeldet, Nachfrage, keine erneute Designfreigabe, Nutzeränderung bleibt erhalten.

### D. Sichtabnahme (Fälle 4, 6, 8)
1. Vergleichsseite `design/rNNN/index.html` im Browser öffnen (bei `file://`-Sperre lokaler Server auf 127.0.0.1). Erwartet: beide Varianten nebeneinander lesbar, Kontrast der gewählten Palette ausreichend.
2. Umgesetzte Startseite von `p-domainless` (nach A.4b, **nicht** die Schreibprobe aus A.4) über `preview` ansehen und mit der freigegebenen Variante vergleichen (Prüfpunkte in A.5). Erwartet: entspricht der Variante in Struktur und Palette; erst danach `record-checks --visual passed` mit Notiz.

## Freigaben, die vor dem Ausführen nötig sind (nichts davon wurde ausgeführt)
| Umfang | Was konkret | Nötig für |
|---|---|---|
| Netzwerk und npm | `npm install` lädt Astro und Abhängigkeiten aus der npm-Registry: in `p-domainless` (A.1), `p-domain` (A.8) und beim `verify` nach `set-domain` (A.7, Lockfile vorhanden); `p-conflict` ist eine Kopie samt `node_modules` ohne neuen Download | A |
| Externe Tests | `python3 -B scripts/run_external_tests.py --approved` (zusätzlich zu A, aber erst nach Anpassung von `test_real_tools.py`, s. o.) | optional A |
| Dev-Server | `control.py start` bindet 127.0.0.1 auf einem freien Port, nur über den Controller beendet | A.5, D |
| Isoliertes Hostprofil | Anlegen leerer Profilordner (`$HOSTPROFILE`), Start von `claude`/`codex` mit `CLAUDE_CONFIG_DIR`/`CODEX_HOME`, `codex plugin marketplace add` und `codex plugin add` **nur im isolierten Profil**; Anmeldung dort durch die Person | B, C |
| Browser-Sicht | nur Öffnen lokaler Dateien/127.0.0.1-Adressen im eingebauten Browser | D |
| Nicht freigegeben und nicht vorgeschlagen | `install-local`/`update-local` (echte Profile, alle Plugins), jede Änderung am Marketplace-Repo oder an `plugin-manager` | – |

Hinweis: Das Marketplace-Repo hat einen bekannten roten Test (Paketierer-Kopien in `plugin-manager`, nicht freigegeben). Das blockiert die Matrix nicht; der Paketweg oben nutzt nur das eigene `scripts/plugin.py` des Website-Plugins.

## Zusammenfassung
Deterministisch belegt: Zustandsvertrag, Manifest Version 2 mit und ohne Domain, Konsistenz, Briefing-, Design-, Freigabe-, Umsetzungs- und Prüfzustände, Wiederaufnahme, Konflikte, Beschädigungsfälle, Paketlauf des Setups. NOT RUN: jeder Host-, Gesprächs-, echte Astro- und Sichtfall der Spalte „Fehlt“ sowie die externen Tests. Diese Matrix behauptet keine Abnahme.
