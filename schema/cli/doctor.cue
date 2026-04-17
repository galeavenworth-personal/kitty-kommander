// Doctor scenarios — `kommander doctor`.
//
// Doctor is the drift detector: it reads the CUE desired state and
// compares it against `kitty @ ls` output. Two scenarios here prove
// the two outcomes: everything matches (healthy), or something is
// missing / extra / wrong (drift).
//
// The drift scenario deliberately uses exit_code: 1 — scripts that
// wrap doctor (CI, cron) depend on the exit code to branch on health.
// The human-readable drift report still goes to stdout so it's
// captured in logs; the reconciliation hint goes to stderr.
package cli

scenarios: doctor: [
	{
		id:   "doctor-healthy"
		tags: ["basic", "doctor"]

		story: """
			After launching, the operator runs doctor to verify that
			the actual kitty state matches the CUE desired state.
			All four tabs exist with the correct windows and commands,
			so the report says healthy and exits 0.
			"""

		// kitty_state is injected into the mock KittyController for
		// test runs. For live runs against a real kitty instance the
		// test harness asserts `kitty @ ls` returns an equivalent
		// shape before running the scenario.
		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [{cmd: "claude"}]},
				{title: "Notebooks", windows: [{cmd: "euporie notebook"}]},
				{title: "Dashboard", windows: [
					{title: "Sidebar", cmd: "kommander-ui --sidebar"},
				]},
			]
		}

		invocation: "kommander doctor"

		expected: {
			exit_code: 0
			stdout_contains: ["healthy", "4/4 tabs", "0 drift"]
			// `equals` on integer paths — substring would admit
			// `.tabs_expected == 40` or `.drift_count == 10` as
			// passing. The enum-valued `.status` stays `contains`
			// since "healthy" is a stable full word.
			json_paths: [
				{path: ".status", contains:        "healthy"},
				{path: ".tabs_expected", equals:   "4"},
				{path: ".drift_count", equals:     "0"},
			]
		}

		help_summary: """
			Check session health:
			  kommander doctor
			  → JSON report: tab/window structure vs CUE desired state.
			  → Exit 0 healthy, exit 1 drift.
			"""
	},
	{
		id:   "doctor-drift-detected"
		tags: ["common", "doctor"]

		story: """
			A Dashboard window crashed. The operator runs doctor and
			sees drift: the Sidebar window is missing from the
			Dashboard tab. The report identifies exactly what's wrong
			(which tab, which window) and suggests `kommander reload`
			as the fix. Exit code is 1 so CI wrappers can branch.
			"""

		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [{cmd: "claude"}]},
				{title: "Notebooks", windows: [{cmd: "euporie notebook"}]},
				// Sidebar missing from Dashboard — that is the drift.
				// Dashboard has no other windows (DAG deferred to
				// uib.3.DAG), so an empty window list is the correct
				// fixture for the "Dashboard degraded" state.
				{title: "Dashboard", windows: []},
			]
		}

		invocation: "kommander doctor"

		expected: {
			exit_code: 1
			stdout_contains: ["drift", "Sidebar", "missing"]
			// Enum-valued paths use `equals` — substring would admit
			// `.status == "no_drift"` for a "drift" expectation, or
			// `.drift[0].kind == "window_missing_expected"` for
			// "window_missing". Titles/free text stay `contains`.
			json_paths: [
				{path: ".status", equals:            "drift"},
				{path: ".drift[0].kind", equals:     "window_missing"},
				{path: ".drift[0].tab", contains:    "Dashboard"},
				{path: ".drift[0].expected", contains: "Sidebar"},
			]
			// Reconciliation hint on stderr so stdout can be piped
			// to JSON parsers without noise.
			stderr_contains: ["run 'kommander reload' to reconcile"]
		}

		help_summary: """
			Drift detected:
			  kommander doctor
			  → exit 1, JSON on stdout lists missing/extra windows.
			  → stderr suggests 'kommander reload' to fix.
			"""
	},
]
