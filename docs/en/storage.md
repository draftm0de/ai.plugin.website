# Storage and recovery

[Deutsch](../de/storage.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

This page describes where data lives and which protection limits apply. The binding rules are in [SCOPE.md](../../SCOPE.md) (R5, R7, R15, R21) and in `skills/_shared/references/interfaces.md`.

## Storage model

There are three separate places. **Nothing is stored in the installed plugin**; the scripts run with `python3 -B` and write neither state nor bytecode there.

| Place | Content | Written by |
|---|---|---|
| **Website project** (your Git repository) | sites under `sites/<site-id>/`; guided-flow state under `.project/website/<site-id>/` (flow record, brief, design revisions with prototypes: never part of the website); manifest `.project/specs/website.json`; schema copy `.project/specs/website.schema.json`; ownership record `.project/specs/website.manage.json`; reports and work list under `.project/reports/<site>/`; launch entry `zyris-<site>` in `.claude/launch.json`; scratch folder `.tmp/` | only the skill named for it (see below) |
| **Outside the repository** (temp area, `<TMPDIR>/zyris-website/…`) | ownership record and log of the dev server (`preview`); backups and session state of `edit` | `preview`, `edit` |
| **Installed plugin** | nothing | nobody |

The internal names `zyris-website`, `zyris-optimize:*` and `ZYRIS_WEBSITE_STATE_DIR` come from the former plugin and stay unchanged: website-project data formats are a separate interface and are never renamed or converted because of the plugin name. The one exception is the schema file (`website.schema.json`).

## Setup and configuration

There is no plugin configuration for users. Site configuration lives in your project's manifest. `setup create` fills it like this: `$schema` = `./website.schema.json`, `version` = 2, per site `name` = the site ID (not necessarily a domain), `domain` only if you stated one (missing = not decided yet; never derived from the name), `path` = `sites/<site-id>`, `type` = `astro-static`, `title` (given or the domain), `aliases` (given or empty), `port` (given or automatic) and `environment` only on explicit request. Existing entries are never rewritten. Every operation that uses an existing project validates the manifest against the **plugin's** schema, never against a looser project copy.

Plugin developers additionally use the ignored file `.local/marketplace.json` for local marketplace associations; it is not committed ([Development](development.md)).

## Save and resume

| Skill | Writes | Never writes |
|---|---|---|
| `setup` | site folder, manifest entry, schema copy (only when absent), `.tmp/` with its `.gitignore` entry, ownership record; with `verify` the npm side effects `node_modules/`, `dist/`, `.astro/` and possibly `package-lock.json` | files of existing sites during `adopt`; generated files during `verify` |
| `preview` | own entry in `.claude/launch.json`; ownership record and log in the temp area | manifest, port, schema copy |
| `optimize` | immutable reports, work list; during `apply` only the approved spot of a non-ignored project source file | site content during audit and decision; manifest; ownership record |
| `edit` | only `src/pages/index.astro`; backup and state in the temp area | reports, rules, brand, check-script, `package.json`, lockfile, manifest, schema and ownership-record files |
| `publish` | nothing | everything |

Resuming: `optimize` continues earlier runs through the work list and stable finding IDs; `preview` recognises its own running server by the ownership record; `edit` works with a session that points to the backup. A chat history is not storage.

## Failures and recovery

- **Nothing is overwritten to “repair”.** Unsupported formats (former schema format, type `astro`, removed fields) are refused with a diagnosis before anything is written. There is no automatic migration, no fallback and no recovery that overwrites user data.
- **setup:** a write error restores all files and the registration (`failed-rolled-back`), otherwise the assistant names the remainder (`failed-partial`). After `failed-build`/`failed-check` files and registration stay; repair the file and run `verify`.
- **optimize:** a work list that was edited by hand or damaged stops all commands before building, without changing it. Restore it from Git. A wholesale line-ending conversion (for example by `autocrlf`) also counts as a change. A report is never overwritten.
- **edit:** if the target file was changed, removed or replaced by a symlink in the meantime, the result is `conflict` without overwriting; the newer version stays. The backup (source-file snapshot and the original, byte-exact) is in a folder with mode 0700 outside project and plugin. A `TMPDIR` inside the project or plugin and symlinks in the area are refused. Only the own folder is cleaned up, only after a confirmed success and only after the whole tree was checked against the expected objects; if a foreign file is found, nothing is removed.
- **preview:** if the state area is unsafe (for example a symlink), `start`/`status`/`stop` report `unsafe-state` and signal nothing.
- Existing uncommitted changes of others stay untouched in all skills (no stash, reset or clean).

## Limitations

The following limits are known and **not** closed; the protections cover only the cases evidenced by the tests.

- **Race window in `edit`:** between the hash check and the atomic replace (`os.replace`) there is a short window. A foreign change in exactly that moment would be overwritten; there is no file-system lock (BD-28).
- **Symlink protection:** `O_NOFOLLOW` protects only the last path component when opening. Swapping a parent directory between check and open is not generally excluded.
- **State area of `preview`:** ancestors of the base directory (the system temp folder, on macOS for example `/var` → `/private/var`) are not checked; a malicious process of the same user is outside the protection.
- **Secret redaction is pattern-based:** `edit` redacts values of known fields in npm output (names containing TOKEN, SECRET, PASSWORD, PASSWD, API_KEY or AUTH, also `Authorization`) before truncating to 2000 characters; unquoted values run to the end of the line, harmless names such as “author” are redacted too. `optimize` redacts token patterns in check output. Secrets without such a pattern stay undetected. There is no complete detection.
- **`--visual-done`** is the caller's statement; the helper cannot verify an actual visual check.
- **`edit` and `setup`:** after an `edit` change to a generated file the ownership hash no longer matches (`conflict` on a repeated `create`, `modified (kept)` on `verify`); no re-baselining of the hashes.
- The process tests of `preview` evidence the behaviour of the local Python/macOS environment, not other platforms.

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
