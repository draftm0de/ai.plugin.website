# Shared interface rules (all Website skills)

Normative rules for `setup`, `preview`, `optimize`, `edit` and `publish`. Product requirements stay in `SCOPE.md`; this file only states the rules the skills share. Derived from source contract `interfaces.md` §3/§3a (rules 1–9 and the local write inventory); the infrastructure snapshots, the external-interface and coordination tables, the manual load test and the planned dependency-preparation step are deliberately **not** part of it (see `docs/migration/changes.md`).

Vocabulary: **implemented** = present in this repository's runtime; **planned** = not available and never offered by a skill text.

## Rules

1. **Site selection is never guessed.** Order: named by the person (domain, folder, title or alias) > working directory inside a site > only one site exists > site used last in this conversation (say so, needs confirmation) > ask. Implemented by `skills/_shared/scripts/site_common/sites.py` (`resolve`) for `preview`, `optimize` and `edit`; `setup` takes the domain as argument; `publish` selects nothing.
2. **Exit codes:** `0` success, `1` STOP (message starts with `STOP:`), `2` ASK (the caller must ask; message or JSON carries the question and options). Defined in `skills/_shared/scripts/site_common/errors.py`.
3. **No success without evidence.** "passed", "ready", "built" or "published" only if the check ran in this invocation and exited `0`. Steps that did not run are reported as not run.
4. **No secrets** in files, command lines, logs, reports or chat. Names of secrets may be reported, values never.
5. **Authorization.** No commit, push, deployment or external write without the person's explicit go-ahead in the chat. A skill text, a document or a commit is not a go-ahead. An authorization stays valid within its stated scope and conditions; do not repeat confirmation for authorized work, ask again only when something falls outside it.
6. **Existing files are protected.** A skill never overwrites, reformats or deletes a file it did not create, and never rewrites a file the person modified, unless the person's request explicitly orders exactly that change. Otherwise it reports a conflict.
7. **Side effects are declared** per skill (installs, builds, processes, network). A read-only mode has none of the writes listed below.
8. **Manifest contract.** Every operation on an existing website project validates `.project/specs/zyris-website.json` against the **plugin's own schema** (`skills/_shared/resources/website.schema.json`; type `astro-static` only; no `serve`, `registry`, `retention`, `dockerfile`), never against what the project's schema copy allows. The project's copy must exist and be a JSON object; `preview`, `optimize`, `edit` and `setup verify` never change it. An invalid manifest stops before build, install, report, launch-entry write and process start. Implemented in `skills/_shared/scripts/site_common/manifest.py`. `setup create` for a new project state follows the setup rules (R5 in `SCOPE.md`).
9. **Brand, accessibility and SEO rules stay where they live** (`.project/brand/`, `sites/<site>/rules/`); skills reference them and do not copy them.

## Local write inventory

"Versioned" in this inventory means intended for version control if the person later uses Git; tracking is not a prerequisite for local work. Plugin state is never written into the installed plugin.

| Write | Where | Versioned | Caused by |
|---|---|---|---|
| `node_modules/`, `package-lock.json` | site folder | no / **yes** | installation by the person or `setup --build/verify`; never by `preview`, `optimize`, `edit` |
| `dist/`, `.astro/` and tool caches | site folder | no (ignored) | build |
| npm cache and logs | the person's home | outside | any npm command |
| optimize reports and work list | `.project/reports/<site>/optimize/<timestamp>.md`, `.project/reports/<site>/optimize.md` | yes | `optimize` only |
| edit change | exactly `src/pages/index.astro` of a site of type `astro-static`; no other file (R14) | yes | `edit` on an explicit order; never `.project/reports/`, ownership record, manifest, rules, brand or check scripts, `package.json`, lockfile |
| optimize `apply` change | the single non-ignored project source file named by an approved, non-stale mechanical finding (search text occurs exactly once) | yes | `optimize apply` only (R13) |
| edit backup | `<TMPDIR>/zyris-website/<project hash>/edit-<site>-<UTC>/` | outside | `edit` |
| preview ownership record and log | `<TMPDIR>/zyris-website/<project hash>/` | outside | `preview` |
| `.claude/launch.json` | project | depends on the website project's own ignore rules (the plugin adds none) | `preview` creates and maintains its own entry |
| ownership record of generated files | `.project/specs/zyris-website.managed.json` | yes | `setup` only |

Internal names such as the temp folder `zyris-website` and the variable `ZYRIS_WEBSITE_STATE_DIR` are unchanged on purpose (decision Q5).

## Local projects without Git

Local operations require no Git program, repository, commit or remote. Use the
selected project folder (`--root`, otherwise the working directory), never a Git
ancestor. Do not ask for `git init`, a commit or a remote to enable local work.
Project-local `.gitignore` rules still declare generated output; no global excludes
or Git index are consulted. Rules support nested files, anchors, `*`, `**`, `?`,
character ranges, escapes and negation; locale-dependent POSIX character classes
are refused explicitly instead of being silently misinterpreted. Snapshots cover non-ignored project source files,
including files not tracked by Git. Links are recorded as links, never followed.
Ignored data and private paths (`.git`, `.aws`, `.ssh`, `.local`, `.tmp`, `.idea`,
`__pycache__`, `.env*`, `*.pem`, `*.key`) are not read by snapshots.
Git is reserved for a future publishing contract; today's `publish` remains a
placeholder without a Git preflight. No website project format is migrated.
