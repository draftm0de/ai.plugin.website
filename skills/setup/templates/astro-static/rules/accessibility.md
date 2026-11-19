# Accessibility rules (binding)

**These rules are mandatory for the whole site.** Every page, section, component, blog post and image, whoever creates it (a person or an AI agent), must follow them. There are no exceptions without the site owner's explicit approval, and any approved exception is written into section 9.

Goal: the site works for people who use screen readers, read-aloud tools, a keyboard only, zoom, high contrast or reader modes. Standard: WCAG 2.2 level AA.

Enforcement: `npm run build && npm run check` (runs `scripts/seo-check.mjs` and `scripts/a11y-check.mjs`) must report no errors before work is called done and before every release. The script checks what a machine can check (sections marked **[auto]**); the rest is the author's responsibility.

## 1. Structure

1. **Landmarks [auto]:** every page has one `main` (id `main`), a `header`, a `nav` with an `aria-label`, and a `footer`. The "Skip to content" link stays first in the body.
2. **Headings [auto]:** exactly one `h1`; levels never skip (`h2` follows `h1`, `h3` follows `h2`). Headings describe the content; do not pick a level for its size.
3. **Language [auto]:** `<html lang>` is the site's language (`LANG` in `src/lib/site.ts`). Mark passages in another language with `lang="…"`.
4. **Reading order:** the HTML order is the reading order. Layout (CSS grid, sticky parts) must not require a different order. Side navigation (`aside`) comes after the main content.

## 2. Text alternatives and decoration

5. **Informative images:** `alt` text that says what the image conveys (not "image of").
6. **Decorative images and symbols [auto]:** use `alt=""` for images that only decorate (hero images in page headers, background art). Icons, glyphs and arrows such as ← → ↗ ▣ ✓ ☰ are decorative: wrap them in `aria-hidden="true"`, or give the control an `aria-label`. A symbol must never be read as "right arrow".
7. **Image size [auto]:** images have `width` and `height`.

## 3. Links and buttons

8. **Meaningful link text [auto]:** the link text alone says where it goes. Never "click here", "here", "more" or a bare "Read →". Links with the same text must lead to the same place; if several links would share a text (lists, cards), the text must include the item name.
9. **No duplicate links:** a row, card or list item has one link. To make the whole row clickable, stretch the title link over the row (`.record__title::after`); do not add a second "View →" link. Keyboard focus is shown on the whole row.
10. **Accessible names [auto]:** every link and button has a name (text or `aria-label`).
11. **External links** open in a new tab only through the global script (`rel="noopener noreferrer"`); the link text names the destination.

## 4. Lists, tables and data

12. **Meaning must not live in position or style alone:** each value in a row, card or list needs its label for assistive technology. If the label is not visible, add it as visually hidden text (`<span class="visually-hidden">Category: </span>`).
13. **Tables [auto]:** use `<table>` only for tabular data, with `<th>` header cells. Wide tables scroll in their own container.
14. **Dates:** use `<time datetime="YYYY-MM-DD">` for every date.

## 5. Forms, filters and dynamic content

15. **Labels [auto]:** every input, select and checkbox has a visible label (wrapping `<label>` or `for`/`id`).
16. **Groups:** related controls (filter chips) sit in a `role="group"` with `aria-labelledby` pointing to the group label.
17. **Announce changes:** when content changes without a page load (filtering, sorting), update a `role="status"` region (visually hidden) with the result, for example "3 of 9 items shown". Do not announce on first load.
18. **No content only with JavaScript:** content and links must exist in the HTML. Scripts may enhance (filter, navigation, table of contents), not create essential content.

## 6. Visual design

19. **Contrast:** normal text at least 4.5:1, large text (24 px, or 19 px bold) and UI components such as borders of inputs and focus rings at least 3:1, in light and dark mode. Re-check whenever `theme.css` or the color tokens change, and whenever text is placed over an image or artwork (measure the worst case at any scroll position). Use only tokens for colors.
20. **Not by color alone:** state and meaning also need text, shape or position (the active menu item has an underline, not only another color).
21. **Focus:** a visible focus ring on every interactive element (the foundation provides it; do not remove `outline`).
22. **Keyboard:** everything works with the keyboard alone, in a logical tab order, without traps. Sticky or hidden parts must not cover focused elements (`scroll-margin` on anchored headings).
23. **Targets and zoom:** controls at least 44 px high (`--control-height`); no horizontal page scroll at 320 px width or 200% zoom; text can be enlarged without loss. Long names without spaces must wrap; the foundation sets `overflow-wrap: anywhere` on headings and record titles, keep it for any new text element that can hold such names.
24. **Font sizes in `rem` [auto]:** all font sizes are relative (`rem`, `em`, `%`, or `clamp()` built from `rem`); never `px` or `pt`. Never set the root `font-size` in `px`; leave it at the browser default so the reader's own text-size setting works. No custom "A A A" size switchers; the browser already offers zoom and text size. At 200% zoom and at 200% text size nothing may overlap, be cut off, or need sideways scrolling (the sticky header and "On this page" navigation included).
25. **Motion and system preferences:** respect `prefers-reduced-motion` (the foundation does). Respect `prefers-contrast: more` (artwork off, solid surfaces, stronger borders) and `forced-colors: active` (no gradient-only meaning; the system colors decide). Printing gives a light, plain page without navigation and artwork (`src/styles/print.css`). No autoplay, no flashing.

## 7. Content authoring (blog posts, copy)

26. Write descriptive link text; no bare URLs in running text.
27. Start with the answer, use short paragraphs and real headings; no heading levels chosen for looks. Plain language; explain abbreviations once.
28. Do not use text in images. If an image carries information, state it in the text or in `alt`.
29. Tables only for data, with a header row; keep them under about seven columns.
30. Quotes use `blockquote`; translated quotes are marked "(translated)".

## 8. Checklist for every new page, section or post

- [ ] One `h1`, no skipped levels, landmarks present
- [ ] Images: informative → alt, decorative → `alt=""`, with width and height
- [ ] Symbols and arrows hidden from assistive technology
- [ ] Link texts unique and meaningful, no duplicate links
- [ ] Each value has a label for assistive technology; dates in `<time>`
- [ ] Forms and filters labelled, grouped and announced
- [ ] Font sizes in `rem` only; contrast, focus, keyboard, 200% zoom and 320 px width checked (preview, light and dark)
- [ ] `npm run build && npm run check` reports no errors

## 9. Approved exceptions

None.
