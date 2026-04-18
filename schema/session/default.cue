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
// Driver and Notebooks windows carry explicit titles per uib.3.C
// Option A. Production LaunchTab passes --title <Title> to kitten @
// launch; kitty treats that as a persistent override beating any
// OSC 0 escape the process emits (claude's "⠂ cell-leader" spinner,
// euporie's "euporie-notebook" default). Verified via live kitty
// probe pre-3.C: --title survived both a one-shot OSC 0 escape and a
// 10Hz continuous stream across 40+ process-side rewrites. Doctor's
// winKey therefore matches title-on-both-sides and drift stays at 0
// under a healthy launch. See schema/cli/doctor.cue
// "doctor-healthy-real-titles" for the executable contract.
//
// Trade-off: the kitty tab bar shows static CUE-declared titles
// (Driver, Notebooks) instead of runtime process indicators. Accepted
// cost — runtime liveness is visible in window contents, and the
// operator-facing upside is a stable, CUE-declarable session identity.
// Omit `title:` on any single window if dynamic titling is wanted for
// that slot (at the cost of re-introducing winKey drift for that one
// window, so consider whether it's worth it).
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
