# Guided flow: state contract (development note)

Scope reference: SCOPE.md (R29 to R33). Implementation: `skills/_shared/scripts/flow.py`, `skills/_shared/scripts/site_common/flowstate.py`.
Tests: `tests/integration/flow/test_flow_state.py` (structural and deterministic; no conversation behaviour, no design quality).

## Files (selected website project only)
`.project/website/<site-id>/flow.json` (schema_version 1) · `brief.json` · `brief-history/rNNN.json` · `design/rNNN/{A,B,...}.html, index.html, manifest.json, feedback.jsonl`.
Unknown `schema_version`, foreign `site`, invalid JSON, missing keys, symlinks anywhere below the project: state `unreadable`/refusal; nothing is repaired, migrated or overwritten; every write command stops first.

## Derived states (never from file existence alone)
setup: `missing | complete | contradictory` · brief: `missing | in-progress | confirmed | damaged` · design: `missing | variants | revising | approved | stale | damaged` · implementation: `missing | started | done | stale | user-changed` · checks: `technical`, `visual` = `open | passed | failed`, bound to the sha256 of the current `index.astro` (otherwise `outdated` and `open`).

## Staleness (nothing is deleted)
- Brief saved after its confirmation: `brief.in-progress` (`changed_since_confirmation`); revisions made from the old brief: design `stale`; the approval: stale; the implementation: `stale`. They stay on disk.
- A newer design revision after an approval: approval stale.
- Variant file changed after registration: `damaged` (approval and registration refuse).
- `index.astro` changed after the implementation was recorded: `user-changed` (not overwritten); changed after the approval and before the start: refusal unless the person agrees (`--accept-current-page`).

## Approval binding
An approval records revision, variant, variant sha256, confirmed brief sha256 and the sha256 of `index.astro` at that moment. It requires the latest shown revision and an explicit statement.

## Out of scope here
Publishing (still a placeholder), further pages, blog, forms, changes to files other than `src/pages/index.astro`. Additional `edit` write paths are not enabled; a minimal proposal is open.

## Review hardening (2026-11-20)
- **Whole record validated** (`validate_record`): exact keys, nested types, sha256 values, gap-free revision numbers and the relations approval -> revision/variant/hash, implementation -> revision/variant/hash, checks -> finished implementation. A record that fails is `unreadable`; every write stops first and the file is kept.
- **Existing brief validated** before every use; a damaged `brief.json`, a revision different from the record, or a missing file with a recorded revision stops `brief-save`/`brief-confirm` without a write. `brief-history/rNNN.json` is never overwritten: an existing file with different content stops the save, an identical one completes the interrupted save. An unregistered revision that already has a `manifest.json` is not registered over it.
- **New vs. incomplete project:** without a manifest, existing `.project/specs/*`, `.project/reports/*`, `.project/website/*` or `sites/*` make the setup `contradictory` (`resolve-setup`), never `missing`.
- **Implementation resumption:** `implement-finish --edit-state <folder>` reads the `index.json` of the `edit` session that `edit.py begin` created (in the project's own session area below `$TMPDIR/zyris-website/`) and accepts it only if it belongs to this project and site (root, site, path, file), was started from the recorded start hash (`original_sha` = `base_sha256`), contains at least one write of its own and its last write and `expected_sha` equal the current page. A matching page hash alone, a manual change, a later session started from changed content, or a check-only session is refused. The accepted session summary is stored in the record (`implementation.edit_session`). A changed page without proof is a conflict (`resolve-implementation-conflict`, `resumed-changed`); `--accept-current-page` rebases the start state when the person agrees. The design approval stays valid. Plain consistency checks of edit's own record, no cryptography; finish before `edit.py finish`, which removes the session folder.
- **Registered artifacts:** variants, the comparison page (`index.html`, sha256) and `manifest.json` (must equal the registered record) are verified; a change or a missing file makes the design `damaged`, blocks approval, registration and implementation (`blocked`), and keeps the records.
- **Astro config reading** (`consistency.astro_site`): the default export is resolved (`export default defineConfig({...})`, `export default {...}`, or one plain `const NAME = ...; export default NAME;`). A `defineConfig` call that is not the export, several defaults, re-exports, `module.exports`, reassignment or function wrapping are *unverifiable*. Nothing is executed.

## Review hardening (third round)
- **Strict numbers:** every version, revision and count field (`schema_version`, `brief.revision`, `confirmed.revision`, `revisions[].revision|brief_revision`, `approval.revision`, `implementation.approval_revision`, `edit_session.writes`, and `brief.json` `schema_version`/`revision`) must be a real integer (`1.0`, `true`, `null`, strings and containers are refused with a diagnosis; the file stays untouched). The manifest `version` must be the integer 2 (`2.0` is refused).
- **Astro config:** the exported object is read only in forms that are certain. `const cfg = {...}; export default cfg;` is trusted only when `cfg` appears exactly twice (declaration, export); any other use (`cfg.site = ...`, `cfg['site'] = ...`, `Object.assign(cfg, ...)`, spread, passing it on) and any expression continuing after the literal or the `defineConfig(...)` call (`.x`, `||`, `??`, calls, operators) make the config *unverifiable*. Unverifiable is neither "domainless" nor "matches".
- Existing `flow.json` files from before this change lack `implementation.edit_session` and are refused as damaged (no migration; development state only).

