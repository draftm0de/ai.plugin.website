# design (reference)

## Where things live
`.project/website/<site-id>/design/rNNN/`: `A.html`, `B.html`, ... (variants), `index.html` (comparison page, generated), `manifest.json` (hashes), `feedback.jsonl` (append only), optional `from-feedback.txt`. Outside `sites/`: nothing here can become part of the built or published website, and the existing start page is not touched. Registered revisions are immutable: changes are a new revision, old ones stay.

## Viewing and comparing
Open `design/rNNN/index.html` (side by side) or a single `X.html` in the host's browser tool; if the host refuses `file://` addresses, serve the revision folder locally on 127.0.0.1 with `python3 -m http.server --bind 127.0.0.1 --directory <folder>` and open the printed address. Prototypes are static: no scripts, no external resources, no web fonts.

## What a variant must be (checked by `design-register`; structural, not a design review)
- A full start page as one self-contained HTML file, `<html lang>` = the brief's website language, the confirmed primary colour used in its styles, exactly one `h1`.
- At least two variants whose page structure clearly differs (header/navigation placement, section order and kinds, grid vs single column, hero vs split ...). A colour change is not a second direction and is refused.
- A real text draft from the brief; no lorem ipsum.
- No invented facts: prices, percentages, founding years, counts, phone numbers, qualifications, awards, guarantees and treatment results may appear **only** inside an element with `data-open-fact` that reads as an open item ("Preis pro Stunde: offene Angabe"). This is a pattern check; it does not prove the absence of other invented claims, so write conservatively.

## Loop
Show -> `design-feedback` -> `design-new` -> new files -> `design-register` -> show again. Combine variants or adapt the chosen one as the feedback says. Only a statement that names the shown revision and layout is an approval ("Yes, revision 2, variant B"). "B is nicer" is feedback. If a newer revision exists, an older approval no longer applies (`stale`).

## After an approval
`design.state` = `approved` and the flow continues with the implementation (plugin-website, `references/entry.md`). If the brief changes later, variants and the approval are marked stale and kept.
