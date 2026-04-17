import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webAdapter = path.resolve(here, "src/adapters/web.tsx");

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Depth-agnostic swap: any relative import ending in
    // `adapters`, `adapters/`, `adapters/index`, `adapters/index.js`,
    // or `adapters/index.ts` resolves to the web adapter in the web
    // build. Consumers at any directory depth (../adapters/index.js,
    // ../../adapters/index.js, etc.) all canonicalize to web.tsx.
    // Chose option (i) over conditional exports (ii) because the
    // adapters barrel lives inside this package, not a sibling — so
    // package.json `exports` would add a subpath-shape decision with
    // no upstream payoff. RegExp alias is the minimal fix.
    alias: [
      {
        find: /^(?:\.\.\/)+adapters(?:\/index(?:\.[jt]sx?)?)?$/,
        replacement: webAdapter,
      },
    ],
  },
  root: here,
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});
