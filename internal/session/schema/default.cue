// Default kommander session — the 4-tab layout every project gets
// unless it provides its own <project-dir>/kommander.cue overlay.
//
// Matches what internal/cli/desired.go hardcoded prior to uib.3.0
// (modulo the DAG deferral per uib.3.DAG — see below). Kept here
// instead of in Go so the binary's desired state is CUE-sourced at
// runtime, not compiled-in. The binary loads this file (via
// go:embed or install path), then applies any project overlay, then
// uses the unified result as the desired session for launch,
// doctor, and reload.
//
// Dashboard has one window (Sidebar) only. The DAG Ink app is
// deferred to uib.3.DAG; when that ships, Dashboard will have two
// windows and this file gets a second entry.
//
// Driver and Notebooks windows are INTENTIONALLY untitled. This
// mirrors the prior hardcoded desiredTabs() layout exactly and
// leaves the winKey asymmetry described by uib.3.C unresolved here.
// 3.C will decide whether to fix that by adding explicit --titles
// to desired windows OR by making doctor's winKey fuzzy-match
// process titles. This file does not pre-empt that decision.
package session

default: #Session & {
	tabs: [
		{
			title:   "Cockpit"
			dynamic: true
			windows: []
		},
		{
			title: "Driver"
			windows: [{
				cmd: ["claude", "--agent", "cell-leader",
					"--dangerously-skip-permissions"]
			}]
		},
		{
			title: "Notebooks"
			windows: [{
				cmd: ["euporie", "notebook"]
			}]
		},
		{
			title: "Dashboard"
			windows: [{
				title: "Sidebar"
				cmd: ["kommander-ui", "--sidebar"]
				ink:  true
			}]
		},
	]
}
