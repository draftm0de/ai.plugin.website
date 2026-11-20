# Guided flow: development evidence (2026-11-20)

Status: **implemented in the source tree.** SCOPE.md (R29–R34) is the target; this file records what exists and what was run.

## Decisions (user-confirmed)
- Manifest version 2: `name` = stable site ID, `domain` optional and only an explicitly given domain; version 1 is refused with a diagnosis, no migration, no fallback; placeholder domains are excluded.
- `edit` keeps writing only `src/pages/index.astro`. No additional write paths are enabled (`site.ts` is not a free design file). Minimal extension proposal, **not enabled**: none needed so far; the prototypes translate into scoped styles of `index.astro`.
- `publish` is unchanged (placeholder, only `SKILL.md`).

## Implemented
| Area | Where |
|---|---|
| Manifest v2 schema, version-1 diagnosis, domain uniqueness, resolver by domain | `skills/_shared/resources/website.schema.json`, `site_common/manifest.py`, `sites.py`, `setup/scripts/manifest.py` |
| Consistency contract (text only, comments ignored, no symlinks incl. parents, "not reliably checkable" ≠ "no domain") | `site_common/consistency.py` |
| Consistency wired before changes/builds/processes | resolver (and so `edit`), `preview.py`, `control.py start`, `audit.py`, `setup` plan (templates / existing folder) and `verify` |
| Site ID decoupled from domain (argument, folder, ownership key) + `--domain`, domainless skeleton, `set-domain` | `setup/scripts/static_setup.py`, `site_setup.py`, templates |
| All URL consumers domain-aware | `astro.config.mjs.tpl`, `site.ts.tpl`, `BaseLayout.astro`, `sitemap.xml.ts`, `robots.txt.ts`, `seo-check.mjs`, `preview inspect` |
| State contract, derived status, staleness, approval binding, implementation record, checks | `site_common/flowstate.py`, `_shared/scripts/flow.py`, `docs/development/guided-flow.md` |
| Skills `plugin-website`, `brief`, `design` | `skills/<name>/SKILL.md` + `references/` |
| Packaging of `.gitignore.tpl` / `.gitkeep` | `ai.plugins/scripts/plugin_payload.py`, website `scripts/plugin.py` |
| Docs (DE/EN), SCOPE R29–R34, architecture, divergence note | `docs/`, `SCOPE.md`, `docs/development/manifest-v2-divergence.md` |

## Tests actually run (this state, after the last change)
- Website repository, `python3 -B scripts/run_tests.py` (unit + integration + contracts, fake npm, no network): **944 tests, OK** (after the third review round; earlier counts 909 and 934 are superseded).
  New: `tests/unit/shared/test_consistency.py` (12), `tests/integration/setup/test_manifest_v2.py` (23), `tests/integration/flow/test_flow_state.py` (31), `tests/integration/package/test_package_setup.py` (5), `tests/contracts/test_guided_flow_contract.py` (6).
- `python3 scripts/plugin.py check`: no drift in the derived host manifest.
- Marketplace repository `ai.plugins`, `python3 -B scripts/run_tests.py`: **33 tests, 1 FAIL**: `test_canonical_standalone_runtime_copies_match`. Cause: the fixed packager `scripts/plugin_payload.py` must equal the copies under `plugins/plugin-manager/skills/_shared/templates/...` (another plugin). Those copies were **not** changed (no authorization). The new test `tests/integration/test_payload_dot_resources.py` (1) passes.
- The marketplace packager applied to the real website checkout (one-off, not a repository test): both payloads contain `skills/setup/templates/astro-static/.gitignore.tpl` and `public/.gitkeep`.

## Not run (NOT RUN)
Real npm/Astro with the version-2 skeleton (`tests/external`, needs separate release; earlier real-tool results predate version 2 and do not cover it) · native Claude/Codex host runs, skill loading, natural activation of `plugin-website` · model/conversation behaviour (questions, palettes, prototype quality, feedback handling) · visual inspection of prototypes and implemented page · installation or update in any host · `verify --review` / independent review.

## Open
1. Marketplace repository: the copies in `plugins/plugin-manager` (templates `plugin_payload.py`, `plugin.py`, `scripts/plugin.py`) need the same three-line packager rule for its own test to pass again; requires authorization to touch that plugin.
2. Prototype checks are structural patterns; they do not prove the absence of invented claims or design quality.
3. Technical check evidence is taken from the `edit.py check` result file; the visual check stays `open` until the page was looked at.
4. No migration tool for version-1 projects (intentionally out of scope).

## Files changed
Both repositories, source state only. Nothing committed, pushed, installed or published; no host uses this state.

## Review fixes (second round)
Findings were checked against the code first; all five were confirmed (details and tests in `docs/development/guided-flow.md`, section "Review hardening"):
1. nested flow-state validation, damaged brief, history overwrite -> `validate_record`, `_brief_current`, history guard; tests `NestedStateValidationTests`, `BriefAndHistoryTests`.
2. missing manifest with existing artifacts routed to setup -> `existing_artifacts`; tests `NewVersusIncompleteProjectTests`.
3. any changed page hash accepted as finished implementation -> `implement-finish --edit-result`, conflict states; tests `ImplementationResumptionTests`.
4. comparison page / revision manifest not verified -> `_variant_problems`; tests `RegisteredArtifactIntegrityTests`.
5. unused `defineConfig` next to another default export -> `astro_site` resolves the exported object; tests in `test_consistency.py` and `AdoptWithDomainTests`.
Evidence gaps of `verify --review` (R2, R18, R25, R29): sources added to SCOPE.md (R2: the eight SKILL.md; R18/R25: the documentation contract test, because the documents lie outside the verifier's allowed Source paths; R29: the schema resource removed from `Source:` as in R5). The verifier is unchanged; it now reports `ready_for_source_review` with 0 findings. That is an evidence-pointer result, not a semantic review.
Side effect: adopting a folder whose `astro.config.mjs` already contains a `site` URL without `--domain` is now refused (`invalid`); the test fixture helper writes a config without `site`.
Tests run: website 934 OK; marketplace `ai.plugins` 33 tests, the same 1 FAIL as before (copies in `plugins/plugin-manager`, not authorised).

## Review fixes (third round)
1. Edit proof: `implement-finish --edit-state` checks the real `edit` session (project, site, file, start hash, own write, last write = page). Regressions in `test_flow_review_regressions.py` (`ImplementationResumptionTests`): manual change then a new session with only `begin` + `check` is refused; a later session over the person's change is refused; foreign project/folder, tampered session records are refused; a real `edit.py begin`/`write` followed by resumption succeeds (idempotent). The earlier `--edit-result` file was removed.
2. Astro config: property/bracket mutation, `Object.assign`, spread, passing the object on and expressions after the literal are unverifiable (`test_consistency.py`, 5 new tests).
3. Strict integers in the flow record, the brief and the manifest version (`NestedStateValidationTests`, incl. `revision: 1.0`).
Result: website repository 944 tests OK; `plugin.py check` no drift; `verify --review`: `ready_for_source_review`, 0 findings (evidence pointers only). Marketplace repository untouched in this round (its 1 known failing test is unchanged). NOT RUN: host, model, visual, real Astro/npm.

