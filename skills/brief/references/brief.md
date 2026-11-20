# brief (reference)

State: `.project/website/<site-id>/brief.json` (current), `brief-history/rNNN.json` (every saved revision, kept), `flow.json` (record). Written only by `flow.py`.

## Format (schema_version 1, strict; unknown keys are refused)
```
{"schema_version": 1,
 "fields": {"<field>": {"value": ..., "status": "confirmed|proposed|open", "note": "optional"}},
 "palette_proposals": [{"name": "...", "colors": {"primary": "#rrggbb", "background": "#rrggbb", "...": "#rrggbb"}, "rationale": "one sentence"}]}
```
Required fields: `purpose`, `audience`, `offer`, `message`, `visitor_action`, `tone`, `site_language` (a language tag such as `de`; the language of the website, **not** the operator language), `design_direction`, `palette` (`{name, colors, rationale}`; at least `primary` and `background`). Optional: `materials` (existing texts, images, logos), `notes`.
`confirmed` = the person said or accepted it; `proposed` = your suggestion; `open` = unknown (value may be empty). Facts the person did not state (prices, qualifications, results, years, counts) are never filled in; they stay `open`.

## Asking
Bundle at most four questions; give a concrete suggestion for each. Palettes: two or three, each with a short reason tied to audience and tone, with sufficient text contrast. Several feedback rounds are normal: save after each round.

## Confirmation and change
`brief-confirm` needs the person's explicit statement and all required fields `confirmed`. Saving a changed brief afterwards makes the confirmation obsolete (`brief.state` = `in-progress`, `changed_since_confirmation`); design revisions and approvals based on the old brief become `stale`, implementation too. Nothing is deleted; the person's page is not touched.
Identical content saves nothing (`unchanged`).
