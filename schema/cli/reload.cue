// Reload scenarios — `kommander reload`.
//
// Reload is the reconciliation step after doctor detects drift. It
// diffs desired (CUE) vs actual (`kitty @ ls`) and performs the
// minimum set of kitty operations to bring them into agreement:
//
//   - spawn windows that exist in desired but not actual
//   - close windows that exist in actual but not desired
//   - restart windows whose command changed
//
// This scenario covers the spawn path — the most common drift type
// (a window died) deserves the first-class scenario. Close and
// restart paths get scenarios in subsequent work once launch and
// doctor are green.
package cli

scenarios: reload: [
	{
		id:   "reload-reconcile"
		tags: ["basic", "reload"]

		story: """
			After doctor reports drift (the Sidebar window died and
			is missing from the Dashboard tab), the operator runs
			reload. It diffs desired vs actual, spawns just the one
			missing window, and reports what it did. A follow-up
			doctor invocation would now report healthy.
			"""

		// Setup mirrors the end-state of doctor-drift-detected —
		// Dashboard is missing its Sidebar window. That's the
		// precondition reload is meant to clear.
		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [{cmd: "claude"}]},
				{title: "Notebooks", windows: [{cmd: "euporie notebook"}]},
				{title: "Dashboard", windows: [
					{title: "DAG", cmd: "kommander-ui --dag"},
					// Sidebar missing — reload spawns it.
				]},
			]
		}

		invocation: "kommander reload"

		expected: {
			exit_code: 0
			stdout_contains: ["reconciled", "spawned: Sidebar"]
			kitty_effects: [
				{kind: "window_created", match: "Sidebar"},
			]
		}

		help_summary: """
			Reconcile session state:
			  kommander reload
			  → Diffs CUE desired state vs kitty actual state.
			  → Kills stale windows, spawns missing ones, restarts changed.
			  → Exit 0 always; check `kommander doctor` after.
			"""
	},
]
