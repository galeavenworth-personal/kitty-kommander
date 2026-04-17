// Default kommander session — the 4-tab layout every project gets
// unless it provides its own <project-dir>/kommander.cue overlay.
//
// Matches what internal/cli/desired.go hardcoded prior to uib.3.0.
// Kept here instead of in Go so the binary's desired state is CUE-
// sourced at runtime, not compiled-in. The binary loads this file
// (via go:embed or install path), then applies any project overlay,
// then uses the unified result as the desired session for launch,
// doctor, and reload.
//
// Dashboard has one window (Sidebar) only. The DAG Ink app is
// deferred to uib.3.DAG; when that ships, Dashboard will have two
// windows and this file gets a second entry.
//
// Driver and Notebooks windows carry explicit titles ("Driver",
// "Notebooks") rather than relying on process names. This matches
// uib.3.C's resolution for the doctor winKey asymmetry — a window
// whose process will retitle itself at runtime (claude → "⠂ cell-
// leader", euporie → "euporie-notebook") MUST have an explicit
// --title so doctor can match reliably.
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
				title: "Driver"
				cmd: ["claude", "--agent", "cell-leader",
					"--dangerously-skip-permissions"]
			}]
		},
		{
			title: "Notebooks"
			windows: [{
				title: "Notebooks"
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
