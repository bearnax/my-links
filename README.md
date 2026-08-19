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
it. The actual source of truth is a Google Sheet; edit rows there, then run
the `handle-the-data` Claude Code skill (`.claude/skills/handle-the-data/`) to
pull the sheet, regenerate `data/links.json`, and open a PR with the diff.

The same sync also runs as the **Sync links data from sheet** GitHub Action
(run it from the Actions tab). For it to open the PR itself, turn on
_Settings → Actions → General → Workflow permissions →_ **Allow GitHub Actions
to create and approve pull requests** — the default `GITHUB_TOKEN` cannot
create PRs without it, no matter what `permissions:` the workflow declares.
Alternatively, set a `SYNC_PR_TOKEN` repository secret to a PAT with `repo`
scope. With neither, the job still pushes the synced branch and prints a
compare link in the run summary for you to open the PR by hand.
