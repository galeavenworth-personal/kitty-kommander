#!/usr/bin/env bash
# cockpit-panes.sh — Create tmux panes in the Cockpit tab for agent teammates.
#
# Usage:
#   cockpit-panes.sh <agent-name> [<agent-name> ...]
#
# Creates one pane per agent in the Cockpit tmux session ($KITTY_KOMMANDER_SESSION).
# Idempotent: if panes already exist for the given agents, they are reused.
# Pane layout: tiled (tmux even-tiled), which produces a 2x2 grid for 4 agents.
#
# Each pane gets:
#   - Title set to the agent name
#   - A visible banner showing the agent name and status
#
# Environment:
#   KITTY_KOMMANDER_SESSION — tmux session name (required)
#   KITTY_KOMMANDER_DIR     — project directory (optional, for cd)
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '[cockpit-panes] %s\n' "$*" >&2; }
die() { printf '[cockpit-panes] ERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    die "Usage: cockpit-panes.sh <agent-name> [<agent-name> ...]"
fi

SESSION="${KITTY_KOMMANDER_SESSION:-}"
if [[ -z "$SESSION" ]]; then
    die "KITTY_KOMMANDER_SESSION is not set"
fi

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    die "tmux session '$SESSION' does not exist"
fi

PROJECT_DIR="${KITTY_KOMMANDER_DIR:-$(pwd)}"

# ---------------------------------------------------------------------------
# Collect requested agents
# ---------------------------------------------------------------------------

AGENTS=("$@")

# ---------------------------------------------------------------------------
# Get existing pane titles to support idempotency
# ---------------------------------------------------------------------------

existing_titles() {
    tmux list-panes -t "${SESSION}:0" -F "#{pane_title}" 2>/dev/null || true
}

pane_exists_for() {
    local agent="$1"
    existing_titles | grep -qF "$agent"
}

# ---------------------------------------------------------------------------
# Count how many panes we need to create
# ---------------------------------------------------------------------------

needed=()
for agent in "${AGENTS[@]}"; do
    if ! pane_exists_for "$agent"; then
        needed+=("$agent")
    else
        log "Pane already exists for '$agent', skipping"
    fi
done

if [[ ${#needed[@]} -eq 0 ]]; then
    log "All panes already exist, nothing to do"
    exit 0
fi

# ---------------------------------------------------------------------------
# Kill the initial empty shell pane if it's the only one and we're creating
# fresh panes. This prevents an extra blank pane in the layout.
# ---------------------------------------------------------------------------

current_pane_count=$(tmux list-panes -t "${SESSION}:0" 2>/dev/null | wc -l)
kill_initial_pane=false

if [[ "$current_pane_count" -eq 1 ]]; then
    # Check if the single pane is just a bare shell (not an agent pane)
    initial_title=$(tmux display-message -t "${SESSION}:0.0" -p "#{pane_title}" 2>/dev/null || echo "")
    has_agent_title=false
    for agent in "${AGENTS[@]}"; do
        if [[ "$initial_title" == *"$agent"* ]]; then
            has_agent_title=true
            break
        fi
    done
    if [[ "$has_agent_title" == "false" ]]; then
        kill_initial_pane=true
    fi
fi

# ---------------------------------------------------------------------------
# Create panes
# ---------------------------------------------------------------------------

first_new=true
for agent in "${needed[@]}"; do
    if [[ "$first_new" == "true" && "$kill_initial_pane" == "true" ]]; then
        # Repurpose the initial pane instead of splitting
        tmux send-keys -t "${SESSION}:0.0" "" ""  # Clear any partial input
        first_new=false
    else
        # Split from the current pane. split-window auto-selects the new pane,
        # so subsequent commands target the active pane.
        tmux split-window -t "${SESSION}:0"
    fi

    # The active pane is the one we want. Set title and banner.
    tmux select-pane -T "$agent"

    tmux send-keys "clear" Enter
    tmux send-keys "printf '\\n  \\033[1;38;2;122;162;247m%s\\033[0m  \\033[2m%s\\033[0m\\n\\n' '$agent' 'waiting for orders'" Enter
    if [[ -n "$PROJECT_DIR" ]]; then
        tmux send-keys "cd '$PROJECT_DIR'" Enter
    fi

    log "Created pane for '$agent'"
done

# ---------------------------------------------------------------------------
# If we repurposed the initial pane, we didn't kill it. If we split new panes
# AND need to kill the initial one, do it now.
# ---------------------------------------------------------------------------

if [[ "$kill_initial_pane" == "true" && "$first_new" == "true" ]]; then
    # We never repurposed it (shouldn't happen, but guard)
    :
fi

# ---------------------------------------------------------------------------
# Rebalance layout to even-tiled (2x2 grid for 4 panes, etc.)
# ---------------------------------------------------------------------------

tmux select-layout -t "${SESSION}:0" tiled

log "Created ${#needed[@]} pane(s), layout rebalanced"
