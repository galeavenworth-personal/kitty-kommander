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
			// target_tab is required on window_* kinds — a window
			// created "somewhere" is a false-pass magnet (spawning
			// Sidebar in Cockpit instead of Dashboard passes the
			// title-only check). The mock enforces tab context.
			kitty_effects: [
				{kind: "window_created", title: "Sidebar", target_tab: "Dashboard"},
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
	{
		id:   "reload-noop"
		tags: ["basic", "reload", "idempotence"]

		story: """
			The operator runs reload on a session that's already
			healthy (doctor would report 0 drift). Reload diffs
			desired vs actual, finds them equal, and exits without
			touching kitty at all. This is the defining property of
			reconcile: running it on healthy state is a no-op, which
			means running it twice in a row is safe.

			Without this scenario, a regression that makes reload
			destructive (kill all, respawn all, on every invocation)
			passes every other scenario in the set — the user just
			loses window state every time they run reload.
			"""

		// Healthy starting state — matches the doctor-healthy fixture.
		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [{cmd: "claude"}]},
				{title: "Notebooks", windows: [{cmd: "euporie notebook"}]},
				{title: "Dashboard", windows: [
					{title: "DAG", cmd: "kommander-ui --dag"},
					{title: "Sidebar", cmd: "kommander-ui --sidebar"},
				]},
			]
		}

		invocation: "kommander reload"

		expected: {
			exit_code: 0
			stdout_contains: ["reconciled", "0 operations"]
			// THE assertion this scenario exists for: reload must
			// not have called the mock KittyController for any
			// create / close / send / focus operation. `no_change`
			// is the only effect recorded — absence of mutation IS
			// the invariant under test.
			kitty_effects: [{kind: "no_change"}]
		}

		help_summary: """
			Reload is idempotent:
			  kommander reload (on a healthy session)
			  → exit 0, '0 operations', no kitty touched.
			  → Safe to run twice; safe to run in cron.
			"""
	},
]
