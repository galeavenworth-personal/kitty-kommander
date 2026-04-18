// Production stays-alive node probe — upz (uib.3.E follow-on).
//
// What this covers that useBeadsProduction.test.tsx does NOT:
//
//   useBeadsProduction.test.tsx mocks execFileSync and asserts the
//   IN-PROCESS ProductionBeadsProvider component shells the right
//   commands at the right cadence. That proves the MECHANISM, not the
//   ENTRY. Before upz, `ProductionAssertion.stays_alive: true` was an
//   operator-declared intent read only by human eyes and a one-off
//   manual `timeout 5 node …` probe (see uib-3-e-shipped memory).
//
// This file converts that declarative flag into an automated assertion
// by spawning the REAL node entry (`node --import=tsx src/ink.tsx
// <flag>`) under a bounded wall-clock timeout and asserting the OS
// signals back that the process was killed while still running — i.e.,
// it stayed alive. Catches the 3.D regression shape directly:
// renderSidebar() returning synchronously without installing a render
// loop would make the Dashboard tab die on first paint; that shape
// surfaces here as a synchronous exit 0 (no throw), which is treated
// as the named failure mode below.
//
// SCHEMA-EXTENSION CHOICE:
//
// The upz bead named schema extension (`entry?: {flag: string}` on
// #ProductionAssertion) as "may be required". This pass DOES NOT add
// that field. One stays_alive scenario exists today; a test-local
// `{id → flag}` map with an exhaustiveness gate covers it cleanly. If
// a second scenario lands whose shape differs (hook-only with no entry,
// or an entry with multiple flags, or an entry in a different package),
// THAT scenario forces the schema decomposition — at which point the
// shape is clear rather than guessed. See `premature-schema-decisions-
// are-not-free` memory (uib.3.0 cost: 2 teammate round-trips + 1
// corrective commit). Loud-fail beats silent-skip: a new stays_alive
// scenario without a flag entry below reds the exhaustiveness test.

import { describe, it, expect } from "vitest";
import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { PRODUCTION_LIST } from "../../generated/production.js";

// id → ink flag. Expand when a new stays_alive:true scenario lands.
// The exhaustiveness gate below catches omissions.
const STAYS_ALIVE_FLAG: Readonly<Record<string, string>> = {
  "sidebar-reads-real-beads-state": "--sidebar",
};

// Resolve packages/ui/src/ink.tsx from this test file's location.
// __tests__ lives at packages/ui/src/hooks/__tests__/, so src/ink.tsx
// is two levels up.
const here = dirname(fileURLToPath(import.meta.url));
const pkgUiRoot = resolve(here, "../../..");
const inkEntry = resolve(pkgUiRoot, "src/ink.tsx");

// 2000ms — long enough that node + tsx cold-start (~500ms locally) plus
// Ink's first paint finish comfortably before timeout, short enough that
// synchronous-return regressions surface instantly and the test suite
// doesn't pay the full budget per healthy scenario on CI. On this repo
// the entry has been observed to paint within ~800ms and then run
// indefinitely — a 2s timeout means a synchronous-exit regression fails
// in ≪2s (no throw at all), not at 2s.
const PROBE_TIMEOUT_MS = 2000;

describe("production stays_alive:true entries actually stay alive", () => {
  const staysAlive = PRODUCTION_LIST.filter((sc) => sc.stays_alive);

  it("has at least one stays_alive production scenario (sanity)", () => {
    // If this reds, `stays_alive` has lost meaning in the schema or
    // PRODUCTION_LIST shape has drifted. Either way, the rest of this
    // file is covering nothing — surface that loudly.
    expect(staysAlive.length).toBeGreaterThan(0);
  });

  it("every stays_alive scenario has a flag mapping in STAYS_ALIVE_FLAG", () => {
    const missing = staysAlive
      .filter((sc) => !(sc.id in STAYS_ALIVE_FLAG))
      .map((sc) => sc.id);
    expect(
      missing,
      `stays_alive:true scenarios missing from STAYS_ALIVE_FLAG: ${JSON.stringify(missing)}. Add each to the map above — or, if the scenario has no corresponding ink entry, extend #ProductionAssertion with a schema-level entry/hook split (see upz arbitration notes at top of this file).`
    ).toEqual([]);
  });

  // Dynamic per-scenario test. If STAYS_ALIVE_FLAG is missing a mapping,
  // the exhaustiveness test above will red; we skip the broken entry
  // rather than throw a less-helpful "undefined is not a flag" error.
  for (const sc of staysAlive) {
    const flag = STAYS_ALIVE_FLAG[sc.id];
    if (flag === undefined) continue;

    it(`${sc.id}: node --import=tsx src/ink.tsx ${flag} stays alive until SIGTERM`, () => {
      let exitedWithoutThrow = false;
      let thrown: unknown = null;
      let signal: string | null = null;
      let status: number | null = null;
      let code: string | null = null;
      let stderrCaptured = "";

      try {
        execFileSync("node", ["--import=tsx", inkEntry, flag], {
          cwd: pkgUiRoot,
          timeout: PROBE_TIMEOUT_MS,
          // Ignore stdout — Ink writes ANSI sequences we don't want in
          // test output. Pipe stderr so we surface entry-crash messages
          // on a red test.
          stdio: ["ignore", "ignore", "pipe"],
          // Cap stderr buffer at a sensible size; a well-behaved entry
          // writes nothing to stderr during the 2s window.
          maxBuffer: 64 * 1024,
        });
        exitedWithoutThrow = true;
      } catch (err) {
        thrown = err;
        const e = err as {
          signal?: string | null;
          status?: number | null;
          code?: string | null;
          stderr?: Buffer | string | null;
        };
        signal = e.signal ?? null;
        status = e.status ?? null;
        code = e.code ?? null;
        if (e.stderr !== undefined && e.stderr !== null) {
          stderrCaptured =
            typeof e.stderr === "string" ? e.stderr : e.stderr.toString();
        }
      }

      const diag = `${sc.id}: signal=${signal} status=${status} code=${code} stderr=${JSON.stringify(stderrCaptured.slice(0, 400))}`;

      // NAMED FAILURE MODE 1 — synchronous exit 0. This IS the 3.D
      // regression: renderSidebar() returned without installing a
      // render loop; node had nothing keeping the event loop alive.
      expect(
        exitedWithoutThrow,
        `${sc.id}: node entry exited synchronously with status 0 within ${PROBE_TIMEOUT_MS}ms — stays_alive:true violated (the 3.D regression shape). ${diag}`
      ).toBe(false);

      // NAMED FAILURE MODE 2 — self-exit with non-zero status (entry
      // crashed during setup). Would manifest as signal=null, status
      // set. Different bug than "stays alive," but we want a precise
      // red rather than a vague "didn't stay alive."
      expect(
        code,
        `${sc.id}: expected timeout to fire (code=ETIMEDOUT); got code=${code} — entry may have self-crashed before timeout. ${diag}`
      ).toBe("ETIMEDOUT");

      // NAMED FAILURE MODE 3 — killed by the wrong signal. Unlikely
      // in practice (Node sends SIGTERM by default via `killSignal`),
      // but an explicit check means a future runner change that
      // switches to SIGKILL without updating this assertion reds
      // loudly rather than silently weakening the test.
      expect(
        signal,
        `${sc.id}: expected SIGTERM from ${PROBE_TIMEOUT_MS}ms timeout (= still alive when killed); got signal=${signal}. ${diag}`
      ).toBe("SIGTERM");
    });
  }
});
