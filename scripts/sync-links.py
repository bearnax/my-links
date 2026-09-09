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
    """Parse '<string-name> #<color-hex>' into (name, hex)."""
    if not raw:
        return None, None
    m = re.match(r"^([a-zA-Z0-9_-]+)\s+(#[0-9a-fA-F]{3,6})$", raw.strip())
    if not m:
        warn(f"Accent color '{raw}' is not formatted as '<string-name> #<color-hex>'")
        return None, None
    return m.group(1).lower(), m.group(2).lower()


def verify_accent_colors(accent_map, css_path=CSS_PATH):
    """Verify that the accent colors in the css match those parsed from the color hex."""
    if not os.path.exists(css_path):
        warn(f"CSS file not found for accent color verification: {css_path}")
        return
    with open(css_path, encoding="utf-8") as f:
        css = f.read().lower()

    for name, hex_code in accent_map.items():
        pattern = rf"--accent-{re.escape(name)}\s*:\s*(#[0-9a-f]{{3,6}})"
        match = re.search(pattern, css)
        if match:
            found_hex = match.group(1)
            if found_hex != hex_code:
                raise ValueError(
                    f"Accent color '{name}' hex '{hex_code}' does not match CSS value '{found_hex}'"
                )
        elif hex_code not in css:
            raise ValueError(
                f"Accent color '{name}' ({hex_code}) not found in {css_path}"
            )


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
                extra_links.append({"label": label_val, "url": url_val})

        item_data = {
            "title": title,
            "search": search,
        }
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

    # Detect Favorites section: section ordering below favorite (favorites is always top)
    favorites = []
    ordered = []

    for entry in sorted(sections.values(), key=lambda s: s["order"]):
        sec = entry["section"]
        sorted_items = [i["data"] for i in sorted(sec["items"], key=lambda i: i["order"])]

        # If items contains no items, is empty, then do not ingest that section. Ignore it.
        if not sorted_items:
            warn(f"section '{sec['title']}' has no items; ignored")
            continue

        sec["items"] = sorted_items

        if sec["id"].lower() in ("favorites", "favorite") or sec["title"].lower() in ("favorites", "favorite"):
            # Extract to top favorites strip
            for it in sorted_items:
                fav_url = it.get("primaryUrl") or (it["links"][0]["url"] if it.get("links") else "")
                fav_label = it.get("primaryUrlLabel") or it["title"]
                favorites.append({
                    "label": fav_label,
                    "url": fav_url,
                    "search": it.get("search", ""),
                })
        else:
            ordered.append(sec)

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

