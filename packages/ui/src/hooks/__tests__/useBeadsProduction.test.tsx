import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "ink-testing-library";
import { Text } from "ink";
import { SIDEBAR_READS_REAL_BEADS_STATE_PRODUCTION } from "../../generated/production.js";
import type { ShellPredicate } from "../../generated/production.js";

const execFileSyncMock = vi.fn();

vi.mock("node:child_process", () => ({
  execFileSync: (...args: unknown[]) => execFileSyncMock(...args),
}));

type Call = {
  command: string;
  args: readonly string[];
};

function recordedCalls(): Call[] {
  return execFileSyncMock.mock.calls.map((call) => {
    const command = call[0];
    const args = call[1];
    if (typeof command !== "string") {
      throw new Error(`unexpected mock call command: ${String(command)}`);
    }
    if (!Array.isArray(args)) {
      throw new Error(`unexpected mock call args: ${String(args)}`);
    }
    return { command, args: args as readonly string[] };
  });
}

function predicateMatchedBy(
  predicate: ShellPredicate,
  calls: readonly Call[]
): boolean {
  for (const call of calls) {
    if (call.command !== predicate.command) continue;
    const joined = call.args.join(" ");
    let allPresent = true;
    for (const needle of predicate.args_contains) {
      if (!joined.includes(needle)) {
        allPresent = false;
        break;
      }
    }
    if (allPresent) return true;
  }
  return false;
}

describe("ProductionBeadsProvider — sidebar-reads-real-beads-state", () => {
  const scenario = SIDEBAR_READS_REAL_BEADS_STATE_PRODUCTION;
  const intervalSeconds = scenario.polling?.interval_seconds;
  if (intervalSeconds === undefined) {
    throw new Error(
      "sidebar-reads-real-beads-state scenario missing polling.interval_seconds"
    );
  }
  const intervalMs = intervalSeconds * 1000;

  beforeEach(() => {
    execFileSyncMock.mockReset();
    execFileSyncMock.mockImplementation((command: string) => {
      if (command === "bd") return "{}";
      if (command === "git") return "";
      return "";
    });
    // Fake only timer APIs — leave microtasks/queueMicrotask real so React
    // can flush useEffect commits after render (ink-testing-library's render
    // returns before effects run; React commits them on a microtask).
    vi.useFakeTimers({
      toFake: ["setInterval", "setTimeout", "clearInterval", "clearTimeout"],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shells every scenario-declared command on mount", async () => {
    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );

    await vi.advanceTimersByTimeAsync(0);

    const calls = recordedCalls();
    for (const predicate of scenario.shells) {
      expect(
        predicateMatchedBy(predicate, calls),
        `expected shell ${predicate.command} with args containing ${JSON.stringify(
          predicate.args_contains
        )}, observed: ${JSON.stringify(calls)}`
      ).toBe(true);
    }
  });

  it("re-shells every scenario-declared command after polling.interval_seconds", async () => {
    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );

    await vi.advanceTimersByTimeAsync(0);
    const mountCallCount = execFileSyncMock.mock.calls.length;
    expect(mountCallCount).toBeGreaterThan(0);

    await vi.advanceTimersByTimeAsync(intervalMs);

    const callsAfterPoll = recordedCalls();
    expect(callsAfterPoll.length).toBeGreaterThan(mountCallCount);

    const postPollOnly = callsAfterPoll.slice(mountCallCount);
    for (const predicate of scenario.shells) {
      expect(
        predicateMatchedBy(predicate, postPollOnly),
        `expected re-shell of ${predicate.command} with args containing ${JSON.stringify(
          predicate.args_contains
        )} after ${intervalMs}ms, observed post-poll: ${JSON.stringify(
          postPollOnly
        )}`
      ).toBe(true);
    }
  });
});
