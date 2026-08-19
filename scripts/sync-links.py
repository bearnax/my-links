#!/usr/bin/env python3
"""Build data/links.json from the Links CMS Airtable base.

Usage:
  sync-links.py [output.json]                 fetch from Airtable
  sync-links.py --from-dir DIR [output.json]  build from saved API responses

The base is addressed entirely by the IDs in data/airtable-schema.json, so
fields and tables can be renamed in Airtable without breaking the build.

Requires AIRTABLE_TOKEN when fetching. --from-dir reads one <table>.json per
table in the same shape the API returns, which is how this is tested without
network access.

Records that cannot be placed are skipped with a warning rather than failing
the run: a person or project with no section has nowhere to render, and one
half-finished row should not take the whole site down. Malformed rows — a bad
status, a missing URL — still raise, because those are wrong rather than
incomplete.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.airtable.com/v0"
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "airtable-schema.json")

# Person profile fields, in the order their links should render on the card.
PERSON_LINKS = [
    ("website", "Website"),
    ("wikipedia", "Wikipedia"),
    ("imdb", "IMDB"),
    ("github", "GitHub"),
    ("linkedin", "LinkedIn"),
    ("x", "X"),
    ("instagram", "Instagram"),
]

warnings = []


def warn(message):
    warnings.append(message)
    print("warning: " + message, file=sys.stderr)


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def fetch_table(base_id, table_id, token):
    """Page through one table, returning every record."""
    records = []
    offset = None
    while True:
        params = {"pageSize": "100", "returnFieldsByFieldId": "true"}
        if offset:
            params["offset"] = offset
        url = f"{API_ROOT}/{base_id}/{table_id}?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise SystemExit(f"Airtable returned {e.code} for table {table_id}: {body}")
        records.extend(payload.get("records", []))
        offset = payload.get("offset")
        if not offset:
            return records


def load_tables(schema, from_dir, token):
    names = {
        "sections": "sections",
        "websites": "websites",
        "people": "people",
        "projects": "projects",
        "projectResources": "project-resources",
    }
    tables = {}
    for key, filename in names.items():
        if from_dir:
            with open(os.path.join(from_dir, filename + ".json"), encoding="utf-8") as f:
                tables[key] = json.load(f)["records"]
        else:
            tables[key] = fetch_table(schema["baseId"], schema["tables"][key]["id"], token)
    return tables


def value(record, field_id, default=""):
    return record.get("fields", {}).get(field_id, default)


def text(record, field_id):
    return (value(record, field_id) or "").strip()


def link_target(record, field_id):
    """First linked record ID, or None. Link fields are always arrays."""
    linked = value(record, field_id, [])
    return linked[0] if linked else None


def search_terms(record, field_id, fallback):
    return text(record, field_id) or fallback.lower()


def build_sections(records, fields):
    sections = {}
    for record in records:
        slug = text(record, fields["slug"])
        title = text(record, fields["title"])
        if not slug or not title:
            warn(f"section {record['id']} is missing a slug or title; skipped")
            continue
        sections[record["id"]] = {
            "order": value(record, fields["order"], 0) or 0,
            "section": {
                "id": slug,
                "title": title,
                "open": bool(value(record, fields["open"], False)),
                "items": [],
            },
        }
    return sections


def build_websites(records, fields):
    """Returns (favorites, sectioned items). A website can be both."""
    favorites, items = [], []
    for record in records:
        label = text(record, fields["name"])
        url = text(record, fields["url"])
        if not label:
            warn(f"website {record['id']} has no name; skipped")
            continue
        if not url:
            raise ValueError(f"website '{label}' has no URL")

        search = search_terms(record, fields["search"], label)

        if value(record, fields["favorite"], False):
            favorites.append({
                "order": value(record, fields["favoriteOrder"], 0) or 0,
                "data": {"label": label, "url": url, "search": search},
            })

        section_id = link_target(record, fields["section"])
        if section_id:
            items.append({
                "section": section_id,
                "order": value(record, fields["order"], 0) or 0,
                "data": {"type": "website", "label": label, "url": url, "search": search},
            })
        elif not value(record, fields["favorite"], False):
            warn(f"website '{label}' is in no section and is not a favorite; skipped")

    favorites.sort(key=lambda f: f["order"])
    return [f["data"] for f in favorites], items


def build_people(records, fields):
    items = []
    for record in records:
        name = text(record, fields["name"])
        if not name:
            warn(f"person {record['id']} has no name; skipped")
            continue

        section_id = link_target(record, fields["section"])
        if not section_id:
            warn(f"person '{name}' is in no section; skipped")
            continue

        links = []
        for key, label in PERSON_LINKS:
            url = text(record, fields[key])
            if url:
                links.append({"label": label, "url": url})
        email = text(record, fields["email"])
        if email:
            links.append({"label": "Email", "url": "mailto:" + email})

        if not links:
            warn(f"person '{name}' has no profile links; the card will be a bare name")

        person = {
            "type": "person",
            "name": name,
            "search": search_terms(record, fields["search"], name),
            "links": links,
        }
        note = text(record, fields["note"])
        if note:
            person["note"] = note

        items.append({
            "section": section_id,
            "order": value(record, fields["order"], 0) or 0,
            "data": person,
        })
    return items


def build_projects(records, resources, fields, resource_fields, statuses):
    by_project = {}
    for record in resources:
        project_id = link_target(record, resource_fields["project"])
        label = text(record, resource_fields["label"])
        url = text(record, resource_fields["url"])
        if not project_id:
            warn(f"project resource '{label or record['id']}' belongs to no project; skipped")
            continue
        if not label or not url:
            raise ValueError(f"project resource {record['id']} needs both a label and a URL")
        by_project.setdefault(project_id, []).append({
            "order": value(record, resource_fields["order"], 0) or 0,
            "data": {"label": label, "url": url},
        })

    items = []
    for record in records:
        name = text(record, fields["name"])
        if not name:
            warn(f"project {record['id']} has no name; skipped")
            continue

        section_id = link_target(record, fields["section"])
        if not section_id:
            warn(f"project '{name}' is in no section; skipped")
            continue

        status = text(record, fields["status"])
        if status not in statuses:
            raise ValueError(
                f"project '{name}' has status '{status}', expected one of {sorted(statuses)}"
            )

        links = sorted(by_project.get(record["id"], []), key=lambda r: r["order"])

        project = {
            "type": "project",
            "name": name,
            "emoji": text(record, fields["emoji"]),
            "status": status,
            "statusLabel": text(record, fields["statusLabel"]) or status,
            "search": search_terms(record, fields["search"], name),
            "links": [link["data"] for link in links],
        }
        note = text(record, fields["note"])
        if note:
            project["note"] = note

        items.append({
            "section": section_id,
            "order": value(record, fields["order"], 0) or 0,
            "data": project,
        })
    return items


def build(tables, schema):
    t = schema["tables"]
    sections = build_sections(tables["sections"], t["sections"]["fields"])
    favorites, website_items = build_websites(tables["websites"], t["websites"]["fields"])
    people_items = build_people(tables["people"], t["people"]["fields"])
    project_items = build_projects(
        tables["projects"],
        tables["projectResources"],
        t["projects"]["fields"],
        t["projectResources"]["fields"],
        set(schema["statuses"]),
    )

    for item in website_items + people_items + project_items:
        entry = sections.get(item["section"])
        if entry is None:
            warn(f"item '{item['data'].get('name') or item['data'].get('label')}' "
                 "points at a section that no longer exists; skipped")
            continue
        entry["section"]["items"].append(item)

    ordered = []
    for entry in sorted(sections.values(), key=lambda s: s["order"]):
        section = entry["section"]
        section["items"] = [i["data"] for i in sorted(section["items"], key=lambda i: i["order"])]
        if not section["items"]:
            warn(f"section '{section['title']}' has no items; it will not render")
            continue
        ordered.append(section)

    return {"favorites": favorites, "sections": ordered}


def main():
    args = sys.argv[1:]
    from_dir = None
    if args and args[0] == "--from-dir":
        if len(args) < 2:
            raise SystemExit("--from-dir needs a directory")
        from_dir = args[1]
        args = args[2:]
    out_path = args[0] if args else "data/links.json"

    token = os.environ.get("AIRTABLE_TOKEN")
    if not from_dir and not token:
        raise SystemExit("AIRTABLE_TOKEN is not set (or pass --from-dir for a local build)")

    schema = load_schema()
    data = build(load_tables(schema, from_dir, token), schema)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    item_count = sum(len(s["items"]) for s in data["sections"])
    print(f"Wrote {out_path}: {len(data['favorites'])} favorites, "
          f"{len(data['sections'])} sections, {item_count} items")
    if warnings:
        print(f"{len(warnings)} warning(s) — see above", file=sys.stderr)


if __name__ == "__main__":
    main()
