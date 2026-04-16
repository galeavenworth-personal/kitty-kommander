#!/usr/bin/env bash
# cell-teardown.sh — Cleanly shut down a sub-cell: sync federation, remove peers,
# terminate the kitty-kommander instance.
#
# Usage:
#   cell-teardown.sh <cell-name> <project-dir> [--force]
#
# Arguments:
#   cell-name     Name used during cell-spawn.sh (federation peer name)
#   project-dir   Absolute or relative path to the sub-cell's project directory
#   --force       Skip the open-beads safety check
#
# Outputs JSON summary to stdout on success. All status messages go to stderr.
# Non-zero exit if safety check fails (use --force to override).
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '[cell-teardown] %s\n' "$*" >&2; }
die() { printf '[cell-teardown] ERROR: %s\n' "$*" >&2; exit 1; }

slug_from_dir() {
    basename "$1" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]-' '-' | sed 's/-$//'
}

usage() {
    cat >&2 <<'EOF'
Usage: cell-teardown.sh <cell-name> <project-dir> [--force]

Cleanly shut down a sub-cell: sync federation, remove peer registrations,
and terminate the kitty-kommander instance.

Arguments:
  cell-name     Name used during cell-spawn.sh (federation peer name)
  project-dir   Path to the sub-cell's project directory
  --force       Skip the open-beads safety check

Outputs JSON summary to stdout on success.
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

FORCE=false

# Check for --help anywhere in args
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        usage
    fi
done

if [[ $# -lt 2 ]]; then
    die "Usage: cell-teardown.sh <cell-name> <project-dir> [--force]"
fi

CELL_NAME="$1"
PROJECT_DIR="$2"
shift 2

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        *) die "Unknown argument: $arg" ;;
    esac
done

# Resolve project-dir to absolute path
if [[ ! -d "$PROJECT_DIR" ]]; then
    die "Project directory does not exist: $PROJECT_DIR"
fi
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# Determine parent directory
PARENT_DIR="${KITTY_KOMMANDER_DIR:-$(pwd)}"

# Derive slug, socket, session for the sub-cell
SLUG="$(slug_from_dir "$PROJECT_DIR")"
SOCKET="unix:/tmp/kitty-kommander-${SLUG}"
SESSION="cockpit-${SLUG}"

log "Tearing down sub-cell '$CELL_NAME'"
log "  project-dir: $PROJECT_DIR"
log "  slug:        $SLUG"
log "  socket:      $SOCKET"
log "  session:     $SESSION"
log "  parent-dir:  $PARENT_DIR"
log "  force:       $FORCE"

# ---------------------------------------------------------------------------
# Safety check — open/in-progress beads
# ---------------------------------------------------------------------------

OPEN_COUNT=0
IN_PROGRESS_COUNT=0

if [[ "$FORCE" != true ]]; then
    log "Checking for open and in-progress beads..."

    open_json=$(cd "$PROJECT_DIR" && bd list --status=open --json 2>/dev/null || echo '[]')
    in_progress_json=$(cd "$PROJECT_DIR" && bd list --status=in_progress --json 2>/dev/null || echo '[]')

    # Count items — handle both array and empty cases
    OPEN_COUNT=$(printf '%s' "$open_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
    IN_PROGRESS_COUNT=$(printf '%s' "$in_progress_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

    if [[ "$OPEN_COUNT" -gt 0 || "$IN_PROGRESS_COUNT" -gt 0 ]]; then
        log "WARNING: Sub-cell has $OPEN_COUNT open and $IN_PROGRESS_COUNT in-progress items."
        die "Sub-cell has $OPEN_COUNT open and $IN_PROGRESS_COUNT in-progress items. Use --force to teardown anyway."
    fi

    log "No open or in-progress beads found."
else
    # Still count for the summary, but don't block
    open_json=$(cd "$PROJECT_DIR" && bd list --status=open --json 2>/dev/null || echo '[]')
    in_progress_json=$(cd "$PROJECT_DIR" && bd list --status=in_progress --json 2>/dev/null || echo '[]')
    OPEN_COUNT=$(printf '%s' "$open_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
    IN_PROGRESS_COUNT=$(printf '%s' "$in_progress_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)

    if [[ "$OPEN_COUNT" -gt 0 || "$IN_PROGRESS_COUNT" -gt 0 ]]; then
        log "WARNING: Forcing teardown with $OPEN_COUNT open and $IN_PROGRESS_COUNT in-progress items."
    fi
fi

# ---------------------------------------------------------------------------
# Final federation sync
# ---------------------------------------------------------------------------

SYNCED=true

log "Running final federation sync..."

# Sub-cell pushes its state outward
if (cd "$PROJECT_DIR" && bd federation sync >/dev/null 2>&1); then
    log "Sub-cell federation sync complete."
else
    log "WARNING: Sub-cell federation sync failed (may be expected if no peers remain)."
    SYNCED=false
fi

# Parent pulls final state from sub-cell
if (cd "$PARENT_DIR" && bd federation sync "$CELL_NAME" >/dev/null 2>&1); then
    log "Parent federation sync from '$CELL_NAME' complete."
else
    log "WARNING: Parent federation sync from '$CELL_NAME' failed."
    SYNCED=false
fi

# ---------------------------------------------------------------------------
# Remove federation peers
# ---------------------------------------------------------------------------

log "Removing federation peer registrations..."

# Parent removes sub-cell peer
if (cd "$PARENT_DIR" && bd federation remove-peer "$CELL_NAME" >/dev/null 2>&1); then
    log "Removed peer '$CELL_NAME' from parent."
else
    log "WARNING: Failed to remove peer '$CELL_NAME' from parent (may already be removed)."
fi

# Sub-cell removes parent peer
if (cd "$PROJECT_DIR" && bd federation remove-peer parent >/dev/null 2>&1); then
    log "Removed peer 'parent' from sub-cell."
else
    log "WARNING: Failed to remove peer 'parent' from sub-cell (may already be removed)."
fi

# ---------------------------------------------------------------------------
# Terminate the kitty-kommander instance
# ---------------------------------------------------------------------------

TERMINATED=true

log "Terminating sub-cell instance..."

# Kill tmux session
if tmux kill-session -t "$SESSION" 2>/dev/null; then
    log "Killed tmux session '$SESSION'."
else
    log "tmux session '$SESSION' was not running (already gone)."
fi

# Quit kitty instance
if kitty @ --to "$SOCKET" quit 2>/dev/null; then
    log "Sent quit to kitty instance at $SOCKET."
else
    log "Kitty instance at $SOCKET was not running (already gone)."
fi

# Clean up lingering socket file
SOCKET_PATH="/tmp/kitty-kommander-${SLUG}"
if [[ -e "$SOCKET_PATH" ]]; then
    rm -f "$SOCKET_PATH"
    log "Removed lingering socket file: $SOCKET_PATH"
fi

log "Sub-cell '$CELL_NAME' teardown complete."

# ---------------------------------------------------------------------------
# Output JSON summary
# ---------------------------------------------------------------------------

TOTAL_OPEN=$(( OPEN_COUNT + IN_PROGRESS_COUNT ))

printf '{"cell_name":"%s","project_dir":"%s","open_items":%d,"synced":%s,"terminated":%s}\n' \
    "$CELL_NAME" "$PROJECT_DIR" "$TOTAL_OPEN" "$SYNCED" "$TERMINATED"
