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

	// --attach is a launch-only flag; extract it here so handlers see a
	// flag-free positional arg list. Silently ignored on other
	// subcommands (doctor/reload don't branch on it today). Repeated
	// occurrences are idempotent.
	rest, attachMode := extractAttachFlag(rest)

	ctl, spawned, initialTabID, socket, mode, err := buildController(sub, rest, attachMode)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	env := &cli.Env{
		Args:       rest,
		Controller: ctl,
		Workdir:    mustWd(),
		Socket:     socket,
		Mode:       mode,
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

// extractAttachFlag scans rest for `--attach` (exact match) and
// returns rest with those occurrences removed plus a bool indicating
// whether the flag was seen. Only the `--attach` bare form is
// accepted — `--attach=true` / `--attach=1` are rejected elsewhere by
// simply not matching, which causes the handler to see an unknown
// positional arg and fail cleanly. Repeated `--attach` is idempotent.
//
// Flag position is intentionally not constrained: operators may write
// `kommander launch --attach /tmp/foo` OR `kommander launch /tmp/foo
// --attach` and both work. This matches the UNIX tradition for
// boolean flags that have no arg to disambiguate from positionals.
func extractAttachFlag(rest []string) ([]string, bool) {
	out := rest[:0:0]
	attach := false
	for _, a := range rest {
		if a == "--attach" {
			attach = true
			continue
		}
		out = append(out, a)
	}
	return out, attach
}

// buildController selects the Controller implementation and its
// configuration for a subcommand.
//
// launch default (no --attach): ALWAYS spawn a fresh kitty from the
// slug derived from <dir>. $KITTY_LISTEN_ON is deliberately ignored
// here — the env var is set in every shell inside kitty, so treating
// it as "consent to attach" silently pollutes unrelated kitty sessions
// with duplicated tabs (the kitty-kommander-6g8 audit finding). The
// operator explicitly opts into attach-mode with `--attach`.
//
// launch --attach: bind the controller to $KITTY_LISTEN_ON. Errors if
// the env var is unset — we need a socket to talk to. No initial tab
// is captured/closed (tabs pre-exist and belong to the operator).
//
// doctor, reload: unchanged. Require $KITTY_LISTEN_ON; error if unset.
// Both operate on an existing session.
//
// Returns (controller, spawnedCmd, initialTabID, socket, mode, err).
//   - spawnedCmd is non-nil only on the spawn path; main uses it to
//     clean up the orphan if the handler later fails.
//   - initialTabID is kitty's id for the cwd-titled tab on the spawn
//     path; 0 otherwise.
//   - socket is the `unix:/path` string the controller is bound to.
//     Empty when err != nil or when we construct against an env-var
//     controller whose socket we don't echo back to the caller (doctor,
//     reload). RunLaunch prints this directly as its `socket:` line.
//   - mode is "spawn" or "attach" on the launch path; empty for
//     doctor/reload.
func buildController(sub string, rest []string, attachMode bool) (kitty.Controller, *exec.Cmd, int, string, string, error) {
	if sub != "launch" {
		ctl, err := kitty.NewKittenExec()
		return ctl, nil, 0, "", "", err
	}
	if attachMode {
		envSock := os.Getenv("KITTY_LISTEN_ON")
		if envSock == "" {
			return nil, nil, 0, "", "", fmt.Errorf(
				"kommander launch --attach: KITTY_LISTEN_ON is not set; --attach requires an existing kitty session socket to bind to")
		}
		ctl := kitty.NewKittenExecForSocket(envSock)
		// Attach mode: the existing kitty's tabs belong to the
		// operator. We do NOT capture an "initial" tab to close —
		// anything present is theirs.
		return ctl, nil, 0, envSock, "attach", nil
	}
	// SPAWN MODE — the default. Ignore $KITTY_LISTEN_ON.
	if len(rest) == 0 {
		// No <dir> arg: let RunLaunch emit its own "missing <dir>"
		// error. We need a Controller shape; return a dummy-safe
		// KittenExec — since the handler will exit before any kitten @
		// call, the socket value never matters. Passing a no-socket
		// KittenExec would only cause trouble if execution reached a
		// run() call, which it won't.
		return kitty.NewKittenExecForSocket(""), nil, 0, "", "spawn", nil
	}
	dir := rest[0]
	slug := deriveSlugForDir(dir)
	socket := "unix:/tmp/kitty-kommander-" + slug
	// Socket-file collision: refuse hard. Another kommander may be
	// running on this slug, or a prior crash left a stale socket. Per
	// CLAUDE.md, we do not probe-then-delete; the operator decides.
	socketPath := strings.TrimPrefix(socket, "unix:")
	if _, err := os.Stat(socketPath); err == nil {
		return nil, nil, 0, "", "", fmt.Errorf(
			"kommander launch: socket exists at %s; another kommander may be running. Remove the file if it is stale, or use a different directory",
			socketPath)
	}
	cmd, err := kitty.SpawnKitty(socket)
	if err != nil {
		return nil, nil, 0, "", "", fmt.Errorf("kommander launch: %w", err)
	}
	if err := kitty.WaitForSocket(socket, 5*time.Second); err != nil {
		// Spawn succeeded but socket never materialized — kitty is
		// broken or the environment is unusual. Clean up before
		// returning.
		cleanupOrphan(cmd)
		return nil, nil, 0, "", "", fmt.Errorf("kommander launch: %w", err)
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
	return ctl, cmd, initialTabID, socket, "spawn", nil
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
