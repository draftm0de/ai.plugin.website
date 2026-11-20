# plugin-website: entry and flow (reference)

## What the entry is
`plugin-website` is the central entry of the plugin `website-manager` (the plugin identity does not change). It is not an alias of a removed plugin name.
It inspects the selected project without changing anything, explains the next step in a sentence or two, starts the missing steps itself and asks only for what is really missing.

## How it is started (support levels, kept apart)
| Level | Claude | Codex |
|---|---|---|
| Explicit call by skill name | `/website-manager:plugin-website` (plugin skills are namespaced by the plugin name); structurally provided | by naming the skill `plugin-website` in the request; structurally provided, host behaviour not verified |
| Natural activation from the description ("create a website for ...") | depends on the host's skill matching; the `description` is written for it; **not verified** | same; **not verified** |
| A single bare word "plugin-website" always activating the skill | **not guaranteed**, not promised | **not guaranteed**, not promised |
Everything in the last two rows needs a real host test (NOT RUN).

## Order and states (`flow.py status`)
1. `setup`: missing -> `setup` skill. `complete` = valid version-2 manifest, consistent configuration, site folder with `package.json` and `src/pages/index.astro`. `contradictory` (invalid manifest, version 1, configuration contradicting the manifest, missing folder) -> `resolve-setup`: report, change nothing.
2. `brief`: `missing` / `in-progress` -> `brief` skill; `confirmed` -> next.
3. `design`: `missing` or `stale` -> `design` skill (new revision); `variants` -> show, ask; `revising` -> new revision from the feedback; `approved` -> next.
4. `implementation`: `missing` / `started` / `stale` -> implement; `done` -> checks; `user-changed` -> report, ask.
5. `checks`: technical and visual both `passed` for the **current** page content -> `done`.
Existence of a file proves nothing; every state is derived from the record and the hashes of the real artifacts.

## Information from the first request
Take over: a stated domain (`setup --domain`), the business type and place (brief `purpose`, `audience`, `offer`, marked `proposed` unless the person stated it as a fact), a stated language. Never invent a domain; without one the project works locally without public addresses. The site ID (`setup <site-id>`) is a short lowercase name derived from the request (for example `physio-wien`); it is internal and stays when a domain is added later (`setup set-domain <site-id> <domain>`).

## Implementing the approved design
Preconditions: `design.state` = `approved`, no `stale` entries. Scope stays the start page `src/pages/index.astro`; other files are not written (the `edit` contract; extensions are not part of this flow).
1. `flow.py implement-start --site <site>`. A refusal means the page changed after the approval: show the person, do not overwrite; continue with `--accept-current-page` only after their agreement. `already-implemented` -> nothing to do. `resumed-changed` (or `next_step` = `resolve-implementation-conflict`): the page differs from the start state. If an `edit` session of this implementation wrote it, finish with that session (step 3). Otherwise treat it as the person's own change: ask once whether it is the new starting point (`--accept-current-page`). The design approval is not asked again.
2. Read the approved prototype (`variant_file` in the result, below `.project/website/<site>/design/`). Translate it into `src/pages/index.astro` with the `edit` skill commands (`preflight`, `begin`, `write`/`replace`, `check`, `diff`), **after** `implement-start`, in one edit session; keep its original backup, expected hashes and conflict detection. Note the `state_folder` that `edit.py begin` returns. Open facts stay marked as open placeholders in the page text; do not fill them with invented content. The page uses the confirmed palette through scoped styles of `index.astro`.
3. `flow.py implement-finish --site <site> --edit-state <that state_folder>` **before** `edit.py finish` (which removes the folder). It is accepted only if that session belongs to this project and site, started from the recorded start hash, wrote at least once itself and its last write is the current page. A matching page hash, a manual change or a check-only session is not proof. After an interruption the surviving state folder is enough to finish later. Then `flow.py record-checks --technical-evidence <edit.py check output file> --visual passed|failed --visual-note "<what was looked at>"`. `passed` for the visual check only after the page was really looked at (preview skill / browser); otherwise leave it `open` and say so.
4. The approval is the order for this implementation: do not ask for the same confirmation again.

## Not part of this flow
Further pages, blog, forms, publishing, deployment, changes to `site.ts`, theme or layout files, git operations.
