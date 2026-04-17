// Command kommander is the Go half of kitty-kommander v2. It reads
// CUE desired state and drives the kitty terminal via remote control.
// See design-package/STACK-v2.md §Layer 2 for the lifecycle contract
// and schema/cli/*.cue for the scenario suite this binary satisfies.
//
// Subcommands implemented in Phase 2: launch, doctor, reload. Other
// subcommands listed in STACK-v2.md (inspect, pane, cell-spawn,
// cell-teardown) arrive in later phases and are not yet registered
// here — keeping main.go scenarios-backed rather than speculative.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/galeavenworth-personal/kitty-kommander/internal/cli"
	"github.com/galeavenworth-personal/kitty-kommander/internal/help"
	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// subcommand bundles everything main needs to dispatch + help-compile
// a subcommand: the handler, the one-line tagline for `kommander
// --help`, and the per-subcommand header for `kommander <sub> --help`.
type subcommand struct {
	handler cli.Handler
	tagline string
	header  string
}

var subcommands = map[string]subcommand{
	"launch": {
		handler: cli.RunLaunch,
		tagline: "Launch a kommander instance for a project directory",
		header:  "Start a kommander instance",
	},
	"doctor": {
		handler: cli.RunDoctor,
		tagline: "Check session health (desired state vs actual state)",
		header:  "Diff CUE desired state against kitty actual state",
	},
	"reload": {
		handler: cli.RunReload,
		tagline: "Reconcile session — spawn missing, kill stale, restart changed",
		header:  "Reconcile session against CUE desired state",
	},
}

func main() {
	if len(os.Args) < 2 || isTopHelp(os.Args[1]) {
		fmt.Print(topHelp())
		return
	}

	sub := os.Args[1]
	rest := os.Args[2:]

	entry, ok := subcommands[sub]
	if !ok {
		fmt.Fprintf(os.Stderr, "kommander: unknown subcommand %q\n\n", sub)
		fmt.Fprint(os.Stderr, topHelp())
		os.Exit(2)
	}

	if containsHelp(rest) {
		fmt.Print(subcommandHelp(sub, entry))
		return
	}

	ctl, spawned, initialTabID, err := buildController(sub, rest)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	env := &cli.Env{
		Args:       rest,
		Controller: ctl,
		Workdir:    mustWd(),
	}
	code, stdout, stderr := entry.handler(env)
	if stdout != "" {
		fmt.Print(stdout)
	}
	if stderr != "" {
		fmt.Fprint(os.Stderr, stderr)
	}
	// If we spawned kitty and the handler failed, kill the orphan and
	// remove the socket file — leaving a half-initialized kitty around
	// is worse than no kitty, and the auditor specifically probes for
	// this class of bug.
	if code != 0 && spawned != nil {
		cleanupOrphan(spawned)
		os.Exit(code)
	}
	// Handler succeeded AND we spawned fresh kitty: close kitty's
	// initial cwd-titled tab so only the CUE-driven tabs remain. We
	// captured the initial tab id in buildController BEFORE the handler
	// ran (when it was definitionally the only tab); closing by stable
	// id avoids any index-based fragility. Close errors are non-fatal
	// — the core launch succeeded; a surviving initial tab is
	// cosmetic, not broken, and we report on stderr so the operator
	// sees it without failing the exit code.
	if code == 0 && spawned != nil && initialTabID > 0 {
		sel := fmt.Sprintf("id:%d", initialTabID)
		if cerr := ctl.CloseTab(sel); cerr != nil {
			fmt.Fprintf(os.Stderr,
				"kommander launch: could not close initial kitty tab %s: %v\n",
				sel, cerr)
		}
	}
	os.Exit(code)
}

// buildController selects the Controller implementation for a
// subcommand. For `launch`, if $KITTY_LISTEN_ON is unset we spawn a
// fresh kitty and construct against its socket. For `doctor`/`reload`
// (and `launch` invoked from inside an existing kitty session), we
// attach to $KITTY_LISTEN_ON via NewKittenExec, which errors if unset.
//
// Returns (controller, spawnedCmd, initialTabID, err). The spawnedCmd
// is non-nil only when we started a kitty process here; main uses it
// to clean up the orphan if the handler later fails. The initialTabID
// is the kitty-assigned id of the cwd-titled tab that kitty spawns on
// startup — captured here, before the handler runs, so main can close
// it post-handler and leave only the CUE-driven tabs. Zero when we
// attached to an existing socket (no initial tab to close).
func buildController(sub string, rest []string) (kitty.Controller, *exec.Cmd, int, error) {
	if sub != "launch" || os.Getenv("KITTY_LISTEN_ON") != "" {
		ctl, err := kitty.NewKittenExec()
		return ctl, nil, 0, err
	}
	// launch from outside kitty — derive socket from the dir arg and
	// spawn a fresh kitty.
	if len(rest) == 0 {
		// Let RunLaunch emit its usual "missing <dir>" error against a
		// nil-free controller. We can't derive a socket, so attach mode
		// would also fail. Construct a no-socket placeholder is wrong;
		// instead, fall through to NewKittenExec which will error
		// cleanly.
		ctl, err := kitty.NewKittenExec()
		return ctl, nil, 0, err
	}
	dir := rest[0]
	slug := deriveSlugForDir(dir)
	socket := "unix:/tmp/kitty-kommander-" + slug
	// Socket-file collision: refuse hard. Another kommander may be
	// running on this slug, or a prior crash left a stale socket. Per
	// CLAUDE.md, we do not probe-then-delete; the operator decides.
	socketPath := strings.TrimPrefix(socket, "unix:")
	if _, err := os.Stat(socketPath); err == nil {
		return nil, nil, 0, fmt.Errorf(
			"kommander launch: socket exists at %s; another kommander may be running. Remove the file if it is stale, or use a different directory",
			socketPath)
	}
	cmd, err := kitty.SpawnKitty(socket)
	if err != nil {
		return nil, nil, 0, fmt.Errorf("kommander launch: %w", err)
	}
	if err := kitty.WaitForSocket(socket, 5*time.Second); err != nil {
		// Spawn succeeded but socket never materialized — kitty is
		// broken or the environment is unusual. Clean up before
		// returning.
		cleanupOrphan(cmd)
		return nil, nil, 0, fmt.Errorf("kommander launch: %w", err)
	}
	ctl := kitty.NewKittenExecForSocket(socket)
	// Capture the initial tab's stable id NOW, before the handler's
	// LaunchTab calls add tabs. At this moment kitty has exactly one
	// tab: its default cwd-titled shell tab. We'll close this tab
	// after the handler succeeds. A List() failure here is recoverable
	// — we proceed without an initialTabID (0), and main skips the
	// post-handler close. The kommander tabs will still be created; the
	// cosmetic extra tab is not worth failing the whole launch.
	//
	// If List returns an unexpected >1 tab count (kitty config with
	// multiple startup tabs, say), we take the FIRST tab as the one to
	// close: it's the one present at spawn, before any LaunchTab. We
	// do not touch any others — that would overreach.
	initialTabID := 0
	if state, lerr := ctl.List(); lerr == nil && len(state.Tabs) >= 1 {
		initialTabID = state.Tabs[0].ID
	}
	return ctl, cmd, initialTabID, nil
}

// deriveSlugForDir duplicates the slug rule from internal/cli/launch.go
// (deriveSlug) so main can compute the socket path before the handler
// runs. Kept here rather than exported from cli to avoid a circular
// import and to keep the handler package mock-testable without this
// surface.
//
// Slug rule: basename, lowercased, non-alnum runs collapsed to a single
// hyphen, trimmed of leading/trailing hyphens.
func deriveSlugForDir(dir string) string {
	base := strings.ToLower(filepath.Base(dir))
	var b strings.Builder
	prevHyphen := false
	for _, r := range base {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
			b.WriteRune(r)
			prevHyphen = false
		} else if !prevHyphen {
			b.WriteRune('-')
			prevHyphen = true
		}
	}
	return strings.Trim(b.String(), "-")
}

// cleanupOrphan terminates a spawned kitty that is about to be
// abandoned due to a post-spawn failure. SIGTERM first, 500ms grace,
// SIGKILL if still alive. Logs both actions to stderr so the operator
// sees the full failure mode. Never returns an error — cleanup is
// best-effort; the primary failure has already been reported.
func cleanupOrphan(cmd *exec.Cmd) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	pid := cmd.Process.Pid
	if err := syscall.Kill(pid, syscall.SIGTERM); err != nil {
		fmt.Fprintf(os.Stderr, "kommander launch: SIGTERM pid %d: %v\n", pid, err)
	}
	// Wait up to 500ms for graceful exit. Poll every 50ms.
	deadline := time.Now().Add(500 * time.Millisecond)
	for time.Now().Before(deadline) {
		if err := syscall.Kill(pid, 0); err != nil {
			// Process is gone.
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	if err := syscall.Kill(pid, syscall.SIGKILL); err != nil {
		fmt.Fprintf(os.Stderr, "kommander launch: SIGKILL pid %d: %v\n", pid, err)
	}
}

func isTopHelp(arg string) bool {
	return arg == "-h" || arg == "--help" || arg == "help"
}

func containsHelp(args []string) bool {
	for _, a := range args {
		if a == "-h" || a == "--help" {
			return true
		}
	}
	return false
}

func topHelp() string {
	taglines := map[string]string{}
	for name, sc := range subcommands {
		taglines[name] = sc.tagline
	}
	return help.Top(taglines)
}

// subcommandHelp loads the CUE scenarios for this subcommand and
// compiles them into --help output. CUE load failures fall back to a
// terse one-line notice so --help still produces SOMETHING the user
// can read — but this is a bug signal, not a normal code path.
func subcommandHelp(sub string, entry subcommand) string {
	scs, err := loadScenariosFromBinary(sub)
	if err != nil {
		return fmt.Sprintf("kommander %s — %s\n(help scenarios unavailable: %v)\n",
			sub, entry.header, err)
	}
	return help.ForSubcommand(sub, entry.header, scs)
}

func loadScenariosFromBinary(sub string) ([]scenario.Scenario, error) {
	// Walk up from the binary's working directory until cue.mod
	// appears. In dev this finds the repo root directly; in an
	// install, the repo root is a known location (the binary is
	// symlinked from scripts/, which lives under the repo root).
	root, err := findRepoRoot()
	if err != nil {
		return nil, err
	}
	all, err := scenario.Load(root)
	if err != nil {
		return nil, err
	}
	return all[sub], nil
}

func findRepoRoot() (string, error) {
	d, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(d + "/cue.mod"); err == nil {
			return d, nil
		}
		parent := parentDir(d)
		if parent == d {
			return "", fmt.Errorf("cue.mod not found above %s", d)
		}
		d = parent
	}
}

func parentDir(d string) string {
	// strings.LastIndexByte would be cleaner but keeping imports
	// minimal here — main.go is short.
	for i := len(d) - 1; i >= 0; i-- {
		if d[i] == '/' {
			if i == 0 {
				return "/"
			}
			return d[:i]
		}
	}
	return d
}

func mustWd() string {
	d, err := os.Getwd()
	if err != nil {
		return "."
	}
	return d
}
