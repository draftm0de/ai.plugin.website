import { absolute } from '../lib/site';

export const GET = () =>
  new Response(`User-agent: *\nAllow: /\n\nSitemap: ${absolute('/sitemap.xml')}\n`, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
