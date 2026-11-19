# Migration: Entscheidungen und offene Punkte

Migrationsnachweis, keine Produktdefinition. Maßgeblich bleibt [SCOPE.md](../../SCOPE.md). Stand: 2026-11-19, fortgeschrieben in Etappe 1 (Abschnitt 12) und Etappe 2 (Abschnitt 13). Die historischen Abschnitte 2–11 geben den Stand von Etappe 0 wieder; wo Etappe 1 etwas beantwortet, steht es in Abschnitt 12.

## 1. Bestätigte Nutzerentscheidungen (nicht erneut vorgelegt)

| ID | Entscheidung |
|---|---|
| D-01 | Eigenständiges Plugin `website`, Anzeigename „Website“, fünf Skills `setup`, `preview`, `optimize`, `edit`, `publish`. Die Skeleton-Identität `website-manager` ist kein fachliches Ziel. |
| D-02 | Zielhosts sind Claude und Codex; Hostverhalten wird getrennt belegt. |
| D-03 | Übernommen wird der aktuelle pluginbezogene Arbeitsstand der Quelle einschließlich uncommitteter Änderungen und neuer Dateien. |
| D-04 | Bestehende Funktionen erhalten und an die globale Struktur anpassen; keine Erweiterung um geplante Funktionen. |
| D-05 | Die bestehenden Skill-Verträge sind die fachliche Grundlage; ausdrücklich Geplantes bleibt draußen; Widersprüche und Unklarheiten werden offengelegt, nicht aus Code entschieden. |
| D-06 | `edit` bleibt auf die Startseite begrenzt; `publish` bleibt Platzhalter ohne Veröffentlichungsfunktion; keine Blogbearbeitung, kein GEO, kein `setup update`, kein Deployment. |
| D-07 | `www.draftmode` bleibt unverändert; nach Abnahme ist `ai.plugin.website` alleinige Entwicklungsquelle; keine Quellbereinigung beauftragt. Verteilung nur nach dem aktuellen Manager-Vertrag. |
| D-08 | Keine Kompatibilitätsaliases; bestehende Website-Projektdatenformate sind eine separate Schnittstelle ohne automatische Umbenennung oder Migration. |
| D-09 | Ein lokaler Marketplace-Eintrag in `ai.plugins` darf später vorbereitet werden; keine Installation, Commits, Pushes oder Veröffentlichung. |
| D-10 | Deterministische Tests in isolierten Verzeichnissen sind für die Implementierungsetappen autorisiert; Modelltests, native Hosttests, GUI-Abnahme, Netzwerk für Tests und Werkzeug-/Abhängigkeitsinstallationen sind es nicht. |
| D-11 | Dokumentation Deutsch und Englisch, Deutsch als Standardsprache. |
| D-12 | Nach den Reviews von Etappe 0 bestätigt der Nutzer den konkretisierten Scope einschließlich der letzten Präzisierungen zu Manifestvalidierung (R5), `publish`-Platzhalter (R23) und Runtime-Aufrufprüfungen (R24). Die bis dahin als `draft` geführten Anforderungen sind `confirmed` (Auftrag Etappe 1, 2026-11-19). |
| D-13 | `setup create` legt bei einem neuen Websiteprojekt ein fehlendes Manifest selbst an: nach dem aktuellen Schema, mit den bestätigten Angaben der neuen Site, ohne bestehende Dateien zu überschreiben. Die konkrete Feldbelegung ist vor Etappe 2 zu dokumentieren und zu prüfen; unbekannte fachliche Angaben werden nicht erfunden. Dokumentiert: `setup-init.md`. Schließt die offene Stelle aus 4.6 (Regel), nicht die Feldbelegung. |
| D-14 | Isolierte Preview-Tests dürfen eigene lokale Prozesse starten, `127.0.0.1`-Ports verwenden und ausschließlich ihre eigenen, eindeutig identifizierten Testprozesse bzw. Prozessgruppen beenden. Externe Netzwerkzugriffe für Tests bleiben ausgeschlossen. Die Freigabe erzwingt keine Preview-Tests bereits in Etappe 1. Beantwortet Q10. |
| D-15 | Deterministische Tests in isolierten Testverzeichnissen sind autorisiert (bestätigt D-10). Modelltests, native Claude-/Codex-Hosttests und GUI-Abnahmen bleiben getrennt; keine Werkzeug- oder Abhängigkeitsinstallation, keine Commits, Pushes oder Veröffentlichung. |
| D-16 | `setup create` belegt das Manifest bei einem neuen Projekt: `$schema` `./website.schema.json`, `version` 1, `name` = Domain, `path` = ausdrücklicher Pfad, sonst `sites/<domain>`, `type` `astro-static`, `title` = ausdrücklicher Titel, sonst Domain, `aliases` = angegebene Aliase, sonst `[]`, `port` = ausdrücklicher Port, sonst automatisch ab 4321 (leeres Projekt 4321; sonst ein folgender gültiger Port auf Grundlage der effektiven Portbelegung; vorhandene Einträge nicht umschreiben; Kollisionen ablehnen; kein stiller Überlauf; fehlt ein gültiger Wert, konkret stoppen), `environment` nur bei ausdrücklicher Angabe. Titel und leere Aliasliste werden wie im Bestand geschrieben; die vorgeschlagene Änderung, diese Felder wegzulassen, ist nicht beauftragt. Schließt O1–O3 aus `setup-init.md` (Auftrag Etappe 2, 2026-11-19). |
| D-17 | Begrenzte Umbenennung (Ausnahme zur Vorgabe „Projektdatenpfade unverändert“): Schema im Plugin `skills/_shared/resources/website.schema.json`, Projektkopie `.project/specs/website.schema.json`, Manifestverweis `"$schema": "./website.schema.json"`. Unverändert bleiben `.project/specs/zyris-website.json`, `…/zyris-website.managed.json`, Berichtsformate und Marker, interne Zustandsnamen (Q5). |
| D-18 | Kein Fallback auf `zyris-website.schema.json`, kein Kompatibilitätsalias, keine automatische Migration. Ein Projekt im alten Format wird mit konkreter Diagnose vor Schreibzugriffen abgelehnt; bestehende Nutzerdaten und alte Schemadateien werden nie gelöscht, umbenannt oder überschrieben. Eine fehlende neue Schemakopie ist nie Anlass, ein erkanntes altes Projekt still zu konvertieren. |

## 2. Planungsentscheidungen des Implementierers

| ID | Entscheidung | Grund |
|---|---|---|
| P-01 | (Stand Etappe 0, überholt durch D-12) `SCOPE.md` blieb als Ganzes `draft`. Nur Anforderungen, die D-01–D-11 oder eine bestehende globale Regel ohne Zusatz wiedergeben, sind `confirmed` (R1, R2, R3, R4, R14, R16, R18, R20); jede Detailformulierung ist `draft` und in eigenen R-Einträgen getrennt (R21–R25). | Neue Formulierungen bedürfen der Scope-Abnahme; ein Review stuft nie selbst hoch. |
| P-02 | In `SCOPE.md` stehen vorhandene Belege als `Source:`/`Test:` (nur R19, R20); für alle anderen Einträge steht „Evidenzstatus: noch nicht vorhanden“. Es gibt keine Platzhalterdateien. | `verify --review` darf Lücken melden; sie werden nicht verschwiegen. |
| P-03 | Inventar nur plugin-relevanter Quelldateien (130); `sites/`, `.project/`, Caches nicht untersucht. | Keine realen Website-Inhalte oder privaten Projektdaten. |
| P-04 | Packaging-Werkzeuge (`tools/*`, `Makefile`) sind nur Evidenz des alten ZIP-Wegs, nicht migriert. | D-07. |
| P-05 | Die Ausgangsinventare (`source-inventory.json`, `target-baseline.json`, `reference-baseline.json`) bleiben unverändert; spätere Basen entstehen als zusätzliche Dateien. | Historische Nachweise. |

## 3. Klassifikation aller offenen Punkte

Kategorien: **A** bereits durch Nutzerentscheidung oder explizite Vertragsstatus beantwortet · **B** technische Implementierungsentscheidung · **C** echte fachliche Unklarheit · **D** fehlender Ausführungs-/Hostnachweis.

| Punkt | Kat. | Kurzfassung | Abschnitt |
|---|---|---|---|
| V1 preview-Verträge | A | Spätere, als implementiert markierte Abschnitte gelten; Host-Tool-Modell geplant/ausgeschlossen | 4.1 |
| V2 optimize-Abhängigkeiten | A | Isolierte Kopie mit `npm ci` ist ausdrücklich geplant → ausgeschlossen | 4.2 |
| V3 gemeinsame Module | B | Architekturentscheidung mit Prüfschritten | 4.3 |
| V4 publish-Verweise | A | Platzhalter (D-06); keine Entscheidung über geplante Veröffentlichung | 4.4 |
| V5 setup↔edit | A | Bekannte Einschränkung dokumentieren; keine Rebaselining-Funktion | 4.5 |
| Q1/Q2 Pfade und Freigabemuster | B (+D) | gemeinsam, Host-Nachweis ausstehend | 5.1 |
| Q3 Prozesssteuerung / Sichtprüfung | A + D | getrennt; Hostfähigkeiten unbelegt, nicht abgeleitet | 5.2 |
| Q4 Aufrufnamen | B (+D) | neutrale Laufzeitmeldungen | 5.3 |
| Q5 interne Zustandsnamen | B | Vorgabe: unverändert | 5.3 |
| Q6 Testklassifikation | B | nach tatsächlichem Verhalten | 5.4 |
| Q7 Vertragsübernahme | A | nur normatives, nicht Geplantes/Historisches (D-04/D-05) | 5.3 |
| Q8 Mindestversionen | B | Etappe 1, statische Prüfung | 5.3 |
| Q9 | – | in V5 aufgegangen | 4.5 |
| Q10 Loopback-Prozesstests | A | beantwortet durch D-14 | 6, 12 |
| Scope-Abnahme | A | beantwortet durch D-12 | 12 |

## 4. Verträge: Prüfung und Einordnung

### 4.1 V1 – preview (Kategorie A)
Gelesen: `preview.md` vollständig. Befund: §3–§10 beschreiben ein früheres Zielmodell mit Host-Tools (`preview_start|stop|list`, `host_server_id`, Capability-Probe, Terminal „Laufzeitsteuerung nicht verfügbar“); §5 trägt die Statusangabe „PLANNED – not implemented“, §3/§6 „DRAFT FORMAT“. §11 („Implementation status“), §12 und §13 tragen „IMPLEMENTED“ und beschreiben den Skript-Controller, §11.2 begründet, dass der Terminalpfad der Standard ist, §13 verbietet Host-Start-Tools. Die expliziten Statusangaben und D-04/D-05 ordnen das Host-Tool-Modell als geplant/überholt ein; es wird nicht als gleichwertige Option angeboten. Kein verbleibender normativer Widerspruch ist als Nutzerentscheidung vorzulegen.
Einschränkung: Dass §11–§13 gelten, folgt aus den Statusangaben der Verträge, nicht aus einer Prüfung des Codes; „implementiert/bestanden“ ist unverifiziert.
Zu berichtigende Texte: §4 (Terminal-Zeile, Host-Tools als Oberfläche), §7 und §9 („started via the host tool“, `missing-tool`), §10 (alle Zeilen „missing“ gegenüber §11.3 „passed“, widersprüchliche Evidenzstände), §2.3 D3/D4; außerdem §3 „needs_install → the skill runs npm install“: Das ist Zielmodell; §11.1 (`needs-install` ohne Installation), `edit.md` §4.3/§6 („preview must not install“) und die Meldungsregel des Skilltexts (die Person führt `npm install` aus) bilden den Bestand. Der Skilltext wird so formuliert, dass der Skill nicht selbst installiert (R10).

### 4.2 V2 – optimize (Kategorie A)
Gelesen: `optimize.md` vollständig. Befund: §5 (Zeile „dependency preparation“) nennt als Standard eine isolierte Kopie mit `npm ci` und erlaubt bei `apply` ein `npm ci` im Projekt, ohne Statusmarker. Dagegen sagen §2 (Audit: kein Install; apply nur freigegebene Änderungen), §3.2 D2 (isolierte Kopie „PLANNED – not implemented“, Lauf nur in place), §8/§10 (`incomplete` statt Installation), `interfaces.md` §3a (Preparation step „PLANNED“) und der Skilltext („this skill does not install“) einheitlich das Gegenteil, und Geplantes ist durch D-04/D-05 ausgeschlossen. Die §5-Zeile ist damit überholter Text, kein vorzulegender Widerspruch. R12/R13 enthalten „installiert nie“.
Zusätzliche Wirkung der vollständigen Lektüre: R12 um Befundklassen, redaktionelle Empfehlungen, manuelle Prüfpunkte ergänzt.

### 4.3 V3 – gemeinsame Module (Kategorie B)
Technische Architekturentscheidung innerhalb der freigegebenen Struktur (`skills/_shared/` erlaubt). Byte-Gleichheit (SHA-256-Präfix; volle Werte im Inventar) ist ein Hinweis, kein Beleg:

| Modul | Gleichheit | Zusätzlich zu prüfen vor einer Zusammenlegung |
|---|---|---|
| `schema.py` | setup = preview = optimize (`b4c2f9fa5438`) | keine lokalen Importe (Importgraph); Fehlerverhalten (Rückgabe der Fehlerliste) nicht im Detail geprüft |
| `errors.py` | preview = optimize (`7695edfb47fa`); setup abweichend (`b932dbcc4ed4`, `Ask` ohne Optionen) | Fehlerklassen `Stop`/`Ask` müssen im ganzen Prozess dieselben Klassen sein (`except`-Zweige); in setup lesen die gefundenen Aufrufer (`static_setup.py:489,764`, `validate.py`) keine Optionen – Gleichheit der Behandlung dort noch nicht belegt |
| `manifest.py` | preview = optimize (`0e084bd987f9`); setup abweichend (`412e98d0172f`: `files()`, Schema als Dict erlaubt, zusätzliche Typprüfung mit eigener Fehlermeldung) | Ressourcenpfad `PLUGIN_SCHEMA = parents[2]/templates/setup/_manifest/root/…` ändert sich beim Verschieben; flacher `import schema`; setup bleibt getrennt (unterschiedliche Signatur und Fehlertext) |
| `sites.py` | preview = optimize (`03b937e7f2c1`) | flache Importe von `manifest`, `errors`; Verhalten bei Namenskollision mit `setup`-Modulen |
| `which_site.py` | nur optimize | fügt seinen Ordner selbst in `sys.path` ein; wird von `edit.py` per Prozess mit `python -I` gestartet (`edit.py:173`) und muss das auch nach dem Verschieben können |

Prüfschritte in Etappe 1 je Modul: (1) Importkontext (flache Namen, `sys.path`-Einfügung, kollisionsfreier Importweg, Isolation in Tests), (2) relative Ressourcenpfade, (3) Fehlerklassen und -meldungen samt Aufrufern. Erst dann wird zusammengelegt; sonst bleiben byte-gleiche Kopien pro Skill mit Gleichheitstest. Gleiche Dateinamen allein begründen keine Zusammenlegung. Keine Nutzerentscheidung nötig.

### 4.4 V4 – publish (Kategorie A)
Gelesen: `publish.md` vollständig. §1 und der Kopf verlangen selbst, dass der Skill sagt, Veröffentlichen sei nicht verfügbar, und keinen dort genannten Modus anbietet; §4–§10 sind Ziel, nichts davon ist umgesetzt (§2.1 „Nothing“). Der migrierte Text bleibt ein Platzhalter (R16, R23). Verweise auf `contracts/publish.md` und die Workflow-Vorlagen-README entfallen, weil beide nicht mitgeliefert werden und Geplantes ausgeschlossen ist. Keine Entscheidung über geplante Veröffentlichung.

### 4.5 V5 – setup↔edit (Kategorie A)
Gelesen: `setup.md` §4–§5, `edit.md` §4.6, §12, `interfaces.md` §7. Beide zitierten Aussagen weisen die Regelung `setup` zu (`setup.md` §5: gehört in den setup-Vertrag, nicht in `edit`; `edit.md` §4.6/§12: Sache des setup-Vertrags). Es gibt keine gegenseitige Verweisung. Was fehlt, ist eine zukünftige Regel zum Neusetzen der Hashes (Rebaselining) bzw. `update`/`--adopt-edits`; beides ist ausdrücklich nicht umgesetzt und durch D-06 ausgeschlossen. Bekannte Einschränkung: siehe SCOPE „Bekannte Einschränkung: edit und setup“. Keine neue Funktion in der Migration.

### 4.6 Offene Stelle im setup-Vertrag: Initialisierung des Manifests (Kategorie C, kein Nutzerentscheid vor Etappe 2 nötig, aber vor deren Abnahme zu klären)
`setup.md` §3 sagt für `create`: „registers the component“, „writes … the manifest (+ schema when new)“, Schreibreihenfolge „manifest last“, bestehende Einträge werden nie geändert. Nicht eindeutig geregelt ist, ob und mit welchem Inhalt `create` ein *fehlendes* Manifest neu anlegt. Der Code baut es aus einer Vorlage (`templates/setup/_manifest/static/…`, `static_setup.py:380–382`); das ist Beleg, keine Festlegung. R5 führt die Stelle als offen; es wird keine Regel erfunden.

## 5. Technische Punkte und Hostplanung

### 5.1 Q1/Q2 – Aufrufpfade und Freigabemuster (B, Hostnachweis D)
Gemeinsam zu behandeln, weil die `allowed-tools`-Muster der Quelle exakt die Aufrufpfade `${CLAUDE_PLUGIN_ROOT}/scripts/<skill>/<script>.py` wiederholen. Mit der Zielstruktur (`skills/<skill>/scripts/…`, `skills/_shared/…`) ändern sich diese Pfade; die alten Muster werden **nicht** unverändert übernommen.
- Etappe 1 legt **eine** Aufrufkonvention fest. Randbedingungen aus dem Bestand (R24): Skriptpfad als ein Argument in Anführungszeichen, `test -f`-Vorprüfung, kein Kopieren von Skripten ins Websiteprojekt.
- Für Claude werden schmale Freigabemuster je Skill aus den **neuen** Aufrufmustern abgeleitet, und ein Vertragstest prüft, dass Muster und Aufrufmuster textlich zusammenpassen (wie `test_skill_texts.py` der Quelle). Die Quelle nennt Ersetzung von `${CLAUDE_PLUGIN_ROOT}` in `allowed-tools` und die Wirkung der Freigabe selbst als im GUI **unbewiesen** (Fall B10); das gilt weiter als *unverified*.
- Für Codex wird keine Vorabfreigabe behauptet; das Verhalten von Frontmatter-Feldern und Pfadvariablen dort ist unbelegt.
- Technische Recherche (offen): aktuelle maßgebliche Dokumentation beider Hosts zu Pfadvariablen im Skilltext, Skill-Frontmatter-Feldern und installiertem Plugin-Layout (wird `skills/_shared/` mitinstalliert?). Bis dahin als *unverified* gekennzeichnet, nicht als belegt.

### 5.2 Q3 – Prozesssteuerung und Sichtprüfung getrennt (A + D)
- **Prozesssteuerung** (`control.py start|status|stop|inspect`) ist hostneutral Python und bleibt der einzige Weg, Dev-Server zu starten, wiederzuverwenden und zu beenden (R10, R11).
- **Sichtprüfung**: verfügbare, autorisierte Browserwerkzeuge des jeweiligen Hosts öffnen nur die vom Controller gelieferte oder durch `inspect` bestätigte Adresse; kein Browserwerkzeug startet zusätzliche Dev-Server oder wechselt den Port. Die Quelle nennt für Claude Desktop `mcp__Claude_Browser__*`; **aus dem Fehlen dieses Namens wird keine Hostfähigkeit abgeleitet**: welche Browserwerkzeuge Codex bietet, ist unbelegt (D). Ohne tatsächlich durchgeführte Sichtprüfung lautet das Ergebnis „technically checked, visual check open“ (R15). Es wird keine neue Browserintegration implementiert.
- `.claude/launch.json`: bestehende Funktion von `preview`; wird unverändert erhalten und als Claude-Desktop-Konfiguration gekennzeichnet; ihre Wirkung (`autoPort:false`) ist laut Quelle nicht im GUI beobachtet (D).

### 5.3 Weitere technische Punkte
- **Q4 Aufrufnamen:** Laufzeitmeldungen nennen den Skill neutral („der Skill `setup` des Plugins Website“); hostspezifische Aufrufschreibweisen gehören nur in Dokumentation und sind bis zum Hostnachweis *unverified* (D).
- **Q5 interne Namen:** Temp-Ordner `zyris-website`, `ZYRIS_WEBSITE_STATE_DIR`, Launch-Präfix `zyris-` bleiben unverändert (kein Anforderungsbedarf; eine Umbenennung machte laufende Preview-Instanzen unbekannt). Marker `zyris-optimize:*` sind Projektdaten (R21). Ändern wollen nur auf ausdrücklichen Wunsch.
- **Q7 Vertragsübernahme:** Übernommen wird nur normatives Verhalten; Stichtags-Audits, `draftmode.srv`-Snapshots, Cleanup-Inventar und datierte Hostbeobachtungen bleiben in der Quelle (D-04/D-05).
- **Q8 Mindestversionen:** Etappe 1 bestimmt Python statisch (ohne Ausführung); Untergrenze mindestens die des Managers. Node ≥ 22.23.4 ist Voraussetzung der Website-Werkzeuge (`docs/prerequisites.md`).

### 5.4 Q6 – Testklassifikation (B)
Nach tatsächlichem Verhalten, nicht nach Werkzeug:
- Tests mit Wegwerf-Git-Repos, Fake-`npm`, Fake-`ps`/`lsof` und lokalen Dateien: `tests/unit` bzw. `tests/integration` (deterministisch, D-10).
- `test_real_npm` (echtes `npm install`, Netzwerk): nicht deterministisch und nicht freigegeben; **kein** nativer Hosttest; Einordnung (Integration mit ausdrücklichem Schalter, im Standardlauf `NOT RUN`) wird in Etappe 2 gegen `tests/README.md` entschieden.
- Manuelle GUI-/Modellfälle B1–B11: `tests/behavior/` bzw. `tests/native/` je nachdem, ob Modellurteil oder Hostverhalten geprüft wird; stets `NOT RUN`, bis ausdrücklich ausgeführt.
- Zwei Quelltests mit Bezug zur echten Website (`test_static_adopt` Zeilen 205–206, `test_findings` Zeile 98): Ersatz durch fiktive Fixtures bzw. die mitgelieferte Vorlagenkopie der Prüfskripte; die Gleichheit von Vorlage und Site-Kopie ist unbelegt (nicht untersucht).

## 6. Q10 (Stand Etappe 0; beantwortet durch D-14, siehe Abschnitt 12)

**Q10 (vor Etappe 3):** Die bestehende Freigabe (D-10) gilt für deterministische Tests in isolierten Verzeichnissen; sie schließt Netzwerkzugriffe für Tests aus. Die `preview`-Tests starten echte lokale Prozesse, binden `127.0.0.1`-Ports, senden Signale an eigene Prozessgruppen und nutzen lokale HTTP-Server – ohne externes Netz. Fallen sie unter D-10? Wenn ja, laufen sie in Etappe 3; wenn nein, bleiben sie `NOT RUN`, und preview wird nur statisch geprüft. Alle anderen Tests (Wegwerf-Git-Repos, Fake-`npm`) sind durch D-10 gedeckt.

## 7. Fehlende Ausführungs- und Hostnachweise

Alle bis zur Ausführung `NOT RUN`: Claude- und Codex-Verhalten je Skill; Ersetzung von `${CLAUDE_PLUGIN_ROOT}` und Wirkung von `allowed-tools` je Host; Browserwerkzeuge je Host; Installation von `skills/_shared/` je Host; GUI-Fälle G1, B1–B11 der Quelle; Plugin-Ladetest (Quelle: für vier statt fünf Skills formuliert, Text zu berichtigen).

## 8. Textabweichungen ohne Entscheidungsbedarf (bei der Migration berichtigen)

| ID | Abweichung in der Quelle | Behandlung |
|---|---|---|
| T-01 | optimize-`SKILL.md` listet `edit` als „not implemented“ | streichen (D-01/D-06) |
| T-02 | `interfaces.md`-Kopf: `edit` „planning draft only“, §7 und `edit.md`: Startseite umgesetzt | Status aus SCOPE neu ableiten |
| T-03 | Entwicklungsdoku §1a: nur Teil von setup umgesetzt | nicht übernehmen |
| T-04 | `interfaces.md` §6, Entwicklungsdoku §8a: Ladetest mit vier Skills | als Hostfall mit fünf Skills neu fassen (`NOT RUN`) |
| T-05 | ZIP-/GUI-Upload, „neuer Chat nach Plugin-Update“ | entfällt (D-07); Pfadverhalten bleibt in R24 |
| T-06 | Skilltexte: „Tests: cd …/tests/…“, obwohl Tests nicht ausgeliefert werden | entfällt |
| T-07 | Quell-`plugin.json`: `0.1.0-dev`, Autor `draftmode` | Zielidentität gilt |
| T-08 | `/zyris-website:<skill>` in Texten und Vorlagen | siehe Q4; Datenformatnamen bleiben (R21) |
| T-09 | `preview.md` §2.3 D3/D4 und §10 als offen/missing, §11 setzt um/passed | als überholt behandeln (4.1) |
| T-10 | `optimize.md` §5 „default isolated copy“ | berichtigen (4.2) |
| T-11 | `preview.md` §3 „skill runs npm install“ | berichtigen (4.1) |
| T-12 | `publish.md` §2.2 D2 (alte Manifestfelder noch vorhanden) | überholt (Cleanup erfolgt laut `edit.md` §13) |

## 9. Wirkung der vollständigen Vertragslektüre

Gelesen wurden `preview.md`, `optimize.md`, `edit.md`, `publish.md` jetzt vollständig (`setup.md`, `interfaces.md`, `communication.md` und die fünf `SKILL.md` bereits in Etappe 0). Änderungen an Anforderungen: R10 (`needs-install` ohne Installation), R12 (Befundklassen, manuelle Prüfpunkte, nie installieren), R13 (keine erfundenen Fakten, kein Ranking-Versprechen), R15 (Sichtprüfung offen auch ohne Browserwerkzeug, verbotene Dateien), neu R22 (Voraussetzungen inkl. Lockfile, Auftragsregeln aus `edit.md` §2/§6), R23 (publish-Inhalt). Neue offene Fragen entstanden nicht; V1/V2 sind durch die Statusangaben geklärt. Die „implementiert“-/„passed“-Aussagen der Verträge wurden nicht als Nachweis übernommen.

## 10. Prüftiefe und Grenzen

Runtime und Tests der Quelle: nur strukturell geprüft (Importgraph, Pfadbezüge, Hashvergleich, Aufrufer von `Ask`/`manifest`); Logik und Testinhalte nicht auf Korrektheit geprüft. Nicht untersucht: `sites/`, `.project/`, reale Website-Inhalte. Nichts ausgeführt, keine Tests, kein Netzwerk, keine Installation.

Drift-Hinweis (Referenz): Beim erneuten Abgleich zeigt das Strukturreferenz-Repository `ai.plugin.interview-coach` uncommittete Änderungen anderer Herkunft (Verschiebung von `skills/interview-coach/references/` nach `skills/_shared/references/`, neue Tests unter `tests/support/`, `tests/integration/git/`). Die Hashes seiner in `reference-baseline.json` erfassten Regeldateien sind unverändert; nur der Git-Status weicht von der Basis ab. Die Basis bleibt unverändert erhalten; die Änderungen wurden nicht angefasst und sind vor Etappe 1 zu lesen, weil sie die `_shared`-Anordnung betreffen.

## 11. Änderungsprotokoll Review 1

| Datei | Änderung |
|---|---|
| `AGENTS.md` | Regel zu Tests/Runtime in drei getrennte Aussagen aufgeteilt (Migration/Tests, ausgelieferte Runtime, autorisierter Produktbetrieb) |
| `SCOPE.md` | Bestätigtes und Konkretisiertes getrennt (R1–R4, R14, R16, R18, R20 `confirmed`; Rest `draft`), neue R20–R26, Evidenzstatus je R, Kategorisierung offener Punkte, „Bekannte Einschränkung“ |
| `docs/migration/decisions.md` | vollständig überarbeitet (diese Datei) |
| `docs/migration/plan.md` | Prüfplan, Hostplanung, Etappenvoraussetzungen angepasst |
| Inventare | unverändert (Ausgangsstand erhalten) |

## 12. Fortschreibung in Etappe 1

### 12.1 Beantwortete Punkte
- Scope-Abnahme: D-12 (SCOPE.md: Gesamtstatus und R1–R26 `confirmed`, Quellenzeilen ergänzt).
- Initialisierungsregel: D-13 (SCOPE R5; Feldbelegung und drei offene Felder in `setup-init.md`).
- Q10: D-14. **Genaue Testgrenze:** erlaubt sind eigene lokale Prozesse, `127.0.0.1`-Ports und das Beenden ausschließlich selbst gestarteter, eindeutig identifizierter Testprozesse/-gruppen; nicht erlaubt sind externe Netzwerkzugriffe, das Signalisieren fremder Prozesse und jede Installation. Etappe 1 enthält keine Preview-Tests.

### 12.2 Technische Entscheidungen
| ID | Entscheidung | Beleg |
|---|---|---|
| E1-01 | V3: gemeinsame Module als Paket `skills/_shared/scripts/site_common/` (`schema`, `errors`, `manifest`, `sites`) plus Einstiegspunkt `skills/_shared/scripts/which_site.py`. Gründe: abweichende `setup`-Varianten von `errors`/`manifest` würden bei flachen Importen kollidieren; Zusammenlegung nur mit belegter Gleichheit (schema, errors: Hash; manifest, sites: Hash der preview/optimize-Kopien plus Prüfschritte). `setup/errors.py` und `setup/manifest.py` bleiben getrennt (Etappe 2). | `changes.md`, Tests `ImportIsolationTests` |
| E1-02 | Genau eine Schemadatei: `skills/_shared/resources/zyris-website.schema.json` (Name unverändert, R4). | Hash gleich Quelle |
| E1-03 | Q1/Q2: hostneutrale Pfadbasis (Ordner der geladenen `SKILL.md`), Claude- und Codex-Teil getrennt, Stopp bei unbekanntem Pfad; Hostbelege offen. | `host-conventions.md` |
| E1-04 | Q4: Meldungen der gemeinsamen Module nennen „the `setup` skill of the Website plugin“ statt `/zyris-website:setup`. | `changes.md` |
| E1-05 | Q8: Python ≥ 3.10, nur Standardbibliothek. | `host-conventions.md` §4.7 |
| E1-06 | Q6: Tests der gemeinsamen Module: `tests/unit/shared/` (in-process), `tests/integration/shared/` (Prozessstart aus Kopie), `tests/contracts/` (Struktur/Unabhängigkeit); Basiswerkzeug: `tests/unit/test_migration_baseline.py`. | `tests/` |

### 12.3 Neue Widersprüche und Hinweise (nicht selbst aufgelöst)
- **Plan §3.1 vs. Etappenauftrag:** plan.md §3.1 nennt den Block `user-communication` „in allen fünf `SKILL.md`“ in Etappe 1; der Etappenauftrag verbietet die öffentlichen `SKILL.md` vor Etappe 2. Etappe 1 hat nur die Referenz migriert; R17 bleibt für die SKILL-Texte offen (Plan §3.1/§5 entsprechend präzisiert).
- **`allowed-tools` und Plugin-Variablen (berichtigt):** Die Skills-Seite nennt die Ersetzung ausdrücklich, die Plugins-Referenz schweigt dazu – kein Widerspruch (Prüfung an den Originalseiten, `host-conventions.md`). Codex: Skillpfad wird dem Modell mitgegeben; Claude-Platzhalter werden dort nicht vorausgesetzt.
- **Referenz-Drift (nicht inhaltlich relevant):** `ai.plugin.interview-coach/SCOPE.md` weicht vom Hash in `reference-baseline.json` ab (fremde, uncommittete Arbeit am Coach). Regeln und Vorlagen von `ai.plugins` sind unverändert. Der Coach hat `skills/_shared/{references,scripts}` und die Aufrufform „`../_shared/scripts/…` von einem Skillordner aus“; das wurde gelesen und bestätigt die geplante `_shared`-Anordnung. Die Inventardatei bleibt unverändert.

### 12.4 Korrekturen nach Review 1 von Etappe 1
- `migration_baseline.py`: Inventar- und Pfadvalidierung vor dem Lesen, keine Symlink-Verfolgung (auch nicht in Pfadkomponenten), `plugin_root` Pflicht, Exit 2 mit Diagnose statt Ausnahme; Tests mit fiktiven Daten.
- `interfaces.md`: Schreibinventar für `edit` auf `src/pages/index.astro` begrenzt (R14); `optimize apply` ergänzt (R13).
- `host-conventions.md`: Codex setzt `${CLAUDE_SKILL_DIR}` nicht voraus; Aussagen gegen Originalseiten geprüft; frühere „Widerspruch“-Aussage zurückgenommen.
- `setup-init.md`: Herkunft der Felder getrennt, Empfehlung für `$schema`, `title`, `port` (nicht entschieden).
- Referenz-Drift: außer `ai.plugin.interview-coach/SCOPE.md` weichen jetzt auch dessen `docs/architecture.md` und `tests/README.md` ab (fremde Coach-Arbeit, coach-spezifische Inhalte, keine Wirkung auf die `_shared`-Struktur); `ai.plugins`-Regeldateien unverändert.

## 13. Fortschreibung in Etappe 2 (setup, Schemaumbenennung)

### 13.1 Beantwortet
D-16 (Manifestfeldbelegung, schließt O1–O3 von `setup-init.md`), D-17 (Schemaumbenennung), D-18 (kein Altformat). Die Schemaumbenennung ist als begrenzte Ausnahme dokumentiert; sie ändert nur den Dateinamen (Bytes gleich dem Inventar), nicht den Inhalt. Der Schema-`title` im Inhalt („zyris-website manifest“) bleibt unverändert, weil nur der Dateiname beauftragt ist.

### 13.2 Technische Entscheidungen
| ID | Entscheidung | Beleg |
|---|---|---|
| E2-01 | Die `setup`-Varianten `errors.py` (byte-gleich zur Quelle) und `manifest.py` bleiben getrennt (andere Signatur `problems(data, schema_file_or_dict, type_names)`, `files()`, eigene `Stop`/`Ask`-Klassen, Typprüfung gegen `types.json`). Sie importieren nur Konstanten, den Schemapfad und `legacy_problem` aus `site_common.manifest` sowie den Validator `site_common.schema`; `setup/schema.py` entfällt (eine Kopie). `Stop`-Klassen werden nie gemischt: `legacy_problem` liefert Text, keine Ausnahme. | `tests/contracts/test_setup_contract.py`, `tests/unit/setup/test_schema.py` |
| E2-02 | Altformaterkennung (`site_common.manifest.legacy_problem`): abgelehnt wird (a) ein Manifest mit `"$schema": "./zyris-website.schema.json"`, (b) ein Projekt, in dem `zyris-website.schema.json` existiert und `website.schema.json` fehlt (auch ohne Manifest). Nicht abgelehnt: eine alte Datei neben vorhandener neuer Kopie (Altlast, bleibt unberührt), ein neues Projekt ohne Altdateien. Die Erkennung gilt für `setup` (create/adopt/plan/verify) und über `sites.load` für alle gemeinsamen Verbraucher. Die alte Datei wird nur auf Existenz geprüft, nie gelesen, geschrieben oder gelöscht. | `tests/integration/setup/test_init_ports_legacy.py::FormerFormatTests` |
| E2-03 | Zustände der Schemakopie (Vertrag R5/R8, `setup.md` §3): fehlend (kein Altformat) → create/adopt legen sie an, `verify` und die anderen Verbraucher stoppen; identisch → behalten; vom Besitzprotokoll geführt und unverändert → ersetzt; fremd/beschädigt/ohne Protokoll abweichend → `conflict` ohne Schreiben. Dieser Fall war im Vertrag eindeutig; es wurde keine Altformat-Unterstützung eingebaut. | `SchemaCopyStateTests`, `test_static_adopt.py::SchemaProtectionTests` |
| E2-04 | Portwahl: `manifest.next_port` = 4321 im leeren Projekt, sonst höchster effektiver Port + 1. Effektiv = expliziter Port, sonst `site_common.sites.BASE_PORT` + Position (dieselbe Regel wie der Resolver). Ein ausdrücklicher Port wird gegen alle effektiven Ports geprüft (Quelle prüfte nur explizite). Ein Eintrag ohne eigenen Port wird nie mit seinem abgeleiteten Wert umgeschrieben. `types.json` `base_port` bleibt unverändert (Hashgleichheit) und wird per Test gegen `BASE_PORT` gebunden. | `PortSelectionTests` |
| E2-05 | Laufzeitpfade: `RES` = `skills/setup/templates`, Schema = `skills/_shared/resources/website.schema.json`; `site_setup.py` setzt `sys.path` selbst (eigener Ordner, `../../_shared/scripts`). Ein fehlendes Schema in der Kopie stoppt jetzt mit `STOP`/`invalid` vor dem Schreiben (in der Quelle wäre es ein Traceback gewesen, siehe 13.4). | `IsolatedPluginCopyTests` |
| E2-06 | Der Skeleton-Skill `skills/website-manager/` wurde entfernt, nachdem geprüft war, dass er nur die bekannte `SKILL.md` mit Marker `plugin-skeleton: unimplemented` enthielt. `docs/documentation.json` `source_skill` zeigt vorläufig auf `skills/setup` (muss auf eine vorhandene `SKILL.md` zeigen); Etappe 6 prüft die Dokumentationsquelle erneut. | `test_skeleton_skill_is_gone_and_not_aliased` |
| E2-07 | Testeinordnung (Q6): Fake-`npm`-Tests mit Wegwerf-Git-Repos → `tests/integration/setup`; reine Funktionsprüfungen → `tests/unit/setup`; Struktur/Text/Hash → `tests/contracts`. Zwei Quelltests, die das echte `npm` starten (`test_real_npm.py` und der Teil `test_real_npm_exit_codes_without_network` aus `test_static_adopt`), liegen gemeinsam in `tests/external/setup/test_real_npm.py` (korrigiert nach Review: zuerst unter `tests/integration/` hinter `ZW_REAL_NPM=1`, was ein geerbtes `ZW_REAL_NPM=1` im Standardlauf aktivierte; jetzt außerhalb der Schichten, Freischaltung nur über `scripts/run_external_tests.py --approved` per Modulflag); im Adopt-Test ersetzt ein Fake-Runner mit denselben simulierten Exit-Codes. | `test_real_npm.py` |
| E2-07a | Die Altformaterkennung (E2-02) erkennt jetzt jede eindeutig gleichbedeutende lokale Schreibweise des Verweises (`zyris-website.schema.json`, `./…`, `././…`, `a/../…`) per Normalisierung des Textes; URLs, absolute Pfade, `../…`, Unterordner und andere Dateinamen werden nicht verwechselt; keine Teilstringprüfung, nichts wird abgerufen oder gelesen. Zuvor nur exakt `./zyris-website.schema.json` (Reviewbefund). | `FormerFormatTests` |
| E2-07b | Die normative Referenz `skills/setup/references/setup.md` ist aus den bestätigten Teilen des Quellvertrags (§1–§4) und SCOPE R5/R8/R9/D-16–D-18 geschrieben; ohne Audits, Geplantes, Testmatrix und „bestanden“-Aussagen. Aktive Verweise auf `contracts/setup.md` in Skripten (Docstrings, Meldungen der nicht verfügbaren Funktionen) sind ersetzt. | `SkillTextTests` |
| E2-08 | Quelltest gegen die echte Website (`test_current_draftmode_project_files…`) ersetzt durch einen Test auf einem von `setup` erzeugten fiktiven Projekt; Quelltest `test_validator_copies` ersetzt durch Vergleich der setup- und der gemeinsamen Variante. Echte Domänennamen in `test_validate` durch fiktive ersetzt. | `changes.md` |
| E2-09 | Hostrecherche (`host-conventions.md` §8) und Korrektur: „nicht dokumentiert“ für Codex ist kein „keine Wirkung“. | `host-conventions.md` |

### 13.3 Offene Punkte
- Keine neue Nutzerentscheidung offen. Zur Kenntnis: Die Altformaterkennung (E2-02) ist eine Auslegung des Auftrags („Ein Projekt im alten Format wird mit konkreter Diagnose … abgelehnt“); ein Projekt, das nur eine Altlast-Datei neben der neuen Kopie hat, wird bewusst nicht abgelehnt.
- Die Beschreibung im Quellvertrag `setup.md` §3 („next free from 4321“) entspricht der neuen, beauftragten Portregel nur teilweise; maßgeblich ist D-16.

### 13.4 Erkannte Bestandsdefekte der Quelle (nicht Migrationsfehler)
- **B-1** Fehlte das Plugin-Schema in der Installation, endete `static_setup.load_schema_bytes` in einem Traceback (`FileNotFoundError`) statt in `STOP`. Im Ziel behoben (E2-05); Verhalten ändert sich nur im Fehlerfall.
- **B-2** Die Quelle prüfte einen ausdrücklichen `--port` nur gegen explizit gesetzte Ports, nicht gegen die vom Resolver abgeleiteten (4321 + Position); eine Kollision wäre erst im Resolver aufgefallen. Im Ziel durch D-16 abgedeckt (E2-04).
- **B-3** `types.json` trägt `defaults.base_port`, der Resolver `BASE_PORT`: zwei Quellen derselben Zahl; im Ziel per Test gleichgehalten, Datei byte-gleich belassen.

