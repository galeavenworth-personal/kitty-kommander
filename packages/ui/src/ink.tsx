import React from "react";
import { render } from "ink";
import { Sidebar } from "./components/Sidebar.js";
import { BeadsProvider } from "./hooks/useBeads.js";
import type { BeadsFixture } from "./types.js";

const DEMO_FIXTURE: BeadsFixture = {
  stats: { total: 20, closed: 12, blocked: 3, in_progress: 2, open: 3 },
  ready: [
    { id: "abc", title: "Fix auth bug", priority: 1 },
    { id: "def", title: "Add logging", priority: 2 },
    { id: "ghi", title: "Update docs", priority: 4 },
  ],
  commits: [{ hash: "f028764", message: "feat: add auth handler" }],
};

export function renderSidebar(fixture: BeadsFixture = DEMO_FIXTURE): void {
  render(
    <BeadsProvider value={fixture}>
      <Sidebar />
    </BeadsProvider>
  );
}

export function main(argv: readonly string[]): void {
  if (argv.includes("--sidebar")) {
    renderSidebar();
    return;
  }
  process.stderr.write(
    "kommander-ui: unknown command\n" +
      "  usage: kommander-ui --sidebar\n"
  );
  process.exit(2);
}
