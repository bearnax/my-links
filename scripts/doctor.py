#!/usr/bin/env python3
"""Check that this checkout is a correctly configured site.

Usage:
  doctor.py            offline checks only
  doctor.py --online   also verify the Airtable base matches the schema

Standing up a fork touches a handful of things that each fail late and
confusingly: a schema still pointing at the base you copied from, a token
missing a scope, a site.json nobody renamed. This surfaces all of it at once.

Exit status is 1 if anything failed, so it can gate CI.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
API_ROOT = "https://api.airtable.com/v0"

# The values that ship in the template. Still present in a fork means step 1
# of SETUP.md was skipped.
TEMPLATE_TITLE = "Will's Links"
TEMPLATE_BASE = "app1bBKfPU7TpXAgm"

results = []


def check(name, ok, detail="", warn=False):
    results.append((name, ok, detail, warn))
    mark = "ok  " if ok else ("warn" if warn else "FAIL")
    # Detail is the remedy for a failure; printing it beside a pass reads as a
    # contradiction ("ok ... run init-base.py").
    print(f"[{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))
    return ok


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def check_site():
    try:
        site = load("data/site.json")
    except (OSError, ValueError) as e:
        check("data/site.json parses", False, str(e))
        return None

    check("data/site.json parses", True)
    for key in ("title", "brand", "tagline", "storagePrefix"):
        check(f"site.{key} is set", bool(site.get(key)),
              "" if site.get(key) else "see SETUP.md step 1")
    if isinstance(site.get("brand"), list):
        check("site.brand is 1-2 lines", 1 <= len(site["brand"]) <= 2,
              f"got {len(site['brand'])}; more lines will overflow the header",
              warn=True)
    return site


def check_schema(site):
    try:
        schema = load("data/airtable-schema.json")
        spec = load("data/airtable-spec.json")
    except (OSError, ValueError) as e:
        check("data/airtable-schema.json parses", False, str(e))
        return None

    check("data/airtable-schema.json parses", True)

    base_id = schema.get("baseId", "")
    check("schema has a base ID", base_id.startswith("app"),
          f"got {base_id!r}; run scripts/init-base.py")

    # The fork trap: a copied checkout whose schema still addresses the base it
    # was copied from will sync someone else's links over yours.
    if site and base_id == TEMPLATE_BASE and site.get("title") != TEMPLATE_TITLE:
        check("schema points at this site's own base", False,
              "site.json was renamed but the base ID is still the template's — "
              "run scripts/init-base.py to create your own")
    else:
        check("schema points at this site's own base", True)

    # Every key sync-links.py reads must be present, or the sync dies mid-run.
    missing = []
    for table in spec["tables"]:
        live = schema.get("tables", {}).get(table["key"])
        if not live:
            missing.append(table["key"])
            continue
        for field in table["fields"]:
            if field["key"] not in live.get("fields", {}):
                missing.append(f"{table['key']}.{field['key']}")
    check("schema covers every field in the spec", not missing,
          f"missing: {', '.join(missing)}" if missing else "")

    check("statuses match the spec", schema.get("statuses") == spec["statuses"],
          f"{schema.get('statuses')} vs {spec['statuses']}")
    return schema


def check_data():
    try:
        data = load("data/links.json")
    except (OSError, ValueError) as e:
        check("data/links.json parses", False, str(e))
        return
    check("data/links.json parses", True)

    sections = data.get("sections", [])
    check("data/links.json has sections", bool(sections),
          "empty is fine for a brand-new site" if not sections else "", warn=True)

    bad = [s["id"] for s in sections if not s.get("items")]
    check("every section has items", not bad,
          f"empty sections will not render: {', '.join(bad)}" if bad else "",
          warn=True)


def check_online(schema):
    token = os.environ.get("AIRTABLE_TOKEN")
    if not check("AIRTABLE_TOKEN is set", bool(token),
                 "export a token with data.records:read"):
        return

    base_id = schema.get("baseId")
    for key, table in schema.get("tables", {}).items():
        url = f"{API_ROOT}/{base_id}/{table['id']}?pageSize=1&returnFieldsByFieldId=true"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                json.load(response)
            check(f"table {key} is readable", True)
        except urllib.error.HTTPError as e:
            hint = {401: "token is invalid",
                    403: "token lacks data.records:read, or the base is not in its scope",
                    404: "table ID does not exist in this base"}.get(e.code, "")
            check(f"table {key} is readable", False, f"HTTP {e.code} — {hint}")
        except OSError as e:
            check(f"table {key} is readable", False, f"network error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true",
                        help="also call Airtable to verify the schema resolves")
    args = parser.parse_args()

    site = check_site()
    schema = check_schema(site)
    check_data()
    if args.online and schema:
        check_online(schema)

    failures = [r for r in results if not r[1] and not r[3]]
    warnings = [r for r in results if not r[1] and r[3]]
    print(f"\n{len(results) - len(failures) - len(warnings)} passed, "
          f"{len(failures)} failed, {len(warnings)} warning(s)")
    if failures:
        print("\nSee SETUP.md for what each of these means.")
        sys.exit(1)


if __name__ == "__main__":
    main()
