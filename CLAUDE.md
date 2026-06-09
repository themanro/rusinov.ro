# rusinov.ro — personal site

Single-page personal site for Roman Rusinov, hosted on GitHub Pages.

## Rules
- Keep it ONE file: `index.html`. No build step, no frameworks, no JS, no external assets.
- Style stays minimal and 90s: system mono font, default-ish colors, dashed `<hr>` dividers, the small inline `<style>` block already in the file. Don't add CSS beyond what's there.
- New content goes into the existing sections (Work, Clients, About, Elsewhere) or a new `<h2>` section in the same plain style.
- Images: avoid unless explicitly asked; if added, put them in `img/` and keep them small.

## Deploying
Pages serves the `main` branch root. To publish any change:

```
git add -A && git commit -m "<message>" && git push
```

The live site updates within a minute or two of pushing.
