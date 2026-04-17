package cli

import (
	"fmt"

	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
	"github.com/galeavenworth-personal/kitty-kommander/internal/session"
)

// desiredTabs loads the canonical session layout from CUE. Source of
// truth is schema/session/default.cue (embedded into the binary via
// internal/session/loader.go). If the project directory contains a
// kommander.cue overlay, the overlay's session.tabs fully replace the
// default tabs — this is the simplest-replace contract proven by the
// cue-config-driven-layout scenario.
//
// projectDir is the positional <dir> arg from `kommander launch`. An
// empty string means "use defaults only" — appropriate for doctor and
// reload call sites that don't yet accept a project arg and must
// operate against the binary's own working directory.
//
// overlayPath is the relative name ("kommander.cue") when an overlay
// was loaded, empty otherwise. Callers use this to decide whether to
// mention the config source in stdout.
func desiredTabs(projectDir string) ([]kitty.TabSpec, string, error) {
	s, overlayPath, err := session.Load(projectDir)
	if err != nil {
		return nil, "", fmt.Errorf("load session: %w", err)
	}
	return toTabSpecs(s), overlayPath, nil
}

// desiredTabsForDoctor is a view of desiredTabs used by doctor and
// reload. Both operate against the ambient session — they don't take
// a project dir arg today. They load the default layout. If a future
// scenario wires doctor/reload to a specific project dir, this
// signature grows an arg and the internal lookup adapts.
func desiredTabsForDoctor() []kitty.TabSpec {
	s, _, err := session.Load("")
	if err != nil {
		// Embedded schema is compiled in; load failure here means
		// the binary shipped broken. Returning nil keeps doctor from
		// panicking; the empty-desired case surfaces as "all tabs
		// are extra" which is a clear-enough signal in the report.
		return nil
	}
	return toTabSpecs(s)
}

// toTabSpecs converts the session.Session shape (decoded from CUE)
// into the kitty.TabSpec shape the Controller consumes. This is a
// pure restructuring — no semantic changes, just two packages with
// parallel shapes that need bridging.
func toTabSpecs(s session.Session) []kitty.TabSpec {
	out := make([]kitty.TabSpec, 0, len(s.Tabs))
	for _, t := range s.Tabs {
		spec := kitty.TabSpec{Title: t.Title}
		for _, w := range t.Windows {
			spec.Windows = append(spec.Windows, kitty.WindowSpec{
				Title: w.Title,
				Cmd:   w.Cmd,
				Env:   w.Env,
			})
		}
		out = append(out, spec)
	}
	return out
}
