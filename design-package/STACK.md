# kitty-kommander — Technical Stack

How the orchestration engine works under the hood, so the UI design
can accurately function as a reified state machine.

## Architecture Overview

The system has five layers, each handled by a different tool:

- **Terminal**: Kitty (GPU-accelerated). Hosts everything, provides the
  inline graphics protocol for rendering sprites and DAGs directly in
  the terminal. No browser, no Electron.
- **Layout**: tmux. Manages panes inside the Cockpit tab. Each
  kitty-kommander instance gets its own tmux session derived from the
  project directory name.
- **Agent runtime**: Claude Code. Runs in the Driver tab. This IS the
  LLM execution engine — there is no LangChain, no AutoGen, no custom
  framework wrapping it.
- **Team coordination**: Claude Agent Teams (native Claude Code feature).
  `TeamCreate`, `Agent` with `team_name`, `SendMessage`. Handles
  real-time intra-cell messaging and agent lifecycle.
- **Work tracking**: beads (`bd`). A Dolt-backed issue tracker with
  dependencies, gates, federation, and file reservations. This is the
  durable state layer.
- **Visualization**: `cockpit_dash.py` + Graphviz + timg. Reads beads
  state via CLI, generates a DOT graph, renders it as an inline PNG.

## State Broadcast Protocol

There is no message broker, no event stream, no SQLite side-channel.
**Agents report state by operating on beads via the `bd` CLI**, which
writes to a Dolt database (`.beads/`).

Beads issue status IS the agent state. There is no separate "agent state"
concept — an agent's state is inferred from the status of the bead(s) it
owns. A kitty sitting on a `wip` yarn ball is active. Same kitty on a
`blocked` yarn ball is stalled. The sprite system reads beads state, not
agent introspection.

### State transitions as beads commands

- **idle to active**: Agent claims work via `bd update <id> --claim`
- **active to thinking**: Implicit — agent is between tool calls, no
  explicit beads state change
- **active to blocked**: Dependency unresolved, visible via
  `bd dep add <child> <blocker>`
- **active to handoff**: Agent passes work downstream —
  `bd close <id>` and the next teammate picks up
- **handoff to done**: Work completed via `bd close <id> --reason "..."`
- **any to alert**: Escalation to leader via
  `SendMessage(to="leader", ...)`

### What the dashboard sees vs. what it doesn't

The dashboard sees **beads state** — issue statuses, ownership,
dependencies, blockers. It does NOT see real-time intra-cell messages
(`SendMessage` traffic between teammates). Those are ephemeral and
in-process. The dashboard only sees the beads mutations that result
from those conversations.

This means sprite state mapping is a pure function:
`(role, bead_status) → sprite_file`. No event subscription needed.

## Dashboard Hydration

Pure 30-second polling. No event stream. No incremental updates.

Each tick of the refresh loop:

1. Shells out to `bd --format=json` (multiple calls: `ready`, `blocked`,
   `list --status=open`, `list --status=in_progress`, `stats`)
2. Builds a Graphviz DOT string with yarn ball PNGs as image nodes
3. Pipes DOT through `dot -Tpng -Gdpi=150`
4. Pipes the PNG through `/usr/bin/timg -p kitty` for inline rendering
   via the kitty graphics protocol

The sidebar does the same: polls `bd stats`, `bd ready`, and
`git log --oneline`, then renders ANSI text to stdout.

Every 30 seconds the screen clears (`ESC[2J ESC[H`) and redraws from
scratch. This is deliberately simple. The bottleneck is Graphviz layout,
not data fetching, and 30 seconds is slow enough that full redraws are
cheap.

When kitty sprites land in the DAG, they will be additional image nodes
or overlays in the DOT graph — same pipeline, same polling cadence. A
future optimization could use filesystem watchers or beads hooks to
trigger redraws on state change, but the current architecture does not
need it.

### Data flow

```
bd --format=json
    → cockpit_dash.py (Python, stdlib only)
        → Graphviz DOT string
            → dot -Tpng -Gdpi=150
                → /usr/bin/timg -p kitty
                    → kitty terminal (inline image via graphics protocol)
```

## The Orchestrator

**Claude Code itself.** There is no external orchestration framework.

The cell-leader agent (`.claude/agents/cell-leader.md`) is a prompt
definition — it tells Claude Code how to behave as a team leader. Claude
Code provides the execution engine, memory, tool access, and agent
lifecycle natively.

When the cell-leader calls
`Agent(name="builder", team_name="mission-name", prompt="...")`,
Claude Code spawns a subagent with its own context, tools, and lifecycle.
Teammates discover each other via
`~/.claude/teams/{team-name}/config.json` and communicate through
`SendMessage`. Teammates go idle between turns (this is normal) and
wake on message delivery.

### Intra-cell coordination (real-time, ephemeral)

Within a single cell (1 leader + up to 4 specialists):

- `TeamCreate(team_name, description)` — creates the team
- `Agent(name, team_name, prompt)` — spawns a teammate into the team
- `SendMessage(to, message)` — delivers a message to a teammate
- Messages are in-process and ephemeral — not persisted to disk

This is tight-loop, real-time collaboration. The leader dispatches
bounded orders, teammates execute, report back, and the leader
integrates.

### Inter-cell coordination (async, durable)

Between cells (separate kitty-kommander instances):

- `bd federation add-peer <name> <url>` — register a sibling or child
  cell as a federation peer
- `bd dep add <local> external:<rig>:<bead>` — create a cross-cell
  dependency (blocks the local bead until the remote bead closes)
- `bd gate check --type=bead` — check if cross-cell gates have resolved
- `bd federation sync` — push/pull state between peers

This is loose-coupling between cells that may be running on different
projects, different machines, or different time windows. The Kommander
sees summarized status from sub-cells, not their internal agent traffic.

### Recursive stacking

Each cell is a separate kitty-kommander instance — its own kitty window,
its own tmux session, its own Claude Code process, its own `.beads/`
database. A cell's teammate can itself be the lead of a sub-cell. The
parent never directly addresses a worker two levels down. Chain of
command flows through leads.

```
Kommander cell (kitty-kommander on /project)
├── Lead A → sub-cell A (kitty-kommander on /project/module-a)
│             ├── worker A.1
│             ├── worker A.2
│             └── worker A.3
├── Lead B → sub-cell B (kitty-kommander on /project/module-b)
│             ├── worker B.1
│             └── worker B.2
├── Lead C (direct worker, no sub-cell)
└── Lead D (direct worker, no sub-cell)
```

Scaling: 1 layer = 5 agents. 2 layers = 21. 3 layers = 85. Nobody
manages more than 4 direct reports.

## Concurrency

The beads Dolt backend has two modes:

- **Embedded** (`dolt_mode: embedded`): Single-writer. Designed for
  CI/CD, containers, and single-use scripts. NOT for multi-agent.
- **Shared server** (`bd init --shared-server`): Runs a Dolt SQL server
  at `~/.beads/shared-server/`. All cells on the same machine connect
  to it. Multiple agents read and write concurrently — no lock
  contention.

Multi-agent cells require shared server mode. This is a one-time reinit:
`bd init --shared-server --force`.

## Implications for Sprite Design

1. **Sprite selection is stateless.** Given a bead's status and its
   owner's role, you can pick the sprite. No event history needed.

2. **Transitions are discrete, not animated.** The dashboard redraws
   every 30 seconds. Between redraws, the DAG is a static image. Sprite
   "animations" are frame-to-frame pose changes across redraws, not
   smooth tweens.

3. **Ownership is explicit.** Beads tracks who owns what via
   `bd pin <id> --for <agent-name>`. The DAG knows which kitty sits on
   which yarn ball.

4. **Group state is derivable.** A "Glaring" (blocked cell) is a cell
   where the majority of beads are in blocked status. A "Nuisance"
   (failing cell) is a cell with repeated close/reopen cycles. These
   can be computed from beads stats, not from a separate state machine.

5. **The DAG is the single source of truth.** Everything the user sees
   in the cockpit is a visualization of beads state. There is no
   separate "UI state" layer. If a sprite is wrong, the fix is in the
   beads data, not in a rendering cache.

## The Helm — Multi-Cell Visualization

When the Kommander deploys sub-cells, a new tab called **Helm** appears
as Tab 0 (leftmost). It is the strategic, inter-cell view. Single-cell
operators never see it.

The Helm has two splits, mirroring Dashboard layout:

- **Left: Cell Topology** — a Graphviz DAG where nodes are cells (not
  beads). Each cell node shows summarized health, group type, and gate
  status. Edges are federation links.
- **Right: Cell Status** — per-cell cards showing lead, agents, progress
  bar, active gates, and recent mutations.

Data sources are inter-cell only:
- `bd federation status --format=json` — peer list and sync recency
- `bd gate check --format=json` — cross-cell blockers
- Per-cell `bd stats` pulled via federation sync

The Helm does NOT show individual beads inside sub-cells. It shows
cells as opaque units with summarized health. This preserves chain of
command in the visualization — the Kommander sees cells, not workers.

The Helm tab is launched dynamically (not in the static session file):
```bash
kitty @ launch --type=tab --tab-title "Helm" \
  python3 scripts/cockpit_dash.py --helm-topology
```

See `PANELS.md` for full wireframes.
