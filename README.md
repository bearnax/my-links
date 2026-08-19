# my-links
A public facing website with my most used links (i.e. my universal bookmarks)

Live on [Github Pages](https://bearnax.github.io/my-links/)

## Building

The site is generated with [Eleventy](https://www.11ty.dev/) from
`data/links.json`. The cards are rendered at build time, so the page ships as
real HTML and works with JavaScript disabled; `src/index.js` only handles
search, the theme toggle, and the section menu.

```sh
npm install
npm run build   # writes _site/
npm run serve   # local dev server with live reload
```

| path | what it is |
|---|---|
| `data/links.json` | generated data, the input to the build |
| `src/index.njk` | the page shell |
| `src/_includes/cards.njk` | one macro per card type (favorite, link, project) |
| `src/_data/links.js` | reads `data/links.json` into the templates |
| `src/style.css`, `src/index.js`, `src/static/` | copied through to `_site/` as-is |

Deploys happen from the **Build and deploy site** GitHub Action on every push
to `main`. Because the site is built rather than served from the repo as-is,
Pages must be set to _Settings → Pages → Build and deployment → Source →_
**GitHub Actions**.

## Editing links

The site is built from `data/links.json`, which is generated — don't hand-edit
it. The source of truth is the **Links CMS** Airtable base (`app1bBKfPU7TpXAgm`,
in the Production DBs workspace). Edit records there, then run the
`handle-the-data` Claude Code skill (`.claude/skills/handle-the-data/`) to pull
the base, regenerate `data/links.json`, and open a PR with the diff.

The committed JSON is deliberately the seam between Airtable and the site: the
build never calls Airtable, so it works offline and every data change arrives
as a reviewable diff rather than appearing silently on the live page.

### Card types

| type | table | renders as |
|---|---|---|
| `website` | Websites | a link row; flag `Favorite` to also pin it to the top strip |
| `person` | People | name, optional note, and whichever profile links are filled in |
| `project` | Projects | emoji, name, status dot, and its Project Resources links |

Sections don't declare a type — each item carries its own, so a section can mix
them. `Status` must be one of `live` / `done` / `wip` / `idea`; those map to the
dot's colour. The label beside the dot is free text.

### Running a sync by hand

```sh
export AIRTABLE_TOKEN=...        # scoped to the base; read access is enough
python3 scripts/sync-links.py    # writes data/links.json
python3 scripts/diff-links.py <old.json> <new.json>   # markdown change summary
```

Without a token you can still exercise the transform against committed
fixtures, which is how it is tested where `api.airtable.com` is unreachable:

```sh
python3 scripts/sync-links.py --from-dir tests/fixtures/airtable /tmp/out.json
```

Records that can't be placed — a person or project with no section — are
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
