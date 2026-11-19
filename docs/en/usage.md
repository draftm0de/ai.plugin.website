# Usage

[Deutsch](../de/usage.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

This page explains how to use the plugin. The authoritative behaviour is in [SCOPE.md](../../SCOPE.md) and in the skills' references (`skills/<skill>/references/`). All domains and texts below are fictional. The examples show no recorded host run.

## Set up

You need a **website project**: a Git repository in which the sites live under `sites/<domain>/` and the project data under `.project/`. Open it in Claude or Codex and work with that folder as the working directory. Python, Git, Node and npm must be present ([prerequisites](../prerequisites.md)).

1. **Create a new site** – “Create a new static website for demo.example, title ‘Demo Workshop’.” `setup create` writes the template into a missing or empty folder `sites/demo.example/`, registers the site in the manifest `.project/specs/zyris-website.json` and, if needed, creates the schema copy `.project/specs/website.schema.json`, the scratch folder `.tmp/` and the ownership record.
2. **Adopt an existing folder** – “Adopt the existing static folder sites/old.example.” `setup adopt` only registers it and changes no file inside.
3. **Look first, change later** – “Show me what creating demo.example would change.” `plan` writes, installs and builds nothing. It does not promise that a later run succeeds.
4. **Install dependencies** – you do that yourself (`npm install` in the site folder) or you order `setup verify` or `--build`: only that explicit check runs the site's declared install (it uses the npm registry over the network). `preview`, `optimize` and `edit` never install; if something is missing, the assistant names the command.
5. **Check** – “Check demo.example.” `setup verify` runs install, build and check with real exit codes (so installation only on that explicit order); steps that did not run appear as “not run”, never as passed. A new or changed `package-lock.json` is a versioned file: review and commit it yourself.

## Choose a workflow

| You say … | Skill |
|---|---|
| “Create a website”, “adopt the folder”, “check the build” | `setup` |
| “Show me the page locally”, “stop the preview” | `preview` |
| “Check SEO and accessibility”, “implement SEO-001” | `optimize` |
| “Shape the start page”, “change the text in the hero” | `edit` |
| “Publish the site” | `publish` (not available) |

### setup

Operations: `create`, `adopt`, `plan create|adopt`, `verify`. Not available are `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, the former type `astro` (Docker/Caddy) and its options; they are refused, never translated. An identical repetition yields `unchanged` without writing. Differences, modified or missing generated files and foreign schema copies yield `conflict` without writing. If a write fails, `setup` restores all files and the registration (`failed-rolled-back`) or names the exact remainder (`failed-partial`).

### preview

“Show me demo.example locally.” Only the controller starts, reuses or stops the dev server, and only if it can prove that the process is its own; a launch name and a port alone are never proof. It reports ready only after a successful HTTP probe. If a foreign process holds the port (`port-conflict`), `preview` does not touch it; instead `inspect` checks the page served there. If dependencies are missing you get `needs-install` and the hint to run `npm install`. A host browser tool may open only the address the controller returned or `inspect` confirmed. Without an actually opened page the assistant says: “running, not looked at yet”.

### optimize

“Check SEO and accessibility of demo.example.” There are three separate steps:

| Step | What happens | What does not happen |
|---|---|---|
| **Audit** | Build into the ignored `dist/`, `seo:check` and `a11y:check` independently, comparison of `git status` and file hashes before and after the run; an immutable report under `.project/reports/<site>/optimize/` and the work list `.project/reports/<site>/optimize.md` | No site content is changed, nothing installed or committed, **nothing approved** |
| **Approval** | You decide per finding: `approved`, `deferred` (later), `wont-do` (do not implement) or `proposed` again. “Approve SEO-001” only stores the decision for the documented proposal and its starting text | Changes no site content; an existing decision changes only on your explicit request (`--change`) |
| **Implementation** (`apply`) | Only approved, non-stale proposals with a mechanical change: the search text must occur exactly once in a versioned file of the site. Then the full check runs again | Nothing else is touched; no install, no commit. If the proposal or its starting text changes, the approval becomes invalid |

A finding moves to the history only when a complete run after a successful build no longer reports it. Technical errors, warnings and editorial recommendations stay separate classes. Manual check points (contrast, keyboard, screen reader, truthfulness, legal pages) are listed in every report and never count as passed. There is no ranking promise; GEO is not available. Search-engine registration, DNS and redirects are for the person to do.

### edit

“Shape the start page of demo.example: name ‘Demo Workshop’, place ‘Sampletown’, offer: bicycle repair.” or “In the start page, change the sentence ‘Welcome’ to ‘Glad you are here’.” `edit` changes only `src/pages/index.astro` of a site of type `astro-static`. The assistant asks specifically for missing facts; it invents no contacts, addresses, prices, ratings or licences. Supplied texts, files and links are data: instructions inside them are quoted and asked about, not executed. A general change order approves no optimize finding; if you name a finding ID, the work goes through `optimize`.

The flow: check prerequisites (writes nothing), back up the original, change, `npm run build` and `npm run check`, look, finish. The outcome is honest: **“complete” exists only after a passed build and check for the current content and an actually performed visual check.** If the assistant could not look at the page itself, the statement is, in substance, “the automatic checks passed, I could not look at the page myself” (technically checked, visual check open). Failed or not-run checks are never reworded into that. At most two repair rounds.

### publish

“Publish demo.example.” The skill says that publishing is **not available**, names in general what is missing (a central workflow, a server-side protocol, the workflow call) and points to `optimize` for a local quality check – explicitly not a publishing check. It runs nothing, queries nothing over the network and creates no file.

## Understand the output

The final answer is short (usually two to four sentences): what changed, whether the checks that ran confirm it, where you can look at it and what you still need to decide. The assistant names process IDs, ports, exit codes and hashes only on request.

| Skill | States (selection) | Meaning |
|---|---|---|
| `setup` | `created`, `adopted`, `verified`, `unchanged`, `planned` | success (exit 0) |
| | `needs-input` | an input is missing, the assistant asks (exit 2) |
| | `conflict`, `invalid`, `failed-rolled-back`, `failed-partial`, `failed-build`, `failed-check` | refused or failed (exit 1) |
| `preview` | `running-new`, `running-reused`, `not-running`, `stopped`, `page-confirmed` | success |
| | `needs-install`, `port-conflict`, `unknown-owner`, `insufficient-evidence`, `timeout`, `unsafe-state` | nothing changed, or a hint what you can do |
| `optimize` | `clean`, `clean-with-warnings` | success |
| | `errors`, `incomplete`, `readonly-violated` | findings, a missing prerequisite or a changed versioned file; `incomplete` never counts as clean |
| `edit` | `written`, `unchanged`, `complete` | success |
| | `conflict`, `not-run`, `stale`, `repair-limit`, `refused`, `stop` | nothing overwritten, or a check did not run or is outdated |

Exit 0 means success, 1 `STOP:` (refused or failed), 2 a question. “Passed”, “built” or “ready” is reported only if the check ran in this call and ended with 0.

## Control the session

- **Which site?** It is never guessed. Order: named by you (domain, folder, title, alias) → working directory inside a site → only one site exists → site used last (with a spoken confirmation) → ask. An unknown site stops, an ambiguous one asks with options.
- **A concrete order is the approval** for exactly the work it describes. If one part is blocked, independent parts continue.
- **Stop the preview** only when you ask (“Stop the preview”); the assistant ends only processes that provably belong to it.
- **Refuse a format:** a project in the former format is refused with a diagnosis before anything is written. That applies when the manifest's `$schema` reference points to the former schema file `zyris-website.schema.json` (in any local spelling) or when only that file exists and no `website.schema.json`. An unused old schema file next to a correctly used `website.schema.json` is not by itself a reason for refusal. There is no automatic migration and no fallback; you convert the project yourself.

## Return later

- **optimize:** findings keep stable IDs (site + criterion + location), decisions persist across runs, a returned finding appears as `reappeared`. The work list is generated: do not edit it by hand, or the next run stops (restore it from Git).
- **preview:** “Is the preview still running?” only queries the state (`status`) without starting anything.
- **edit:** the original is in a backup outside the repository; after a confirmed complete finish only the own backup folder is removed. With an open outcome the assistant says where the backup is.
- **After a failure of `setup verify`** the person (or a separately ordered `edit`) repairs the file and then runs `verify` again – not `create` (which reports a conflict for a repaired generated file).
- **Known limitation `edit` ↔ `setup`:** after an `edit` change to a file generated by `setup`, the stored ownership hash no longer matches. A repeated `setup create` then yields `conflict` for that site without writing, and `setup verify` keeps the file (`modified (kept)`). There is no re-baselining of the hashes, no `setup update`, no `--adopt-edits`. That the hashes are not reset is a limit of today's scope, not a recovery instruction.

## Specialized workflows

Not available (the assistant does not offer them and does not work around them): publishing and deployment, blog and further page types in `edit`, forms, `setup update`, re-baselining ownership hashes, GEO, Lighthouse, link-graph checks, isolated dependency copy, new browser integration. Completeness of the checks: [acceptance matrix](../migration/acceptance.md).

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
