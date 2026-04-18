// Package cli holds the CUE scenario suite for the `kommander` Go binary.
//
// A scenario is the single source of truth for three downstream artifacts:
//   1. A Go table-driven test (`t.Run(scenario.id, ...)`)
//   2. A line in `kommander <subcommand> --help` (compiled from help_summary)
//   3. A chunk of operator-facing documentation
//
// The TDD cycle is: write scenario → `cue vet schema/` → generate test
// (red) → implement → test passes (green) → help text auto-compiles.
// The implementation never invents behavior the scenarios don't describe.
//
// This file defines the TYPES. Scenario bodies live in sibling files
// (launch.cue, doctor.cue, reload.cue, …) — CUE unifies them into a
// single `scenarios` struct at vet time.
package cli

import "github.com/galeavenworth-personal/kitty-kommander/schema/shared"

// Scenario is one end-to-end specification for a single CLI invocation.
//
// The primary consumer of `kommander --help` is an AI agent forming
// tool calls, not a human reading flags. help_summary is therefore
// written as a complete worked example the agent can pattern-match
// and adapt — not a terse description.
#Scenario: {
	// Lowercase-with-dashes, machine-readable. Becomes the Go sub-test
	// name, the golden-file basename, and the anchor in generated docs.
	id: string & =~"^[a-z][a-z0-9-]*$"

	// Coarse classification. Conventions: "basic" (first scenario per
	// subcommand), "common" (frequent but non-trivial), "error"
	// (non-zero exit), "edge-case", "validation".
	tags: [...string]

	// The user story the scenario instantiates — what the user wants
	// and why. This IS the UAT case; test readers and agents both
	// lean on this to decide whether the scenario is the right fit.
	story: string

	// Preconditions for the scenario. Default {} = nothing set up.
	setup: #Setup | *{}

	// The exact invocation, copy-pasteable. Matches what goes in the
	// generated Go test as the command under test.
	//
	// Default "" exists only so `steps`-shaped scenarios (see below)
	// can omit `invocation`; every pre-3.F scenario sets this
	// explicitly. The loader rejects scenarios that leave both
	// `invocation` and `steps` empty, and scenarios that set both.
	invocation: string | *""

	// Multi-step scenarios, opt-in. When non-empty, the runner
	// executes each step's invocation in order against a shared
	// controller (and shared real-kitty instance under run_modes:
	// "real_kitty"), applying each step's `expected` after that
	// step's invocation returns. The scenario's TOP-LEVEL `expected`
	// still applies after all steps complete — use it for
	// post-chain assertions like `final_kitty_state`.
	//
	// `steps` and top-level `invocation` are MUTUALLY EXCLUSIVE: a
	// scenario sets one or the other. Enforced at load time in
	// internal/scenario/load.go, not in CUE — a clean disjunction
	// here would require bifurcating #Scenario and updating every
	// existing file, so the constraint lives in the loader instead.
	// Trade-off: `cue vet` passes a misuse; `go generate
	// ./internal/cli/` and `scenario.Load` catch it with a clear
	// error.
	//
	// First consumer: schema/cli/integration.cue's
	// launch-then-doctor-clean scenario (uib.3.F). The chain
	// launch → doctor → reload IS the assertion — splitting it
	// into three scenarios would decouple premise from assertion
	// and silently break the auditor's "reload is noop after launch"
	// guard.
	steps?: [...#Step]

	// Assertions. Generated tests check every non-empty field.
	expected: #Expected

	// Trimmed help excerpt — what `kommander <subcmd> --help` shows
	// for this scenario. Must be a complete worked example an AI
	// agent can adapt.
	help_summary: string

	// Optional golden file for exact output comparison. Path is
	// relative to `testdata/golden/` (Go convention).
	golden?: string

	// Execution modes the scenario runs in. Default ["mock"] covers
	// every pre-3.F scenario: the generated test builds a kitty.Mock,
	// calls the handler in-process, asserts on recorded effects.
	// Opting into ["real_kitty"] (or both) tells the generator to
	// also emit a real-kitty test variant that spawns a fresh kitty
	// process on an isolated socket, binds a production KittenExec
	// controller, runs the scenario, and asserts final state via
	// `expected.final_kitty_state`. Real-kitty tests carry the
	// //go:build integration tag so `go test ./...` stays mock-only
	// by default; `go test -tags=integration ./...` adds the real
	// pass.
	//
	// Naming: "run_modes" (controller execution axis) is deliberately
	// distinct from packages/ui/schema's "render_mode" (React render
	// path axis) — two orthogonal mode concepts, distinct names to
	// prevent cross-package confusion.
	run_modes: [...("mock" | "real_kitty")] | *["mock"]
}

// Step is one invocation in a multi-step scenario. Fields mirror the
// subset of #Scenario relevant to a single exec: invocation + its
// own expected block. setup is scenario-level (not per-step) — stage
// world state once, chain invocations against it.
#Step: {
	// The exact invocation for this step. Same shape as #Scenario.invocation.
	invocation: string

	// Assertions for this step. Post-step: stdout/stderr/exit_code/
	// json_paths/kitty_effects all apply to THIS invocation's output.
	// `final_kitty_state` is scenario-level only — put it on the
	// scenario's top-level `expected`, not per-step.
	expected: #Expected
}

// Setup bundles every way a scenario stages the world.
#Setup: {
	// Env vars injected into the command's environment.
	env: {[string]: string} | *{}

	// Files created on disk before the command runs. Key is a path
	// relative to a tmp dir allocated per test; value is file content.
	files: {[string]: string} | *{}

	// Beads fixture — populated into a sandbox .beads/ db before the
	// command runs, so scenarios can assert against `bd ready`
	// output or similar without depending on real repo state.
	beads_state?: shared.#BeadsFixture

	// Kitty state — desired snapshot of what `kitty @ ls` should
	// return. Injected through the mock KittyController for scenario
	// tests. In real execution this is compared against live state.
	kitty_state?: #KittyFixture
}

// KittyFixture describes exactly what `kitty @ ls` returns — no more,
// no less. This is the ACTUAL-STATE side of the doctor diff.
//
// Intentionally NOT a superset of the CUE session schema: the session
// schema (see STACK-v2.md Layer 2) carries `ink?: bool` and
// `location?: "vsplit" | …` fields that are kommander's internal
// directives for HOW to spawn, not runtime attributes kitty retains.
// Once kitty has launched the window, `kitty @ ls` returns title,
// cmd, env, cwd — it does not echo back whether the window was
// intended to be an Ink process or spawned with --location=vsplit.
//
// Consequence: a `doctor` scenario's `setup.kitty_state` can assert
// what kitty SHOWS (tabs, titles, running commands), but cannot
// assert "the desired session wanted this to be an Ink window."
// Drift on ink/location is caught by the session-schema comparison
// step inside the doctor command itself (implementation concern,
// not scenario concern) — not by this fixture.
#KittyFixture: {
	tabs: [...#KittyTab]
}

#KittyTab: {
	title:   string
	layout?: "tall" | "splits" | "stack"
	windows: [...#KittyWindow]
}

// KittyWindow mirrors the subset of `kitty @ ls` window objects that
// scenarios care about. Deliberately does NOT include `ink` or
// `location` — see #KittyFixture doc.
#KittyWindow: {
	title?: string
	cmd:    string | [...string]
	env?:   {[string]: string}
}

// Expected is the structured assertion block. Every non-empty field
// becomes a check in the generated Go test.
#Expected: {
	// Process exit code. 0 = success. Non-zero means the scenario
	// deliberately tests an error path.
	exit_code: int | *0

	// Substrings that must appear in stdout (order-insensitive).
	stdout_contains: [...string]
	// Substrings that must NOT appear in stdout.
	stdout_excludes: [...string]
	// Substrings that must appear in stderr.
	stderr_contains: [...string]
	// Substrings that must NOT appear in stderr.
	stderr_excludes: [...string]

	// Effects the command must have produced on the kitty instance,
	// as recorded by the mock KittyController (or observed live
	// via `kitty @ ls` in an end-to-end test).
	//
	// Real-kitty mode (run_modes: "real_kitty") has no effect
	// recorder — the production KittenExec shells out to `kitten @`
	// and the kitty instance is the ground truth. Under real-kitty
	// mode, the ONLY kitty_effects value honored today is
	// [{kind: "no_change"}], which asserts the pre-step and
	// post-step `kitten @ ls` snapshots are equal (no tabs or
	// windows created, closed, or renamed). Other effect kinds
	// on real-kitty steps are silently ignored in 3.F — if later
	// integration scenarios need per-step tab_created / window_*
	// assertions, bolt on an inferred-effect diff; don't fake the
	// mock.Effects channel.
	kitty_effects: [...#KittyEffect]

	// When true, the recorded effect list must EXACTLY equal
	// kitty_effects (same length, same elements — ordering still
	// unenforced, per assertKittyEffects convention). When false
	// (default), the recorded list may be a superset of expected —
	// presence-of-expected is checked, absence-of-unexpected is not.
	//
	// Use kitty_effects_exact when the scenario's point is "these
	// effects and no others" — e.g. proving a fallback path does NOT
	// also fire alongside the intended path. The default of false
	// preserves contains-semantics for scenarios (like launch-basic,
	// doctor-healthy) where extra effects would be a different bug
	// caught by other scenarios.
	kitty_effects_exact: bool | *false

	// JSONPath assertions over `stdout` when the invocation emits
	// JSON (e.g. `kommander inspect`, `kommander doctor --json`).
	json_paths: [...#JSONPathCheck]

	// Final kitty state, asserted ONCE at end of scenario against
	// `kitten @ ls`. Scenario-level assertion only — put this on
	// the scenario's top-level `expected`, never on a #Step's
	// expected (the runner reads only the top-level final state).
	//
	// Reuses #KittyFixture — the same shape that scenarios use as
	// setup input for doctor/reload tests is semantically identical
	// to the assertion side in real-kitty mode (what the production
	// stack produced). Under run_modes: "mock", this field is
	// ignored by the runner — the mock already staged its state via
	// setup.kitty_state and assertions flow through kitty_effects.
	final_kitty_state?: #KittyFixture
}

// KittyEffect is one observable change the command made (or should
// have made) to the kitty instance. The mock KittyController records
// effects as it receives calls; the generated Go test then compares
// the recorded stream to the scenario's `expected.kitty_effects`.
//
// Each kind uses a different subset of fields. A single overloaded
// `match` would collapse distinct semantics (text payload vs
// selector vs created title) and permit false-passes where the test
// records "something named X" while the command did the right thing
// to the wrong window. Explicit fields per concern:
//
//   tab_created     → title (the tab title; must equal the
//                     `--tab-title` arg passed to `kitten @ launch`)
//   tab_focused     → selector (the `--match` arg passed to
//                     `kitten @ focus-tab`)
//   window_created  → title (new window's title) + target_tab (which
//                     tab the window was created in)
//   window_closed   → selector (the `--match` arg passed to
//                     `kitten @ close-window`)
//   text_sent       → selector (who received, e.g. "title:builder") +
//                     text (the exact string sent to send-text's stdin)
//   no_change       → no fields used; this asserts the command did
//                     NOT call the mock for any kitty operation
//
// The mock enforces the field→kind mapping; the generator reads
// these comments to produce targeted assertions.
#KittyEffect: {
	kind: "tab_created" | "window_created" | "window_closed" |
		"text_sent" | "tab_focused" | "no_change"

	// For tab_created: the tab title (equals `--tab-title` arg).
	// For window_created / window_closed: the window title.
	// Unused for text_sent, tab_focused, no_change.
	title?: string

	// For window_created / window_closed: the tab the window was
	// created or closed in. Scenarios MUST set this for window_*
	// kinds — "window created somewhere" is a false-pass magnet
	// (e.g. spawning the Sidebar window in the Cockpit tab instead
	// of the Dashboard tab).
	target_tab?: string

	// The `--match` selector the command passed to `kitten @`.
	// For tab_focused: `--match title:Dashboard`
	// For window_closed: `--match title:builder`
	// For text_sent: who received the text (`--match title:builder`)
	// Unused for tab_created, window_created (their creation
	// invocation does not take --match), and no_change.
	selector?: string

	// For text_sent: the exact string piped to send-text's stdin.
	// Unused for every other kind.
	text?: string

	// Number of times this effect should have been recorded. Default
	// 1. Higher values are rare but valid (e.g. multiple windows
	// created in one launch).
	count: int | *1
}

// JSONPathCheck asserts a JSON-emitting invocation produces the
// expected shape. `path` is a JSONPath expression (e.g.
// `.tabs[0].title`, `.drift[0].kind`). Exactly one match mode:
//
//   contains — substring match against stringified value. Tolerant
//              but LOOSE: `"0"` is contained in `"10"` and `"20"`.
//              Use for enum-like string values where partial match
//              is actually what you want.
//
//   equals   — stringified-value equality. Strict. Use for integers
//              and for exact enum values where substring would admit
//              false positives.
//
//   matches  — regex match against stringified value. Use for
//              structured-but-variable values (timestamps, hashes).
//
// Vet-time enforcement (CUE v0.16.0, concrete-field usage — which is
// how scenarios actually consume this type):
//   {path, <one mode>}      → ok
//   {path, <two modes>}     → vet error: field not allowed (empty disjunction)
//   {path, <mode>, <typo>}  → vet error: field not allowed (empty disjunction)
//   {path} alone            → vet error: some instances are incomplete
//
// The disjunction is fully load-bearing for concrete fields: every
// wrong shape is caught by `cue vet` without flags. The generator
// does not need to re-verify mode exclusivity.
//
// Caveat, for completeness: under HIDDEN fields (`_foo: #JSONPathCheck
// & {path: ".x"}`), CUE permits the value to remain abstract and vet
// passes. Scenarios do not use hidden fields for json_paths entries,
// so this is a theoretical rather than practical gap. If a future
// consumer needs concreteness under hidden fields too, add `cue vet -c`
// (or the equivalent API flag) to the CI step.
#JSONPathCheck: close({path: string, contains: string}) |
	close({path: string, equals: string}) |
	close({path: string, matches: string})

// scenarios is the aggregate of every scenario across every
// subcommand file. CUE unifies partial definitions across files in
// this package, so each sibling file contributes one key (launch,
// doctor, reload, …) without needing imports.
scenarios: [string]: [...#Scenario]
