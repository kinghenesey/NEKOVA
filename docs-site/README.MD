# NEKOVA Docs Site

A static documentation site for NEKOVA. Content is plain markdown;
the design (theme, animations, layout) lives entirely in
`templates/` and `static/`, separate from content, so updating a
page never means touching HTML or CSS.

## Requirements

```bash
pip install jinja2 markdown pyyaml python-frontmatter
```

## Building the site

```bash
python build.py
```

This regenerates everything into `output/` — a plain folder of
HTML/CSS/JS you can open directly, upload to any static host
(GitHub Pages, Netlify, Vercel, an S3 bucket, anywhere), or serve
yourself.

To build and preview locally in one step:

```bash
python build.py --serve
```

then open http://localhost:8000

## Editing an existing page

Every page is a markdown file under `content/`. Find it, edit it,
save it, run `python build.py` again. That's the entire workflow.

```
content/
├── nav.yaml                    ← sidebar structure — the only file
│                                  you need to touch to add/remove/
│                                  reorder pages
├── getting-started/
│   ├── installation.md
│   ├── quickstart.md
│   └── project-structure.md
├── syntax/
│   ├── variables.md
│   ├── control-flow.md
│   └── ...
├── ai-native/
├── classes/
├── advanced/
└── reference/
```

Each markdown file starts with frontmatter:

```markdown
---
title: Page Title
lede: One-sentence summary shown under the title.
---

## A heading

Regular markdown content. Fenced code blocks tagged ```nekova get
NEKOVA-specific syntax highlighting automatically.
```

**Watch out for YAML-sensitive characters at the very start of a
`lede:` value** — `|`, `?`, `>`, `&`, `*`, `!`, `%`, `@`, and `-`
all mean something special to YAML if they're the first character.
If your lede needs to start with one, quote the whole value:
`lede: "?. does the thing"`.

## Adding a brand-new page

1. Write the markdown file under the right `content/` subfolder.
2. Add one entry to `content/nav.yaml`:
   ```yaml
   - title: My New Page
     file: category/my-new-page.md
   ```
3. Run `python build.py`.

The sidebar, the prev/next pager at the bottom of every page, and
the page's own table of contents (from its `##`/`###` headings) are
all generated automatically — you never edit those by hand.

## Editing the design

- `static/css/theme.css` — colors, fonts, spacing, and the shared
  top bar / footer. Change a value here and it updates everywhere.
- `static/css/docs.css` — the documentation page layout (sidebar,
  content column, table of contents).
- `static/css/landing.css` — the landing page only.
- `static/js/animations.js` — scroll reveal, the 3D card tilt, the
  hero canvas, copy-to-clipboard buttons, active-link tracking.
- `templates/base.html` — the shared `<head>`, top nav, and footer
  every page inherits.
- `templates/page.html` — the documentation page layout.
- `templates/home.html` — the landing page content and structure.

## Brand colors

Pulled directly from the NEKOVA VS Code theme — green, white, and
grey. Red and amber exist only as `--nk-error` / `--nk-warning` and
are used nowhere decoratively, matching NEKOVA's own rule that those
colors are reserved for actual errors and warnings.

## Deploying

`output/` is a complete, self-contained static site. Point any
static host at it, or copy it to a web server's document root.
There's no backend, database, or build step required at request
time — everything is pre-rendered.

### GitHub Pages (automated)

A workflow at `.github/workflows/deploy-docs.yml` (repo root, not
inside this folder) rebuilds and republishes the site automatically
on every push to `main` that touches `docs-site/`. One-time setup:

1. In the GitHub repo: **Settings → Pages → Source** → select
   **"GitHub Actions"** (not "Deploy from a branch").
2. Push this folder to `main` under `docs-site/` at the repo root.
3. Check the **Actions** tab — the "Deploy NEKOVA Docs" workflow
   runs automatically. First run takes a minute or two.
4. Your site is live at `https://<username>.github.io/<repo>/`
   (GitHub shows the exact URL in Settings → Pages once it's live).

No further steps after that — edit a markdown file, commit, push,
and the live site updates itself within a couple of minutes.

To trigger a rebuild without a content change (e.g. after editing
`nav.yaml` design tokens), use the **Run workflow** button on the
"Deploy NEKOVA Docs" workflow in the Actions tab — the workflow
also supports manual triggering.