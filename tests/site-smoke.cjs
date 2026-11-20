const { chromium } = require("playwright");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    for (const width of [375, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: "light" });
      try {
        await page.goto("http://localhost:8080/");
        assert.deepEqual(await page.locator(".collection-stats dt").allTextContents().then((labels) => labels.slice(0, 2)), ["Links", "Projects"]);

        const searchButton = page.getByRole("button", { name: "Search links", exact: true });
        await searchButton.focus();
        await page.keyboard.press("/");
        const search = page.getByRole("textbox", { name: "Search links and projects" });
        assert.equal(await search.evaluate((element) => document.activeElement === element), true);

        const entry = await page.locator(".item-card").first().evaluate((element) => ({
          title: element.querySelector(".item-title").textContent.trim(),
          description: element.querySelector(".item-description")?.textContent.trim(),
        }));
        await search.fill(entry.description || entry.title);
        await page.locator(".search-result-title").filter({ hasText: entry.title }).first().waitFor();
        await page.keyboard.press("Escape");
        await page.getByRole("dialog").waitFor({ state: "hidden" });
        await page.waitForFunction(() => document.activeElement?.id === "open-search-btn");

        for (const theme of ["light", "dark"]) {
          await page.locator("details").evaluateAll((sections) => sections.forEach((section) => { section.open = true; }));
          assert.equal(await page.locator("html").getAttribute("data-theme"), theme);
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Overflow at ${width}px in ${theme}`);
          if (theme === "light") await page.getByRole("button", { name: "Toggle light and dark mode" }).click();
        }
        await page.reload();
        assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
        assert.equal(await page.locator("details:not([open])").count(), 0);
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
  console.log("Search, focus, themes, accordions, and page width passed at 375px and 1280px.");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
