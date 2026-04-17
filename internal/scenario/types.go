// Package scenario mirrors the CUE scenario types from
// schema/cli/types.cue into Go. These are the IR the test generator
// walks over when it emits *_gen_test.go.
//
// Fields line up 1:1 with the CUE definitions. Comments on each field
// explain ONLY the Go-specific nuance (pointer vs slice, zero-value
// semantics); the semantic authority is the CUE schema.
package scenario

// Scenario is one CLI invocation specification, loaded from CUE.
type Scenario struct {
	ID          string   `json:"id"`
	Tags        []string `json:"tags"`
	Story       string   `json:"story"`
	Setup       Setup    `json:"setup"`
	Invocation  string   `json:"invocation"`
	Expected    Expected `json:"expected"`
	HelpSummary string   `json:"help_summary"`
	Golden      string   `json:"golden,omitempty"`
}

// Setup stages the world before the command runs.
type Setup struct {
	Env         map[string]string `json:"env"`
	Files       map[string]string `json:"files"`
	KittyState  *KittyFixture     `json:"kitty_state,omitempty"`
}

// KittyFixture is what the mock Controller's List() returns before
// the command runs. Matches schema/cli/types.cue #KittyFixture.
type KittyFixture struct {
	Tabs []KittyTab `json:"tabs"`
}

type KittyTab struct {
	Title   string        `json:"title"`
	Windows []KittyWindow `json:"windows"`
}

// KittyWindow mirrors #KittyWindow. Cmd is stored as StringOrList —
// the CUE schema accepts `cmd: string | [...string]` to let scenarios
// spell single-token commands ergonomically ("claude") without
// wrapping them in a one-element list. StringOrList.Argv() collapses
// both forms to a []string at use sites so the test generator and
// mock compare against a single shape.
type KittyWindow struct {
	Title string            `json:"title,omitempty"`
	Cmd   StringOrList      `json:"cmd"`
	Env   map[string]string `json:"env,omitempty"`
}

// Expected is the assertion bundle.
type Expected struct {
	ExitCode       int           `json:"exit_code"`
	StdoutContains []string      `json:"stdout_contains"`
	StdoutExcludes []string      `json:"stdout_excludes"`
	StderrContains []string      `json:"stderr_contains"`
	StderrExcludes []string      `json:"stderr_excludes"`
	KittyEffects   []KittyEffect `json:"kitty_effects"`
	// KittyEffectsExact: when true, assertKittyEffects must require
	// the recorded effect list to EXACTLY match KittyEffects (no extras).
	// When false (default), the recorded list may be a superset.
	// See schema/cli/types.cue #Expected.kitty_effects_exact.
	KittyEffectsExact bool       `json:"kitty_effects_exact"`
	JSONPaths      []JSONPath    `json:"json_paths"`
}

// KittyEffect matches the CUE discriminated shape. Only fields
// relevant to the `kind` are populated; the generator uses the
// field→kind mapping from schema/cli/types.cue.
type KittyEffect struct {
	Kind      string `json:"kind"`
	Title     string `json:"title,omitempty"`
	TargetTab string `json:"target_tab,omitempty"`
	Selector  string `json:"selector,omitempty"`
	Text      string `json:"text,omitempty"`
	Count     int    `json:"count"`
}

// JSONPath is one of the three #JSONPathCheck shapes, collapsed to a
// common Go struct with exactly one of Contains/Equals/Matches set.
type JSONPath struct {
	Path     string `json:"path"`
	Contains string `json:"contains,omitempty"`
	Equals   string `json:"equals,omitempty"`
	Matches  string `json:"matches,omitempty"`
}
