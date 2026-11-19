import { absolute } from '../lib/site';

// Every indexable page belongs here. Noindex pages (404, legal pages) are left out on purpose.
const paths: { path: string; lastmod?: string }[] = [{ path: '/' }];

export function GET() {
  const urls = paths
    .map((e) => `  <url><loc>${absolute(e.path)}</loc>${e.lastmod ? `<lastmod>${e.lastmod}</lastmod>` : ''}</url>`)
    .join('\n');
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
    { headers: { 'Content-Type': 'application/xml; charset=utf-8' } },
  );
}
