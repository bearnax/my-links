import { readFile } from "node:fs/promises";

const favoriteIcons = new Map([
  ["www.youtube.com", "static/logos/youtube.png"],
  ["www.twitch.tv", "static/logos/twitch.png"],
  ["www.gmail.com", "static/logos/gmail.webp"],
]);

export default async function () {
  const url = new URL("../../data/links.json", import.meta.url);
  const data = JSON.parse(await readFile(url, "utf8"));
  const destinations = new Set(data.favorites.map((favorite) => favorite.url));
  let projects = 0;

  for (const section of data.sections) {
    for (const item of section.items) {
      if (item.isProject) projects += 1;
      if (item.primaryUrl) destinations.add(item.primaryUrl);
      for (const link of item.links ?? []) destinations.add(link.url);
    }
  }

  for (const favorite of data.favorites) {
    const hostname = URL.canParse(favorite.url) ? new URL(favorite.url).hostname : "";
    favorite.icon = favoriteIcons.get(hostname);
  }

  destinations.delete("");
  const contentDate = process.env.LINKS_PUBLISHED_AT || data.contentUpdated;
  const updated = contentDate && new Date(contentDate);
  data.stats = {
    links: destinations.size,
    projects,
    updated: updated && !Number.isNaN(updated.getTime()) ? {
      iso: updated.toISOString(),
      label: new Intl.DateTimeFormat("en-US", {
        month: "short", day: "numeric", year: "numeric", timeZone: "America/New_York",
      }).format(updated),
    } : null,
  };
  return data;
}
