# CSS Style Guide

A small, dependency-free CSS foundation for static sites. No preprocessor, no framework.
It lives in `foundation/` and can be copied unchanged into any other project; only `theme.css` is edited per site.

## 1. Using it on a new site

1. Copy `src/styles/foundation/` and `src/styles/main.css` into the new project.
2. Create `theme.css` (see section 3) with your brand values.
3. Create an empty `site.css` for styles that only belong to that site.
4. Import `main.css` once in your base layout.
5. Build pages from the classes in sections 5 to 7. Do not write new CSS until nothing fits.

```
styles/
  main.css              entry point (imports in a fixed order)
  theme.css             per-site inputs          ← edit per site
  site.css              per-site extras          ← edit per site
  foundation/           reusable                 ← do not edit per site
    tokens.css          design tokens
    reset.css           minimal reset
    elements.css        default look of plain HTML
    layout.css          layout primitives
    components/*.css    one file per component
    utilities.css       tiny helper set
```

## 2. Principles

- **Tokens, not values.** Colors, sizes, spacing, radii and shadows come from `var(--…)` tokens. Never type a hex value or a pixel size in a component.
- **Two layers of variables.** `--theme-*` are inputs a site may set. All other tokens derive from them. Components read only the derived tokens.
- **Layers decide order, not specificity.** Cascade order is `reset → elements → layout → components → utilities → site`. A later layer always wins, so keep selectors flat (one class).
- **Layout is separate from components.** Layout primitives arrange, components decorate. Combine them in markup rather than adding page-specific CSS.
- **One component, one file, one block name** (BEM-light: `block`, `block__element`, `block--modifier`).
- **Dark mode comes for free.** Color tokens use `light-dark()`. Components never contain dark-mode rules.
- **Accessible by default.** Visible focus ring, 44px controls, reduced-motion support, skip link, WCAG AA contrast for text tokens. The binding rules for a site are in `rules/accessibility.md` (copy that file together with the foundation) and are checked by `scripts/a11y-check.mjs`.

## 3. Theme inputs (`theme.css`)

All optional, with neutral fallbacks.

| Input | Purpose | Example |
|---|---|---|
| `--theme-brand` | Primary action and link color | `#00529a` |
| `--theme-ink` | Text color and the base of all neutrals | `#0d2039` |
| `--theme-accent` | Warm glow in the page background | `#ffc97a` |
| `--theme-font-sans` | Body font stack | `Inter, system-ui, sans-serif` |
| `--theme-font-heading` | Heading font stack (default: the body font) | `"Open Sans", sans-serif` |
| `--theme-font-mono` | Code font stack | `ui-monospace, Menlo, monospace` |
| `--theme-text-xs`, `-sm`, `-base`, `-lg`, `-xl`, `-2xl`, `-3xl`, `-4xl` | Type scale (rem, or `clamp()` of rem) | `0.875rem` |
| `--theme-leading-normal` | Line height of body text | `1.7` |
| `--theme-container`, `--theme-gutter`, `--theme-section-space`, `--theme-header-height` | Column width, side padding, vertical band, header height | `60rem` |

Hover colors, tints, muted text, borders and tag colors are derived from these with `color-mix()`.
Check contrast again when you pick a new brand color: `--color-on-action` is white and `--color-text-muted` is 66% ink.

## 4. Tokens

| Group | Tokens |
|---|---|
| Color | `--color-bg`, `--color-text`, `--color-text-muted`, `--color-surface`, `--color-surface-sunken`, `--color-surface-solid`, `--color-border`, `--color-link`, `--color-action`, `--color-action-hover`, `--color-on-action`, `--color-tag-bg`, `--color-tag-text`, `--color-focus` |
| Type | `--font-sans`, `--font-mono`, sizes `--text-xs` (13px) · `--text-sm` (15px, UI text) · `--text-base` (17px, body) · `--text-lg` … `--text-4xl` (fluid), weights `--weight-regular/medium/bold`, `--leading-*`, `--tracking-*` |
| Space | `--space-1` (4px) … `--space-9` (96px) |
| Shape | `--radius-s/m/l/xl/full`, `--shadow-raised`, `--shadow-hover` |
| Layout | `--container`, `--gutter`, `--section-space`, `--control-height`, `--header-height` |
| Motion | `--duration`, `--easing` |

Rule of thumb: need a new value? Add a token first, then use it. Do not inline it.

The only breakpoint is **48rem** (narrow screens). Layout primitives (`grid`, `filter-bar`) adapt on their own without media queries.

## 5. Layout primitives (`layout.css`)

| Class | Use | Tuning variable |
|---|---|---|
| `.container` | Centered, width-limited column | `--container`, `--gutter` |
| `.section` | Vertical band | `--section-space` |
| `.stack` | Vertical rhythm between children | `--stack-space` |
| `.cluster` | Wrapping horizontal group (buttons, tags) | `--cluster-space`, `--cluster-justify`, `--cluster-align` |
| `.grid` | Responsive equal columns | `--grid-min`, `--grid-gap` |
| `.split` | Two columns, stacks when narrow | `--split-columns` |
| `.with-sidebar` | Fixed aside + flexible main | `--sidebar-width` |

Tune with a local variable, for example `<div class="grid" style="--grid-min: 12rem">`.

## 6. Components

| Component | Classes | Notes |
|---|---|---|
| Button | `.button`, `.button--primary` | On `<a>` or `<button>` |
| Card | `.card`, `.card--raised`, `.card--link`, `.card--media`, `.card__media`, `.card__body`, `.card__kicker`, `.card__title`, `.card__text` | `--raised` is the large page panel; `--media` puts a 16:9 image on top |
| Tags | `.tags` > `.tag`, `a.tag` | Labels; as link with `aria-current="page"` for the active one |
| Chip | `.chip` wrapping a checkbox | Filter toggle |
| Field | `.field`, `.field__label`, `.filter-bar` | Label above select, text input or chips |
| Site header | `.site-header`, `__bar`, `__brand`, `__toggle`, `.site-nav` | Nav script toggles `data-open` |
| Site footer | `.site-footer`, `__bar` | Sits at page bottom |
| Page header | `.page-header`, `__eyebrow`, `__title`, `__lead`, `__media`, `--display` | Top of every page; `__media` is a 16:9 image next to the text (inside `.split`), hidden on narrow screens |
| Feature | `.feature`, `__icon` | Icon + title + text |
| Meta list | `.meta-list` on `<dl>` | Label/value pairs |
| Record list | `.record-list`, `__head`, `.record`, `__title`, `__muted` | Table that turns into cards when narrow; columns via `--record-columns`; rows are top aligned and the whole row is clickable through one stretched title link (hover highlights the row and colors the title, no underline) |
| Prose | `.prose` | Wrap Markdown or CMS content |
| Article | `.article`, `__header`, `__aside`, `.toc` | Reading layout: content card at the full container width (the text keeps a readable measure) with sticky "on this page" navigation on the right, level with the top of the content card (the navigation is a sibling of the `.section` that holds the card); the side navigation is hidden below 64rem. **Rule:** use the navigation only for long texts, at least about 300 words and four `h2` sections; short pages (imprint, legal notices, short posts) simply omit it; the content card then takes the full width including the navigation area and its right part stays empty, so hero and card always have the same outer width. The script enforces the threshold and removes the navigation on shorter texts. Use on text pages; put the page header inside `.article` as `article__header` so hero text and card share the same left edge; keep lists and overviews full width |

## 7. Utilities

`.visually-hidden`, `.skip-link`, `.text-muted`, `.text-small`, `.measure`. Add a utility only when it is needed in several places.

## 8. Adding or changing things

**New component**
1. Check that no existing component plus layout primitive does the job.
2. Create `foundation/components/<name>.css`, start with a comment showing the markup.
3. Use tokens only, one class per rule, no dark-mode rules.
4. Register it in `foundation/index.css` with `layer(components)`.
5. Add a row to the table in section 6.

**Site-specific styling** goes in `site.css` (it is in the last layer and wins). If you need it on a second site, move it into the foundation.

**Do**: reuse tokens, keep selectors flat, test at 320px width and in dark mode.
**Don't**: hardcode colors or sizes, use `!important`, nest selectors deeper than two levels, style by element inside components, add a media query when `grid` or `split` can adapt.

## 9. Checklist before shipping a page

- Headings in order (one `h1`), images have `alt`.
- Keyboard: focus visible, nav works without a mouse.
- Looks right in light and dark mode and at 320px width.
- No new hardcoded values in CSS.
