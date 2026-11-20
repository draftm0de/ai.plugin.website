---
name: optimize
description: Audit SEO and accessibility of a website in this repository (sites folder per domain), keep dated reports and a running work list of findings, and implement only the proposals the person approved. Use when the user asks about SEO, search visibility, meta tags, sitemap, social cards, accessibility checks, or before publishing new or changed pages. GEO (generative engine optimization) is not available.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py" *)'
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py")'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/audit.py")'
---

# optimize (Website plugin)

> **Status (local development).** Available: audit with durable reports and a running work list, decisions, bounded `apply` of approved mechanical proposals with an automatic recheck, and the site resolver. **Not available (do not offer, do not work around):** GEO, Lighthouse, link-graph checks, an isolated dependency copy with `npm ci`. This skill never installs dependencies, not even for `apply`.

> **Script location (binding).** The scripts are `scripts/audit.py` next to the **actually loaded** `SKILL.md` and the shared resolver `../_shared/scripts/which_site.py` (relative to the folder of that `SKILL.md`). Run them with the **website project** as working directory (or `--root`). Site configuration (`.project/`, `sites/`) and content always come from that project; the plugin folder is read-only and holds no state. The manifest `.project/specs/zyris-website.json` is validated against the plugin's own schema before anything is built or written; an invalid manifest or the former project format (schema file `zyris-website.schema.json`) stops the skill with a diagnosis, without migration or fallback.
>
> - **Claude:** the host replaces `${CLAUDE_SKILL_DIR}` with the folder of this `SKILL.md`; the commands below use it in double quotes. The `allowed-tools` pre-approvals above are Claude-specific and exactly the call patterns of this text; they are a convenience, not a requirement.
> - **Codex:** use the path of the loaded `SKILL.md` that the host gave you and form the absolute script paths `<folder of that SKILL.md>/scripts/audit.py` and `<folder of that SKILL.md>/../_shared/scripts/which_site.py`. Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable; do not rely on a Claude placeholder or on `allowed-tools`.
> - **No path, no run:** if the path of the loaded `SKILL.md` is not available, stop and say so. Do not search caches or plugin folders, do not guess a replacement path, never copy scripts into the website project.
> - **Form of the call:** `python3 -B` with each script path as **one** quoted argument (the path may contain spaces), no `PYTHONPATH`. Before the first call check that both scripts exist (`test -f "<script path>"`); if one is missing or outdated, stop and report that the plugin path is missing or outdated.

## Operator language (first)

Before setup/domain interaction, read and follow `../_shared/references/operator-language.md`. Its persisted project preference governs the language in the communication rules below. Missing preference: ask the language question alone, wait, and persist the explicit answer before continuing.

<!-- user-communication -->
## Working with the person (binding)

- **Language and tone:** answer in the language of the person, including every short remark between steps (no English remarks for a German-speaking person); short, concrete, no technical knowledge assumed.
- **Finish the work yourself:** do everything the order covers and that is technically possible. A concrete order is the release for exactly the work it covers; no extra confirmation. A blocked part never stops independent parts: do those, report the blocked one at the end. Do not extend to deployment, other people's processes or project changes the order does not cover.
- **Ask rarely:** only when information or a decision is missing that really changes the result, as one specific question. Never "how should we continue?" while authorised, technically possible work is left or when the next step follows from the order.
- **Progress:** a message only for an important new finding, a longer wait or a needed decision; none per tool call, browser step or test.
- **Final answer:** normally 2-4 short sentences, about 100 words at most. It says what changed for the person, whether it works according to the checks that were run, where to look at it (a clickable link), and what the person must still decide or do (only if really needed). A relevant limit is said plainly. A required check that is missing means the order is not fully checked, and it is never relabelled as optional afterwards. An optional extra check that was left out does not stop the work: mention it only if its absence matters for this result, briefly, and do not repeat it endlessly.
- **Not in the default answer:** process IDs, ports, script names, exit codes, hashes, CSS measurements, console messages, full diffs, git status, temporary archive paths, and repeated "no commit, push or deployment". Keep them internally for a diagnosis or audit the person asks for. After a failure keep what is needed to recover (what was kept, where) and say it briefly and plainly.
<!-- /user-communication -->

## Read first

Before the first call read, relative to the folder of this loaded `SKILL.md`:

1. `references/optimize.md`: the full behaviour (modes, result states, finding classes, decisions, apply, reports, work list, errors, limits). Report only what it and the command output say.
2. `../_shared/references/interfaces.md`: rules shared by all Website skills (site selection, exit codes, evidence, secrets, manifest contract, write inventory).

If one of these files cannot be read, say so and do not reconstruct its content from memory or search other folders; the command output stays authoritative.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py" [site] [--cwd <dir>] [--last <domain>] [--root <dir>]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" <audit|show> [--site <name>] [--editorial <file>] [--applied <ID> ...] [--cwd <dir>] [--last <domain>] [--root <dir>]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" propose --proposals <file> [--site <name>] [--root <dir>]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" decide <ID> [<ID> ...] --status <proposed|approved|deferred|wont-do> [--reason "<text>"] [--change] [--site <name>] [--root <dir>]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/audit.py" apply <ID> [<ID> ...] [--site <name>] [--root <dir>]
```

Existence check before the first call: `test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/which_site.py"` and `test -f "${CLAUDE_SKILL_DIR}/scripts/audit.py"` (Codex: the same checks with the absolute script paths).

Works on one site of `.project/specs/zyris-website.json`. Brand rules (tone, colors, images) are in `.project/brand/`: read them before you write any proposed text. The web rules belong to the site: `<site>/rules/seo.md` and `<site>/rules/accessibility.md` (both binding).

## What the default call does

A bare "optimize" is **audit, write proposals, reconcile the work list. No repair.** An audit never edits site content, never installs dependencies, never commits. It writes only:

- `.project/reports/<site>/optimize/<timestamp>.md`: immutable snapshot of this run (time with zone, source commit, every check with its real exit code, output tail, skipped or failed checks, findings, changes since the last run, limits).
- `.project/reports/<site>/optimize.md`: the **one authoritative work list** (open work, deferred/rejected, done history). It is generated from a machine-readable block at its end and must not be edited by hand (a hand edit makes the next run stop; restore it from your own backup).

Finding statuses are exactly `proposed`, `approved`, `deferred`, `wont-do`. "Done" is not a status: it is a recorded result of a passed recheck. Audit and decision never authorise `apply`.

## Steps

1. **Site:** `which_site.py [site] ...`. Exit `0`: JSON with `site`, `path`, `rule_files`, ... (if `confirm` is true, say which site you use). Exit `2`: ask the `ask` question with the `options`, then run again. Exit `1` (`STOP: ...`): show it and stop. If `rule_files` lacks `seo.md` or `accessibility.md`, stop: the site has no rules yet.
2. **Audit:** `audit.py audit --site <name>`. It builds into the git-ignored `dist/`, then runs `seo:check` and `a11y:check` **independently** (an SEO error does not hide the accessibility result), reads the process exit codes and compares project source paths and hashes before and after. The JSON `status` is `clean`, `clean-with-warnings`, `errors`, `incomplete` (a tool, dependency, lockfile, build or unreadable output is missing: **never** reported as clean) or `readonly-violated` (a project source file changed during the run: listed, not reverted). Exit `0` only for `clean*`. Report the status honestly, including every `incomplete` reason. If dependencies are missing, say so and give `npm ci` in the site folder for the person to run; this skill does not install. Report the result as passed only for a check that ran in this call and ended with exit `0`.
3. **Proposals:** for each finding that needs concrete text, read the source file named in the work list and write a draft that follows the rules and the brand voice. Use only facts already on the page; no invented claims, ratings, dates or structured data; no ranking promise; do not pad text to reach a length. Write a proposals file **outside the repository** (scratchpad) as JSON `{"<finding ID or criterion|location|detail>": {"summary", "kind": "draft", "current", "proposed", "edit": {"file", "find", "replace"}, "source", "limits"}}` and store it with `audit.py propose --proposals <file>` (no new run). `edit` makes the proposal mechanically applicable: `file` repo-relative inside the site, `find` text occurring exactly once. Editorial suggestions (judgement, not a check) go in a JSON list passed with `audit --editorial <file>` (`criterion`, `location`, `title`, `evidence`, `proposal`, optional `proposal.verify` `{file, present|absent}` to make one property confirmable). Mark them as editorial; never present them as test results.
4. **Show:** `audit.py show` lists open, parked and done findings. Present open work with ID, class, location, evidence, proposal and priority. Do not ask for approval of things that are already `approved`.

## Decisions (by finding ID)

| The person says | You run | Effect |
|---|---|---|
| approve SEO-001 | `audit.py decide SEO-001 --status approved [--reason "..."]` | stores the decision for the documented proposal only; changes nothing else |
| defer SEO-001 | `... --status deferred` | kept across runs |
| reject SEO-001 | `... --status wont-do` | not proposed or released again automatically |
| an explicit change of an earlier decision | add `--change` | without it a decided finding is refused |
| implement SEO-001 | decide `approved` if it is still open (the scope must already be concrete), then apply | see below |
| implement the approved points | apply exactly the findings that are already `approved` | no other finding |

An approval is bound to the documented proposal **and** its starting point. If either changed since (a new draft, a changed current text), the next run shows the deviation, resets the finding to `proposed` with an attention note, and the person decides again. Unchanged approvals are never asked for again.

## Implementing approved proposals

1. Check each ID is `approved` and unresolved. Do not touch anything else: no neighbouring wording, design, rules, `package.json`, lockfile.
2. If the proposal has an `edit`: `audit.py apply SEO-001 [SEO-003 ...]`. It refuses unapproved or stale proposals, requires the find text exactly once in a non-ignored project source file inside the selected site (no path outside the site, no traversal, no symbolic link, no unversioned file), edits only that file, then runs the recheck itself. It installs nothing and commits nothing.
3. If the proposal has no mechanical `edit`: make the change by hand **within the documented scope only** (one file at a time), then run `audit.py audit --applied SEO-001`.
4. The recheck is the same audit (build, `seo:check`, `a11y:check` independently, guard) and is **not** left to the person. A finding moves to the history only when a complete run after a successful build no longer reports it; the decision and the evidence stay with it. If it persists, the check is incomplete or the build fails, it stays open and approved, with the reason and the next step in its attention note. Improving within the same approved scope needs no new approval.
5. Report what changed, the check results and what could not be checked. Do not commit.

## Repeated audits

Findings are matched by site + criterion + location (never by message text or line number): IDs and decisions are preserved, nothing is duplicated, `wont-do` stays, `deferred` stays. A problem marked done that returns is shown as **reappeared** (same ID) and goes back to the person. A fix made outside optimize is accepted only when a complete run proves it. Confirmed means only what a check can confirm locally: never better rankings, traffic or snippets. Technical errors, warnings and editorial recommendations stay separate classes; manual check points (contrast, keyboard, screen reader, truthfulness of claims, legal pages) are listed in every report and are never reported as passed.

Things only the person can do (list them, do not attempt): Search Console and Bing Webmaster registration, DNS and server redirects, legal pages (imprint, privacy policy), colour contrast, keyboard and screen-reader checks, truthfulness of page claims.

## Rules

- Scripts contain logic only. `scripts/` holds the driver `audit.py` and its helpers `findings.py` (adapter for the output of the site's checks), `worklist.py` and `store.py`; the site resolver and the manifest validator are shared (`../_shared/`). Dev tests are not part of this skill; do not run any.
- Do not weaken a check, do not edit the site's check scripts to make a finding disappear.
- Never put secrets or full environment variables in a report or the chat.
- The report and work-list formats and their markers (`zyris-optimize:*`) are project data and stay as they are.
