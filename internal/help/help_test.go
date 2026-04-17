package help

import (
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(file), "..", "..")
}

// TestHelpContainsHelpSummary is the definition-of-done guarantee:
// `./kommander <sub> --help` must contain the right help_summary text
// for every scenario of that subcommand. We load the real CUE and
// check ForSubcommand output contains every scenario's help_summary
// as a substring. Covers launch, doctor, reload — one test per
// subcommand per the definition of done.
func TestHelpContainsHelpSummary(t *testing.T) {
	scs, err := scenario.Load(repoRoot(t))
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	for _, subcmd := range []string{"launch", "doctor", "reload"} {
		sclist, ok := scs[subcmd]
		if !ok || len(sclist) == 0 {
			t.Fatalf("no scenarios loaded for %q", subcmd)
		}
		out := ForSubcommand(subcmd, "test header", sclist)
		for _, sc := range sclist {
			want := strings.TrimSpace(sc.HelpSummary)
			if !strings.Contains(out, want) {
				t.Errorf("%s --help missing help_summary for scenario %q\nhelp was:\n%s\n\nwant substring:\n%s",
					subcmd, sc.ID, out, want)
			}
		}
	}
}
