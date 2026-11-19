# Repository architecture / Repository-Struktur

- `SCOPE.md`: confirmed goals, non-goals and acceptance criteria; draft until agreed.
- `skills/<name>/SKILL.md`: public skill entry points for plugins.
- `skills/<name>/scripts/`: distributed runtime; no imports from a developer checkout.
- `skills/_shared/`: optional shared runtime/rules, no extra SKILL.md.
- `scripts/`: development, validation and distribution helpers only.
- `tests/unit/`, `tests/integration/`, `tests/contracts/`: deterministic tests.
- `tests/behavior/`, `tests/native/`: explicit model/isolated-host tests only.
- `tests/fixtures/`, `tests/support/`: fictional data and shared helpers.
- `docs/`: maintained documentation. Do not duplicate authoritative product facts.
- `.local/marketplace.json`: ignored machine-local associations, never committed.

Plugin repositories have plugin.json and derived host manifests, never marketplace
catalogs. Marketplace repositories have marketplace.json and derived host catalogs,
never new embedded plugins. GitHub repository creation is outside these tools.

Root scripts are not shipped runtime. Keep runtime dependencies inside the plugin
payload. Do not store user state in the installed plugin. Use only needed directories.
Before claiming completion, compare implementation against each confirmed requirement
and distinguish missing evidence from verified contradictions. Files existing and
structural checks passing do not prove domain behavior or host acceptance.

Die Struktur ist eine Entwicklungsregel, keine Garantie für LLM-Verhalten. Das
bestätigte Zielbild bleibt maßgeblich. Fehlende Belege und tatsächliche Widersprüche
getrennt berichten; fachliche Erfüllung braucht Source-Review und passende Tests.

## Website plugin / Website-Plugin

- Planned layout (see `docs/migration/plan.md`): five skills `setup`, `preview`, `optimize`, `edit`, `publish` under `skills/`; shared runtime and the plugin's manifest schema under `skills/_shared/` (no `SKILL.md`); skill-specific templates and references with their skill; no runtime dependency on `www.draftmode`, `ai.plugins`, the Coach checkout or developer paths.
- State of website projects (`.project/`, `sites/`, `.claude/launch.json`) belongs to the user's project and is written only by the skill named for it; process state and backups live outside the repository and outside the installed plugin.
- `docs/migration/` holds migration evidence (source inventory with SHA-256, decisions, plan). It is not a second product definition; SCOPE.md stays authoritative.

Geplante Struktur siehe `docs/migration/plan.md`; Migrationsnachweise unter `docs/migration/` sind keine Produktdefinition.
