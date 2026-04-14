---
name: cockpit
description: This skill should be used when managing the Kitty terminal cockpit session, controlling terminal panes and tabs, sending commands to specific panes, checking teammate status, launching or restarting the cockpit session, or performing any terminal window management. Activate for "launch cockpit", "send to pane", "focus tab", "teammate status", "list panes", "manage windows", "terminal layout" requests.
---

## When to Use This Skill
- Launching or restarting the cockpit session
- Sending text/commands to specific terminal panes
- Switching focus between tabs or panes
- Querying the state of kitty windows/tabs
- Managing tmux panes within the cockpit

## Kitty Remote Control

All commands use the kitty remote control socket. IMPORTANT: The socket path includes the PID and varies per session. Always use the environment variable:

```bash
kitty @ --to "$KITTY_LISTEN_ON" <command>
```

If `$KITTY_LISTEN_ON` is not set, find the socket:
```bash
ls /tmp/kitty-actuator-*
```

### List all windows and tabs
```bash
kitty @ --to "$KITTY_LISTEN_ON" ls
```
Returns JSON with all OS windows, tabs, and their windows.

### Send text to a specific window
```bash
# By title match
kitty @ --to "$KITTY_LISTEN_ON" send-text --match "title:Events" "echo hello\n"

# By tab title
kitty @ --to "$KITTY_LISTEN_ON" send-text --match "title:Cockpit" "ls -la\n"
```

### Focus a tab
```bash
# By index (0-based)
kitty @ --to "$KITTY_LISTEN_ON" focus-tab --match "index:0"

# By title
kitty @ --to "$KITTY_LISTEN_ON" focus-tab --match "title:Notebooks"
```

### Set tab/window title
```bash
kitty @ --to "$KITTY_LISTEN_ON" set-tab-title --match "index:0" "Lead Agent"
```

### Create new window in current tab
```bash
kitty @ --to "$KITTY_LISTEN_ON" launch --type=window --title "Monitor" htop
```

## tmux Pane Management

The cockpit's first tab runs tmux session "cockpit". Agent Teams creates panes within it.

### List tmux panes
```bash
tmux list-panes -t cockpit -F "#{pane_index}: #{pane_current_command} (#{pane_width}x#{pane_height})"
```

### Send keys to a tmux pane
```bash
tmux send-keys -t cockpit.0 "echo hello" Enter
```

### Navigate tmux panes
```bash
tmux select-pane -t cockpit.0    # Select pane by index
# Or use Alt+1..4 keybinds (configured in tmux.conf)
```

## Cockpit Session Lifecycle

### Launch cockpit
```bash
kitty --session ~/.config/kitty/sessions/actuator.kitty-session
```
Or press F7 then A if already in Kitty (keybind configured in kitty.conf).

### Save current session state
Press F7 then S (keybind configured in kitty.conf).

### Check cockpit health
```bash
# Kitty responding?
kitty @ --to "$KITTY_LISTEN_ON" ls > /dev/null 2>&1 && echo "kitty: ok" || echo "kitty: no socket"

# tmux session alive?
tmux has-session -t cockpit 2>/dev/null && echo "tmux: ok" || echo "tmux: no session"
```

## Tab Layout Reference

| Index | Name | Purpose |
|-------|------|---------|
| 0 | Cockpit | tmux session "cockpit" — Agent Teams canvas |
| 1 | Files | File browser (bash) |
| 2 | Notebooks | euporie notebook editor |
| 3 | Logs | Event stream + git log |

## Guidelines
- Always use `$KITTY_LISTEN_ON` for the socket path — never hardcode
- The `--match` flag uses kitty's matching syntax: `title:`, `index:`, `id:`, `env:`
- When sending text, always append `\n` to execute the command
- For long-running commands in panes, check if the pane is busy before sending
- The tmux session name is always "cockpit" (created by the session file with `-A -s cockpit`)
