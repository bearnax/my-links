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
  2. `Items`: `Title`, `Section`, `Order`, `Search`, `Primary URL & Label`, `Link1-3 URLs & Labels`.
- **CRITICAL - Never Invent Placeholder IDs**:
  - `data/airtable-schema.json` stores live Airtable table and field IDs (e.g. `tblrcM5Gwd4yuVupP`, `fldBJeSAj8ZC9tDTW`).
  - **NEVER** write fabricated IDs like `tblItems000000001` or `fldItemTitle00001`. Fake IDs cause Airtable API calls to fail with 403 `INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND`.
  - To discover or update live IDs, use the Airtable Meta API (`/v0/meta/bases/{baseId}/tables`) or run `python3 scripts/doctor.py --online`.

---

## 3. UI Design System: Neumorphic Guidelines

The site follows **Hybrid Neumorphism** ("The Molded Sheet"):
- **The Single Material**: The background and component surfaces share the exact same base color (`--bg`). Depth and differentiation are created entirely through dual directional shadows (top-left light highlight + bottom-right dark shadow).
- **Fixed Top-Left Sun**:
  - Resting extrusion: `-4px -4px 10px var(--shadow-light), 4px 4px 10px var(--shadow-dark)`
  - Active / pressed state: `inset 2px 2px 4px var(--shadow-dark), inset -2px -2px 4px var(--shadow-light)`
- **Surface Tension**: Corner radii are tightly controlled between `12px` and `18px` (`999px` for pills/dock). Avoid sharp corners (<12px) and puffy claymorphism (>24px).
- **Interactive States**:
  - **Only interactive elements** (buttons, link pills, toggles) receive hover and active states.
  - **Item rows (`.item-card`) and titles do NOT have hover states.** They are structural surfaces with contrast, not clickable buttons.
- **Link Pills**:
  - Compact pills sitting inline next to the title.
  - Filled with `var(--section-accent)`, borderless (`border: none`), with bold white text.
  - All outbound links must have `target="_blank" rel="noopener noreferrer"`.
- **Floating Dock**:
  - Pinned at bottom center: contains only **Search** (opens popup modal, hotkey `/`) and **Light/Dark theme toggle**.
  - No footer palette switcher.

---

## 4. Commands & Verification

Always run tests before completing work:

```sh
npm run sync    # Pulls fresh links from Airtable (reads .env or AIRTABLE_TOKEN)
npm run build   # Generates _site/
npm run test    # Runs build + python3 scripts/doctor.py
```
