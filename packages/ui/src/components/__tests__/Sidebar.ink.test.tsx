import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "ink-testing-library";
import { Sidebar } from "../Sidebar.js";
import { BeadsProvider } from "../../hooks/useBeads.js";
import type { BeadsFixture } from "../../types.js";
import {
  SIDEBAR_SHOWS_HEALTH,
  SIDEBAR_EMPTY_PROJECT,
} from "../../generated/fixtures.js";

function renderSidebar(fixture: BeadsFixture) {
  return render(
    <BeadsProvider value={fixture}>
      <Sidebar />
    </BeadsProvider>
  );
}

describe("Sidebar — sidebar-shows-health", () => {
  it("renders health bar, ready queue, and recent commits from a realistic fixture", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_SHOWS_HEALTH);
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
    const { lastFrame } = renderSidebar(SIDEBAR_SHOWS_HEALTH);
    expect(lastFrame()).toMatchSnapshot("sidebar-basic");
  });
});

describe("Sidebar — sidebar-empty-project", () => {
  it("shows 0% complete and No work items placeholder — never NaN", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_EMPTY_PROJECT);
    const frame = lastFrame() ?? "";

    expect(frame).toContain("0% complete");
    expect(frame).toContain("No work items");
    expect(frame).not.toContain("NaN");
  });

  it("matches sidebar-empty snapshot", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_EMPTY_PROJECT);
    expect(lastFrame()).toMatchSnapshot("sidebar-empty");
  });
});
