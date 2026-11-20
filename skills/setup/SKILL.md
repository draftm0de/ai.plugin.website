---
name: setup
description: Create a new static Astro website folder (sites folder per domain), register an existing static folder, show what a setup run would change, or re-run install/build/check of a registered site. Updating existing sites is not implemented yet.
allowed-tools:
  - 'Bash(python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" *)'
  - 'Bash(test -f "${CLAUDE_SKILL_DIR}/scripts/site_setup.py")'
---

# setup (Website plugin)

> **Status (local development).** Implemented: `create` (type `astro-static`), `adopt`, `plan create|adopt`, `verify`, with ownership hashes, rollback and real install/build/check exit codes. **Not available (do not offer, do not work around):** `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` without naming the operation, workflow-call generation, deployment, publishing. `astro-static` is the only supported site type: the Docker/Caddy type `astro` and its options (`--serve`, `--network`, `--host`, `--email`, `--legacy-docker`) are refused, never translated.

> **Script location (binding).** The script is `scripts/site_setup.py` next to the **actually loaded** `SKILL.md`. Run it with the **website project** as working directory (or `--root`). Site configuration (`.project/`, `sites/`) always comes from that project; the skill's templates and the shared schema stay inside the plugin and are never written to.
>
> - **Claude:** the host replaces `${CLAUDE_SKILL_DIR}` with the folder of this `SKILL.md`; the commands below use it in double quotes.
> - **Codex:** use the path of the loaded `SKILL.md` that the host gave you and form the absolute script path `<folder of that SKILL.md>/scripts/site_setup.py`. Do **not** run `${CLAUDE_SKILL_DIR}` as a shell variable; do not rely on a Claude placeholder.
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

1. `references/setup.md`: the full behaviour of the commands (states, exit codes, manifest fields, port rule, schema copy, ownership record). Report only what it and the command output say.
2. `../_shared/references/interfaces.md`: rules shared by all Website skills (exit codes, evidence, secrets, protected files, write inventory).

If one of these files cannot be read, say so and do not reconstruct its content from memory or search other folders; the command output stays authoritative for the result.

## Call

```
python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" create <site-id> --type astro-static [--domain D] [--path sites] [--title T] [--alias A]... [--port N] [--environment E] [--root R] [--json] [--build]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" adopt <site-id> [same options]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" plan create|adopt <site-id> [same options]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" set-domain <site-id> <domain> [--plan] [--root R] [--json]
python3 -B "${CLAUDE_SKILL_DIR}/scripts/site_setup.py" verify <site-id> [--root R] [--json]
```

Existence check before the first call: `test -f "${CLAUDE_SKILL_DIR}/scripts/site_setup.py"` (Codex: the same check with the absolute script path).

## Site ID and domain (manifest version 2)

The positional argument is the **site ID**: a short internal lowercase name (letters, digits, `-`, `.`), also the folder name; it need not be a domain. Pass `--domain` **only** when the person stated a real domain; never invent or guess one, never use a placeholder domain and never derive it from the site ID. Without a domain the site is built for local work with no public addresses. A domain decided later: `set-domain <site-id> <domain>` (`--plan` first if unsure); it keeps ID, folder, port and assignments and refuses (conflict, nothing written) when a generated address file was modified. Only manifest version 2 is accepted. A contradiction between the manifest `domain` and the site configuration stops the run and is reported, never repaired.

## Steps

1. Name the operation and the site. If the person is unsure what would change, run `plan create|adopt <domain> ...` first: it writes, installs and builds nothing and lists the operation, changes, findings and conflicts (it does not promise that a later write or build succeeds).
2. Run the real command. Exit codes: `0` ok (`created`, `adopted`, `verified`, `unchanged`, `planned`), `2` input missing (`needs-input`: ask exactly that question, then run again), `1` refused or failed (show the message; states `conflict`, `invalid`, `failed-rolled-back`, `failed-partial`, `failed-build`, `failed-check`). Never work around a refusal.
3. Report the state and, with `--build`, the three real exit codes (install, build, check; `not run` means not run, never passed). A new or changed `package-lock.json` is a versioned file: tell the person to review it; no commit required for local work.
4. After `failed-build`/`failed-check` the files and the registration stay. The person (or a separately ordered edit) repairs the file; then run `verify <domain>`. Do **not** repeat `create` (it reports a conflict for a repaired generated file) and never regenerate or revert a repaired file. `verify` keeps modified generated files (`modified (kept)`).
5. Do not commit or push; that needs the owner's go-ahead.

## What the commands do

- **create**: needs an absent or empty `sites/<domain>/`; writes the static template (no Dockerfile, compose, Caddy or workflow file), registers the component, writes the project's schema copy when absent, `.tmp/` with its `.gitignore` entry and the ownership record `.project/specs/website.managed.json` (hashes of the written files). No Git program, repository, commit or remote needed. The selected project folder is the root; never require or suggest `git init` for local work. Everything is written through temporary names; a failure before the build restores every file and the registration (`failed-rolled-back`, or `failed-partial` with the exact remainder).
- **manifest of a new site** (`.project/specs/website.json`, created when absent, otherwise only extended by the new entry; existing entries are never rewritten): `$schema` `./website.schema.json`, `version` 1, and one component with `name` = the domain, `path` = `<sites folder>/<domain>` (`--path` names the sites folder, default `sites`; it is not the site path itself), `type` `astro-static`, `title` = `--title` or the domain, `aliases` = the given `--alias` values or `[]`, `port` = `--port` or automatic, `environment` only when given. Automatic port: 4321 in an empty project, otherwise the highest effective port in use plus one (a site without explicit port counts with its derived port, 4321 + position); a collision is refused and an automatic port that would leave 1024-65535 stops with the request to pass `--port`.
- **adopt**: registers an existing static folder and changes no file inside it. Blocking findings stop before any change (no/invalid `package.json`, no `build` script, build output not git-ignored, folder missing or behind a symlink); warnings are listed and not repaired (no lockfile, no `check` script, missing rules/audit scripts, adapter/server output, Docker/Caddy files of an old architecture that are kept as they are and not carried over). With `--build` the declared install/build/check run.
- **identical repetition** (same effective options, unmodified generated files): `unchanged`, nothing written. Differences on a registered domain or a modified/missing generated file are a `conflict`; `update` is not available.
- **verify**: install, build and check of a registered static site's current content; regenerates and overwrites no site source file; its npm side effects are `node_modules/`, `dist/`, `.astro/` and possibly `package-lock.json`.
- **Schema copy** `.project/specs/website.schema.json`: created when absent, kept when equal to the plugin schema, replaced only when setup recorded it and nobody modified it. Every other existing copy (foreign, older without a record, modified) is a `conflict` with the hash comparison; nothing is overwritten as a shortcut. A manifest that still holds the removed type `astro` (or the removed `serve`, `registry`, `retention` fields) is invalid.
## What a new static site contains

The quality block of the reference template: binding rules (`rules/accessibility.md`, `rules/seo.md`), audit scripts (`scripts/seo-check.mjs`, `scripts/a11y-check.mjs`, run by `npm run check`), the CSS foundation with `STYLEGUIDE.md`, `theme.css`, `site.css`, a generic `BaseLayout`, sitemap, `robots.txt`, a 404 page, favicon and a placeholder share image (`public/assets/og-default.png`, replace it). The static type has no serving files.

## Scratch folder

`.tmp/` in the repository root is created by `setup` and git-ignored on demand; it is the project's scratch folder and is never committed. It does not hold the process state of `preview` or the backups of `edit`: those live outside the website repository (see `references/setup.md`).

## Rules

- Scripts contain logic only; all file content lives in the skill's `templates/` folder. The only type in `templates/types.json` is `astro-static` (one complete template folder `templates/astro-static/`).
- Do not create or edit generated files by hand to get around a refusal. Do not add form functions.
