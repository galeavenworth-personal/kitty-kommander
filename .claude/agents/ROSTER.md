# Roster

Standing list of reusable teammate identities in `.claude/agents/`. One section per teammate. Record a deployment row every time we spawn — the roster is how the leader learns across sessions what each identity does well and where it drifts.

## How to use

When a teammate is spawned, append a row under their **Deployments** table. When the Mol closes, fill in **Result** and any **Perf note**. A perf note is one sentence on what worked or what to tune in the identity next time — not a summary of the work.

If an identity's perf notes pile up in one direction (e.g. "kept under-scoping, needed more mission context"), update the `.md` file. Identity tuning is the point.

## Leader's standing notes

- Identity first, mission second. The `.md` file carries the lens and discipline; the spawn prompt carries bead IDs and file boundaries.
- Silence is clear in the light-communication protocol. Absence of a message from a well-defined role is signal, not gap.
- Four-follower cap is real. A fifth teammate costs more coordination than it adds capacity.

---

## cell-leader

**Role:** Intent Cell Architecture leader. Receives intent, creates team, spawns specialists, tracks via beads, integrates result, accountable for the whole.
**File:** `.claude/agents/cell-leader.md`
**Model:** opus

_No deployment log — this is the leader identity; deployments are sessions, tracked implicitly by git history and beads._

---

## go-builder

**Role:** Go+CUE implementation specialist. Consumes CUE scenarios, generates Go tests, implements to green. Never invents behavior scenarios don't describe.
**File:** `.claude/agents/go-builder.md`
**Model:** opus

### Deployments

| Date | Mission | Bead | Result | Perf note |
|---|---|---|---|---|
| 2026-04-16 | Phase 1 Go skeleton + scenariogen + help compiler | `kitty-kommander-6zu` | ✓ shipped | — |

---

## ui-builder

**Role:** React dual-target specialist. Components that render identically through Ink (TUI) and react-dom (web). Single-sources what can be single-sourced.
**File:** `.claude/agents/ui-builder.md`
**Model:** opus

### Deployments

| Date | Mission | Bead | Result | Perf note |
|---|---|---|---|---|
| 2026-04-16 | React Sidebar dual-target (Tiers 2+3) | `kitty-kommander-uib.2` | ✓ shipped | — |
| 2026-04-16 | Vite alias + data-testid selectors | `kitty-kommander-r6x` | ✓ shipped | — |
| 2026-04-17 | TS scenariogen — fixture single-source | `kitty-kommander-5lg` | ✓ shipped | — |
| 2026-04-17 | TS assertions codegen | `kitty-kommander-fta` | ✓ shipped | — |

---

## steel-thread-auditor

**Role:** Adversarial reviewer. Reads committed work and asks "will this pass for the right reasons across every verification tier?" Four-shape protocol: challenge / clear / deep / question. Silence is also clear.
**File:** `.claude/agents/steel-thread-auditor.md`
**Model:** opus

### Deployments

| Date | Mission | Bead | Result | Perf note |
|---|---|---|---|---|

_Not yet deployed. First deployment scheduled for `kitty-kommander-uib.3`._

---

## integrator

**Role:** End-to-end wiring specialist. Owns the seams where components meet — launches the real artifact, runs the real tools, proves the stack holds weight when connected. Does not write new features; wires what exists.
**File:** `.claude/agents/integrator.md`
**Model:** opus

### Deployments

| Date | Mission | Bead | Result | Perf note |
|---|---|---|---|---|

_Not yet deployed. First deployment scheduled for `kitty-kommander-uib.3`._

---

## Proposed future roles (not yet crafted)

- **cue-architect** — schema-level thinking. Owns CUE types, cross-file constraints, `cue vet` hygiene. Would relieve the leader of schema-interpretation load on complex multi-file evolutions.
- **doc-keeper** — CLAUDE.md, HANDOFF, skill README surface. Writes to match the state of the code, not to summarize sessions. Earns its seat once docs start lagging code by enough that the leader reads commits instead of docs.

Do not craft an identity speculatively. Wait for a mission that names the gap, then craft.
