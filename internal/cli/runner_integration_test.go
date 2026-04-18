//go:build integration

package cli

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// RunIntegrationScenario runs a multi-step scenario against a live
// kitty instance by shelling out to a prebuilt kommander binary for
// each step.
//
// Shape choices (per uib.3.F D1-D4 arbitration):
//
//   - D1: no pre-spawn. The runner does NOT call kitty.SpawnKitty
//     itself. The scenario's first step is "kommander launch <dir>",
//     which spawns kitty on a deterministic socket derived from the
//     project dir basename (see cmd/kommander/main.go buildController).
//     The scenario pins "socket: unix:/tmp/kitty-kommander-kommander-
//     integration-test" in stdout_contains, so the socket basename is
//     contract-required to be deterministic. A t.TempDir-basename
//     socket path would break that stdout assertion.
//
//   - D2: subprocess via TestMain-prebuilt binary. Every step shells
//     out to the kommander binary compiled by TestMainIntegration
//     (see TestMain in this file). This exercises the exact
//     production code path — buildController, os.Exit, stderr writes
//     — that in-process handler dispatch would bypass. If a future
//     refactor of main.go silently breaks socket derivation or
//     cleanupOrphan wiring, this test catches it at the integration
//     tier.
//
//   - D3: diffLsSnapshots on (title, cmd, pid). no_change under real-
//     kitty is asserted by capturing `kitten @ ls` pre-step and post-
//     step, then comparing WindowState on all three fields. PID is
//     load-bearing: a destructive close-and-respawn reload produces
//     identical titles and cmds (same session spec) but fresh PIDs;
//     title-and-cmd-only equality would silently accept that as a
//     no-op. See schema/cli/types.cue #Expected.kitty_effects
//     docstring for the real-kitty semantic.
//
//   - D4: pre-sweep + kitten quit teardown. The deterministic socket
//     path means a prior crashed run can leave a stale socket file,
//     which would make kommander launch's "socket exists" pre-flight
//     abort the current test. The runner sweeps the deterministic
//     path on startup (before calling the binary) so consecutive
//     test runs recover cleanly. Teardown uses `kitten @ --to
//     <socket> quit` (graceful kitty shutdown, the kitten way) plus
//     os.Remove on the socket file, rather than signal-killing the
//     kitty pid — we do not own the kitty *exec.Cmd here (D1); only
//     the kommander subprocess's *exec.Cmd, which has already exited
//     by the time each step returns.
//
// Parallelism: no t.Parallel(). The deterministic socket path allows
// only one live kitty at a time; the serialization is inherent.
func RunIntegrationScenario(t *testing.T, sc scenario.Scenario) {
	t.Helper()
	RequireKitty(t)

	if pkgMainBinary == "" {
		t.Fatal("integration test: kommander binary not compiled; TestMainIntegration did not run (or failed)")
	}

	if len(sc.Steps) == 0 {
		t.Fatalf("integration scenario %q has no steps; real_kitty single-invocation not supported yet", sc.ID)
	}

	// Pre-sweep the deterministic socket path. A prior crashed run
	// can leave the socket file behind, which would make kommander
	// launch's "socket exists" pre-flight abort. We best-effort
	// quit any live kitty bound to the socket first (so we're not
	// ripping the file out from under a healthy kitty on a contended
	// run), then remove the file unconditionally.
	const sockPath = "/tmp/kitty-kommander-kommander-integration-test"
	const sockURI = "unix:" + sockPath
	preSweepSocket(t, sockPath, sockURI)

	// Per-scenario tmp root for path-shaped args. basename preserved so
	// deriveSlug yields "kommander-integration-test" — the literal the
	// scenario's stdout assertion is pinned on.
	tmpRoot := t.TempDir()

	// Teardown runs in reverse registration order. Register the
	// socket-file remove FIRST (runs last) so it unconditionally
	// executes even if the kitten-quit call errors out. Then register
	// the kitten-quit (runs first, while the socket is still live).
	t.Cleanup(func() {
		if _, err := os.Stat(sockPath); err == nil {
			_ = os.Remove(sockPath)
		}
	})
	t.Cleanup(func() {
		closeKittySession(t, sockURI)
	})

	for i, step := range sc.Steps {
		runIntegrationStep(t, i, step, sockURI, tmpRoot)
	}

	if sc.Expected.FinalKittyState != nil {
		ctl := kitty.NewKittenExecForSocket(sockURI)
		got, err := ctl.List()
		if err != nil {
			t.Fatalf("final state: list: %v", err)
		}
		compareFinalState(t, got, sc.Expected.FinalKittyState)
	}
}

// preSweepSocket best-effort closes any kitty already bound to the
// deterministic socket (from a prior crashed run) and removes the
// socket file. Must leave the path clean for kommander launch's
// "socket exists" pre-flight to pass.
//
// Teardown primitive is `kitten @ close-tab --match all` — kitty
// 0.43 has no `@ quit` command, and closing every tab triggers
// kitty's natural shutdown. On a quiesced kitty the socket file is
// then removed by kitty itself; if the process is unresponsive we
// still os.Remove the file to unblock the next test.
func preSweepSocket(t *testing.T, path, uri string) {
	t.Helper()
	if _, err := os.Stat(path); err != nil {
		return
	}
	closeKittyViaSocket(uri)
	deadline := time.Now().Add(1 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(path); err != nil {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	_ = os.Remove(path)
}

// closeKittySession gracefully shuts down the kitty instance the
// runner started via `kommander launch`, via `kitten @ close-tab
// --match all`. Best-effort — teardown failures are logged but do
// not fail the test (the test's primary assertions have already
// completed by this point).
//
// Waits up to 2s for the socket file to disappear; if it doesn't,
// os.Remove is called in the companion cleanup (registered earlier
// in RunIntegrationScenario, runs last per LIFO).
func closeKittySession(t *testing.T, sockURI string) {
	t.Helper()
	sockPath := strings.TrimPrefix(sockURI, "unix:")
	if _, err := os.Stat(sockPath); err != nil {
		return
	}
	if err := closeKittyViaSocket(sockURI); err != nil {
		// Pre-existing dead socket is an expected condition; only
		// log something when the error surface is richer than that.
		if !strings.Contains(err.Error(), "Connection refused") &&
			!strings.Contains(err.Error(), "no such file") {
			t.Logf("cleanup: close-tab --match all %s: %v", sockURI, err)
		}
	}
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(sockPath); err != nil {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
}

// closeKittyViaSocket issues `kitten @ --to <uri> close-tab --match
// all`. Returns the underlying run error with stderr captured for
// teardown diagnostics. Used by both pre-sweep (recover from prior
// crash) and end-of-test teardown (shut down the launched kitty).
func closeKittyViaSocket(uri string) error {
	cmd := exec.Command("kitten", "@", "--to", uri, "close-tab", "--match", "all")
	var errBuf bytes.Buffer
	cmd.Stderr = &errBuf
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%w: %s", err, strings.TrimSpace(errBuf.String()))
	}
	return nil
}

// runIntegrationStep shells out to the prebuilt kommander binary for
// one step. Each step is independent: args are built from the
// invocation string, path-shaped args are rewritten into tmpRoot, and
// KITTY_LISTEN_ON is injected for non-launch subcommands (so doctor
// and reload find the socket the launch step just created).
func runIntegrationStep(t *testing.T, stepIdx int, step scenario.Step, sockURI, tmpRoot string) {
	t.Helper()

	parts := strings.Fields(step.Invocation)
	if len(parts) < 2 {
		t.Fatalf("step %d: invocation %q has no subcommand", stepIdx, step.Invocation)
	}
	sub := parts[1]
	rawArgs := parts[2:]
	args := materializeIntegrationArgs(t, rawArgs, tmpRoot)

	// no_change sentinel: snapshot pre-step state if the scenario's
	// kitty_effects is [{kind:"no_change"}]. Per types.cue, this is
	// the only real-kitty kitty_effects honored in 3.F.
	var pre *kitty.State
	wantNoChange := expectsNoChange(step.Expected)
	if wantNoChange {
		ctl := kitty.NewKittenExecForSocket(sockURI)
		s, err := ctl.List()
		if err != nil {
			t.Fatalf("step %d: pre-list: %v", stepIdx, err)
		}
		pre = s
	}

	// Invoke the binary. For non-launch subcommands we must set
	// KITTY_LISTEN_ON — main.go's buildController reads it for
	// doctor/reload. The launch step does NOT need it (default spawn
	// mode derives the socket from the project-dir basename).
	cmd := exec.Command(pkgMainBinary, append([]string{sub}, args...)...)
	cmd.Dir = tmpRoot
	env := os.Environ()
	if sub != "launch" {
		env = append(env, "KITTY_LISTEN_ON="+sockURI)
	}
	// Unset KITTY_LISTEN_ON for launch steps so main.go's default
	// spawn-mode branch activates (not attach-mode), regardless of
	// whether the test process itself inherited the variable.
	if sub == "launch" {
		env = filterOutEnv(env, "KITTY_LISTEN_ON")
	}
	cmd.Env = env

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	exitCode := 0
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			exitCode = ee.ExitCode()
		} else {
			t.Fatalf("step %d: run kommander %s: %v", stepIdx, sub, err)
		}
	}

	assertStepOutput(t, stepIdx, step, exitCode, stdout.String(), stderr.String())

	if wantNoChange {
		ctl := kitty.NewKittenExecForSocket(sockURI)
		post, perr := ctl.List()
		if perr != nil {
			t.Fatalf("step %d: post-list: %v", stepIdx, perr)
		}
		if diff := diffLsSnapshots(pre, post); diff != "" {
			t.Errorf("step %d (%q): expected no_change but kitten @ ls differs:\n%s",
				stepIdx, step.Invocation, diff)
		}
	}
}

// assertStepOutput mirrors RunScenario's non-kitty-effects assertions,
// scoped to a single step. kitty_effects under real-kitty mode are
// handled in runIntegrationStep via diffLsSnapshots.
func assertStepOutput(t *testing.T, stepIdx int, step scenario.Step, exitCode int, stdout, stderr string) {
	t.Helper()
	if exitCode != step.Expected.ExitCode {
		t.Errorf("step %d (%q) exit code: got %d, want %d\nstdout: %s\nstderr: %s",
			stepIdx, step.Invocation, exitCode, step.Expected.ExitCode, stdout, stderr)
	}
	for _, want := range step.Expected.StdoutContains {
		if !strings.Contains(stdout, want) {
			t.Errorf("step %d (%q) stdout missing %q\nstdout: %s", stepIdx, step.Invocation, want, stdout)
		}
	}
	for _, nope := range step.Expected.StdoutExcludes {
		if strings.Contains(stdout, nope) {
			t.Errorf("step %d (%q) stdout unexpectedly contains %q", stepIdx, step.Invocation, nope)
		}
	}
	for _, want := range step.Expected.StderrContains {
		if !strings.Contains(stderr, want) {
			t.Errorf("step %d (%q) stderr missing %q\nstderr: %s", stepIdx, step.Invocation, want, stderr)
		}
	}
	for _, nope := range step.Expected.StderrExcludes {
		if strings.Contains(stderr, nope) {
			t.Errorf("step %d (%q) stderr unexpectedly contains %q", stepIdx, step.Invocation, nope)
		}
	}
	assertJSONPaths(t, stdout, step.Expected.JSONPaths)
}

// expectsNoChange is true when the step's expected.kitty_effects is
// exactly [{kind:"no_change"}] — the only real-kitty kitty_effects
// assertion 3.F honors. Other kinds are silently ignored per types.cue
// #Expected.kitty_effects docstring.
func expectsNoChange(e scenario.Expected) bool {
	return len(e.KittyEffects) == 1 && e.KittyEffects[0].Kind == "no_change"
}

// diffLsSnapshots returns "" when two live kitten @ ls snapshots
// represent the same session (same tab titles, same per-tab window
// titles + cmds + pids). Returns a human-readable diff otherwise.
//
// PID equality is the load-bearing field: a destructive close-and-
// respawn reload produces identical titles and cmds (same session
// spec) but fresh PIDs. Title-and-cmd-only equality would silently
// accept that as a no-op, defeating the auditor's "reload-immediately-
// after-launch is idempotent" guard.
//
// Ordering: `kitten @ ls` returns tabs and windows in a stable order
// on a quiescent session (both are backed by kitty's internal linked
// lists). The integration runner guards no_change between a step's
// invocation and its completion, at which point the session IS
// quiescent — so positional comparison is correct here. If later
// kitty versions turn ordering nondeterministic, swap to a
// title-keyed comparison.
func diffLsSnapshots(pre, post *kitty.State) string {
	if pre == nil || post == nil {
		if pre == post {
			return ""
		}
		return fmt.Sprintf("one snapshot is nil (pre=%v post=%v)", pre != nil, post != nil)
	}
	if len(pre.Tabs) != len(post.Tabs) {
		return fmt.Sprintf("tab count differs: pre=%d post=%d", len(pre.Tabs), len(post.Tabs))
	}
	var b strings.Builder
	for i := range pre.Tabs {
		pt, qt := pre.Tabs[i], post.Tabs[i]
		if pt.Title != qt.Title {
			fmt.Fprintf(&b, "  tab[%d] title: pre=%q post=%q\n", i, pt.Title, qt.Title)
		}
		if len(pt.Windows) != len(qt.Windows) {
			fmt.Fprintf(&b, "  tab[%d] %q window count: pre=%d post=%d\n",
				i, pt.Title, len(pt.Windows), len(qt.Windows))
			continue
		}
		for j := range pt.Windows {
			pw, qw := pt.Windows[j], qt.Windows[j]
			if pw.Title != qw.Title {
				fmt.Fprintf(&b, "  tab[%d] %q window[%d] title: pre=%q post=%q\n",
					i, pt.Title, j, pw.Title, qw.Title)
			}
			if !cmdSliceEqual(pw.Cmd, qw.Cmd) {
				fmt.Fprintf(&b, "  tab[%d] %q window[%d] cmd: pre=%v post=%v\n",
					i, pt.Title, j, pw.Cmd, qw.Cmd)
			}
			if pw.PID != qw.PID {
				fmt.Fprintf(&b, "  tab[%d] %q window[%d] PID churn: pre=%d post=%d (destructive respawn — not a no-op)\n",
					i, pt.Title, j, pw.PID, qw.PID)
			}
		}
	}
	return b.String()
}

func cmdSliceEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// compareFinalState asserts the live kitten @ ls state matches the
// scenario's declared FinalKittyState. Thin wrapper around
// diffFinalState (pure function, no *testing.T) so the defensive
// unit tests can exercise the comparison logic directly.
func compareFinalState(t *testing.T, got *kitty.State, want *scenario.KittyFixture) {
	t.Helper()
	for _, e := range diffFinalState(got, want) {
		t.Errorf("%s", e)
	}
}

// diffFinalState returns zero or more error messages describing how
// the live state diverges from the fixture, under field-exact /
// no-coercion rules:
//
//   - Fixture DECLARES a field (title, cmd) → live value MUST match
//     exactly. Empty-string title in the fixture is a fixture bug
//     (Option A requires every non-dynamic window to carry an
//     explicit title); diffFinalState reports it as such rather than
//     silently accepting any live window.
//   - Fixture OMITS a field → that field is not asserted on the live
//     side. In practice: cmd is omitted from integration.cue's
//     final_kitty_state because install-dependent wrapper expansion
//     (euporie's python shebang, kommander-ui's node wrapper) differs
//     from the user-facing CUE declaration. Option A's thesis is that
//     titles are the install-independent identity layer.
//   - Dynamic-tab semantic: a fixture tab with `windows: []` means
//     "runtime-populated; don't assert window count or content." The
//     tab's presence and title ARE asserted (a missing Cockpit still
//     fails the tab-count check above).
//   - Tab ordering is not asserted; tabs are keyed by title.
//   - Tab count IS asserted exactly — extra tabs or missing tabs
//     both fail.
//
// Pure function — no *testing.T, no side effects. Returns a slice
// rather than a single error so every mismatch surfaces in one run;
// a test that's wrong in three places should surface three messages,
// not stop at the first.
func diffFinalState(got *kitty.State, want *scenario.KittyFixture) []string {
	var errs []string
	if len(got.Tabs) != len(want.Tabs) {
		errs = append(errs, fmt.Sprintf("final state: got %d tabs, want %d\ngot: %v",
			len(got.Tabs), len(want.Tabs), tabTitles(got.Tabs)))
		return errs
	}
	gotByTitle := map[string]kitty.TabState{}
	for _, tb := range got.Tabs {
		gotByTitle[tb.Title] = tb
	}
	for _, wt := range want.Tabs {
		gt, ok := gotByTitle[wt.Title]
		if !ok {
			errs = append(errs, fmt.Sprintf("final state: missing tab %q\ngot tabs: %v", wt.Title, tabTitles(got.Tabs)))
			continue
		}
		if len(wt.Windows) == 0 {
			continue
		}
		if len(gt.Windows) != len(wt.Windows) {
			errs = append(errs, fmt.Sprintf("final state: tab %q has %d windows, want %d\ngot: %v",
				wt.Title, len(gt.Windows), len(wt.Windows), gt.Windows))
			continue
		}
		gotWinByTitle := map[string]kitty.WindowState{}
		for _, gw := range gt.Windows {
			gotWinByTitle[gw.Title] = gw
		}
		for _, ww := range wt.Windows {
			if ww.Title == "" {
				errs = append(errs, fmt.Sprintf("final state: tab %q declares a window with empty title — fixture contract requires an explicit title (Option A)",
					wt.Title))
				continue
			}
			gw, ok := gotWinByTitle[ww.Title]
			if !ok {
				errs = append(errs, fmt.Sprintf("final state: tab %q missing window titled %q\ngot: %v",
					wt.Title, ww.Title, windowTitles(gt.Windows)))
				continue
			}
			wantCmd := ww.Cmd.Argv()
			if len(wantCmd) > 0 {
				if !cmdlineMatches(gw.Cmd, wantCmd) {
					errs = append(errs, fmt.Sprintf("final state: tab %q window %q: cmd mismatch\ngot:  %v\nwant: %v",
						wt.Title, ww.Title, gw.Cmd, wantCmd))
				}
			}
		}
	}
	return errs
}

// cmdlineMatches compares a kitten @ ls cmdline to the scenario's
// declared cmd. `got[0]` may be an absolute path (PATH-resolved) while
// `want[0]` is the bare command name — treat them as matching when
// `filepath.Base(got[0]) == want[0]`. Remaining argv elements must be
// identical.
func cmdlineMatches(got, want []string) bool {
	if len(got) == 0 || len(want) == 0 {
		return len(got) == len(want)
	}
	if filepath.Base(got[0]) != want[0] {
		return false
	}
	if len(got) != len(want) {
		return false
	}
	for i := 1; i < len(got); i++ {
		if got[i] != want[i] {
			return false
		}
	}
	return true
}

func tabTitles(tabs []kitty.TabState) []string {
	out := make([]string, len(tabs))
	for i, t := range tabs {
		out[i] = t.Title
	}
	return out
}

func windowTitles(ws []kitty.WindowState) []string {
	out := make([]string, len(ws))
	for i, w := range ws {
		out[i] = w.Title
	}
	return out
}

// materializeIntegrationArgs rewrites path-shaped args to per-test
// directories under tmpRoot. Same rule as runner.go's materializeDirs:
// "/"-prefixed arg, not "/nonexistent/*", gets rewritten to
// <tmpRoot>/<basename(arg)>. Basename preserved so deriveSlug yields
// the scenario-asserted stdout literal ("kommander-integration-test").
func materializeIntegrationArgs(t *testing.T, args []string, tmpRoot string) []string {
	t.Helper()
	out := make([]string, len(args))
	for i, a := range args {
		if strings.HasPrefix(a, "/") && !strings.HasPrefix(a, "/nonexistent") {
			dst := filepath.Join(tmpRoot, filepath.Base(a))
			if err := os.MkdirAll(dst, 0o755); err != nil {
				t.Fatalf("materialize %s: %v", dst, err)
			}
			out[i] = dst
		} else {
			out[i] = a
		}
	}
	return out
}

// filterOutEnv drops any `<name>=...` entry from an os.Environ-style
// slice. Used to strip KITTY_LISTEN_ON from the launch step's env —
// the test process may be running inside kitty itself (contributor's
// terminal), and we want launch's buildController to take its default
// spawn branch, not attach-mode-by-accident.
func filterOutEnv(env []string, name string) []string {
	prefix := name + "="
	out := env[:0:0]
	for _, e := range env {
		if strings.HasPrefix(e, prefix) {
			continue
		}
		out = append(out, e)
	}
	return out
}

// RequireKitty skips the test when `kitty` is not on PATH. Idiomatic
// Go test skip — not an error, because the integration tier is
// local-only today. CI-tier wiring (3.G) decides whether these tests
// must run on every push; today the auto-skip is the right default
// so contributors without kitty installed aren't blocked.
func RequireKitty(t *testing.T) {
	t.Helper()
	if _, err := exec.LookPath("kitty"); err != nil {
		t.Skipf("integration test requires `kitty` on PATH: %v", err)
	}
	if _, err := exec.LookPath("kitten"); err != nil {
		t.Skipf("integration test requires `kitten` on PATH: %v", err)
	}
}

