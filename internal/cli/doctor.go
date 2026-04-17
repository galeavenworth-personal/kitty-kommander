package cli

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
)

// DoctorReport is the JSON shape emitted to stdout. Scenarios assert
// against specific paths (`.status`, `.tabs_expected`, `.drift[0].kind`),
// so field names are load-bearing.
type DoctorReport struct {
	Status       string       `json:"status"`
	TabsExpected int          `json:"tabs_expected"`
	TabsFound    int          `json:"tabs_found"`
	DriftCount   int          `json:"drift_count"`
	Drift        []DriftEntry `json:"drift"`
	Summary      string       `json:"summary"`
}

// DriftEntry describes one divergence between desired and actual.
// Kinds:
//
//	tab_missing     → a desired tab is absent from kitty
//	tab_extra       → a tab in kitty is not in the desired set
//	window_missing  → a window expected inside a tab is absent
//	window_extra    → a window in kitty's tab is not in the desired set
//	window_cmd_drift → a window exists but its cmd[0] differs
//
// Only window_missing appears in a Phase-2 scenario; the others are
// defined here so the doctor output shape is stable as later
// scenarios (reload-kill-stale, reload-restart-changed) land.
type DriftEntry struct {
	Kind     string `json:"kind"`
	Tab      string `json:"tab,omitempty"`
	Expected string `json:"expected,omitempty"`
	Actual   string `json:"actual,omitempty"`
}

// RunDoctor implements `kommander doctor`. It reads actual kitty
// state via Controller.List(), diffs it against the desired state
// from desiredTabs(), and emits a JSON report. Exit 0 on no drift,
// exit 1 on drift. The reconciliation hint goes to stderr so stdout
// is a clean JSON stream.
func RunDoctor(env *Env) (exitCode int, stdout, stderr string) {
	actual, err := env.Controller.List()
	if err != nil {
		return 1, "", fmt.Sprintf("kommander doctor: list: %v\n", err)
	}
	desired := desiredTabsForDoctor()

	report := computeDrift(desired, *actual)

	buf, err := json.Marshal(report)
	if err != nil {
		return 1, "", fmt.Sprintf("kommander doctor: marshal: %v\n", err)
	}

	if report.DriftCount == 0 {
		return 0, string(buf), ""
	}
	return 1, string(buf), "run 'kommander reload' to reconcile\n"
}

// computeDrift returns a DoctorReport for the desired/actual pair.
// The comparison is tab-title-keyed (order insensitive for tabs) and
// window-title-keyed inside each tab. A window without a title is
// keyed on the first cmd token — kitty @ ls returns running
// processes, and a user-launched "claude" window has no title but
// has `cmd: ["claude"]`.
func computeDrift(desired []kitty.TabSpec, actual kitty.State) DoctorReport {
	r := DoctorReport{
		Status:       "healthy",
		TabsExpected: len(desired),
		TabsFound:    len(actual.Tabs),
		Drift:        []DriftEntry{},
	}

	actualByTitle := map[string]kitty.TabState{}
	for _, t := range actual.Tabs {
		actualByTitle[t.Title] = t
	}
	desiredByTitle := map[string]kitty.TabSpec{}
	for _, t := range desired {
		desiredByTitle[t.Title] = t
	}

	for _, dt := range desired {
		at, ok := actualByTitle[dt.Title]
		if !ok {
			r.Drift = append(r.Drift, DriftEntry{
				Kind:     "tab_missing",
				Expected: dt.Title,
			})
			continue
		}
		// Check windows.
		actualWinByKey := map[string]kitty.WindowState{}
		for _, w := range at.Windows {
			actualWinByKey[winKey(w.Title, w.Cmd)] = w
		}
		for _, dw := range dt.Windows {
			want := winKey(dw.Title, dw.Cmd)
			if _, ok := actualWinByKey[want]; !ok {
				r.Drift = append(r.Drift, DriftEntry{
					Kind:     "window_missing",
					Tab:      dt.Title,
					Expected: dw.Title,
				})
			}
		}
	}
	for _, at := range actual.Tabs {
		if _, ok := desiredByTitle[at.Title]; !ok {
			r.Drift = append(r.Drift, DriftEntry{
				Kind:   "tab_extra",
				Tab:    at.Title,
				Actual: at.Title,
			})
		}
	}

	r.DriftCount = len(r.Drift)
	if r.DriftCount > 0 {
		r.Status = "drift"
		r.Summary = fmt.Sprintf("drift: %d issue(s) — %d/%d tabs, %d drift",
			r.DriftCount, r.TabsFound, r.TabsExpected, r.DriftCount)
	} else {
		r.Summary = fmt.Sprintf("healthy: %d/%d tabs, 0 drift",
			r.TabsFound, r.TabsExpected)
	}
	return r
}

// winKey uniquely identifies a window within a tab. Title is preferred
// (unambiguous, matches the `--title` set at launch). Falls back to
// cmd[0] for windows that were not given a title (e.g. Driver's
// "claude" window, Notebooks' "euporie notebook" window in the
// doctor-healthy fixture).
func winKey(title string, cmd []string) string {
	if title != "" {
		return "title:" + title
	}
	if len(cmd) > 0 {
		return "cmd0:" + firstToken(cmd[0])
	}
	return ""
}

// firstToken returns the first whitespace-separated token of s. The
// doctor-healthy fixture sets `cmd: "euporie notebook"` as a single
// string — that becomes `[]string{"euporie notebook"}` via StringOrList
// — and the desired tab has `Cmd: []string{"euporie", "notebook"}`.
// We match on the first word either way.
func firstToken(s string) string {
	if i := strings.IndexAny(s, " \t"); i >= 0 {
		return s[:i]
	}
	return s
}
