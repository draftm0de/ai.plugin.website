# Development

[Deutsch](../de/development.md) | **English**

[Home](../../README.en.md) · [Overview](README.md) · [Install](installation.md) · [Use](usage.md) · [Screens](screens.md) · [FAQ](faq.md)

## Source of truth

- The product definition is [SCOPE.md](../../SCOPE.md) (R1–R26). It separates the confirmed target from implementation evidence. Development rules: [AGENTS.md](../../AGENTS.md) and the [architecture](../architecture.md). Read both before any change; domain gaps are not hidden by later changes to the target.
- Plugin identity lives in `plugin.json` (name `website-manager`, display name “Website Manager”, no version). `.claude-plugin/plugin.json` is derived from it (`make sync-plugin`, checked with `make check-plugin`). The plugin repository owns **no** marketplace catalogs; they belong to the marketplace repository `ai.plugins`.
- Skills live under `skills/<skill>/` (`SKILL.md`, `scripts/`, `references/`, `templates/`); shared runtime and the manifest schema under `skills/_shared/` (no `SKILL.md`). The root `scripts/` folder holds development tooling only.
- The shipped runtime contains no developer paths and does not depend on the former source checkout, on `ai.plugins` or on the Coach checkout.
- Migration evidence under `docs/migration/` (plan, decisions, change list, host conventions, completeness mapping, [acceptance matrix](../migration/acceptance.md)) is not a second product definition.
- Prerequisites: [prerequisites](../prerequisites.md) (Website runtime; for this repository Git and Python 3.10+, standard library only; Make is optional). Global management rules belong to the Plugin Manager.

## Checks

Structure, source review and tests are separate steps:

```sh
python3 -B scripts/verify.py --source . --kind plugin            # structure, read-only
python3 -B scripts/verify.py --source . --kind plugin --review   # scope/source review, read-only
python3 -B scripts/plugin.py check                               # host manifest without drift
python3 -B scripts/run_tests.py --kind deterministic             # unit, integration and contract tests
```

- `make verify` and `make verify REVIEW=1` correspond to the first two commands. The review starts no target runtime. If it reports open host evidence (`needs_attention`), scope, rules or checker are not weakened.
- `make test` (layers `tests/unit`, `tests/integration`, `tests/contracts`) uses fictional fixtures and a fake `npm` only; no network and no real Node. The preview tests start their own local processes on `127.0.0.1` and end only their own, uniquely identified test processes. Skipped tests never count as passed.
- `tests/external/` (real `npm`, network) belongs to no default layer and runs only through `scripts/run_external_tests.py --approved` after a separate release; without it, it reports `NOT RUN`. Inherited environment variables do not enable it.
- `tests/native/` and `tests/behavior/` (host and model tests) never run in the default run; no suite has been run (`NOT RUN`). `tests/behavior/edit_cases.md` classifies the source's manual cases without running them.
- `scripts/migration_baseline.py` checks a source read-only against a historical inventory (`--strict-git`) and never creates a new baseline. The mapping of all 130 inventory files is in `docs/migration/completeness.json`.
- New tests should cover actual risks (broken links, incomplete mapping, manifest drift) and do not replace a documentation review. Structural checks evidence no product behaviour.

## Packaging

There is no ZIP distribution and no package build. Local tests without GitHub:

```sh
make update-local TARGET=claude DRY_RUN=1
```

- `install-local`/`update-local` (`TARGET=claude|codex`) create snapshots of the current checkout including uncommitted changes and require the chosen host CLI (`DRY_RUN=1` only creates the snapshot). After edits or branch switches run `update-local` and open a new host session. No commit, push or PR is needed for it. Never copy into host caches.
- Marketplace management (catalogs, local associations, publication) explicitly belongs to the Plugin Manager (`/plugin-manager`); the Website plugin offers no function for it. Local associations live in the ignored file `.local/marketplace.json` (normal setup through the Plugin Manager's `configure`). Before this stage's catalog change, `make verify` reported under `local_development` that the plugin was not registered in the selected marketplace; after renaming the catalog entry to `website` it reports `complete`. That is a structural check of the local configuration (the file was neither created nor changed in this stage), not evidence of an installation or a host import.

## CI and releases

The prepared CI runs `make test` and `make check-plugin`; its existence evidences no successful run. There are no release Actions, manually maintained versions, tags or plugin ZIPs. Publication happens only after concrete approval via feature branch, commit, push, PR, checks and merge (see the Plugin Manager). This stage performed no commit, push, tag, release or deployment. The locally adjusted catalog entry in `ai.plugins` proves neither a push nor reachability of the plugin repository nor a host import.

## Maintain documentation

German is the default language, English equivalent: statements, commands, limits and status must agree in both languages and are changed together. The pages explain the behaviour and link [SCOPE.md](../../SCOPE.md) instead of duplicating contracts. `docs/documentation.json` points to the canonical sources with the fields the Plugin Manager supports (`source_skill`, `extra_sources`). Examples must be marked as fictional; real screenshots only with host, language and date. No absolute developer paths in user pages. A contract test checks internal links, the correspondence of `docs/de` and `docs/en` and the completeness mapping; it does not replace the technical review.

---

Documentation prepared with Plugin Manager. Source-product ownership remains unchanged.
