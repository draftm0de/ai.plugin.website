# SEO rules

Goal: every page is crawlable, understandable and shareable. The rules apply to all new and changed pages.
Verify with `npm run build && npm run check` (the `optimize` skill of the Website plugin). Together with `rules/accessibility.md` these rules are binding.

## 1. What is built in (do not remove)

| Area | Where | What it does |
|---|---|---|
| Site facts | `src/lib/site.ts` | Site name, language, default description and share image, helpers |
| Head tags | `src/layouts/BaseLayout.astro` | `<title>`, description, canonical, robots, Open Graph, Twitter card, JSON-LD slot |
| Sitemap | `src/pages/sitemap.xml.ts` | The list of indexable pages (add every new page there) |
| robots.txt | `src/pages/robots.txt.ts` | Allows everything, points to the sitemap |
| 404 | `src/pages/404.astro` | Helpful, `noindex`, built into `dist/`; how unknown URLs reach it is decided by the serving setup, not by this site |
| Redirects | serving setup | Redirects from old URLs to the canonical ones; this static site carries no serving files, the place for redirects is defined with the publish path |

## 2. Per page (required)

- **Title:** unique, 30 to 60 characters, main topic first. Pass `title` to `BaseLayout`.
- **Description:** unique, 120 to 160 characters, a real sentence that makes someone click. No keyword lists. Pass `description`.
- **One `h1`**, matching the title's topic. Headings in order (no skipped levels).
- **Canonical:** automatic. Never link to a URL that redirects.
- **Indexing:** pages are indexable by default. Use `noindex` only for legal and utility pages (imprint, privacy, 404).
- **Internal links:** every new page is linked from at least one other page with descriptive link text. No "click here".
- **Images:** `alt` text that describes the image (empty `alt=""` for decoration), `width` and `height` set, `loading="lazy"` below the fold. Prefer WebP or SVG, keep files under 200 KB.
- **Language:** the `<html lang>` of the page is the site's language (`LANG` in `src/lib/site.ts`).

## 3. URLs

- Lowercase, hyphens, no dates in the path, short and readable.
- Never change a published URL. If you must, record a 301 redirect for the serving setup (not yet defined for static sites) and update the sitemap. This also applies to the URLs of a site imported from elsewhere.
- New section: add it to `src/pages/sitemap.xml.ts`.

## 4. Social cards

- Default share image: `public/assets/og-default.png` (1200 x 630). It is a plain placeholder; replace it with the site's own image. Pages can pass `image` (also 1200 x 630, PNG or JPG; WebP is not shown by every network).

## 5. Performance (ranking factor)

- Keep pages light: no web fonts or third-party scripts unless needed; JavaScript only for progressive enhancement.
- Cache static assets and gzip are the job of the serving setup.
- Target Lighthouse (mobile): Performance, Accessibility, Best Practices and SEO all at 95 or higher. Check after layout changes.
- Avoid layout shift: always set image dimensions.

## 6. Operations (outside the code)

- Serve one canonical host and redirect HTTP to HTTPS (serving setup).
- Register the site in Google Search Console and Bing Webmaster Tools, submit `sitemap.xml`, and check Coverage and Core Web Vitals after each release.
- Legal pages (imprint, privacy policy) are required in many countries; their text comes from the owner, never from the model.
- Analytics only if privacy-friendly and self-hosted; no cookie banner is needed without tracking.

## 7. Checklist before publishing

- [ ] `npm run build && npm run check` reports no errors
- [ ] Title and description are unique and within length
- [ ] One `h1`, logical headings
- [ ] Linked from another page, listed in the sitemap, URL is final
- [ ] Images have alt text and dimensions
