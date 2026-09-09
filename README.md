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
npm run test    # builds and checks site configuration via doctor.py
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
| `Items` | Title, Section, Order, Search, Primary URL & Label, Link1-3 URLs & Labels |

Sections are collapsible and specify an accent color that dynamically styles the section and its link pills. A section titled or slugged `favorites` is pinned to the top favorites strip.

### Checking the setup

```sh
python3 scripts/doctor.py --online
```

Verifies `site.json`, that every field in `data/airtable-spec.json` is present
in the schema, and that the base actually answers. Run it first whenever a sync
fails in a way that doesn't obviously point at the data.

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
skipped with a `warning:` on stderr rather than failing the run. Malformed
rows (a bad status, a missing URL) raise instead.

### The scheduled sync

The **Sync links data from Airtable** GitHub Action runs the same
pull/validate/build/diff/PR sequence on weekday mornings and on demand from the
Actions tab. It needs an `AIRTABLE_TOKEN` repository secret holding a personal
access token with `data.records:read` scoped to the base.

For it to open the PR itself, turn on _Settings → Actions → General → Workflow
permissions →_ **Allow GitHub Actions to create and approve pull requests**, or
set a `SYNC_PR_TOKEN` secret to a PAT with `repo` scope. With neither, the job
still pushes the synced branch and prints a compare link in the run summary.

