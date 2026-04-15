#!/usr/bin/env bash
# Launch Claude Code with kitty-kommander configuration.
# Config: config/kommander.cue (requires cue CLI) or env var overrides.
# Falls back to built-in defaults if neither is available.
set -euo pipefail

PROJECT_DIR="${KITTY_KOMMANDER_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

# ── Defaults (must match config/kommander.cue) ─────────────────────────────
model="opus"
agent="cell-leader"
skip_permissions="true"

# ── Override from CUE config ────────────────────────────────────────────────
cue_file="$PROJECT_DIR/config/kommander.cue"
if command -v cue &>/dev/null && [ -f "$cue_file" ]; then
    IFS=$'\t' read -r model agent skip_permissions < <(
        cue export "$cue_file" 2>/dev/null | python3 -c '
import json, sys
c = json.load(sys.stdin).get("claude", {})
m = c.get("model", "opus")
a = c.get("agent", "cell-leader")
s = str(c.get("dangerouslySkipPermissions", True)).lower()
print(f"{m}\t{a}\t{s}")
' 2>/dev/null
    ) || true
fi

# ── Environment overrides (highest priority) ────────────────────────────────
model="${CLAUDE_MODEL:-$model}"
agent="${CLAUDE_AGENT:-$agent}"
skip_permissions="${CLAUDE_SKIP_PERMISSIONS:-$skip_permissions}"

# ── Launch ──────────────────────────────────────────────────────────────────
args=(--model "$model" --agent "$agent")
[ "$skip_permissions" = "true" ] && args+=(--dangerously-skip-permissions)

cd "$PROJECT_DIR"
exec claude "${args[@]}"
