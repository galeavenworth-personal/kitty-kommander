package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
)

// RunLaunch implements `kommander launch <dir>`. Scenarios:
// launch-basic, launch-missing-dir, cue-config-driven-layout,
// launch-multi-window-tab (schema/cli/launch.cue).
//
// Launch derives the session slug and socket path from the project
// directory basename, validates the directory exists, loads the
// desired tab layout from CUE (embedded default + optional per-project
// kommander.cue overlay), and spawns each tab via the KittyController.
// It does NOT spawn agent panes inside Cockpit — those come from
// `kommander pane` at runtime.
//
// Tab spawn semantics mirror `kitten @ launch`: `--type=tab` accepts
// exactly one initial command, not a list. Tabs with a single window
// use one LaunchTab call. Tabs with N>1 windows use one LaunchTab
// (carrying the first window's cmd) plus N-1 LaunchWindow calls
// targeting the tab by title. This matches the launch-multi-window-tab
// scenario's expected effect stream: tab_created once, window_created
// per additional window with target_tab set.
//
// When a kommander.cue overlay is loaded, stdout reports
// `config: kommander.cue` so the operator can tell which layout the
// binary used. Absence of this line means "default layout, no overlay
// found" — useful for catching typos in the overlay filename.
//
// Error path: if <dir> doesn't exist, fail immediately with a clear
// error on stderr and leave kitty untouched. Half-built sessions are
// worse than no session.
func RunLaunch(env *Env) (exitCode int, stdout, stderr string) {
	if len(env.Args) == 0 {
		return 1, "", "kommander launch: missing <dir> argument\n"
	}
	dir := env.Args[0]

	info, err := os.Stat(dir)
	if err != nil || !info.IsDir() {
		return 1, "", fmt.Sprintf("kommander launch: directory does not exist: %s\n", dir)
	}

	slug := deriveSlug(dir)
	session := "cockpit-" + slug
	socket := "unix:/tmp/kitty-kommander-" + slug

	tabs, overlayPath, err := desiredTabs(dir)
	if err != nil {
		return 1, "", fmt.Sprintf("kommander launch: %v\n", err)
	}

	var out strings.Builder
	fmt.Fprintf(&out, "session: %s\n", session)
	fmt.Fprintf(&out, "socket: %s\n", socket)
	if overlayPath != "" {
		fmt.Fprintf(&out, "config: %s\n", overlayPath)
	}

	for _, t := range tabs {
		if err := spawnTab(env.Controller, t); err != nil {
			return 1, out.String(),
				fmt.Sprintf("kommander launch: %v\n", err)
		}
	}

	return 0, out.String(), ""
}

// spawnTab creates a tab and all its windows. The first window (if any)
// is folded into the tab_created call as `kitten @ launch --type=tab`'s
// initial cmd; remaining windows are spawned with LaunchWindow against
// the tab's title. Passing only the first window to LaunchTab keeps
// mock and production state in sync — mock.LaunchTab stores every
// nested window into state (matching real kitty's behavior where the
// initial argv becomes the first window's running process), so feeding
// it the additional windows there would double-count them once those
// windows are ALSO explicitly LaunchWindow'd.
//
// Dynamic tabs (Cockpit) have Windows == nil and get a bare
// --type=tab call. Empty tabs spawn with an interactive shell by
// default per kitty's own semantics.
//
// Window spawn errors abort the whole launch — a half-built tab with
// windows 1..N-1 missing is a worse state than none at all, matching
// the launch-missing-dir discipline.
func spawnTab(ctl kitty.Controller, t kitty.TabSpec) error {
	initial := t
	if len(t.Windows) > 0 {
		initial.Windows = t.Windows[:1]
	}
	if err := ctl.LaunchTab(initial); err != nil {
		return fmt.Errorf("LaunchTab %q: %w", t.Title, err)
	}
	if len(t.Windows) < 2 {
		return nil
	}
	for _, w := range t.Windows[1:] {
		if err := ctl.LaunchWindow(t.Title, w); err != nil {
			return fmt.Errorf("LaunchWindow %q in %q: %w", w.Title, t.Title, err)
		}
	}
	return nil
}

// deriveSlug mirrors launch-cockpit.sh's slug rule: basename,
// lowercased, non-alnum runs collapsed to a single hyphen. Multiple
// projects with the same basename collide — rename one, per CLAUDE.md.
func deriveSlug(dir string) string {
	base := filepath.Base(dir)
	base = strings.ToLower(base)
	var b strings.Builder
	prevHyphen := false
	for _, r := range base {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
			b.WriteRune(r)
			prevHyphen = false
		} else if !prevHyphen {
			b.WriteRune('-')
			prevHyphen = true
		}
	}
	return strings.Trim(b.String(), "-")
}
