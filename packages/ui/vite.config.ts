import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "../adapters/index.js": path.resolve(here, "src/adapters/web.tsx"),
      "../adapters/index": path.resolve(here, "src/adapters/web.tsx"),
    },
  },
  root: here,
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});
