package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// RunScenario is the runtime harness the generated tests call. It
// builds an Env from sc.Setup, invokes handler, then asserts every
// expected field.
//
// Order of assertions: exit code first (fail fast on wrong path),
// then stdout / stderr substring checks, then kitty effects, then
// JSON path checks. Each assertion uses t.Errorf so one scenario
// reports every failing claim in a single run, rather than stopping
// at the first.
func RunScenario(t *testing.T, handler Handler, sc scenario.Scenario) {
	t.Helper()

	mock := kitty.NewMock()
	if sc.Setup.KittyState != nil {
		mock.SetState(kittyStateFromFixture(*sc.Setup.KittyState))
	}

	args := argsFromInvocation(sc.Invocation)
	// materializeDirs creates real temp dirs for path-shaped args
	// whose basename is baked into the scenario's expected output
	// (e.g. launch-basic expects "cockpit-my-app" because the
	// invocation uses "/home/user/my-app"). The substitution
	// preserves the basename so slug-derivation still produces the
	// expected output.
	args = materializeDirs(t, args)

	// Stage Setup.Files inside the first materialized project dir.
	// Scenarios that ship an overlay (e.g. cue-config-driven-layout
	// dropping kommander.cue into the project root) need those files
	// on disk before the handler runs — otherwise the binary's loader
	// can't find them and the test goes red for the wrong reason.
	// The convention: files map relative-path → contents, all paths
	// resolve under the first path-shaped arg. Error-path scenarios
	// (/nonexistent/*) don't carry Setup.Files, so the absence of a
	// materialized dir for those is not a concern.
	materializeFiles(t, args, sc.Setup.Files)

	env := &Env{
		Args:       args,
		Controller: mock,
	}

	exitCode, stdout, stderr := handler(env)

	if exitCode != sc.Expected.ExitCode {
		t.Errorf("exit code: got %d, want %d\nstdout: %s\nstderr: %s",
			exitCode, sc.Expected.ExitCode, stdout, stderr)
	}

	for _, want := range sc.Expected.StdoutContains {
		if !strings.Contains(stdout, want) {
			t.Errorf("stdout missing %q\nstdout was: %s", want, stdout)
		}
	}
	for _, nope := range sc.Expected.StdoutExcludes {
		if strings.Contains(stdout, nope) {
			t.Errorf("stdout unexpectedly contains %q\nstdout: %s", nope, stdout)
		}
	}
	for _, want := range sc.Expected.StderrContains {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr missing %q\nstderr was: %s", want, stderr)
		}
	}
	for _, nope := range sc.Expected.StderrExcludes {
		if strings.Contains(stderr, nope) {
			t.Errorf("stderr unexpectedly contains %q\nstderr: %s", nope, stderr)
		}
	}

	assertKittyEffects(t, mock.Effects, sc.Expected.KittyEffects, sc.Expected.KittyEffectsExact)
	assertJSONPaths(t, stdout, sc.Expected.JSONPaths)
}

// materializeFiles writes Setup.Files into the first path-shaped arg's
// directory. The path-shaped arg is the one materializeDirs rewrote —
// it's both the tmp dir on disk AND the value the handler receives as
// its positional arg, so the binary and the on-disk overlay agree on
// the same directory.
//
// Scenarios SHOULD keep relative paths simple (e.g. "kommander.cue",
// not "nested/path/kommander.cue") — nested dirs are supported via
// MkdirAll but discouraged for readability. Empty files map is a no-op.
func materializeFiles(t *testing.T, args []string, files map[string]string) {
	t.Helper()
	if len(files) == 0 {
		return
	}
	projectDir := ""
	for _, a := range args {
		if strings.HasPrefix(a, "/") && !strings.HasPrefix(a, "/nonexistent") {
			projectDir = a
			break
		}
	}
	if projectDir == "" {
		t.Fatalf("materializeFiles: scenario has Setup.Files but no path-shaped arg to host them: %+v", args)
	}
	for rel, content := range files {
		dst := filepath.Join(projectDir, rel)
		if dir := filepath.Dir(dst); dir != projectDir {
			if err := os.MkdirAll(dir, 0o755); err != nil {
				t.Fatalf("materializeFiles: mkdir %s: %v", dir, err)
			}
		}
		if err := os.WriteFile(dst, []byte(content), 0o644); err != nil {
			t.Fatalf("materializeFiles: write %s: %v", dst, err)
		}
	}
}

// materializeDirs rewrites path-shaped positional args so the test
// can exercise the happy path. The rule:
//
//	arg starts with "/"
//	AND arg does NOT start with "/nonexistent"
//	    (the conventional prefix for error-path scenarios)
//	→ create a tmp dir at <t.TempDir>/<basename(arg)>, substitute.
//
// Scenarios that deliberately assert on a missing path MUST use
// /nonexistent/* so the substitution is skipped. `launch-missing-dir`
// follows this convention.
//
// This keeps the slug (which derives from basename) stable across
// the substitution — "launch /home/user/my-app" gets rewritten to
// "launch /tmp/xxx/my-app", and deriveSlug still returns "my-app".
func materializeDirs(t *testing.T, args []string) []string {
	t.Helper()
	out := make([]string, len(args))
	for i, a := range args {
		if strings.HasPrefix(a, "/") && !strings.HasPrefix(a, "/nonexistent") {
			tmp := t.TempDir()
			real := filepath.Join(tmp, filepath.Base(a))
			if err := os.MkdirAll(real, 0o755); err != nil {
				t.Fatalf("materializeDirs: mkdir %s: %v", real, err)
			}
			out[i] = real
		} else {
			out[i] = a
		}
	}
	return out
}

// argsFromInvocation extracts the argv after the subcommand word
// from the scenario's `invocation` string. The scenario writes the
// full command line (e.g. "kommander launch /home/user/my-app");
// the handler wants just the args after the subcommand.
func argsFromInvocation(inv string) []string {
	parts := strings.Fields(inv)
	// Expect "kommander <subcmd> [args...]"
	if len(parts) < 2 {
		return nil
	}
	return parts[2:]
}

// kittyStateFromFixture converts the CUE fixture shape to the
// runtime state shape. These are deliberately separate types so the
// fixture (input to tests) and the runtime state (what the mock
// tracks internally) can evolve independently.
func kittyStateFromFixture(f scenario.KittyFixture) kitty.State {
	s := kitty.State{}
	for _, tab := range f.Tabs {
		t := kitty.TabState{Title: tab.Title}
		for _, w := range tab.Windows {
			t.Windows = append(t.Windows, kitty.WindowState{
				Title: w.Title,
				Cmd:   w.Cmd.Argv(),
				Env:   w.Env,
			})
		}
		s.Tabs = append(s.Tabs, t)
	}
	return s
}

// assertKittyEffects compares recorded mock calls to expected effects.
//
// The `no_change` sentinel is handled specially: a single-element
// expected list of {kind: "no_change"} asserts the recorded list is
// empty. For every other case, we require an exact-count match per
// expected effect — ordering is not enforced, since kitty operations
// within a single subcommand invocation are often dispatched in
// parallel or in an order the scenario doesn't care about.
//
// When exact is true (from the scenario's kitty_effects_exact field),
// the recorded list's total length must equal the sum of expected
// counts — no extras. This is the auditor-requested guard against
// vacuous passes where a scenario asserts "Custom was created" but
// the binary also created all four default tabs behind the assertion.
// When exact is false (default), recorded may be a superset of expected.
func assertKittyEffects(t *testing.T, recorded []kitty.Effect, expected []scenario.KittyEffect, exact bool) {
	t.Helper()

	// The no_change sentinel: exactly one element, kind == no_change.
	// Absence-of-effect IS strict by definition; the `exact` flag is
	// ignored for this sentinel (would be a redundant ask).
	if len(expected) == 1 && expected[0].Kind == "no_change" {
		if len(recorded) > 0 {
			t.Errorf("expected no kitty effects; recorded %d: %+v", len(recorded), recorded)
		}
		return
	}

	totalWant := 0
	for _, want := range expected {
		if want.Kind == "no_change" {
			t.Errorf("no_change effect can only appear as the sole effect in a scenario")
			continue
		}
		want := want // capture
		wantCount := want.Count
		if wantCount == 0 {
			wantCount = 1
		}
		totalWant += wantCount

		got := 0
		for _, rec := range recorded {
			if effectMatches(rec, want) {
				got++
			}
		}
		if got != wantCount {
			t.Errorf("kitty effect %+v: got %d match(es), want %d.\nrecorded: %+v",
				want, got, wantCount, recorded)
		}
	}

	if exact && len(recorded) != totalWant {
		t.Errorf("kitty_effects_exact: recorded %d effect(s), expected exactly %d.\nrecorded: %+v\nexpected: %+v",
			len(recorded), totalWant, recorded, expected)
	}
}

// effectMatches compares a recorded mock call to an expected effect.
// Only the fields appropriate to the `kind` are compared:
//
//	tab_created    → Kind, Title
//	window_created → Kind, Title, TargetTab
//	window_closed  → Kind, Selector
//	text_sent      → Kind, Selector, Text
//	tab_focused    → Kind, Selector
//
// Anything else is a generator bug (the CUE schema constrains kind
// to this set) — but we still compare Kind first so the failure
// mode is "wrong kind" rather than "mysterious mismatch."
func effectMatches(rec kitty.Effect, want scenario.KittyEffect) bool {
	if rec.Kind != want.Kind {
		return false
	}
	switch want.Kind {
	case "tab_created":
		return rec.Title == want.Title
	case "window_created":
		return rec.Title == want.Title && rec.TargetTab == want.TargetTab
	case "window_closed":
		return rec.Selector == want.Selector
	case "text_sent":
		return rec.Selector == want.Selector && rec.Text == want.Text
	case "tab_focused":
		return rec.Selector == want.Selector
	default:
		return false
	}
}
