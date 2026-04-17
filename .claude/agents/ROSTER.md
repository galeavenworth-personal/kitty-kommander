# Roster

Two rosters, one file. **Teams** are capability loadouts — durable units that persist across missions. **Identities** are individual teammate designs that belong to one or more teams. A mission deploys into a team by activating a subset of its roster.

## Mental model

- **Team ≠ mission.** `dev-cell` is a team; "ship uib.3" is a mission. Deploying `dev-cell` on uib.3 activates integrator + steel-thread-auditor. Deploying `dev-cell` on a greenfield feature might activate go-builder + ui-builder + integrator + auditor. Same team, different activation.
- **Identities are cross-team.** `steel-thread-auditor` can serve both `dev-cell` and a future `design-cell`. The identity file at `.claude/agents/<name>.md` is the same; team affiliation is metadata tracked here.
- **Perf tracking is two-axis.** Per-identity (how does integrator perform?) and per-team-on-mission-class (how does dev-cell perform on wiring missions vs. greenfield?). A team that looks right on paper but underperforms on a class of mission is a tuning problem at the team level — wrong loadout, wrong adjacency, wrong handoff protocol — not any one member's fault.
- **Craft on demand, not speculatively.** A new identity is authored when a mission names a capability gap. A new team is created when a repeated activation pattern deserves a preset. Don't pre-build roles or teams for imagined work.

## How to use

**On spawn:** append a row under the team's **Deployments** table naming the mission, the activated subset, and the date. Append per-identity rows in that identity's table too. Cross-reference by mission (bead ID).

**On mission close:** fill in **Result** at both layers (team deployment + each member deployment). Add a **Perf note** at each layer — one sentence, forward-looking. Team-level perf: "dev-cell spent too many turns on handoff between integrator and auditor; next time pre-brief the auditor's watchlist before integrator starts." Individual perf: "integrator under-scoped environment hygiene; tighten that section of integrator.md next edit."

**When perf notes pile up in one direction:** edit the identity `.md` file, or adjust the team's default activation. The roster is the feedback mechanism that makes identities and teams evolve. Identity drift from perf notes is the point.

## Leader's standing notes

- Identity first, mission second. The `.md` file carries lens and discipline; the spawn prompt carries bead IDs and file boundaries.
- Silence is clear in the light-communication protocol. Absence of a message from a well-defined role is signal, not gap.
- Four-follower cap is real. A fifth teammate costs more coordination than it adds capacity.
- Stale team state in `~/.claude/teams/<team>/` can shadow a fresh TeamCreate with misleading "already leading team" errors even after the directory is gone. If that fires, run TeamDelete once and retry; it clears the in-session cache.

---

# Teams

## dev-cell

**Capability:** Ships code end-to-end across Go+CUE backend and React dual-target frontend. Home team for everything from greenfield features to integration/wiring to verification.

**Roster (who can activate):** `go-builder`, `ui-builder`, `integrator`, `steel-thread-auditor`.

**Default activation patterns (heuristics, not rules):**
- **Greenfield feature, backend only** → `go-builder` + `steel-thread-auditor`.
- **Greenfield feature, frontend only** → `ui-builder` + `steel-thread-auditor`.
- **Greenfield feature, full-stack** → `go-builder` + `ui-builder` + `integrator` (handoff) + `steel-thread-auditor`. Four followers — cap. No room for a fifth.
- **Integration / wiring** (work exists in parts; the mission is to prove the seams hold) → `integrator` + `steel-thread-auditor`. Leader-heavy; no builders needed when the components are already shipped.
- **Pure review / audit** (no code to write, just to challenge) → `steel-thread-auditor` alone.

The leader may deviate from these if the mission warrants. Record deviation + result in the deployment row; if the pattern repeats, update the heuristic here.

### Deployments

| Date | Mission | Bead | Activated subset | Result | Team perf note |
|---|---|---|---|---|---|
| 2026-04-17 | Steel thread: prove v2 stack end-to-end | `kitty-kommander-uib.3` | integrator, steel-thread-auditor | in progress | — |

## (Future teams — not yet minted)

- **design-cell** — schema/doc/aesthetic capability. Would contain `cue-architect`, `doc-keeper` once those identities exist. Minted when a mission repeatedly pulls on schema-shape work that's currently flowing through the leader.
- **review-cell** — pure review capability for cross-cell audits. Minted when the auditor is regularly deployed standalone outside dev-cell context.

Do not mint a team speculatively. Wait for repeated activation-patterns that deserve a preset.

---

# Identities

## cell-leader

**Role:** Intent Cell Architecture leader. Receives intent, creates team, spawns specialists, tracks via beads, integrates result, accountable for the whole.
**File:** `.claude/agents/cell-leader.md`
**Model:** opus
**Teams:** (leader — not a team member, commands the cell)

_No deployment log — deployments are sessions, tracked implicitly by git history and beads._

---

## go-builder

**Role:** Go+CUE implementation specialist. Consumes CUE scenarios, generates Go tests, implements to green. Never invents behavior scenarios don't describe.
**File:** `.claude/agents/go-builder.md`
**Model:** opus
**Teams:** `dev-cell`

### Deployments

| Date | Mission | Bead | Team | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-16 | Phase 1 Go skeleton + scenariogen + help compiler | `kitty-kommander-6zu` | dev-cell (retroactive) | ✓ shipped | — |

---

## ui-builder

**Role:** React dual-target specialist. Components that render identically through Ink (TUI) and react-dom (web). Single-sources what can be single-sourced.
**File:** `.claude/agents/ui-builder.md`
**Model:** opus
**Teams:** `dev-cell`

### Deployments

| Date | Mission | Bead | Team | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-16 | React Sidebar dual-target (Tiers 2+3) | `kitty-kommander-uib.2` | dev-cell (retroactive) | ✓ shipped | — |
| 2026-04-16 | Vite alias + data-testid selectors | `kitty-kommander-r6x` | dev-cell (retroactive) | ✓ shipped | — |
| 2026-04-17 | TS scenariogen — fixture single-source | `kitty-kommander-5lg` | dev-cell (retroactive) | ✓ shipped | — |
| 2026-04-17 | TS assertions codegen | `kitty-kommander-fta` | dev-cell (retroactive) | ✓ shipped | — |

---

## steel-thread-auditor

**Role:** Adversarial reviewer. Reads committed work and asks "will this pass for the right reasons across every verification tier?" Four-shape protocol: challenge / clear / deep / question. Silence is also clear.
**File:** `.claude/agents/steel-thread-auditor.md`
**Model:** opus
**Teams:** `dev-cell` (and eventually `review-cell` if that team is ever minted)

### Deployments

| Date | Mission | Bead | Team | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-17 | Steel thread: prove v2 stack end-to-end | `kitty-kommander-uib.3` | dev-cell | in progress | — |

---

## integrator

**Role:** End-to-end wiring specialist. Owns the seams where components meet — launches the real artifact, runs the real tools, proves the stack holds weight when connected. Does not write new features; wires what exists.
**File:** `.claude/agents/integrator.md`
**Model:** opus
**Teams:** `dev-cell`

### Deployments

| Date | Mission | Bead | Team | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-17 | Steel thread: prove v2 stack end-to-end | `kitty-kommander-uib.3` | dev-cell | in progress | — |

---

## Proposed future identities (not yet crafted)

- **cue-architect** — schema-level thinking. Owns CUE types, cross-file constraints, `cue vet` hygiene. Would relieve the leader of schema-interpretation load on complex multi-file evolutions. Would belong to `design-cell` (and possibly `dev-cell` as a cross-team member).
- **doc-keeper** — CLAUDE.md, HANDOFF, skill README surface. Writes to match the state of the code, not to summarize sessions. Earns its seat once docs start lagging code by enough that the leader reads commits instead of docs. Would belong to `design-cell`.

Do not craft an identity speculatively. Wait for a mission that names the gap, then craft.
