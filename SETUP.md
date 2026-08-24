# Standing up a new site

This repo is both a live site and the template the sibling sites are forked
from. Everything under `src/` and `scripts/` is shared; everything that makes a
deployment *itself* lives in three files:

| file | what it holds |
|---|---|
| `data/site.json` | title, brand lines, tagline, storage prefix |
| `data/airtable-schema.json` | this site's base and field IDs — **generated** |
| `src/static/icons/` | favicons |

If a change only touches those, it stays in one site. If it touches anything
else, it is an upgrade every sibling site wants — see [Sharing upgrades](#sharing-upgrades).

## 1. Copy the repo

```sh
git clone https://github.com/bearnax/my-links.git my-new-site
cd my-new-site
rm -rf .git && git init
git remote add upstream https://github.com/bearnax/my-links.git
```

Keeping `upstream` wired up from the start is what makes step 6 cheap later.

## 2. Name the site

Edit `data/site.json`:

```json
{
  "title": "By Will",
  "brand": ["By", "Will"],
  "tagline": ["Work link", "hub"],
  "storagePrefix": "bw"
}
```

`storagePrefix` namespaces `localStorage`. Two sites on `*.github.io` share an
origin, so **two sites with the same prefix will overwrite each other's saved
theme and open-section state.** Make it unique.

Replace the favicons in `src/static/icons/` while you're here.

## 3. Create the Airtable base

You need a personal access token with `schema.bases:write` and
`data.records:read`, and the workspace ID (the `wsp...` segment in the
workspace URL).

```sh
export AIRTABLE_TOKEN=pat...
python3 scripts/init-base.py --workspace wspXXXXXXXXXXXX --name "By Will CMS"
```

This creates the five tables from `data/airtable-spec.json` and writes
`data/airtable-schema.json` with the IDs Airtable generated. Those IDs cannot
be guessed or copied from another site — this is the only supported way to
produce that file, and it should never be hand-edited.

Already made a base by hand? `--base appXXXXXXXX` adopts it instead: missing
link fields are added, existing ones left alone.

## 4. Seed it (optional)

To start from another site's content rather than an empty base:

```sh
python3 scripts/build-airtable-seed.py data/links.json data/airtable-seed
```

Then import each CSV in `data/airtable-seed/` into the matching table. Link
columns (`Section`, `Project`) match on the primary field, so import
**Sections and Projects first**, then the tables that point at them.

Starting empty is also fine — create a couple of sections in Airtable by hand
and skip to step 5.

## 5. Check it before you build

```sh
python3 scripts/doctor.py --online
```

This catches the failures that otherwise surface late and cryptically: a schema
still addressing the base you copied from, a token missing a scope, a renamed
site that never got its own base. Exit status is non-zero on failure, so it can
gate CI.

Then:

```sh
npm install && npm run build   # writes _site/
python3 scripts/sync-links.py  # pull the base into data/links.json
```

## 6. Wire up GitHub

- **Pages**: _Settings → Pages → Build and deployment → Source →_ **GitHub Actions**.
  The site is built, not served from the repo, so a branch source renders nothing.
- **Secret**: `AIRTABLE_TOKEN`, scoped to this site's base. `data.records:read`
  is enough for the sync — the write scope is only needed for `init-base.py`.
- **PR permissions** for the scheduled sync: turn on _Settings → Actions →
  General → Workflow permissions →_ **Allow GitHub Actions to create and approve
  pull requests**, or set a `SYNC_PR_TOKEN` secret to a PAT with `repo` scope.
  With neither, the sync still pushes its branch and prints a compare link.
- **Private repos** cannot use Pages on a free plan. Build and sync work; only
  the deploy step fails until the repo is public.

## Sharing upgrades

Sibling sites keep their own repo, their own base, and their own data. Only the
engine is shared, so upgrades move as cherry-picks:

```sh
git fetch upstream
git log --oneline HEAD..upstream/main            # what's new
git cherry-pick <sha>                            # take one
```

A commit that touches only `src/`, `scripts/`, `.github/`, or `eleventy.config.js`
will apply cleanly. A commit that also edits `data/` will conflict — which is the
point: that's a content change, not an upgrade, and it should not travel.

**So keep those separate in your commits.** A commit that changes the card
renderer *and* adds a link is a commit no sibling can take.

To send a fix the other way, push a branch to `bearnax/my-links` and open a PR
there as normal.
