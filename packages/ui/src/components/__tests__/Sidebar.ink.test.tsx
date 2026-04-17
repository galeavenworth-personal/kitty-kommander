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
import {
  SIDEBAR_SHOWS_HEALTH_EXPECTED,
  SIDEBAR_EMPTY_PROJECT_EXPECTED,
} from "../../generated/assertions.js";

function renderSidebar(fixture: BeadsFixture) {
  return render(
    <BeadsProvider value={fixture}>
      <Sidebar />
    </BeadsProvider>
  );
}

describe("Sidebar — sidebar-shows-health", () => {
  it("renders every contains string from the scenario and no excludes", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_SHOWS_HEALTH);
    const frame = lastFrame() ?? "";

    for (const s of SIDEBAR_SHOWS_HEALTH_EXPECTED.contains) {
      expect(frame, `expected "${s}" in frame:\n${frame}`).toContain(s);
    }
    for (const s of SIDEBAR_SHOWS_HEALTH_EXPECTED.excludes) {
      expect(frame, `expected "${s}" NOT in frame:\n${frame}`).not.toContain(s);
    }
  });

  it("matches the snapshot named by the scenario", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_SHOWS_HEALTH);
    const name = SIDEBAR_SHOWS_HEALTH_EXPECTED.snapshot;
    if (!name) throw new Error("sidebar-shows-health missing snapshot name");
    expect(lastFrame()).toMatchSnapshot(name);
  });
});

describe("Sidebar — sidebar-empty-project", () => {
  it("renders every contains string from the scenario and no excludes", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_EMPTY_PROJECT);
    const frame = lastFrame() ?? "";

    for (const s of SIDEBAR_EMPTY_PROJECT_EXPECTED.contains) {
      expect(frame, `expected "${s}" in frame:\n${frame}`).toContain(s);
    }
    for (const s of SIDEBAR_EMPTY_PROJECT_EXPECTED.excludes) {
      expect(frame, `expected "${s}" NOT in frame:\n${frame}`).not.toContain(s);
    }
  });

  it("matches the snapshot named by the scenario", () => {
    const { lastFrame } = renderSidebar(SIDEBAR_EMPTY_PROJECT);
    const name = SIDEBAR_EMPTY_PROJECT_EXPECTED.snapshot;
    if (!name) throw new Error("sidebar-empty-project missing snapshot name");
    expect(lastFrame()).toMatchSnapshot(name);
  });
});
