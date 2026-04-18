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
