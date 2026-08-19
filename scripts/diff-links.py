#!/usr/bin/env python3
"""Summarize the differences between two links.json files as markdown bullets.

Usage: diff-links.py <old.json> <new.json>

Prints a bullet list of added/removed/edited favorites, links, and projects,
grouped by section. Intended for use as a generated pull request body.
"""
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def key_for(item):
    return item.get("url") or item.get("name") or item.get("label")


def diff_list(old_items, new_items, kind_label):
    old_by_key = {key_for(i): i for i in old_items}
    new_by_key = {key_for(i): i for i in new_items}

    lines = []
    for key, item in new_by_key.items():
        if key not in old_by_key:
            name = item.get("name") or item.get("label")
            lines.append(f"- Add {kind_label}: {name}")
    for key, item in old_by_key.items():
        if key not in new_by_key:
            name = item.get("name") or item.get("label")
            lines.append(f"- Remove {kind_label}: {name}")
    for key, item in new_by_key.items():
        if key in old_by_key and old_by_key[key] != item:
            name = item.get("name") or item.get("label")
            lines.append(f"- Edit {kind_label}: {name}")
    return lines


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    old = load(sys.argv[1])
    new = load(sys.argv[2])

    lines = diff_list(old.get("favorites", []), new.get("favorites", []), "favorite")

    old_sections = {s["id"]: s for s in old.get("sections", [])}
    new_sections = {s["id"]: s for s in new.get("sections", [])}

    for sid, section in new_sections.items():
        items_key = "links" if section["type"] == "links" else "projects"
        old_items = old_sections.get(sid, {}).get(items_key, [])
        new_items = section.get(items_key, [])
        item_lines = diff_list(old_items, new_items, section["type"][:-1])
        if sid not in old_sections and item_lines:
            lines.append(f"- Add section: {section['title']}")
        lines.extend(item_lines)

    for sid, section in old_sections.items():
        if sid not in new_sections:
            lines.append(f"- Remove section: {section['title']}")

    if not lines:
        print("No changes detected.")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
