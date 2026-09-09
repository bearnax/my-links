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
    """Fan data/links.json back out into one list of rows per table.

    Sections carry a mixed `items` list where each item declares its own
    `type`; this is the inverse of the join scripts/sync-links.py performs.
    """
    sections, websites, projects, resources, people = [], [], [], [], []

    for order, sec in enumerate(data.get("sections", []), start=1):
        sections.append({
            "Slug": sec["id"],
            "Title": sec["title"],
            "Order": order,
            "Open": bool(sec.get("open")),
        })

        for i, item in enumerate(sec.get("items", []), start=1):
            kind = item.get("type")

            if kind == "website":
                websites.append({
                    "Name": item["label"],
                    "URL": item["url"],
                    "Search": item.get("search", ""),
                    "Section": sec["id"],
                    "Order": i,
                    "Favorite": False,
                    "Favorite Order": None,
                })

            elif kind == "person":
                row = {
                    "Name": item["name"],
                    "Note": item.get("note", ""),
                    "Search": item.get("search", ""),
                    "Section": sec["id"],
                    "Order": i,
                }
                # Profile links are stored as a list of {label, url}; the base
                # keeps one column per service. Email arrives as a mailto:.
                for link in item.get("links", []):
                    label, url = link["label"], link["url"]
                    if label == "Email":
                        row["Email"] = url[len("mailto:"):] if url.startswith("mailto:") else url
                    else:
                        row[label] = url
                people.append(row)

            elif kind == "project":
                projects.append({
                    "Name": item["name"],
                    "Emoji": item.get("emoji", ""),
                    "Status": item["status"],
                    "Status Label": item.get("statusLabel", item["status"]),
                    "Note": item.get("note", ""),
                    "Search": item.get("search", ""),
                    "Section": sec["id"],
                    "Order": i,
                })
                for j, link in enumerate(item.get("links", []), start=1):
                    resources.append({
                        "Label": link["label"],
                        "URL": link["url"],
                        "Project": item["name"],
                        "Order": j,
                    })

            else:
                print(f"warning: item {i} in section '{sec['id']}' has unknown "
                      f"type {kind!r}; skipped", file=sys.stderr)

    # Favorites are websites flagged for the top row. They are their own list
    # in the JSON, so match them back onto the website rows by URL.
    by_url = {w["URL"]: w for w in websites}
    for i, fav in enumerate(data.get("favorites", []), start=1):
        row = by_url.get(fav["url"])
        if row is None:
            # A favorite that is not also a section link still needs a home.
            row = {
                "Name": fav["label"],
                "URL": fav["url"],
                "Search": fav.get("search", ""),
                "Section": "",
                "Order": None,
                "Favorite": True,
                "Favorite Order": i,
            }
            websites.append(row)
        else:
            row["Favorite"] = True
            row["Favorite Order"] = i

    # People rows are ragged — each person fills in a different subset of the
    # profile columns — but the CSV writer needs one stable header, so pad
    # every row to the same shape.
    if people:
        columns = ["Name", "Note", "Website", "Wikipedia", "IMDB", "GitHub",
                   "LinkedIn", "X", "Instagram", "Email", "Search",
                   "Section", "Order"]
        people = [{c: p.get(c, "") for c in columns} for p in people]

    return {
        "Sections": sections,
        "Websites": websites,
        "Projects": projects,
        "Project Resources": resources,
        "People": people,
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
