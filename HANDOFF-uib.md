# HANDOFF — kitty-kommander uib epic, Phase 3 partial — 3.0 / 3.A / 3.B / 3.D shipped

Last updated: end of session that landed uib.3.D (kommander launch spawns fresh kitty from outside) and `kitty-kommander-6g8` (attach-branch audit fix — `--attach` as explicit opt-in).

## Current state

- HEAD: `8ed01d3` (roster deployment rows for 3.D) — tree clean, `main` up to date with `origin/main`
- Phase 3 now ~4/7 shipped by atomic-task count (3.0 / 3.A / 3.B / 3.D closed; 3.C / 3.E / 3.F / 3.G open; 3.DAG deferred)
- Remaining Phase 3 work: uib.3.C, 3.E, 3.F, 3.G. DAG still deferred to uib.3.DAG.

## What shipped this session

| Bead | Commit(s) | Title | Notes |
|---|---|---|---|
| `uib.3.D` (`kitty-kommander-e8v`) | `6455b75` → `07c4c3d` | kommander launch spawns fresh kitty via `--listen-on`; closes kitty's default initial tab | Commit pair. First commit adds `SpawnKitty` / `WaitForSocket` / `NewKittenExecForSocket` in `internal/kitty/exec.go`, subcommand-aware `buildController` in `main.go`, `CloseTab` on Controller interface, initial-tab capture + close in main.go after handler success. Second commit fixes the attach-branch audit finding (see `6g8` below). |
| `kitty-kommander-6g8` (attach audit) | `07c4c3d` | `--attach` flag required for attach-branch; default always spawns; stdout truth-telling | Round-1 leader arbitration treated `KITTY_LISTEN_ON`-in-env as operator opt-in for attach — wrong; env var is default state inside any kitty. Auditor caught via two silent-pollution repros + false-stdout proof. Remediation: `--attach` as explicit flag, default ALWAYS spawns (ignores env), `cli.Env.Socket` + `cli.Env.Mode` carry controller's truthful state, `mode: spawn\|attach` stdout line when Mode set, mock test path unchanged. |

Leader-class work this session:
- `8ed01d3` — roster deployment rows for dev-cell, integrator, steel-thread-auditor (captures the 4-round mission dynamic with honest perf notes)

## Remaining Phase 3 scope

| Bead | Status | Shape |
|---|---|---|
| `uib.3.C` (`kitty-kommander-9vy`) | open, needs leader scenario + arbitration | doctor `winKey` asymmetry — currently title-preferred / cmd0 fallback. Desired windows untitled → cmd0:claude. Live kitty returns process-driven titles → title:"⠂ cell-leader". Keys never match. Arbitration needed: add explicit titles to default.cue's Driver/Notebooks windows, OR make winKey fuzzy-match runtime titles against desired cmd0. Leader drafts scenario (`doctor-against-real-kitty` or similar) that exercises process-title'd actual state; integrator implements. |
| `uib.3.E` (`kitty-kommander-1mj`) | open, blocks 3.G | `kommander-ui --sidebar` currently renders the SIDEBAR_SHOWS_HEALTH fixture in production. Needs a production `useBeads` hook that shells `bd --format=json` (stats, ready, git log). Requires new `#UIScenario.render_mode: "test" \| "production"` schema extension + `gen-scenarios.mjs` update. **Added requirement (from 3.D integrator discovery, persisted in 1mj notes):** `packages/ui/src/ink.tsx:18-22` `renderSidebar()` returns synchronously with no stdin subscription or render loop — process exits immediately and kitty closes the Dashboard tab. 3.E must ALSO make the process stay alive (polling loop OR stdin subscription). Different surface (packages/ui) — could activate ui-builder identity from the roster if the leader wants to parallelize. |
| `uib.3.F` (`kitty-kommander-zhi`) | open, blocks on 3.C all green (3.D shipped) | Integration scenario exercising real `KittenExec` against a real kitty: launch → doctor → reload cycle with green Tier 1. Needs a new `#IntegrationScenario` type OR an annotation on existing scenarios marking "run against real controller." Leader arbitration pending. |
| `uib.3.G` (`kitty-kommander-gx9`) | open, blocks on 3.E + 3.F | Three verification tiers green in one CI-shape run. Final uib.3 gate. |
| `uib.3.DAG` (`kitty-kommander-4ep`) | open, deferred post-uib.3 close | DAG Ink app for Dashboard (`kommander-ui --dag`). Sidebar-alone proves the dual-target thesis; DAG is net-new construction that belongs after the steel thread holds weight. |

## Follow-on beads filed this session (not blocking uib.3)

- **`kitty-kommander-ngj`** (P2) — retire `.kitty-session` layout path; production convergence on Go+CUE launch. Surfaced by integrator's 3.D recon: default.cue and `config/kitty/sessions/kommander.kitty-session` are out of sync (CUE has dynamic-empty Cockpit + bare `claude` in Driver + Sidebar-only Dashboard; session file has tmux-in-Cockpit + `scripts/launch-claude.sh` wrapper + DAG+Sidebar split with `resize_window narrower 10`). 3.D scoped to "kommander launch matches CUE"; convergence (shell-script retirement, tmux-start reassignment, resize-window handling) punted here.
- **`kitty-kommander-dwf`** (P3) — SIGKILL-parent orphan: `kommander launch` leaves orphan kitty when parent killed uncleanly (cleanupOrphan is in-process). Proposed fix: `Pdeathsig` on `SysProcAttr` OR systemd-scope wrapper. Known kernel-shaped limitation; not blocking.
- **`kitty-kommander-0m1`** (P3) — CLI arg-parsing hygiene: launch silently discards extra positional args after `Args[0]`; `--` positional separator unhandled; `--attach=true` becomes a confusing positional dir. Auditor's NN1/NN4 finding during 3.D re-probe. Not 3.D-specific; general pre-existing CLI gap.

All three are priority-low; unblock lane-choice freedom for next session.

## Session-accumulated leader lessons (persistent via `bd memories`)

Two new this session:
- **`implicit-consent-via-env-var-is-not-consent`** — `kommander launch` round-1 arbitration treated `KITTY_LISTEN_ON`-in-env as operator opt-in for attach-branch. Wrong: env var is default state inside any kitty, not conscious opt-in. Real consent is an explicit flag (`--attach`). Silent pollution of unrelated kitty sessions + false stdout is the cost. See uib.3.D audit trail (`kitty-kommander-6g8`) for repro pattern.
- **`bead-lane-ordering-technical-dep-not-visibility-claim`** — uib.3 handoff ordered 3.D first as "smallest, unblocks end-to-end visibility." 3.D ships = fresh kitty with 4 tabs — but Dashboard tab dies immediately because `kommander-ui --sidebar` is a one-shot stub (fixture-only, no render loop). 3.E is the lane that makes the stub production + long-running. True visibility needs 3.E FIRST, not 3.D. Lesson: "smallest technical lift" ≠ "shortest path to visible demo." When sequencing partial-ship lanes, check what content fills each slot, not just what frame exists.

Prior lessons still live (search `bd memories <keyword>`):
- `premature-schema-decisions-are-not-free`
- `verification-stronger-than-exit-code`
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

- **Next lane = 3.E** (recommended — see "What the next session should do first" below): activate `ui-builder` + `steel-thread-auditor`. This is frontend-heavy work in `packages/ui/`. Leader-heavy schema work (`#UIScenario.render_mode` extension) precedes implementation.
- **Next lane = 3.C**: activate `integrator` + `steel-thread-auditor`. Same loadout as 3.D; proven.
- **Next lane = 3.F**: activate `integrator` + `steel-thread-auditor`. Integration surface. `ui-builder` not needed.
- **Full-stack parallelization** (3.C + 3.E concurrently): `go-builder` + `ui-builder` + `integrator` + `steel-thread-auditor`. Four-follower cap exactly; no room for fifth. Only attempt if both lanes are clearly independent; otherwise cost exceeds benefit.

**3.D perf this session** (4-round mission — longest integrator cycle to date):
- integrator caught THREE pre-implementation issues via structured challenges (seam divergence recon, env-i Dashboard repro, full-PATH Dashboard root-cause); self-flagged a pre-discipline mishap (attach-branch operator-kitty pollution, 36 stray tabs) that became cornerstone evidence for the subsequent auditor CHALLENGE.
- steel-thread-auditor ran 6 probes + 5 net-new post-fix including code-inspection spot-checks; caught leader round-1 arbitration error on attach-branch with scenario-literal repro + false-stdout proof; refused CLEAR until V9 independently reproduced.
- Team dynamic: leader arbitration errors (two of them — seam under-scope + attach-branch consent) absorbed into remediation cleanly without cascading; both teammates escalated rather than absorbed; lessons persisted downstream.

See `.claude/agents/ROSTER.md` for full roster, cross-team affiliations, and deployment perf notes (including the updated uib.3.D deployment rows added this session at `8ed01d3`).

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

1. **Read**: this file, `bd show kitty-kommander-uib.3`, `design-package/STACK-v2.md` Steel Thread section (lines ~1055-1082), `.claude/agents/ROSTER.md` (updated this session), and recent `bd memories` (`implicit-consent-via-env-var-is-not-consent`, `bead-lane-ordering-technical-dep-not-visibility-claim`, `premature-schema-decisions-are-not-free`, `verification-stronger-than-exit-code`).
2. **Check**: `bd ready --json` for the current ready queue (should show 3.C / 3.E plus the four P2/P3 follow-ons: ngj, dwf, 0m1, and the prior session's four — embed-drift-CI, path-traversal, DriftEntry-empty-title, runner-whitelist).
3. **Pick a lane (updated recommendation per this session's `bead-lane-ordering-technical-dep-not-visibility-claim` lesson)**:
   - **3.E** (biggest technical lift — but largest VISIBILITY gain): production `useBeads` + stay-alive render loop + `#UIScenario.render_mode` schema extension + `gen-scenarios.mjs` update. Turns 3.D's 3-tab state into a 4-tab state with live content. Activate `ui-builder` + `steel-thread-auditor`. Leader schema arbitration precedes implementation.
   - **3.C** (doctor winKey) — needs leader arbitration first; author a `doctor-against-real-kitty` scenario exercising process-title'd actual state. Arbitrate: explicit titles in default.cue OR fuzzy winKey. Then integrator implements. Activate `integrator` + `steel-thread-auditor`.
   - **3.F** (real KittenExec integration) — after 3.C. Depends on 3.D ✓, needs 3.C green. Integrator lane.

**Order now recommended: 3.E first → 3.C → 3.F → 3.G.** This revises the prior handoff's 3.D → 3.C → 3.E order. Reason: 3.D shipped proves the launch frame; the Dashboard slot is empty until 3.E. 3.C can proceed in parallel with 3.E if the leader wants to use the full team — 3.C is backend, 3.E is frontend, minimal overlap.

## Leader lessons from this session (persistent, via bd memories)

Search `bd memories <keyword>` for:

- `implicit-consent-via-env-var-is-not-consent` — env vars represent state, not intent. Opt-in must be an explicit flag. Silent pollution + false stdout is the cost.
- `bead-lane-ordering-technical-dep-not-visibility-claim` — "smallest technical lift" ≠ "shortest path to visible demo." Sequence lanes by what fills each visible slot, not just what builds each frame.
