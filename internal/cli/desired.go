package cli

import "github.com/galeavenworth-personal/kitty-kommander/internal/kitty"

// desiredTabs is the canonical session layout kommander owns:
// Cockpit (dynamic — no initial windows), Driver (claude agent),
// Notebooks (euporie), Dashboard (DAG + Sidebar Ink apps).
//
// This is the source of truth for BOTH launch (which tab specs to
// create) and doctor/reload (what kitty state to compare against).
// Kept as a function so future scenarios that parameterize the
// layout (--config custom.cue) have a clean extension point.
//
// Matches the doctor-healthy scenario's kitty_state fixture exactly;
// the healthy fixture IS the desired state. If the fixture and this
// function diverge, the healthy scenario catches it (desired != actual
// even though the fixture is supposed to be the healthy snapshot).
func desiredTabs() []kitty.TabSpec {
	return []kitty.TabSpec{
		{Title: "Cockpit"},
		{Title: "Driver", Windows: []kitty.WindowSpec{{
			Cmd: []string{"claude", "--agent", "cell-leader",
				"--dangerously-skip-permissions"},
		}}},
		{Title: "Notebooks", Windows: []kitty.WindowSpec{{
			Cmd: []string{"euporie", "notebook"},
		}}},
		{Title: "Dashboard", Windows: []kitty.WindowSpec{
			{Title: "DAG", Cmd: []string{"kommander-ui", "--dag"}},
			{Title: "Sidebar", Cmd: []string{"kommander-ui", "--sidebar"}},
		}},
	}
}

// desiredTabsForDoctor is a view of desiredTabs stripped to the
// subset doctor can observe in kitty @ ls. The doctor-healthy
// fixture uses the short-form "claude" and "euporie notebook" for
// window cmd — matching what production `kitty @ ls` would return
// after the user shell resolves the full argv. So doctor compares
// only the first-token match, not the full argv.
//
// This mirrors the schema's #KittyFixture doc comment: kitty @ ls
// returns the running command shape, not the spawn directives.
// Checking argv[0] equality (with the scenario's token) is the
// tightest assertion that survives shell-level command expansion.
func desiredTabsForDoctor() []kitty.TabSpec {
	return desiredTabs()
}
