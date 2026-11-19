{
  "name": "{{name}}",
  "type": "module",
  "version": "0.0.1",
  "engines": { "node": ">=22.23.4" },
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "astro": "astro",
    "seo:check": "node scripts/seo-check.mjs",
    "a11y:check": "node scripts/a11y-check.mjs",
    "check": "node scripts/seo-check.mjs && node scripts/a11y-check.mjs"
  },
  "dependencies": { "astro": "^7.4.10" }
}
