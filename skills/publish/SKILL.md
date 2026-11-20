---
name: publish
description: Explains that publishing a website is not available. This skill never starts a release and never reports publishing as possible, prepared or done.
---

# publish (Website plugin)

> **Status (local development): publishing is not available.** There is no script, remote query, preflight or workflow file behind this skill. What is missing: a central reusable workflow, a server-side deployment protocol and the workflow call that each site would need. Only the shared operator-language gate needs the selected project and its preference helper. The publishing placeholder needs no website manifest or publishing runtime.

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

## What this skill does

1. Say plainly that publishing is **not available**. Never say a publication is possible, prepared or done.
2. Say in general terms what is missing (above).
3. For a local quality check of a site point to the `optimize` skill (build, SEO and accessibility audit). That is not a publishing check and says nothing about whether a site could be published.

## What it must not do

- Do not deploy, push, commit, trigger a workflow or query a remote or the network.
- Except for the shared operator-language gate, do not run any script, check for any file or read the website project or its manifest.
- Do not invent workflow names, SHAs, hosts, secrets or variables.
- Do not create a workflow file or any other file except the explicitly selected operator preference.
