---
name: plugin-website
description: Guided start for a static website: inspect the project state without changing anything, say what is missing, and lead through setup, briefing, design variants, approval and implementation of the start page. Use when the person wants a website made or asks where a website project stands, for example "plugin-website" or "create a website for demo-a.com for a physiotherapist in Vienna". Publishing is not available.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py")'
---

# plugin-website (Website plugin)

> **Status (local development).** This is the central entry. It decides nothing about the content and starts no step by itself that the order does not cover. **Not available (do not offer, do not work around):** further pages, blog, forms, publishing/deployment. Whether a host starts this skill from a plain word or sentence depends on the host and is not proven here; the explicit invocation by skill name is the reliable way (see `references/entry.md`).

> **Script location (binding).** The shared helper is `../_shared/scripts/flow.py` next to the **actually loaded** `SKILL.md` (one level up, folder `_shared/scripts`). Run it with the **website project** as working directory or `--root`. State lives only in that project (`.project/website/<site-id>/`); the plugin folder is read-only.
>
> - **Claude:** the host replaces `${CLAUDE_SKILL_DIR}` with the folder of this `SKILL.md`; use it in double quotes.
> - **Codex:** use the path of the loaded `SKILL.md` that the host gave you and form the absolute path `<folder of that SKILL.md>/../_shared/scripts/flow.py`. Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable.
> - **No path, no run:** if the path of the loaded `SKILL.md` is not available, stop and say so. Do not search caches or plugin folders, never copy scripts into the website project.
> - **Form of the call:** `python3 -B` with the script path as **one** quoted argument, no `PYTHONPATH`. Check first that the script exists (`test -f "<script path>"`).

## Operator language (first)

Before any question or action, read and follow `../_shared/references/operator-language.md`. Its persisted project preference governs the language of everything you say to the person. Missing preference: ask the language question alone, wait, and persist the explicit answer before continuing. The language of the **website** is a different setting (brief field `site_language`) and is never derived from the operator language.

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

1. `references/entry.md`: the exact order of the guided flow, the state values, how information from the first request is carried over, what each state means, and what the entry may and may not do.
2. `../_shared/references/interfaces.md`: rules shared by all Website skills.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" status [--site <site>] [--root <project>]
```

`status` writes nothing. Run it first, on every call, also for a bare "status" request. Never treat an existing, unknown or contradictory project as an empty one: only `setup.state` = `missing` means "nothing there yet".

## Steps

1. Operator language (above). Then determine the **explicitly selected** website project (the working directory or the folder the person named) and, if there are several sites, which one (ask once).
2. Run `status`. Read `setup.state`, `brief.state`, `design.state`, `implementation.state`, `checks`, `stale`, `problems` and `next_step`.
3. Say in one or two sentences where the project stands and which step comes next. Then do that step yourself, following the skill named by `next_step`:
   - `setup` -> the `setup` skill (site ID from the order; `--domain` only if the person stated a real domain);
   - `resolve-setup` -> report the concrete `problems`; change nothing; offer the one next action;
   - `brief` -> the `brief` skill; `design`, `design-choose`, `design-revise` -> the `design` skill;
   - `implement` -> follow `references/entry.md` section "Implementing the approved design" (uses the `edit` skill and its protections);
   - `checks` -> run/record the checks as described there; `done` -> report what was finished and what is open;
   - `resolve-implementation-conflict`, `resolve-user-change`, `report-damaged-state` -> report plainly, change nothing, ask for the one decision.
4. Carry over what the first request already said (site name or domain, business type, place, language). Do not ask for it again. A domain stated by the person goes to `setup --domain`; if none was stated, none is invented.
5. After each answer or completed step run `status` again and continue at the next step. A repeated call continues where the state says; it never recreates a project, forgets a decision or repeats a finished step.
6. Ask only for information or a decision that is really missing (one short question, with a concrete suggestion).
