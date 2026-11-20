import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The live search view talks to the Scala service; the reports are static files.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/v1": process.env.TFS_URL ?? "http://localhost:8080" } },
  preview: { proxy: { "/v1": process.env.TFS_URL ?? "http://localhost:8080" } },
});
