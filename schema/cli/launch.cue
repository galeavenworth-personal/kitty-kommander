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
			kitty_effects: [
				{kind: "tab_created", match: "Cockpit"},
				{kind: "tab_created", match: "Driver"},
				{kind: "tab_created", match: "Notebooks"},
				{kind: "tab_created", match: "Dashboard"},
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
]
