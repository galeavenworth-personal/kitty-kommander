import React from "react";
import { createRoot } from "react-dom/client";
import { Sidebar } from "./components/Sidebar.js";
import { BeadsProvider } from "./hooks/useBeads.js";
import type { BeadsFixture } from "./types.js";

const ROUTE_FIXTURES: Record<string, BeadsFixture> = {
  "sidebar-shows-health": {
    stats: { total: 20, closed: 12, blocked: 3, in_progress: 2, open: 3 },
    ready: [
      { id: "abc", title: "Fix auth bug", priority: 1 },
      { id: "def", title: "Add logging", priority: 2 },
      { id: "ghi", title: "Update docs", priority: 4 },
    ],
    commits: [{ hash: "f028764", message: "feat: add auth handler" }],
  },
  "sidebar-empty-project": {
    stats: { total: 0, closed: 0, blocked: 0, in_progress: 0, open: 0 },
    ready: [],
    commits: [],
  },
};

function pickFixtureKey(): string {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash && Object.hasOwn(ROUTE_FIXTURES, hash)) return hash;
  const search = new URLSearchParams(window.location.search);
  const q = search.get("fixture");
  if (q && Object.hasOwn(ROUTE_FIXTURES, q)) return q;
  return "sidebar-shows-health";
}

function App(): React.ReactElement {
  const key = pickFixtureKey();
  const fixture = ROUTE_FIXTURES[key];
  if (!fixture) {
    return (
      <div style={{ padding: 24, color: "#f7768e" }}>
        Unknown fixture: {key}
      </div>
    );
  }
  return (
    <div data-fixture={key} className="sidebar-host">
      <BeadsProvider value={fixture}>
        <Sidebar />
      </BeadsProvider>
    </div>
  );
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root missing from index.html");
createRoot(rootEl).render(<App />);
