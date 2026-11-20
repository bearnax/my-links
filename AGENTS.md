# Agent Guidelines: my-links

This file outlines the rules, architecture, and design system for any autonomous or headless agent (such as Antigravity, Cursor, or Escapement) operating in this repository.

---

## 1. Architecture & Source of Truth

- **Source of Truth**: The live Airtable base **Links CMS** (`app1bBKfPU7TpXAgm`), configured in [`data/airtable-schema.json`](data/airtable-schema.json).
- **The Seam**: [`data/links.json`](data/links.json) is generated from Airtable by `scripts/sync-links.py`. Do **not** hand-edit `data/links.json`.
- **Site Generator**: [Eleventy (11ty)](https://www.11ty.dev/) builds static HTML into `_site/` at build time. No client-side framework is used.
- **Deploys**: GitHub Pages deploys via GitHub Actions (`.github/workflows/deploy.yml`) on pushes to `main`.

---

## 2. Airtable Schema Rules

- **The Two-Table Model**:
  1. `Sections`: `Title`, `Sub Title` (optional), `slug`, `Accent Color` (`<name> #<hex>` or `#<hex>`), `Order`, `Open`.
  2. `Items`: `Title`, `Section`, `Order`, `Search`, `Primary URL & Label`, `Link1-3 URLs & Labels`, `Description`, `Presentation`, `Image URL`, `Is Project`, `Favorite`.
- **CRITICAL - Never Invent Placeholder IDs**:
  - `data/airtable-schema.json` stores live Airtable table and field IDs (e.g. `tblrcM5Gwd4yuVupP`, `fldBJeSAj8ZC9tDTW`).
  - **NEVER** write fabricated IDs like `tblItems000000001` or `fldItemTitle00001`. Fake IDs cause Airtable API calls to fail with 403 `INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND`.
  - To discover or update live IDs, use the Airtable Meta API (`/v0/meta/bases/{baseId}/tables`) or run `python3 scripts/init-base.py --refresh`.

---

## 3. UI Design System

- Keep the stacked title, collection stats, light and dark themes, and section accents.
- Give Favorites clear, compact pill buttons. Use a local icon where it helps identify the service.
- Use tappable rows for single destinations and separate buttons for multiple destinations.
- Use roomier cards for featured projects, with optional descriptions and public image URLs.
- Use section subtitles where available and let accordions retain the visitor's state.
- Keep search and the theme toggle in the floating dock.
- Outbound links use `target="_blank" rel="noopener noreferrer"`.

## 4. Commands & Verification

Always run tests before completing work:

```sh
npm run sync    # Pulls fresh links from Airtable (reads .env or AIRTABLE_TOKEN)
npm run build   # Generates _site/
npm run test    # Runs build + python3 scripts/doctor.py
```
