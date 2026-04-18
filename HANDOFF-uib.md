# HANDOFF — kitty-kommander uib epic, Phase 3 partial — 3.0 / 3.A / 3.B / 3.C / 3.D / 3.E shipped

Last updated: end of session that landed uib.3.C (doctor `winKey` asymmetry fix — CUE now declares window titles, `LaunchTab` emits `--title`, kitty's override beats process OSC 0 escapes, so `kitten @ ls` returns CUE-declared titles verbatim and doctor's winKey matches title-on-both-sides).

## Current state

- HEAD: `7ef139f` (uib.3.C impl: LaunchTab emits --title; default.cue declares window titles) — tree clean, `main` up to date with `origin/main`
- Phase 3 now ~6/7 shipped by atomic-task count (3.0 / 3.A / 3.B / 3.C / 3.D / 3.E closed; 3.F / 3.G open; 3.DAG deferred)
- Remaining Phase 3 work: uib.3.F, 3.G. DAG still deferred to uib.3.DAG.

## What shipped this session

| Bead | Commit(s) | Title | Notes |
|---|---|---|---|
| `uib.3.C` (`kitty-kommander-9vy`) | `9cb98c1` → `7ef139f` | doctor `winKey` asymmetry fix — Option A | Solo-leader mission, no team dispatch. Problem: desired side untitled → `cmd0:claude` winKey; live kitty returned process-driven titles (`⠂ cell-leader` spinner, `euporie-notebook`) → `title:<runtime>` winKey; keys never matched, doctor reported permanent drift on healthy state. **Arbitration path:** leader initially framed as A/B/C options (add CUE titles / fuzzy winKey / per-window opt-out), operator pushed back on "window vs process identity" framing, leader distilled into Option D (layered: title-first with cmd-fallback for dynamic windows). **Decisive move:** operator called "do the live probe before arbitrating" — leader ran a one-shot OSC 0 escape probe and a 10Hz continuous stream probe against a real kitty-launched window; **kitty's `--title` override survived 40+ process-side rewrites in both probes**. That collapsed the 4-option tree to Option A (simplest + confirmed working). `9cb98c1` (scenario, red): new `doctor-healthy-real-titles` scenario declaring full Option A contract — Driver titled "Driver", Notebooks titled "Notebooks", Dashboard/Sidebar titled "Sidebar". Updated `doctor-healthy`, `doctor-drift-detected`, `reload-reconcile`, `reload-noop` fixtures so Driver/Notebooks carry titles (otherwise the drift scenario's `.drift[0]` would be nondeterministic across 3 missing-title windows). Bumped `TestLoadScenarios` doctor count 2→3. `7ef139f` (impl, green): `internal/kitty/exec.go` — `LaunchTab` appends `--title <Windows[0].Title>` when CUE declares one, BEFORE the command argv (kitten positional rule). `schema/session/default.cue` — added `title: "Driver"` and `title: "Notebooks"`; embed copy at `internal/session/schema/default.cue` regenerated via `go generate ./internal/session/`. Post-commit end-to-end probe: spawned real kitty, ran `LaunchTab` via KittenExec, `kitten @ ls` returned `"title": "Driver"` verbatim — kitty honored `--title` even through `claude --agent cell-leader --dangerously-skip-permissions` argv. Trade-off accepted: tab bar shows static "Driver"/"Notebooks" instead of runtime process indicators; operator explicitly OK with losing the claude spinner. |
| `uib.3.E` (`kitty-kommander-1mj`, prior session, for context) | `630f475` → `d99084d` → `16e2983` → `4f5943c` → `bb2159b` → `580f555` | `kommander-ui --sidebar` production data path | 6-commit stack. `630f475` (leader schema): `#UIScenario.render_mode:*"fixture"|"production"` + `#ProductionAssertion` (shells + polling + stays_alive, no default on stays_alive). Sub-agent drafted `sidebar-reads-real-beads-state` scenario; leader arbitrated two sub-agent-flagged schema frictions pre-commit (dropped duplicate `hook` field, removed silent default on stays_alive). `d99084d`: gen-scenarios.mjs split by render_mode — production scenarios emit to new `generated/production.ts`, NOT fixtures.ts/assertions.ts. `16e2983`: ProductionBeadsProvider wraps existing BeadsContext, shells `bd stats` + `bd ready` + `git log` via execFileSync, polls via setInterval at prop-passed intervalMs (no hardcoded 30 in hook source). `4f5943c`: ink.tsx rewired with ProductionBeadsProvider + isEntryPoint guard; liveness probe `timeout 5 node … --sidebar` → exit 124 (was 0 pre-3.E). `bb2159b`: per-command log-once + stderr on shell failure, recovery clears suppression (leader-arbitrated refinement). `580f555`: cadence-test strengthener after auditor's class-of-bug CHALLENGE — boundary-advance pattern. |

Leader-class work this session:
- Solo-leader throughout. No team dispatched (small scenario surface + empirical probe path collapsed the arbitration tree).
- Live kitty probe before arbitration locked in. One-shot OSC 0 + 10Hz continuous stream, both failed to beat `kitty @ launch --title`. That empirical result — not a dialectic — is what picked Option A.
- Bead chain: `kitty-kommander-9vy` closed with reason `Option A shipped; probe-confirmed kitty --title override beats process OSC 0 escapes`.

## Remaining Phase 3 scope

| Bead | Status | Shape |
|---|---|---|
| `uib.3.F` (`kitty-kommander-zhi`) | open, READY (3.C + 3.D + 3.E all shipped) | Integration scenario exercising real `KittenExec` against a real kitty: launch → doctor → reload cycle with green Tier 1. Needs a new `#IntegrationScenario` type OR an annotation on existing scenarios marking "run against real controller." Leader arbitration pending. **3.C's Option A contract locks in the shape of the real-kitty probe** — `doctor-healthy-real-titles` is already the canonical fixture for what a healthy launched kitty should look like. 3.F can reuse that scenario (or a sibling) as the integration target. |
| `uib.3.G` (`kitty-kommander-gx9`) | open, blocks on 3.F only | Three verification tiers green in one CI-shape run. Final uib.3 gate. |
| `uib.3.DAG` (`kitty-kommander-4ep`) | open, deferred post-uib.3 close | DAG Ink app for Dashboard (`kommander-ui --dag`). Sidebar-alone proves the dual-target thesis; DAG is net-new construction that belongs after the steel thread holds weight. |

## Follow-on beads filed this session (not blocking uib.3)

From uib.3.C (this session):
- None filed. The Option A trade-off (static tab bar instead of runtime process indicators) is accepted per operator; dynamic-title opt-out was considered and documented inline in `schema/session/default.cue` header comment ("Omit `title:` on any single window if dynamic titling is wanted for that slot"), but not wired as a scenario until a concrete ask appears.

From uib.3.E (prior session):
- **`kitty-kommander-upz`** (P2) — stays-alive node-probe test iterating PRODUCTION_LIST. Auditor class-of-bug B: `#ProductionAssertion.stays_alive:true` appears in schema + generated production.ts but is not read by any test — verification lives only in manual `timeout 5 node …` probe. Wire a vitest iterator (PRODUCTION_LIST.filter(stays_alive:true) → execFileSync with timeout → assert throws ETIMEDOUT). May require schema extension classifying production scenarios as "entry" vs "hook." Useful before 3.F for integrator-reproducibility.
- **`kitty-kommander-3jw`** (P3) — `sidebar-tolerates-shell-failure` CUE scenario. 580f555 ships per-command log-once + stderr behavior with 3 vitest tests, but the contract is implementation-defined. Formalize by extending `#ProductionAssertion` with `tolerates_failure` block (per_command_log_once + stderr_line_pattern + recovery_clears_suppression). Not urgent — current tests defend behavior, just not via scenario surface.

From prior sessions (uib.3.D):
- **`kitty-kommander-ngj`** (P2) — retire `.kitty-session` layout path; production convergence on Go+CUE launch. Surfaced by integrator's 3.D recon: default.cue and `config/kitty/sessions/kommander.kitty-session` are out of sync (CUE has dynamic-empty Cockpit + bare `claude` in Driver + Sidebar-only Dashboard; session file has tmux-in-Cockpit + `scripts/launch-claude.sh` wrapper + DAG+Sidebar split with `resize_window narrower 10`). 3.D scoped to "kommander launch matches CUE"; convergence (shell-script retirement, tmux-start reassignment, resize-window handling) punted here.
- **`kitty-kommander-dwf`** (P3) — SIGKILL-parent orphan: `kommander launch` leaves orphan kitty when parent killed uncleanly (cleanupOrphan is in-process). Proposed fix: `Pdeathsig` on `SysProcAttr` OR systemd-scope wrapper. Known kernel-shaped limitation; not blocking.
- **`kitty-kommander-0m1`** (P3) — CLI arg-parsing hygiene: launch silently discards extra positional args after `Args[0]`; `--` positional separator unhandled; `--attach=true` becomes a confusing positional dir. Auditor's NN1/NN4 finding during 3.D re-probe. Not 3.D-specific; general pre-existing CLI gap.

All five are priority-low (except upz at P2); unblock lane-choice freedom for next session.

## Session-accumulated leader lessons (persistent via `bd memories`)

New this session (3.C):
- **`uib-3-c-shipped`** — doctor winKey asymmetry resolved via Option A. The transferable lesson is **probe-before-arbitrate when arbitration rests on an empirical question.** 3.C's arbitration tree had four named options (A/B/C/D). The operator cut through it with "do the live probe to see if option A will work — it's a shot at a very easy solution." Two probes (one-shot OSC 0 + 10Hz continuous stream, 40+ process-side rewrites) confirmed kitty's `--title` override is durable, which collapsed A/B/C/D to A in one shot. Without the probe, the team would have shipped a more defensive fallback (Option D layered) and carried incidental complexity forever. **Rule**: if an arbitration node names an assumption about the world (e.g. "process escapes beat kitty's override"), and the assumption is cheap to test, test it before writing the decision doc. Arbitration conversations cost more than the code in small-surface scenarios.

Prior session (3.E):
- **`uib-3-e-shipped`** — ProductionBeadsProvider + render_mode schema shipped with auditor-caught cadence-vacuity strengthener. Boundary-advance pattern is the template for every future production-mode cadence test. Without it, `setInterval(fn, 1)` hardcodes ship silently.

Prior session (3.D):
- **`implicit-consent-via-env-var-is-not-consent`** — `kommander launch` round-1 arbitration treated `KITTY_LISTEN_ON`-in-env as operator opt-in for attach-branch. Wrong: env var is default state inside any kitty, not conscious opt-in. Real consent is an explicit flag (`--attach`). Silent pollution of unrelated kitty sessions + false stdout is the cost. See uib.3.D audit trail (`kitty-kommander-6g8`) for repro pattern.
- **`bead-lane-ordering-technical-dep-not-visibility-claim`** — uib.3 handoff ordered 3.D first as "smallest, unblocks end-to-end visibility." 3.D ships = fresh kitty with 4 tabs — but Dashboard tab dies immediately because `kommander-ui --sidebar` is a one-shot stub (fixture-only, no render loop). 3.E is the lane that makes the stub production + long-running. True visibility needs 3.E FIRST, not 3.D. Lesson: "smallest technical lift" ≠ "shortest path to visible demo." When sequencing partial-ship lanes, check what content fills each slot, not just what frame exists. **Confirmed this session** — 3.E shipped and the Dashboard tab now shows live bead state. The visibility payoff was real.

Prior lessons still live (search `bd memories <keyword>`):
- `premature-schema-decisions-are-not-free`
- `verification-stronger-than-exit-code` — **applied directly this session**: leader ran two separate live kitty probes (one-shot + continuous) before arbitrating, rather than relying on docs-inference about kitty's title precedence.
- `beads-dolt-remote-for-outer-gates-is-not`
- `light-communication-protocol`
- `teammate-identity-as-lens`
- `honor-goal-over-text`
- `leader-as-review-layer`
- `display-model-chain-of-command-helm-all-sub`

## Hard rules for the remainder of Phase 3

- **Scenarios-before-code is still sacrosanct.** Every new `.cue` scenario is authored + committed before its implementation. 3.C followed this: `9cb98c1` red-scenario commit precedes `7ef139f` green-impl commit, both separately reviewable.
- **Probe before you arbitrate** when the arbitration rests on a testable assumption about the runtime. 3.C's "does kitty --title survive OSC 0 escapes?" question had a 10-minute empirical answer; the arbitration dialectic would have run an hour and picked a more defensive path.
- **Three-tier verification is the gate.** Green on Tier 1 (doctor) + Tier 2 (ink-testing-library) + Tier 3 (Playwright) is uib.3.G's definition of done.
- **Trust-but-verify applies leader-downward.** Re-run a teammate's "green" claim yourself with the rigor the claim's failure mode warrants. 3.C: leader ran the end-to-end probe against a real kitty post-commit (not just the mock-path `go test ./...`) to confirm `--title` survived through `claude --agent cell-leader --dangerously-skip-permissions` argv, because kitten `@ launch` positional rules mean a flag placement mistake would be invisible to mock tests but fatal in production.
- **Implicit consent via environment is not consent.** If a behavior should be opt-in, it's opt-in via a typed flag. Env vars represent state, not intent.
- **Lane ordering for partial ships must account for content, not just frame.** Before sequencing a "visible demo" around a lane, verify what process populates each visible slot.

## Team shape for the next session

`dev-cell` is a durable team (capability loadout, not mission-scoped). Default roster: `go-builder`, `ui-builder`, `integrator`, `steel-thread-auditor`.

**Recommended activation depends on lane choice:**

- **Next lane = 3.F** (recommended — now unblocked): activate `integrator` + `steel-thread-auditor`. Integration surface (real `KittenExec` against real kitty). `ui-builder` not needed. 3.C's `doctor-healthy-real-titles` scenario is the already-validated target shape. Leader arbitration needed upfront on scenario form: new `#IntegrationScenario` type OR render-mode-style annotation (`run_against: *"mock"|"real_kitty"`).
- **Next lane = 3.upz** (stays-alive follow-on, prep/companion for 3.F): activate `ui-builder` + `steel-thread-auditor`. Low-risk, unlocks 3.F's integrator-reproducibility. Can run concurrent with 3.F since surfaces don't overlap (upz is packages/ui schema+tests; 3.F is internal/cli/integration).
- **Full-stack parallelization** (3.F + 3.upz concurrently): `integrator` + `steel-thread-auditor` + `ui-builder` for upz lane. Under four-follower cap. Clean split.

**3.C perf this session** (solo-leader, 2-commit mission — probe-cut-short arbitration):
- Leader ran the mission solo, no team dispatch. Scenario surface was small enough and the arbitration question collapsed fast enough under probe pressure that the overhead of spinning dev-cell wouldn't have paid back.
- Operator intervention was the decisive moment ("do the live probe before arbitrating"). Leader had been framing A/B/C/D options in prose; operator re-framed as "test the cheap empirical question first." Two probes, total spend <10 minutes, confirmed Option A. Translation for future solo-leader missions: **when you notice yourself authoring an arbitration doc longer than the code it picks between, the arbitration is the wrong shape.**
- Green discipline held: scenario-before-code split into two separate commits (`9cb98c1` red + `7ef139f` green); mock tests green via `go test ./...`; end-to-end real-kitty probe independently verified `kitten @ ls` returned CUE-declared titles verbatim.

**3.E perf from prior session** (5-commit mission — clean arbitration → impl → challenge → strengthen loop):
- ui-builder shipped 5 tight-scoped commits, surfaced both design questions pre-code (naming + shell-failure behavior), absorbed leader's two refinements (per-command-log-once + stderr) cleanly, no escalations needed.
- steel-thread-auditor ran 7 probes including a class-of-bug CHALLENGE (cadence vacuity) that would have shipped as weak pattern into 3 future production scenarios (useGitLog/useCells/useDAGDot).

**3.D perf from earlier session** (4-round mission — longest integrator cycle to date, retained for reference):
- integrator caught THREE pre-implementation issues via structured challenges; self-flagged a pre-discipline mishap (attach-branch operator-kitty pollution, 36 stray tabs) that became cornerstone evidence for the subsequent auditor CHALLENGE.
- steel-thread-auditor ran 6 probes + 5 net-new post-fix; caught leader round-1 arbitration error on attach-branch with scenario-literal repro + false-stdout proof.

See `.claude/agents/ROSTER.md` for full roster, cross-team affiliations, and deployment perf notes (3.C was solo-leader, no roster row needed; 3.D + 3.E rows are there).

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

**Doctor / reload (uib.3.C — DONE this session, reference):**
- `internal/cli/doctor.go` — `winKey` function (~line 142) left UNCHANGED. 3.C fixed the asymmetry by making the inputs match, not by changing the key function. Title-preferred / cmd0-fallback is still correct; now both sides actually carry the title.
- `internal/kitty/exec.go` — `LaunchTab` now appends `--title <Windows[0].Title>` BEFORE the command argv when CUE declares one. Critical placement detail: kitten `@ launch` treats first non-flag positional as start of child command; `--title` after the argv leaks into child. Explicit comment in source.
- `schema/session/default.cue` — Driver and Notebooks now carry `title: "Driver"` and `title: "Notebooks"`. Sidebar already had `title: "Sidebar"`. Header comment documents Option A contract + probe evidence + accepted trade-off (static tab bar).
- `internal/session/schema/default.cue` — embed copy, drift-guarded. Regenerate via `go generate ./internal/session/` after any change to `schema/session/default.cue`.
- `schema/cli/doctor.cue` — **three** scenarios now (`doctor-healthy`, `doctor-drift-detected`, `doctor-healthy-real-titles`). Third is the executable Option A contract: titled Driver/Notebooks/Sidebar fixture + healthy expectation.
- `schema/cli/reload.cue` — two scenarios (reconcile + noop). Fixtures updated: Driver/Notebooks carry titles (otherwise reload-reconcile's drift detection would see 3 drifts instead of 1, and reload-noop's "0 operations" would be spuriously wrong).
- `internal/scenario/load_test.go` — `TestLoadScenarios` doctor count is **3** (bumped from 2 this session). If the next scenario add doesn't bump this, CI reds — by design.

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

1. **Read**: this file, `bd show kitty-kommander-uib.3`, `design-package/STACK-v2.md` Steel Thread section (lines ~1055-1082), `.claude/agents/ROSTER.md`, and recent `bd memories` (`uib-3-c-shipped`, `uib-3-e-shipped`, `implicit-consent-via-env-var-is-not-consent`, `bead-lane-ordering-technical-dep-not-visibility-claim`, `verification-stronger-than-exit-code`).
2. **Check**: `bd ready --json` for the current ready queue (should show 3.F plus follow-ons: upz (P2), 3jw (P3), ngj (P2), dwf (P3), 0m1 (P3), and prior session's four — embed-drift-CI, path-traversal, DriftEntry-empty-title, runner-whitelist).
3. **Pick a lane**:
   - **3.F** (real KittenExec integration) — **recommended**. Now unblocked by 3.C green. Depends on 3.D ✓ + 3.E ✓ + 3.C ✓. Needs leader arbitration upfront on scenario form (new `#IntegrationScenario` type OR render-mode-style annotation). Activate `integrator` + `steel-thread-auditor`. Unblocks 3.G.
   - **3.upz** (stays-alive PRODUCTION_LIST node-probe) — relatively small; converts `stays_alive:true` flag into automated assertion; unblocks 3.F's integrator-reproducibility story. Can run in parallel with 3.F (ui-builder surface vs integrator surface, minimal overlap).
   - **3.G** (three-tier CI shape) — blocked on 3.F. Final uib.3 gate.

**Order now recommended: 3.F → 3.G.** 3.C shipped this session (doctor winKey). 3.upz is optional prep/companion for 3.F, can run concurrent. Full-team activation (3.F + 3.upz) fits under four-follower cap exactly.

## Leader lessons from this session (persistent, via bd memories)

Search `bd memories <keyword>` for:

- `uib-3-c-shipped` — **new this session**: probe-before-arbitrate when the arbitration rests on a cheap-to-test runtime assumption. Option A shipped via live kitty probe that collapsed a 4-option tree in <10 minutes.
- `uib-3-e-shipped` (prior) — ProductionBeadsProvider pattern; cadence-test boundary-advance defeat for class-of-bug that would bite future production scenarios.
- `implicit-consent-via-env-var-is-not-consent` (prior) — env vars represent state, not intent. Opt-in must be an explicit flag.
- `bead-lane-ordering-technical-dep-not-visibility-claim` (prior) — "smallest technical lift" ≠ "shortest path to visible demo." Sequence lanes by what fills each visible slot, not just what builds each frame.
