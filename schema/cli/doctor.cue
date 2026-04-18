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
		//
		// Windows carry titles matching schema/session/default.cue per
		// uib.3.C Option A — production LaunchTab passes --title at
		// launch, kitty's override survives any later OSC 0 escape from
		// the process, so kitten @ ls reports the CUE-declared title
		// verbatim. Driver/Notebooks untitled fixtures (pre-3.C) re-hid
		// the winKey asymmetry under the mock and shipped a bug that
		// reload amplified in the field.
		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [{title: "Driver", cmd: "claude"}]},
				{title: "Notebooks", windows: [{title: "Notebooks", cmd: "euporie notebook"}]},
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
				{title: "Driver", windows: [{title: "Driver", cmd: "claude"}]},
				{title: "Notebooks", windows: [{title: "Notebooks", cmd: "euporie notebook"}]},
				// Sidebar missing from Dashboard — that is the drift.
				// Driver/Notebooks remain healthy (titles match
				// default.cue per Option A); without their titles the
				// drift count would balloon to 3 and the json_paths
				// check against .drift[0] would become nondeterministic.
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
	{
		id:   "doctor-healthy-real-titles"
		tags: ["common", "doctor", "option-a-titled-layout"]

		story: """
			uib.3.C Option A contract. Production LaunchTab passes
			--title <CUE-declared title> to `kitten @ launch`; kitty
			treats that as a persistent override that survives any
			OSC 0 escape the process emits later (claude's spinner,
			euporie's process name, bash's cwd escapes). So the state
			kitty @ ls returns post-launch carries the CUE-declared
			titles verbatim — not the process-driven runtime strings
			integrator observed in the pre-3.C repro ("⠂ cell-leader",
			"euporie-notebook").

			This scenario asserts the full titled layout doctor must
			validate under Option A: Driver titled "Driver", Notebooks
			titled "Notebooks", Dashboard/Sidebar titled "Sidebar",
			Cockpit dynamic. The fixture deliberately declares the
			title on every non-dynamic window — that IS the shape a
			real `kitten @ ls` returns after a correct launch, per the
			live kitty probe (one-shot OSC 0 + 10Hz continuous stream
			both failed to beat --title).

			Red-before-green: until schema/session/default.cue grows
			`title:` on its Driver and Notebooks windows, the desired
			side's winKey is cmd0:<token> while this fixture produces
			title:<Title> — they never match, drift is reported, test
			fails. The contract is what pins Option A's implementation
			in place; dropping --title from LaunchTab silently regresses
			3.F's real-kitty run while mock-path tests still pass, so
			3.F's integration scenario is what catches that direction.
			"""

		setup: kitty_state: {
			tabs: [
				{title: "Cockpit", windows: []},
				{title: "Driver", windows: [
					{title: "Driver", cmd: ["claude", "--agent",
						"cell-leader", "--dangerously-skip-permissions"]},
				]},
				{title: "Notebooks", windows: [
					{title: "Notebooks", cmd: ["euporie", "notebook"]},
				]},
				{title: "Dashboard", windows: [
					{title: "Sidebar", cmd: ["kommander-ui", "--sidebar"]},
				]},
			]
		}

		invocation: "kommander doctor"

		expected: {
			exit_code: 0
			stdout_contains: ["healthy", "4/4 tabs", "0 drift"]
			json_paths: [
				{path: ".status", contains: "healthy"},
				{path: ".tabs_expected", equals: "4"},
				{path: ".drift_count", equals: "0"},
			]
		}

		help_summary: """
			Check session health with titled windows:
			  kommander doctor
			  → Each desired window's title matches kitty's reported
			    title (--title override survives process OSC 0 escapes).
			  → Healthy when titles + tab structure agree with CUE.
			"""
	},
]
