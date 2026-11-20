import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sync_links", ROOT / "scripts/sync-links.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class CollectionSyncTest(unittest.TestCase):
    def test_favorite_migration_and_project_metadata(self):
        schema = json.loads((ROOT / "data/airtable-schema.json").read_text())
        sections = schema["tables"]["sections"]["fields"]
        items = schema["tables"]["items"]["fields"]
        # These aliases are only used by this synthetic test payload.
        items.update({key: key for key in sync.ITEM_METADATA_FIELDS})
        tables = {
            "sections": [
                {"id": "legacy", "fields": {
                    sections["slug"]: "favorites", sections["title"]: "Favorites",
                }},
                {"id": "projects", "fields": {
                    sections["slug"]: "projects", sections["title"]: "Projects",
                }},
            ],
            "items": [
                {"id": "old-favorite", "fields": {
                    items["title"]: "Old name", items["section"]: ["legacy"],
                    items["primaryUrl"]: "https://example.com/",
                }},
                {"id": "current", "fields": {
                    items["title"]: "Project", items["section"]: ["projects"],
                    items["primaryUrl"]: "https://example.com/",
                    items["link1Url"]: "https://example.com/code", items["link1Label"]: "Code",
                    items["description"]: "A sample description.", items["isProject"]: True,
                    items["favorite"]: True, items["presentation"]: "Featured",
                    items["imageUrl"]: "https://assets.example.com/project.webp",
                }},
            ],
        }
        result = sync.build(tables, schema)
        self.assertEqual([item["id"] for item in result["favorites"]], ["current"])
        project = result["sections"][0]["items"][0]
        self.assertEqual(project["id"], "current")
        self.assertEqual(project["presentation"], "featured")
        self.assertEqual(project["description"], "A sample description.")
        self.assertTrue(project["isProject"])
        self.assertEqual(project["imageUrl"], "https://assets.example.com/project.webp")
        self.assertEqual(project["links"], [{"url": "https://example.com/code", "label": "Code"}])

    def test_date_tracks_content_including_deletions(self):
        previous = {"favorites": [{"url": "https://example.com/"}], "sections": [],
                    "contentUpdated": "2020-01-01T00:00:00+00:00"}
        same_content = {key: val for key, val in previous.items() if key != "contentUpdated"}
        self.assertEqual(sync.with_content_date(same_content, previous, {}, set_date=True), previous)

        empty = {"favorites": [], "sections": []}
        after_delete = sync.with_content_date(empty, previous, {}, set_date=True)
        self.assertNotEqual(after_delete["contentUpdated"], previous["contentUpdated"])
        self.assertEqual(sync.with_content_date(empty, previous, after_delete, set_date=True), after_delete)

    def test_image_url_requires_https(self):
        with self.assertRaisesRegex(ValueError, "invalid image URL"):
            sync.validate_url("http://example.com/image", "Example", "image", https_only=True)
