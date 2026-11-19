#!/usr/bin/env node
// Accessibility audit of the built site (dist/). Rules: rules/accessibility.md
// Run: npm run build && npm run a11y:check   (or npm run check for SEO + accessibility)
// Static HTML checks only; keyboard, contrast and screen reader behaviour still need a manual check.
import fs from 'node:fs';
import path from 'node:path';

const DIST = path.resolve('dist');
const errors = [];

const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );
const pages = walk(DIST).filter((f) => f.endsWith('.html'));
const rel = (f) => '/' + path.relative(DIST, f).replaceAll(path.sep, '/');

const text = (html) =>
  html.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
const attr = (tag, name) => tag.match(new RegExp(`\\s${name}="([^"]*)"`))?.[1];

// Remove elements marked aria-hidden (repeat for nesting) so we only see what assistive tech sees.
const withoutHidden = (html) => {
  let prev;
  let out = html;
  do {
    prev = out;
    out = out.replace(/<(\w+)\b[^>]*\baria-hidden="true"[^>]*>(?:(?!<\1\b)[\s\S])*?<\/\1>/g, ' ');
  } while (out !== prev);
  return out;
};

const GLYPHS = /[←→↑↓↗↘↖↙▣✓✔✕✖☰»«]/;
const VAGUE = new Set(['click here', 'here', 'more', 'read more', 'link', 'this link', 'learn more']);

for (const file of pages) {
  const raw = fs.readFileSync(file, 'utf8');
  const name = rel(file);
  const err = (m) => errors.push(`${name}: ${m}`);

  const body = raw.match(/<body[\s\S]*<\/body>/)?.[0] ?? raw;
  const visible = withoutHidden(body.replace(/<script[\s\S]*?<\/script>/g, ' '));

  // Landmarks and skip link
  if ((visible.match(/<main[\s>]/g) ?? []).length !== 1) err('expected exactly one <main>');
  if (!/<header[\s>]/.test(visible)) err('missing <header>');
  if (!/<footer[\s>]/.test(visible)) err('missing <footer>');
  if (!/<nav[^>]*aria-label="/.test(visible)) err('<nav> without aria-label');
  if (!/class="skip-link" href="#main"/.test(body)) err('missing skip link');
  if (!/<main[^>]*id="main"/.test(body)) err('<main> without id="main"');

  // Heading levels must not skip
  let last = 0;
  for (const m of visible.matchAll(/<h([1-6])[\s>]/g)) {
    const level = Number(m[1]);
    if (last && level > last + 1) err(`heading level jumps from h${last} to h${level}`);
    last = level;
  }

  // Links: accessible name, vague text, same text to different targets
  const byName = new Map();
  for (const m of visible.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a>/g)) {
    const open = `<a ${m[1]}>`;
    const href = attr(open, 'href');
    const label = attr(open, 'aria-label') ?? text(m[2]);
    const hasImgAlt = /<img[^>]*\salt="[^"]+"/.test(m[2]);
    if (!label && !hasImgAlt) {
      err(`link without accessible name (href=${href})`);
      continue;
    }
    const key = label.toLowerCase();
    if (VAGUE.has(key.replace(/[→←»]/g, '').trim())) err(`vague link text "${label}" (href=${href})`);
    if (href && !href.startsWith('#')) byName.set(key, new Set([...(byName.get(key) ?? []), href]));
  }
  for (const [label, hrefs] of byName) {
    if (hrefs.size > 1) err(`same link text "${label}" leads to different targets: ${[...hrefs].slice(0, 3).join(', ')}`);
  }

  // Buttons need a name
  for (const m of visible.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
    if (!attr(`<button ${m[1]}>`, 'aria-label') && !text(m[2])) err('button without accessible name');
  }

  // Decorative symbols must be hidden from assistive technology (buttons with aria-label are fine)
  const readable = text(
    visible
      .replace(/<button\b[^>]*aria-label="[^"]*"[^>]*>[\s\S]*?<\/button>/g, ' ')
      .replace(/<a\b[^>]*aria-label="[^"]*"[^>]*>[\s\S]*?<\/a>/g, ' ')
      .replace(/<(code|pre)\b[\s\S]*?<\/\1>/g, ' '),
  );
  const glyph = readable.match(GLYPHS);
  if (glyph) err(`symbol "${glyph[0]}" is read aloud; wrap it in aria-hidden="true"`);

  // Images
  for (const img of body.match(/<img\b[^>]*>/g) ?? []) {
    if (!/\salt="/.test(img)) err(`image without alt: ${img.slice(0, 70)}`);
    if (!/\swidth="/.test(img) || !/\sheight="/.test(img)) err(`image without width/height: ${img.slice(0, 70)}`);
  }

  // Tables need header cells
  for (const m of body.matchAll(/<table\b[\s\S]*?<\/table>/g)) {
    if (!/<th[\s>]/.test(m[0])) err('table without <th> header cells');
  }

  // Form controls need a label
  for (const m of body.matchAll(/<(input|select|textarea)\b([^>]*)>/g)) {
    const tag = m[0];
    if (attr(tag, 'type') === 'hidden') continue;
    const before = body.slice(0, m.index);
    const insideLabel = before.lastIndexOf('<label') > before.lastIndexOf('</label>');
    const id = attr(tag, 'id');
    const labelled =
      insideLabel ||
      attr(tag, 'aria-label') ||
      attr(tag, 'aria-labelledby') ||
      (id && new RegExp(`<label[^>]*for="${id}"`).test(body));
    if (!labelled) err(`form control without label: ${tag.slice(0, 70)}`);
  }

  // Dynamic lists need a status region
  if (/data-(repository|blog)-list/.test(body) && !/role="status"/.test(body)) err('filterable list without role="status" region');
}

// Font sizes must be relative so the reader's own text-size setting works (rule 24).
for (const css of walk(DIST).filter((f) => f.endsWith('.css'))) {
  const content = fs.readFileSync(css, 'utf8');
  for (const m of content.matchAll(/font-size:\s*([0-9.]+(?:px|pt))/g)) {
    errors.push(`${rel(css)}: font-size in ${m[1]} (use rem)`);
  }
  for (const m of content.matchAll(/(?:html|:root)\s*\{[^}]*font-size:\s*([0-9.]+(?:px|pt))/g)) {
    errors.push(`${rel(css)}: root font-size ${m[1]} overrides the browser setting`);
  }
}

console.log(`Checked ${pages.length} pages for accessibility.`);
if (errors.length) {
  console.log(`\nErrors (${errors.length}):\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log('\nNo errors. (Contrast, keyboard use and screen reader output still need a manual check.)');
