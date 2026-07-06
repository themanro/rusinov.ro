# rusinov.ro — personal site ("the pile")

Single-page personal site for Roman Rusinov, served by GitHub Pages at
https://rusinov.ro. One column, system mono, an undated pile of made things.

## How it works
- **`content/site.md` is the entire site content** — sections `## hero`, `## now`,
  `## pile`. Pile entries: `### caption` + optional `image:` or `video:` (YouTube) line;
  no media line = plain text entry. Extra options per entry: `pinned: yes` (floats to
  top, max 3) and `circa: YYYY` (renders a dim "(circa YYYY)" tag once 10+ years old).
- `tools/build.py` renders site.md into `tools/template.html` → `index.html`.
  Stdlib only. Run `python3 tools/build.py` after editing, or just push —
  the GitHub Action (`.github/workflows/build-deploy.yml`) rebuilds and deploys
  every push to main.
- **Never hand-edit index.html** — it's generated, the next build overwrites it.
- Layout/CSS/meta/footer/contact links live in `tools/template.html`.
- Email is obfuscated: `data-mail` anchor + footer script. Never put the plain
  address in markup or markdown.

## Process
- **Always verify in the local preview before pushing** (Roman's standing rule):
  `python3 tools/build.py`, then check the `rusinov-site` preview server (port 8642) —
  images load, layout sane — before commit/push.

## Content conventions
- The pile is undated and order-curated, not chronological. New things usually
  go near the top. Keep captions one line, lowercase-ish, dry.
- Images: `/uploads/` for new ones (Roman drag-drops on GitHub web — any size/HEIC;
  `tools/process_uploads.py` runs in CI: resize to 1600px, HEIC→JPEG, EXIF/GPS
  stripped). Legacy art lives in `/assets/img/`. Note: originals persist in git
  history — truly sensitive photos should be stripped before upload.
- Build is content-fault-tolerant: bad entries render as text + warning, never a dead
  deploy. CI opens a GitHub issue if a build fails outright. 404.html is the branded
  not-found page.
- Roman self-edits site.md via GitHub web; expect bot commits
  ("Rebuild site from content/site.md") — always `git pull --rebase` before pushing.

## History
The previous Webflow-replica site (28 pages) was retired June 2026 — it lives in
git history before commit 0f3451b. Original full-res assets: `~/rusinov-archive/`.
