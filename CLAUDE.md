# rusinov.ro — personal site

Roman Rusinov's personal site: a self-hosted replica of his original Webflow site
(mirrored from rusinov.webflow.io in June 2026), served by GitHub Pages.

## Structure
- `index.html` — homepage
- `work/<slug>/index.html` — 27 project pages
- `assets/css/` — single Webflow-generated stylesheet (badge-hiding rule appended at the end)
- `assets/js/` — self-hosted Webflow animation engine (`webflow.schunk.*.js`) + countUp.js
- `assets/img/`, `assets/fonts/` — all media, fully local
- Original full-res source images also live outside the repo in `~/rusinov-archive/work/`

## Rules
- This is generated Webflow markup — edit content (text, links, images) in place, but
  don't restructure the class soup or touch `data-w-id` attributes (they drive animations).
- Email is obfuscated: anchors use `href="#" data-mail` and a footer script assembles
  the real mailto client-side. Never put `hello@` + domain as plain text in markup.
- Typekit was stripped; fonts currently fall back to system stacks. If adding Google Fonts,
  add the `<link>` to all 28 pages (`grep -rl '</head>' --include=index.html`).
- Dead externals (Cushion availability widget, old Google Analytics) were removed — don't re-add.
- The `.w-webflow-badge` CSS rule at the end of the stylesheet hides the staging badge; keep it.

## Deploying
Pages serves the `main` branch root; custom domain rusinov.ro (CNAME file), HTTPS enforced.

```
git add -A && git commit -m "<message>" && git push
```

Live within a minute or two of pushing.

## Bulk edits
For changes across all 28 pages (nav, footer, head tags), script it:
`find . -name index.html` + python/sed, then spot-check in the `rusinov-site` preview server.
