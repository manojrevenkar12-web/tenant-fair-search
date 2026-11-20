import { defineConfig } from "@playwright/test";

const PORT = 8102;

export default defineConfig({
  testDir: "e2e",
  timeout: 45_000,
  use: {
    baseURL: `http://localhost:${PORT}`,
    viewport: { width: 1360, height: 900 },
    launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {},
  },
  // the built dashboard with the committed reports; the live search view is answered by route stubs in the tests
  webServer: { command: "pnpm preview", url: `http://localhost:${PORT}`, reuseExistingServer: !process.env.CI, timeout: 60_000 },
  reporter: [["list"]],
});
