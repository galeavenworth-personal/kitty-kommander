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
    // vi.resetModules() so the hook's module-scope failure-suppression Set
    // resets between tests. Without this, a test that records a "bd"
    // failure leaves the failureLogged set dirty for the next test.
    vi.resetModules();
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

  it("pins polling cadence to scenario.polling.interval_seconds (boundary-advance probe)", async () => {
    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );

    await vi.advanceTimersByTimeAsync(0);
    const mountCallCount = execFileSyncMock.mock.calls.length;
    expect(mountCallCount).toBeGreaterThan(0);

    // BOUNDARY PROBE: advance to exactly 1ms BEFORE the first tick.
    // A correct hook schedules setInterval(fn, intervalMs), so no tick
    // has fired yet; call count must still equal mountCallCount. A hook
    // that hardcoded setInterval(fn, 1) — ignoring the prop entirely —
    // would have fired ~intervalMs-1 ticks by now, and this assertion
    // would red. This is the auditor-probe-defeating check: without it,
    // the test only proves "calls grew" and passes even when cadence
    // is wrong.
    await vi.advanceTimersByTimeAsync(intervalMs - 1);
    expect(
      execFileSyncMock.mock.calls.length,
      `expected no ticks before t=${intervalMs}ms; got ${execFileSyncMock.mock.calls.length - mountCallCount} extra calls — hook may be ignoring intervalMs prop`
    ).toBe(mountCallCount);

    // Cross the boundary by 1ms — the tick fires exactly here.
    await vi.advanceTimersByTimeAsync(1);

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

describe("ProductionBeadsProvider — shell-failure behavior", () => {
  // Mirror the loud-throw style of the sidebar-reads-real-beads-state block
  // above. A `?? 30` silent fallback would let the test keep passing if
  // someone dropped polling from the scenario — that's the opposite of
  // what scenario-driven tests should do.
  const failureIntervalSeconds =
    SIDEBAR_READS_REAL_BEADS_STATE_PRODUCTION.polling?.interval_seconds;
  if (failureIntervalSeconds === undefined) {
    throw new Error(
      "polling.interval_seconds required for shell-failure tests"
    );
  }
  const intervalMs = failureIntervalSeconds * 1000;

  let stderrWrites: string[];
  const originalStderrWrite = process.stderr.write.bind(process.stderr);

  beforeEach(() => {
    stderrWrites = [];
    // Replace process.stderr.write with a capture fn. We restore in
    // afterEach. Not using vi.spyOn here because the Node stderr write
    // overload signatures don't unify cleanly with vi.spyOn's generics
    // under TS strict — plain assignment is simpler and equally correct.
    process.stderr.write = ((chunk: string | Uint8Array): boolean => {
      stderrWrites.push(typeof chunk === "string" ? chunk : chunk.toString());
      return true;
    }) as typeof process.stderr.write;
    execFileSyncMock.mockReset();
    vi.resetModules();
    vi.useFakeTimers({
      toFake: ["setInterval", "setTimeout", "clearInterval", "clearTimeout"],
    });
  });

  afterEach(() => {
    process.stderr.write = originalStderrWrite;
    vi.useRealTimers();
  });

  function throwExec(status: number, stderrText: string): Error {
    const err = new Error(`mock exec failure (status=${status})`);
    (err as unknown as { status: number }).status = status;
    (err as unknown as { stderr: string }).stderr = stderrText;
    return err;
  }

  it("logs exactly one stderr line per failing command per lifecycle, including exit code + stderr", async () => {
    execFileSyncMock.mockImplementation((command: string) => {
      if (command === "bd") throw throwExec(127, "bd: command not found\n");
      if (command === "git") throw throwExec(128, "fatal: not a git repo\n");
      return "";
    });

    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );
    await vi.advanceTimersByTimeAsync(0);

    // Advance across two polling cycles. Without suppression, each cycle
    // would emit one bd line + one git line (two per cycle × three cycles
    // total counting mount = six lines). With suppression, we expect ONE
    // bd line and ONE git line regardless of cycle count.
    await vi.advanceTimersByTimeAsync(intervalMs);
    await vi.advanceTimersByTimeAsync(intervalMs);

    const bdLines = stderrWrites.filter((s) => s.startsWith("kommander-ui: bd "));
    const gitLines = stderrWrites.filter((s) =>
      s.startsWith("kommander-ui: git ")
    );

    expect(bdLines.length, `bd lines: ${JSON.stringify(bdLines)}`).toBe(1);
    expect(gitLines.length, `git lines: ${JSON.stringify(gitLines)}`).toBe(1);

    const bdLine = bdLines[0];
    if (bdLine === undefined) throw new Error("bd line missing");
    expect(bdLine).toContain("exited 127");
    expect(bdLine).toContain("bd: command not found");

    const gitLine = gitLines[0];
    if (gitLine === undefined) throw new Error("git line missing");
    expect(gitLine).toContain("exited 128");
    expect(gitLine).toContain("fatal: not a git repo");
  });

  it("re-logs a command after a successful run clears its suppression entry", async () => {
    let bdShouldFail = true;
    execFileSyncMock.mockImplementation((command: string) => {
      if (command === "bd") {
        if (bdShouldFail) throw throwExec(1, "transient failure\n");
        return "{}";
      }
      if (command === "git") return "";
      return "";
    });

    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );
    await vi.advanceTimersByTimeAsync(0);

    const linesAfterMount = stderrWrites.filter((s) =>
      s.startsWith("kommander-ui: bd ")
    ).length;
    expect(linesAfterMount).toBe(1);

    // bd recovers — its next invocation succeeds, clearing suppression.
    bdShouldFail = false;
    await vi.advanceTimersByTimeAsync(intervalMs);

    // bd fails again — suppression was cleared, so this re-logs.
    bdShouldFail = true;
    await vi.advanceTimersByTimeAsync(intervalMs);

    const linesAfterRecurrence = stderrWrites.filter((s) =>
      s.startsWith("kommander-ui: bd ")
    ).length;
    expect(
      linesAfterRecurrence,
      `expected 2 bd log lines (one on initial fail, one after recovery-then-fail); got ${linesAfterRecurrence}: ${JSON.stringify(stderrWrites)}`
    ).toBe(2);
  });

  it("keeps polling after a failure (polling is not broken by one transient)", async () => {
    execFileSyncMock.mockImplementation((command: string) => {
      if (command === "bd") throw throwExec(1, "transient\n");
      if (command === "git") return "";
      return "";
    });

    const { ProductionBeadsProvider } = await import("../useBeadsProduction.js");

    render(
      <ProductionBeadsProvider intervalMs={intervalMs}>
        <Text>child</Text>
      </ProductionBeadsProvider>
    );
    await vi.advanceTimersByTimeAsync(0);
    const callsAfterMount = execFileSyncMock.mock.calls.length;

    await vi.advanceTimersByTimeAsync(intervalMs);

    // Every shell (bd×2 + git) is re-attempted on the tick, even though bd
    // failed on mount. That is the contract: one transient does not break
    // polling forever.
    const callsAfterTick = execFileSyncMock.mock.calls.length;
    expect(callsAfterTick).toBeGreaterThan(callsAfterMount);
  });
});
