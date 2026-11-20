#!/usr/bin/env node
// SEO audit of the built site (dist/). Run: npm run build && npm run seo:check
// Exit code 1 when any error is found; warnings do not fail.
import fs from 'node:fs';
import path from 'node:path';

const DIST = path.resolve('dist');
// The site address comes from astro.config.mjs (the single source of truth). No `site` entry means the domain is not decided yet:
// then no page may carry an absolute address and the checks that need one are skipped (and said so), never failed.
const configText = fs.readFileSync(path.resolve('astro.config.mjs'), 'utf8').replace(/\/\*[\s\S]*?\*\/|(^|[^:])\/\/.*$/gm, '$1');
const SITE = configText.match(/\bsite:\s*['"]([^'"]+)['"]/)?.[1]?.replace(/\/$/, '');
const errors = [];
const warnings = [];
if (!SITE) warnings.push('no domain configured (astro.config.mjs has no site): canonical, social and sitemap address checks are skipped');

const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );

const files = walk(DIST);
const pages = files.filter((f) => f.endsWith('.html'));
const rel = (f) => '/' + path.relative(DIST, f).replaceAll(path.sep, '/');
const attr = (html, re) => html.match(re)?.[1]?.trim();

const titles = new Map();
const descriptions = new Map();
const indexable = [];

for (const file of pages) {
  const html = fs.readFileSync(file, 'utf8');
  const name = rel(file);
  const err = (m) => errors.push(`${name}: ${m}`);
  const warn = (m) => warnings.push(`${name}: ${m}`);

  const noindex = /<meta name="robots" content="[^"]*noindex/i.test(html);
  if (!noindex) indexable.push(name);

  const title = attr(html, /<title>([^<]*)<\/title>/);
  if (!title) err('missing <title>');
  else {
    if (title.length > 65) warn(`title is ${title.length} chars (aim for 60 or less)`);
    if (title.length < 15) warn(`title is very short (${title.length})`);
    if (!noindex) titles.set(title, [...(titles.get(title) ?? []), name]);   // pages kept out of the index may repeat
  }

  const desc = attr(html, /<meta name="description" content="([^"]*)"/);
  if (!desc) err('missing meta description');
  else {
    if (desc.length > 160) warn(`description is ${desc.length} chars (max 160)`);
    if (desc.length < 70) warn(`description is short (${desc.length}, aim for 120 to 160)`);
    if (!noindex) descriptions.set(desc, [...(descriptions.get(desc) ?? []), name]);
  }

  const canonical = attr(html, /<link rel="canonical" href="([^"]*)"/);
  if (!SITE) {
    if (canonical) err(`canonical link without a configured domain: ${canonical}`);
  } else if (!canonical) err('missing canonical link');
  else if (!canonical.startsWith(SITE + '/')) err(`canonical is not on ${SITE}: ${canonical}`);

  const h1 = (html.match(/<h1[\s>]/g) ?? []).length;
  if (h1 !== 1) err(`expected exactly one <h1>, found ${h1}`);

  if (!/<html lang="/.test(html)) err('missing lang on <html>');
  if (!/name="viewport"/.test(html)) err('missing viewport meta');

  for (const p of ['og:title', 'og:description', 'og:url', 'og:image', 'og:type']) {
    if (!html.includes(`property="${p}"`)) err(`missing ${p}`);
  }
  if (!html.includes('name="twitter:card"')) err('missing twitter:card');

  for (const img of html.match(/<img\b[^>]*>/g) ?? []) {
    if (!/\balt="/.test(img)) err(`image without alt: ${img.slice(0, 80)}`);
    if (!/\bwidth="/.test(img) || !/\bheight="/.test(img)) warn(`image without width/height (layout shift): ${img.slice(0, 80)}`);
  }

  for (const block of html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)) {
    try {
      JSON.parse(block[1]);
    } catch {
      err('invalid JSON-LD');
    }
  }
}

for (const [value, list] of [...titles, ...descriptions]) {
  if (list.length > 1) errors.push(`duplicate title/description "${value.slice(0, 50)}" on: ${list.join(', ')}`);
}

// robots.txt, sitemap, 404
const need = (f) => {
  if (!fs.existsSync(path.join(DIST, f))) errors.push(`missing /${f}`);
};
['robots.txt', 'sitemap.xml', '404.html'].forEach(need);

if (SITE && fs.existsSync(path.join(DIST, 'sitemap.xml'))) {
  const xml = fs.readFileSync(path.join(DIST, 'sitemap.xml'), 'utf8');
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  for (const loc of locs) {
    const p = new URL(loc).pathname;
    const candidates = p.endsWith('/') ? [p.slice(0, -1) + '.html', p + 'index.html'] : [p, p + '.html', p + '/index.html'];
    const file = p === '/' ? ['/index.html'] : candidates;
    if (!file.some((c) => fs.existsSync(path.join(DIST, c)))) errors.push(`sitemap URL has no page: ${loc}`);
  }
  const listed = new Set(locs.map((l) => new URL(l).pathname));
  for (const name of indexable) {
    if (name === '/404.html') continue;
    const pathname = name === '/index.html' ? '/' : name.endsWith('/index.html') ? name.slice(0, -'/index.html'.length) : name;
    if (!listed.has(pathname)) warnings.push(`${name}: indexable page is not in the sitemap`);
  }
}

console.log(`Checked ${pages.length} pages.`);
if (warnings.length) console.log(`\nWarnings (${warnings.length}):\n- ${warnings.join('\n- ')}`);
if (errors.length) {
  console.log(`\nErrors (${errors.length}):\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log('\nNo errors.');
