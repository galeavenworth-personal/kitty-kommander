// Launch scenarios — `kommander launch <dir>`.
//
// Launch is the entry point. Every other subcommand assumes a session
// exists; these scenarios are what prove one can be brought up.
package cli

scenarios: launch: [
	{
		id:   "launch-basic"
		tags: ["basic", "launch"]

		story: """
			An operator wants to launch a kitty-kommander instance for
			their project directory. The command reads the CUE session
			schema, derives the slug and socket path from the directory
			basename, and launches kitty with the configured four tabs:
			Cockpit, Driver, Notebooks, Dashboard.
			"""

		// The test harness will create a real temp dir and substitute
		// its path before asserting. The literal path here is just for
		// help-text clarity — scenario readers see a realistic shape.
		invocation: "kommander launch /home/user/my-app"

		expected: {
			exit_code: 0
			stdout_contains: [
				"session: cockpit-my-app",
				"socket: unix:/tmp/kitty-kommander-my-app",
			]
			// `title` on a tab_created effect asserts the value of
			// the `--tab-title` arg passed to `kitten @ launch`.
			// NOT the title kitty ends up displaying. If kommander
			// forgets --tab-title, the tab shows as the process
			// name ("claude") and the mock records a tab_created
			// with a different title — the test fails correctly.
			kitty_effects: [
				{kind: "tab_created", title: "Cockpit"},
				{kind: "tab_created", title: "Driver"},
				{kind: "tab_created", title: "Notebooks"},
				{kind: "tab_created", title: "Dashboard"},
			]
		}

		help_summary: """
			Launch a kommander instance:
			  kommander launch /path/to/project
			  → Opens kitty with Cockpit, Driver, Notebooks, Dashboard tabs.
			  → Derives session name + socket path from the directory basename.
			"""
	},
	{
		id:   "launch-missing-dir"
		tags: ["error", "launch", "validation"]

		story: """
			An operator invokes 'kommander launch' with a directory that
			does not exist. The command fails immediately with a clear
			error pointing at the bad path, and does not touch kitty.
			A valid session is never partially created.
			"""

		invocation: "kommander launch /nonexistent/path"

		expected: {
			exit_code: 1
			stderr_contains: [
				"directory does not exist",
				"/nonexistent/path",
			]
			// Explicit no_change: this scenario's entire point is
			// that a failed precondition must not leak a half-built
			// kitty session. The mock KittyController records zero
			// effects; the assertion fails if any effect is recorded.
			kitty_effects: [{kind: "no_change"}]
		}

		help_summary: """
			Error — directory does not exist:
			  kommander launch /bad/path
			  → exit 1, no kitty launched, error on stderr.
			"""
	},
	{
		id:   "cue-config-driven-layout"
		tags: ["common", "launch", "config"]

		story: """
			An operator wants a non-default session layout for a
			specific project. They drop a kommander.cue file in the
			project root describing a two-tab custom layout. When they
			run 'kommander launch <dir>', the binary reads
			kommander.cue from the project directory, unifies it with
			the compiled-in default, and creates exactly the tabs the
			overlay describes — not the default Cockpit/Driver/
			Notebooks/Dashboard set.

			This proves the binary's desired state is CUE-sourced at
			runtime. If the binary ignores the overlay and uses a
			compiled-in layout, the expected tab_created effects do
			not match and the test fails. Negative assertion via
			stdout_excludes guards against silent fallback: if the
			default is used, the default tab titles appear in the
			binary's startup output.
			"""

		// The overlay file content is verbatim — the test harness
		// writes it to <tmp>/kommander.cue before invocation. CUE
		// inside the string is not vet-validated at scenario-vet time;
		// the binary's CUE loader validates it at runtime.
		setup: files: {
			"kommander.cue": """
				package kommander

				session: tabs: [
				    {title: "Custom", windows: [{cmd: ["my-agent"]}]},
				    {title: "Worker", windows: [{cmd: ["worker-process"]}]},
				]
				"""
		}

		invocation: "kommander launch /home/user/my-project"

		expected: {
			exit_code: 0
			stdout_contains: [
				"session: cockpit-my-project",
				"config: kommander.cue",
			]
			// If the binary falls back to the compiled-in default,
			// one or more default tab titles will appear in the
			// "creating tab X" startup output — test fails here
			// without waiting for the kitty_effects assertion.
			stdout_excludes: [
				"Cockpit",
				"Driver",
				"Notebooks",
				"Dashboard",
			]
			kitty_effects: [
				{kind: "tab_created", title: "Custom"},
				{kind: "tab_created", title: "Worker"},
			]
			// Exact match: if the binary falls back to default AND
			// creates the overlay's tabs (a "both sources" bug), the
			// recorded effects would be a superset of expected — under
			// contains-semantics this passes. Exact-match catches it.
			// This is the load-bearing assertion for the 3.0 contract;
			// stdout_excludes above is complementary, not primary.
			kitty_effects_exact: true
		}

		help_summary: """
			Project-local override of the session layout:
			  # Drop kommander.cue in project root with custom tabs
			  kommander launch /path/to/project
			  → Binary reads <project>/kommander.cue for session overlay.
			  → Creates only the tabs the overlay describes; default
			    (Cockpit, Driver, Notebooks, Dashboard) is NOT applied
			    when overlay exists.
			  → stdout reports 'config: kommander.cue' to confirm the
			    overlay was found and loaded.
			"""
	},
]
