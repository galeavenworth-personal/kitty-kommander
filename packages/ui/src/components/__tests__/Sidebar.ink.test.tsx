import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "ink-testing-library";
import { Sidebar } from "../Sidebar.js";
import { BeadsProvider } from "../../hooks/useBeads.js";
import type { BeadsFixture } from "../../types.js";

const sidebarShowsHealth: BeadsFixture = {
  stats: { total: 20, closed: 12, blocked: 3, in_progress: 2, open: 3 },
  ready: [
    { id: "abc", title: "Fix auth bug", priority: 1 },
    { id: "def", title: "Add logging", priority: 2 },
    { id: "ghi", title: "Update docs", priority: 4 },
  ],
  commits: [{ hash: "f028764", message: "feat: add auth handler" }],
};

const sidebarEmpty: BeadsFixture = {
  stats: { total: 0, closed: 0, blocked: 0, in_progress: 0, open: 0 },
  ready: [],
  commits: [],
};

function renderSidebar(fixture: BeadsFixture) {
  return render(
    <BeadsProvider value={fixture}>
      <Sidebar />
    </BeadsProvider>
  );
}

describe("Sidebar — sidebar-shows-health", () => {
  it("renders health bar, ready queue, and recent commits from a realistic fixture", () => {
    const { lastFrame } = renderSidebar(sidebarShowsHealth);
    const frame = lastFrame() ?? "";

    const requiredSubstrings = [
      "60% complete",
      "12 closed",
      "3 blocked",
      "2 wip",
      "Fix auth bug",
      "Add logging",
      "f028764",
    ];
    for (const s of requiredSubstrings) {
      expect(frame, `expected "${s}" in frame:\n${frame}`).toContain(s);
    }

    expect(frame).not.toContain("NaN");
  });

  it("matches sidebar-basic snapshot", () => {
    const { lastFrame } = renderSidebar(sidebarShowsHealth);
    expect(lastFrame()).toMatchSnapshot("sidebar-basic");
  });
});

describe("Sidebar — sidebar-empty-project", () => {
  it("shows 0% complete and No work items placeholder — never NaN", () => {
    const { lastFrame } = renderSidebar(sidebarEmpty);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("0% complete");
    expect(frame).toContain("No work items");
    expect(frame).not.toContain("NaN");
  });

  it("matches sidebar-empty snapshot", () => {
    const { lastFrame } = renderSidebar(sidebarEmpty);
    expect(lastFrame()).toMatchSnapshot("sidebar-empty");
  });
});
