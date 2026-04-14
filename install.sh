#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RST='\033[0m'

ok()   { echo -e "  ${GREEN}[ok]${RST}  $1"; }
warn() { echo -e "  ${YELLOW}[!!]${RST}  $1"; }
fail() { echo -e "  ${RED}[XX]${RST}  $1"; }
info() { echo -e "  ${CYAN}[..]${RST}  $1"; }

echo
echo -e "${CYAN}kitty-kommander installer${RST}"
echo -e "${CYAN}========================${RST}"
echo

# ── Dependency check ─────────────────────────────────────────────────────────
MISSING=0

check_dep() {
    if command -v "$1" &>/dev/null; then
        ok "$1"
    else
        fail "$1 — not found"
        MISSING=$((MISSING + 1))
    fi
}

echo "Checking dependencies..."
echo
check_dep kitty
check_dep tmux
check_dep timg
check_dep dot       # graphviz
check_dep bd        # beads issue tracker
check_dep claude    # Claude Code CLI
check_dep python3
echo

if [ "$MISSING" -gt 0 ]; then
    warn "$MISSING missing dependency(ies). Install them before using the cockpit."
    echo
fi

# ── Symlink configs ──────────────────────────────────────────────────────────
echo "Symlinking configs..."
echo

symlink() {
    local src="$1" dst="$2"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        warn "$(basename "$dst") — exists (not a symlink), skipping. Back up and re-run to replace."
        return
    fi
    mkdir -p "$(dirname "$dst")"
    ln -sf "$src" "$dst"
    ok "$(basename "$dst") -> $src"
}

symlink "$SCRIPT_DIR/config/kitty/kitty.conf" "$HOME/.config/kitty/kitty.conf"
symlink "$SCRIPT_DIR/config/kitty/sessions/kommander.kitty-session" "$HOME/.config/kitty/sessions/kommander.kitty-session"
symlink "$SCRIPT_DIR/config/tmux/tmux.conf" "$HOME/.tmux.conf"
echo

# ── Install skills ───────────────────────────────────────────────────────────
echo "Installing Claude Code skills..."
echo

CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/subagents"

for skill in plot view cockpit notebook; do
    src="$SCRIPT_DIR/skills/$skill"
    dst="$CLAUDE_DIR/skills/$skill"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        warn "$skill skill — exists (not a symlink), skipping"
    else
        ln -sf "$src" "$dst"
        ok "$skill skill"
    fi
done

# Subagent
if [ -e "$CLAUDE_DIR/subagents/cell-leader.md" ] && [ ! -L "$CLAUDE_DIR/subagents/cell-leader.md" ]; then
    warn "cell-leader.md — exists (not a symlink), skipping"
else
    ln -sf "$SCRIPT_DIR/subagents/cell-leader.md" "$CLAUDE_DIR/subagents/cell-leader.md"
    ok "cell-leader subagent"
fi

echo
echo -e "${GREEN}Done.${RST} Launch the cockpit: ${CYAN}F7 > A${RST} in Kitty, or:"
echo -e "  kitty --session ~/.config/kitty/sessions/kommander.kitty-session"
echo
