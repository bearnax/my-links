#!/usr/bin/env python3
"""Turn a data/links.json into per-table seed records for a fresh Airtable base.

Usage: build-airtable-seed.py [links.json] [out_dir]

Populating a new base by hand is the slowest part of standing up a fork, so
this derives the records from data the site already ships. Every record here
comes from the input file — nothing is invented, and no site's own contacts
are baked into this script.

Writes one JSON file per table, plus matching CSVs so the same seed can be
loaded either through the API or through Airtable's CSV import.

To start a fork from an empty base, point this at a links.json with the
sections you want and no items, or just create the sections by hand — the
schema comes from scripts/init-base.py, not from here.
"""
import csv
import json
import os
import sys


def build(data):
    """Fan data/links.json back out into Sections and Items tables."""
    sections = []
    items = []

    # If there are favorites, add them as a Favorites section (order 0)
    fav_list = data.get("favorites", [])
    if fav_list:
        sections.append({
            "Slug": "favorites",
            "Title": "Favorites",
            "Sub Title": "",
            "Accent Color": "blue #2b5c8f",
            "Order": 0,
            "Open": True,
        })
        for i, fav in enumerate(fav_list, start=1):
            items.append({
                "Title": fav.get("label", ""),
                "Section": "favorites",
                "Order": i,
                "Search": fav.get("search", ""),
                "Primary URL": fav.get("url", ""),
                "Primary URL Label": fav.get("label", ""),
                "Link1 URL": "",
                "Link1 URL Label": "",
                "Link2 URL": "",
                "Link2 URL Label": "",
                "Link3 URL": "",
                "Link3 URL Label": "",
            })

    for order, sec in enumerate(data.get("sections", []), start=1):
        # Skip quick-access if present
        if sec["id"] == "quick-access":
            continue

        sections.append({
            "Slug": sec["id"],
            "Title": sec["title"],
            "Sub Title": sec.get("subtitle", ""),
            "Accent Color": sec.get("accentColor", ""),
            "Order": sec.get("order", order),
            "Open": bool(sec.get("open")),
        })

        for i, it in enumerate(sec.get("items", []), start=1):
            title = it.get("title") or it.get("name") or it.get("label", "")
            primary_url = it.get("primaryUrl") or it.get("url", "")
            primary_label = it.get("primaryUrlLabel", "")

            # If older format had links list:
            extra_links = list(it.get("links", []))
            if not primary_url and extra_links:
                first = extra_links.pop(0)
                primary_url = first["url"]
                primary_label = first.get("label", "")

            row = {
                "Title": title,
                "Section": sec["id"],
                "Order": it.get("order", i),
                "Search": it.get("search", ""),
                "Primary URL": primary_url,
                "Primary URL Label": primary_label,
                "Link1 URL": "",
                "Link1 URL Label": "",
                "Link2 URL": "",
                "Link2 URL Label": "",
                "Link3 URL": "",
                "Link3 URL Label": "",
            }

            for num, link in enumerate(extra_links[:3], start=1):
                row[f"Link{num} URL"] = link["url"]
                row[f"Link{num} URL Label"] = link.get("label", "")

            items.append(row)

    return {
        "Sections": sections,
        "Items": items,
    }


def write(tables, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in tables.items():
        stem = os.path.join(out_dir, name.lower().replace(" ", "-"))

        with open(stem + ".json", "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
            f.write("\n")

        if not rows:
            continue
        with open(stem + ".csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                flat = {
                    k: (",".join(v) if isinstance(v, list) else "" if v is None else v)
                    for k, v in row.items()
                }
                writer.writerow(flat)

        print(f"{name}: {len(rows)} records -> {stem}.json / {stem}.csv")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data/links.json"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "data/airtable-seed"

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    write(build(data), out_dir)


if __name__ == "__main__":
    main()
