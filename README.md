# my-links
A public facing website with my most used links (i.e. my universal bookmarks)

Live on [Github Pages](https://bearnax.github.io/my-links/)

## Building

The site is generated with [Eleventy](https://www.11ty.dev/) from
`data/links.json`. The cards are rendered at build time, so the page ships as
real HTML and works with JavaScript disabled; `src/index.js` handles
the interactive search modal (with `/` shortcut), light/dark mode switching,
and accordion persistence.

```sh
npm install
npm run build   # writes _site/
npm run serve   # local dev server with live reload
npm run sync    # pulls latest data from Airtable into data/links.json
npm run test    # builds, checks configuration, and tests the Airtable transform
```

| path | what it is |
|---|---|
| `data/links.json` | generated data, the input to the build |
| `data/site.json` | this site's name, brand lines, and storage prefix |
| `data/airtable-spec.json` | the schema every site's base must have (template) |
| `data/airtable-schema.json` | this site's table and field IDs (generated) |
| `src/index.njk` | the page shell (includes floating search/theme dock) |
| `src/_includes/cards.njk` | macros for favorite buttons, item row cards, and sections |
| `src/_data/links.js` | reads `data/links.json` into the templates |
| `src/style.css`, `src/index.js`, `src/static/` | copied through to `_site/` as-is |

Deploys happen from the **Build and deploy site** GitHub Action on every push
to `main`. Because the site is built rather than served from the repo as-is,
Pages must be set to _Settings → Pages → Build and deployment → Source →_
**GitHub Actions**.

## Editing links

The site is built from `data/links.json`, which is generated — don't hand-edit
it. The source of truth is this site's Airtable base, whose ID lives in
`data/airtable-schema.json` (for this deployment: **Links CMS**,
`app1bBKfPU7TpXAgm`, in the Production DBs workspace). Edit records there, then run the
`handle-the-data` skill (`.agents/skills/handle-the-data/`) or `npm run sync` to pull
the base, regenerate `data/links.json`, and review the diff.

The committed JSON is deliberately the seam between Airtable and the site: the
build never calls Airtable, so it works offline and every data change arrives
as a reviewable diff rather than appearing silently on the live page.

### Schema

| table | holds |
|---|---|
| `Sections` | Title, Sub Title (optional), slug, Accent Color (`<name> #<hex>`), Order, Open |
| `Items` | Title, Section, Order, Search, Primary URL & Label, Link1-3 URLs & Labels, Description, Presentation, Image URL, Is Project, Favorite |

Sections control grouping, accent color, and default open state. Give every
item a home section. Check **Favorite** to also pin its primary destination to
the top. The legacy Favorites section is supported during migration. To move a
record out of it, choose its home section and check Favorite. Once empty,
the legacy section can be archived or removed in Airtable.

Use **Description** to explain an unfamiliar link in a sentence. **Is Project**
adds the item to the Projects count. Choose **Featured** under **Presentation**
for a larger card, with an optional **Image URL**. Upload public images to R2
and paste the stable HTTPS URL. The page counts distinct destination URLs,
including secondary links, and displays the last content-change date from the
published snapshot. Unchanged syncs keep the existing date.

### Checking the setup

```sh
python3 scripts/doctor.py --online
```

Verifies `site.json`, that every field in `data/airtable-spec.json` is present
in the schema, and that the base actually answers. Run it first when a sync fails. After new fields are created, refresh the
ID map with `python3 scripts/init-base.py --refresh` and an `AIRTABLE_TOKEN`
with `schema.bases:read` on this base. This only reads Airtable metadata.

### Running a sync by hand

```sh
npm run sync                     # pulls directly using .env or AIRTABLE_TOKEN
python3 scripts/diff-links.py <old.json> <new.json>   # markdown change summary
```

Without a token you can still exercise the transform against committed
fixtures, which is how it is tested where `api.airtable.com` is unreachable:

```sh
python3 scripts/sync-links.py --from-dir tests/fixtures/airtable /tmp/out.json
```

Records that can't be placed — an item with no section — are
skipped with a `warning:` on stderr rather than failing the run. Malformed rows, such as a missing destination or an invalid image URL, stop the sync.

### Publishing from GitHub Actions

Open **Actions → Sync links data from Airtable → Run workflow** on `main`.
Review the generated PR, then merge to deploy. Rerunning the workflow
refreshes the open PR from the latest Airtable data. If Airtable matches
`main` again, the workflow closes the obsolete sync PR. Review warnings in
the run summary and PR body.

Set the repository's `AIRTABLE_TOKEN` secret to a token scoped to the base
with `data.records:read`. Use **Refresh field IDs** only after a schema
change and grant the token `schema.bases:read` for that run.
GitHub Actions must be allowed to open PRs, or `SYNC_PR_TOKEN` must have
permission to do so for this repository. If PR creation fails after the
branch is pushed, the run summary includes a link to open it manually.
