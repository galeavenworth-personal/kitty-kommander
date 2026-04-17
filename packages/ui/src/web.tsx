import React from "react";
import { createRoot } from "react-dom/client";
import { Sidebar } from "./components/Sidebar.js";
import { BeadsProvider } from "./hooks/useBeads.js";
import { SCENARIOS } from "./generated/fixtures.js";

function pickFixtureKey(): string {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash && Object.hasOwn(SCENARIOS, hash)) return hash;
  const search = new URLSearchParams(window.location.search);
  const q = search.get("fixture");
  if (q && Object.hasOwn(SCENARIOS, q)) return q;
  return "sidebar-shows-health";
}

function App(): React.ReactElement {
  const key = pickFixtureKey();
  const scenario = SCENARIOS[key];
  if (!scenario) {
    return (
      <div style={{ padding: 24, color: "#f7768e" }}>
        Unknown fixture: {key}
      </div>
    );
  }
  return (
    <div data-fixture={key} className="sidebar-host">
      <BeadsProvider value={scenario.fixture}>
        <Sidebar />
      </BeadsProvider>
    </div>
  );
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root missing from index.html");
createRoot(rootEl).render(<App />);
