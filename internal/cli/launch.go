package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
)

// RunLaunch implements `kommander launch <dir>`. Scenarios:
// launch-basic, launch-missing-dir (schema/cli/launch.cue).
//
// Launch derives the session slug and socket path from the project
// directory basename, validates the directory exists, and calls
// Controller.LaunchTab for each of the four tabs: Cockpit, Driver,
// Notebooks, Dashboard. It does NOT spawn agent panes inside Cockpit
// — those come from `kommander pane` at runtime.
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

	var out strings.Builder
	fmt.Fprintf(&out, "session: %s\n", session)
	fmt.Fprintf(&out, "socket: %s\n", socket)

	tabs := []kitty.TabSpec{
		{Title: "Cockpit"},
		{Title: "Driver", Windows: []kitty.WindowSpec{{
			Cmd: []string{"claude", "--agent", "cell-leader",
				"--dangerously-skip-permissions"},
		}}},
		{Title: "Notebooks", Windows: []kitty.WindowSpec{{
			Cmd: []string{"euporie", "notebook"},
		}}},
		{Title: "Dashboard", Windows: []kitty.WindowSpec{
			{Title: "DAG", Cmd: []string{"kommander-ui", "--dag"}},
			{Title: "Sidebar", Cmd: []string{"kommander-ui", "--sidebar"}},
		}},
	}
	for _, t := range tabs {
		if err := env.Controller.LaunchTab(t); err != nil {
			return 1, out.String(),
				fmt.Sprintf("kommander launch: LaunchTab %q: %v\n", t.Title, err)
		}
	}

	return 0, out.String(), ""
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
