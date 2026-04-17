# HANDOFF — kitty-kommander uib epic, Phase 3 partial — 3.0 / 3.A / 3.B shipped

Last updated: end of session that landed uib.3.0 (CUE-driven desired state), uib.3.A (LaunchTab multi-window), uib.3.B (install.sh wrapper for kommander-ui).

## Current state

- HEAD: `99317c3` (uib.3.A) — tree clean, `main` up to date with `origin/main`
- Phase 3 roughly 1/3 shipped by atomic-task count; the foundational thread is proven (CUE-driven state → launch → real Sidebar render from outside `packages/ui/`)
- Remaining Phase 3 work: uib.3.C, 3.D, 3.E, 3.F, 3.G. DAG deferred to uib.3.DAG.

## What shipped this session

| Bead | Commit | Title | Notes |
|---|---|---|---|
| `uib.3.0` | `f8f14d6` | CUE-driven desired state | Session loader with go:embed default + `<dir>/kommander.cue` overlay (simplest-replace). Schema at `schema/session/`. Runner harness also honors setup.files + kitty_effects_exact. |
| `uib.3.B` | `c187816` → `6001761` | install.sh kommander-ui on $PATH | Wrapper script (not symlink) at `~/.local/bin/kommander-ui`, baked-path from $SCRIPT_DIR at install time. Original wrapper had ghost-execution bug (wrong exec target), fix at 6001761 routes through `./bin/kommander-ui` and strengthens smoke check to output-contains assertion. |
| `uib.3.A` | `99317c3` | LaunchTab iterates all windows | spawnTab helper calls LaunchTab with Windows[:1], then LaunchWindow for Windows[1:]. Mirrors `kitten @ launch` semantics (one initial cmd per tab, additional windows via --type=window --match). |

Leader-class work this session:
- `c55542f` + `3cbd44d` + `0bfddaf` — uib.3.0 contract (schema + scenarios + kitty_effects_exact + fixture corrections)
- `d9f9131` — uib.3.A contract (`launch-multi-window-tab` scenario)
- `6940eab` + `9eb0650` + `c4d8315` + `09751f5` — agent identity + roster infrastructure

## Remaining Phase 3 scope

| Bead | Status | Shape |
|---|---|---|
| `uib.3.C` | open, needs leader scenario + arbitration | doctor `winKey` asymmetry — currently title-preferred / cmd0 fallback. Desired windows untitled → cmd0:claude. Live kitty returns process-driven titles → title:"⠂ cell-leader". Keys never match. Arbitration needed: add explicit titles to default.cue's Driver/Notebooks windows, OR make winKey fuzzy-match runtime titles against desired cmd0. Leader drafts scenario (`doctor-against-real-kitty` or similar) that exercises process-title'd actual state; integrator implements. |
| `uib.3.D` | open, blocked on nothing (3.B shipped) | `kommander launch` must spawn a FRESH kitty from outside (`--listen-on=<socket>`), not only attach to `$KITTY_LISTEN_ON`. `launch-basic` already asserts `socket: unix:/tmp/kitty-kommander-<slug>`; current binary prints that line but doesn't actually spawn. Leader may need to extend launch-basic or author a fresh-spawn scenario; integrator wires the spawn. |
| `uib.3.E` | open, blocks 3.G | `kommander-ui --sidebar` currently renders the SIDEBAR_SHOWS_HEALTH fixture in production. Needs a production `useBeads` hook that shells `bd --format=json` (stats, ready, git log). Requires new `#UIScenario.render_mode: "test" \| "production"` schema extension + `gen-scenarios.mjs` update. Different surface (packages/ui) — could activate ui-builder identity from the roster if the leader wants to parallelize. |
| `uib.3.F` | open, blocks on 3.A/3.B/3.C/3.D all green | Integration scenario exercising real `KittenExec` against a real kitty: launch → doctor → reload cycle with green Tier 1. Needs a new `#IntegrationScenario` type OR an annotation on existing scenarios marking "run against real controller." Leader arbitration pending. |
| `uib.3.G` | open, blocks on 3.E + 3.F | Three verification tiers green in one CI-shape run. Final uib.3 gate. |
| `uib.3.DAG` | open, deferred post-uib.3 close | DAG Ink app for Dashboard (`kommander-ui --dag`). Sidebar-alone proves the dual-target thesis; DAG is net-new construction that belongs after the steel thread holds weight. |

## Follow-on beads filed this session (not blocking uib.3)

- **CI enforcement for embed-drift guard** — `internal/session/schema/` embed copies are guarded by `TestEmbeddedSchemaMatchesSource`, but nothing enforces running it pre-commit or in CI. P3.
- **Path-traversal sanitization on setup.files** — `runner.go:materializeFiles` doesn't reject `../` in scenario setup.files keys. Low-severity (scenarios are operator-authored), defense-in-depth. P3.
- **DriftEntry operator-facing message when window title empty** — couples naturally with 3.C's arbitration. Defer until 3.C lands; resolve-or-close-as-superseded then. P3.
- **Runner whitelist on non-empty setup.\* fields** — auditor's class-of-bug catch: `setup.env` and `setup.beads_state` have no runner wiring today; if a future scenario populates them, silent vacuous pass. Preventive panic when first scenario uses those fields. P3.

## Hard rules for the remainder of Phase 3

- **Scenarios-before-code is still sacrosanct.** Every new `.cue` scenario is authored + committed before its implementation.
- **Three-tier verification is the gate.** Green on Tier 1 (doctor) + Tier 2 (ink-testing-library) + Tier 3 (Playwright) is uib.3.G's definition of done.
- **Leader error patterns named this session** (bd memories stored):
  - `premature-schema-decisions-are-not-free` — don't pre-empt another bead's arbitration by choosing one of its resolution paths in advance under "low regret" rationale. Cost materializes at integration, not at review.
  - `verification-stronger-than-exit-code` — leader must hold self to the same probe strength as the auditor is asked to apply. Exit-code-only verification is a ghost-execution trap.
  - `beads-dolt-remote-for-outer-gates-is-not` (updated) — Dolt remote is `http://192.168.1.30:50051/admin/kitty-kommander`. The `:50051` gRPC port is mandatory; port 80 is DoltLab web UI and returns HTML 404. Operator is `admin` on outer-gates.
- **Trust-but-verify applies leader-downward.** Before propagating a teammate's "green" claim upstream (including to the operator), re-run the thing yourself with the rigor the claim's failure mode warrants. If the claim is "wrapper runs from arbitrary CWD," the check is rendered-output-contains, not `echo $?`.

## Team shape for the next session

`dev-cell` is a durable team (capability loadout, not mission-scoped). Default roster: `go-builder`, `ui-builder`, `integrator`, `steel-thread-auditor`.

**Recommended activation for the next Phase 3 session**: `integrator` + `steel-thread-auditor`, same as this session. Proven perf this session:
- integrator caught two pre-implementation seam hazards (symlink→tsx CWD-sensitivity on 3.B; ghost-execution follow-up after leader's wrong-target brief), absorbed the leader's `verification-stronger-than-exit-code` lesson into 6001761's install.sh smoke check.
- steel-thread-auditor ran adversarial probes (disabled `materializeFiles`, tested stub-mimicry on 3.B smoke check) and produced three class-of-bug follow-ons that wouldn't surface from code-reading alone.

**If the next session activates 3.E (production beads path)**, consider also activating `ui-builder` for the React side. Four-follower cap remains — do NOT exceed.

See `.claude/agents/ROSTER.md` for full roster, cross-team affiliations, and deployment perf notes.

## Files to know for the remainder of Phase 3

**Session schema + loader (uib.3.0 — DONE, reference):**
- `schema/session/types.cue` — `#Session`, `#Tab`, `#Window` (contract)
- `schema/session/default.cue` — default 4-tab layout (Cockpit dynamic / Driver / Notebooks / Dashboard=Sidebar)
- `internal/session/loader.go` — go:embed default + `<dir>/kommander.cue` overlay load, simplest-replace
- `internal/session/schema/` — embed copies (drift-guarded by `TestEmbeddedSchemaMatchesSource`)

**Orchestration (uib.3.A — DONE, reference for spawnTab):**
- `internal/cli/launch.go` — spawnTab helper per tab, handles Windows[0] via LaunchTab + Windows[1:] via LaunchWindow
- `internal/cli/desired.go` — Session → []TabSpec bridge (CUE-sourced, no longer hardcoded)
- `internal/cli/runner.go` — materializes setup.files into project dir; honors KittyEffectsExact
- `internal/kitty/exec.go` — LaunchTab / LaunchWindow / CloseWindow / SendText against real kitten @

**Doctor / reload (uib.3.C scope):**
- `internal/cli/doctor.go` — `winKey` function (line ~142) is the asymmetry surface
- `schema/cli/doctor.cue` — two scenarios; fixtures updated in `0bfddaf` to align with default.cue post-Q2-A
- `schema/cli/reload.cue` — two scenarios; same fixture update

**Install + CLI:**
- `install.sh` — kommander-ui wrapper write + render-verify
- `packages/ui/bin/kommander-ui` — the proper entry point the wrapper routes through
- `packages/ui/src/ink.tsx` — Ink entry, `main(argv)` dispatch on `--sidebar` flag

**Contracts for remaining scope:**
- `schema/cli/launch.cue` — four scenarios (launch-basic, launch-missing-dir, cue-config-driven-layout, launch-multi-window-tab)
- `schema/cli/types.cue` — `#Scenario`, `#Expected`, `#Setup`, `#KittyEffect`. `kitty_effects_exact` added this session (commit `3cbd44d`).
- `packages/ui/schema/types.cue` + scenarios — 3.E's scope; render_mode extension still pending.

## Known non-blockers / pre-existing state

- **Ghost cockpit panes** — tmux panes for `go-builder` and `ui-builder` persist in the Cockpit tab from earlier-session spawns. `scripts/cockpit-panes.sh` is additive; no auto-cleanup on team close. Operator noticed the "4 panes" and asked if there were 4 auditors — actual teammate count was always ≤ 2. Worth filing a bead if this becomes repeated confusion; held at awareness for now.
- **Dolt remote green** — `bd dolt push` against `http://192.168.1.30:50051/admin/kitty-kommander` works. Stored as bd memory.
- **Source `packages/ui/bin/kommander-ui` is CWD-sensitive** — `--import=tsx` resolves tsx via CWD. Wrapper closes the operator path; direct-invocation from outside packages/ui still fails for developers. Not filed (properly ui-builder territory; surfaces when packages/ui/bin/ is next touched).

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

1. **Read**: this file, `bd show kitty-kommander-uib.3`, `design-package/STACK-v2.md` Steel Thread section (lines ~1055-1082), `.claude/agents/ROSTER.md`, and recent `bd memories` (`premature-schema-decisions-are-not-free`, `verification-stronger-than-exit-code`).
2. **Check**: `bd ready --json` for the current ready queue (should show 3.C / 3.D / 3.E / 3.DAG at minimum; 3.A closed, 3.B closed, 3.0 closed).
3. **Pick a lane**:
   - **3.C** (doctor winKey) — needs leader arbitration first; author a `doctor-against-real-kitty` (or equivalent) scenario that exercises process-title'd actual state. Arbitrate: explicit titles in default.cue OR fuzzy winKey. Then integrator implements.
   - **3.D** (fresh kitty from outside) — doesn't need new leader scenario (launch-basic already has the aspirational stdout); just an integrator implementation pass to actually spawn `kitty --listen-on=<path>`.
   - **3.E** (production beads path) — biggest lift. Needs `#UIScenario.render_mode` schema extension, `gen-scenarios.mjs` update, production `useBeads` hook. Activate ui-builder if parallelizing.

Order I'd recommend: 3.D first (smallest, unblocks end-to-end visibility) → 3.C (next, needed for real-kitty doctor) → 3.E (biggest, can parallelize ui-builder if activating).

## Leader lessons from this session (persistent, via bd memories)

Search `bd memories <keyword>` for:

- `premature-schema-decisions-are-not-free` — pre-empting another bead's arbitration via schema is not low regret; costs materialize at integration.
- `verification-stronger-than-exit-code` — hold self-verification to the same probe strength demanded of the auditor. Exit-code-only is a ghost-execution trap.
- `beads-dolt-remote-for-outer-gates-is-not` — Dolt remote on :50051 gRPC port, `admin` user.
- `light-communication-protocol` — four-shape teammate-to-leader, silence-as-signal, no status reports.
- `teammate-identity-as-lens` — identity out-performs instructions in ambiguity. Save to `.claude/agents/`, update perf notes in ROSTER.
- `honor-goal-over-text` — extend scope for same bug-class, flag the surprising.
- `leader-as-review-layer` — verify before propagating; boundaries are responsibility markers.
- `display-model-chain-of-command-helm-all-sub` — each level sees one level down; never drill through, switch scope.
