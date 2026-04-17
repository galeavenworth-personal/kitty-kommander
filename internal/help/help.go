// Package help compiles --help output from CUE scenario help_summary
// fields, per the expectation-drift rule in STACK-v2.md §TDD Architecture.
// Help text is generated from the same source of truth as tests, so
// the three artifacts (implementation, tests, docs) cannot drift.
//
// The compiler is deliberately simple: a header, the per-scenario
// help_summary blocks joined by blank lines, and a short footer.
// No flag reference table — the primary consumer is an AI agent
// forming tool calls, and worked examples outperform flag lists for
// that use case.
package help

import (
	"fmt"
	"strings"

	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// ForSubcommand renders the --help output for `kommander <subcmd>`.
// scenarios is the loaded list for that subcommand; header is a
// one-line description (e.g. "Launch a kommander instance for a
// project directory.").
//
// Output shape (example for `kommander launch`):
//
//	kommander launch — Launch a kommander instance for a project directory
//
//	Launch a kommander instance:
//	  kommander launch /path/to/project
//	  → Opens kitty with Cockpit, Driver, Notebooks, Dashboard tabs.
//	  → Derives session name + socket path from the directory basename.
//
//	Error — directory does not exist:
//	  kommander launch /bad/path
//	  → exit 1, no kitty launched, error on stderr.
//
// Every scenario contributes its help_summary as a block.
func ForSubcommand(subcmd, header string, scenarios []scenario.Scenario) string {
	var b strings.Builder
	fmt.Fprintf(&b, "kommander %s — %s\n\n", subcmd, header)
	for i, sc := range scenarios {
		if i > 0 {
			b.WriteString("\n")
		}
		b.WriteString(sc.HelpSummary)
		b.WriteString("\n")
	}
	return b.String()
}

// Top renders `kommander --help` — the subcommand index. Each
// subcommand gets one line with the operator-facing tagline passed
// in via taglines.
func Top(taglines map[string]string) string {
	var b strings.Builder
	b.WriteString("kommander — Terminal cockpit for AI agent teams\n\n")
	b.WriteString("Commands:\n")
	// Stable order so --help output is deterministic.
	keys := make([]string, 0, len(taglines))
	for k := range taglines {
		keys = append(keys, k)
	}
	sortStrings(keys)
	for _, k := range keys {
		fmt.Fprintf(&b, "  %-10s %s\n", k, taglines[k])
	}
	b.WriteString("\nSee `kommander <command> --help` for worked examples per command.\n")
	return b.String()
}

func sortStrings(ss []string) {
	// Tiny inline bubble-ish — only called once per process with <10
	// entries, so keeping stdlib out of help keeps the imports minimal.
	for i := 0; i < len(ss); i++ {
		for j := i + 1; j < len(ss); j++ {
			if ss[j] < ss[i] {
				ss[i], ss[j] = ss[j], ss[i]
			}
		}
	}
}
