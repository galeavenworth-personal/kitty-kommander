# kitty-kommander — Panel Designs

Functional wireframes grounded in real data shapes. Every field shown
maps to an actual `bd` command or system query. Nothing decorative.

## Tab layout

Single-cell mode (current):

```
[ Cockpit ] [ Driver ] [ Notebooks ] [ Dashboard ]
```

Multi-cell mode (Helm appears when Kommander deploys a second cell):

```
[ Helm ] [ Cockpit ] [ Driver ] [ Notebooks ] [ Dashboard ]
```

Helm is Tab 0 in multi-cell. It's the strategic view. Single-cell
operators never see it.

---

## 1. Dashboard — DAG Pane (left split)

Source: `bd blocked --format=json`, `bd ready --format=json`,
`bd list --status=in_progress --format=json`

This is the existing `cockpit_dash.py --dag`, redesigned. Graphviz
renders the topology; timg pushes it inline via kitty graphics protocol.

```
 DEPENDENCY DAG                                    4 blocked  7 ready
 ─────────────────────────────────────────────────────────────────────

                    ┌─────────┐
                    │  bv3.1  │   [kommander] idle
                    │ Kitty   │   ~~~~~~~~~~~
                    │ state   │   yarn: ready
                    │ module  │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌─────────┐┌─────────┐┌─────────┐
        │  bv3.2  ││  bv3.3  ││  bv3.4  │
        │ tmux    ││ capture ││ desktop  │
        │ state   ││ module  ││ module   │
        │         ││         ││         │
        └────┬────┘└────┬────┘└─────────┘
             │          │      [scout] active
             ▼          ▼      ~~~~~~~~~~~
        ┌─────────┐┌─────────┐ yarn: wip
        │  bv3.5  ││  bv3.6  │
        │ wait    ││ __init_ │
        │ module  ││ module  │
        │ BLOCKED ││         │
        └─────────┘└─────────┘

 [builder] ██ active    [scout] ██ active    [critic] ░░ idle
 bv3.2, bv3.3           bv3.4               (unassigned)
```

Each node is a Graphviz image node. The yarn ball sprite shows bead
status (color). The kitty badge sprite shows owner role (accent color).
On redraw, sprites swap based on current `bd` state — no animation,
just the next frame.

**Data per node:**
- Bead short ID (from `bd list`)
- Title (truncated)
- Status → yarn ball sprite color
- Owner → kitty badge sprite (from `bd show <id>` assignee field)
- Owner state → kitty pose (derived from bead status)

**Agent roster at bottom:**
- One line per agent with role color block
- Current status (active/idle/blocked)
- Assigned bead IDs

---

## 2. Dashboard — Sidebar Pane (right split)

Source: `bd stats --format=json`, `bd ready --format=json`,
`git log --oneline`

```
 PROJECT HEALTH  62% complete
 ─────────────────────────────────────────

 ████████████████████████░░░░░░░░░░░░░░░░
 ■ 31 closed  ■ 7 ready  ■ 4 blocked  ■ 3 wip  ■ 5 open

 ─────────────────────────────────────────
 READY QUEUE
 ─────────────────────────────────────────

 bv3.7   P1  Implement __main__.py
 bv3.8   P1  Write conftest.py fixture
 bv3.9   P2  Test kitty_state module
 bv3.10  P2  Test tmux_state module
 bv3.11  P3  Test capture module
 bv3.12  P3  Test desktop module
 bv3.13  P4  Test wait module

 ─────────────────────────────────────────
 RECENT MUTATIONS
 ─────────────────────────────────────────

 14:32:07  bv3.4   wip → done       scout
 14:31:52  bv3.5   blocked → ready  (dep resolved)
 14:30:18  bv3.6   open → wip       builder
 14:28:44  bv3.2   open → wip       builder
 14:25:01  bv3.1   created          kommander

 ─────────────────────────────────────────
 RECENT COMMITS
 ─────────────────────────────────────────

 f028764  feat: add kitty mascot logo to README
 2451806  feat: kitty-kommander boxout
 0ba550e  Initial commit

 Updated 14:32:37  ~  30s refresh
```

**Changes from current sidebar:**
- "RECENT MUTATIONS" section added — shows bead state transitions with
  timestamps and actor. Source: `bd log --format=json` (the bead audit
  trail, not git). This is the "punch record" — irreversible, timestamped
  state changes.
- Ready queue shows priority with color coding (P0-P1 red, P2 yellow,
  P3-P4 grey).

---

## 3. Helm — Multi-Cell Strategic View (NEW)

Appears only when the Kommander has deployed sub-cells. This is the
inter-cell view. It does NOT show individual beads — it shows cells
as nodes and federation links as edges.

Source: `bd federation status --format=json`, `bd gate check --format=json`,
`bd stats --format=json` (per cell via federation)

### Layout: Helm is a full tab, two splits like Dashboard

```
[ Cell Topology (left) | Cell Status (right) ]
```

### Helm — Topology Pane (left split)

```
 HELM — CELL TOPOLOGY                      Pounce x3   Glaring x1
 ─────────────────────────────────────────────────────────────────

                    ┌─────────────────┐
                    │   KOMMANDER     │
                    │   kitty-komm    │
                    │                 │
                    │  ■ 12/18 done   │
                    │  ■ 3 wip        │
                    │  ■ 1 blocked    │
                    └───────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  CELL-A    │ │  CELL-B    │ │  CELL-C    │
     │  auth-mod  │ │  api-gate  │ │  ui-shell  │
     │  Pounce    │ │  Pounce    │ │  Glaring   │
     │            │ │            │ │            │
     │  ■ 8/8     │ │  ■ 3/6 wip │ │  ■ 0/4     │
     │  COMPLETE  │ │  ▸▸▸ 50%   │ │  BLOCKED   │
     │            │ │            │ │  gate: B.3 │
     └────────────┘ └─────┬──────┘ └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │  CELL-B.1  │
                   │  schema    │
                   │  Pounce    │
                   │            │
                   │  ■ 5/5     │
                   │  COMPLETE  │
                   └────────────┘

 ── federation ──────────────────────────────────
 cell-a   synced 14:30:02   3m ago    healthy
 cell-b   synced 14:32:18   42s ago   healthy
 cell-b1  synced 14:31:55   1m ago    healthy
 cell-c   synced 14:28:44   4m ago    stale
```

Each cell node shows:
- Cell name (derived from project dir slug)
- Group type (Pounce / Clowder / Glaring / Nuisance)
- Summarized health (closed/total, dominant status)
- Gate blockers if any (which cross-cell dependency is stalling it)

The federation status bar at the bottom shows sync recency per peer.
A cell that hasn't synced in >5 minutes is "stale" — the Kommander
may need to investigate.

**Data per cell node:**
- Cell name: from `bd federation list-peers`
- Health: from `bd stats` pulled via federation sync
- Group type: computed from health (all clear = Pounce, has blockers =
  Glaring, has failures = Nuisance, has sub-cells = Clowder)
- Gate status: from `bd gate check --type=bead`

### Helm — Cell Status Pane (right split)

```
 CELL STATUS                               3 cells  21 agents
 ─────────────────────────────────────────────────────────────

 CELL-A  auth-module                           COMPLETE
 ─────────────────────────────────────────────────────────────
 Lead:   lead-a (gold)     done    all beads closed
 Agents: builder-a1        done    auth_handler.py
         builder-a2        done    auth_middleware.py
         scout-a1          done    auth_test_suite.py
         critic-a1         done    review complete
 Beads:  ████████████████████████████████████  8/8  100%
 Gate:   resolved → Kommander bv3.x9f unblocked

 CELL-B  api-gateway                           IN PROGRESS
 ─────────────────────────────────────────────────────────────
 Lead:   lead-b (gold)     active  coordinating
 Agents: builder-b1        active  route_handler.py
         builder-b2        idle    (waiting on b1)
         scout-b1          active  endpoint_scan.py
 Beads:  ██████████████████░░░░░░░░░░░░░░░░░  3/6  50%
 Sub:    cell-b1 (schema)  complete — synced 1m ago

 CELL-C  ui-shell                              BLOCKED
 ─────────────────────────────────────────────────────────────
 Lead:   lead-c (gold)     blocked gate: cell-b bead b.3
 Agents: builder-c1        idle    (waiting on lead)
         builder-c2        idle    (waiting on lead)
         integrator-c1     idle    (waiting on lead)
 Beads:  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0/4  0%
 Gate:   PENDING — waiting on cell-b bead api-gate-b.3

 ─────────────────────────────────────────────────────────────
 CROSS-CELL GATES
 ─────────────────────────────────────────────────────────────

 komm-x9f  ← cell-a:auth-a.ep    RESOLVED   14:28
 komm-y2k  ← cell-b:api-b.ep     PENDING    (cell-b 50%)
 cell-c.1  ← cell-b:api-b.3      PENDING    (cell-b wip)

 ─────────────────────────────────────────────────────────────
 MUTATIONS
 ─────────────────────────────────────────────────────────────

 14:32:18  cell-b   synced     3/6 done
 14:30:02  cell-a   completed  gate komm-x9f resolved
 14:28:44  cell-c   blocked    gate on cell-b:api-b.3
 14:25:01  komm     deployed   cell-a, cell-b, cell-c

 Updated 14:32:37  ~  30s refresh
```

This pane is the Kommander's command picture. It answers:
- Which cells exist and what state they're in
- Who leads each cell and what agents are assigned
- Where the cross-cell blockers are (gates)
- What just happened (mutations log)

The Kommander never sees individual beads inside a sub-cell — only
the cell's summarized health and the gates it cares about. Chain of
command is preserved in the visualization.

---

## 4. Cockpit — tmux Agent Panes

The Cockpit tab is a tmux session. Each agent gets a pane. The
cell-leader manages pane layout via the cockpit skill.

Single-cell layout (4 agents):

```
┌──────────────────────┬──────────────────────┐
│                      │                      │
│  builder-1           │  builder-2           │
│  bv3.2: tmux state   │  bv3.3: capture      │
│                      │                      │
│  $ python3 -m pytest │  $ vim capture.py    │
│  ...                 │  ...                 │
│                      │                      │
├──────────────────────┼──────────────────────┤
│                      │                      │
│  scout-1             │  critic-1            │
│  bv3.4: desktop mod  │  (idle)              │
│                      │                      │
│  $ kitty @ ls        │                      │
│  ...                 │                      │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

Each pane header shows: agent name, current bead assignment, role color.
The cell-leader (in the Driver tab) creates and manages these panes
via `tmux split-window`, `tmux send-keys`, etc.

---

## Group type derivation

Group names are computed from cell health, not manually assigned:

```python
def group_type(cell_stats, has_sub_cells):
    if has_sub_cells:
        return "Clowder"    # cell with sub-cells
    blocked = cell_stats.get("blocked_issues", 0)
    total = cell_stats.get("total_issues", 0)
    failed = cell_stats.get("failed_issues", 0)  # reopen count
    if failed > 0:
        return "Nuisance"   # experiencing failures
    if blocked > total * 0.5:
        return "Glaring"    # majority blocked
    return "Pounce"         # healthy single cell
```

A "Destruction" is not a group type — it's a scale label. Any 3-layer
deployment where the Kommander has Clowders beneath it is a Destruction.
The Helm title bar could show it: `HELM — DESTRUCTION (3 layers, 85 agents)`.

---

## Sprite placement in the DAG

In the Graphviz DOT output, each node currently looks like:

```dot
"bv3.2" [image="sprites/nodes/yarn_wip.png", label="bv3.2: tmux state"];
```

With kitty sprites, a node becomes a composite:

```dot
// Yarn ball as the node image
"bv3.2" [image="sprites/nodes/yarn_wip.png", label="bv3.2: tmux state",
          xlabel=<<TABLE><TR><TD><IMG SRC="sprites/kitties/badge/builder_active.png"/></TD></TR></TABLE>>];
```

The `xlabel` places the kitty badge adjacent to the node without
affecting layout. Graphviz HTML-like labels support embedded images.

Alternative: render composite sprites (yarn ball + kitty overlay) as
a single PNG at render time via Pillow, then use that as the node image.
This gives more control over positioning but adds a render step.

---

## What the Helm changes architecturally

The Helm tab needs a new renderer: `cockpit_dash.py --helm-topology`
and `cockpit_dash.py --helm-status`. These would:

1. Call `bd federation status --format=json` for peer list and sync state
2. Call `bd gate check --format=json` for cross-cell blockers
3. Pull per-cell stats via federation (each peer's `bd stats`)
4. Render cell-level DOT graph (cells as nodes, not beads)
5. Render cell status cards as ANSI text

The session file gains a conditional fifth tab. Since kitty sessions
are static, the Helm tab could be launched dynamically via
`kitty @ launch --type=tab` when the Kommander first deploys a sub-cell.
The cockpit skill would handle this:

```bash
kitty @ launch --type=tab --tab-title "Helm" \
  --cwd "$KITTY_KOMMANDER_DIR" \
  python3 scripts/cockpit_dash.py --helm-topology
```

The tab appears at position 0 (leftmost) — strategic view first.
