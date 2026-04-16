#!/usr/bin/env bash
# helm-launch.sh — Launch the Helm tab for multi-cell strategic view.
#
# Usage:
#   helm-launch.sh
#
# Requires: KITTY_LISTEN_ON, KITTY_KOMMANDER_DIR environment variables.
# Idempotent: exits 0 if Helm tab already exists.
#
# Creates a two-pane tab at the leftmost position:
#   Left:  cockpit_dash.py --helm-topology
#   Right: cockpit_dash.py --helm-status
#
# Outputs JSON metadata to stdout on success. All status messages go to stderr.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '[helm-launch] %s\n' "$*" >&2; }
die() { printf '[helm-launch] ERROR: %s\n' "$*" >&2; exit 1; }

kitty_cmd() { kitty @ --to "$KITTY_LISTEN_ON" "$@"; }

# ---------------------------------------------------------------------------
# Validate environment
# ---------------------------------------------------------------------------

if [[ -z "${KITTY_LISTEN_ON:-}" ]]; then
    die "KITTY_LISTEN_ON is not set — must run inside a kitty-kommander instance."
fi

if [[ -z "${KITTY_KOMMANDER_DIR:-}" ]]; then
    die "KITTY_KOMMANDER_DIR is not set — must run inside a kitty-kommander instance."
fi

# ---------------------------------------------------------------------------
# Duplicate detection — check if a Helm tab already exists
# ---------------------------------------------------------------------------

log "Checking for existing Helm tab..."

helm_exists=$(kitty_cmd ls 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for os_win in data:
    for tab in os_win.get('tabs', []):
        if tab.get('title', '') == 'Helm':
            print('yes')
            sys.exit(0)
print('no')
" 2>/dev/null) || die "Failed to query kitty tabs — is the socket active?"

if [[ "$helm_exists" == "yes" ]]; then
    log "Helm tab already exists, nothing to do."
    printf '{"helm_launched": false, "reason": "already_exists"}\n'
    exit 0
fi

# ---------------------------------------------------------------------------
# Launch the Helm tab at the leftmost position
# ---------------------------------------------------------------------------

# Focus tab at index 0 first, then launch with --location=before so the new
# tab lands at position 0 (before the current leftmost tab).
log "Focusing tab at index 0..."
kitty_cmd focus-tab --match "index:0" 2>/dev/null || true

log "Launching Helm tab (topology pane)..."
if ! kitty_cmd launch \
    --type=tab \
    --tab-title "Helm" \
    --location=before \
    --cwd "$KITTY_KOMMANDER_DIR" \
    python3 "${SCRIPT_DIR}/cockpit_dash.py" --helm-topology; then
    die "Failed to launch Helm tab."
fi

# ---------------------------------------------------------------------------
# Create the right-side split for the status pane
# ---------------------------------------------------------------------------

log "Splitting Helm tab for status pane..."
if ! kitty_cmd launch \
    --type=window \
    --match "title:Helm" \
    --location=vsplit \
    --cwd "$KITTY_KOMMANDER_DIR" \
    python3 "${SCRIPT_DIR}/cockpit_dash.py" --helm-status; then
    # Non-fatal: topology pane is already running. Log and continue.
    log "Warning: Failed to create status split pane. Helm tab has topology only."
fi

# ---------------------------------------------------------------------------
# Success — output JSON metadata
# ---------------------------------------------------------------------------

log "Helm tab launched successfully."
printf '{"helm_launched": true, "tab_title": "Helm", "panes": ["helm-topology", "helm-status"]}\n'
