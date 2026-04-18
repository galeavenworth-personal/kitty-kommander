# HANDOFF — kitty-kommander uib epic, Phase 3 partial — 3.0 / 3.A / 3.B / 3.D / 3.E shipped

Last updated: end of session that landed uib.3.E (kommander-ui --sidebar production data path — shells bd + git log, polls at CUE-declared cadence, stays alive under kitty).

## Current state

- HEAD: `580f555` (uib.3.E cadence-test strengthen) — tree clean, `main` up to date with `origin/main`
- Phase 3 now ~5/7 shipped by atomic-task count (3.0 / 3.A / 3.B / 3.D / 3.E closed; 3.C / 3.F / 3.G open; 3.DAG deferred)
- Remaining Phase 3 work: uib.3.C, 3.F, 3.G. DAG still deferred to uib.3.DAG.

## What shipped this session

| Bead | Commit(s) | Title | Notes |
|---|---|---|---|
| `uib.3.E` (`kitty-kommander-1mj`) | `630f475` → `d99084d` → `16e2983` → `4f5943c` → `bb2159b` → `580f555` | `kommander-ui --sidebar` production data path | 6-commit stack. `630f475` (leader schema): `#UIScenario.render_mode:*"fixture"|"production"` + `#ProductionAssertion` (shells + polling + stays_alive, no default on stays_alive). Sub-agent drafted `sidebar-reads-real-beads-state` scenario; leader arbitrated two sub-agent-flagged schema frictions pre-commit (dropped duplicate `hook` field, removed silent default on stays_alive). `d99084d`: gen-scenarios.mjs split by render_mode — production scenarios emit to new `generated/production.ts`, NOT fixtures.ts/assertions.ts. `16e2983`: ProductionBeadsProvider wraps existing BeadsContext, shells `bd stats` + `bd ready` + `git log` via execFileSync, polls via setInterval at prop-passed intervalMs (no hardcoded 30 in hook source). `4f5943c`: ink.tsx rewired with ProductionBeadsProvider + isEntryPoint guard; liveness probe `timeout 5 node … --sidebar` → exit 124 (was 0 pre-3.E). `bb2159b`: per-command log-once + stderr on shell failure, recovery clears suppression (leader-arbitrated refinement). `580f555`: cadence-test strengthener after auditor's class-of-bug CHALLENGE — boundary-advance pattern (advance `intervalMs-1` → assert no tick; advance `1` → assert tick) pins to scenario's declared cadence, catches `setInterval(fn, 1)` hardcode mutations. |

Leader-class work this session:
- `630f475` — schema arbitration + scenario (leader-direct + Plan sub-agent dispatch).
- Team dispatched: `uib-3-e` (ui-builder + steel-thread-auditor under dev-cell).
- Auditor's cadence-vacuity CHALLENGE is the session career catch — "eventually, more calls happened" test pattern would have shipped as a class-of-bug into 3 future production scenarios (useGitLog, useCells, useDAGDot).

## Remaining Phase 3 scope

| Bead | Status | Shape |
|---|---|---|
| `uib.3.C` (`kitty-kommander-9vy`) | open, needs leader scenario + arbitration | doctor `winKey` asymmetry — currently title-preferred / cmd0 fallback. Desired windows untitled → cmd0:claude. Live kitty returns process-driven titles → title:"⠂ cell-leader". Keys never match. Arbitration needed: add explicit titles to default.cue's Driver/Notebooks windows, OR make winKey fuzzy-match runtime titles against desired cmd0. Leader drafts scenario (`doctor-against-real-kitty` or similar) that exercises process-title'd actual state; integrator implements. |
| `uib.3.F` (`kitty-kommander-zhi`) | open, blocks on 3.C all green (3.D + 3.E shipped) | Integration scenario exercising real `KittenExec` against a real kitty: launch → doctor → reload cycle with green Tier 1. Needs a new `#IntegrationScenario` type OR an annotation on existing scenarios marking "run against real controller." Leader arbitration pending. |
| `uib.3.G` (`kitty-kommander-gx9`) | open, blocks on 3.F only (3.E shipped) | Three verification tiers green in one CI-shape run. Final uib.3 gate. |
| `uib.3.DAG` (`kitty-kommander-4ep`) | open, deferred post-uib.3 close | DAG Ink app for Dashboard (`kommander-ui --dag`). Sidebar-alone proves the dual-target thesis; DAG is net-new construction that belongs after the steel thread holds weight. |

## Follow-on beads filed this session (not blocking uib.3)

From uib.3.E (this session):
- **`kitty-kommander-upz`** (P2) — stays-alive node-probe test iterating PRODUCTION_LIST. Auditor class-of-bug B: `#ProductionAssertion.stays_alive:true` appears in schema + generated production.ts but is not read by any test — verification lives only in manual `timeout 5 node …` probe. Wire a vitest iterator (PRODUCTION_LIST.filter(stays_alive:true) → execFileSync with timeout → assert throws ETIMEDOUT). May require schema extension classifying production scenarios as "entry" vs "hook." Useful before 3.F for integrator-reproducibility.
- **`kitty-kommander-3jw`** (P3) — `sidebar-tolerates-shell-failure` CUE scenario. 580f555 ships per-command log-once + stderr behavior with 3 vitest tests, but the contract is implementation-defined. Formalize by extending `#ProductionAssertion` with `tolerates_failure` block (per_command_log_once + stderr_line_pattern + recovery_clears_suppression). Not urgent — current tests defend behavior, just not via scenario surface.

From prior sessions (uib.3.D):
- **`kitty-kommander-ngj`** (P2) — retire `.kitty-session` layout path; production convergence on Go+CUE launch. Surfaced by integrator's 3.D recon: default.cue and `config/kitty/sessions/kommander.kitty-session` are out of sync (CUE has dynamic-empty Cockpit + bare `claude` in Driver + Sidebar-only Dashboard; session file has tmux-in-Cockpit + `scripts/launch-claude.sh` wrapper + DAG+Sidebar split with `resize_window narrower 10`). 3.D scoped to "kommander launch matches CUE"; convergence (shell-script retirement, tmux-start reassignment, resize-window handling) punted here.
- **`kitty-kommander-dwf`** (P3) — SIGKILL-parent orphan: `kommander launch` leaves orphan kitty when parent killed uncleanly (cleanupOrphan is in-process). Proposed fix: `Pdeathsig` on `SysProcAttr` OR systemd-scope wrapper. Known kernel-shaped limitation; not blocking.
- **`kitty-kommander-0m1`** (P3) — CLI arg-parsing hygiene: launch silently discards extra positional args after `Args[0]`; `--` positional separator unhandled; `--attach=true` becomes a confusing positional dir. Auditor's NN1/NN4 finding during 3.D re-probe. Not 3.D-specific; general pre-existing CLI gap.

All five are priority-low (except upz at P2); unblock lane-choice freedom for next session.

## Session-accumulated leader lessons (persistent via `bd memories`)

New this session (3.E):
- **`uib-3-e-shipped`** — ProductionBeadsProvider + render_mode schema shipped with auditor-caught cadence-vacuity strengthener. Boundary-advance pattern is the template for every future production-mode cadence test. Without it, `setInterval(fn, 1)` hardcodes ship silently.

Prior session (3.D):
- **`implicit-consent-via-env-var-is-not-consent`** — `kommander launch` round-1 arbitration treated `KITTY_LISTEN_ON`-in-env as operator opt-in for attach-branch. Wrong: env var is default state inside any kitty, not conscious opt-in. Real consent is an explicit flag (`--attach`). Silent pollution of unrelated kitty sessions + false stdout is the cost. See uib.3.D audit trail (`kitty-kommander-6g8`) for repro pattern.
- **`bead-lane-ordering-technical-dep-not-visibility-claim`** — uib.3 handoff ordered 3.D first as "smallest, unblocks end-to-end visibility." 3.D ships = fresh kitty with 4 tabs — but Dashboard tab dies immediately because `kommander-ui --sidebar` is a one-shot stub (fixture-only, no render loop). 3.E is the lane that makes the stub production + long-running. True visibility needs 3.E FIRST, not 3.D. Lesson: "smallest technical lift" ≠ "shortest path to visible demo." When sequencing partial-ship lanes, check what content fills each slot, not just what frame exists. **Confirmed this session** — 3.E shipped and the Dashboard tab now shows live bead state. The visibility payoff was real.

Prior lessons still live (search `bd memories <keyword>`):
- `premature-schema-decisions-are-not-free` — **applied directly this session**: no default on stays_alive.
- `verification-stronger-than-exit-code` — **applied directly this session**: leader reproduced cadence vacuity probe (setInterval(fn, 1) → cadence test reds "got 90000 extra calls").
- `beads-dolt-remote-for-outer-gates-is-not`
- `light-communication-protocol`
- `teammate-identity-as-lens`
- `honor-goal-over-text`
- `leader-as-review-layer`
- `display-model-chain-of-command-helm-all-sub`

## Hard rules for the remainder of Phase 3

- **Scenarios-before-code is still sacrosanct.** Every new `.cue` scenario is authored + committed before its implementation.
- **Three-tier verification is the gate.** Green on Tier 1 (doctor) + Tier 2 (ink-testing-library) + Tier 3 (Playwright) is uib.3.G's definition of done.
- **Trust-but-verify applies leader-downward.** Re-run a teammate's "green" claim yourself with the rigor the claim's failure mode warrants. See 3.D for three concrete applications: leader independently ran `go build`, `go test`, and V8 before propagating integrator's claims; leader independently verified auditor's claimed code at main.go:133-137 before arbitrating.
- **Implicit consent via environment is not consent.** If a behavior should be opt-in, it's opt-in via a typed flag. Env vars represent state, not intent.
- **Lane ordering for partial ships must account for content, not just frame.** Before sequencing a "visible demo" around a lane, verify what process populates each visible slot.

## Team shape for the next session

`dev-cell` is a durable team (capability loadout, not mission-scoped). Default roster: `go-builder`, `ui-builder`, `integrator`, `steel-thread-auditor`.

**Recommended activation depends on lane choice:**

- **Next lane = 3.C**: activate `integrator` + `steel-thread-auditor`. Same loadout as 3.D; proven. Needs leader arbitration first (explicit titles in default.cue OR fuzzy winKey).
- **Next lane = 3.F**: activate `integrator` + `steel-thread-auditor`. Integration surface. `ui-builder` not needed. Blocked on 3.C.
- **Next lane = 3.upz** (stays-alive follow-on, prep for 3.F): activate `ui-builder` + `steel-thread-auditor`. Low-risk, unlocks 3.F's integrator-reproducibility.
- **Full-stack parallelization** (3.C + 3.upz concurrently): `go-builder` + `ui-builder` + `integrator` + `steel-thread-auditor`. Four-follower cap exactly; no room for fifth. Only attempt if both lanes are clearly independent.

**3.E perf this session** (5-commit mission — clean arbitration → impl → challenge → strengthen loop):
- ui-builder shipped 5 tight-scoped commits, surfaced both design questions pre-code (naming + shell-failure behavior), absorbed leader's two refinements (per-command-log-once + stderr) cleanly, no escalations needed.
- steel-thread-auditor ran 7 probes including a class-of-bug CHALLENGE (cadence vacuity) that would have shipped as weak pattern into 3 future production scenarios (useGitLog/useCells/useDAGDot). Auditor's probe pattern (resolveId stub → mutation test) is now re-usable shape.
- Leader absorbed one sub-agent dispatch cleanly (Plan for scenario draft, two schema frictions flagged pre-commit), both frictions arbitrated into the commit without drift.
- Team dynamic: every verification claim leader-reproduced green before propagating (verification-stronger-than-exit-code holding). Mission closed in one session with no rework.

**3.D perf from prior session** (4-round mission — longest integrator cycle to date, retained for reference):
- integrator caught THREE pre-implementation issues via structured challenges (seam divergence recon, env-i Dashboard repro, full-PATH Dashboard root-cause); self-flagged a pre-discipline mishap (attach-branch operator-kitty pollution, 36 stray tabs) that became cornerstone evidence for the subsequent auditor CHALLENGE.
- steel-thread-auditor ran 6 probes + 5 net-new post-fix including code-inspection spot-checks; caught leader round-1 arbitration error on attach-branch with scenario-literal repro + false-stdout proof; refused CLEAR until V9 independently reproduced.
- Team dynamic: leader arbitration errors (two of them — seam under-scope + attach-branch consent) absorbed into remediation cleanly without cascading; both teammates escalated rather than absorbed; lessons persisted downstream.

See `.claude/agents/ROSTER.md` for full roster, cross-team affiliations, and deployment perf notes (including the updated uib.3.E deployment rows).

## Files to know for the remainder of Phase 3

**Launch (uib.3.D — DONE this session, reference):**
- `internal/kitty/exec.go` — `SpawnKitty` (Setsid detach, /dev/null stdio), `WaitForSocket` (50ms poll / 5s cap), `NewKittenExecForSocket`, `KittenExec.CloseTab`.
- `cmd/kommander/main.go` — `extractAttachFlag` helper; `buildController(sub, rest, attachMode bool)` returns (controller, spawnedCmd, initialTabID, socket, mode, err); main.go captures initial tab id post-`WaitForSocket` BEFORE the handler runs; closes initial tab AFTER handler success (only when `spawnedFresh`); `cleanupOrphan` on post-spawn failure.
- `internal/cli/env.go` — added `Socket string` + `Mode string` fields carrying controller's actual state.
- `internal/cli/launch.go` — prints `env.Socket` verbatim (not recomputed slug); emits `mode:` line when `env.Mode` set (mock path keeps empty → line suppressed → scenarios stable).
- `internal/kitty/controller.go` — `CloseTab(selector string) error` added to interface.
- `internal/kitty/mock.go` — `Mock.CloseTab` impl.

**Session schema + loader (uib.3.0 — reference):**
- `schema/session/types.cue` — `#Session`, `#Tab`, `#Window` (contract)
- `schema/session/default.cue` — default 4-tab layout
- `internal/session/loader.go` — go:embed default + `<dir>/kommander.cue` overlay load, simplest-replace
- `internal/session/schema/` — embed copies (drift-guarded by `TestEmbeddedSchemaMatchesSource`)

**Orchestration (uib.3.A — reference for spawnTab):**
- `internal/cli/launch.go:spawnTab` — Windows[0] via LaunchTab + Windows[1:] via LaunchWindow
- `internal/cli/desired.go` — Session → []TabSpec bridge
- `internal/cli/runner.go` — materializes setup.files; honors KittyEffectsExact
- `internal/kitty/exec.go` — LaunchTab / LaunchWindow / CloseWindow / CloseTab / SendText / FocusTab / List

**Doctor / reload (uib.3.C scope):**
- `internal/cli/doctor.go` — `winKey` function (line ~142) is the asymmetry surface
- `schema/cli/doctor.cue` — two scenarios
- `schema/cli/reload.cue` — two scenarios

**Install + CLI:**
- `install.sh` — kommander-ui wrapper write + render-verify
- `packages/ui/bin/kommander-ui` — entry point the wrapper routes through
- `packages/ui/src/ink.tsx` — Ink entry. **Critical for 3.E:** line 18-22 `main(argv)` calls `renderSidebar()` which returns synchronously — no stdin subscription or render loop. Process exits immediately; kitty closes the Dashboard tab. 3.E must make this stay alive.

**Contracts for remaining scope:**
- `schema/cli/launch.cue` — four scenarios (launch-basic, launch-missing-dir, cue-config-driven-layout, launch-multi-window-tab). Attach-mode intentionally NOT scenarized in 3.D — lives in 3.F's real-KittenExec integration scope.
- `schema/cli/types.cue` — `#Scenario`, `#Expected`, `#Setup`, `#KittyEffect`
- `packages/ui/schema/types.cue` + scenarios — 3.E's scope; `render_mode` extension still pending.

## Known non-blockers / pre-existing state

- **Operator tmux session `cockpit-kitty-kommander` was lost** — during integrator's pre-discipline 3.D testing, `kommander launch` with inherited `KITTY_LISTEN_ON` silently injected tabs into the operator's kitty (attach-branch footgun, fixed at `07c4c3d`). Integrator cleaned up 36 stray tabs; the original Cockpit tab with tmux was among the closed ones. Current operator Cockpit tab is a bare `/bin/bash`. Restart with `tmux new-session -s cockpit-kitty-kommander` inside that tab if you want agent-pane visibility.
- **Ghost cockpit panes from `scripts/cockpit-panes.sh`** — the tmux loss above makes this moot for now, but the pattern returns whenever tmux is running: the script is additive, no auto-cleanup on team dissolve. Worth a P3 bead if the pattern annoys you.
- **Dolt remote green** — `bd dolt push` against `http://192.168.1.30:50051/admin/kitty-kommander` works (verified this session).
- **Source `packages/ui/bin/kommander-ui` is CWD-sensitive** — `--import=tsx` resolves tsx via CWD. Wrapper closes the operator path; direct-invocation from outside `packages/ui` still fails for developers. Separately, under stripped PATH (e.g. `env -i`), `tsx` itself can't be resolved. 3.F will force a decision; not filed as a separate bead today.
- **3.D known limitations not blocking close:**
  - Dashboard tab dies immediately after launch because `kommander-ui --sidebar` is a one-shot stub. 3.E-owned. Documented in `kitty-kommander-1mj` notes.
  - `kommander launch` leaves orphan kitty if parent killed with SIGKILL. `kitty-kommander-dwf` P3.

## Session close protocol

Before reporting "done" in the next session:
```bash
git status                    # see what changed
git add <paths>               # scoped, never "git add ."
git commit -m "..."           # scenario-conscious message
git pull --rebase             # integrate anything upstream
bd dolt push                  # expected green per memory
git push                      # mandatory; work isn't done until pushed
```

## What the next session should do first

1. **Read**: this file, `bd show kitty-kommander-uib.3`, `design-package/STACK-v2.md` Steel Thread section (lines ~1055-1082), `.claude/agents/ROSTER.md`, and recent `bd memories` (`uib-3-e-shipped`, `implicit-consent-via-env-var-is-not-consent`, `bead-lane-ordering-technical-dep-not-visibility-claim`, `premature-schema-decisions-are-not-free`, `verification-stronger-than-exit-code`).
2. **Check**: `bd ready --json` for the current ready queue (should show 3.C / 3.F plus the follow-ons: upz (P2), 3jw (P3), ngj (P2), dwf (P3), 0m1 (P3), and prior session's four — embed-drift-CI, path-traversal, DriftEntry-empty-title, runner-whitelist).
3. **Pick a lane**:
   - **3.C** (doctor winKey) — needs leader arbitration first; author a `doctor-against-real-kitty` scenario exercising process-title'd actual state. Arbitrate: explicit titles in default.cue OR fuzzy winKey. Then integrator implements. Activate `integrator` + `steel-thread-auditor`. **This is the clearest next lane** — unblocks 3.F which unblocks 3.G.
   - **3.upz** (stays-alive PRODUCTION_LIST node-probe) — relatively small; converts `stays_alive:true` flag into automated assertion; unblocks 3.F's integrator-reproducibility story. Activate `ui-builder` + `steel-thread-auditor`.
   - **3.F** (real KittenExec integration) — after 3.C. Depends on 3.D ✓ + 3.E ✓, needs 3.C green. Integrator lane.

**Order now recommended: 3.C → 3.F → 3.G.** 3.E shipped this session. 3.upz is optional prep for 3.F. 3.C can run in parallel with 3.upz if leader wants full-team activation — 3.C is backend (integrator), 3.upz is frontend (ui-builder), minimal overlap.

## Leader lessons from this session (persistent, via bd memories)

Search `bd memories <keyword>` for:

- `uib-3-e-shipped` — ProductionBeadsProvider pattern; cadence-test boundary-advance defeat for class-of-bug that would bite future production scenarios.
- `implicit-consent-via-env-var-is-not-consent` (prior) — env vars represent state, not intent. Opt-in must be an explicit flag. Silent pollution + false stdout is the cost.
- `bead-lane-ordering-technical-dep-not-visibility-claim` (prior, **confirmed this session**) — "smallest technical lift" ≠ "shortest path to visible demo." Sequence lanes by what fills each visible slot, not just what builds each frame. 3.E shipped and the Dashboard slot now shows live bead state.
