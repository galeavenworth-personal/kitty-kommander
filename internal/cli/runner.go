package cli

import (
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

	env := &Env{
		Args:       argsFromInvocation(sc.Invocation),
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

	assertKittyEffects(t, mock.Effects, sc.Expected.KittyEffects)
	assertJSONPaths(t, stdout, sc.Expected.JSONPaths)
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
func assertKittyEffects(t *testing.T, recorded []kitty.Effect, expected []scenario.KittyEffect) {
	t.Helper()

	// The no_change sentinel: exactly one element, kind == no_change.
	if len(expected) == 1 && expected[0].Kind == "no_change" {
		if len(recorded) > 0 {
			t.Errorf("expected no kitty effects; recorded %d: %+v", len(recorded), recorded)
		}
		return
	}

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
