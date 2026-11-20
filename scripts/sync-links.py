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
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.airtable.com/v0"
HERE = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(HERE, "..", "data", "airtable-schema.json")
CSS_PATH = os.path.join(HERE, "..", "src", "style.css")

SNAPSHOT_PATH = os.path.join(HERE, "..", "data", "links.json")
ITEM_METADATA_FIELDS = ("description", "presentation", "imageUrl", "isProject", "favorite")

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
    tables = {}
    names = {"sections": "sections", "items": "items"}
    for key, filename in names.items():
        if from_dir:
            path = os.path.join(from_dir, filename + ".json")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                tables[key] = data if isinstance(data, list) else data.get("records", [])
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


def parse_accent_color(raw):
    """Parse '<string-name> #<color-hex>' or '#<hex>' or any color string into (name, hex)."""
    if not raw:
        return None, None
    raw = raw.strip()
    m = re.match(r"^([a-zA-Z0-9_-]+)\s+(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))$", raw)
    if m:
        return m.group(1).lower(), m.group(2).lower()
    m = re.match(r"^(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))$", raw)
    if m:
        return m.group(1).lower(), m.group(1).lower()
    raise ValueError(f"Invalid section accent: {raw!r}")


def verify_accent_colors(accent_map, css_path=CSS_PATH):
    """Informational check: if CSS defines a variable for this accent, verify hex."""
    if not os.path.exists(css_path):
        return
    with open(css_path, encoding="utf-8") as f:
        css = f.read().lower()

    for name, hex_code in accent_map.items():
        pattern = rf"--accent-{re.escape(name)}\s*:\s*(#[0-9a-f]{{3,8}})"
        match = re.search(pattern, css)
        if match:
            found_hex = match.group(1)
            if found_hex != hex_code:
                warn(f"Accent color '{name}' hex '{hex_code}' differs from CSS fallback '{found_hex}'")


def build_sections(records, fields):
    sections = {}
    accent_map = {}
    for record in records:
        slug = text(record, fields["slug"])
        title = text(record, fields["title"])
        if not slug or not title:
            warn(f"section {record['id']} is missing a slug or title; skipped")
            continue

        sec_data = {
            "id": slug,
            "title": title,
            "open": bool(value(record, fields["open"], False)),
            "items": [],
        }

        subtitle = text(record, fields.get("subtitle", ""))
        if subtitle:
            sec_data["subtitle"] = subtitle

        raw_accent = text(record, fields.get("accentColor", ""))
        accent_name, accent_hex = parse_accent_color(raw_accent)
        if accent_name and accent_hex:
            sec_data["accentColor"] = raw_accent
            sec_data["accentName"] = accent_name
            sec_data["accentHex"] = accent_hex
            accent_map[accent_name] = accent_hex

        sections[record["id"]] = {
            "order": value(record, fields["order"], 0) or 0,
            "section": sec_data,
        }

    return sections, accent_map


def validate_url(url, title, label, *, https_only=False):
    if not url:
        return
    try:
        parsed = urllib.parse.urlsplit(url)
        valid = parsed.hostname and parsed.scheme in (("https",) if https_only else ("http", "https"))
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError(f"Item {title!r} has an invalid {label} URL")


def build_items(records, fields):
    items = []
    for record in records:
        title = text(record, fields["title"])
        if not title:
            warn(f"item {record['id']} has no title; skipped")
            continue

        section_id = link_target(record, fields["section"])
        if not section_id:
            warn(f"item '{title}' has no section; skipped")
            continue

        search = search_terms(record, fields["search"], title)
        primary_url = text(record, fields["primaryUrl"])
        primary_label = text(record, fields["primaryUrlLabel"])
        validate_url(primary_url, title, "primary")
        if primary_url and not primary_label:
            primary_label = title

        extra_links = []
        for num in (1, 2, 3):
            url_val = text(record, fields[f"link{num}Url"])
            label_val = text(record, fields[f"link{num}Label"])
            if url_val and not label_val:
                raise ValueError(
                    f"item '{title}' has Link{num} URL '{url_val}' but is missing Link{num} URL Label"
                )
            if url_val:
                validate_url(url_val, title, f"Link{num}")
                extra_links.append({"label": label_val, "url": url_val})

        if not primary_url and not extra_links:
            raise ValueError(f"Item {title!r} has no destination")

        item_data = {"id": record["id"], "title": title, "search": search}
        description = text(record, fields.get("description"))
        if description:
            item_data["description"] = description
        presentation = text(record, fields.get("presentation")).casefold()
        if presentation == "featured":
            item_data["presentation"] = presentation
        elif presentation not in ("", "standard"):
            raise ValueError(f"Item {title!r} has an unknown Presentation: {presentation!r}")
        image_url = text(record, fields.get("imageUrl"))
        if image_url:
            validate_url(image_url, title, "image", https_only=True)
            item_data["imageUrl"] = image_url
        for flag in ("isProject", "favorite"):
            if value(record, fields.get(flag), False):
                item_data[flag] = True
        if primary_url:
            item_data["primaryUrl"] = primary_url
            item_data["primaryUrlLabel"] = primary_label
        if extra_links:
            item_data["links"] = extra_links

        items.append({
            "section": section_id,
            "order": value(record, fields["order"], 0) or 0,
            "data": item_data,
        })
    return items


def build(tables, schema):
    t = schema["tables"]
    sections, accent_map = build_sections(tables["sections"], t["sections"]["fields"])

    # Verify accent colors against CSS
    verify_accent_colors(accent_map)

    items = build_items(tables["items"], t["items"]["fields"])

    for item in items:
        entry = sections.get(item["section"])
        if entry is None:
            warn(f"item '{item['data']['title']}' points at a section that no longer exists; skipped")
            continue
        entry["section"]["items"].append(item)

    favorites = {}
    ordered = []
    section_ids = set()

    for entry in sorted(sections.values(), key=lambda s: (s["order"], s["section"]["id"])):
        sec = entry["section"]
        if sec["id"] in section_ids:
            raise ValueError(f"Duplicate section slug: {sec['id']!r}")
        section_ids.add(sec["id"])
        sorted_items = [
            i["data"] for i in sorted(
                sec["items"], key=lambda i: (i["order"], i["data"]["title"].casefold(), i["data"]["id"])
            )
        ]
        legacy = any(sec[key].lower() in ("favorites", "favorite") for key in ("id", "title"))

        if not sorted_items:
            if not legacy:
                warn(f"section '{sec['title']}' has no items; ignored")
            continue

        if not legacy:
            sec["items"] = sorted_items
            ordered.append(sec)

        for item in sorted_items:
            if not legacy and not item.get("favorite"):
                continue
            url = item.get("primaryUrl") or item["links"][0]["url"]
            label = item.get("primaryUrlLabel") or item["title"]
            # A checked item in a regular section wins over a legacy duplicate.
            if url not in favorites or (favorites[url][0] and not legacy):
                favorites[url] = (legacy, {
                    "id": item["id"], "label": label, "url": url, "search": item["search"],
                })

    return {"favorites": [favorite for _, favorite in favorites.values()], "sections": ordered}


def load_snapshot(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def with_content_date(data, previous, pending, *, set_date):
    for snapshot in (previous, pending):
        content = {key: val for key, val in snapshot.items() if key != "contentUpdated"}
        if data == content:
            return data | ({"contentUpdated": snapshot["contentUpdated"]} if snapshot.get("contentUpdated") else {})
    if set_date:
        return data | {"contentUpdated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-dir", help="read Airtable responses from fixtures")
    parser.add_argument("--pending", help="previously proposed snapshot for the open sync PR")
    parser.add_argument("output", nargs="?", default=SNAPSHOT_PATH)
    args = parser.parse_args()
    from_dir = args.from_dir
    out_path = args.output

    token = os.environ.get("AIRTABLE_TOKEN")
    if not token:
        env_path = os.path.join(HERE, "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AIRTABLE_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not from_dir and not token:
        raise SystemExit("AIRTABLE_TOKEN is not set (or pass --from-dir for a local build)")

    schema = load_schema()
    if not from_dir:
        missing = set(ITEM_METADATA_FIELDS) - schema["tables"]["items"]["fields"].keys()
        if missing:
            raise SystemExit(
                f"Missing Airtable mapping for {', '.join(sorted(missing))}. "
                "Run python3 scripts/init-base.py --refresh."
            )
    data = build(load_tables(schema, from_dir, token), schema)
    data = with_content_date(
        data, load_snapshot(SNAPSHOT_PATH), load_snapshot(args.pending) if args.pending else {},
        set_date=not from_dir,
    )

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

