# my-links
A single HTML, public facing website with my most used links (i.e. my universal bookmarks)

Live on [Github Pages](https://bearnax.github.io/my-links/)

## Editing links

The page renders from `data/links.json`, which is generated — don't hand-edit
it. The actual source of truth is a Google Sheet; edit rows there, then run
the `handle-the-data` Claude Code skill (`.claude/skills/handle-the-data/`) to
pull the sheet, regenerate `data/links.json`, and open a PR with the diff.
