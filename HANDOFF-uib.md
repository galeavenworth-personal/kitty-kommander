# HANDOFF — kitty-kommander uib epic, Phase 3 near-complete — 3.0 / 3.A / 3.B / 3.C / 3.D / 3.E / 3.F shipped

Last updated: end of session that landed uib.3.F (integration scenario — real `KittenExec` against real kitty for launch → doctor → reload with `no_change` assertion keyed on `(title, cmd, pid)`; first consumer of `run_modes: ["real_kitty"]`; Option A titles verified surviving claude OSC 0 spinner and euporie process-name relabeling on a live terminal).

## Current state

- HEAD: `c03c3a7` (handoff: uib.3.F shipped — 7/7 Phase 3 atomic tasks complete) — tree clean, `main` up to date with `origin/main`
- Phase 3 now 7/7 atomic tasks shipped (3.0 / 3.A / 3.B / 3.C / 3.D / 3.E / 3.F closed; 3.G open; 3.DAG deferred post-uib.3 close)
- Remaining Phase 3 work: **uib.3.G only**. DAG still deferred to uib.3.DAG.

## What shipped this session

| Bead | Commits | Title | Notes |
|---|---|---|---|
| `uib.3.F` (`kitty-kommander-zhi`) | `b15043a` → `54a9b41` → `e01f6eb` → `ed15eaa` → `73e56ff` → `5c0c7fb` | First-ever real-`KittenExec` integration scenario — `launch-then-doctor-clean` | 6-commit chain, 3 red layers before green, 1 post-green tightening. **Team**: `uib-3-f` (cell-leader + integrator + steel-thread-auditor). **Red chain**: `b15043a` shipped the schema + runner stub (`RunIntegrationScenario` `t.Fatal`'s with a declared-red message); `54a9b41` made `run_modes` required-no-default (leader pre-catch of integrator miss #1 + auditor audit-layer); `e01f6eb` dropped `cmd` from integration fixture and pinned dynamic-tab semantics on `#KittyFixture` (resolution of seams #3+#4 from integrator's live-probe — euporie surfaces as python shebang, kommander-ui surfaces as node wrapper, neither matches the user-facing CUE name; titles are Option A's stable identity, cmd is install-shape noise); `ed15eaa` landed all three of auditor's formal-audit items (b/c/d): PID explicit in `kitty_effects` docstring, `partitionByMode` returns error on empty RunModes instead of silent normalization, `TestValidateScenarioMutex` covers every branch of `validateScenario`. **Green** (`73e56ff`) ships the D1-D4 runner per leader arbitration: (D1) no pre-spawn — `kommander launch` derives the deterministic socket, runner parses it from stdout; (D2) subprocess via TestMain-prebuilt binary, so the full production code path (`buildController`, `os.Exit`, `cleanupOrphan`) is on the tested path, not in-process-handler dispatch; (D3) `diffLsSnapshots` keys on `(title, cmd, pid)` — a destructive reload that closes every tab and respawns it yields identical titles/cmds but fresh PIDs, and PID equality is what catches it; (D4) pre-sweep + `kitten @ close-tab --match all` teardown (kitty 0.43 has no `@ quit`), `t.Cleanup` LIFO-ordered so `os.Remove` runs last. **Green tightening** (`5c0c7fb`) pins `expectsNoChange` predicate with 3 defensive tests — post-green auditor found this gate had no direct test, swapped `len == 1` to `>= 1` showed `TestExpectsNoChangeFalseOnMixed` reds with "non-exclusive marker silently ignored," reverted. **Supporting**: `cleanupOrphan` lifted from `cmd/kommander/main.go` into `internal/kitty/cleanup.go` as `CleanupOrphan(cmd, report)` so production main and the integration harness share teardown semantics. `compareFinalState` refactored into pure `diffFinalState([]string)` so defensive tests exercise comparison directly. `#KittyWindow.cmd` became `cmd?:` optional so absent-means-unasserted can hold. Five defensive unit tests under `//go:build integration`: PID-churn detection + quiet-on-match + empty-title rejection + absent-field non-assertion + dynamic-tab skip — each with weakened-then-reverted tamper evidence in the commit message. **Live evidence**: `kitten @ ls` against the deterministic socket post-launch shows Cockpit carrying the holding shell (`/bin/bash --posix`, dynamic-tab skip), Driver with title `"Driver"` + claude argv + distinct PID, Notebooks with python shebang expansion of euporie, Dashboard/Sidebar with node wrapper expansion — every window has a distinct PID (the diff contract's target). Integration runtime ~0.7s end-to-end on dev host. |

Leader-class work this session:

- **Team activated for the first time in Phase 3.** Scenario surface was big enough and the arbitration questions were layered enough that solo-leader wouldn't have paid back. `integrator` + `steel-thread-auditor` both earned their dispatch — auditor caught three load-bearing pre-red findings (MkdirTemp-vs-stdout-literal collision, `partitionByMode` silent-skip hazard, mutex test missing); integrator surfaced the cmd/argv0 empirical divergence when running the green runner against real kitty.
- **Bridge across post-compaction team-state gap.** The session compacted mid-mission. On resume, integrator had just landed red-correction `54a9b41` and gone idle awaiting cmd arbitration; auditor's formal b15043a audit had landed ~90 seconds later but NOT yet been seen by integrator. Leader's job was to bridge: read both sides, consolidate, dispatch a single arbitration covering (a) my MkdirTemp retraction (auditor #7 conflicted with stdout literal in the scenario — pre-test sweep + deterministic path replaced randomization), (b) cmd drop per my earlier arbitration, (c) green-phase items from the formal audit. Without that bridge, green would have shipped with the socket-isolation hole.
- **Six-commit layered chain vs `--amend`.** Every amendment landed as its own commit — no history rewrites. Red (`b15043a`) → red-correction `run_modes` (`54a9b41`) → red-amendment cmd-drop (`e01f6eb`) → red-amendment auditor b/c/d (`ed15eaa`) → green D1-D4 (`73e56ff`) → green tightening (`5c0c7fb`) → handoff (`c03c3a7`). The audit trail is the record; forcing it into one `--amend`'d commit would have destroyed the dialectic.
- **Tamper-then-revert for every defensive test.** Each defensive assertion's commit message shows the specific weakening that would defeat it and the specific red that appears when the weakening is in place. Four weakening paths in `73e56ff`'s message; one more in `5c0c7fb`'s. Low-cost self-audit; pins what each test actually defends.

## Remaining Phase 3 scope

| Bead | Status | Shape |
|---|---|---|
| `uib.3.G` (`kitty-kommander-gx9`) | open, READY (3.F shipped) | Three verification tiers green in one CI-shape run. Final uib.3 gate. Depends on 3.F ✓. Tier 1 = `go test ./...` mock tier; Tier 2 = vitest + ink-testing-library + `go test -tags=integration ./...`; Tier 3 = Playwright against real browser (sidebar dual-target render). See `kitty-kommander-iez` (P3) — deterministic socket path may need a regex/template stdout assertion or explicit `-parallel=1` guard before CI concurrency is sound. |
| `uib.3.DAG` (`kitty-kommander-4ep`) | open, deferred post-uib.3 close | DAG Ink app for Dashboard (`kommander-ui --dag`). Sidebar-alone proved the dual-target thesis through 3.E + 3.F; DAG is net-new construction that belongs after the steel thread holds weight and 3.G closes. |

## Follow-on beads filed this session (not blocking uib.3.G)

From uib.3.F (this session):

- **`kitty-kommander-433`** (P3) — cmd/argv0 architectural question. When declaring a window's command in CUE, should fixtures carry the user-facing name (`["euporie", "notebook"]`) or the resolved argv (`["/usr/bin/python3", "/home/x/.local/bin/euporie", "notebook"]`)? Today integration fixtures omit `cmd` entirely; doctor mock-path scenarios still declare user-facing. Candidate mitigations captured in the bead: (a) split into `cmd` (declared) + `argv0` (install-dependent, unasserted), (b) mode-aware generator that drops cmd under `run_modes: ["real_kitty"]`, (c) accept the asymmetry and document it. Surfaced by integrator's live-probe seam analysis.
- **`kitty-kommander-9dd`** (P3) — dynamic-tab skip admits 0 or many windows. Today `diffFinalState` treats fixture `windows: []` as "skip per-window assertion for this tab," which silently accepts a regression where Cockpit has zero holding shells (launch never spawned one) OR many (bug in initial-tab-close logic spawns extras). Auditor's post-green concern #5. Candidates: (a) `min_windows: N` on fixture, (b) distinct marker type `dynamic: true` vs empty-list, (c) Cockpit-specific contract once one exists.
- **`kitty-kommander-iez`** (P3) — deterministic socket path creates race under parallel integration runs. `/tmp/kitty-kommander-kommander-integration-test` is contract-pinned by the scenario's stdout literal assertion; `go test -tags=integration -count=N` or CI concurrency will collide on it. Auditor's post-green concern #7. Probably the first bead 3.G touches (CI wiring inherits this constraint). Candidates: (a) stdout assertion becomes regex/template allowing per-test `os.MkdirTemp`, (b) enforced `-parallel=1` on integration-tagged tests via Makefile wrapper or testing.TB invariant.

From uib.3.E (prior session, still open):

- **`kitty-kommander-upz`** (P2) — stays-alive node-probe test iterating PRODUCTION_LIST. Auditor class-of-bug B from 3.E: `#ProductionAssertion.stays_alive:true` appears in schema but isn't read by any test. **3.G may fold this in** — it's a natural Tier-2 companion to 3.F's integration tier.
- **`kitty-kommander-3jw`** (P3) — `sidebar-tolerates-shell-failure` CUE scenario. Formalize 580f555's per-command-log-once behavior by extending `#ProductionAssertion` with `tolerates_failure` block.

From prior sessions (uib.3.D):

- **`kitty-kommander-ngj`** (P2) — retire `.kitty-session` layout path.
- **`kitty-kommander-dwf`** (P3) — SIGKILL-parent orphan cleanup.
- **`kitty-kommander-0m1`** (P3) — CLI arg-parsing hygiene.

Priority-low follow-ons unblock lane-choice freedom for 3.G and post-uib.3 work.

## Session-accumulated leader lessons (persistent via `bd memories`)

New this session (3.F):

- **`uib-3-f-shipped`** — real-`KittenExec` integration scenario shipped via 6-commit layered chain. Six distinct lessons:
  1. **Probe-before-arbitrate carries forward from 3.C.** Seams #3 (euporie python shebang) and #4 (kommander-ui node wrapper) only surfaced when the green runner hit real kitty. Pre-empirical arbitration on argv matching would have picked a brittle contract. The integrator ran the probe; the ensuing arbitration dropped `cmd` from fixture (title is Option A's stable identity, cmd is install-shape noise). Generalize: integration-tier scenarios MUST probe the live system before the schema's assertion surface is finalized.
  2. **"Belt-and-braces going the wrong direction" is a new class-of-bug.** Auditor finding #2 on b15043a: `partitionByMode` silently normalized empty `RunModes` back to `["mock"]`. A "defensive fallback" that REINTRODUCES the exact hazard the upstream check is defending against. Rule: every fallback must be a fail-louder than the thing it catches, not a smooth-over.
  3. **Layered commits preserve dialectic; `--amend` destroys it.** Six commits in 3.F's chain each had a distinct rationale (red stub → `run_modes` required → cmd drop → auditor audit-layer → green → predicate tightening). Squashing would have flattened the audit trail. Operators and future-leaders read this history.
  4. **Tamper-then-revert discipline.** Every defensive test ships with a commit-message excerpt showing the specific weakening and the specific red. Leader verifies by reading the commit message; auditor verifies by running the weakening themselves. Five tamper paths in 3.F green + tightening. High-value pattern.
  5. **Leader-as-message-bridge across compaction boundaries.** This session compacted mid-mission; integrator had gone idle awaiting arbitration; auditor's formal audit had landed AFTER that idle. The audit was addressed-to-leader but its findings were destined-for-integrator. Leader's job on resume was to read both sides, consolidate into one dispatch, arbitrate my own earlier MkdirTemp direction against the auditor's finding #7, and dispatch to integrator before green shipped. Without that bridge, green would have shipped with the socket-isolation hole.
  6. **Subprocess-under-test beats in-process handler dispatch for integration tier.** D2 decision: runner compiles `cmd/kommander` once per test invocation and each step shells out to that binary. This puts `os.Exit`, `buildController`, `cleanupOrphan`, and stderr-wrap on the tested path. A future refactor of main.go that silently breaks socket derivation gets caught at the integration tier, not at user report. Worth remembering for every future "real-binary vs handler-injection" test-shape call.

Prior sessions still live (search `bd memories <keyword>`):

- `uib-3-c-shipped` (prior) — probe-before-arbitrate on testable runtime assumptions.
- `uib-3-e-shipped` (prior) — ProductionBeadsProvider + cadence-test boundary-advance against setInterval(fn, 1) vacuity.
- `implicit-consent-via-env-var-is-not-consent` (prior) — env vars represent state, not intent; opt-in requires a typed flag.
- `bead-lane-ordering-technical-dep-not-visibility-claim` (prior) — "smallest technical lift" ≠ "shortest path to visible demo."
- `premature-schema-decisions-are-not-free`
- `verification-stronger-than-exit-code` — **applied again this session**: 3.F's integration tier asserts on `kitty_effects: [{kind: "no_change"}]` via PID diff, not on exit-code-zero. A destructive reload that respawned every window would exit 0 but fail the PID-delta check.
- `beads-dolt-remote-for-outer-gates-is-not`
- `light-communication-protocol`
- `teammate-identity-as-lens`
- `honor-goal-over-text`
- `leader-as-review-layer`
- `display-model-chain-of-command-helm-all-sub`

## Hard rules for Phase 3 close-out (3.G)

- **Scenarios-before-code remains sacrosanct.** 3.F followed this through six commits; 3.G will need the same discipline when wiring the three-tier CI matrix.
- **Probe before you arbitrate** when the arbitration rests on a testable assumption. 3.F's seam #3/#4 resolution came from the live-probe empirical finding, not from dialectic.
- **Three-tier verification IS uib.3.G's definition of done.** Tier 1 mock (`go test ./...`), Tier 2 integration (`go test -tags=integration ./...` + vitest + ink-testing-library), Tier 3 Playwright. All three green in one CI-shape run.
- **Trust-but-verify applies leader-downward.** Post-push, leader ran `git log` + `git status` + `bd show` on zhi + bead A + bead B before calling mission accomplished. An integrator claiming clean push is not proof of clean push.
- **Implicit consent via environment is not consent.** (3.D rule, still live.)
- **Lane ordering for partial ships must account for content, not just frame.** (3.D rule, still live.)
- **Layered commits over `--amend` when the audit trail matters.** (3.F rule, newly promoted.)
- **Every defensive fallback must fail louder than the thing it catches.** (3.F rule, newly promoted — auditor finding #2's "belt-and-braces going the wrong direction.")
- **Tamper-then-revert evidence in commit messages for every defensive assertion.** (3.F rule, newly promoted.)

## Team shape for the next session

`dev-cell` is a durable team (capability loadout, not mission-scoped). Default roster: `go-builder`, `ui-builder`, `integrator`, `steel-thread-auditor`.

**Recommended activation for 3.G:**

- **Next lane = 3.G** (only remaining Phase 3 lane): activate `integrator` + `steel-thread-auditor` + possibly `ui-builder` for Tier 3 Playwright wiring. 3.G is CI/infra surface — integrator owns the matrix definition, auditor guards against false-green on any tier, ui-builder pulls Playwright into the tier 3 surface if that's still pending from 3.E. Consider `go-builder` as a fourth if Tier 1/Tier 2 go-side interactions need unstitching — probably not, since 3.F already demonstrated the real-kitty runner works. Under four-follower cap.
- **Parallel pre-work option**: if you want to clear follow-on debt before 3.G, `kitty-kommander-iez` (P3, socket isolation) will probably become a 3.G blocker once CI runs `-count=N` or parallel matrix. Cheap to land standalone: regex the stdout assertion in `integration.cue`, let runner use `os.MkdirTemp`. Small enough for solo-leader or single-integrator dispatch.

**3.F perf this session** (6-commit chain, 3-phase red + 2-phase green + handoff, full team):

- `integrator` shipped 5 of 6 commits (all except the first red stub was authored across three pre-dispatch leader arbitrations). Tamper-evidence discipline held across every commit. Filed three follow-on beads (433, 9dd, iez) at green-push time without prompting.
- `steel-thread-auditor` ran 2 formal audit passes (red-commit + post-green) and 1 pre-commit structural review. Caught 3 load-bearing pre-red findings (MkdirTemp-vs-literal, partitionByMode silent-skip, mutex test missing) and 3 post-green tighteners (expectsNoChange unpinned predicate, dynamic-tab-skip semantic too loose, socket-path race under repeated runs). Two of the post-green tighteners landed as follow-on beads; one (expectsNoChange) landed as the pre-push tightening commit `5c0c7fb`.
- Leader ran bridge-across-compaction duty (see lesson 5 above), arbitrated 3 rounds of schema questions, re-ordered the commit chain from integrator's bundled plan into layered form, managed pre-push checklist per CLAUDE.md.

See `.claude/agents/ROSTER.md` for full roster and deployment perf notes.

## Files to know for 3.G

**Integration tier (uib.3.F — DONE this session, reference for 3.G):**

- `internal/cli/runner_integration_test.go` — `RunIntegrationScenario` + `runIntegrationStep` + `diffLsSnapshots` + `diffFinalState` + `preSweepSocket` + `closeKittySession`. Keyed on `(title, cmd, pid)` for `no_change` semantics. D1-D4 shape documented inline.
- `internal/cli/runner_integration_defensive_test.go` — 5 defensive tests (PID churn, quiet on match, empty-title rejection, absent-field non-assertion, dynamic-tab skip) + 3 `expectsNoChange` predicate tests. All `//go:build integration`.
- `internal/cli/testmain_integration_test.go` — TestMain prebuilds `cmd/kommander` binary into `t.TempDir`-scoped path; subprocess path uses it.
- `internal/cli/runner_integration.go` — stub file replaced in green; path retained so build-tag matrix compiles.
- `internal/kitty/cleanup.go` — `CleanupOrphan(cmd *exec.Cmd, report func(string))` exported; main.go and integration harness share it.
- `internal/kitty/controller.go` — `WindowState.PID int` field added; interface method documentation notes PID is load-bearing for `no_change` semantics.
- `internal/kitty/exec.go` — `kitten @ ls` parser populates PID.
- `schema/cli/integration.cue` — `scenarios.integration: [...]` bucket; first scenario `launch-then-doctor-clean` with 3 steps (launch, doctor, reload) and post-chain `final_kitty_state` assertion.
- `schema/cli/types.cue` — `#Scenario.run_modes: [_, ...("mock" | "real_kitty")]` (required, non-empty at vet time, no default); `#Scenario.steps?: [...#Step]` mutex-with-invocation enforced at loader; `#KittyFixture` dynamic-tab docstring; `#Expected.final_kitty_state?: #KittyFixture`; `#Expected.kitty_effects` docstring names PID explicitly under real_kitty mode.
- `internal/scenario/load.go` — `validateScenario(subcmd, sc)` covers mutex + empty-run_modes. Extracted from inline loop for test coverage.
- `internal/scenario/load_test.go` — `TestLoadRejectsEmptyRunModes` + `TestValidateScenarioMutex` pin loader invariants.
- `internal/scenariogen/gen.go` — `partitionByMode` returns error on empty RunModes; `writeIntegrationTestFile` emits `//go:build integration` + `TestScenariosIntegration` per integration-bucket subcmd.

**Launch (uib.3.D — reference):**

- `internal/kitty/exec.go` — `SpawnKitty`, `WaitForSocket`, `NewKittenExecForSocket`.
- `cmd/kommander/main.go` — `buildController(sub, rest, attachMode)`; `cleanupOrphan` wraps `kitty.CleanupOrphan` with `"kommander launch:"` stderr prefix.
- `internal/cli/env.go` — `Socket string` + `Mode string` fields.
- `internal/cli/launch.go` — prints `env.Socket` verbatim; emits `mode:` line when set.

**Session schema (uib.3.0 — reference):**

- `schema/session/types.cue`, `schema/session/default.cue`, `internal/session/loader.go`, `internal/session/schema/` (embed copies, drift-guarded).

**Doctor / reload (uib.3.C — reference):**

- `internal/cli/doctor.go` — `winKey` function unchanged; title-preferred / cmd0-fallback.
- `schema/session/default.cue` — Driver/Notebooks/Sidebar titled per Option A.
- `schema/cli/doctor.cue` — 3 scenarios including `doctor-healthy-real-titles` (executable Option A contract).
- `internal/scenario/load_test.go` — `TestLoadScenarios` doctor count is 3; integration count is 1.

**Production data path (uib.3.E — reference):**

- `packages/ui/src/ink.tsx` — Ink entry with `ProductionBeadsProvider` wrapping; `isEntryPoint` guard keeps the render loop alive.
- `packages/ui/src/*BeadsProvider*.tsx` — production vs fixture providers; `render_mode` annotation on `#UIScenario`.
- `packages/ui/schema/` — `render_mode:*"fixture"|"production"` + `#ProductionAssertion` (shells + polling + stays_alive, no default on stays_alive).

**Install + CLI:**

- `install.sh` — kommander-ui wrapper write + render-verify.
- `packages/ui/bin/kommander-ui` — entry point the wrapper routes through.

**Scenarios + types:**

- `schema/cli/launch.cue` — 4 scenarios (all `run_modes: ["mock"]`).
- `schema/cli/doctor.cue` — 3 scenarios (all `run_modes: ["mock"]`).
- `schema/cli/reload.cue` — 2 scenarios (all `run_modes: ["mock"]`).
- `schema/cli/integration.cue` — 1 scenario (`run_modes: ["real_kitty"]`).
- `schema/cli/types.cue` — `#Scenario`, `#Step`, `#Expected`, `#Setup`, `#KittyEffect`, `#KittyFixture`.
- `packages/ui/schema/types.cue` + scenarios — 3.E's scope; `render_mode` extension still in play for 3.G's Tier 2/Tier 3.

## Known non-blockers / pre-existing state

- **Operator tmux session** — lost during 3.D pre-discipline testing; current operator Cockpit tab is bare `/bin/bash`. Restart with `tmux new-session -s cockpit-kitty-kommander` inside that tab if agent-pane visibility matters.
- **Ghost cockpit panes from `scripts/cockpit-panes.sh`** — script is additive, no auto-cleanup on team dissolve. P3 pattern.
- **Dolt remote green** — `bd dolt push` against `http://192.168.1.30:50051/admin/kitty-kommander` works (verified this session, 7 commits pushed through including handoff).
- **Source `packages/ui/bin/kommander-ui` is CWD-sensitive** — `--import=tsx` resolves tsx via CWD. 3.G may force a decision (ESM resolution in CI vs dev).
- **Integration tier deterministic socket path race** — see `kitty-kommander-iez` (P3). Current design waives via implicit `-p 1`; 3.G CI concurrency will need explicit mitigation. Candidate paths in the bead.
- **Dynamic-tab skip semantic is loose** — see `kitty-kommander-9dd` (P3). Fixture `windows: []` admits any window count in that tab. Not load-bearing for 3.F's Cockpit slot today; becomes a concern if Cockpit grows a defined contract.
- **`cmd` vs `argv0` in real-kitty `kitten @ ls`** — see `kitty-kommander-433` (P3). Integration fixture omits `cmd`; doctor mock-path scenarios still declare user-facing cmd. Asymmetry accepted as the Option A trade-off for 3.F.
- **3.D/3.E known limitations** — `kitty-kommander-dwf` (SIGKILL-parent orphan P3), `kitty-kommander-upz` (stays-alive PRODUCTION_LIST node-probe P2), `kitty-kommander-3jw` (sidebar-tolerates-shell-failure P3), `kitty-kommander-ngj` (`.kitty-session` retire P2), `kitty-kommander-0m1` (CLI arg-parsing P3).

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

Trust-but-verify: re-check `git log`, `git status`, and `bd show` on any closed bead post-push before calling mission accomplished. Teammate "pushed" claims are claim, not proof.

## What the next session should do first

1. **Read**: this file, `bd show kitty-kommander-gx9`, `design-package/STACK-v2.md` Steel Thread section (lines ~1055-1082), `.claude/agents/ROSTER.md`, and recent `bd memories` (`uib-3-f-shipped`, `uib-3-c-shipped`, `uib-3-e-shipped`, `verification-stronger-than-exit-code`, `light-communication-protocol`).
2. **Check**: `bd ready --json` for the current ready queue. Should show 3.G plus follow-ons (433, 9dd, iez from this session; upz P2, 3jw P3, ngj P2, dwf P3, 0m1 P3 from prior sessions).
3. **Pick a lane**:
   - **3.G** (three-tier CI shape) — **recommended and only remaining Phase 3 lane**. Unblocks uib.3 close. Wire Tier 1 + Tier 2 + Tier 3 green in one CI-shape run. Likely first-step concern: `kitty-kommander-iez` (integration socket race) becomes a real blocker under `-count=N` or parallel matrix — consider landing it before or alongside 3.G's CI wiring.
   - **Parallel pre-work** on follow-on debt: `iez` (P3, socket isolation) is the most likely 3.G blocker; `upz` (P2, stays-alive node-probe) is Tier 2 infra that 3.G will want. Both small enough for solo-leader or single-integrator dispatch.
4. **Activate team**: `integrator` + `steel-thread-auditor` (and possibly `ui-builder` for Tier 3 Playwright). See "Team shape for the next session" above.

**Order recommended: 3.G → uib.3 close.** uib.3.DAG remains deferred until after uib.3 closes. Follow-on beads (433, 9dd, iez, upz, 3jw, ngj, dwf, 0m1) can interleave or land parallel as lane-choice freedom allows.

## Leader lessons from this session (persistent, via `bd memories`)

Search `bd memories <keyword>` for:

- `uib-3-f-shipped` — **new this session**: six-commit layered red→amendment→green chain; probe-before-arbitrate at integration tier; "belt-and-braces going the wrong direction" as class-of-bug; leader-as-message-bridge across compaction; subprocess-under-test beats handler-injection for integration tier; tamper-then-revert for every defensive assertion.
- `uib-3-c-shipped` (prior) — probe-before-arbitrate on testable runtime assumptions (applied again this session at seams #3/#4).
- `uib-3-e-shipped` (prior) — ProductionBeadsProvider + cadence-test boundary-advance.
- `implicit-consent-via-env-var-is-not-consent` (prior) — env vars represent state, not intent.
- `bead-lane-ordering-technical-dep-not-visibility-claim` (prior) — "smallest technical lift" ≠ "shortest path to visible demo."
