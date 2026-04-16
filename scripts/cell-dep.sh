#!/usr/bin/env bash
# Cross-cell dependency management for kitty-kommander multi-cell architecture.
# Creates and inspects dependencies between beads across cells (rigs).
#
# Usage: cell-dep.sh <command> [args...]
# Commands: add, list, tree
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
cell-dep.sh — cross-cell dependency management

Usage:
  cell-dep.sh add  <local-bead> <cell-name> <remote-bead>
  cell-dep.sh list [--cell=<name>]
  cell-dep.sh tree <bead-id>
  cell-dep.sh --help

Commands:
  add    Create a cross-cell dependency (local depends on remote)
  list   List external dependencies, optionally filtered by cell
  tree   Show dependency tree including cross-cell deps
EOF
  exit 1
}

# --- add ---
cmd_add() {
  if [[ $# -lt 3 ]]; then
    echo >&2 "Error: add requires <local-bead> <cell-name> <remote-bead>"
    usage
  fi
  local local_bead="$1" cell_name="$2" remote_bead="$3"

  echo >&2 "Adding cross-cell dependency: ${local_bead} depends on ${cell_name}:${remote_bead}"
  bd dep add "$local_bead" "external:${cell_name}:${remote_bead}" --json
  echo >&2 "Dependency added."
}

# --- list ---
cmd_list() {
  local cell_filter=""
  for arg in "$@"; do
    case "$arg" in
      --cell=*) cell_filter="${arg#--cell=}" ;;
      *) echo >&2 "Error: unknown argument: ${arg}"; usage ;;
    esac
  done

  # bd dep list requires issue IDs; list all open issues and gather their deps.
  # We get all issues, then query deps for each, filtering for external refs.
  local all_deps
  all_deps=$(bd dep list --json 2>/dev/null || echo '[]')

  if [[ -n "$cell_filter" ]]; then
    # Filter to only deps referencing the specified cell
    echo "$all_deps" | python3 -c "
import json, sys
deps = json.load(sys.stdin)
if isinstance(deps, list):
    filtered = [d for d in deps if 'external:${cell_filter}:' in d.get('depends_on_id', '')]
    json.dump(filtered, sys.stdout, indent=2)
else:
    json.dump(deps, sys.stdout, indent=2)
print()
"
  else
    # Show all — filter to external deps only
    echo "$all_deps" | python3 -c "
import json, sys
deps = json.load(sys.stdin)
if isinstance(deps, list):
    filtered = [d for d in deps if d.get('depends_on_id', '').startswith('external:')]
    json.dump(filtered, sys.stdout, indent=2)
else:
    json.dump(deps, sys.stdout, indent=2)
print()
"
  fi
}

# --- tree ---
cmd_tree() {
  if [[ $# -lt 1 ]]; then
    echo >&2 "Error: tree requires <bead-id>"
    usage
  fi
  local bead_id="$1"
  bd dep tree "$bead_id" --json
}

# --- main ---
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  usage
fi

command="$1"; shift
case "$command" in
  add)  cmd_add "$@" ;;
  list) cmd_list "$@" ;;
  tree) cmd_tree "$@" ;;
  *)    echo >&2 "Error: unknown command: ${command}"; usage ;;
esac
