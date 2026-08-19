#!/usr/bin/env python3
"""Turn the current data/links.json into per-table seed records for Airtable.

Usage: build-airtable-seed.py [links.json] [out_dir]

This is a one-shot migration aid, not part of the ongoing sync. It exists so
the initial Airtable base is populated from the data the site already ships
rather than by hand — every record here is derived, nothing is invented.

Writes one JSON file per table, plus matching CSVs so the same seed can be
loaded either through the API or through Airtable's CSV import.
"""
import csv
import json
import os
import sys

SITE_PERSONAL = "Personal"


def build(data):
    sections, websites, projects, resources = [], [], [], []

    for order, sec in enumerate(data.get("sections", []), start=1):
        sections.append({
            "Slug": sec["id"],
            "Title": sec["title"],
            "Order": order,
            "Open": bool(sec.get("open")),
            "Sites": [SITE_PERSONAL],
        })

        for i, item in enumerate(sec.get("links", []), start=1):
            websites.append({
                "Name": item["label"],
                "URL": item["url"],
                "Search": item.get("search", ""),
                "Section": sec["id"],
                "Order": i,
                "Favorite": False,
                "Favorite Order": None,
                "Sites": [SITE_PERSONAL],
            })

        for i, item in enumerate(sec.get("projects", []), start=1):
            projects.append({
                "Name": item["name"],
                "Emoji": item.get("emoji", ""),
                "Status": item["status"],
                "Status Label": item["statusLabel"],
                "Note": item.get("note", ""),
                "Search": item.get("search", ""),
                "Section": sec["id"],
                "Order": i,
                "Sites": [SITE_PERSONAL],
            })
            # Live/Repo become ordinary resource rows, so a project can carry
            # any number of links rather than exactly these two.
            for label, key in (("Live", "live"), ("Repo", "repo")):
                if item.get(key):
                    resources.append({
                        "Label": label,
                        "URL": item[key],
                        "Project": item["name"],
                        "Order": 1 if label == "Live" else 2,
                    })

    # Favorites are websites flagged for the top row. They are their own list
    # in the JSON, so match them back onto the website rows by URL.
    by_url = {w["URL"]: w for w in websites}
    for i, fav in enumerate(data.get("favorites", []), start=1):
        row = by_url.get(fav["url"])
        if row is None:
            # A favorite that is not already a section link still needs a home.
            row = {
                "Name": fav["label"],
                "URL": fav["url"],
                "Search": fav.get("search", ""),
                "Section": "",
                "Order": None,
                "Favorite": True,
                "Favorite Order": i,
                "Sites": [SITE_PERSONAL],
            }
            websites.append(row)
        else:
            row["Favorite"] = True
            row["Favorite Order"] = i

    return {
        "Sections": sections,
        "Websites": websites,
        "Projects": projects,
        "Project Resources": resources,
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
