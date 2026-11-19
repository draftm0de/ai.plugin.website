# Hostkonventionen: Aufrufpfade, Freigabemuster, Auslieferung

Migrationsnachweis zu Q1/Q2/Q8 (decisions.md), Stand Etappe-1-Korrektur. Technische Dokumentationsrecherche, **kein** Runtime- oder Hosttest. Die Skilltexte der späteren Etappen übernehmen diese Konvention; hier entstehen keine öffentlichen Skills.

## 1. Quellen (Originalseiten gelesen am 2026-11-19)

| Quelle | Lesestand |
|---|---|
| Claude Code Skills `https://code.claude.com/docs/en/skills` | vollständig bis zum Abschnitt Shell-Injection; der Rest nur als Zusammenfassung |
| Claude Code Plugins-Referenz `https://code.claude.com/docs/en/plugins-reference` | vollständig |
| Claude Code Plugin-Laden `https://code.claude.com/docs/en/plugins/loading` | vollständig |
| Claude Code Permissions `https://code.claude.com/docs/en/permissions` | wörtlich bis rund 80 von 92 kB; Rest nur Zusammenfassung |
| OpenAI Codex Skills `https://developers.openai.com/codex/skills` (Weiterleitung 308 auf `https://learn.chatgpt.com/docs/build-skills`) und `https://developers.openai.com/plugins/build/skills` | vollständig |
| Lokal: Manager `ai.plugins/plugins/plugin-manager/skills/*/SKILL.md`, Coach `skills/_shared/references/runtime.md` | gelesen; bestehende Konvention: relative Verweise `../_shared/…` vom Skillordner aus |

Die Seiten wurden durch ein Lesewerkzeug zugänglich gemacht; Wortlaute sind nicht Zeichen für Zeichen geprüft. Vor der Verwendung in einem Skilltext einmal an der Originalseite gegenlesen.

## 2. Dokumentierte Aussagen

**Claude Code**
- `${CLAUDE_SKILL_DIR}`: „The directory containing the skill's SKILL.md file“; wird im Skilltext **und** in Bash-Regeln von `allowed-tools` ersetzt. `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}`: nur in Plugin-Skills, an denselben zwei Stellen. Die Plugins-Referenz nennt `allowed-tools` nicht; das ist Schweigen, **kein Widerspruch** (frühere Fassung dieser Datei sprach irrtümlich von einem Widerspruch).
- `allowed-tools`: Leerzeichen-/Komma-getrennte Zeichenkette oder YAML-Liste; erteilt Freigabe ohne Rückfrage, schränkt die verfügbaren Werkzeuge nicht ein. Beispiel der Doku: `Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)`.
- Bash-Regeln: `*` passt auf beliebigen Text einschließlich Leerzeichen; `Bash(ls *)` passt auf `ls -la`, nicht auf `lsof`; Regeln gelten für den gesamten Befehlstext; zusammengesetzte Befehle müssen je Teil passen.
- Marketplace-Plugins werden in `…/cache/<marketplace>/<plugin>/<version>/` kopiert; Dateien außerhalb des Plugin-Ordners werden nicht kopiert; `${CLAUDE_PLUGIN_ROOT}` ändert sich bei Updates, dort keinen Zustand schreiben.

**Codex**
- Frontmatter: `name`, `description` erforderlich; weitere `SKILL.md`-Felder nicht dokumentiert; optional `agents/openai.yaml`.
- Unterstützungsordner `scripts/`, `references/`, `assets/` im Skillordner; Hinweis „Reference supporting files from SKILL.md“.
- Dem Modell wird laut Codex-Seite zusammen mit Name und Beschreibung **der Dateipfad jedes Skills** mitgegeben.

## 3. Nicht dokumentiert (unbelegt, nicht erfunden)

- Claude: Behandlung von Anführungszeichen und Pfaden mit Leerzeichen in Bash-Regeln; ob `${CLAUDE_SKILL_DIR}/../_shared/…` (mit `..`) in einer Regel passt; ob der Plugin-Ordner vollständig kopiert wird (wörtlich nicht gesagt, auch `skills/_shared/` nicht erwähnt); ob ein Ordner ohne `SKILL.md` ignoriert wird.
- Codex: Basis relativer Skriptpfade; jedes Skill-Variablenkonzept; Pfad zu Geschwisterordnern wie `skills/_shared/`; ob sie installiert werden; Vorabfreigabe für Skills (keine `allowed-tools`-Entsprechung dokumentiert).
- Ob ein Host Schreiben ins Plugin-Verzeichnis technisch verhindert.

Hostnachweis für alle Punkte: **NOT RUN**.

## 4. Festgelegte Konvention (hostneutraler Teil)

1. **Pfadbasis.** Gemeinsame Basis ist das Verzeichnis der **tatsächlich geladenen** `SKILL.md` („Skillordner“). Skriptpfad eines Skills: `<Skillordner>/scripts/<einstieg>.py`; gemeinsamer Ordner: `<Skillordner>/../_shared`. Das ist eine reine Pfadbeschreibung ohne Platzhaltersyntax.
2. **Claude.** Der Host liefert den Skillordner über `${CLAUDE_SKILL_DIR}` (siehe Abschnitt 5).
3. **Codex.** Es wird der vom Host bereitgestellte Pfad der geladenen `SKILL.md` verwendet; daraus bildet der Agent den **absoluten** Skriptpfad. Ein Claude-Platzhalter wird **nicht** als Shellvariable ausgeführt oder erwartet. Die Codex-Dokumentation nennt `${CLAUDE_SKILL_DIR}` nicht; ob Codex sie ersetzt, ist **unbelegt (NOT RUN)** – deshalb wird sie dort weder vorausgesetzt noch verwendet, und nichts folgt daraus über eine Nichtunterstützung.
4. **Pfad nicht verfügbar.** Ist der tatsächliche Skillpfad nicht bekannt, stoppt der Skill mit einer konkreten Meldung („Pfad der geladenen SKILL.md nicht verfügbar“). Keine Suche in Caches oder Plugin-Verzeichnissen, keine Ersatzpfade, keine Kopien der Skripte ins Websiteprojekt, kein Raten.
5. **Aufrufform.** `python3 -B "<absoluter Skriptpfad>" <Argumente>`: der Skriptpfad ist **ein** Argument (Anführungszeichen, Leerzeichen im Pfad möglich); `-B` verhindert Bytecode im installierten Plugin (Test `test_bytecode_suppression_flag_…`); kein `PYTHONPATH`; Einstiegspunkte laufen auch unter `python3 -I -B` (sie fügen ihren Ordner selbst in `sys.path` ein).
6. **Vorprüfung.** Vor dem ersten Aufruf `test -f "<absoluter Skriptpfad>"`; fehlt die Datei, stoppt der Skill mit Meldung und kopiert nichts (R24). `publish` hat weder Aufruf noch Prüfung.
7. **Zustand.** Die Runtime schreibt nie in das installierte Plugin; Zustand liegt im Websiteprojekt oder in `<TMPDIR>/zyris-website/…` (Q5).
8. **Mindestversionen (Q8).** Python ≥ 3.10 (Manager-Voraussetzung), nur Standardbibliothek, keine 3.11+-Syntax. Lokal ausgeführt wurde nur die vorhandene Python-Version (3.15.0).

## 5. Claude-spezifisch (getrennt gekennzeichnet)

- Im Skilltext darf `${CLAUDE_SKILL_DIR}` den Skillordner bezeichnen; der Host ersetzt ihn (dokumentiert).
- `allowed-tools` nur mit schmalen Mustern, exakt aus den Aufrufmustern desselben Skilltexts abgeleitet, z. B. `Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/<einstieg>.py" *)` und für den Resolver `Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py" *)`. Nicht erlaubt: `Bash(python3 *)`, `Bash(python3:*)`, `Bash(*)`, Freigaben beliebiger Shellbefehle.
- Die Einzelmuster legen die Etappen 2–5 mit den Skills fest (Etappe 2: `setup`, siehe unten); ein Vertragstest prüft dann, dass jedes Aufrufmuster von genau einem Muster gedeckt ist und umgekehrt. Ob der Host Muster mit Anführungszeichen, Leerzeichen und `..` tatsächlich deckt, ist unbelegt (NOT RUN). Fällt der Test des Hosts negativ aus, ist die Form anzupassen; die Freigabe darf nie verbreitert werden.
- Die Freigabe ist eine Bequemlichkeit, keine Voraussetzung: ohne sie fragt Claude die Person.

## 6. Codex-spezifisch

- Keine Vorabfreigabe wird behauptet, angelegt oder vorausgesetzt; Befehle laufen unter Sandbox und Genehmigungsrichtlinie der Person.
- Keine Frontmatter-Felder außer `name` und `description` für Codex voraussetzen; zusätzliche Claude-Felder (`allowed-tools`) werden in der Codex-Dokumentation nicht erwähnt (‚nicht dokumentiert‘). Daraus folgt weder, dass sie dort wirkungslos sind, noch dass sie nicht unterstützt oder geduldet werden: Wirkung und Duldung sind **unbelegt (NOT RUN)**. Die Skilltexte verlassen sich für Codex nicht darauf.

## 7. Belegklassen

| Aussage | Klasse |
|---|---|
| `${CLAUDE_SKILL_DIR}` wird bei Claude in Skilltext und `allowed-tools` ersetzt | dokumentiert (Originalseite) |
| Codex gibt dem Modell den Skill-Dateipfad | dokumentiert (Originalseite) |
| Aufruf mit einem Pfadargument, `-B`, ohne `PYTHONPATH`, aus Kopie mit Leerzeichen | lokal deterministisch geprüft, **kein** Hostnachweis |
| `skills/_shared/` wird installiert und ist erreichbar (beide Hosts) | unbelegt, NOT RUN |
| Bash-Regel deckt Anführungszeichen/Leerzeichen/`..` | unbelegt, NOT RUN |
| Codex tolerant gegenüber `allowed-tools`; Codex-Pfadauflösung in der Praxis | unbelegt, NOT RUN |

## 8. Gegenlesen vor Verwendung im Skilltext (Etappe 2, 2026-11-19)

Technische Dokumentationsrecherche, **kein** Hosttest. Gelesen wurden die Originalseiten erneut durch ein Lesewerkzeug; Lesestand je Aussage:

| Aussage | Ergebnis |
|---|---|
| Claude: `${CLAUDE_SKILL_DIR}` = Ordner der `SKILL.md`, ersetzt auch in Bash-Regeln von `allowed-tools`; Beispiel `Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)` | bestätigt, aber nur als Zusammenfassung des Lesewerkzeugs (Seite nur zu etwa einem Drittel wörtlich gelesen) |
| Claude: `allowed-tools` erteilt Freigabe ohne Rückfrage, schränkt Werkzeuge nicht ein | bestätigt (Zusammenfassung) |
| Claude: Anführungszeichen oder Leerzeichen in Bash-Regeln bzw. expandierten Pfaden | **nicht dokumentiert** → unbelegt |
| Claude Plugins-Referenz: `${CLAUDE_PLUGIN_ROOT}` in Skilltexten ersetzt; `allowed-tools` für Skills nicht erwähnt; Pfade müssen im Pluginordner liegen; Geschwisterordner wie `skills/_shared` nicht erwähnt | wörtlich bestätigt; `_shared`-Installation bleibt unbelegt (NOT RUN) |
| Codex (Seite `plugins/build/skills`): Frontmatter-Beispiel nur `name` und `description`; Unterstützungsordner `scripts/`, `references/`, `assets/` | bestätigt |
| Codex: Modell erhält den Skill-Dateipfad | in dieser Runde **nicht erneut bestätigt** (Weiterleitung `…/codex/skills` → `learn.chatgpt.com` nicht gelesen); frühere Lesung aus Etappe 1 bleibt, gilt hier als Hinweis, nicht als Beleg |
| Codex: zusätzliche Frontmatter-Felder, Variablen wie `${CLAUDE_SKILL_DIR}` | **nicht erwähnt** (kein Beleg für Wirkung oder Nichtunterstützung) |

Folge für `setup`: Der Claude-Teil des Skilltextes nutzt `${CLAUDE_SKILL_DIR}` und ein schmales `allowed-tools`-Muster; der Codex-Teil verlangt den vom Host gelieferten Pfad der geladenen `SKILL.md`. Die praktische Wirkung auf beiden Hosts bleibt **NOT RUN**.
