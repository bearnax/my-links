/**
 * Site identity, read from the committed `data/site.json`.
 *
 * This is the fork seam: the template renders whatever is in here, so a new
 * site is a new site.json plus a new airtable-schema.json, with src/ and
 * scripts/ left byte-identical to upstream. Keep it that way — anything that
 * hardcodes a name in a template makes the next upgrade a merge conflict.
 */
import { readFile } from "node:fs/promises";

const REQUIRED = ["title", "brand", "tagline", "storagePrefix"];

export default async function () {
  const url = new URL("../../data/site.json", import.meta.url);
  const site = JSON.parse(await readFile(url, "utf8"));

  // Fail the build rather than shipping a page that says "undefined" in the
  // <title>. A fork that skipped SETUP.md should find out here, not in a tab.
  const missing = REQUIRED.filter((key) => !site[key] || !site[key].length);
  if (missing.length) {
    throw new Error(
      `data/site.json is missing: ${missing.join(", ")}. See SETUP.md step 1.`
    );
  }

  return { lang: "en", ...site };
}
