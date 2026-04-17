# HANDOFF — kitty-kommander uib epic, Phase 3 ready

Last updated: end of session that landed Phases 1-2 + hardening follow-ons.

## Current state

- HEAD: `498098b`
- Tree: clean, `main` up to date with `origin/main`
- Phase 1 (schema) + Phase 2 (parallel builders) + hardening (r6x, 5lg, fta) all merged

## What shipped

| Bead | Title | Status |
|---|---|---|
| `uib.1` | CUE scenario schema + steel-thread scenarios | ✓ closed |
| `uib.2` | React Sidebar dual-target (Tiers 2 + 3) | ✓ closed |
| `6zu` | Go+CUE binary — launch / doctor / reload + scenariogen + --help compiler | ✓ closed |
| `r6x` | Vite alias depth-agnostic + data-testid selector alignment | ✓ closed |
| `5lg` | TS scenariogen — fixtures single-source from CUE | ✓ closed |
| `fta` | TS assertions codegen — inline test literals eliminated | ✓ closed |

## Phase 3 — Steel Thread (`kitty-kommander-uib.3`)

`bd show kitty-kommander-uib.3` is now dependency-clean. Every prereq has shipped. Mission:

1. `kommander launch <dir>` reads CUE → spawns kitty with 4 tabs → Dashboard runs `kommander-ui --sidebar` as an Ink app.
2. `kommander doctor` on the live kitty matches CUE desired state.
3. The Sidebar React component renders the same code through Ink (TUI) AND react-dom (Vite dev server).
4. All three verification tiers pass: `kommander doctor` (Tier 1 structural), ink-testing-library (Tier 2 layout), Playwright (Tier 3 visual).
5. `kommander reload` reconciles drift.
6. `--help` text on all subcommands compiles from scenario `help_summary` (already shipping per 6zu).

**Phase 3 is wiring work, not new construction.** Every part exists; the job is to prove they hold weight when connected.

### Recommended team shape

**Leader solo + steel-thread-auditor on review.**

Reasons:
- Work is largely sequential (can't verify `doctor` before `launch` exists).
- Work is cross-domain (Go, React, kitty, bd, Playwright) — integration is a leader responsibility.
- Spawning a builder for integration adds coordination cost without capacity gain.

Alternative if the operator expects Phase 3 to span multiple sessions: spawn a dedicated `integrator` teammate so the work log stays separated from leader duties.

### Files to know for Phase 3

**Go side (shipped in 6zu):**
- `cmd/kommander/main.go` — binary entry, subcommand dispatch
- `internal/cli/handler.go` — Env + Handler signature (production and tests share the Env shape)
- `internal/kitty/controller.go` — Controller interface
- `internal/kitty/exec.go` — kitten@ shell-out, reads `$KITTY_LISTEN_ON` (never hardcode)
- `internal/kitty/mock.go` — test mock recording effects
- `internal/scenario/` — CUE loader
- `internal/scenariogen/` — `go generate` driven test generator
- `internal/help/` — scenario-driven `--help` compiler

**UI side (shipped in uib.2 + r6x + 5lg + fta):**
- `packages/ui/src/components/Sidebar.tsx` — shared component
- `packages/ui/src/adapters/{ink,web}.tsx` — target-specific adapters; Vite resolves via depth-agnostic regex alias in `vite.config.ts`
- `packages/ui/src/ink.tsx` — TUI entry
- `packages/ui/src/web.tsx` — Vite dev server entry
- `packages/ui/bin/kommander-ui` — Node shebang CLI (`--sidebar` etc.)
- `packages/ui/src/generated/{fixtures,assertions}.ts` — single-source from CUE
- `packages/ui/scripts/gen-scenarios.mjs` — the generator (supports `--check` for drift detection)
- `packages/ui/src/hooks/useBeads.ts` — production path (shells `bd --format=json`); test path (BeadsProvider context)

**Schema (DO NOT EDIT without leader decision — they're the contract):**
- `schema/cli/*.cue` — CLI scenarios (launch, doctor, reload)
- `schema/shared/types.cue` — `#BeadsFixture`
- `packages/ui/schema/*.cue` — UI scenarios (sidebar, expandable)

## Hard rules for Phase 3

- **Scenarios-before-code is still sacrosanct.** If uib.3 needs a new scenario (e.g., a steel-thread-specific integration scenario), author it in CUE first, `cue vet` green, then wire.
- **Three-tier verification is the gate.** Green on all three tiers, or it's not done.
- **No tmux / Python / `cockpit_dash.py` references.** Those die in uib.4. Nothing new should depend on them.
- **Staging discipline**: scoped `git add <paths>`, `git pull --rebase` before commit. Even solo, the habit is cheap.
- **Trust-but-verify claims.** Before propagating teammate (or auditor) claims upstream, re-run the test yourself.

## Reusable agent definitions

Saved to `.claude/agents/` for the next session to spawn via `subagent_type`:
- `go-builder.md` — Go+CUE TDD specialist
- `ui-builder.md` — React dual-target specialist
- `steel-thread-auditor.md` — adversarial reviewer, challenge/clear/deep protocol

Spawn with `Agent(subagent_type="<name>", team_name=..., name=..., prompt="<mission context>")`. The definition file carries identity + discipline; the spawn prompt carries mission specifics (bead IDs, file boundaries, scope constraints, escalation triggers).

## Remaining uib work after Phase 3

- `uib.4` (P2) — Dead code removal (tmux.conf, cockpit_dash.py, cell-spawn.sh, etc.). Blocked on uib.3.
- `uib.5` (P2) — Update CLAUDE.md + skill docs for v2 architecture. Blocked on uib.3.

Both are leader-solo work. Can run in parallel after uib.3 closes.

## Known non-blockers

- **Dolt auto-push** to `outer-gates` (192.168.1.30) returns 404. Local `.beads/` state is durable. First new session may want to ask the operator for the corrected remote URL; see `.claude/local/HANDOFF-local.md` (gitignored) for operator-private context.

## Session close protocol

Before reporting "done":
```bash
git status            # see what changed
git add <paths>       # scoped, never "git add ."
git commit -m "..."   # scenario-conscious message
git pull --rebase     # integrate anything upstream
bd dolt push          # expected to warn on 404, non-blocking
git push              # mandatory; work isn't done until pushed
```

## Leader lessons from the prior session (persistent, via `bd memories`)

Search `bd memories <keyword>` for:

- `teammate-identity-as-lens` — identity out-performs instructions in ambiguity; save to `.claude/agents/`
- `light-communication-protocol` — challenge / clear / deep / question, silence-as-signal, no status reports
- `leader-as-review-layer` — verify before propagating; boundaries are responsibility markers
- `honor-goal-over-text` — missions are intent, not contracts; extend scope for same bug-class, flag the surprising
