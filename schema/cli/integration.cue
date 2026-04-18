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
				// Launch with a placeholder project dir. The ${BASENAME}
				// token is substituted at step-time by the integration
				// runner (runner_integration_test.go :: expandBasename)
				// with a per-test-invocation slug of shape
				// kommander-it-<pid>-<nanosec>. The runner rewrites
				// path-shaped args through the same materializeDirs
				// convention as mock scenarios AFTER substitution, so
				// the derived project-dir basename (and therefore
				// deriveSlug → session name → socket path) carries the
				// unique suffix. stdout_contains below uses the same
				// token so the literal assertion survives substitution.
				//
				// Per-test uniqueness fixes kitty-kommander-iez: a
				// literal basename (pre-this-change
				// "kommander-integration-test") collides under
				// `go test -tags=integration -count=N` or CI matrix
				// sharding because both runs pre-sweep and bind the
				// same /tmp/kitty-kommander-<literal> socket.
				invocation: "kommander launch /tmp/${BASENAME}"
				expected: {
					exit_code: 0
					stdout_contains: [
						"session: cockpit-${BASENAME}",
						"socket: unix:/tmp/kitty-kommander-${BASENAME}",
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
		// four-tab Option A layout verbatim. ONLY titles are asserted
		// here — cmd is deliberately absent. Option A's thesis is that
		// titles are the install-independent identity layer (claude's
		// OSC 0 spinner, euporie's self-rename, kitty's --title arg
		// winning the race — all title surface). Cmds via kitten @ ls
		// are resolved argv from the kernel and necessarily differ
		// from the user-facing CUE declaration: euporie shows as
		// `/usr/bin/python3 /home/.../euporie notebook` (shebang);
		// kommander-ui shows as `node --import=tsx ./bin/kommander-ui
		// --sidebar` (install.sh wrapper). Making the integration
		// scenario assert on resolved argv would couple the contract
		// to install.sh's wrapper choice and the operator's python/
		// node install location — the opposite of Option A. Field-
		// exact / no-coercion still holds: every field this fixture
		// DECLARES (title, windows-layout) must match live state
		// exactly; fields it doesn't declare (cmd) aren't asserted.
		// The argv0-vs-cmd architectural question is kitty-kommander-
		// 433 (P3 follow-on) — deliberately out of scope for 3.F.
		//
		// Cockpit's `windows: []` is the dynamic-tab marker. Real
		// kitty always creates a holding shell when a tab is
		// launched without an explicit window; production doctor
		// treats dynamic tabs' window set as operator-owned, not
		// CUE-declared. The runner mirrors this: empty `windows` in
		// a fixture means "don't assert window count or content for
		// this tab" (safe because a genuinely-missing Cockpit fails
		// the tab-count assertion one level up).
		expected: {
			final_kitty_state: {
				tabs: [
					{title: "Cockpit", windows: []},
					{title: "Driver", windows: [
						{title: "Driver"},
					]},
					{title: "Notebooks", windows: [
						{title: "Notebooks"},
					]},
					{title: "Dashboard", windows: [
						{title: "Sidebar"},
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
