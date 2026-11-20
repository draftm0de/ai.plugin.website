# setup: behaviour reference (Website plugin)

Normative description of the implemented `setup` skill. Product scope and acceptance live in the repository's `SCOPE.md` (R5, R8, R9, R21); this file describes what the script does so that the skill can report it correctly. Shared vocabulary and rules: `../../_shared/references/interfaces.md`. Nothing here describes planned functions.

## 1. Purpose and scope

Create, take over and check static Astro websites in `<sites folder>/<site-id>/` of a website project, and show what a change would do before it is written.

- One supported site type: `astro-static`. Other types and the former Docker/Caddy options are refused, never translated. A manifest that still holds them is invalid; setup does not migrate it.
- Typical requests: create a new site, take over an existing folder, show what setup would change, re-run install, build and check of a registered site.
- Out of scope: form sending, writing content (that is the `edit` skill), design, publishing, server work.

## 2. Commands and exit codes

```
site_setup.py create <site-id> --type astro-static [--domain D] [--path P] [--title T] [--alias A]... [--port N] [--environment E] [--root R] [--json] [--build]
site_setup.py adopt  <site-id> [--type astro-static] [--domain D] [same options]
site_setup.py plan create|adopt <site-id> [same options]      # writes, installs and builds nothing
site_setup.py set-domain <site-id> <domain> [--plan] [--root R] [--json]   # later domain assignment (manifest + two generated address files)
site_setup.py verify <site-id> [--root R] [--json]            # install, build, check of the registered site's current content
```

- `--path P` is the **sites folder** (relative to the repository root, default `sites`); the site folder is `<P>/<domain>`. `--root` selects the project folder (default: working directory). No Git program, repository, commit or remote is required; never suggest `git init` as a setup prerequisite.
- Defaults live in `templates/types.json`. `environment` is written only if given.
- Exit `0`: `created`, `adopted`, `verified`, `unchanged`, `planned`. Exit `2`: `needs-input` (site ID or `--type` missing). Exit `1`: everything else (`conflict`, `invalid`, `failed-rolled-back`, `failed-partial`, `failed-build`, `failed-check`, commands that are not available).
- Answered with `STOP:` and exit 1: `update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` without `create|adopt`. Any other unknown option (including `--serve`, `--network`, `--host`, `--email`, `--legacy-docker`) is an argument error (exit 2) and writes nothing. The type `astro` is `invalid`: "Unsupported type 'astro'. Supported: astro-static."
- `--json` prints `{state, operation, site, changes[{path, action, reason}], findings[{level, text}], notes, verification{install,build,check: {command?, ran, exit}}, exit}` plus, when present, `problems`, `error`, `remaining`, `rollback_errors`, `failed_step`, `output_tail` (last 40 lines), `local_output`, `lockfile` (`created|changed|unchanged|absent`).
- States: `created`/`adopted` only when the writes are complete and verified and, with `--build`, build and check exited 0. `verified` only when install, build and check all ran with exit 0. `unchanged`: identical repetition. `planned`: pre-write validation passed (says nothing about a later write or build). Steps that ran keep their real exit code; steps that did not run have `ran:false, exit:null` and are never reported as passed.

## 3. Behaviour

- **One planner.** Validates inputs, paths (relative, no `..`, no absolute path, no symlink along the site path, `.project/specs`, `.gitignore`, `.tmp`), the manifest and ownership record, the resulting manifest (plugin schema, semantic rules, name/alias/port collisions as `conflict`), template placeholders and file conflicts. `plan` prints that result; `create`/`adopt` apply exactly that plan. No `origin` remote is needed.
- **create**: the target folder must be absent or empty (otherwise `conflict`; use `adopt`). Output: the one complete template (pages, layout, foundation CSS, `STYLEGUIDE.md`, rules `accessibility.md` and `seo.md`, audit scripts, `CLAUDE.md`). No Docker, Caddy, compose or workflow file.
- **adopt**: registers an existing static folder and writes no file below the site folder (a tree hash before and after; a difference rolls the run back). Blocking findings (state `invalid`, nothing written): missing or invalid `package.json`, no `build` script, build output paths not git-ignored, folder missing or behind a symlink. Warnings (reported, never repaired): no lockfile, no `check` script, missing `rules/accessibility.md`, `rules/seo.md` or audit scripts, adapter/server output in the Astro config (heuristic), Docker/Caddy files of an old architecture (foreign, kept, not carried over). With `--build` the declared install/build/check run.
- **Identical repetition** (same effective options, recorded mode equals the operation, every recorded file exists with its recorded hash, project schema copy equals the plugin schema, preconditions re-checked): `unchanged`, exit 0, no write. Any difference on a registered site (including a different or newly stated `--domain`), a modified or missing generated file, a site without ownership record, or `create` on an adopted site is a `conflict` (nothing written). The message names `setup verify` as the way to re-run checks and says that `update`/`--regenerate` are not available.
- **Write order and rollback.** Files are staged in exclusively created temporary files next to their targets, then renamed; an existing file or symlink with a similar name is never opened, overwritten or removed. Order: site files, `.tmp/` and `.gitignore`, schema copy, ownership record, manifest last. A failing write, rename or post-write verification restores every file of this run (including the registration) and reports `failed-rolled-back`; if the revert itself fails, `failed-partial` lists the remaining paths. No build runs after such a failure.
- **Build** (`--build`): `npm install`, `npm run build`, `npm run check` in that order with real exit codes; a build that exits 0 without `dist/` is `failed-build`. After a failure the files and the registration stay (`failed-build`/`failed-check`, output tail, local build output, and a new or changed `package-lock.json` named as a versioned file to review; no commit required for local work). Restart after a repaired file with `verify`, not a repeated `create`.
- **verify**: the site must be registered, its folder and `package.json` must exist; the manifest is validated against the plugin schema and the project's schema copy must exist and be valid JSON. Runs the three steps on the current content. Files whose hash differs from the record are listed `modified (kept)`, missing ones `missing (kept)`; nothing is regenerated and the ownership record is not touched.
- **Reads and writes.** `plan` writes nothing. `create` writes `<sites folder>/<site-id>/**`, the manifest (and the schema copy when absent), `.gitignore` (adds `.tmp/`), `.tmp/`, the ownership record. `adopt` writes the manifest entry, the schema copy when absent or replaceable, `.gitignore`/`.tmp/` and the record, no site file. `verify` and `--build` write `node_modules/`, `dist/`, `.astro/` (git-ignored) and possibly `package-lock.json` (versioned, reported); they use the npm registry (network). Never: `git add`, commit, push, remote or server access, global installs, `docker`, changes outside the repository. No option accepts a secret.
- **Authorization.** A named operation on a named site is the authorization for exactly that operation, its listed writes and `--build` if requested. A new yes is needed for a write outside `<sites folder>/<site-id>/`, `.project/specs/`, `.gitignore`, `.tmp/`, for removing a registered site, or for a commit/push (never done by setup).
- **Scratch folder.** `.tmp/` in the repository root is created by setup and git-ignored; it is never committed. It is the project's scratch folder only: the process state of `preview` and the backups of `edit` are kept outside the website repository (see `../../_shared/references/interfaces.md`, local write inventory).

## 4. Manifest and schema

- **Plugin schema** (binding): `skills/_shared/resources/website.schema.json`, found through the shared runtime inside the plugin. Every manifest is validated against it (type `astro-static` only; no `serve`, `registry`, `retention`, `dockerfile`), never against a looser project copy.
- **Project schema copy** `.project/specs/website.schema.json`: created when absent; kept when equal to the plugin schema; replaced only when setup recorded it and nobody modified it. Every other existing copy (foreign, older without a record, modified, not valid JSON) is a `conflict` with the hash comparison; there is no list of accepted earlier schemas.
- **Manifest** `.project/specs/website.json` (name unchanged): created when absent, otherwise only extended by the new component; existing entries are never edited (the file is re-serialized with 2-space JSON when a component is appended). A new manifest holds `$schema` `./website.schema.json`, `version` 1 and the component list.
- **Component of a new site (manifest version 2):** `name` = the site ID; `domain` = `--domain` only when given (absent = not decided; never derived, no placeholder domain); `path` = `<sites folder>/<site-id>` (`<sites folder>` is `--path`, default `sites`); `type` `astro-static`; `title` = `--title`, else the domain; `aliases` = the `--alias` values, else `[]`; `port` = `--port`, else automatic; `environment` only when `--environment` is given. Unknown facts are never invented.
- **Port.** An explicit `--port` must be 1024-65535 and must not equal any effective port in the manifest. Automatic: 4321 in an empty project, otherwise the highest effective port plus one. The effective port of a component is its explicit `port`, otherwise 4321 plus its position in the list (the rule of the shared site resolver). Existing entries are not rewritten. If the automatic port would exceed 65535, setup stops and asks for `--port`.
- **Former project format** (refused before any write or install/build, never migrated, no fallback): a manifest whose `$schema` is a local spelling of the former schema file `zyris-website.schema.json` in the same folder (for example `./zyris-website.schema.json` or without `./`), or a project that has that old file and no `.project/specs/website.schema.json`. Remote references are not fetched or interpreted. The old file is never read, changed, renamed or deleted; a leftover old file next to a correctly used `website.schema.json` is ignored. The person converts such a project themselves or keeps the old tooling.

## 5. Ownership record

File `.project/specs/website.manage.json` (name unchanged; sorted keys, 2 spaces, final newline; written in the same transaction as the files it describes; never changed by `verify`):

```
{"version": 1,
 "project_files": {"<repo-relative path>": {"sha256": "...", "template_version": "..."}},
 "sites": {"<site-id>": {"mode": "created|adopted", "type": "astro-static", "template_version": "...",
                        "files": {"<path relative to the site>": "<sha256>"}}}}
```

A file is generator-managed only if it is listed; a file without an entry is foreign even if it looks like the template. An invalid record stops every operation and is not overwritten. Pages, posts, data, brand and rule files and any file setup did not create are never overwritten. A file changed later by the `edit` skill stays changed; its recorded hash goes stale, so a repeated `create` reports `conflict` and `verify` keeps the file (`modified (kept)`). A rule for re-baselining is not defined.

## 6. Not implemented (do not offer)

`update`, `--add-missing`, `--regenerate`, `--adopt-edits`, `plan` without an operation, generation of a publish workflow call, deployment, detection of interrupted runs. They are refused and never emulated.

## Manifest version 2, domain, consistency (binding)

- `version` is 2; version 1 is refused with a diagnosis before any write (no migration, no fallback from `domain` to `name`, nothing read from `site.ts` or `astro.config.mjs`).
- With a domain the generated `astro.config.mjs` has `site: 'https://<domain>'` and `src/lib/site.ts` has `SITE` set to the same address; without a domain there is no `site` entry, `SITE = null`, the layout omits canonical/og:url/og:image/twitter:image, `sitemap.xml` is empty, `robots.txt` has no sitemap line and the SEO check skips (and reports) the address checks.
- `create|adopt` plan the resulting state first: a contradiction between the requested domain and the configuration (rendered templates, or the existing folder for `adopt`) is reported as `invalid` before any file is written. `verify` stops on a contradiction before install/build. Values the text-only reader cannot judge (variables, template literals, spreads, symlinks, missing files) are reported as "not reliably checkable", never as "no domain".
- `set-domain <site-id> <domain>`: needs a registered site created by setup without a domain, unmodified `astro.config.mjs` and `src/lib/site.ts` (recorded hashes), and a domain nobody else uses. It rewrites exactly those two files, their two hashes in the ownership record and the manifest entry (`domain` added after `name`); all writes are rolled back on failure. A decided domain is not changed here.
