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

# Optional: cue validates and exports config/kommander.cue
if command -v cue &>/dev/null; then
    ok "cue (optional — enables live config)"
else
    info "cue not found (optional — launch defaults still work)"
    info "Install: ${CYAN}go install cuelang.org/go/cmd/cue@latest${RST}"
fi
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
mkdir -p "$CLAUDE_DIR/skills"

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

# Cell-leader agent definition (project-level, loaded via .claude/agents/)
# The agent definition lives at .claude/agents/cell-leader.md in the repo itself.
# No user-level symlink needed — Claude Code discovers it from the project directory.
if [ -f "$SCRIPT_DIR/.claude/agents/cell-leader.md" ]; then
    ok "cell-leader agent (.claude/agents/)"
else
    warn "cell-leader agent definition not found at .claude/agents/cell-leader.md"
fi

# Clean up old subagent location (migrated to project-level .claude/agents/)
if [ -e "$CLAUDE_DIR/subagents/cell-leader.md" ]; then
    rm -f "$CLAUDE_DIR/subagents/cell-leader.md"
    ok "removed old cell-leader subagent (migrated to .claude/agents/)"
fi

# Install beads hooks (SessionStart + PreCompact) if bd is available
if command -v bd &>/dev/null; then
    PROJ_SETTINGS="$SCRIPT_DIR/.claude/settings.json"
    if [ -f "$PROJ_SETTINGS" ] && grep -q "SessionStart" "$PROJ_SETTINGS" 2>/dev/null; then
        ok "beads hooks (already installed)"
    else
        # Only install hooks to settings.json — CLAUDE.md is maintained by hand
        bd setup claude --project --quiet 2>/dev/null && ok "beads hooks" || warn "beads hooks — bd setup claude failed"
    fi
fi

# ── Validate CUE config ─────────────────────────────────────────────────────
if command -v cue &>/dev/null && [ -f "$SCRIPT_DIR/config/kommander.cue" ]; then
    if cue vet "$SCRIPT_DIR/config/kommander.cue" 2>/dev/null; then
        ok "config/kommander.cue validated"
    else
        warn "config/kommander.cue has errors — launch will use defaults"
    fi
fi

# Ensure launch scripts are executable
chmod +x "$SCRIPT_DIR/scripts/launch-cockpit.sh" 2>/dev/null && ok "launch-cockpit.sh" || true
chmod +x "$SCRIPT_DIR/scripts/launch-claude.sh" 2>/dev/null && ok "launch-claude.sh" || true
chmod +x "$SCRIPT_DIR/scripts/cockpit-panes.sh" 2>/dev/null && ok "cockpit-panes.sh" || true

# Symlink inspector kitten (enables 'kitty +kitten inspector <subcommand>')
KITTEN_DIR="$HOME/.config/kitty"
mkdir -p "$KITTEN_DIR"
symlink "$SCRIPT_DIR/kittens/inspector" "$KITTEN_DIR/inspector"

# Symlink CLI entry point to ~/.local/bin (enables parallel instance support)
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
symlink "$SCRIPT_DIR/scripts/launch-cockpit.sh" "$LOCAL_BIN/kitty-kommander"
if ! echo "$PATH" | tr ':' '\n' | grep -q "$LOCAL_BIN"; then
    warn "\$PATH does not include $LOCAL_BIN — add it to your shell profile"
fi

# ── Generate sprites ─────────────────────────────────────────────────────────
echo
echo "Generating sprites..."
echo

if python3 -c "from PIL import Image" &>/dev/null; then
    python3 "$SCRIPT_DIR/sprites/generate.py"
    ok "yarn ball sprites"
else
    warn "Pillow not installed — skipping sprite generation (pip install Pillow)"
fi

# ── Desktop integration (right-click "Launch kitty-kommander") ──────────────
echo
echo "Installing desktop integration..."
echo

# .desktop file — "Open With" for directories (works across all file managers)
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
symlink "$SCRIPT_DIR/config/desktop/kitty-kommander.desktop" "$DESKTOP_DIR/kitty-kommander.desktop"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null
fi

# Add to MIME associations so it appears in "Open With" without manual setup
MIMEAPPS="$HOME/.config/mimeapps.list"
if [ -f "$MIMEAPPS" ]; then
    if ! grep -q "kitty-kommander.desktop" "$MIMEAPPS" 2>/dev/null; then
        if grep -q "^\[Added Associations\]" "$MIMEAPPS"; then
            # Append to existing section
            sed -i '/^\[Added Associations\]/a inode/directory=kitty-kommander.desktop;' "$MIMEAPPS"
        else
            echo -e "\n[Added Associations]\ninode/directory=kitty-kommander.desktop;" >> "$MIMEAPPS"
        fi
        ok "MIME association (Open With)"
    else
        ok "MIME association (already set)"
    fi
else
    mkdir -p "$(dirname "$MIMEAPPS")"
    echo -e "[Added Associations]\ninode/directory=kitty-kommander.desktop;" > "$MIMEAPPS"
    ok "MIME association (Open With)"
fi

# Nautilus extension — top-level right-click menu item (directory-only)
NAUTILUS_EXT_DIR="$HOME/.local/share/nautilus-python/extensions"
if python3 -c "from gi.repository import Nautilus" &>/dev/null; then
    mkdir -p "$NAUTILUS_EXT_DIR"
    symlink "$SCRIPT_DIR/config/desktop/kitty_kommander_nautilus.py" "$NAUTILUS_EXT_DIR/kitty_kommander.py"
    info "Restart Nautilus to activate: ${CYAN}nautilus -q${RST}"
else
    warn "nautilus-python not installed — skipping context menu extension"
    info "Install it: ${CYAN}sudo dnf install nautilus-python${RST}"
fi

echo
echo -e "${GREEN}Done.${RST} Launch the cockpit: ${CYAN}F7 > A${RST} in Kitty, or:"
echo -e "  kitty --session ~/.config/kitty/sessions/kommander.kitty-session"
echo -e "  Right-click any directory in Files → ${CYAN}Launch kitty-kommander${RST}"
echo
