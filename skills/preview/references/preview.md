# preview: behaviour reference (Website plugin)

Normative behaviour of the `preview` skill. Product requirements: `SCOPE.md` R10, R11 (and R5, R6, R7, R24). Shared rules: [`../../_shared/references/interfaces.md`](../../_shared/references/interfaces.md). The host-tool model (`preview_start|stop|list`, host server IDs) is **not** part of this plugin and must not be used. Statements about test results do not belong here.

## 1. Purpose

Show one registered site locally: select the site, make sure its dev server runs exactly once, report readiness, report the state, stop it on request, and check what the served page shows. Three facts are always kept apart:

1. **Process ownership and process state** (`start`, `status`, `stop`).
2. **Identity and content of the served page** (`inspect`, an HTTP pre-check).
3. **Actual visual check in a browser** (done by the host's browser tool, only if it really happened).

## 2. Commands

`control.py <start|status|stop|inspect> [site] [--page P] [--expect TEXT]... [--cwd DIR] [--last DOMAIN] [--root DIR] [--timeout S]`. JSON on stdout (`started` is `false` before a process exists, `true` after). Exit `0` for `running-new`, `running-reused`, `not-running`, `stopped`, `page-confirmed`; `1` for every failure state and `STOP:` messages; `2` when a choice is needed (`ask` with `options`).

Site selection follows the shared rule (named > working directory > only site > last used with confirmation > ask). `status` and `stop` never use "last used" without confirmation. The port comes from the manifest (`port`), otherwise 4321 plus the position in the manifest.

`--timeout` is finite, greater than 0 and at most 600 (default 60). Anything else (`nan`, `inf`, `0`, negative, above 600, non-numbers) is rejected as `STOP` before the site is read or anything is started or written.

Order for every verb: validate timeout, load and validate the manifest against the plugin schema (invalid manifest, removed type/fields or unusable schema copy: `STOP` with the cause, before anything below), resolve the site.

## 3. Process control (`start`, `status`, `stop`)

Only `control.py` starts, reuses or stops a dev server. It starts `npm --prefix <site> run dev -- --port <n> --ignore-lock` in a new process group, output to a log file. `--ignore-lock` is appended by the controller (not by the launch template) so that the dev server stays in the process group the record names; a dev command that detaches itself anyway ends as `failed-early-exit` with "NOT adopted", and the detached server is left alone.

**Ownership record** `<TMPDIR>/website-manager/<sha256(project root realpath)[:12]>/preview-<site>.json` (override: `WEBSITE_MANAGER_STATE_DIR`): `start_id`, `project_root`, `site`, `working_dir`, `launch_name`, `port`, `pid`, `pgid`, `process_start_time`, `command_line_at_start` (informational only), `started_at`, `surface`, `log`. Log `preview-<site>-<start_id>.log` beside it. Both live outside the repository and outside the plugin.

**An instance is ours only if all hold:** the record's project root, site and working directory equal the selected ones; the PID is alive (not a zombie) with the same process start time and process group; the recorded port equals the manifest port; every listener of the port (`lsof`) belongs to the recorded process group. Launch name and port are never proof. Verdicts: `ours`; `stale` (process gone or PID reused: record and its log dropped, nothing signalled); `foreign` (another root/site/directory/port, or the port is held outside our group: `unknown-owner`, nothing signalled); `none`. Readiness and reuse additionally need **attribution**: an HTTP answer counts only if at least one listener of the port was seen and all listeners belong to the recorded group; otherwise `insufficient-evidence` (`kind: not-attributed`), never `running-*`.

**Operating-system evidence.** `ps` and `lsof` are required. Before any write, start or signal (all of `start`, `status`, `stop`) a self-test runs. Missing, denied or failing tools, or tools that cannot see their own process/socket, give `insufficient-evidence` (`tool`, `kind`: `missing|denied|failed`): exit 1, nothing written, started or signalled. `stop` without evidence signals nothing; the person stops the process themselves.

**`start`** (after the checks of section 2): `needs-install` if `node_modules` is missing (nothing is installed; the person runs `npm install` in the site folder); the evidence self-test; state-directory and record-target safety checks; then the launch entry (invalid `.claude/launch.json` is a `STOP`, the file stays untouched; an identical own entry is not rewritten); ours and alive: wait for the answer and report `running-reused` (no second server); the port bound by anything not ours: `port-conflict` (`next_step: inspect`), nothing signalled, adopted or moved; otherwise spawn, record, poll `GET http://127.0.0.1:<port>/` (2xx/3xx, 2 s per request, 0.5 s interval). Results: `running-new`; `failed-early-exit` (child exited; log tail); `port-conflict` (an answer from outside our group; our group is ended); `timeout` (the instance is left running and ours, `status` then says `starting`, never running). A state is never reported as running unless the readiness probe succeeded in this invocation.

**After a process exists**, every failure ends the instance again with only the own `Popen` handle (SIGTERM, then SIGKILL; success only when the leader is reaped and the group has no members) or says that it could not: `failed-after-start` with `cleanup.result` `stopped` (record and log removed) or `incomplete` (record/log kept, PID, group, start time, `kept`; the message says the group may still run). "Nothing was started" is said only for failures before the spawn.

**`status`** only reports: `running-reused`, `starting`, `not-running` (also with `foreign_candidate` when something else holds the port), `unknown-owner`, `insufficient-evidence`. It never starts anything.

**`stop`** signals only when the verdict is `ours`, re-verified immediately before the signal: SIGTERM to the recorded process group, SIGKILL after 10 s, then group and port must be gone, otherwise `failed`. Never by name, port or guessed PID. Foreign, stale or no record: no signal (`unknown-owner` or `not-running`).

**State files** are safe by construction: directories `0700` owned by the user (a symlink, non-directory, foreign owner or group/other-writable directory is `unsafe-state`); records and logs are created exclusively (`O_CREAT|O_EXCL|O_NOFOLLOW`, `0600`), records via a staging file and atomic rename; a path that is a symlink, a non-regular file or another user's file is never read, followed, replaced or removed; a failed write after the start ends the started instance and removes only the staging file this call created. Before **any** access to a record or log (read, write, remove; also for `status`, `stop`, the process check of `inspect` and the cleanup) the state area is checked read-only (`lstat`, nothing is created): the base directory and the project's state directory must each be absent (a normal case) or a real, own, not group/other-writable directory. A symlink in either is `unsafe-state` for `start`, `status` and `stop`: nothing behind it is read, changed or removed, it is no evidence of ownership and no signal is sent. `inspect` then continues with the page check and reports the process as `unknown`. The ancestors of the base directory (the system temp folder, which may sit behind a system link) are not examined. A malicious process of the same user is out of scope.

## 4. `inspect`: the served page, separate from the process

`inspect [site] [--page P] --expect TEXT...` starts, signals and adopts nothing, never changes the manifest or the port, and works whoever runs the server. A refused start (`port-conflict`) therefore does not prevent looking at a page that already answers there.

- **Identity:** the page's `<link rel="canonical">` must belong to `SITE` (structured comparison of scheme, host, port and path segment; `https://site.test.other.example/` is not `https://site.test`) and `og:site_name` must equal `SITE_NAME`, both read from the site's `src/lib/site.ts`. Unreadable value: `page-identity-unknown`.
- **Content:** every `--expect` text must appear in the visible body text (no script, style, template, noscript, head/metadata, comments or `hidden` elements; entities and inline elements are handled; an empty expectation confirms nothing). A missing text is `page-stale`; no `--expect` is `page-identity-only`.
- **States:** `page-confirmed` (exit 0); `page-other-site`, `page-stale`, `page-identity-only`, `page-identity-unknown`, `page-not-reachable` (exit 1, never evidence). The JSON also says whether the process on the port is ours (`process`: `ours`, `not-managed-by-this-skill`, `unknown`).
- **Limit:** a static parse cannot know CSS visibility or rendering. `page-confirmed` is a pre-check (`visibility_checked: false`), never proof of the actual display.

## 5. Browser tools and hosts

- `control.py` alone starts, reuses and stops dev servers. Browser tools of the host only open and look at the URL that the controller returned (`running-*`) or `inspect` confirmed (`page-confirmed`). They never start another dev server and never switch the port; a port change is not a workaround.
- A visual success is reported only if a browser tool really opened the page in this run. Without it: "technically running, visual check open".
- Which browser tool exists is host-specific and is never derived from the absence of a tool name on another host (no conclusion about Codex from missing Claude tool names). Claude desktop example: `mcp__Claude_Browser__navigate` opens the Browser pane at a URL. Whether and how each host provides such a tool in a given session is unverified here (NOT RUN).
- **`.claude/launch.json` is a Claude-desktop-specific artifact**, not a Codex integration. `control.py start` writes only its own entry `website-manager-<site>` from `templates/launch/<type>.json.tpl` (entries of other names are kept, the own entry is replaced, never duplicated; an identical entry is not rewritten). `.claude` and `launch.json` are checked with `lstat` first: a symbolic link (also a broken one) or an unsupported file type is a `STOP` with a diagnosis, nothing behind a link is read, written or removed, and no dev server is started. The template sets `"autoPort": false`; the desktop documentation says this makes the app fail instead of moving to another port when the port is busy. The practical effect in the app has not been observed (NOT RUN).

## 6. Side effects

| Reads | Writes | Processes / network |
|---|---|---|
| manifest, project schema copy, the plugin schema, site folder, `src/lib/site.ts`, launch template, `.claude/launch.json`, ownership record | the own entry in `.claude/launch.json` (generated, `start` only; whether the file is git-ignored depends on the website project's own rules, the plugin adds no ignore rule); record and log in the system temp area | the dev server (`npm run dev`, `start` only); `ps`, `lsof`; HTTP to `127.0.0.1:<port>` |

Never: installing dependencies, editing site files, commits, deployment, signalling processes it does not own, writing into the installed plugin.
