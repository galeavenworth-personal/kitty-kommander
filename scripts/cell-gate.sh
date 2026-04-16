#!/usr/bin/env bash
# Cross-cell gate management for kitty-kommander multi-cell architecture.
# Gates block a local bead until a remote bead in another cell is closed.
#
# Usage: cell-gate.sh <command> [args...]
# Commands: create, check, wait, list
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
cell-gate.sh — cross-cell gate management

Usage:
  cell-gate.sh create <local-bead> <cell-name> <remote-bead>
  cell-gate.sh check  [--type=bead]
  cell-gate.sh wait   <local-bead> [--timeout=300]
  cell-gate.sh list   [--all]
  cell-gate.sh --help

Commands:
  create   Create a cross-cell bead gate (local blocks on remote)
  check    Sync federation peers, then evaluate bead gates
  wait     Poll until a gate on local-bead resolves or timeout
  list     List gates (open by default, --all includes closed)
EOF
  exit 1
}

# --- create ---
cmd_create() {
  if [[ $# -lt 3 ]]; then
    echo >&2 "Error: create requires <local-bead> <cell-name> <remote-bead>"
    usage
  fi
  local local_bead="$1" cell_name="$2" remote_bead="$3"

  echo >&2 "Creating cross-cell dependency: ${local_bead} blocked by ${cell_name}:${remote_bead}"
  bd dep add "$local_bead" "external:${cell_name}:${remote_bead}" --json

  echo >&2 "Syncing federation peer: ${cell_name}"
  bd federation sync --peer "$cell_name" >&2
  echo >&2 "Gate created."
}

# --- check ---
cmd_check() {
  local gate_type="bead"
  for arg in "$@"; do
    case "$arg" in
      --type=*) gate_type="${arg#--type=}" ;;
      *) echo >&2 "Error: unknown argument: ${arg}"; usage ;;
    esac
  done

  echo >&2 "Syncing all federation peers..."
  bd federation sync >&2

  echo >&2 "Checking gates (type=${gate_type})..."
  bd gate check --type="$gate_type" --json
}

# --- wait ---
cmd_wait() {
  if [[ $# -lt 1 ]]; then
    echo >&2 "Error: wait requires <local-bead>"
    usage
  fi
  local local_bead="$1"; shift
  local timeout=300
  for arg in "$@"; do
    case "$arg" in
      --timeout=*) timeout="${arg#--timeout=}" ;;
      *) echo >&2 "Error: unknown argument: ${arg}"; usage ;;
    esac
  done

  local elapsed=0
  local interval=10

  echo >&2 "Waiting for gate on ${local_bead} to resolve (timeout=${timeout}s)..."
  while (( elapsed < timeout )); do
    bd federation sync >&2 2>/dev/null || true
    local result
    result=$(bd gate check --type=bead --json 2>/dev/null || echo '{}')

    # Check if the bead still has an open gate blocking it.
    # bd gate list shows open gates; if none reference our bead, it resolved.
    local open_gates
    open_gates=$(bd gate list --json 2>/dev/null || echo '[]')
    if ! echo "$open_gates" | grep -q "$local_bead"; then
      echo >&2 "Gate on ${local_bead} resolved after ${elapsed}s."
      echo "{\"status\":\"resolved\",\"bead\":\"${local_bead}\",\"elapsed\":${elapsed}}"
      exit 0
    fi

    echo >&2 "  ${elapsed}s/${timeout}s — still waiting..."
    sleep "$interval"
    elapsed=$(( elapsed + interval ))
  done

  echo >&2 "Timeout: gate on ${local_bead} did not resolve within ${timeout}s."
  echo "{\"status\":\"timeout\",\"bead\":\"${local_bead}\",\"elapsed\":${elapsed}}"
  exit 1
}

# --- list ---
cmd_list() {
  local flags=()
  for arg in "$@"; do
    case "$arg" in
      --all) flags+=("--all") ;;
      *) echo >&2 "Error: unknown argument: ${arg}"; usage ;;
    esac
  done
  bd gate list "${flags[@]+"${flags[@]}"}" --json
}

# --- main ---
if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  usage
fi

command="$1"; shift
case "$command" in
  create) cmd_create "$@" ;;
  check)  cmd_check "$@" ;;
  wait)   cmd_wait "$@" ;;
  list)   cmd_list "$@" ;;
  *)      echo >&2 "Error: unknown command: ${command}"; usage ;;
esac
