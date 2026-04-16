# HANDOFF — Execute the `uib` epic: kitty-kommander v2 rewrite

> Written by the previous cell-leader at the end of a roadmap-review session.
> This is your starting brief. Read it in full before touching code.

## What this handoff is

You are the next kitty-kommander working this repo. The previous session did three
things and stopped deliberately so you'd start with a clean context:

1. Reviewed the v2 design (`design-package/STACK-v2.md`) and confirmed the roadmap.
2. Cleaned up the beads graph — closed 16 orphaned `91t.*` descendants, rewired
   `vxo → dh3` (dropped stale `ae6` edge), added `ae6.1 → uib.1` block, promoted
   `dh3` from feature to epic. Resulting ready queue has the correct top:
   `uib.1` (P1 task) → `6zu` (P1 feature) ∥ `uib.2` (P1 feature) → `uib.3` steel
   thread → `uib.4` + `uib.5` cleanup.
3. Confirmed the rewrite strategy: **in-place**, not a fresh directory. V2 code
   lives alongside v1 in new paths. V1 dies in one atomic commit (`uib.4`) only
   after the steel thread (`uib.3`) goes green.

Your mission is to execute the entire `uib` epic end-to-end, plus `6zu` which is
in the critical path but sits at the top level. When you finish, v2 is live and
v1 is gone.

## Read these first, in this order

1. `design-package/STACK-v2.md` — the architecture contract. Do not improvise on
   anything the spec decides. ~1100 lines, all load-bearing.
2. `design-package/BRIEF.md` — aesthetic + product intent.
3. `design-package/PANELS.md` — panel wireframes for each Ink surface.
4. `CLAUDE.md` — project conventions, beads workflow, session-close protocol.
5. `.claude/agents/cell-leader.md` — how to run the team.
6. `bd memories` — prior session notes worth scanning.

## Mission

Ship v2. Concretely, all of this must be true:

- [ ] `kommander` Go binary exists at `cmd/kommander/`, installed at
      `~/.local/bin/kommander`, passes every CUE CLI scenario.
- [ ] `kommander-ui` TS/React package exists at `packages/ui/`, dual-target
      (Ink + react-dom), passes every CUE UI scenario across all three test tiers.
- [ ] `kommander launch <dir>` opens a kitty session with the four tabs,
      Dashboard runs Ink apps (not Python), no tmux anywhere.
- [ ] `kommander doctor` reports healthy against CUE desired state.
- [ ] `kommander reload` reconciles drift (verified by scenario).
- [ ] `--help` output is compiled from scenario `help_summary` fields.
- [ ] v1 "Dies" artifacts from STACK-v2.md §"What Moves, What Stays, What Dies"
      are deleted in a single commit gated on the steel thread passing.
- [ ] `CLAUDE.md` and `skills/*/SKILL.md` rewritten for v2 (no tmux refs, no
      Python dashboard refs, `kommander pane` replaces `cockpit-panes.sh`, etc).
- [ ] `install.sh` still produces a working install.
- [ ] All changes pushed to GitHub `origin/main`, beads state pushed to the
      operator's private Dolt remote (see `.claude/local/HANDOFF-local.md`
      — gitignored — for the URL and auth setup).

## The beads you own

From `bd list --status=open`:

| ID | Type | Title | Blocked by |
|---|---|---|---|
| `uib` | epic | kommander Go+CUE rewrite — power tool binary | — |
| `uib.1` | task | CUE scenario schema + steel thread scenarios | — (start here) |
| `uib.2` | feature | React UI package — Ink + react-dom dual-target | `uib.1` |
| `6zu` | feature | Phase 1: Go module skeleton + CUE schema + launch/reload/doctor | `uib.1` |
| `uib.3` | feature | Steel thread — end-to-end vertical slice | `6zu`, `uib.2` |
| `uib.4` | task | Dead code removal — tmux, Python, shell scripts | `uib.3` |
| `uib.5` | task | Update CLAUDE.md + skill docs for v2 | `uib.3` |

`dh3`, `i8x`, `ae6*`, `vxo*` are downstream. Not your problem until v2 ships.

## Team structure — you must use the cell-leader architecture

This epic is too large for a solo op. Use `TeamCreate` + `Agent` with `team_name`.
Team size cap is four. Read `.claude/agents/cell-leader.md` before spawning.

Phasing (adapt as you learn):

### Phase 1 — Schema foundation (`uib.1`)
**Do this alone, or with one teammate only.** The CUE scenario schema is the seed
for three parallel efforts (Go, React, and future notebook work). Over-specify it.
Underspecification cascades into rework.

- Define `#Scenario`, `#UIScenario`, `#Setup`, `#Expected`, `#KittyEffect`,
  `#BeadsFixture`, `#PlaywrightAssertion` in `schema/cli/types.cue` and
  `packages/ui/schema/types.cue`.
- Author steel-thread scenarios: `launch-basic`, `launch-missing-dir`,
  `doctor-healthy`, `doctor-drift-detected`, `reload-reconcile`,
  `sidebar-shows-health`, `sidebar-empty-project`.
- `cue vet schema/` must pass.
- Commit. Push to GitHub. `bd close uib.1`.

### Phase 2 — Parallel build (`6zu` + `uib.2`)
**Spawn two teammates.** They work in parallel, both consuming Phase 1 CUE.

Teammate A: `go-builder` (subagent_type: `general-purpose`)
- Mission: execute `6zu`. Build `cmd/kommander`, `pkg/kitty` (KittyController),
  `pkg/beads` (BeadsClient), `pkg/cue` (loader + diff), the `launch`, `inspect`,
  `doctor`, `reload`, and `pane` subcommands.
- Every subcommand gets CUE scenarios red → green → help auto-compiles.
- Mock KittyController for scenario tests; real impl shells to `kitten @`.
- Purpose: this is half the steel thread's substrate.
- Constraint: do not touch any file outside `cmd/`, `pkg/`, `schema/cli/`, `go.mod`.
- Constraint: `pane` subcommand is needed for `uib.3`, so include it here even
  though nominally Phase 3 — it's cheap to add now.
- Output: `cd cmd/kommander && go test ./...` green; `kommander --help` shows
  scenario-derived text.
- Escalate: if the CUE schema is inadequate for a real scenario, stop and escalate
  — do not extend the schema unilaterally.

Teammate B: `ui-builder` (subagent_type: `general-purpose`)
- Mission: execute `uib.2`. Build `packages/ui/` dual-target React.
  - `src/hooks/{useBeads,useGitLog,useMutations,useAgents,useCells,useDAGDot,useRefresh}.ts`
  - `src/components/{Sidebar,Dashboard,HelmTopology,HelmStatus,AgentStatus,ProgressBar,ReadyQueue,MutationLog,DAGImage}.tsx`
  - `src/tui/` (Ink entry + adapters, uses ink-picture for kitty graphics)
  - `src/web/` (react-dom entry + adapters + Vite dev server)
  - `src/theme.ts` (Tokyo Night palette — hex values are canonical in STACK-v2 and
    v1 `cockpit_dash.py`'s `PAL` dict; match exactly)
  - `src/types.ts`
  - `test/generated/` (ink-testing-library fixtures from CUE scenarios)
  - `test/tui/`, `test/web/`, `test/hooks/`
- Purpose: half the steel thread, and replaces all v1 Python rendering.
- Constraint: all new code in `packages/ui/` and root `package.json`/`playwright.config.ts`.
  Never modify `scripts/cockpit_dash.py` or the other Python dashboards — frozen.
- Constraint: do not pre-split `uib.2` into beads subtasks. Each CUE UI scenario
  is the natural unit of work. Let the scenarios drive decomposition.
- Output: `pnpm test` green for TUI (ink-testing-library), `pnpm test:e2e` green
  for web (Playwright), `vite dev` serves the dashboard.
- Escalate: same schema-gap rule as go-builder.

### Phase 3 — Steel thread (`uib.3`)
**Do this yourself. Do not delegate.** This is the integration gate and the
architecture proof. If you split it, you invent rework.

Verification gates — all three tiers must be green, simultaneously, against the
same scenario set:

1. **Tier 1 (Structural)** — `kommander launch <tmpdir>` then `kommander doctor`.
   JSON output matches scenario `expected.json_paths`.
2. **Tier 2 (Layout)** — `ink-testing-library` `lastFrame()` matches golden
   files for Sidebar with both `sidebar-shows-health` and `sidebar-empty-project`
   fixtures.
3. **Tier 3 (Visual)** — `npx playwright test` against the Vite-served web build
   passes the same Sidebar screenshots.

Plus: `kommander --help` output contains scenario-derived text (proving the help
auto-compilation path works). Plus: modify the CUE config (e.g. remove the
Sidebar window), run `kommander reload`, confirm reconciliation.

Record a short screen capture or `inspector screenshot` of Tier 1–3 passing and
attach to the bead close reason. Visible proof matters.

### Phase 4 — Cleanup (`uib.4` + `uib.5`)
**Two teammates, one landing.** Do these together. Dead code removal and docs
rewrite is one cut-over.

Teammate C: `deleter` (subagent_type: `general-purpose`)
- Mission: `uib.4`. Delete every artifact in STACK-v2.md's "Dies" table, in a
  single commit. Also update `install.sh` to drop the v1 scripts and add symlinks
  for `kommander` and `kommander-ui`.
- Constraint: refuse to start if Tier 1–3 are not all green.
- Constraint: do not remove anything from the "Stays" list. If unsure, read the
  spec and ask.

Teammate D: `scribe` (subagent_type: `general-purpose`)
- Mission: `uib.5`. Rewrite `CLAUDE.md` for v2 — kitty-only control plane, two
  runtimes, Ink apps in Dashboard, three-tier testing. Rewrite each
  `skills/*/SKILL.md` — `cockpit` (kitty windows not tmux panes, `kommander pane`
  not `cockpit-panes.sh`), `view` (ink-picture not timg mentions where relevant),
  `plot` (rendering references), `notebook` (euporie integration path updated).
- Constraint: no new doc files. Rewrite in place.
- Output: `CLAUDE.md` and `skills/*/SKILL.md` updated; diff is large but every
  change traces to STACK-v2.md.

Land C and D in the same PR. When merged, `bd close uib.4 uib.5 uib.3 uib uib.1 uib.2 6zu`.

## Hard rules (do not negotiate with yourself)

1. **Scenarios before code.** Every subcommand, every component. Write scenario →
   `cue vet` → generate test → red → implement → green → help auto-compiles.
   If a teammate is coding without a scenario in `schema/`, stop them.

2. **Two runtimes, clean separation.** Go does lifecycle. React does UI. They do
   not call each other. They share state via filesystem (beads, CUE) and via
   kitty remote control (Go launches React processes).

3. **In-place rewrite.** All new code in `cmd/`, `pkg/`, `schema/`, `packages/ui/`,
   and root `go.mod`/`package.json`/`playwright.config.ts`. Do not touch v1 files
   (scripts/, config/tmux/, DESIGN-multi-cell.md, STACK.md) until `uib.4` removes
   them atomically. **Patching v1 mid-rewrite is the failure mode — don't.**

4. **Steel thread is one bead.** Do not decompose `uib.3` into subtasks.

5. **`uib.2` stays as one bead.** Scenarios decompose it naturally. Resist the
   urge to create `uib.2.1` through `uib.2.N`.

6. **Tokyo Night palette is canonical.** Hex values match across STACK-v2.md,
   v1 `cockpit_dash.py` `PAL` dict, `tmux.conf` (until deleted), and graphviz
   colors. Background `#1a1b26`, accent `#7aa2f7`, red `#f7768e`, green
   `#9ece6a`, yellow `#e0af68`, grey `#565f89`. Do not invent new shades.

7. **`/usr/bin/timg`** is the explicit path to use if any remaining v1 script
   touches image rendering during the transition. Bare `timg` may resolve to a
   Python shim. This is documented in CLAUDE.md — preserve the rule.

8. **Session close protocol.** Per CLAUDE.md: `git pull --rebase && bd dolt push &&
   git push`. Work is NOT done until `git push` succeeds. Push after every phase,
   not just at the end.

9. **Dolt remote is operator-private — do not commit its URL to git.** The
   Dolt remote targets the operator's own infrastructure. All URLs, hostnames,
   IPs, auth tokens, and related notes live in `.claude/local/HANDOFF-local.md`
   (gitignored). Before your first `bd dolt push`, read that file and run
   `bd dolt remote add origin <URL from local file>`. Until configured, local
   `.beads/` is still durable (Dolt auto-versions it), just not replicated.
   **Never put private infra details in any file that will be committed.**

10. **No TaskCreate/TaskList/TaskUpdate.** Use `bd` for work tracking. Beads
    replaces those. This is in CLAUDE.md.

## Checkpoints — report to the operator between each

- ✅ After `uib.1` lands: "`cue vet schema/` green, N scenarios authored, pushed."
- ✅ After `6zu` + `uib.2` both land: "Both paths green against scenarios,
     pushed, ready to integrate."
- ✅ **After `uib.3` steel thread turns green:** "All three tiers passing:
     Tier 1 [doctor output], Tier 2 [golden file match], Tier 3 [Playwright
     screenshot match]. Help text compiles." **This is the big demonstration —
     attach visual proof.**
- ✅ After `uib.4` + `uib.5` land: "V1 removed in commit X, docs rewritten in
     commit Y, `install.sh` produces a working install, epic closed."

## Dependencies to install

Check before starting Phase 2:

- Go 1.22+ (`go version`)
- Node.js 20+ and pnpm (`node --version`, `pnpm --version`)
- cue CLI (`cue version` — should be v0.8+)
- Playwright will install its browsers on first run

If anything is missing, tell the operator — don't apt-get blindly.

## What you should NOT do

- Spawn more than four teammates.
- Start any work before reading STACK-v2.md end to end.
- Touch v1 files until `uib.4`.
- Decompose `uib.3` or `uib.2` into subtasks.
- Create a new repo or worktree unless explicitly authorized.
- Invent schema extensions — if a scenario needs something the schema doesn't
  express, stop and talk to the operator.
- Skip a test tier. All three must be green for the steel thread.
- Push without running the full test suite locally first.

## What to expect

This is weeks of focused work, not a single session. You will likely compact or
clear context multiple times before it ships. Leave handoff notes as you go —
update this document, or `bd remember` key decisions, so the next cold start
isn't a reconstruction job.

Good luck. The design is solid and the beads graph is clean. Execute the spec.

— previous cell-leader, 2026-04-16
