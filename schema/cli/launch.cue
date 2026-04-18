// Launch scenarios — `kommander launch <dir>`.
//
// Launch is the entry point. Every other subcommand assumes a session
// exists; these scenarios are what prove one can be brought up.
package cli

scenarios: launch: [
	{
		id:   "launch-basic"
		tags:      ["basic", "launch"]
		run_modes: ["mock"]

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
		tags:      ["error", "launch", "validation"]
		run_modes: ["mock"]

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
		tags:      ["common", "launch", "config"]
		run_modes: ["mock"]

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
	{
		id:   "launch-multi-window-tab"
		tags:      ["common", "launch", "config", "multi-window"]
		run_modes: ["mock"]

		story: """
			An operator defines a tab with several windows in their
			overlay kommander.cue — e.g. a 'Workstation' tab with
			Editor, Terminal, and Logs windows open at launch. When
			'kommander launch <dir>' runs against that config, the
			binary must create the tab AND every window — not just
			the first.

			Regression guard for uib.3.A: a naive LaunchTab
			implementation passes only windows[0].cmd to
			`kitten @ launch --type=tab` and stops. The second and
			third windows never materialize. Production code with
			that bug passed every prior scenario because no existing
			scenario used a multi-window tab.

			Effect shape mirrors kitten semantics: `--type=tab` with
			one initial cmd (recorded as tab_created), then
			additional windows via `--type=window --match
			title:<TabTitle>` (each recorded as window_created with
			target_tab set). A scenario that tests only presence of
			effects (not absence of extras) would pass a buggy
			implementation that also spawned windows in the wrong
			tab — kitty_effects_exact is load-bearing here.
			"""

		setup: files: {
			"kommander.cue": """
				package kommander

				session: tabs: [{
				    title: "Workstation"
				    windows: [
				        {title: "Editor", cmd: ["nvim"]},
				        {title: "Terminal", cmd: ["bash"]},
				        {title: "Logs", cmd: ["tail", "-f", "/var/log/syslog"]},
				    ]
				}]
				"""
		}

		invocation: "kommander launch /home/user/my-project"

		expected: {
			exit_code: 0
			stdout_contains: [
				"session: cockpit-my-project",
				"config: kommander.cue",
			]
			// First window (Editor) is the tab's initial window
			// under `kitten @ launch --type=tab`; it does not
			// produce a separate window_created effect (mock.go:53
			// elides nested initial windows from the effect stream
			// deliberately — matches real kitty behavior). Second
			// and third windows come in via LaunchWindow calls and
			// SHOULD record window_created with explicit target_tab.
			kitty_effects: [
				{kind: "tab_created", title: "Workstation"},
				{kind: "window_created", title: "Terminal", target_tab: "Workstation"},
				{kind: "window_created", title: "Logs", target_tab: "Workstation"},
			]
			// Exact match guards two failure modes:
			//   1. Implementation forgets to spawn windows[1:] at all
			//      — Terminal + Logs missing, recorded < expected.
			//   2. Implementation spawns windows[1:] in the wrong
			//      tab (wrong target_tab) or spawns an extra
			//      window_created for the initial Editor window —
			//      recorded has an entry that doesn't match the
			//      target_tab-scoped expectations, fails on
			//      len(recorded) != len(expected).
			kitty_effects_exact: true
		}

		help_summary: """
			Tab with multiple windows in the overlay:
			  # kommander.cue defines a tab with several windows
			  kommander launch /path/to/project
			  → Binary creates the tab with the first window as its
			    initial command, then spawns each additional window
			    into the same tab with explicit target.
			  → Subsequent windows carry window_created effects with
			    target_tab set; the initial window is folded into
			    tab_created (matching `kitten @ launch --type=tab`).
			"""
	},
]
