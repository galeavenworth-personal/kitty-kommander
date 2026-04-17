// Package kitty is the KittyController abstraction used by every
// kommander subcommand that touches the terminal. Two implementations
// live in this package:
//
//   - KittenExec: shells out to `kitten @ --to $KITTY_LISTEN_ON <verb>`.
//     Used in production. The socket path is NEVER hardcoded — the
//     constructor errors if $KITTY_LISTEN_ON is unset.
//
//   - Mock: records every call as an Effect and returns the state
//     the caller configured. Used by scenario tests to assert the
//     exact set of kitty operations a command performed, without
//     launching a real terminal.
//
// The interface is intentionally narrow — only operations a scenario
// can describe appear here. LaunchTab, LaunchWindow, CloseWindow,
// SendText, FocusTab, and List cover the six current scenarios.
package kitty

// WindowSpec describes a window to spawn inside a tab.
//
// Cmd is an argv slice; the zeroth element is the program. Title is
// the window title (becomes the `kitten @ launch --title` argument in
// production, and the recorded title in the mock).
type WindowSpec struct {
	Title string
	Cmd   []string
	Env   map[string]string
}

// TabSpec describes a tab and its initial windows. A tab may be
// "dynamic" (Cockpit, Helm) in which case Windows is empty and
// kommander populates it at runtime via LaunchWindow.
type TabSpec struct {
	Title   string
	Windows []WindowSpec
}

// State is what `kitty @ ls` returns, projected to the fields the
// scenarios care about. Matches schema/cli/types.cue #KittyFixture.
type State struct {
	Tabs []TabState `json:"tabs"`
}

type TabState struct {
	Title   string        `json:"title"`
	Windows []WindowState `json:"windows"`
}

type WindowState struct {
	Title string            `json:"title,omitempty"`
	Cmd   []string          `json:"cmd"`
	Env   map[string]string `json:"env,omitempty"`
}

// Controller is the surface every kommander subcommand uses to drive
// kitty. Scenarios assert what the command calls, in what order, with
// what arguments.
type Controller interface {
	// LaunchTab creates a new tab with the given title. Corresponds
	// to `kitten @ launch --type=tab --tab-title <title>`. Scenarios
	// record this as KittyEffect{kind: "tab_created", title: <title>}.
	LaunchTab(spec TabSpec) error

	// LaunchWindow creates a window inside the tab identified by
	// targetTab. Corresponds to
	// `kitten @ launch --type=window --match title:<targetTab> --title <title>`.
	// Scenarios record KittyEffect{kind: "window_created",
	// title: <title>, target_tab: <targetTab>}.
	LaunchWindow(targetTab string, spec WindowSpec) error

	// CloseWindow closes windows matched by the selector (e.g.
	// "title:builder"). Scenarios record KittyEffect{kind:
	// "window_closed", selector: <selector>}.
	CloseWindow(selector string) error

	// SendText pipes text into a window matched by selector.
	// Scenarios record KittyEffect{kind: "text_sent",
	// selector: <selector>, text: <text>}.
	SendText(selector, text string) error

	// FocusTab focuses the tab matched by selector (e.g.
	// "title:Dashboard"). Scenarios record KittyEffect{kind:
	// "tab_focused", selector: <selector>}.
	FocusTab(selector string) error

	// List returns the current kitty state. In production this
	// parses `kitten @ ls` JSON; the mock returns a configured State.
	List() (*State, error)
}
