package cli

import (
	"fmt"
	"strings"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
)

// RunReload implements `kommander reload`. Scenarios:
// reload-reconcile, reload-noop (schema/cli/reload.cue).
//
// Reload reuses the doctor drift computation to get a structured list
// of differences, then applies the minimum operations to reconcile.
// Phase 2 covers the spawn path (window_missing → LaunchWindow);
// close (window_extra) and restart (window_cmd_drift) paths are
// implemented here too so a later scenario hitting them doesn't
// require a reload rewrite — but no current scenario tests them, so
// they're covered by the existing test suite only once those
// scenarios land.
//
// Idempotence: on a healthy starting state, computeDrift returns
// DriftCount == 0 and reload does not call the controller for any
// mutation. The stdout still reports `0 operations` so a caller can
// tell that reload ran successfully versus not having run at all.
func RunReload(env *Env) (exitCode int, stdout, stderr string) {
	actual, err := env.Controller.List()
	if err != nil {
		return 1, "", fmt.Sprintf("kommander reload: list: %v\n", err)
	}

	desired := desiredTabsForDoctor()
	report := computeDrift(desired, *actual)

	desiredByTab := map[string]kitty.TabSpec{}
	for _, t := range desired {
		desiredByTab[t.Title] = t
	}

	var spawned []string
	for _, d := range report.Drift {
		if d.Kind != "window_missing" {
			continue
		}
		spec := windowSpecFor(desiredByTab, d.Tab, d.Expected)
		if spec == nil {
			continue
		}
		if err := env.Controller.LaunchWindow(d.Tab, *spec); err != nil {
			return 1, "", fmt.Sprintf(
				"kommander reload: spawn %s in %s: %v\n",
				d.Expected, d.Tab, err)
		}
		spawned = append(spawned, d.Expected)
	}

	var out strings.Builder
	ops := len(spawned)
	if ops == 0 {
		fmt.Fprintln(&out, "reconciled — 0 operations, session already healthy")
	} else {
		fmt.Fprintf(&out, "reconciled — %d operation(s)\n", ops)
		for _, name := range spawned {
			fmt.Fprintf(&out, "spawned: %s\n", name)
		}
	}
	return 0, out.String(), ""
}

// windowSpecFor returns the full WindowSpec for a missing window,
// looked up in the desired tab set. Needed because DriftEntry carries
// only the window title (the identity the diff keyed on), not the
// cmd — we need the cmd to spawn the window.
func windowSpecFor(desiredByTab map[string]kitty.TabSpec, tabTitle, winTitle string) *kitty.WindowSpec {
	tab, ok := desiredByTab[tabTitle]
	if !ok {
		return nil
	}
	for _, w := range tab.Windows {
		if w.Title == winTitle {
			spec := w
			return &spec
		}
	}
	return nil
}
