#!/usr/bin/env bash
# Launch a kitty-kommander instance for a project directory.
# All entry points (desktop, Nautilus, F7+A) call this script.
#
# Each instance gets its own tmux session and kitty control socket,
# derived from the project directory basename. This allows parallel
# instances on different projects without collision.
set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

# Derive session slug from directory basename
# e.g. /home/user/Projects/my-app → my-app → cockpit-my-app
slug=$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]-' '-' | sed 's/-$//')

export KITTY_KOMMANDER_DIR="$PROJECT_DIR"
export KITTY_KOMMANDER_SESSION="cockpit-${slug}"

SESSION_FILE="${HOME}/.config/kitty/sessions/kommander.kitty-session"

cd "$PROJECT_DIR"
exec kitty \
  --listen-on "unix:/tmp/kitty-kommander-${slug}" \
  --session "$SESSION_FILE"
