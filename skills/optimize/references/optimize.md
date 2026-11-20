# optimize: behaviour reference (Website plugin)

Normative behaviour of the `optimize` skill. Product requirements: `SCOPE.md` R12, R13 (and R4, R5, R6, R7, R21, R24). Shared rules: [`../../_shared/references/interfaces.md`](../../_shared/references/interfaces.md). Derived from the implemented parts of the source contract; everything the source marked as planned (GEO, Lighthouse, link-graph checks, an isolated copy with `npm ci`) is **not** part of this plugin and must not be offered. Statements about test results do not belong here.

## 1. Purpose

Make SEO and accessibility of one site checkable, keep a durable record of every audit and one running work list of findings, propose improvements, and implement only what the person approved. Typical requests: "audit the SEO of the site", "why does the check warn about descriptions?", "what would you improve?", "fix the meta descriptions of the new pages", "check before we publish".

## 2. Modes and the approval flow

Entry point: `scripts/audit.py <audit|propose|decide|apply|show>`. JSON on stdout. Exit `0` for `clean`, `clean-with-warnings` and the successful `propose|decide|show`; `1` for `errors`, `incomplete`, `readonly-violated` and every `STOP:` message (including a failed file operation); `2` when the site must be chosen (`ask` with `options`).

| Mode | Triggered by | Allowed | Forbidden |
|---|---|---|---|
| **audit** (default) | "check", "audit", "what is wrong", a bare "optimize" | read files, build into the git-ignored `dist/`, run the checks, write the snapshot report and update the work list (the report area only), store proposals | any change to `src/`, `public/`, content, metadata, design, rules, configuration, lockfiles; any commit; any install; any automatic repair |
| **decide** | "SEO-001 approve / defer / reject" | change the decision of named finding IDs in the work list | any site change; changing an earlier decision needs an explicit instruction (`--change`) |
| **apply** | "implement SEO-001", "implement the approved points" | only findings that are `approved` with an unchanged proposal and starting point, only the file of the documented edit, then the automatic recheck | anything outside the approved scope; unapproved or stale proposals; an install; a commit |
| **show** | "what is open?" | read and summarise the work list | every write |
| **propose** | writing drafts | store proposals for existing findings (no new audit run) | every site change |

An order that only says "optimize" is audit + proposals + work-list reconciliation. **Audit and decide never authorise apply.** Approval is bound to the **documented proposal and its starting point**; it is not a blanket permission and is not asked for again while both are unchanged. If either changed, the next run shows the deviation, resets the finding to `proposed` with an attention note and the person decides again. A finding gets a decision status only through `decide`; "done" is a recorded result of a passed recheck, not a status.

Finding statuses are exactly `proposed`, `approved`, `deferred`, `wont-do`.

## 3. Inputs, prerequisites

- `audit.py audit|propose|decide|apply|show [IDs] [--site] [--cwd] [--last] [--root] [--status] [--reason] [--change] [--proposals FILE] [--editorial FILE] [--applied IDs] [--npm PATH]`. The working directory (or `--root`) is the website project; the project is never searched for elsewhere.
- Site: the shared resolver (named > working directory > only site > last used with confirmation > ask). The skill additionally runs `_shared/scripts/which_site.py` first to learn the site's rule files; **the driver itself does not check that `rules/seo.md` and `rules/accessibility.md` exist**, so the skill stops before the audit if they are missing (the site has no rules yet).
- The manifest `.project/specs/zyris-website.json` is validated against the plugin's own schema before anything else: an invalid manifest, a removed type or field, or the former project format (reference to or only a copy of `zyris-website.schema.json`) is a `STOP` with the cause before a build, report, work list or lock exists. No fallback, no migration, the old file is never read or changed.
- Prerequisites of an audit and of `apply`: `npm` and Node 22.23.4 or newer (unless `--npm` names a tool); in the site folder `package.json` with a `build` script, `node_modules/` and `package-lock.json`; `dist/`, `node_modules/` and `.astro/` are git-ignored. A gap is reported (`incomplete`, `STOP` for `apply`) with the step for the person (for example `npm ci` in the site folder). **Nothing is ever installed**, not in the project and not in a copy; this holds for `apply` too.
- Brand rules (`.project/brand/`) and the site's rules (`<site>/rules/seo.md`, `accessibility.md`) are read before writing any proposed text.

## 4. Side effects

| Step | Local writes | Mode |
|---|---|---|
| `npm run build` | `dist/`, `.astro/`, tool caches (git-ignored) in the site; `package-lock.json` is versioned and is not touched | audit, apply |
| `npm run seo:check`, `npm run a11y:check` | none | audit, apply |
| report and work list | the report area only: `.project/reports/<site>/optimize/<timestamp>.md` (created exclusively, never overwritten) and `.project/reports/<site>/optimize.md` (replaced atomically under the lock file `.optimize.lock` in `.project/reports/<site>/`) | audit, propose, decide, apply |
| source edit | the one non-ignored project source file of the approved, non-stale mechanical edit (see section 7) | apply only |

**Audit, decide, propose and show leave all project source files unchanged**, including `package-lock.json` and `.gitignore`. The driver compares the paths and SHA-256 hashes of non-ignored, non-private files before and after (the report area of the site excluded); a difference ends in `readonly-violated` with the list of changed files. Symlinks are recorded as link objects, never followed. Replacing a directory by a link is visible as removed source paths plus the new link; the target is never opened. Existing changes are audited as they were and kept. The skill never reverts a changed file (another cause is possible).

## 5. Results

From the **process exit codes**, read directly, never from words in the output:

- `clean` (no errors, no warnings), `clean-with-warnings`, `errors` (technical errors present);
- `incomplete`: build failed or produced no `dist/`, prerequisite missing, a check script missing, did not start, timed out, exited with an undefined code, or printed output without the known shape or contradicting its exit code. **Never reported as clean.** After a failed build the checks are skipped and reported as not run (a stale `dist/` must not count). `seo:check` and `a11y:check` run separately, so an error in one does not hide the other's result;
- `readonly-violated`: a project source file was added, removed or changed during the run (listed, not reverted); nothing is closed by such a run.

Driver exit `0` only for `clean` and `clean-with-warnings`. "Passed", "built" or "clean" is reported only for a step that ran in this invocation and ended with `0`.

## 6. Findings, classes, evidence, limits

Every finding carries `id` (`SEO-001`, `A11Y-001`, `ED-001`; counters per site, never reused), `key` = criterion + location + detail (the identity: **site + criterion + location**, never message text or line number), class, criterion with rule reference, location, evidence (the latest check message, occurrence count), why, proposal (kind `draft`, `rule` or `opinion`; current text, proposed text, optional mechanical `edits`), priority with reason, method, limits, first found, last checked, report references, status, decision log, `approved_basis`, `attention`, resolution, earlier resolutions, `reappeared`, `applied`.

Classes are never mixed:

1. **technical error**: a script error that makes the check exit `1`. Fixed only as an approved proposal.
2. **warning**: a script warning (lengths, missing size attributes, page not in the sitemap); the exit code stays `0`.
3. **editorial recommendation**: a judgement (wording, topic coverage, internal links) supplied by the reviewer with `audit --editorial FILE`. Never produced or closed by a script; never closed by the absence of a check. Only a named `verify` property of the source text (`present` or `absent`, in a file inside the project) can be confirmed locally, and that confirms the text change, not any effect on rankings or readers.

The adapter (`findings.py`) adds no criteria: it reads the output of the site's own check scripts, verifies shape and agreement with the real exit code, and maps each message to a stable criterion. An unknown shape is `unparsed` (the check is incomplete), an unknown message stays visible as `<family>.unclassified`. The site's check scripts are never edited, wrapped or filtered. A changed script format needs an adapter update.

**Manual check points** are listed in every report and are **never** marked as passed by a script: colour contrast, keyboard path and visible focus, zoom/reflow at 200 %, screen-reader reading of headings and links, truthfulness of every claim on the page, hero-image alt decisions, legal pages (only the owner can do these), redirects/HTTPS/headers/404 status at the live server, Search Console / Bing Webmaster registration and DNS.

**No invention.** Proposals use only facts already on the page and the rule files: no invented claims, sources, reviews, ratings, awards, dates, authors, statistics or quotes; no structured data (`Organization`, `Review`, `FAQPage`, `Product`, ...) for content the page does not visibly contain; no padding to reach a length; no promise or estimate of ranking, traffic, snippets or AI citations. A proposal without a source from a rule file or official documentation is labelled `opinion`. The checks are static checks of the built HTML/CSS; the report says so and that no ranking is measured.

## 7. Decisions and apply

- `decide ID... --status proposed|approved|deferred|wont-do [--reason TEXT] [--change]`: stores the decision and its log entry only. A finding that already has a decision other than `proposed` is changed only with `--change`; a done finding cannot be decided (until it reappears). A call with several IDs is atomic: one unknown ID changes nothing.
- `apply ID...`: all IDs must be open, `approved`, with an unchanged `approved_basis` and a proposal that carries a mechanical `edit` (`file`, `find`, `replace`). Otherwise `STOP`, nothing changed. The edit file must be a **non-ignored source file of the selected site** (repo-relative, inside the site folder, no `..`, not absolute, no symbolic link in the path); the search text must occur **exactly once** in the original content and must not be empty; the replacement must differ; every replacement span is located in that original content (never in text produced by another edit of the same request), spans that overlap or contradict each other are refused with a `STOP:` before the first write (no partial application), and an ID named twice is applied once; the file must be UTF-8 text and its line endings stay byte-exact. The prerequisites of section 3 are checked before the first write. Several files are written one by one and restored if a later file fails; the driver stops if any other file changed during the apply. The recheck is run by `apply` itself: the same audit (build, `seo:check`, `a11y:check`, guard). No install, no commit, no push.
- A proposal without a mechanical edit is implemented by hand within the documented scope (one file at a time, nothing else), then rechecked with `audit --applied ID...`; `--applied` accepts only approved, open findings.
- **A finding moves to the history only when a complete run (build ok, check exit and output valid, guard passed) after a successful build no longer reports it**; the decision and the evidence stay with it (`via: apply` if optimize applied it, otherwise `external`). On a failed build, an incomplete check or a violated guard, the finding stays open and approved with the reason and the next step in its attention note; `deferred` and `wont-do` findings that are no longer reported stay where they are, marked "not reported". Improving within the same approved scope needs no new approval.
- A done finding that is reported again keeps its ID, gets `reappeared + 1`, goes back to `proposed` with the earlier resolution and the decision log kept, and waits for a new decision.
- Approval, proposal and evidence changes: an approved finding whose proposal or evidence changed is voided (`proposed`, attention note) unless it was just applied by optimize.

## 8. Reports and the work list

Location: `.project/reports/<site>/optimize/<YYYYMMDD-HHMMSS>.md` (local time; the file states offset and UTC) and `.project/reports/<site>/optimize.md`. `<site>` is the canonical manifest name and must match `[a-z0-9]+([.-][a-z0-9]+)*`. A timestamp collision gets `-2`, `-3`, ... and never overwrites (also when the name appears during the run, or is a dangling symbolic link). Every path component below the project root must be a real directory, not a symbolic link; the report area is versioned (no ignore rule). Foreign files in the report area are left alone.

**Snapshot report** (immutable): run table (site, time with zone, mode, result, source-files digest, read-only guard result, previous run), check table (command, **process exit code**, result), skipped or failed checks with reasons, output tails (secrets redacted), changes since the previous run, the full text of every finding touched in the run, the applied diff (apply only), the limits and the manual check points. The marker `<!-- zyris-optimize:report v1 site=<site> -->` is part of the project data format.

**Work list** (`optimize.md`, the only status source): sections *Open work* (`proposed`, `approved`), *Deferred and rejected*, *Done (history)*, generated from a JSON block at the end (`<!-- zyris-optimize:state sha256=... -->`, format `zyris-optimize-worklist` version 1). The SHA-256 must match, the block must validate for the selected site, and the generated text must equal what the block renders to. These markers and the generated text (which still names the former skill call) are the **unchanged project data format** (R21): changing them would make every existing work list look "edited by hand". Decisions change only with `audit.py decide`.

**Errors and abort.**

| Case | Behaviour |
|---|---|
| site not resolved | `STOP`/ask, nothing run |
| damaged, hand-edited, unreadable (not UTF-8), foreign-site or future-version work list | `STOP` before anything is built; the file is not changed |
| work list locked or changed by someone else | `Conflict` stop naming the file; a decision made during an audit is merged, never overwritten; a leftover `.optimize.lock` (killed run) is reported with its path and removed by hand after checking |
| report path is a symbolic link, site name unsafe | `STOP`, nothing written |
| `build` fails or prerequisites are missing | `incomplete`, exit code and output tail (secrets redacted) reported, checks skipped, nothing closed |
| file-system error while writing | `STOP: a file operation failed (...)`; nothing is reported as done; check `.project/reports/` and `git status` |
| interruption | `dist/` may be partial (the next run rebuilds); leftover `.snapshot-*.tmp`/`.optimize-*.tmp` files in the report area are harmless |

## 9. Permission boundaries

Audit, propose, decide and show need no confirmation (a decision is itself the person's instruction). Apply: only approved proposals within their documented scope. Needs a separate yes: touching more than the named file, changing `rules/`, design/CSS foundation, serving configuration, `package.json`, the lockfile, deleting content, any commit. Never in scope: Search Console / Bing Webmaster registration, DNS and server redirects, legal pages, publishing, form sending, claims about rankings. Secrets and full environment variables never go into a report or the chat.

## 10. Not available

GEO criteria, Lighthouse, link-graph checks and orphan-page detection, an isolated dependency preparation (copy plus `npm ci`), live crawling, ranking or traffic measurement. They are not offered and not worked around; a request for them is answered with this limit.
