# {{title}} (`{{name}}`)

{{domain_line}}

Static website built with Astro. It is one site of this repository (`{{path}}`); the registry entry is in `.project/specs/zyris-website.json`.

## Commands
Run inside this folder:
- `npm install` once
- `npm run dev` for the local preview (port {{port}}; or use the `preview` skill of the Website plugin)
- `npm run build` writes the static site into `dist/`
- `npm run check` audits SEO and accessibility of `dist/` (run after build)
- After any page, component or content change: `npm run build && npm run check` must report no errors.

## Binding rules
- **Brand:** if the repository has `.project/brand/` (voice, colors, image style for all channels), read it before writing any text; the rules below apply on top.
- **Accessibility:** `rules/accessibility.md` applies to every page, section, component and image, whoever creates it. Exceptions only with the owner's explicit approval, recorded in that file.
- **SEO:** `rules/seo.md` (audit with the `optimize` skill of the Website plugin). Every page passes a unique `title` and `description` to `BaseLayout`.
- **Style:** `src/styles/STYLEGUIDE.md`. Use foundation classes and tokens only; brand values live in `src/styles/theme.css`, site-only styles in `src/styles/site.css`. Do not edit `src/styles/foundation/` for site-specific needs.

## Working agreement
- Claude and Codex work on this repository under the same project rules; the owner gives decisions in the chat.
- Change only files in this folder when working on this site.
- Keep published URLs stable; a URL that must change needs a redirect, which belongs to the serving setup (not part of this static site).
- New pages: add every indexable page to `src/pages/sitemap.xml.ts`.
- Do not commit, push or publish without the owner's go-ahead. Publishing of static sites is not implemented yet.
