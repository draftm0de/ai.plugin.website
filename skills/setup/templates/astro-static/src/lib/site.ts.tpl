// Central site facts used for canonical URLs, social cards, sitemap and structured data.
export const SITE = 'https://{{domain}}';
export const SITE_NAME: string = {{title_json}};
export const LANG = 'en'; // language of the pages: <html lang>
export const LOCALE = 'en_US'; // Open Graph locale
export const DEFAULT_DESCRIPTION = `Website of ${SITE_NAME}.`;
export const DEFAULT_IMAGE = '/assets/og-default.png'; // 1200 x 630, a plain placeholder: replace it
export const THEME_COLOR = '#00529a'; // browser UI color, keep in step with --theme-brand
export const SITE_THEME: 'light' | 'dark' | 'auto' = 'auto'; // 'auto' follows the visitor's system; the others fix the scheme
export const LOGO: { src: string; width: number; height: number } | null = null; // image in the header instead of the site name

// Main navigation: id (matches `current` of the layout), link, label.
export const NAV = [{ id: 'home', href: '/', label: 'Home' }];
// Footer links (imprint, privacy policy ...); `lang` limits a link to the pages of that language.
// Language versions of the site (shown as a switch in the header when there are several).
export const LANGS: { lang: string; href: string; label: string }[] = [];
export const TO_TOP: string | null = null; // label of a round "back to top" button that appears after scrolling, null for none
export const FOOTER_TEXT: string[] = []; // lines of text in the footer (address, copyright)
export const FOOTER: { href: string; label: string; lang?: string }[] = [];
// Navigation per page language when the site has several languages (the layout falls back to NAV).
export const NAV_BY_LANG: Record<string, { id: string; href: string; label: string; children?: { href: string; label: string }[] }[]> = {};

export const absolute = (path: string) => new URL(path, SITE).href;

/** Keep descriptions within the length search engines show (about 160 characters). */
export const clip = (text: string, max = 160) => {
  const clean = text.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  return clean.length <= max ? clean : clean.slice(0, max - 1).replace(/\s+\S*$/, '') + '…';
};

/** Canonical path: /index.html is served as /; no trailing slash elsewhere (matches the sitemap and the redirects). */
export const canonicalPath = (pathname: string) => pathname.replace(/\/index\.html$/, '/').replace(/(.)\/$/, '$1');
