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

### Three-layer delegation taxonomy

Leader has three distinct delegation surfaces; picking the wrong one costs context or capability.

| Layer | Shape | When to use |
|---|---|---|
| **Team member** | Multi-turn, identity-filed, in-flight comms. | Implementation, adversarial review, multi-commit work. |
| **Sub-agent** (Agent tool with subagent_type) | Bounded single-shot, throwaway identity, no in-flight comms. | Verification against source, codebase exploration, drafting a single artifact (scenario sketch, diff analysis). Leader privilege only — team members can't dispatch. |
| **Leader direct** | Do it yourself. | Arbitration, identity authoring, operator interface, integrating outputs, single-tool-call mutations (bead filing, single git commit). |

**Sub-agent discipline:**
- **Target small and sharp.** Prefer sonnet/haiku-class agents. "Read files X/Y/Z; answer question Q as a structured response." Open-ended briefs produce drift.
- **Include identity, not just task.** A one-line identity ("you are a scenario-idiom auditor") opens the right realm of outputs. `as a biologist` vs `as an accountant` — cheap token cost, large output shaping.
- **Verify, don't accept-on-claim.** Sub-agents can report "done" without the work holding up. Verify the artifact against source before propagating. Same trust-but-verify rule that applies to teammates applies to sub-agents.
- **Over-reliance is not-delegating.** If I find myself routing team-scoped work through sub-agents instead of the team, that's a failure mode — the team is where persistent-identity work lives. Sub-agents fill the gap between "leader task" and "team task."

### Leader sub-agent dispatch log

Record non-trivial sub-agent dispatches — lets leader retrospect on what sub-agenting did and didn't buy across missions.

| Date | Mission | Agent type | Task | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-17 | uib.3 | Plan (sonnet) | Draft cue-config-driven-layout + sidebar-reads-real-beads-state scenarios; flag schema extensions | ✓ used; Draft A committed at `c55542f` after arbitrating option (b), setup.files over proposed setup.config_file field | Sub-agent correctly flagged both schema-extension points rather than silently widening. "Scenario-idiom auditor" identity produced fidelity to existing CUE shape on first pass — identity framing earned its tokens. Leader-verified: existing `#Setup.files` covers Draft A with zero schema change, which sub-agent itself offered as option (b). Draft B deferred to uib.3.E onset (render_mode schema extension + gen-scenarios.mjs update). |


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
| 2026-04-17 | Steel thread: 3.0 + 3.A + 3.B shipped (uib.3 remains open for 3.C/D/E/F/G) | `kitty-kommander-uib.3` | integrator, steel-thread-auditor | partial — 3 of 6 atomic subtasks shipped | Two leader errors this mission: (c55542f) pre-emptive Driver/Notebooks titling rippled to unchanged doctor/reload fixtures, integrator caught pre-commit; (c187816 brief) wrong wrapper exec target produced ghost execution, auditor caught via adversarial probe. Both errors absorbed by the loop without leaking downstream — structured-challenge → arbitration → fix. Lessons persisted via bd memories (`premature-schema-decisions-are-not-free`, `verification-stronger-than-exit-code`). Team dynamic: integrator's challenges were precisely structured; auditor's adversarial probes (disabled materializeFiles, stub-mimicry tests, effect-count probe) caught what code-reading alone misses; mirror-lesson propagation (integrator cited leader's memo in 6001761's commit body) showed the roster-as-feedback loop working bidirectionally. See 0bfddaf + 6001761 retrospectives. |

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
| 2026-04-17 | Steel thread: 3.0 + 3.A + 3.B shipped | `kitty-kommander-uib.3` | dev-cell | ✓ completed (3 clears, 1 challenge, 1 re-audit) | Four adversarial probes across the mission: (f8f14d6) disabled materializeFiles to verify cue-config-driven-layout reds for right reasons; (c187816) caught ghost execution via cross-CWD render check — the leader was verifying exit-code-only; (6001761) stub-mimicry attack on smoke check to test probe strength; (99317c3) synthesized effect-count probe to verify spawnTab cost accounting. Surfaced 4 class-of-bug follow-ons in total (embed drift CI, path traversal, empty-title DriftEntry, tab-title uniqueness). Initial "low regret" clear on c55542f missed a cost-timing nuance — costs of pre-emptive schema decisions materialize at integration, not at audit-time. Calibration note for future low-regret calls. Strong identity performance overall. |

---

## integrator

**Role:** End-to-end wiring specialist. Owns the seams where components meet — launches the real artifact, runs the real tools, proves the stack holds weight when connected. Does not write new features; wires what exists.
**File:** `.claude/agents/integrator.md`
**Model:** opus
**Teams:** `dev-cell`

### Deployments

| Date | Mission | Bead | Team | Result | Perf note |
|---|---|---|---|---|---|
| 2026-04-17 | Steel thread: 3.0 + 3.A + 3.B shipped | `kitty-kommander-uib.3` | dev-cell | ✓ completed (3 commits: f8f14d6, c187816→6001761, 99317c3) | Three pre-implementation challenges caught real issues before commit: (c55542f) flagged pre-emptive titling rippled to fixtures, scoped precisely with file:line evidence and three options+lean; (3.B initial) flagged bare symlink insufficient for cross-CWD invocation, established the seam before implementation; (3.B post-ghost) absorbed leader's verification-stronger-than-exit-code memo into 6001761's install.sh smoke check without prompting — team-level discipline propagation. Consistent pattern: scopes problem, names commit/file:line, proposes options with lean, stands down for arbitration. Missed one adjacent issue (DAG fixture mismatch alongside c55542f titling), leader caught it. Ran leader-suggested adversarial probes on own work before committing 99317c3 (wrong-tab spawn, drop-extras) — reduced auditor round-trip load. All three commits landed tight-scoped, green, beads closed with refs. |

---

## Proposed future identities (not yet crafted)

- **cue-architect** — schema-level thinking. Owns CUE types, cross-file constraints, `cue vet` hygiene. Would relieve the leader of schema-interpretation load on complex multi-file evolutions. Would belong to `design-cell` (and possibly `dev-cell` as a cross-team member).
- **doc-keeper** — CLAUDE.md, HANDOFF, skill README surface. Writes to match the state of the code, not to summarize sessions. Earns its seat once docs start lagging code by enough that the leader reads commits instead of docs. Would belong to `design-cell`.

Do not craft an identity speculatively. Wait for a mission that names the gap, then craft.
