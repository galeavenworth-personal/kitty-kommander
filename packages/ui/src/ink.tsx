import React from "react";
import { render } from "ink";
import { Sidebar } from "./components/Sidebar.js";
import { BeadsProvider } from "./hooks/useBeads.js";
import type { BeadsFixture } from "./types.js";
import { SIDEBAR_SHOWS_HEALTH } from "./generated/fixtures.js";

export function renderSidebar(
  fixture: BeadsFixture = SIDEBAR_SHOWS_HEALTH
): void {
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
