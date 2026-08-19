# my-links
A single HTML, public facing website with my most used links (i.e. my universal bookmarks)

Live on [Github Pages](https://bearnax.github.io/my-links/)

## Editing links

The page renders from `data/links.json`, which is generated — don't hand-edit
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
