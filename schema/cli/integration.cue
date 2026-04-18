// Integration scenarios — multi-step chains executed against a real
// kitty instance. uib.3.F ships the first: launch-then-doctor-clean.
//
// Lives under its own `scenarios.integration` bucket rather than
// mixing into `scenarios.launch` — CUE list unification at the same
// path index would require explicit concat + index alignment, which
// trades clarity for no benefit. Separate bucket keeps the scenario
// enumerable alongside its peers while letting the generator emit a
// dedicated integration_gen_test.go under the //go:build integration
// build tag.
//
// The integration tier skips cleanly when `kitty` is not on PATH
// (via scenariotest.RequireKitty), so operators without a local
// kitty install can still run `go test -tags=integration ./...`
// without false failures. CI tier three-way wiring (3.G) is out of
// scope for this file.
package cli

scenarios: integration: [
	{
		id:   "launch-then-doctor-clean"
		tags: ["integration", "launch", "doctor", "reload", "option-a-titled-layout"]

		// Real-kitty ONLY: this chain has no mock analogue because
		// the mock's state model doesn't participate in the launch
		// flow (the handler constructs tabs via LaunchTab, which
		// the mock records as effects but doesn't feed back into a
		// shared State for subsequent doctor/reload invocations in
		// a way that matches production). The mock harness runs
		// each scenario in its own fresh mock; the real-kitty
		// harness runs each STEP against the same live kitty.
		run_modes: ["real_kitty"]

		story: """
			Steel-thread integration for uib.3.F. Spawn a fresh kitty on
			an isolated socket via `kommander launch`, then prove the
			post-launch state holds weight under every other subcommand
			in turn. Doctor must report healthy (0 drift) against the
			CUE-declared titled layout per Option A — proving --title
			survives claude's OSC 0 spinner and euporie's default
			process-name relabeling in a real kitty, not just in the
			mock. Reload must be a no-op — proving the auditor's
			watchlist "reload immediately after launch" guard: the diff
			is empty, kitten @ ls before ≡ after, no duplicate spawns.

			Red-before-green at the stack level: this scenario is the
			first consumer of run_modes: real_kitty. Until the runner
			grows a real-mode branch, the generated test t.Fatal's with
			a specific "real_kitty mode not implemented" message under
			-tags=integration. The mock-path test suite (go test ./...)
			stays green — default run_modes: ["mock"] on every other
			scenario preserves the entire pre-3.F matrix.
			"""

		steps: [
			{
				// Launch with a placeholder project dir. The test
				// harness rewrites path-shaped args to a per-test
				// t.TempDir before invocation, same convention as
				// materializeDirs for mock scenarios. The basename
				// ("kommander-integration-test") is what deriveSlug
				// maps to the session name and socket path stdout
				// assertions rely on.
				invocation: "kommander launch /tmp/kommander-integration-test"
				expected: {
					exit_code: 0
					stdout_contains: [
						"session: cockpit-kommander-integration-test",
						"socket: unix:/tmp/kitty-kommander-kommander-integration-test",
					]
				}
			},
			{
				// Doctor asserts the launched session matches the
				// Option A titled layout: four tabs, every non-
				// dynamic window carrying its CUE-declared title.
				// The `healthy / 4/4 tabs / 0 drift` literals match
				// the summary line doctor emits on success; json
				// path `drift_count == 0` is the structured check.
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
			},
			{
				// Reload-after-launch must be a no-op. This is the
				// auditor's "no duplicate spawns" watchlist item:
				// a reload that silently re-launches the whole
				// session would pass every single-subcommand
				// scenario but balloon tab count here.
				//
				// `kitty_effects: [{kind: "no_change"}]` under real-
				// kitty mode asserts kitten @ ls before-reload
				// equals kitten @ ls after-reload. See types.cue
				// #Expected.kitty_effects docstring for the
				// real-kitty semantic.
				invocation: "kommander reload"
				expected: {
					exit_code: 0
					stdout_contains: ["reconciled", "0 operations"]
					kitty_effects: [{kind: "no_change"}]
				}
			},
		]

		// Post-chain assertion: kitten @ ls returns the canonical
		// four-tab Option A layout verbatim. Titles + cmds match
		// schema/session/default.cue exactly, so doctor would
		// report healthy again (redundant with step 2's assertion,
		// but this checks the SHAPE of the state, not just doctor's
		// interpretation of it — catches a broken doctor that would
		// silently report healthy on a wrong state).
		expected: {
			final_kitty_state: {
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
		}

		help_summary: """
			End-to-end integration flow:
			  kommander launch /path/to/project
			  kommander doctor     # healthy, 0 drift
			  kommander reload     # 0 operations (no-op on fresh session)
			  → Proves --title survives process OSC 0 escapes in a real
			    kitty and that reload is idempotent after launch.
			  → Local-only by default; `go test -tags=integration ./...`
			    spawns a real kitty. Skipped when `kitty` is not on PATH.
			"""
	},
]
