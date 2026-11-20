// Screenshots of the built dashboard for the README: node scripts/screenshots.mjs (with `pnpm preview` running).
import { chromium } from "@playwright/test";
const base = process.env.BASE ?? "http://localhost:8102";
const browser = await chromium.launch(process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {});
const page = await browser.newPage({ viewport: { width: 1360, height: 1000 }, deviceScaleFactor: 1 });
for (const view of ["relevance", "isolation", "cost"]) {
  await page.goto(`${base}/#/${view}`);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `../docs/screenshots/${view}.png`, fullPage: view !== "relevance" });
}
await browser.close();
