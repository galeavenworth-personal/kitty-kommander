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
	kitty_effects: [...#KittyEffect]

	// JSONPath assertions over `stdout` when the invocation emits
	// JSON (e.g. `kommander inspect`, `kommander doctor --json`).
	json_paths: [...#JSONPathCheck]
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
// Generator requires exactly one of {contains, equals, matches} to
// be set per check. A check with zero or multiple is a cue vet
// concern (enforced by the constraint below) — but CUE lacks a
// clean "exactly one" operator, so the generator verifies.
#JSONPathCheck: {
	path:      string
	contains?: string
	equals?:   string
	matches?:  string
}

// scenarios is the aggregate of every scenario across every
// subcommand file. CUE unifies partial definitions across files in
// this package, so each sibling file contributes one key (launch,
// doctor, reload, …) without needing imports.
scenarios: [string]: [...#Scenario]
