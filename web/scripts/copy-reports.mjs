// The dashboard shows the committed, generated reports; nothing in it is typed by hand.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
mkdirSync("public/reports", { recursive: true });
for (const name of ["dev", "heldout"]) {
  const src = `../reports/${name}.json`;
  if (existsSync(src)) copyFileSync(src, `public/reports/${name}.json`);
}
