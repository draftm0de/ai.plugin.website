---
name: preview
description: Show a website of this repository locally - pick the site from .project/specs/website.json, start its dev server with the controller, check the served page and open the controller's address in the host's browser tool. Use when the user wants to see a site, a page or a change locally.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/control.py")'
---

# preview (Website plugin)

Shows one site from `sites/<domain>/` locally. Only the controller `scripts/control.py` starts, reuses or stops a dev server; this skill never installs dependencies.

> **Script location (binding).** The script is `scripts/control.py` next to the **actually loaded** `SKILL.md`. Run it with the **website project** as working directory (or `--root`). Site configuration (`.project/`, `sites/`) always comes from that project; templates and the shared schema stay inside the plugin and are never written to.
>
> - **Claude:** the host replaces `${CLAUDE_SKILL_DIR}` with the folder of this `SKILL.md`; the commands below use it in double quotes. The `allowed-tools` pre-approvals above are Claude-specific and exactly the two call patterns of this text; they are a convenience, not a requirement.
> - **Codex:** use the path of the loaded `SKILL.md` that the host gave you and form the absolute script path `<folder of that SKILL.md>/scripts/control.py`. Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable; do not rely on a Claude placeholder or on `allowed-tools`.
> - **No path, no run:** if the path of the loaded `SKILL.md` is not available, stop and say so. Do not search caches or plugin folders, do not guess a replacement path, never copy scripts into the website project.
> - **Form of the call:** `python3 -B` with the script path as **one** quoted argument (the path may contain spaces), no `PYTHONPATH`. Before the first call check that the script exists (`test -f "<script path>"`); if it is missing or outdated, stop and report that the plugin path is missing or outdated.

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

1. `references/preview.md`: the full behaviour (ownership proof, states, exit codes, `inspect`, browser and host limits). Report only what it and the command output say.
2. `../_shared/references/interfaces.md`: rules shared by all Website skills (site selection, exit codes, evidence, secrets, manifest contract).

If one of these files cannot be read, say so and do not reconstruct its content from memory or search other folders; the command output stays authoritative.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" <start|status|stop> [site] [--page /about.html] [--cwd <dir>] [--last <domain>] [--root <dir>] [--timeout 60]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/control.py" inspect [site] [--page /] --expect <text the current page must show> [--expect ...] [--root <dir>]
```

Existence check before the first call: `test -f "${CLAUDE_SKILL_DIR}/scripts/control.py"` (Codex: the same check with the absolute script path).

## Which site

The site is never guessed. The shared resolver (called by `control.py`) decides: named by the person (domain, folder, title or alias) -> working directory inside a site -> only one site exists -> site used last in this conversation (say which one; `status` and `stop` ask first) -> ask.

## Steps

Verbs: `start` (default), `status`, `stop`, `inspect`.

1. Run the verb. Read the exit code and the JSON `state`:
   - `0`: `running-new`, `running-reused` (`url`), `not-running`, `stopped`, `page-confirmed`.
   - `2`: JSON with `ask` and `options`: ask exactly that, run again with the answer as `site`.
   - `1`: evaluate `state` and `message`/`reason`; tell the person the problem and the next step. `needs-install` (dependencies missing: the person runs `npm install` in the site folder, then start again; this skill never installs), `port-conflict` (something this skill did not start holds the port: step 3), `failed-early-exit`, `timeout` (the instance stays running and ours; `status` says `starting`), `unknown-owner` (the evidence does not prove ownership; nothing was done), `insufficient-evidence` (`ps` or `lsof` unavailable or blind: nothing was started or signalled; the person must make the tool available), `unsafe-state`, `failed-after-start`, `failed`, and the `STOP:` messages (invalid manifest, unknown site). Do not retry blindly and never signal a process yourself.
2. **Who does what (binding).** Starting, reusing and stopping a server is done **only** by `control.py`. A browser tool of the host may open and look at the URL the controller returned (`running-*`) or confirmed (`inspect` -> `page-confirmed`). It must not start a dev server (no host preview/start tool for a site of this plugin) and must not change the port; a port change is never a workaround. An instance that `control.py` proves to be its own is reused no matter which application started it.
3. **Port taken by something that is not ours** (`port-conflict`, `next_step: inspect`): do not stop, adopt or replace it, do not change the manifest or port, do not start anything else. Run `inspect`. With `page-confirmed` open **that existing URL** and look there. Without confirmation, say it plainly in one sentence, finish all work that does not depend on the look, and do not loop.
4. Stop only when the person asks, with `control.py stop`.
5. **Inspect the served page** (separate from the process): it starts, signals and adopts nothing and never changes the manifest or port. Only `page-confirmed` is evidence, and only a pre-check from the served HTML; `page-other-site`, `page-stale`, `page-identity-only`, `page-identity-unknown` and `page-not-reachable` are never evidence. The result says separately whether the process is ours.
6. **Visual check.** Use the host's own authorised browser tool, if one is available, to open the address and read the page (and the console, if the tool offers it). Never conclude from a missing tool name on one host that another host cannot do it. If no browser tool was actually used in this run, do not claim a visual result: say the server runs and the look is not checked.

## Message to the person

Write in the person's language, short and plain; the JSON and all evidence stay internal.

- Success: `The preview of <title> is open: [View website](<url>).` only if a browser tool actually opened it; otherwise `The preview of <title> is running: [View website](<url>) (not looked at yet).` Mention the console only if it was read and say what it showed.
- `running-reused`: `The existing preview is being reused.`; `stopped`: confirm briefly; `not-running`: say that no preview is running.
- URLs are clickable Markdown links. No PID, start ID, process start time, internal states, exit codes, log paths or `matched_on` unless the person asks for a diagnosis.
- Failure: name the problem in one sentence and the next sensible step. Never claim "nothing was started" when a process may exist (`started` in the JSON tells).

## Rules

- `control.py start` writes the own entry `website-manager-<site>` into the project's `.claude/launch.json` from `templates/launch/<type>.json.tpl`; do not edit that file by hand. **`.claude/launch.json` is a Claude-desktop artifact** and not a Codex integration; its practical effect in the host is not verified.
- Ownership record and log live in the system temp area (`<TMPDIR>/website-manager/`), never in the repository or the plugin.
- Ports come from the manifest (`port`), otherwise 4321 plus the position in the manifest.
- Dev tests are not part of this skill; do not run any.
