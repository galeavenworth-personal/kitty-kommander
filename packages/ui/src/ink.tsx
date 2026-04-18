import React from "react";
import { fileURLToPath } from "node:url";
import { realpathSync } from "node:fs";
import { render } from "ink";
import { Sidebar } from "./components/Sidebar.js";
import { ProductionBeadsProvider } from "./hooks/useBeadsProduction.js";
import { SIDEBAR_READS_REAL_BEADS_STATE_PRODUCTION } from "./generated/production.js";

function productionIntervalMs(): number {
  const polling = SIDEBAR_READS_REAL_BEADS_STATE_PRODUCTION.polling;
  if (polling === undefined) {
    throw new Error(
      "sidebar-reads-real-beads-state scenario missing polling.interval_seconds"
    );
  }
  return polling.interval_seconds * 1000;
}

export function renderSidebar(): void {
  render(
    <ProductionBeadsProvider intervalMs={productionIntervalMs()}>
      <Sidebar />
    </ProductionBeadsProvider>
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

function isEntryPoint(): boolean {
  const entry = process.argv[1];
  if (entry === undefined) return false;
  try {
    return realpathSync(entry) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isEntryPoint()) {
  main(process.argv.slice(2));
}
