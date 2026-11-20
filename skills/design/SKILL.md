---
name: design
description: Make at least two clearly different start page prototypes from a confirmed website brief, compare them locally, take feedback, revise or combine them, and record the explicit approval of one concrete revision and layout. Prototypes are stored outside the website and never replace the existing start page.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py")'
---

# design (Website plugin)

> **Status (local development).** Prototypes only. This skill never writes into `sites/<id>/`; implementing the approved design is a separate step (see `plugin-website`, `references/entry.md`).

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

`references/design.md`: prototype rules, what counts as a different direction, open facts, the feedback loop, approval wording and staleness.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" status | design-new | design-register --revision <n> | design-feedback --text "<...>"
python3 -B "${CLAUDE_SKILL_DIR}/../_shared/scripts/flow.py" design-approve --revision <n> --variant <V> --statement "<the person's own words>"
```
(always with `--site <site>`; `--root <project>` when the working directory is not the project)

## Steps

1. `status`. Proceed only with `brief.state` = `confirmed`; otherwise hand back to the entry.
2. `design-new` (creates or resumes the next revision folder and returns its path, the website language and the palette). Write `A.html`, `B.html`, ... into that folder (see the reference). Then `design-register --revision <n>`; fix what it reports and register again.
3. Show the comparison page (`design/rNNN/index.html`, see the reference for opening it) and ask which direction the person prefers and what to change.
4. Record the person's feedback with `design-feedback`. A preference such as "B is nicer" is feedback, not an approval. Make the next revision (`design-new`, new files, `design-register`) and show it again. Repeat.
5. When the person approves one concrete layout of the **shown revision** ("Yes, revision 2, variant B, build it"), `design-approve --revision --variant --statement` with their words. Name revision and variant in your question so the answer can refer to them.
6. After the approval the guided flow implements the approved page without asking the same question again.
