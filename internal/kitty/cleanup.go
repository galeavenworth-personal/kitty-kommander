package kitty

import (
	"fmt"
	"os/exec"
	"syscall"
	"time"
)

// CleanupOrphan terminates an abandoned kitty child process. SIGTERM
// first, 500ms grace, SIGKILL if still alive. Never returns an error —
// cleanup is best-effort; the primary failure has already been
// reported.
//
// report is invoked for each signal that returns an error from
// syscall.Kill. Callers attach their own stderr prefix ("kommander
// launch: ...", "cleanup: ..."). A nil report is treated as "swallow
// the diagnostic" — the integration-test harness uses this form when a
// t.Logf equivalent is not desired.
//
// Lifted out of cmd/kommander/main.go so the integration-test harness
// (internal/cli/runner_integration.go) can reuse exactly the same
// teardown semantics the production binary uses for post-spawn
// failure cleanup. The harness builds the binary once via TestMain
// and shells out per-step; it does not own a *exec.Cmd for the kitty
// itself, so this helper is used only for the TestMain-compiled
// kommander subprocess. Kitty teardown goes through `kitten @ quit`
// + os.Remove, not this helper.
func CleanupOrphan(cmd *exec.Cmd, report func(string)) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	pid := cmd.Process.Pid
	if err := syscall.Kill(pid, syscall.SIGTERM); err != nil && report != nil {
		report(fmt.Sprintf("SIGTERM pid %d: %v", pid, err))
	}
	deadline := time.Now().Add(500 * time.Millisecond)
	for time.Now().Before(deadline) {
		if err := syscall.Kill(pid, 0); err != nil {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	if err := syscall.Kill(pid, syscall.SIGKILL); err != nil && report != nil {
		report(fmt.Sprintf("SIGKILL pid %d: %v", pid, err))
	}
}
