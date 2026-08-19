#!/usr/bin/env python3
"""Summarize the differences between two links.json files as markdown bullets.

Usage: diff-links.py <old.json> <new.json>

Prints a bullet list of added/removed/edited favorites and items, grouped by
section. Intended as a generated pull request body, so a sync PR says what
actually changed rather than "synced from Airtable".
"""
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def key_for(item):
    """Identity for diffing. Websites are identified by URL because a rename
    is an edit; people and projects by name because their links move around."""
    if item.get("type") in ("person", "project"):
        return item["name"]
    return item.get("url") or item.get("label")


def label_for(item):
    return item.get("name") or item.get("label")


def kind_of(item, default):
    """Items carry a type since the Airtable cutover. Older data does not, so
    fall back to shape: only projects ever had a status."""
    if "type" in item:
        return item["type"]
    if "status" in item:
        return "project"
    return default


def diff_list(old_items, new_items, default_kind="website"):
    old_by_key = {key_for(i): i for i in old_items}
    new_by_key = {key_for(i): i for i in new_items}

    lines = []
    for key, item in new_by_key.items():
        if key not in old_by_key:
            lines.append(f"- Add {kind_of(item, default_kind)}: {label_for(item)}")
    for key, item in old_by_key.items():
        if key not in new_by_key:
            lines.append(f"- Remove {kind_of(item, default_kind)}: {label_for(item)}")
    for key, item in new_by_key.items():
        if key in old_by_key and old_by_key[key] != item:
            lines.append(f"- Edit {kind_of(item, default_kind)}: {label_for(item)}{describe_edit(old_by_key[key], item)}")
    return lines


def describe_edit(old, new):
    """Name the fields that changed, so a one-character tweak is not
    indistinguishable from a rewrite in the PR body."""
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    return f" ({', '.join(changed)})" if changed else ""


def items_of(section):
    # Tolerates the pre-Airtable shape so this still runs against old data.
    if "items" in section:
        return section["items"]
    return section.get("links", []) + section.get("projects", [])


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    old, new = load(sys.argv[1]), load(sys.argv[2])

    lines = diff_list(old.get("favorites", []), new.get("favorites", []), "favorite")

    old_sections = {s["id"]: s for s in old.get("sections", [])}
    new_sections = {s["id"]: s for s in new.get("sections", [])}

    for sid, section in new_sections.items():
        item_lines = diff_list(items_of(old_sections.get(sid, {})), items_of(section))
        if sid not in old_sections:
            lines.append(f"- Add section: {section['title']}")
        lines.extend(item_lines)

    for sid, section in old_sections.items():
        if sid not in new_sections:
            lines.append(f"- Remove section: {section['title']}")

    print("\n".join(lines) if lines else "No changes detected.")


if __name__ == "__main__":
    main()
