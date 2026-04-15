# Multi-Cell Architecture — Design

Kitty Kommander as a recursive agent cell hierarchy.

## The Two-Layer Principle

There are exactly two coordination layers. They never mix.

| Layer | Scope | Tool | Manages |
|-------|-------|------|---------|
| **Intra-cell** | Within one cell (1 lead + up to 4 agents) | Claude Agent Teams (`TeamCreate`, `Agent`, `SendMessage`) | Team lifecycle, real-time messaging, task dispatch |
| **Inter-cell** | Between cells | Beads (`bd federation`, `bd gate`, `bd dep external`) | Status sync, cross-cell blocking, chain of command |

A cell-leader agent uses `TeamCreate` to manage its team. It uses `bd` to
report status to its parent cell and to wait on sibling/child cells.
These are not parallel paths for the same thing — they solve different
problems at different scales.

**Why two layers:** Claude Agent Teams is real-time, in-process, and handles
the tight feedback loop of teammates working together. Beads federation is
asynchronous, durable, and handles the loose coupling between cells that
may be running in separate kitty-kommander instances on different projects,
different machines, or different time windows.

## Cell Anatomy

A cell is one kitty-kommander instance:

```
┌─────────────────────────────────────────────┐
│  kitty-kommander instance                   │
│                                             │
│  ┌─────────┐  ┌─────────────────────────┐  │
│  │ Cockpit │  │ Driver                  │  │
│  │ (tmux)  │  │ Claude Code             │  │
│  │         │  │   cell-leader agent     │  │
│  │ agent   │  │   ├── teammate A        │  │
│  │ panes   │  │   ├── teammate B        │  │
│  │ here    │  │   ├── teammate C        │  │
│  │         │  │   └── teammate D        │  │
│  └─────────┘  └─────────────────────────┘  │
│                                             │
│  ┌─────────┐  ┌─────────────────────────┐  │
│  │Notebooks│  │ Dashboard               │  │
│  │         │  │ beads DAG + health      │  │
│  └─────────┘  └─────────────────────────┘  │
│                                             │
│  .beads/  ← this cell's work tracking      │
│  Dolt database (shared server)              │
└─────────────────────────────────────────────┘
```

Internal coordination: `TeamCreate` → `Agent` with `team_name` → `SendMessage`.
External reporting: `bd close`, `bd gate resolve`, `bd federation sync`.

## Stacking: Cells within Cells

A cell's teammate can itself be the lead of a sub-cell. The parent cell
doesn't manage the sub-cell's internal agents — it only sees the sub-cell's
lead kitty as one of its four teammates.

```
Kommander cell (kitty-kommander on /project)
├── Lead A ─── sub-cell A (kitty-kommander on /project/module-a)
│              ├── worker A.1
│              ├── worker A.2
│              └── worker A.3
├── Lead B ─── sub-cell B (kitty-kommander on /project/module-b)
│              ├── worker B.1
│              └── worker B.2
├── Lead C (direct worker, no sub-cell)
└── Lead D (direct worker, no sub-cell)
```

**Scaling math:**
- 1 layer: 1 Kommander + 4 workers = 5 agents
- 2 layers: 1 Kommander + 4 leads × 4 workers = 21 agents
- 3 layers: 1 + 4 + 16 + 64 = 85 agents
- No agent manages more than 4 direct reports

## Inter-Cell Communication via Beads

### How cells see each other

Each cell has its own `.beads/` database (its own "rig" in beads terminology).
Cells register each other as federation peers:

```bash
# In the Kommander's cell, register sub-cell A as a peer
bd federation add-peer cell-alpha file:///project/module-a/.beads
bd federation add-peer cell-beta file:///project/module-b/.beads
```

For remote cells (different machines):
```bash
bd federation add-peer cell-alpha dolthub://org/module-a-beads
# or via dolt server:
bd federation add-peer cell-alpha host:3307/module_a
```

### How work flows down (Kommander → sub-cell)

The Kommander creates a bead in its own rig, then the sub-cell's lead
creates a corresponding bead in the sub-cell's rig. The Kommander's bead
gets a cross-rig dependency:

```bash
# Kommander cell:
bd create "Build auth module" -t epic -p 1 --silent
# → kitty-kommander-x9f

# Kommander tells Lead A (via TeamCreate/SendMessage): 
#   "Build auth module. Your tracking bead is kitty-kommander-x9f."

# Sub-cell A (Lead A creates local tracking):
bd create "Build auth module" -t epic -p 1 --silent
# → module-a-k3m

# Kommander adds cross-rig gate:
bd dep add kitty-kommander-x9f external:module-a:module-a-k3m
```

### How status flows up (sub-cell → Kommander)

When sub-cell A completes its epic:

```bash
# Sub-cell A:
bd close module-a-k3m --reason "Auth module complete, merged in PR #42"
bd federation sync  # push state to peers
```

The Kommander periodically checks gates:

```bash
# Kommander cell:
bd gate check --type=bead  # resolves the gate on kitty-kommander-x9f
bd federation sync         # pull latest state from peers
```

The gate resolving unblocks the Kommander's downstream work automatically.

### How siblings coordinate (sub-cell A needs something from sub-cell B)

Sub-cell A does NOT talk to sub-cell B directly. It escalates to its
parent (the Kommander), which creates the cross-cell dependency:

```bash
# Lead A to Kommander (via SendMessage): 
#   "I need the API schema from cell B before I can proceed."

# Kommander creates the dependency:
bd dep add kitty-kommander-a-task external:module-b:module-b-schema-bead

# Kommander to Lead B (via SendMessage):
#   "Cell A needs the API schema. Priority 1."
```

This is chain of command. The Kommander sees the full picture. Individual
cells see only their own work plus gates on external beads.

## Concurrency: Shared Dolt Server

The embedded dolt backend (`dolt_mode: embedded`) is single-writer — it's
designed for CI/CD and single-use contexts, not multi-agent operation.

For multi-agent cells, use shared server mode:

```bash
# Initialize with shared server (one server for all projects on this machine)
bd init --shared-server

# Or initialize with an explicit server
bd init --server --server-host 127.0.0.1 --server-port 3307
```

Shared server mode runs a Dolt SQL server at `~/.beads/shared-server/`.
All cells on the same machine connect to it. Multiple agents can read and
write concurrently — no lock contention.

**Recommendation for kitty-kommander:** Switch to `--shared-server` before
running agent teams. This is a one-time reinit:

```bash
bd init --shared-server --force
```

## Cell Lifecycle

### When to spawn a sub-cell

A cell-leader spawns a sub-cell when:
- The workload exceeds what 4 direct workers can handle
- The work is in a separate codebase/directory
- The work needs its own independent commit history
- Isolation is needed (the sub-cell can fail without taking down the parent)

A cell-leader does NOT spawn a sub-cell when:
- The work fits within one cell (4 workers)
- The work is all in the same files/directory
- The feedback loop needs to be tight (real-time messaging, not async sync)

### Spawning a sub-cell

The Kommander (or any lead) spawns a sub-cell by launching a new
kitty-kommander instance:

```bash
# From within a cell-leader's context:
kitty-kommander /path/to/sub-project
```

The sub-cell initializes its own beads database, starts its own Claude Code
session with the cell-leader agent, and registers its parent as a federation
peer.

### Tearing down a sub-cell

When the sub-cell's work is done:

1. Sub-cell lead closes all beads, squashes wisps
2. Sub-cell lead runs `bd federation sync` to push final state
3. Sub-cell lead reports completion to parent (via SendMessage)
4. Parent's bead gate resolves
5. Parent terminates the sub-cell's kitty-kommander instance
6. The tmux session and kitty window clean up on process exit

## Dashboard: Multi-Cell Visualization

The Kommander's Dashboard tab shows the top-level DAG — its own beads plus
summarized status from sub-cells (via federation sync). Each sub-cell has
its own Dashboard showing its internal DAG.

**Future:** The Cockpit tab could dedicate a tmux pane per sub-cell,
showing a mini-DAG or status summary. The kitty sprites would represent
agents — different sprites for different roles/states.

### Sprite vocabulary (planned)

| Sprite | Meaning |
|--------|---------|
| Yarn ball (existing) | Bead/issue — color indicates state |
| Sitting kitty | Idle agent — waiting for work |
| Pouncing kitty | Active agent — working on a bead |
| Sleeping kitty | Agent in sub-cell — awaiting gate |
| Kitty with yarn | Agent closing/squashing a bead |
| Crown kitty | Cell leader |
| Double crown kitty | Kommander |

### Group names

| Name | Potential mapping |
|------|------------------|
| Pounce | A single cell (1 lead + workers) |
| Clowder | A cell with sub-cells (2 layers) |
| Destruction | Full 3-layer deployment |
| Glaring | A cell that's blocked/waiting on gates |
| Nuisance | A cell experiencing failures/retries |

## Bootstrap: Self-Construction

Once these pieces work together:
- **Beads** — work tracking within a cell ✓ (working)
- **TeamCreate** — intra-cell agent coordination ✓ (working)
- **Inspector kitten** — visual verification of output (in design)
- **Federation** — inter-cell status sync (beads native, needs wiring)
- **Shared server** — concurrent agent writes (beads native, needs reinit)

...kitty-kommander can build itself. The Kommander dispatches work to
sub-cells, each sub-cell builds a component, the inspector kitten verifies
each component works, and the parent cell integrates the results.

The minimum coordination threshold is:
1. A cell can track and complete a bounded task (beads + TeamCreate)
2. A cell can verify its output matches expectations (inspector kitten)
3. A cell can report completion to its parent (federation + gates)
4. A parent can dispatch work and collect results (routing + gates)

Items 1 and 2 are what the current inspector epic delivers.
Items 3 and 4 are the next phase — wiring federation and gates.

## Beads Primitives → Cell Operations

| Cell operation | Beads primitive | Command |
|---------------|----------------|---------|
| Create sub-cell work | Cross-rig dependency | `bd dep add <local> external:<rig>:<bead>` |
| Wait on sub-cell | Bead gate | `bd gate check --type=bead` |
| Report up to parent | Close bead + sync | `bd close <id>` + `bd federation sync` |
| Route work to sub-cell | Routes | `.beads/routes.jsonl` pattern matching |
| Sync state between cells | Federation | `bd federation sync --peer <name>` |
| Audit who did what | Actor identity | `bd --actor <agent-name> <command>` |
| Prevent cross-cell file conflicts | Reservations | `bd reserve <file> --for <agent>` |
| Worker read-only access | Sandbox mode | `bd --readonly` for workers that only read state |

## What's NOT in Beads (handled by Claude Agent Teams)

| Concern | Tool | Why not beads |
|---------|------|---------------|
| Real-time teammate messaging | `SendMessage` | Beads is async/durable, not real-time |
| Teammate discovery | `TeamCreate` → config.json | Beads doesn't know about Claude agents |
| Idle/wake management | Agent Teams auto-notifications | Beads tracks work, not process state |
| Task dispatch within a cell | `Agent` with `team_name` | Beads routes between rigs, not within one |

## Open Questions

1. **Sub-cell initialization**: Should the Kommander run `bd init --shared-server`
   in the sub-project before launching kitty-kommander there? Or should
   launch-cockpit.sh handle this?

2. **Federation peer discovery**: Currently manual (`bd federation add-peer`).
   Could kitty-kommander auto-register parent/child peers on launch?

3. **Gate polling frequency**: `bd gate check` needs to run periodically.
   The Dashboard already refreshes every 30s. Should gate checks piggyback
   on that, or should the cell-leader poll independently?

4. **Sovereignty tiers**: Federation add-peer accepts `--sovereignty T1-T4`.
   What do these tiers mean for cell hierarchy? Presumably T1 = Kommander
   (sovereign), T4 = leaf worker cell. Needs investigation.

5. **Cross-machine cells**: Federation supports remote URLs
   (`dolthub://`, `host:port`). The architecture supports distributed
   cells natively, but the kitty terminal visualization assumes local.
   Multi-machine visualization is a separate design problem.
