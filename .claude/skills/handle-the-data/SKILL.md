---
name: handle-the-data
description: Sync the links/projects data on the site from the Google Sheet source of truth. Use when asked to sync, update, pull, or refresh the site's links from the sheet, or when the human says they've edited the "Will's Links" data sheet and want it reflected on the site.
---

# Handle the Data

`data/links.json` drives everything rendered on the page (favorites, sections,
links, projects). It is a **generated file** — the actual source of truth for
humans to edit is this Google Sheet:

**Sheet**: https://docs.google.com/spreadsheets/d/1-N1-rREX72eqmdyA-cGBr9UQsO2pGfTQ15KVFn5WH2k/edit
**File ID**: `1-N1-rREX72eqmdyA-cGBr9UQsO2pGfTQ15KVFn5WH2k`

There's also a code-only path for this: the `.github/workflows/sync-links.yml`
GitHub Action does the same pull/validate/diff/PR sequence without any LLM
involved (triggerable via `workflow_dispatch`, e.g. `gh workflow run
sync-links.yml`). Use this skill when a human is driving the conversation;
use the Action when you just need the sync to happen from code.

This skill pulls the sheet, regenerates `data/links.json`, and opens a PR with
the diff. It never pushes straight to `main`.

## Schema

The sheet is one flat tab. One row per favorite, link, or project. Columns:

| column | meaning |
|---|---|
| `group_id` | slug for the section (`favorites` for the favorites row, else e.g. `cnn`, `projects-work`) |
| `group_title` | section heading text, e.g. `CNN`, `Projects — Work` |
| `group_kind` | `favorites` \| `links` \| `projects` |
| `group_order` | sort order of sections (favorites is always first, kind of order `0`) |
| `group_open` | `TRUE`/`FALSE` — whether the section is expanded by default (ignored for favorites) |
| `item_order` | sort order of rows within their group |
| `label` | link label, or project name |
| `url` | link URL (favorites/links only — leave blank for projects) |
| `search` | search keywords; falls back to lowercased label if blank |
| `emoji` | project emoji prefix (projects only) |
| `note` | optional parenthetical note after a project name, e.g. `(formerly TIP Scout)` |
| `status` | project status: `done` \| `live` \| `wip` \| `idea` (projects only) |
| `status_label` | human status text shown next to the dot, e.g. `Not deployed` |
| `live_url` | project's live URL, blank if none |
| `repo_url` | project's repo URL, blank if none |

`scripts/sync-links.py` (in this repo) implements this schema — read it if
anything above is ambiguous. It raises on malformed rows rather than silently
dropping data, so trust its errors.

## Process

1. **Conflict check.** Before touching anything:
   - `git status` — the working tree must be clean. If it isn't, stop and ask
     the human what to do with the in-progress work rather than clobbering it.
   - `git fetch origin main && git log HEAD..origin/main` — make sure you're
     about to branch from the latest `main`. If your local `main` is behind,
     update it first (`git checkout main && git pull origin main`).
   - Check for an existing open PR from a previous run of this skill (branch
     prefix `links-sync-`) via the GitHub MCP tools. If one is open and
     unmerged, don't open a second one — either update that PR's branch or
     tell the human it's already pending review.

2. **Pull the sheet.** Use `mcp__Google_Drive__download_file_content` on the
   file ID above with `exportMimeType: "text/csv"`. The result's `content` is
   base64 — decode it to get the CSV text. (Don't use `read_file_content` for
   this — its markdown-table export has mangled multi-byte emoji in testing.
   The CSV export round-trips cleanly.) Save it to a temp file.

3. **Validate before writing.** Run the converter against a scratch path first:
   `python3 scripts/sync-links.py /tmp/links-sync.csv /tmp/links-sync-out.json`
   If it raises (bad `group_kind`, bad `status`, missing required field),
   stop here and report the exact row/error back to the human — do not open a
   PR with partial or guessed data.

4. **Diff.** Compare `/tmp/links-sync-out.json` against the repo's
   `data/links.json`. If they're identical, there's nothing to do — say so
   and stop (no branch, no PR).

5. **Branch, commit, PR.** If there's a real diff:
   - `git checkout -b links-sync-YYYYMMDD` off latest `main`.
   - Copy the validated output over `data/links.json`.
   - Commit with a message summarizing what changed (added/removed/edited
     favorites, links, or projects — describe them by name, not just "update
     data").
   - Push and open a PR. In the PR body, list the concrete changes (e.g. "Add
     project: Foo (wip)", "Edit link: CNN Shorts URL", "Remove favorite:
     Old Thing") by diffing the old and new JSON — don't just say "synced
     from sheet."
   - Leave the PR for human review/merge — this skill does not merge.
