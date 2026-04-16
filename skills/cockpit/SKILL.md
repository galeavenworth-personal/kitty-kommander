---
name: cockpit
description: This skill should be used when managing the Kitty terminal cockpit session, controlling terminal panes and tabs, sending commands to specific panes, checking teammate status, launching or restarting the cockpit session, managing the Helm tab for multi-cell strategic views, or performing any terminal window management. Activate for "launch cockpit", "send to pane", "focus tab", "teammate status", "list panes", "manage windows", "terminal layout", "helm tab", "cell topology", "cell status" requests.
---

## When to Use This Skill
- Launching or restarting the cockpit session
- Sending text/commands to specific terminal panes
- Switching focus between tabs or panes
- Querying the state of kitty windows/tabs
- Managing tmux panes within the cockpit

## Kitty Remote Control

All commands use the kitty remote control socket. IMPORTANT: The socket path includes the PID and varies per session. Always use the environment variable:

```bash
kitty @ --to "$KITTY_LISTEN_ON" <command>
```

If `$KITTY_LISTEN_ON` is not set, find the socket:
```bash
ls /tmp/kitty-actuator-*
```

### List all windows and tabs
```bash
kitty @ --to "$KITTY_LISTEN_ON" ls
```
Returns JSON with all OS windows, tabs, and their windows.

### Send text to a specific window
```bash
# By title match
kitty @ --to "$KITTY_LISTEN_ON" send-text --match "title:Events" "echo hello\n"

# By tab title
kitty @ --to "$KITTY_LISTEN_ON" send-text --match "title:Cockpit" "ls -la\n"
```

### Focus a tab
```bash
# By index (0-based)
kitty @ --to "$KITTY_LISTEN_ON" focus-tab --match "index:0"

# By title
kitty @ --to "$KITTY_LISTEN_ON" focus-tab --match "title:Notebooks"
```

### Set tab/window title
```bash
kitty @ --to "$KITTY_LISTEN_ON" set-tab-title --match "index:0" "Lead Agent"
```

### Create new window in current tab
```bash
kitty @ --to "$KITTY_LISTEN_ON" launch --type=window --title "Monitor" htop
```

## tmux Pane Management

The cockpit's first tab runs a tmux session named `$KITTY_KOMMANDER_SESSION` (e.g. `cockpit-my-app`). This allows parallel instances on different projects. Always use the env var — never hardcode the session name.

### List tmux panes
```bash
tmux list-panes -t "$KITTY_KOMMANDER_SESSION" -F "#{pane_index}: #{pane_current_command} (#{pane_width}x#{pane_height})"
```

### Send keys to a tmux pane
```bash
tmux send-keys -t "$KITTY_KOMMANDER_SESSION.0" "echo hello" Enter
```

### Navigate tmux panes
```bash
tmux select-pane -t "$KITTY_KOMMANDER_SESSION.0"    # Select pane by index
# Or use Alt+1..4 keybinds (configured in tmux.conf)
```

## Agent Pane Management

The cell-leader creates tmux panes for teammates using `cockpit-panes.sh`.

### Create panes for teammates
```bash
# After spawning agents, create their Cockpit panes:
scripts/cockpit-panes.sh builder-1 scout-1 critic-1

# The script:
# - Creates one pane per agent in $KITTY_KOMMANDER_SESSION
# - Sets each pane's title to the agent name
# - Prints a visible banner with agent name + "waiting for orders"
# - Uses tmux tiled layout (2x2 grid for 4 agents)
# - Is idempotent: re-running with same names is safe
```

### Check agent pane state
```bash
# List all panes with titles
tmux list-panes -t "$KITTY_KOMMANDER_SESSION:0" -F "#{pane_index}: #{pane_title} (#{pane_current_command})"

# Read a specific pane's content
tmux capture-pane -p -t "$KITTY_KOMMANDER_SESSION:0.0"
```

### Send a command to an agent's pane
```bash
# By pane index
tmux send-keys -t "$KITTY_KOMMANDER_SESSION:0.1" "echo status update" Enter
```

## Cockpit Session Lifecycle

### Launch cockpit
```bash
kitty-kommander /path/to/project
```
Or press F7 then A if already in Kitty (launches for current working directory).

### Save current session state
Press F7 then S (keybind configured in kitty.conf).

### Check cockpit health
```bash
# Kitty responding?
kitty @ --to "$KITTY_LISTEN_ON" ls > /dev/null 2>&1 && echo "kitty: ok" || echo "kitty: no socket"

# tmux session alive?
tmux has-session -t "$KITTY_KOMMANDER_SESSION" 2>/dev/null && echo "tmux: ok" || echo "tmux: no session"
```

## Tab Layout Reference

| Index | Name | Purpose |
|-------|------|---------|
| 0 | Cockpit | tmux session `$KITTY_KOMMANDER_SESSION` — Agent Teams canvas |
| 1 | Driver | Claude Code cell-leader session |
| 2 | Notebooks | euporie notebook editor |
| 3 | Dashboard | beads DAG + project health |

## Helm Tab — Multi-Cell Strategic View

The Helm tab appears when the Kommander deploys sub-cells. It provides the strategic, inter-cell overview.

**Launch Helm manually:**
```bash
scripts/helm-launch.sh
```
Idempotent — safe to call multiple times. Auto-launches on first `cell-spawn.sh` deployment.

**Check if Helm tab exists:**
```bash
kitty @ --to "$KITTY_LISTEN_ON" ls | python3 -c "
import json, sys
tabs = json.load(sys.stdin)
helm = any(t['title'] == 'Helm' for w in tabs for t in w['tabs'])
print('Helm tab exists' if helm else 'No Helm tab')
"
```

**Helm pane renderers:**
```bash
# Left pane: cell topology DAG (graphviz)
python3 scripts/cockpit_dash.py --helm-topology

# Right pane: cell status cards (ANSI text)
python3 scripts/cockpit_dash.py --helm-status

# Capture for agentic vision
python3 scripts/cockpit_dash.py --capture-helm-topology /tmp/helm.png
python3 scripts/cockpit_dash.py --capture-helm-status /tmp/helm.txt
```

**Data sources:**
- `bd federation list-peers --format=json` — cell topology
- `bd gate check --format=json` — cross-cell blockers
- `bd stats --format=json` (per cell) — cell health summaries

**When Helm appears:**
- Helm launches automatically on first `cell-spawn.sh` deployment
- Single-cell operators never see it
- Helm shows cells as opaque nodes — never individual beads

## Guidelines
- Always use `$KITTY_LISTEN_ON` for the kitty socket path — never hardcode
- Always use `$KITTY_KOMMANDER_SESSION` for the tmux session name — never hardcode `cockpit`
- The `--match` flag uses kitty's matching syntax: `title:`, `index:`, `id:`, `env:`
- When sending text, always append `\n` to execute the command
- For long-running commands in panes, check if the pane is busy before sending
- Multiple kitty-kommander instances can run in parallel (one per project directory)
