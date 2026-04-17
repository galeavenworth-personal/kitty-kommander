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

	ctl, err := kitty.NewKittenExec()
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
	os.Exit(code)
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
