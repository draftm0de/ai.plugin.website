# Manifest version 2: deliberate divergence from the former source

Status: user-confirmed product decision (manifest version 2, domain optional). It differs from the manifest format of the former `zyris-website` plugin (version 1). Behaviour is proven by acceptance tests (`tests/integration/setup/test_manifest_v2.py` and the entry-point tests).

## Data contract
- `version` is 2 (was 1). `name` is the stable site ID (also folder name and ownership key), not necessarily a domain.
- `domain` is optional and holds only an explicitly given domain. Absent = "domain not decided yet".
- Version 1 is refused with a diagnosis before any write, build or process; no migration, no fallback from `domain` to `name`,
  nothing is read from `site.ts` or `astro.config.mjs` to fill `domain`.
- Manifest and domain-dependent configuration must agree (`site_common/consistency.py`). Contradictions stop; values that cannot be
  read reliably are reported as not reliably checkable (never treated as "no domain").

## Diverged files (relative to `skills/`)
- `_shared/resources/website.schema.json`: `version` const 2, optional `domain`.
- `setup/scripts/validate.py`: adds `check_site_id`.
- `setup/templates/astro-static/astro.config.mjs.tpl`: `site` only with a domain.
- `setup/templates/astro-static/src/lib/site.ts.tpl`: `SITE` is `string | null`; `absolute()` returns null without a domain.
- `setup/templates/astro-static/src/layouts/BaseLayout.astro`: canonical, og:url, og:image and twitter:image only with a domain.
- `setup/templates/astro-static/src/pages/robots.txt.ts`, `sitemap.xml.ts`: no sitemap address / empty sitemap without a domain.
- `setup/templates/astro-static/src/pages/index.astro.tpl`: no domain text in the page when none is set.
- `setup/templates/astro-static/scripts/seo-check.mjs`: without a domain, address checks are skipped and reported; a canonical without a domain is an error.
- `setup/templates/astro-static/CLAUDE.md.tpl`, `setup/templates/_manifest/static/website.json.tpl`: ID/domain wording and version 2.
- `preview/scripts/preview.py`, `preview/scripts/control.py`: consistency check before launch entry / start; `inspect` accepts a domainless site (identity by site name only, reported as `identity_basis`).
- `optimize/scripts/findings.py`, `optimize/scripts/audit.py`, `_shared/scripts/which_site.py`, `setup/scripts/static_setup.py|site_setup.py|manifest.py|ownership.py`: logic changes for the same decision (adapted code without hash identity, as before).

## Not part of this decision
No migration tool for version 1 projects; no placeholder domains. Later domain assignment is the separate `set-domain` operation of `setup`.
