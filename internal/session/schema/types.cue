// Session schema — the canonical description of a kommander session.
//
// This package defines the shape of the desired kitty session: tabs,
// windows, commands, layouts. A kommander binary loads:
//
//   1. The default session (schema/session/default.cue, baked in via
//      go:embed or loaded from the install path).
//   2. Optional per-project overlay (<project-dir>/kommander.cue) when
//      present. If the overlay sets `session:`, it wins; otherwise the
//      default is used.
//
// The unified #Session drives `kommander launch`, `doctor`, `reload` —
// no Go hardcode of tab/window layout lives anywhere in the binary.
// Drift between this schema and the binary's behavior IS the bug the
// `cue-config-driven-layout` scenario is designed to catch.
package session

#Session: {
	// Derived from the project dir basename at launch time. The
	// default.cue file leaves these empty; the binary fills them in
	// per-invocation.
	slug:   string | *""
	socket: string | *""

	// Tabs in order. First tab shows on kitty launch; others via
	// `focus-tab`.
	tabs: [...#Tab]
}

#Tab: {
	// Tab title as set via `kitten @ launch --tab-title`. Also the
	// identity doctor/reload use to match against live kitty state.
	title: string

	// Pre-configured window layout. If omitted, kitty default.
	layout?: "tall" | "splits" | "stack"

	// Windows spawned at launch. A dynamic:true tab launches with
	// zero initial windows (Cockpit, Helm) — agents spawn windows
	// later via `kommander pane`.
	windows: [...#Window] | *[]

	// true = tab has no initial windows; windows are created at
	// runtime by agent commands. Default false. When true, `doctor`
	// does not treat an empty-windows tab as drift.
	dynamic: bool | *false
}

#Window: {
	// Window title set via `--title`. Optional — if absent, kitty
	// shows the process name. doctor's window-matching depends on
	// this: titled windows match by title; untitled match by cmd[0].
	// Leaving this empty on a window whose process produces a
	// dynamic title (like "⠂ cell-leader" for claude) will cause
	// doctor to misreport window_missing — set an explicit title
	// whenever the process may retitle itself at runtime.
	title?: string

	// Command to run in the window. Tolerates string OR []string.
	// Shell-style "euporie notebook" and argv-style ["euporie",
	// "notebook"] both legal — the binary normalizes at launch.
	cmd: string | [...string]

	// Directional spawn hint for `kitten @ launch --location`.
	// Spawn-time directive only; kitty does NOT retain this in `@ ls`
	// output (see schema/cli/types.cue #KittyFixture doc).
	location?: "vsplit" | "hsplit" | "after" | "before"

	// Environment variables. Spawn-time only.
	env?: {[string]: string}

	// true = this window runs a kommander-ui Ink app (--sidebar or,
	// once uib.3.DAG ships, --dag). Used by doctor for Ink-specific
	// health checks beyond "is the process running" (e.g. the Ink
	// frame is rendering, not stuck).
	ink?: bool
}
