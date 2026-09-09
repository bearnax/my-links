---
name: handle-the-data
description: Sync the links/projects/people data on the site from the Airtable source of truth. Use when asked to sync, update, pull, or refresh the site's links, or when the human says they've edited the Links CMS Airtable base and want it reflected on the site.
---

# Handle the Data

`data/links.json` drives everything rendered on the page. It is a **generated
file** — the source of truth is the **Links CMS** Airtable base:

**Base**: read the `baseId` out of `data/airtable-schema.json` — do not rely on
an ID memorised from another checkout. This repo is the template for sibling
link sites, each with its own base, so a hardcoded ID here would sync the wrong
site's data. (`python3 scripts/doctor.py` fails loudly if the schema still
points at the base a fork was copied from.)

`data/links.json` is deliberately kept as the seam between Airtable and the
site. The Eleventy build reads the committed file, never Airtable directly, so
a build works offline and every data change lands as a reviewable diff.

There's also a code-only path: the `.github/workflows/sync-links.yml` GitHub
Action does the same pull/validate/diff/PR sequence with no LLM involved
(`workflow_dispatch`, plus a weekday schedule). Use this skill when a human is
driving; use the Action when the sync just needs to happen.

## Schema

Five tables, defined in `data/airtable-spec.json` and instantiated per site by
`scripts/init-base.py`. `data/airtable-schema.json` holds every table and field ID —
**address the base by ID, never by display name**, so fields can be renamed in
Airtable without breaking the build.

| table | holds |
|---|---|
| `Sections` | slug, title, order, open-by-default, sites |
| `Websites` | simple link rows; `Favorite` also puts one in the top strip |
| `People` | name, note, and profile URLs (Website, Wikipedia, IMDB, GitHub, LinkedIn, X, Instagram, Email) |
| `Projects` | emoji, status, status label, note |
| `Project Resources` | child of Projects — arbitrary Label + URL rows |

Two things worth knowing about the model:

- **Sections do not declare a type.** Each item carries its own `type`
  (`website` / `person` / `project`) and the renderer dispatches per item, so a
  section can mix them.
- **`Status` must be one of `live` / `done` / `wip` / `idea`.** These map to
  CSS classes for the status dot's colour, so a new option renders a grey dot.
  `Status Label` beside it is free text and can say anything.

## Process

1. **Conflict check.** Before touching anything:
   - `git status` — the working tree must be clean. If it isn't, stop and ask
     rather than clobbering in-progress work.
   - `git fetch origin main && git log HEAD..origin/main` — branch from the
     latest `main`.
   - Check for an open PR from a previous run (branch prefix `links-sync-`)
     via the GitHub MCP tools. If one is open, update it or say it's pending
     rather than opening a second.

2. **Pull the base.** `python3 scripts/sync-links.py /tmp/links-sync-out.json`
   with `AIRTABLE_TOKEN` set to a token scoped to the base (read is enough).
   Without a token, or without network access to `api.airtable.com`, use
   `--from-dir tests/fixtures/airtable` to build from the committed fixtures —
   useful for testing the transform, but it is **not** a real sync and must
   never be committed as one.

3. **Read the warnings.** The sync skips records it cannot place rather than
   failing: a person or project with no `Section` has nowhere to render.
   Every skip prints `warning:` on stderr. Relay these to the human — a
   skipped record is almost always an oversight in the base, not a decision.
   Malformed rows (bad status, missing URL) raise instead; report the exact
   error and stop.

4. **Diff.** Compare against the repo's `data/links.json`. Identical means
   there is nothing to do — say so and stop, no branch and no PR.

5. **Build before proposing.** `npm ci && npm run build`. The PR deploys on
   merge, so a build failure belongs here, not on `main`.

6. **Branch, commit, PR.** If there's a real diff:
   - `git checkout -b links-sync-YYYYMMDD` off the latest `main`.
   - Copy the validated output over `data/links.json`.
   - Commit describing what changed by name, not just "update data".
   - Use `python3 scripts/diff-links.py <old> <new>` for the PR body — it
     names added, removed, and edited items and which fields changed.
   - Include any `warning:` lines in the PR body so skipped records are
     visible to the reviewer.
   - Leave the PR for human review. This skill does not merge.
