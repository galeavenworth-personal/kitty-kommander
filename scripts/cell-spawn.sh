#!/usr/bin/env bash
# cell-spawn.sh — Launch a sub-cell and wire bidirectional federation peers.
#
# Usage:
#   cell-spawn.sh <project-dir> <cell-name>
#
# Arguments:
#   project-dir   Absolute or relative path to the sub-cell's project directory
#   cell-name     Human-readable name for the sub-cell (used in federation peer
#                 registration). Must be slug-safe: lowercase alphanumeric + hyphens.
#
# Outputs JSON metadata to stdout on success. All status messages go to stderr.
# Non-zero exit on any failure; launched instance is killed if federation fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '[cell-spawn] %s\n' "$*" >&2; }
die() { printf '[cell-spawn] ERROR: %s\n' "$*" >&2; exit 1; }

slug_from_dir() {
    basename "$1" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]-' '-' | sed 's/-$//'
}

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

if [[ $# -lt 2 ]]; then
    die "Usage: cell-spawn.sh <project-dir> <cell-name>"
fi

PROJECT_DIR="$1"
CELL_NAME="$2"

# Resolve project-dir to absolute path
if [[ ! -d "$PROJECT_DIR" ]]; then
    die "Project directory does not exist: $PROJECT_DIR"
fi
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# Validate cell-name is non-empty and slug-safe
if [[ -z "$CELL_NAME" ]]; then
    die "Cell name must not be empty"
fi
if [[ ! "$CELL_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    die "Cell name must be slug-safe (lowercase alphanumeric + hyphens, no leading/trailing hyphen): $CELL_NAME"
fi

# Determine parent directory
PARENT_DIR="${KITTY_KOMMANDER_DIR:-$(pwd)}"

# Derive slug, socket, session for the sub-cell
SLUG="$(slug_from_dir "$PROJECT_DIR")"
SOCKET="unix:/tmp/kitty-kommander-${SLUG}"
SESSION="cockpit-${SLUG}"

log "Spawning sub-cell '$CELL_NAME'"
log "  project-dir: $PROJECT_DIR"
log "  slug:        $SLUG"
log "  socket:      $SOCKET"
log "  session:     $SESSION"
log "  parent-dir:  $PARENT_DIR"

# ---------------------------------------------------------------------------
# Initialize beads in sub-cell if needed
# ---------------------------------------------------------------------------

if [[ ! -d "${PROJECT_DIR}/.beads" ]]; then
    log "Initializing beads in sub-cell..."
    (cd "$PROJECT_DIR" && bd init)
    log "Beads initialized."
else
    log "Beads already initialized in sub-cell."
fi

# ---------------------------------------------------------------------------
# Launch the sub-cell
# ---------------------------------------------------------------------------

log "Launching kitty-kommander for ${PROJECT_DIR}..."
kitty-kommander "$PROJECT_DIR" &
CHILD_PID=$!
log "Launched with PID $CHILD_PID"

# Cleanup trap: kill the launched instance on failure
cleanup() {
    if kill -0 "$CHILD_PID" 2>/dev/null; then
        log "Cleaning up: killing sub-cell (PID $CHILD_PID)..."
        kill "$CHILD_PID" 2>/dev/null || true
        wait "$CHILD_PID" 2>/dev/null || true
    fi
}

# ---------------------------------------------------------------------------
# Wait for readiness
# ---------------------------------------------------------------------------

log "Waiting for sub-cell readiness (timeout 30s)..."
if ! python3 -m kittens.inspector --socket "$SOCKET" wait --session "$SESSION" --timeout 30; then
    log "Sub-cell failed to become ready."
    cleanup
    die "Sub-cell did not reach ready state within timeout."
fi
log "Sub-cell is ready."

# ---------------------------------------------------------------------------
# Register bidirectional federation peers
# ---------------------------------------------------------------------------

log "Registering federation peers..."

# Parent -> sub-cell
if ! bd federation add-peer "$CELL_NAME" "file://${PROJECT_DIR}/.beads"; then
    log "Failed to register sub-cell as peer in parent."
    cleanup
    die "Federation peer registration failed (parent -> sub-cell)."
fi
log "Registered peer in parent: $CELL_NAME -> file://${PROJECT_DIR}/.beads"

# Sub-cell -> parent
if ! (cd "$PROJECT_DIR" && bd federation add-peer parent "file://${PARENT_DIR}/.beads"); then
    log "Failed to register parent as peer in sub-cell."
    # Attempt to undo the parent-side registration before cleanup
    bd federation remove-peer "$CELL_NAME" 2>/dev/null || true
    cleanup
    die "Federation peer registration failed (sub-cell -> parent)."
fi
log "Registered peer in sub-cell: parent -> file://${PARENT_DIR}/.beads"

# ---------------------------------------------------------------------------
# Auto-launch Helm tab on first sub-cell
# ---------------------------------------------------------------------------

if [[ -n "${KITTY_LISTEN_ON:-}" ]]; then
    log "Checking if Helm tab needs launching..."
    if "${SCRIPT_DIR}/helm-launch.sh" 2>&1 | while read -r line; do log "$line"; done; then
        log "Helm tab ready."
    else
        log "Warning: Helm tab launch failed (non-fatal)."
    fi
fi

# ---------------------------------------------------------------------------
# Success — output JSON metadata
# ---------------------------------------------------------------------------

log "Sub-cell '$CELL_NAME' spawned and federated successfully."

printf '{"cell_name":"%s","project_dir":"%s","socket":"%s","session":"%s","slug":"%s"}\n' \
    "$CELL_NAME" "$PROJECT_DIR" "$SOCKET" "$SESSION" "$SLUG"
