# kitty-kommander v2 — Technical Stack

**Supersedes**: `STACK.md` (v1 — Python + tmux + timg pipeline)

This document defines the architecture for the kitty-kommander rewrite.
The design brief (`BRIEF.md`), panel wireframes (`PANELS.md`), and sprite
doctrine (`SPRITES.md`) remain canonical — this stack serves them.

## Driving Decisions

Four lessons from v1 forced the rewrite:

1. **The deployment gap.** Long-lived Python processes don't reload. No
   mechanism to diff desired state vs actual state. Code changes don't
   deploy. The user sees stale output while the agent reports success.

2. **Two control planes is one too many.** Kitty remote control and tmux
   do the same job — create panes, send text, query state. tmux adds
   detach/reattach, which is worthless when kitty dying kills everything
   else anyway. One control plane, one socket, one API.

3. **The verification gap.** The agent cannot confirm what the user sees.
   Screenshots are forensics, not feedback. The engineering loop —
   change → verify → iterate — requires the rendered UI to be structurally
   inspectable and visually testable at CI speed, not screenshot speed.

4. **Expectation drift.** Help text says one thing, code does another,
   tests cover a third subset. The three artifacts drift because they're
   maintained independently. For a CLI whose primary consumer is an AI
   agent, this drift directly degrades invocation reliability.

These four problems are solved by four architectural choices:

| Problem | Solution |
|---------|----------|
| Deployment gap | CUE desired-state + `kommander doctor/reload` reconciliation |
| Dual control planes | Kitty remote control only — no tmux |
| Verification gap | React (Ink + react-dom) — test TUI structurally, test web visually |
| Expectation drift | CUE scenario TDD — one source produces tests, help text, and docs |

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│ kitty (GPU terminal)                                      │
│   sole terminal host — tabs, windows, graphics protocol   │
│   one socket: unix:/tmp/kitty-kommander-{slug}            │
│                                                           │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────────────┐  │
│  │Cockpit  │ │Driver   │ │Notebooks │ │Dashboard      │  │
│  │Ink apps │ │claude   │ │euporie   │ │Ink apps       │  │
│  │per agent│ │cell-    │ │          │ │DAG + Sidebar  │  │
│  │pane     │ │leader   │ │          │ │               │  │
│  └─────────┘ └─────────┘ └──────────┘ └───────────────┘  │
│  ┌───────────────┐ (appears when sub-cells deploy)        │
│  │Helm           │                                        │
│  │Ink apps       │                                        │
│  │Topology+Status│                                        │
│  └───────────────┘                                        │
└──────────────────────────────────────────────────────────┘
```

**Ink is the rendering layer for any kitty window that shows formatted
information.** Not confined to one tab. Every pane that displays status,
data, or visualizations is an Ink app:

| Surface | Ink app | What it renders |
|---------|---------|-----------------|
| Dashboard left | `kommander-ui --dag` | Dependency DAG (ink-picture for graph image) |
| Dashboard right | `kommander-ui --sidebar` | Health bar, ready queue, mutations, commits |
| Helm left | `kommander-ui --helm-topology` | Cell topology graph (ink-picture) |
| Helm right | `kommander-ui --helm-status` | Cell status cards, gates, mutations |
| Cockpit agent panes | `kommander-ui --agent-status <name>` | Agent name, current bead, role, status |
| Future surfaces | `kommander-ui --<view>` | Any new view is another Ink entry point |

The only kitty windows that are NOT Ink apps:
- **Driver** — Claude Code CLI (not ours to render)
- **Notebooks** — euporie (not ours to render)
- **Agent shell panes** — raw shells where agents execute commands

Each Ink app instance is a separate process in its own kitty window.
kommander launches them via `kitty @ launch`. They share the same
React component library and hooks, differing only in which root
component they mount.

**Two runtimes, clean separation:**

- **Go + CUE** (`kommander` binary): Terminal lifecycle — launch, reload,
  doctor, inspect, cell-spawn, cell-teardown. Talks to kitty via remote
  control socket. Reads CUE config for desired state. Does NOT render UI.

- **TypeScript + React** (`kommander-ui`): UI rendering for all display
  panes. Runs inside kitty windows launched by kommander. Dual-target:
  Ink for TUI, react-dom for web. Does NOT manage terminal lifecycle.

Each runtime does what it's best at. Go manages infrastructure. React
renders UI. They communicate through the filesystem (beads state, CUE
config) and kitty remote control (kommander launches/kills the React
processes).

---

## TDD Architecture

> Adapted from actuator's CLI TDD design. CUE scenarios are the single
> source of truth for tests, help text, and documentation. One source,
> no drift.

### The Problem

Three independent artifacts drift when maintained separately:

1. **Implementation** — Go code for lifecycle, React code for UI
2. **Documentation** — help text, CLAUDE.md, skill docs
3. **Tests** — unit tests, integration tests, visual tests

When these diverge, the agent's expectations (formed from help text)
don't match reality (what the code does), and tests cover a third
subset nobody verified against either. The user hits the gap.

The additional constraint: **the primary CLI consumer is an AI agent.**
The help output is not scanned by a human — it's consumed by a model
forming tool calls. Terse flag descriptions are insufficient. The model
needs complete invocation examples with expected outcomes.

### The Scenario Format

```cue
package kommander

#Scenario: {
    id:    string & =~"^[a-z][a-z0-9-]*$"
    tags:  [...string]

    // The user story — what the user wants and why.
    // This IS the UAT case.
    story: string

    // Preconditions.
    setup: #Setup | *{}

    // The exact invocation. Must be copy-pasteable.
    invocation: string

    // Structured assertions. These become test cases.
    expected: #Expected

    // Trimmed help summary — what --help shows.
    // Must be a complete example an AI can use to form
    // a correct invocation.
    help_summary: string

    // Optional golden file for exact output comparison.
    golden?: string
}

#Setup: {
    env:              {[string]: string} | *{}
    files:            {[string]: string} | *{}
    beads_state?:     #BeadsFixture
    kitty_state?:     #KittyFixture
}

#Expected: {
    exit_code:       int | *0
    stdout_contains: [...string]
    stdout_excludes: [...string]
    stderr_contains: [...string]
    stderr_excludes: [...string]
    kitty_effects:   [...#KittyEffect]
    json_paths:      [...#JSONPathCheck]
}

#KittyEffect: {
    kind: "tab_created" | "window_created" | "window_closed"
        | "text_sent" | "tab_focused" | "no_change"
    match?: string
    count:  int | *1
}

#JSONPathCheck: {
    path:     string
    contains: string
}
```

### CLI Scenarios (Go side)

Every `kommander` subcommand is specified as scenarios before
implementation. The TDD cycle: write scenario → `cue vet` → generate
test → test fails → implement → test passes → help text auto-compiles.

```cue
scenarios: launch: [{
    id:   "launch-basic"
    tags: ["basic", "launch"]

    story: """
        An operator wants to launch a kitty-kommander instance for
        their project directory. The command reads the CUE session
        schema, derives the slug and socket path, and launches kitty
        with the configured tabs.
        """

    invocation: "kommander launch /home/user/my-app"

    expected: {
        exit_code: 0
        stdout_contains: ["session: cockpit-my-app", "socket: unix:/tmp/kitty-kommander-my-app"]
        kitty_effects: [
            {kind: "tab_created", match: "Cockpit"},
            {kind: "tab_created", match: "Driver"},
            {kind: "tab_created", match: "Notebooks"},
            {kind: "tab_created", match: "Dashboard"},
        ]
    }

    help_summary: """
        Launch a kommander instance:
          kommander launch /path/to/project
          → Opens kitty with Cockpit, Driver, Notebooks, Dashboard tabs.
        """
}, {
    id:   "launch-missing-dir"
    tags: ["error", "launch", "validation"]

    story: """
        An operator invokes 'kommander launch' with a directory that
        does not exist. The command fails immediately with a clear
        error and does not launch kitty.
        """

    invocation: "kommander launch /nonexistent/path"

    expected: {
        exit_code: 1
        stderr_contains: ["directory does not exist", "/nonexistent/path"]
        kitty_effects: [{kind: "no_change"}]
    }

    help_summary: """
        Error: directory does not exist
          kommander launch /bad/path → exit 1, no kitty launched.
        """
}]

scenarios: doctor: [{
    id:   "doctor-healthy"
    tags: ["basic", "doctor"]

    story: """
        After launching, the operator runs doctor to verify that
        the actual kitty state matches the CUE desired state.
        All tabs and windows exist with the correct processes.
        """

    setup: {
        kitty_state: {
            tabs: [
                {title: "Cockpit", windows: []},
                {title: "Driver", windows: [{cmd: "claude"}]},
                {title: "Notebooks", windows: [{cmd: "euporie"}]},
                {title: "Dashboard", windows: [
                    {title: "DAG", cmd: "kommander-ui --dag"},
                    {title: "Sidebar", cmd: "kommander-ui --sidebar"},
                ]},
            ]
        }
    }

    invocation: "kommander doctor"

    expected: {
        exit_code: 0
        stdout_contains: ["healthy", "4/4 tabs", "0 drift"]
        json_paths: [
            {path: ".status", contains: "healthy"},
            {path: ".tabs_expected", contains: "4"},
            {path: ".drift_count", contains: "0"},
        ]
    }

    help_summary: """
        Check session health:
          kommander doctor
          → JSON report: tab/window structure vs CUE desired state.
        """
}, {
    id:   "doctor-drift-detected"
    tags: ["common", "doctor"]

    story: """
        A Dashboard window crashed. The operator runs doctor and
        sees drift: the Sidebar window is missing. The report tells
        them exactly what's wrong and suggests 'kommander reload'.
        """

    setup: {
        kitty_state: {
            tabs: [
                {title: "Cockpit", windows: []},
                {title: "Driver", windows: [{cmd: "claude"}]},
                {title: "Notebooks", windows: [{cmd: "euporie"}]},
                {title: "Dashboard", windows: [
                    {title: "DAG", cmd: "kommander-ui --dag"},
                    // Sidebar missing
                ]},
            ]
        }
    }

    invocation: "kommander doctor"

    expected: {
        exit_code: 1
        stdout_contains: ["drift", "Sidebar", "missing"]
        json_paths: [
            {path: ".status", contains: "drift"},
            {path: ".drift[0].kind", contains: "window_missing"},
            {path: ".drift[0].tab", contains: "Dashboard"},
            {path: ".drift[0].expected", contains: "Sidebar"},
        ]
        stderr_contains: ["run 'kommander reload' to reconcile"]
    }

    help_summary: """
        Drift detected:
          kommander doctor → exit 1, lists missing/extra windows.
          Fix: kommander reload
        """
}]

scenarios: reload: [{
    id:   "reload-reconcile"
    tags: ["basic", "reload"]

    story: """
        After doctor reports drift (missing Sidebar window), the
        operator runs reload. It diffs desired vs actual, spawns
        the missing window, and confirms the session is healthy.
        """

    invocation: "kommander reload"

    expected: {
        exit_code: 0
        stdout_contains: ["reconciled", "spawned: Sidebar"]
        kitty_effects: [
            {kind: "window_created", match: "Sidebar"},
        ]
    }

    help_summary: """
        Reconcile session state:
          kommander reload
          → Diffs CUE desired state vs kitty actual state.
            Kills stale windows, spawns missing ones, restarts changed.
        """
}]

scenarios: pane: [{
    id:   "pane-create-agent"
    tags: ["basic", "pane"]

    story: """
        The cell-leader spawns a new teammate called 'builder'.
        It calls 'kommander pane builder' to create a kitty window
        in the Cockpit tab for the agent to work in.
        """

    invocation: "kommander pane builder"

    expected: {
        exit_code: 0
        kitty_effects: [
            {kind: "window_created", match: "builder"},
        ]
        stdout_contains: ["created pane: builder", "tab: Cockpit"]
    }

    help_summary: """
        Create an agent pane:
          kommander pane builder
          → New kitty window in the Cockpit tab titled 'builder'.
        """
}]
```

### UI Scenarios (React side)

UI components get the same treatment. CUE scenarios define fixtures
(mock beads data) and expected rendered content. These generate both
ink-testing-library tests (TUI) and Playwright assertions (web).

```cue
#UIScenario: {
    id:        string & =~"^[a-z][a-z0-9-]*$"
    tags:      [...string]
    story:     string
    component: string
    fixtures:  #BeadsFixture
    expected: {
        contains:    [...string]
        excludes:    [...string]
        snapshot?:   string    // golden file name
        playwright?: #PlaywrightAssertion
    }
}

#BeadsFixture: {
    stats?: {
        total: int; closed: int; blocked: int
        in_progress: int; open: int
    }
    ready?: [...{id: string, title: string, priority: int}]
    blocked?: [...{id: string, title: string, blocked_by: string}]
    commits?: [...{hash: string, message: string}]
    mutations?: [...{time: string, id: string, transition: string, actor: string}]
    agents?: [...{name: string, role: string, status: string, bead?: string}]
    cells?: [...{name: string, health: string, group_type: string}]
    gates?: [...{id: string, source: string, status: string}]
}

#PlaywrightAssertion: {
    screenshot?:   string    // golden screenshot filename
    locator_text?: {[string]: string}  // CSS selector → expected text
}

scenarios: ui: sidebar: [{
    id:   "sidebar-shows-health"
    tags: ["basic", "sidebar"]

    story: """
        The operator glances at the Dashboard sidebar and sees
        project health: completion percentage, status breakdown,
        and the ready queue sorted by priority.
        """

    component: "Sidebar"

    fixtures: {
        stats: {total: 20, closed: 12, blocked: 3, in_progress: 2, open: 3}
        ready: [
            {id: "abc", title: "Fix auth bug", priority: 1},
            {id: "def", title: "Add logging", priority: 2},
            {id: "ghi", title: "Update docs", priority: 4},
        ]
        commits: [
            {hash: "f028764", message: "feat: add auth handler"},
        ]
    }

    expected: {
        contains: [
            "60% complete",
            "12 closed", "3 blocked", "2 wip",
            "Fix auth bug",
            "Add logging",
            "f028764",
        ]
        excludes: [
            "0% complete",    // must not show zero
            "NaN",            // must not show NaN
        ]
        snapshot: "sidebar-basic"
        playwright: {
            screenshot: "sidebar-basic.png"
            locator_text: {
                ".health-bar": "60%"
                ".ready-queue li:first-child": "Fix auth bug"
            }
        }
    }
}, {
    id:   "sidebar-empty-project"
    tags: ["edge-case", "sidebar"]

    story: """
        A freshly initialized project has no beads. The sidebar
        should show 0% with an empty ready queue and a helpful
        message, not crash or show NaN.
        """

    component: "Sidebar"

    fixtures: {
        stats: {total: 0, closed: 0, blocked: 0, in_progress: 0, open: 0}
        ready: []
        commits: []
    }

    expected: {
        contains: ["0% complete", "No work items"]
        excludes: ["NaN", "undefined", "null"]
        snapshot: "sidebar-empty"
    }
}]

scenarios: ui: helm_status: [{
    id:   "helm-shows-blocked-cell"
    tags: ["basic", "helm-status"]

    story: """
        The Kommander has three sub-cells. Cell-C is blocked on a
        cross-cell gate. The Helm status pane shows Cell-C as
        BLOCKED with the gate source identified.
        """

    component: "HelmStatus"

    fixtures: {
        cells: [
            {name: "cell-a", health: "complete", group_type: "Pounce"},
            {name: "cell-b", health: "in_progress", group_type: "Pounce"},
            {name: "cell-c", health: "blocked", group_type: "Glaring"},
        ]
        gates: [
            {id: "cell-c.1", source: "cell-b:api-b.3", status: "PENDING"},
        ]
    }

    expected: {
        contains: [
            "cell-c", "BLOCKED", "Glaring",
            "cell-b:api-b.3", "PENDING",
        ]
        snapshot: "helm-blocked-cell"
    }
}]
```

### The TDD Cycle

```
     ┌─────────────────────────────────────────┐
     │  1. Write scenario in CUE               │
     │     (story + invocation/fixtures +       │
     │      expected assertions)                │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  2. cue vet schema/                     │
     │     (schema validates — surface is       │
     │      internally consistent)              │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  3. Generate test cases from scenarios   │
     │     CLI: go generate → table-driven tests│
     │     UI:  codegen → test fixtures + asserts│
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  4. Tests FAIL (red)                     │
     │     Command not implemented, or          │
     │     component not rendering expected      │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  5. Implement                            │
     │     Go command logic, or                 │
     │     React component rendering            │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  6. Tests PASS (green)                   │
     │     CLI: exit code, stdout, kitty effects│
     │     UI:  contains, snapshot, Playwright  │
     └───────────────────┬─────────────────────┘
                         │
                         ▼
     ┌─────────────────────────────────────────┐
     │  7. Help text + docs auto-compile from   │
     │     scenario help_summary fields         │
     └─────────────────────────────────────────┘
```

### What's Generated vs. Hand-Written

| Artifact | Source | Method |
|----------|--------|--------|
| Go test case table | CUE CLI scenarios | Generated — each scenario becomes a `t.Run` sub-test |
| React test fixtures | CUE UI scenarios | Generated — mock data + assertions |
| Playwright assertions | CUE UI scenarios | Generated — locator checks + golden screenshots |
| Help text (`--help`) | CUE `help_summary` | Generated — compiled from scenario fields |
| Golden files (initial) | First passing test | Generated — `--update` flag to regenerate |
| **Command logic** | **Developer** | **Hand-written** — what the command actually does |
| **Component rendering** | **Developer** | **Hand-written** — how the component looks |
| **Scenario narratives** | **Developer** | **Hand-written** — what the user expects |

The boundary: CUE generates the **shell** (test scaffolding, help text,
fixture data). The developer writes the **core** (implementation logic)
and the **intent** (scenarios describing expected behavior).

### Scenario-Driven Help

Traditional help is a flag reference table. It tells you *what flags
exist* but not *how to combine them to accomplish a goal*. For an AI
consumer, a scenario shows a complete working invocation with the
expected outcome. The model can pattern-match to its task and adapt.

```
$ kommander --help
kommander — Terminal cockpit for AI agent teams

Commands:
  launch     Launch a kommander instance for a project directory
  inspect    Dump current kitty state as JSON
  doctor     Check session health (desired state vs actual state)
  reload     Reconcile session — spawn missing, kill stale, restart changed
  pane       Create an agent pane in the Cockpit tab
  cell-spawn Launch a sub-cell and wire federation
  cell-teardown  Tear down a sub-cell

$ kommander launch --help
kommander launch — Start a kommander instance

Launch a kommander instance:
  kommander launch /path/to/project
  → Opens kitty with Cockpit, Driver, Notebooks, Dashboard tabs.

Launch with custom CUE config:
  kommander launch /path/to/project --config custom.cue
  → Uses custom session schema instead of default.

Error: directory does not exist
  kommander launch /bad/path → exit 1, no kitty launched.

Flags:
  --config, -c  CUE session file (default: config/kommander.cue)
  --socket      Override socket path (default: derived from project slug)
  --dry-run     Print what would be launched without launching
```

### AI-Driven Validation

Because the CLI's primary consumer is an AI agent, the UAT loop is:

1. Present the scenario's story to an agent
2. Give it only the `--help` output
3. Ask it to form the correct invocation
4. Compare to the scenario's `invocation` field
5. If they diverge, the help text is insufficient — improve `help_summary`

Target: **>95% first-try reliability** for basic and common scenarios.

---

## Layer 1: Terminal — Kitty (sole control plane)

No tmux. Kitty remote control handles everything:

| Operation | Command |
|-----------|---------|
| Create tab | `kitty @ launch --type=tab --tab-title "Dashboard"` |
| Create pane | `kitty @ launch --type=window --location=vsplit` |
| Send text | `kitty @ send-text --match title:builder "cd /project"` |
| Kill pane | `kitty @ close-window --match title:builder` |
| Query state | `kitty @ ls` → JSON tree of tabs/windows/panes |
| Focus | `kitty @ focus-tab --match title:Dashboard` |

One socket per instance: `unix:/tmp/kitty-kommander-{slug}`.

The session file (`kommander.kitty-session`) defines initial tab layout.
Agent panes in the Cockpit tab are created dynamically by kommander via
`kitty @ launch --type=window`.

## Layer 2: Lifecycle — Go + CUE (`kommander` binary)

A single Go binary. CUE is the configuration language and intermediate
representation (IR), consistent with actuator and orisome.

### CUE Session Schema

```cue
package kommander

#Tab: {
    title:    string
    layout?:  "tall" | "splits" | "stack"
    windows:  [...#Window]
    dynamic?: bool  // true = windows created at runtime (Cockpit, Helm)
}

#Window: {
    title?:    string
    cmd:       string | [...string]
    location?: "vsplit" | "hsplit" | "after" | "before"
    env?:      {[string]: string}
    ink?:      bool  // true = this is a kommander-ui Ink app
}

#Session: {
    slug:     string
    socket:   string
    tabs:     [...#Tab]
}

session: #Session & {
    tabs: [
        {title: "Cockpit", dynamic: true, windows: []},
        {title: "Driver", windows: [{
            cmd: ["claude", "--agent", "cell-leader",
                  "--dangerously-skip-permissions"],
        }]},
        {title: "Notebooks", windows: [{cmd: "euporie notebook"}]},
        {title: "Dashboard", windows: [
            {title: "DAG", cmd: ["kommander-ui", "--dag"],
             ink: true},
            {title: "Sidebar", cmd: ["kommander-ui", "--sidebar"],
             ink: true, location: "vsplit"},
        ]},
    ]
}
```

### Subcommands

| Command | What it does |
|---------|-------------|
| `kommander launch <dir>` | Read CUE, derive slug/socket, exec kitty with session |
| `kommander inspect` | `kitty @ ls` → structured JSON, typed to CUE schema |
| `kommander doctor` | Diff CUE desired-state vs kitty actual-state, report drift |
| `kommander reload` | Diff and reconcile — kill stale, spawn missing, restart changed |
| `kommander pane <agent>` | Create a kitty window in the Cockpit tab for an agent |
| `kommander cell-spawn <dir> <name>` | Launch sub-cell, wire federation, launch Helm if first |
| `kommander cell-teardown <name>` | Reverse of spawn — deregister peer, kill instance |

Every subcommand has CUE scenarios before it has Go code.

### KittyController Interface

```go
type KittyController interface {
    Launch(opts LaunchOpts) (WindowID, error)
    Close(match string) error
    SendText(match string, text string) error
    FocusTab(match string) error
    FocusWindow(match string) error
    List() (*KittyState, error)
}
```

All kitty `@` commands go through this interface. Mockable for testing.
The real implementation shells out to `kitten @` with the instance socket.
Scenario tests inject a mock that records kitty effects without launching
a real terminal.

### beads.Client Interface

```go
type BeadsClient interface {
    Ready() ([]Issue, error)
    List(filter ListFilter) ([]Issue, error)
    Stats() (*ProjectStats, error)
    Show(id string) (*Issue, error)
    Mutations(limit int) ([]Mutation, error)
    Agents() ([]Agent, error)
    FederationStatus() ([]Peer, error)
    GateCheck() ([]Gate, error)
}
```

Wraps `bd --format=json` calls. Used by kommander for cell health checks
and by the React app for data fetching.

## Layer 3: Rendering — React (Ink + react-dom)

### Dual-Target Architecture

```
packages/ui/
├── src/
│   ├── hooks/           # Shared: data fetching, state, polling
│   │   ├── useBeads.ts       # bd ready, bd stats, bd list
│   │   ├── useGitLog.ts      # git log --oneline
│   │   ├── useMutations.ts   # bd log (audit trail)
│   │   ├── useAgents.ts      # agent roster
│   │   ├── useCells.ts       # federation status, cell health
│   │   ├── useDAGDot.ts      # DOT generation + graphviz rendering
│   │   └── useRefresh.ts     # 30s polling interval
│   │
│   ├── components/      # Shared: component logic + interfaces
│   │   ├── Dashboard.tsx      # Composes DAG + Sidebar
│   │   ├── Sidebar.tsx        # Health bar, ready queue, mutations, commits
│   │   ├── HelmTopology.tsx   # Cell topology graph
│   │   ├── HelmStatus.tsx     # Cell status cards + gates
│   │   ├── AgentStatus.tsx    # Per-agent pane header in Cockpit
│   │   ├── ProgressBar.tsx    # Completion bar
│   │   ├── ReadyQueue.tsx     # Priority-sorted bead list
│   │   ├── MutationLog.tsx    # Recent state transitions
│   │   └── DAGImage.tsx       # Graph — ink-picture (TUI), <img> (web)
│   │
│   ├── tui/             # Ink-specific entry points + adapters
│   │   ├── index.tsx          # Ink render(<App />) entry
│   │   ├── App.tsx            # Route --dag/--sidebar/--helm-*/--agent-* to component
│   │   └── adapters.tsx       # <Box>/<Text> primitives
│   │
│   ├── web/             # react-dom entry points + adapters
│   │   ├── index.tsx          # createRoot() entry
│   │   ├── App.tsx            # Same routing, HTML primitives
│   │   ├── adapters.tsx       # <div>/<span> primitives
│   │   └── styles.css         # Tokyo Night theme
│   │
│   ├── adapters.ts      # Re-export — build system swaps tui/ or web/ target
│   ├── theme.ts         # Tokyo Night palette, shared constants
│   └── types.ts         # Bead, Agent, Cell, Gate, Mutation types
│
├── schema/              # CUE UI scenarios (source of test truth)
│   ├── types.cue             # #UIScenario, #BeadsFixture, etc.
│   ├── sidebar.cue           # Sidebar scenarios
│   ├── helm.cue              # Helm scenarios
│   ├── dag.cue               # DAG scenarios
│   └── agent-status.cue      # Agent pane header scenarios
│
├── test/
│   ├── generated/       # Generated from CUE scenarios (do not edit)
│   │   ├── sidebar.fixtures.ts
│   │   ├── sidebar.assertions.ts
│   │   ├── helm.fixtures.ts
│   │   └── ...
│   │
│   ├── tui/             # ink-testing-library tests (use generated fixtures)
│   │   ├── sidebar.test.tsx
│   │   ├── helm-status.test.tsx
│   │   └── ready-queue.test.tsx
│   │
│   ├── web/             # Playwright visual tests (use generated assertions)
│   │   ├── dashboard.spec.ts
│   │   ├── helm.spec.ts
│   │   └── screenshots/       # Golden files (.png)
│   │
│   └── hooks/           # Pure hook tests (no renderer)
│       ├── useBeads.test.ts
│       └── useCells.test.ts
│
├── package.json
└── tsconfig.json
```

### Shared Hooks (100% reusable across TUI and web)

```tsx
// hooks/useBeads.ts
export function useBeads(refreshMs = 30_000) {
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [ready, setReady] = useState<Issue[]>([])
  const [blocked, setBlocked] = useState<Issue[]>([])

  useEffect(() => {
    const fetch = async () => {
      const s = await bd(["stats"])
      const r = await bd(["ready", "-n", "100"])
      const b = await bd(["blocked"])
      setStats(s); setReady(r); setBlocked(b)
    }
    fetch()
    const id = setInterval(fetch, refreshMs)
    return () => clearInterval(id)
  }, [refreshMs])

  return { stats, ready, blocked }
}
```

### Component Pattern

Components import from a local adapter module, not directly from Ink or
react-dom. The adapter module is swapped per build target:

```tsx
// components/Sidebar.tsx (shared)
import { Box, Text } from '../adapters'
import { useTheme } from '../theme'

export function Sidebar({ stats, ready, commits, mutations }) {
  const theme = useTheme()
  return (
    <Box flexDirection="column" padding={1}>
      <Text bold>PROJECT HEALTH  {stats.percent}% complete</Text>
      <ProgressBar value={stats.closed} max={stats.total} />
      <ReadyQueue items={ready} />
      <MutationLog items={mutations} />
    </Box>
  )
}
```

```tsx
// tui/adapters.tsx
export { Box, Text } from 'ink'

// web/adapters.tsx
export function Box({ children, flexDirection, padding, ...props }) {
  return <div style={{ display: 'flex', flexDirection, padding }}>{children}</div>
}
export function Text({ children, bold, color, ...props }) {
  return <span style={{ fontWeight: bold ? 700 : 400, color }}>{children}</span>
}
```

### Image Rendering: ink-picture (TUI) / `<img>` (web)

The DAG and Helm topology graphs are rendered by graphviz (`dot -Tpng`)
and displayed via different mechanisms per target:

```tsx
// components/DAGImage.tsx
import { useDAGDot } from '../hooks/useDAGDot'

// TUI version — uses ink-picture for kitty graphics protocol
export function DAGImageTUI({ beads }) {
  const pngPath = useDAGDot(beads)
  if (!pngPath) return <Text dim>No dependency chains.</Text>
  return <Picture src={pngPath} alt="Dependency DAG" />
}

// Web version — standard <img> tag
export function DAGImageWeb({ beads }) {
  const pngPath = useDAGDot(beads)
  if (!pngPath) return <span className="dim">No dependency chains.</span>
  return <img src={pngPath} alt="Dependency DAG" />
}
```

The graph data (nodes, edges, states, assignees) lives in the hook.
The rendering is target-specific. Tests verify the data via hooks;
Playwright verifies the visual via the web build.

## Layer 4: Agent Runtime — Claude Code (unchanged)

Claude Code is the agent runtime. The cell-leader agent definition
(`.claude/agents/cell-leader.md`) drives team coordination via
TeamCreate, Agent, SendMessage.

What changes: agent panes are kitty windows managed by `kommander pane`,
not tmux panes. The cell-leader calls `kommander pane builder` to create
a workspace. Agent status headers are Ink apps
(`kommander-ui --agent-status builder`) showing the agent's name, current
bead, role color, and status — refreshed from beads state.

## Layer 5: Work Tracking — beads (unchanged)

beads (`bd`) remains the issue tracker and durable state layer. React
hooks call `bd` via Node.js `child_process` instead of Python
`subprocess`. Same CLI, same JSON output, same polling cadence.

## Layer 6: Verification — Three Tiers

All tiers are driven by CUE scenarios. The scenarios define what should
be true. The tiers verify it at different levels of fidelity.

| Tier | What | How | Speed | Scenario field |
|------|------|-----|-------|----------------|
| 1. Structural | State correctness | `kommander doctor` + React model inspection | ms | `expected.kitty_effects`, `expected.json_paths` |
| 2. Layout | Text rendering | ink-testing-library `lastFrame()` + golden files | ms | `expected.contains`, `expected.snapshot` |
| 3. Visual | Pixel correctness | Playwright `toHaveScreenshot()` on web build | ~1s | `expected.playwright.screenshot` |

**Tier 1 — Structural:**
```bash
$ kommander doctor
{"status": "healthy", "tabs_expected": 4, "tabs_found": 4, "drift_count": 0}
```

**Tier 2 — Layout:**
```tsx
const { lastFrame } = render(<Sidebar {...sidebarBasicFixture} />)
expect(lastFrame()).toContain('60% complete')
expect(lastFrame()).toMatchSnapshot('sidebar-basic')
```

**Tier 3 — Visual:**
```ts
await page.goto('/dashboard')
await expect(page.locator('.sidebar')).toHaveScreenshot('sidebar-basic.png')
```

**Tier 3b — Inspector screenshots (terminal-specific):**
For kitty-specific rendering that the web build can't represent.
```bash
inspector screenshot --tab Dashboard --output test-artifacts/dashboard.png
```

## Orisome Compatibility

The React web build is a standard SPA. Orisome's fabrication pipeline
can scan and generate React components:

- Orisome scans analyze the component tree (structure, props, types)
- Orisome artifacts (generated React components) import directly
- CUE schemas are consumable by orisome and actuator via shared IR
- The web build is a target for orisome's React SPA fabrication

## What Moves, What Stays, What Dies

### Preserved (copy or adapt)

| Artifact | Action |
|----------|--------|
| `design-package/*` | Stays canonical — BRIEF, PANELS, SPRITES, concept art |
| `.claude/agents/cell-leader.md` | Stays — agent definition unchanged |
| `skills/*/SKILL.md` | Update references (tmux → kitty, Python → kommander) |
| `kittens/inspector/` | Stays — tier 3b verification, remove tmux refs |
| `sprites/` | Stays — yarn balls + kitty sprites used by both targets |
| `config/desktop/` | Stays — .desktop entry, Nautilus extension |
| `config/kitty/kitty.conf` | Stays — kitty config |
| `config/kommander.cue` | Expand — becomes the full session schema |
| `scripts/dash_data.py` | Port logic to TypeScript hooks |
| `scripts/helm_data.py` | Port logic to TypeScript hooks |
| `test/test_dag_dot.py` | Port to CUE scenarios + TypeScript tests |
| `test/test_helm_data.py` | Port to CUE scenarios + TypeScript tests |
| `test/test_desktop.py` | Stays — Python, validates install surface |

### Dies

| Artifact | Why |
|----------|-----|
| `config/tmux/tmux.conf` | No tmux |
| `scripts/cockpit-panes.sh` | Replaced by `kommander pane` |
| `scripts/cockpit_dash.py` | Replaced by kommander-ui Ink apps |
| `scripts/helm-launch.sh` | Replaced by `kommander reload` |
| `scripts/cell-spawn.sh` | Replaced by `kommander cell-spawn` |
| `scripts/cell-teardown.sh` | Replaced by `kommander cell-teardown` |
| `scripts/cell-gate.sh` | Replaced by Go gate management |
| `scripts/cell-dep.sh` | Replaced by Go dep management |
| `scripts/launch-cockpit.sh` | Replaced by `kommander launch` |
| `scripts/launch-claude.sh` | Inlined into CUE session config |
| `DESIGN-multi-cell.md` | Superseded by this document |
| `STACK.md` (v1) | Superseded by this document |

### New

| Artifact | What |
|----------|------|
| `cmd/kommander/` | Go binary — lifecycle management |
| `pkg/kitty/` | KittyController implementation |
| `pkg/beads/` | BeadsClient implementation |
| `pkg/cue/` | CUE schema loading + diffing |
| `schema/cli/` | CUE CLI scenarios (kommander subcommands) |
| `schema/session/` | CUE session schema (#Tab, #Window, #Session) |
| `packages/ui/` | React TUI + web app |
| `packages/ui/schema/` | CUE UI scenarios (component behaviors) |
| `packages/ui/test/generated/` | Generated fixtures + assertions from CUE |
| `packages/ui/test/web/` | Playwright visual tests |
| `packages/ui/test/tui/` | ink-testing-library tests |
| `go.mod` | Go module |
| `package.json` | Root — workspace for packages/ui |
| `playwright.config.ts` | Visual test config |

## Steel Thread

The minimum vertical slice that proves the entire stack:

1. **CUE scenarios written** for `kommander launch`, `kommander doctor`,
   and the Sidebar component — tests exist before code.

2. **`kommander launch <dir>`** — Go binary reads CUE, launches kitty
   with Cockpit, Driver, Notebooks, Dashboard tabs. Dashboard windows
   run `kommander-ui --dag` and `kommander-ui --sidebar` (Ink apps).

3. **Sidebar** — React component rendering `bd stats` health bar,
   `bd ready` queue, `git log` commits. Runs as Ink in the Dashboard
   tab AND as react-dom in a Vite dev server.

4. **All three verification tiers passing:**
   - `kommander doctor` → tab/window structure matches CUE (scenario-driven)
   - ink-testing-library → Sidebar golden file matches (scenario-driven)
   - Playwright → web Sidebar screenshot matches (scenario-driven)

5. **`kommander reload`** — change CUE config, run reload, verify
   drift is reconciled.

6. **Help text compiles** from scenario `help_summary` fields.
   Running `kommander --help` shows scenario-derived examples.

When this thread holds weight, every feature is incremental. The
architecture and the TDD discipline are proven by the thread.

## Dependency Summary

### Go (kommander binary)

```
cuelang.org/go         — CUE schema loading and evaluation
```

### TypeScript (UI)

```
ink                    — React TUI renderer
ink-picture            — kitty graphics protocol images in Ink
react                  — Component model
react-dom              — Web target renderer
ink-testing-library    — TUI component tests
@playwright/test       — Visual regression tests
vite                   — Web build + dev server
```

### System

```
kitty                  — Terminal emulator (>= 0.35 for remote control)
bd (beads)             — Issue tracker CLI
dot (graphviz)         — Graph rendering
cue                    — CUE CLI (for schema evaluation)
```
