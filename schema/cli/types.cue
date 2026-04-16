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
	invocation: string

	// Assertions. Generated tests check every non-empty field.
	expected: #Expected

	// Trimmed help excerpt — what `kommander <subcmd> --help` shows
	// for this scenario. Must be a complete worked example an AI
	// agent can adapt.
	help_summary: string

	// Optional golden file for exact output comparison. Path is
	// relative to `testdata/golden/` (Go convention).
	golden?: string
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

// KittyFixture describes a snapshot of what `kitty @ ls` would return.
// The mock KittyController in tests returns this verbatim; the doctor
// command compares this (as desired state from CUE) against live state.
#KittyFixture: {
	tabs: [...#KittyTab]
}

#KittyTab: {
	title:   string
	layout?: "tall" | "splits" | "stack"
	windows: [...#KittyWindow]
}

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
	kitty_effects: [...#KittyEffect]

	// JSONPath assertions over `stdout` when the invocation emits
	// JSON (e.g. `kommander inspect`, `kommander doctor --json`).
	json_paths: [...#JSONPathCheck]
}

// KittyEffect is one observable change the command made (or should
// have made) to the kitty instance. `no_change` is explicit — it lets
// an error scenario state "this must not touch kitty", rather than
// relying on the absence of other kinds.
#KittyEffect: {
	kind: "tab_created" | "window_created" | "window_closed" |
		"text_sent" | "tab_focused" | "no_change"

	// Tab title, window title, or text content to match. For
	// `no_change` this field is meaningless and should be omitted.
	match?: string

	// Number of times this effect should have been recorded. Default
	// 1. Higher values are rare but valid (e.g. multiple windows
	// created in one launch).
	count: int | *1
}

// JSONPathCheck asserts a JSON-emitting invocation produces the
// expected shape. `path` is a JSONPath expression (e.g. `.tabs[0].title`,
// `.drift[0].kind`). `contains` is a substring match against the
// value at that path — tolerant to surrounding formatting.
#JSONPathCheck: {
	path:     string
	contains: string
}

// scenarios is the aggregate of every scenario across every
// subcommand file. CUE unifies partial definitions across files in
// this package, so each sibling file contributes one key (launch,
// doctor, reload, …) without needing imports.
scenarios: [string]: [...#Scenario]
