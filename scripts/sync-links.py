#!/usr/bin/env python3
"""Convert the links data sheet (as CSV) into data/links.json.

Usage: sync-links.py <input.csv> [output.json]

CSV columns (one row per favorite / link / project):
  group_id, group_title, group_kind, group_order, group_open, item_order,
  label, url, search, emoji, note, status, status_label, live_url, repo_url

group_kind is one of: favorites | links | projects
status (projects only) is one of: done | live | wip | idea
"""
import csv
import json
import sys

VALID_KINDS = {"favorites", "links", "projects"}
VALID_STATUSES = {"done", "live", "wip", "idea"}


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require(row, field, context):
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{context}: missing required field '{field}'")
    return value


def build(rows):
    favorites = []
    groups = {}  # group_id -> {title, kind, order, open, items: []}

    for i, row in enumerate(rows):
        line = i + 2  # header is line 1
        kind = require(row, "group_kind", f"row {line}")
        if kind not in VALID_KINDS:
            raise ValueError(f"row {line}: invalid group_kind '{kind}'")
        label = require(row, "label", f"row {line}")
        item_order = int(row.get("item_order") or 0)

        if kind == "favorites":
            favorites.append({
                "order": item_order,
                "data": {
                    "label": label,
                    "url": require(row, "url", f"row {line}"),
                    "search": (row.get("search") or "").strip() or label.lower(),
                },
            })
            continue

        group_id = require(row, "group_id", f"row {line}")
        group = groups.setdefault(group_id, {
            "title": require(row, "group_title", f"row {line}"),
            "kind": kind,
            "order": int(row.get("group_order") or 0),
            "open": (row.get("group_open") or "").strip().upper() == "TRUE",
            "items": [],
        })

        if kind == "links":
            item = {
                "label": label,
                "url": require(row, "url", f"row {line}"),
                "search": (row.get("search") or "").strip() or label.lower(),
            }
        else:  # projects
            status = require(row, "status", f"row {line}")
            if status not in VALID_STATUSES:
                raise ValueError(f"row {line}: invalid status '{status}'")
            item = {
                "emoji": (row.get("emoji") or "").strip(),
                "name": label,
                "status": status,
                "statusLabel": require(row, "status_label", f"row {line}"),
                "search": (row.get("search") or "").strip() or label.lower(),
                "live": (row.get("live_url") or "").strip() or None,
                "repo": (row.get("repo_url") or "").strip() or None,
            }
            note = (row.get("note") or "").strip()
            if note:
                item["note"] = note

        group["items"].append({"order": item_order, "data": item})

    favorites.sort(key=lambda x: x["order"])
    result_favorites = [x["data"] for x in favorites]

    ordered_group_ids = sorted(groups.keys(), key=lambda gid: groups[gid]["order"])
    sections = []
    for gid in ordered_group_ids:
        group = groups[gid]
        group["items"].sort(key=lambda x: x["order"])
        items = [x["data"] for x in group["items"]]
        section = {
            "id": gid,
            "title": group["title"],
            "type": group["kind"],
            "open": group["open"],
        }
        if group["kind"] == "links":
            section["links"] = items
        else:
            section["projects"] = items
        sections.append(section)

    return {"favorites": result_favorites, "sections": sections}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data/links.json"

    rows = load_rows(in_path)
    data = build(rows)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {out_path} ({len(data['favorites'])} favorites, {len(data['sections'])} sections)")


if __name__ == "__main__":
    main()
