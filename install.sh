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

# kommander-ui wrapper (NOT a symlink — a generated shell script).
#
# packages/ui/bin/kommander-ui uses `#!/usr/bin/env -S node --import=tsx`,
# where `--import=tsx` resolves the tsx package from the CALLER'S CWD via
# node_modules upward-walk, not from the script's own location. A bare
# symlink therefore fails with ERR_MODULE_NOT_FOUND when invoked from any
# CWD outside packages/ui — which is every production invocation path
# (kommander launch opens the Dashboard window with CWD=project-dir).
#
# The wrapper cd's into packages/ui before execing node, so tsx resolves
# correctly regardless of the caller's CWD. The repo path is baked in
# at install time from $SCRIPT_DIR. Re-run install.sh to update.
#
# The wrapper carries a sentinel line. Re-runs identify their own
# generated file via that sentinel and regenerate it atomically (temp
# file + mv). If ~/.local/bin/kommander-ui exists but is NOT one of
# ours (operator hand-installed something else at that name), we warn
# and preserve — matches the symlink() helper's posture for foreign
# files. An old symlink at that path (from a prior bare-symlink
# attempt) gets replaced by the wrapper.
KOMMANDER_UI_WRAPPER="$LOCAL_BIN/kommander-ui"
KOMMANDER_UI_SENTINEL="# kitty-kommander kommander-ui wrapper — generated by install.sh"

install_kommander_ui_wrapper() {
    local dst="$1"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        # Regular file: only overwrite if it's one we generated. A
        # user-authored kommander-ui script is preserved; the warning
        # mirrors the symlink() helper's convention. Return nonzero so
        # the caller knows verification should not run — skip doesn't
        # mean our wrapper is active.
        if ! head -n 3 "$dst" 2>/dev/null | grep -Fq "$KOMMANDER_UI_SENTINEL"; then
            warn "kommander-ui — exists (not our wrapper), skipping. Back up and re-run to replace."
            return 1
        fi
    elif [ -L "$dst" ]; then
        # An old symlink (from a prior release that tried bare-symlink
        # install) gets replaced by the wrapper.
        rm -f "$dst"
    fi

    local tmp
    tmp="$(mktemp "${dst}.XXXXXX")" || {
        fail "kommander-ui — mktemp failed"
        return
    }
    # Write via heredoc. $SCRIPT_DIR is the repo root; the wrapper cd's
    # into packages/ui where node_modules/tsx is installed, then execs
    # node against ./bin/kommander-ui — the package's Node entry,
    # which invokes main() to actually render.
    #
    # Prior revision (c187816) wrote `src/ink.js` here. That file does
    # not exist; tsx's extension-bridge silently resolved it to
    # ink.tsx. Node loaded the module (import side-effects only —
    # main() was NEVER called), exited 0 with no render. Ghost
    # execution that passed every exit-code smoke check. The post-
    # install verification below asserts on RENDERED content to catch
    # any recurrence of this class of bug.
    cat >"$tmp" <<EOF
#!/usr/bin/env bash
$KOMMANDER_UI_SENTINEL
# Generated from: $SCRIPT_DIR/install.sh
# Do NOT edit by hand — re-run install.sh to regenerate.
set -euo pipefail
cd '$SCRIPT_DIR/packages/ui'
exec node --import=tsx ./bin/kommander-ui "\$@"
EOF
    # 0755: world-readable and executable. mktemp defaults to 0600 so
    # `chmod +x` alone lands at 0711; set explicit 0755 to match the
    # readability of every other file install.sh touches.
    chmod 0755 "$tmp"
    mv -f "$tmp" "$dst"
    ok "kommander-ui wrapper -> $SCRIPT_DIR/packages/ui"
}

# Verify the wrapper actually renders (NOT just exits 0). The prior
# revision of this install step passed every exit-code smoke check
# while silently doing nothing — ghost execution via tsx's extension-
# bridge resolving a nonexistent path. The assertion below probes for
# a fixture-specific string ("Fix auth bug" from SIDEBAR_SHOWS_HEALTH)
# in the wrapper's combined stdout+stderr. Run from /tmp to also
# prove the `cd` is effective — if the wrapper forgot to cd into
# packages/ui, tsx resolution fails with ERR_MODULE_NOT_FOUND.
#
# Only runs when install_kommander_ui_wrapper returned success
# (i.e., we actually wrote our wrapper). When the operator has a
# foreign kommander-ui at that path we skipped; verifying theirs
# would produce misleading output.
#
# timeout bounds at 4s — anything longer is either a hang or a node
# startup anomaly worth seeing in the warning.
if install_kommander_ui_wrapper "$KOMMANDER_UI_WRAPPER"; then
    if command -v node >/dev/null 2>&1; then
        _ku_verify_output="$(cd /tmp && timeout 4 "$KOMMANDER_UI_WRAPPER" --sidebar </dev/null 2>&1 || true)"
        if echo "$_ku_verify_output" | grep -qF "Fix auth bug"; then
            ok "kommander-ui render verified (SIDEBAR_SHOWS_HEALTH fixture strings in output)"
        else
            warn "kommander-ui wrapper installed but did NOT render expected fixture strings"
            warn "  repro: cd /tmp && kommander-ui --sidebar"
            warn "  expected: output containing 'Fix auth bug'"
            warn "  got: $(echo "$_ku_verify_output" | head -c 200)"
        fi
        unset _ku_verify_output
    else
        warn "kommander-ui render check skipped — node not installed"
    fi
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
