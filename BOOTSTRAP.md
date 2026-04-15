# kitty-kommander — Bootstrap Plan

How kitty-kommander constructs herself. Each phase unlocks the next.
Work tracked in beads with 3-level hierarchy (epic.task.subtask).

## Phase Map — 215 issues across 7 epics

```
Phase 0: Foundation          ← YOU (human + Claude) do this manually
    │
    ▼
Phase 1: bv3                 ← Inspector Kitten (69 issues)
    │                            Single cell builds this
    ├────────────────────┐
    ▼                    ▼
Phase 2: z0q             Phase 4: q4r
Dashboard v2 (21)        Multi-Cell Infra (27)
    │                        │
    ▼                        ▼
Phase 3: 91t             Phase 5: wvf
Sprite System (35)       Helm (23)
                             │
                             ▼
═══════════════════════════════════════════════════
    MULTI-CELL THRESHOLD — kitty can now herd cats
═══════════════════════════════════════════════════
                             │
                             ▼
                         Phase 6: ae6
                         Notebook System (19)
                         First multi-cell target
                             │
                             ▼
                         Phase 7: vxo
                         Full Self-Build (23)
                         Multiple cells in parallel
```

**Two parallel tracks after Phase 1:**
- Visual track: bv3 → z0q → 91t (inspector → dashboard → sprites)
- Multi-cell track: bv3 → q4r → wvf → ae6 → vxo (inspector → infra → helm → notebooks → full)

## Phase 0: Foundation (manual, one-time)

**Who:** You + Claude, this session.
**What:** Commit everything, switch to shared server, verify baseline.

- Commit all uncommitted work from design sessions
- `bd init --shared-server --force` (enable concurrent agent access)
- Run `install.sh` to verify symlinks are current
- Verify kitty-kommander launches and all 4 tabs appear
- **HUMAN ACTION:** Launch a fresh kitty-kommander instance on this repo

No beads needed — this is pre-work.

## Phase 1: Inspector Kitten (epic: kitty-kommander-bv3)

**Who:** Single cell (cell-leader + up to 4 agents)
**What:** Build the inspector kitten so kitty can verify her own UI.
**Beads:** 69 issues already structured with dependencies.
**Unlock:** Kitty can now see herself. Every subsequent phase uses the
inspector to verify changes.

**HUMAN ACTION at start:** Launch `kitty-kommander ~/Projects/kitty-kommander`
so the cell has a live instance to test against.

## Phase 2: Dashboard v2 (epic: kitty-kommander-z0q)

**Who:** Single cell, verified by inspector.
**What:** Upgrade cockpit_dash.py with composite nodes, mutations log,
agent roster. Refactor for sprite integration hooks.
**Depends on:** Phase 1 (inspector must exist to verify dashboard changes)

Tasks:
- 2.1 Refactor cockpit_dash.py data layer (extract pure functions)
- 2.2 DAG pane: composite nodes (yarn ball + kitty badge overlay)
- 2.3 Sidebar: add RECENT MUTATIONS section (bd log audit trail)
- 2.4 Sidebar: agent roster with role colors and current assignment
- 2.5 End-to-end visual verification (inspector screenshot tests)

## Phase 3: Sprite System (epic: kitty-kommander-91t)

**Who:** Single cell + human for AI-generated art review.
**What:** Refresh yarn balls to pixel-art-with-depth style. Build kitty
sprite generation pipeline. Integrate into cockpit_dash.py.
**Depends on:** Phase 2 (dashboard must have sprite hooks)

Tasks:
- 3.1 Rewrite generate.py for pixel-art yarn balls (32-bit RGBA)
- 3.2 Kitty sprite generation pipeline (prompt templates, cleanup script)
- 3.3 Generate Kommander sprite set (7 states at Panel size)
- 3.4 Generate remaining 5 roles (7 states each at Panel size)
- 3.5 Badge (16x16) downscale pipeline
- 3.6 Focus (48x48) common states
- 3.7 Integrate sprites into cockpit_dash.py node rendering
- 3.8 Visual verification via inspector

**HUMAN ACTION:** Review AI-generated sprites before integration. Iterate
on prompt templates until quality is right.

## Phase 4: Multi-Cell Infrastructure (epic: kitty-kommander-q4r)

**Who:** Single cell.
**What:** Build the scripts and automation for spawning, connecting, and
tearing down sub-cells. Federation wiring. Gate primitives.
**Depends on:** Phase 1 (inspector for testing)

Tasks:
- 4.1 Cell spawn script (launch kitty-kommander sub-instance)
- 4.2 Federation auto-registration (parent/child peer setup)
- 4.3 Gate primitive wiring (cross-cell blocking via bd gate)
- 4.4 Cell teardown script (clean shutdown, final sync)
- 4.5 Cross-cell dependency helper (bd dep add external:...)
- 4.6 Integration tests (spawn cell, create gate, resolve, teardown)

**HUMAN ACTION:** Launch second kitty-kommander instance for testing.
Agent will instruct: "Please launch `kitty-kommander /tmp/test-cell-a`
so I can test federation wiring."

## Phase 5: Helm (epic: kitty-kommander-wvf)

**Who:** Single cell, depends on Phase 4.
**What:** Build the Helm tab — multi-cell strategic visualization.
**Depends on:** Phase 4 (multi-cell infra must exist)

Tasks:
- 5.1 cockpit_dash.py --helm-topology renderer
- 5.2 cockpit_dash.py --helm-status renderer
- 5.3 Dynamic Helm tab launch via kitty @ launch
- 5.4 Cockpit skill update (Helm tab management commands)
- 5.5 Visual verification (inspector screenshot of Helm)

**HUMAN ACTION:** Will need multiple kitty-kommander instances running
for Helm to have data to display.

## ═══ MULTI-CELL THRESHOLD ═══

After Phase 5, kitty-kommander can:
- Verify her own UI (inspector)
- Render agent state visually (sprites + dashboard v2)
- Spawn sub-cells (multi-cell infra)
- Monitor sub-cells (Helm)

She can now herd cats.

## Phase 6: Notebook System (epic: kitty-kommander-ae6)

**Who:** FIRST MULTI-CELL BUILD. Kommander + 1 sub-cell.
**What:** Build the notebook catalog envelope system and euporie tab
improvements. This is the proving ground for multi-cell coordination.
**Depends on:** Phase 5 (Helm must exist so Kommander can monitor)

The Kommander dispatches the notebook work to a sub-cell while monitoring
via Helm. The sub-cell builds independently. Federation gates track
completion.

Tasks:
- 6.1 Notebook envelope schema (CUE or TOML — identity, owner, tags)
- 6.2 Notebook catalog indexer (scan, register, validate envelopes)
- 6.3 euporie tab improvements (notebook navigator concept)
- 6.4 Notebook → beads linking (notebooks reference bead IDs)
- 6.5 Integration: notebooks visible in Dashboard sidebar

**HUMAN ACTION:** Launch Kommander instance + sub-cell instance.
"Please launch `kitty-kommander ~/Projects/kitty-kommander` as Kommander
and `kitty-kommander ~/Projects/kitty-kommander/notebooks` as sub-cell."

## Phase 7: Full Self-Build (epic: kitty-kommander-vxo)

**Who:** Multiple cells in parallel.
**What:** Remaining work parallelized across sub-cells. Sprite variants,
additional test coverage, documentation, polish.
**Depends on:** Phase 6 (proven multi-cell coordination)

Tasks:
- 7.1 Sprite completion: Compact (24x24) tier, remaining Focus states
- 7.2 Group identity visuals (Pounce/Clowder/Glaring/Nuisance borders)
- 7.3 Full E2E test suite (all panels, all modes, parallel instances)
- 7.4 Documentation: user guide, contributor guide
- 7.5 install.sh v2 (Helm support, sprite installation, shared server)

Multiple sub-cells work in parallel. Each owns a bounded deliverable.
Kommander integrates via Helm.

## Dependencies Between Phases (wired in beads)

```
Phase 0 (manual)
    │
    ▼
bv3 (inspector) ──────────────────────┐
    │                                  │
    ▼                                  ▼
z0q (dashboard v2)               q4r (multi-cell infra)
    │                                  │
    ▼                                  ▼
91t (sprites)                    wvf (helm)
    │  └── 91t.7 depends on              │
    │      z0q.2 (composite nodes)        │
    │                                     ▼
    │                               ae6 (notebooks)
    │                                     │
    │                                     ▼
    └────────────────────────────► vxo (full self-build)
```

Phase 1 (inspector) is the critical path. After it completes, two
tracks run in parallel:
- **Visual track**: z0q → 91t (dashboard → sprites)
- **Multi-cell track**: q4r → wvf → ae6 → vxo (infra → helm → notebooks → full)

Both tracks converge at Phase 7 (vxo) for final parallel self-build.

## Agent Instructions Template

Every task-level bead (.N) includes a description with:
- **Mission:** What to build
- **Verify:** How to test (inspector commands, pytest, manual check)
- **Files:** Which files to create/modify
- **Escalate:** When to ask the human (instance launch, art review, etc.)
- **Human action:** If the human needs to do something (launch instance,
  review art, approve push), this is explicit and specific.
