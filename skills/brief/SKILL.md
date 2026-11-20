---
name: brief
description: Work out the content direction of a static website with the person: purpose, audience, offer and message, wanted visitor action, tone, website language, materials, design direction and colour palette. Saves the brief in the selected website project, supports several feedback rounds and asks for explicit confirmation before any design variants are made.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py")'
---

# brief (Website plugin)

> **Status (local development).** Works on the brief of an already set-up site only. Makes no design, writes no site file.

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

`references/brief.md`: the brief format, field statuses, how to ask, palette proposals, confirmation and what a change does to later results.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" status [--site <site>] [--root <project>]
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" brief-save    --site <site> --file <brief.json> [--root <project>]
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" brief-confirm --site <site> --statement "<the person's own words>" [--root <project>]
```

## Steps

1. Run `status`. If `setup.state` is not `complete`, stop and hand back to the entry (`plugin-website`).
2. Collect what is already known (the first request, an earlier brief revision in `.project/website/<site>/brief.json`). Never ask again for it.
3. Ask short, bundled questions with a concrete proposal for each open topic; at most four questions at a time. Mark each field `confirmed` (the person said or accepted it), `proposed` (your suggestion, not yet accepted) or `open`.
4. Propose two or three colour palettes with a one-sentence reason each (`palette_proposals`); the chosen palette goes into `fields.palette`.
5. Write the brief to a scratch file (not into the site) and `brief-save` it after every round. Show the person a short summary that separates confirmed, proposed and open items.
6. When all required fields are `confirmed`, ask the person to confirm the whole brief ("Shall I make design variants from this?"). Only their explicit yes counts; then `brief-confirm --statement` with their words. A later `brief-save` makes the confirmation obsolete and marks dependent design results stale (nothing is deleted).
