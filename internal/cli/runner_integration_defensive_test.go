//go:build integration

package cli

import (
	"strings"
	"testing"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// TestDiffLsSnapshotsDetectsPIDChurn is the defensive unit test for
// the real-kitty no_change contract. A destructive reload that closes
// and respawns every window produces identical titles and cmds (same
// session spec) but fresh PIDs. The no_change assertion must fail in
// that case — otherwise the auditor's "reload-immediately-after-
// launch is idempotent" guard is vacuous.
//
// This test constructs two snapshots that agree on every field except
// PID and confirms diffLsSnapshots returns a non-empty diff mentioning
// PID churn. Without this test, a refactor that drops PID from the
// comparison (e.g. during a "simplify the equality check" cleanup)
// would pass every integration test on a quiescent kitty — because
// fresh launches on a healthy machine also have stable PIDs — and
// regress only on the specific destructive-reload scenario we're
// trying to catch.
func TestDiffLsSnapshotsDetectsPIDChurn(t *testing.T) {
	pre := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"claude"}, PID: 100},
		}},
	}}
	post := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"claude"}, PID: 200},
		}},
	}}
	diff := diffLsSnapshots(pre, post)
	if diff == "" {
		t.Fatal("expected non-empty diff for PID churn; got empty (PID equality is not being checked)")
	}
	if !strings.Contains(diff, "PID churn") {
		t.Errorf("diff message does not mention PID churn: %s", diff)
	}
	if !strings.Contains(diff, "100") || !strings.Contains(diff, "200") {
		t.Errorf("diff message does not include pre/post PIDs 100/200: %s", diff)
	}
}

// TestDiffLsSnapshotsQuietOnMatch is the companion: when every field
// including PID matches, diffLsSnapshots must return "". Pinning the
// green side of the contract stops a future refactor from flipping
// the logic polarity.
func TestDiffLsSnapshotsQuietOnMatch(t *testing.T) {
	pre := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"claude"}, PID: 100},
		}},
	}}
	post := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"claude"}, PID: 100},
		}},
	}}
	if diff := diffLsSnapshots(pre, post); diff != "" {
		t.Errorf("expected empty diff for identical snapshots; got: %s", diff)
	}
}

// TestDiffFinalStateEmptyTitleRejected pins the field-exact /
// no-coercion contract: a fixture that declares a window with empty
// title is a bug in the fixture, not a "match anything" shorthand.
// The runner MUST report this as a failure rather than silently
// passing on whatever the live side has.
//
// Why this matters: empty-title in the CUE fixture is unprintable and
// easy to introduce accidentally during a fixture refactor (e.g. a
// copy-paste that forgets to populate title: on a new window). Without
// this guard, an "assertion" on an empty-title window is no assertion
// at all — every live window would trivially match, defeating the
// Option A titled-layout contract that 3.F exists to pin.
func TestDiffFinalStateEmptyTitleRejected(t *testing.T) {
	got := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"claude"}, PID: 100},
		}},
	}}
	want := &scenario.KittyFixture{Tabs: []scenario.KittyTab{
		{Title: "Driver", Windows: []scenario.KittyWindow{
			// Deliberate fixture bug: empty title.
			{Title: "", Cmd: scenario.StringOrList(nil)},
		}},
	}}
	errs := diffFinalState(got, want)
	if len(errs) == 0 {
		t.Fatal("expected diffFinalState to reject empty-title fixture window; got no errors")
	}
	joined := strings.Join(errs, "\n")
	if !strings.Contains(joined, "empty title") {
		t.Errorf("error message does not mention 'empty title': %s", joined)
	}
}

// TestDiffFinalStateAbsentFieldNotAsserted pins the absent-vs-
// declared distinction: when a fixture omits cmd (len(Cmd.Argv()) ==
// 0), the live side's cmd is NOT asserted. This is the Option A
// contract integration.cue relies on — titles are install-independent
// identity; cmd is install-dependent (python shebang expansion,
// kommander-ui wrapper) so the scenario deliberately leaves it
// unspecified.
//
// Without this test, a refactor that changed the "absent = don't
// assert" rule to "absent = must also be empty" would silently regress
// the only real-kitty integration scenario — live cmd is never empty,
// so the assertion would ALWAYS fail. The CUE fixture would need a
// bulk rewrite to paper over the bug.
func TestDiffFinalStateAbsentFieldNotAsserted(t *testing.T) {
	got := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Driver", Windows: []kitty.WindowState{
			{Title: "Driver", Cmd: []string{"/usr/bin/claude", "--foo"}, PID: 100},
		}},
	}}
	want := &scenario.KittyFixture{Tabs: []scenario.KittyTab{
		{Title: "Driver", Windows: []scenario.KittyWindow{
			// Fixture omits cmd — should not assert.
			{Title: "Driver", Cmd: scenario.StringOrList(nil)},
		}},
	}}
	if errs := diffFinalState(got, want); len(errs) > 0 {
		t.Errorf("diffFinalState unexpectedly failed when fixture omits cmd: %v", errs)
	}
}

// TestDiffFinalStateDynamicTabSkipsWindows pins the dynamic-tab
// semantic: a fixture tab with `windows: []` means "don't assert
// window count or content for this tab." Cockpit is the sole such tab
// in the steel-thread scenario (real kitty always creates a holding
// shell inside the Cockpit tab at spawn time, which is operator-owned
// per design). Without this skip, the runner would complain that
// Cockpit has 1 window but the fixture expected 0 — a false failure
// on a correct live state.
func TestDiffFinalStateDynamicTabSkipsWindows(t *testing.T) {
	got := &kitty.State{Tabs: []kitty.TabState{
		{Title: "Cockpit", Windows: []kitty.WindowState{
			{Title: "bash", Cmd: []string{"/bin/bash"}, PID: 100},
		}},
	}}
	want := &scenario.KittyFixture{Tabs: []scenario.KittyTab{
		// Dynamic-tab marker.
		{Title: "Cockpit", Windows: []scenario.KittyWindow{}},
	}}
	if errs := diffFinalState(got, want); len(errs) > 0 {
		t.Errorf("diffFinalState unexpectedly failed for dynamic tab (windows: []): %v", errs)
	}
}

// TestExpectsNoChangeOnSingleNoChange pins the true branch of the
// predicate that gates the real-kitty no_change assertion path. A step
// with exactly one kitty_effects entry of kind "no_change" MUST cause
// the runner to snapshot pre-state and diff against post-state; any
// weakening of this predicate (e.g. requiring len == 0, or keying on a
// different field) would silently disable the destructive-reload guard
// for every integration scenario that uses it.
func TestExpectsNoChangeOnSingleNoChange(t *testing.T) {
	e := scenario.Expected{KittyEffects: []scenario.KittyEffect{{Kind: "no_change"}}}
	if !expectsNoChange(e) {
		t.Fatal("expectsNoChange returned false for [{Kind:\"no_change\"}]; no_change assertion path disabled")
	}
}

// TestExpectsNoChangeFalseOnEmpty pins the false branch for the empty-
// slice case. The reload step's Expected is the only place 3.F honors
// kitty_effects; scenarios that don't declare kitty_effects must not
// trip the no_change machinery (it would snapshot pre-state needlessly
// and fail on any step that legitimately mutates session state).
func TestExpectsNoChangeFalseOnEmpty(t *testing.T) {
	e := scenario.Expected{KittyEffects: nil}
	if expectsNoChange(e) {
		t.Fatal("expectsNoChange returned true for empty KittyEffects; no_change guard is too eager")
	}
}

// TestExpectsNoChangeFalseOnMixed pins the false branch for the multi-
// entry case. types.cue #Expected.kitty_effects docstring reserves the
// no_change kind as an exclusive marker — mixing it with tab_created or
// window_closed is a fixture bug, not a partial-constraint. The
// predicate must reject the mix rather than honoring the no_change half
// and ignoring the rest.
func TestExpectsNoChangeFalseOnMixed(t *testing.T) {
	e := scenario.Expected{KittyEffects: []scenario.KittyEffect{
		{Kind: "no_change"},
		{Kind: "tab_created"},
	}}
	if expectsNoChange(e) {
		t.Fatal("expectsNoChange returned true for mixed [no_change, tab_created]; non-exclusive marker silently ignored")
	}
}

// TestUniqueIntegrationBasenameDistinct pins kitty-kommander-iez's
// load-bearing invariant: two successive calls to
// uniqueIntegrationBasename MUST return different slugs. This is what
// lets `go test -tags=integration -count=N` (and CI matrix shards)
// derive non-colliding /tmp/kitty-kommander-<basename> sockets.
//
// Without this test, a refactor that stripped the nanosecond clock
// (e.g. "keep only pid for stability") would silently reintroduce the
// race: every call within the same pid returns the same basename, two
// concurrent go test invocations from one CI worker collide on
// /tmp/kitty-kommander-kommander-it-<pid>, first invocation's pre-
// sweep rips the socket out from under the second.
//
// Tamper-then-revert evidence: replacing the format string with just
// "kommander-it-%d" (pid-only) makes both calls return the same slug;
// this test reds with "uniqueIntegrationBasename returned identical
// slugs". Reverted to pid+nanosec; test greens.
func TestUniqueIntegrationBasenameDistinct(t *testing.T) {
	a := uniqueIntegrationBasename()
	b := uniqueIntegrationBasename()
	if a == b {
		t.Fatalf("uniqueIntegrationBasename returned identical slugs on back-to-back calls: %q (race mitigation for iez would silently collide on parallel invocations)", a)
	}
	// Both must be slug-safe so deriveSlug(basename) == basename and
	// the kommander-derived socket path is predictable from our side.
	for _, s := range []string{a, b} {
		for _, r := range s {
			valid := (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-'
			if !valid {
				t.Errorf("basename %q contains non-slug-safe rune %q; deriveSlug will mangle it", s, r)
			}
		}
		if !strings.HasPrefix(s, "kommander-it-") {
			t.Errorf("basename %q missing kommander-it- prefix (readability / greppability)", s)
		}
	}
}

// TestExpandBasenameSubstitutes pins the substitution contract. Every
// ${BASENAME} token in the input string is replaced with the supplied
// basename; other text is untouched. The runner calls this on step
// Invocation and on every string in Expected.Stdout/Stderr before
// running a step — without substitution, the scenario's literal
// ${BASENAME} string would fail the stdout-contains check against
// kommander's actual per-run stdout.
//
// Tamper-then-revert evidence: swapping ReplaceAll for Replace with
// limit 1 makes the "twice-in-one-string" sub-test red ("session:
// cockpit-xyz socket: unix:/tmp/kitty-kommander-${BASENAME}");
// reverting greens. Replacing the sentinel with something else (say
// "$BASENAME" without braces) leaves the input unchanged — the
// "stdout-contains-assertion-shape" sub-test reds. Both reverted.
func TestExpandBasenameSubstitutes(t *testing.T) {
	t.Run("single token", func(t *testing.T) {
		got := expandBasename("kommander launch /tmp/${BASENAME}", "kommander-it-abc")
		want := "kommander launch /tmp/kommander-it-abc"
		if got != want {
			t.Errorf("expandBasename single-token: got %q, want %q", got, want)
		}
	})
	t.Run("twice in one string", func(t *testing.T) {
		got := expandBasename("session: cockpit-${BASENAME} socket: unix:/tmp/kitty-kommander-${BASENAME}", "xyz")
		want := "session: cockpit-xyz socket: unix:/tmp/kitty-kommander-xyz"
		if got != want {
			t.Errorf("expandBasename two-tokens: got %q, want %q", got, want)
		}
	})
	t.Run("no token leaves input unchanged", func(t *testing.T) {
		in := "healthy / 4/4 tabs / 0 drift"
		if got := expandBasename(in, "xyz"); got != in {
			t.Errorf("expandBasename no-token: got %q, want %q (assertions without the placeholder must pass through verbatim)", got, in)
		}
	})
	t.Run("stdout-contains-assertion-shape", func(t *testing.T) {
		// This is the exact shape of the stdout assertion that pins
		// kitty-kommander-iez's fix — if expandBasename stops doing
		// any substitution, the runner would compare kommander's
		// actual stdout against the literal "${BASENAME}" string and
		// every integration run would red immediately.
		got := expandBasename("socket: unix:/tmp/kitty-kommander-${BASENAME}", "kommander-it-42-999")
		want := "socket: unix:/tmp/kitty-kommander-kommander-it-42-999"
		if got != want {
			t.Errorf("expandBasename stdout-shape: got %q, want %q", got, want)
		}
	})
}

// TestExpandBasenamesInStepsMutates pins the driver that wires
// expandBasename into the RunIntegrationScenario flow. A step whose
// Invocation and Stdout/Stderr substring lists carry ${BASENAME} must
// be rewritten in place so runIntegrationStep sees the expanded
// strings. Without this, the helpers would exist but the runner would
// still compare literal ${BASENAME} against production stdout.
//
// Tamper-then-revert evidence: deleting the StdoutContains line from
// expandBasenamesInSteps reds the "stdout-contains" sub-assertion
// below; reverting greens. Deleting the Invocation line reds the
// "invocation-rewritten" sub-assertion; reverting greens.
func TestExpandBasenamesInStepsMutates(t *testing.T) {
	steps := []scenario.Step{
		{
			Invocation: "kommander launch /tmp/${BASENAME}",
			Expected: scenario.Expected{
				StdoutContains: []string{"session: cockpit-${BASENAME}", "no-token-here"},
				StderrContains: []string{"error: ${BASENAME}"},
			},
		},
		{
			Invocation: "kommander doctor",
			Expected: scenario.Expected{
				StdoutContains: []string{"healthy"},
			},
		},
	}
	expandBasenamesInSteps(steps, "test-slug")

	if steps[0].Invocation != "kommander launch /tmp/test-slug" {
		t.Errorf("invocation-rewritten: got %q", steps[0].Invocation)
	}
	if steps[0].Expected.StdoutContains[0] != "session: cockpit-test-slug" {
		t.Errorf("stdout-contains: got %v", steps[0].Expected.StdoutContains)
	}
	if steps[0].Expected.StdoutContains[1] != "no-token-here" {
		t.Errorf("non-token stdout entry was mangled: got %q", steps[0].Expected.StdoutContains[1])
	}
	if steps[0].Expected.StderrContains[0] != "error: test-slug" {
		t.Errorf("stderr-contains: got %v", steps[0].Expected.StderrContains)
	}
	if steps[1].Invocation != "kommander doctor" {
		t.Errorf("second step invocation should be untouched: got %q", steps[1].Invocation)
	}
	if steps[1].Expected.StdoutContains[0] != "healthy" {
		t.Errorf("second step non-token stdout was mangled: got %v", steps[1].Expected.StdoutContains)
	}
}
