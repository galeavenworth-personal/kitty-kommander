package kitty

import "fmt"

// Effect is one recorded call against a Mock controller. The fields
// line up with schema/cli/types.cue #KittyEffect so scenario tests can
// compare recorded effects to expected effects with a straight struct
// comparison.
//
// Kind values: "tab_created", "window_created", "window_closed",
// "text_sent", "tab_focused". The "no_change" effect is not recorded
// here — it is the ASSERTION that len(mock.Effects) == 0.
type Effect struct {
	Kind      string
	Title     string
	TargetTab string
	Selector  string
	Text      string
}

// Mock is the in-memory Controller used by scenario tests. It records
// every call as an Effect and returns the State the test configured
// via SetState.
//
// A single Mock is stateful across a test: LaunchWindow appends a
// WindowState to the matching tab in its State so a doctor test that
// first launches then lists sees the launched windows. Scenarios that
// only run one subcommand rarely exercise this chain, but keeping the
// mock consistent prevents surprise when a future scenario composes
// operations.
type Mock struct {
	Effects []Effect
	state   State
}

// NewMock returns a Mock with empty state.
func NewMock() *Mock { return &Mock{} }

// SetState replaces the state returned by List. Used by `doctor`
// scenarios to stage the "actual" kitty state the command diffs
// against CUE desired state.
func (m *Mock) SetState(s State) { m.state = s }

// Effect recording helpers are methods so a future implementation
// could swap to a channel for concurrency, without changing call sites.
func (m *Mock) record(e Effect) { m.Effects = append(m.Effects, e) }

func (m *Mock) LaunchTab(spec TabSpec) error {
	m.record(Effect{Kind: "tab_created", Title: spec.Title})
	m.state.Tabs = append(m.state.Tabs, TabState{
		Title: spec.Title,
	})
	for _, w := range spec.Windows {
		// Nested windows in an initial tab spec are also created;
		// they show up in List output but are NOT separately
		// recorded as window_created effects — scenarios assert
		// at the tab granularity when a tab is created with its
		// windows at once (matches `kitten @ launch --type=tab`
		// behavior of launching a single initial command).
		tab := &m.state.Tabs[len(m.state.Tabs)-1]
		tab.Windows = append(tab.Windows, WindowState{
			Title: w.Title,
			Cmd:   w.Cmd,
			Env:   w.Env,
		})
	}
	return nil
}

func (m *Mock) LaunchWindow(targetTab string, spec WindowSpec) error {
	m.record(Effect{
		Kind:      "window_created",
		Title:     spec.Title,
		TargetTab: targetTab,
	})
	for i := range m.state.Tabs {
		if m.state.Tabs[i].Title == targetTab {
			m.state.Tabs[i].Windows = append(m.state.Tabs[i].Windows, WindowState{
				Title: spec.Title,
				Cmd:   spec.Cmd,
				Env:   spec.Env,
			})
			return nil
		}
	}
	return fmt.Errorf("mock: tab %q not found for LaunchWindow", targetTab)
}

func (m *Mock) CloseWindow(selector string) error {
	m.record(Effect{Kind: "window_closed", Selector: selector})
	return nil
}

func (m *Mock) SendText(selector, text string) error {
	m.record(Effect{Kind: "text_sent", Selector: selector, Text: text})
	return nil
}

func (m *Mock) FocusTab(selector string) error {
	m.record(Effect{Kind: "tab_focused", Selector: selector})
	return nil
}

func (m *Mock) List() (*State, error) {
	s := m.state
	return &s, nil
}
