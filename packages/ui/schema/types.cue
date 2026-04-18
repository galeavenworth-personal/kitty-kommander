// Package ui holds the CUE scenario suite for the kommander-ui React
// package — the dual-target renderer that produces both the Ink TUI
// (Dashboard, Helm, Cockpit status, agent panes) and the react-dom
// web build (Vite dev server, Playwright target).
//
// Each scenario drives THREE test artifacts, not one:
//   1. An ink-testing-library test that renders the component and
//      checks contains/excludes + lastFrame() snapshot.
//   2. A Playwright spec that renders the same component in the
//      web build and checks locator_text + screenshot.
//   3. Pure-hook tests (when a scenario exercises hook logic directly).
//
// A scenario whose generated artifacts pass all three tiers is the
// steel thread's proof that the same React code renders identically
// through both targets against the same fixtures.
package ui

import "github.com/galeavenworth-personal/kitty-kommander/schema/shared"

// UIScenario specifies one verification case for one component or hook.
//
// Two render modes, gated by `render_mode`:
//
//   "fixture" (default) — classic frame-assertion scenario. Component
//     is rendered under a fixture-injected provider; assertions check
//     the rendered Ink frame (Tier 2) + the rendered web DOM (Tier 3).
//     The scenario body must satisfy BOTH the TUI and web tiers — if
//     the fixtures can only render correctly in one target, the
//     scenario is lying about the component.
//
//   "production" — verification of a production hook's side-effecting
//     behavior: which shell commands it invokes, how often it polls,
//     and whether the entry point stays alive after first render.
//     Generates a vitest test that mocks execFileSync and asserts
//     the hook's shell calls + polling + stays-alive semantics.
//     NOT a frame-assertion scenario; no snapshot, no playwright.
//
// Field requirements split by mode. Fixture scenarios require
// `fixtures` + `expected`. Production scenarios require `production`.
// CUE if-blocks enforce this; a scenario that sets wrong-mode fields
// fails `cue vet`.
#UIScenario: {
	// Lowercase-with-dashes; becomes the TUI test name, the
	// Playwright test name, and the golden-file basename.
	id: string & =~"^[a-z][a-z0-9-]*$"

	// Classification. Conventions match the CLI side:
	//   "basic"      — first scenario per component
	//   "common"     — frequent non-trivial state
	//   "edge-case"  — empty, zero, nil — these must NOT crash
	//   "error"      — explicit failure surface
	//   "production" — (suggested) production-mode scenarios
	tags: [...string]

	// The user story. "The operator glances at the Dashboard and
	// sees …" Drives the scenario's content and the test's docstring.
	story: string

	// The React component OR hook under test. For fixture-mode
	// scenarios, matches the filename in packages/ui/src/components/
	// (without extension). For production-mode scenarios, may name
	// a hook (e.g. "useBeads") or an entry (e.g. "ink-main-sidebar")
	// — the generator uses `render_mode` + `component` to decide
	// which test template to emit.
	component: string

	// Render mode — see the type-level docstring above. Default is
	// "fixture" to preserve the existing scenario shape; new scenarios
	// that verify production code paths opt in to "production".
	render_mode: *"fixture" | "production"

	if render_mode == "fixture" {
		// The world the component renders. Same shape the production
		// hooks (useBeads, useGitLog, useCells, …) return, so the
		// component doesn't need a separate fixture-adapter.
		fixtures: shared.#BeadsFixture

		// What the rendered output must (and must not) contain, plus
		// snapshot and Playwright assertions for the three tiers.
		expected: #UIExpected
	}

	if render_mode == "production" {
		// Production-path assertions — what the hook shells, how
		// often it polls, and whether the entry stays alive.
		production: #ProductionAssertion
	}
}

// ProductionAssertion describes the observable behavior of a production
// hook or entry point. Unlike fixture-mode assertions (which check
// rendered output), these check side effects and process-lifecycle
// properties — the kind of thing a mocked-execFileSync vitest test
// can verify.
//
// This type exists because "the Sidebar renders 60% complete" and
// "useBeads shells `bd --format=json stats`" are structurally different
// claims: the first is about pixels/characters in a frame, the second
// is about a syscall trace. Forcing them into one assertion shape
// (e.g. contains/excludes on the rendered frame) either generates
// vacuous tests or couples the scenario to implementation details
// (the hook's log output). Keep them separate.
#ProductionAssertion: {
	// Hook or entry under test is read from the enclosing scenario's
	// `component` field — there is no separate `hook` field here,
	// because every attempt to set both ended in duplicate strings
	// (`component: "useBeads"` + `hook: "useBeads"`). If a future
	// scenario needs to decompose an entry (`component: "ink-main-
	// sidebar"`) into the hook it mocks, extend this type with a
	// `mocks_hook` field then — not pre-emptively.

	// Commands the hook must shell during its lifecycle. Each entry
	// is a predicate over observed execFileSync calls: the generated
	// test asserts at least one observed call where command == entry.command
	// AND every string in entry.args_contains appears in the joined
	// args array. Substring match is deliberately forgiving — the
	// scenario cares about "did it shell bd for the ready queue"
	// (args_contains: ["ready"]), not "did it use exactly these
	// flags" (which couples scenario to implementation).
	shells: [...{
		// Exact command binary, e.g. "bd" or "git".
		command: string

		// Substrings every one of which must appear in args.join(" ").
		// Empty list means "any invocation of this command counts".
		args_contains: [...string]
	}]

	// Polling contract — if set, the generated test advances fake
	// timers by `interval_seconds` and asserts the shell commands
	// above are re-invoked. If unset, the hook runs once at mount
	// and the test asserts exactly one invocation per command.
	polling?: {
		interval_seconds: int & >0
	}

	// Liveness contract — if true, the generated test imports the
	// entry point (e.g. ink.tsx's main with --sidebar) under a
	// timeout and asserts the process does not exit synchronously.
	// If false, no liveness check is generated.
	//
	// Specifically designed to catch the 3.D-discovered regression:
	// renderSidebar() returned without stdin subscription or polling
	// loop, so the Dashboard tab died immediately under kitty.
	//
	// No default — explicit required. A silent default to `false`
	// would mean a forgetful author drops the 3.D-regression check
	// without any CUE error; `true` is the common case but not
	// universal (a pure-read hook-unit scenario with no entry
	// concern might legitimately set `false`). Make the author
	// state their intent.
	stays_alive: bool
}

// UIExpected bundles every tier's assertions into one block.
//
// - `contains` / `excludes` are BLUNT string checks against the
//   full rendered output — Tier 2 checks `lastFrame()` (Ink's
//   terminal buffer as one string), Tier 3 checks the visible
//   text on the Playwright page as one string. Neither is
//   region-scoped. A substring match is "exists somewhere in the
//   frame," not "exists in the expected part of the frame."
//
// - `snapshot` is the Tier 2 golden (stored under
//   packages/ui/test/tui/__snapshots__/<snapshot>.txt). First run
//   writes the frame; subsequent runs diff. This is the targeted
//   Tier 2 check — the one that catches "60% rendered in the wrong
//   region" even though `contains: ["60%"]` is satisfied.
//
// - `playwright` is the Tier 3 block — pixel screenshot + CSS
//   selector text map. `locator_text` is the Tier 3 equivalent of
//   what `snapshot` is for Tier 2: targeted, region-scoped checks.
//
// TIER ASYMMETRY — intentional, named explicitly:
//   Tier 2 has: contains, excludes, snapshot (golden-file diff)
//   Tier 3 has: contains, excludes, screenshot (pixel diff),
//               locator_text (selector-scoped text)
// Tier 3 can targeted-check WITHOUT a golden file (locator_text);
// Tier 2 cannot. If you want a region-scoped Tier 2 assertion,
// rely on `snapshot` — there is no `tui_regions` equivalent.
//
// CONVENTIONS (not CUE-enforced, generator-enforced):
// - Every visible-surface scenario sets at least `snapshot` OR a
//   non-empty `contains`. A scenario with only `playwright` set
//   is syntactically legal but passes Tier 2 trivially — the
//   generator flags this unless tags include "tier-web-only".
// - Prefer `snapshot` + `playwright.screenshot` together on any
//   rendering scenario — Tier 2 catches layout in terminal space,
//   Tier 3 catches layout in DOM space, neither is redundant.
#UIExpected: {
	contains: [...string]
	excludes: [...string]
	snapshot?:   string
	playwright?: #PlaywrightAssertion
}

// PlaywrightAssertion drives the Tier 3 web test generator.
// Both fields are optional so a scenario can pick: golden screenshot
// only, locator assertions only, or both. Most rendering scenarios
// want both — locators catch semantic regressions (wrong text in
// the right place), screenshots catch layout regressions (right
// text in the wrong place).
#PlaywrightAssertion: {
	// Filename stored under packages/ui/test/web/screenshots/.
	// Compared pixel-wise with Playwright's default tolerance
	// (maxDiffPixelRatio 0.1 recommended for text-heavy UI).
	screenshot?: string

	// CSS selector → expected visible text. Generator produces
	// `await expect(page.locator(sel)).toHaveText(text)` per entry.
	//
	// SELECTOR CONVENTION: keys SHOULD be `[data-testid="..."]`
	// attribute selectors, not class selectors. Class-based
	// selectors (`.health-bar`) couple scenarios to the web
	// adapter's styling decisions; a rename in CSS breaks the
	// test without the feature being broken.
	//
	// The web adapter (packages/ui/src/web/adapters.tsx) is
	// responsible for emitting `data-testid` attributes on every
	// element a scenario references. The TUI adapter ignores
	// them. Scenarios document the contract; the web adapter
	// implements it.
	//
	// Class selectors are NOT forbidden — use them only when the
	// class name is a stable part of the component's public API
	// (e.g. a third-party theme hook), and document why inline.
	locator_text?: {[string]: string}
}

// scenarios is the aggregate across every UI scenario file. CUE
// unifies partial definitions across files in this package.
//
// Scenarios are nested by component area (sidebar, helm, dag, …) so
// generators can produce one test file per area without re-parsing
// every scenario's `component` field.
scenarios: ui: [string]: [...#UIScenario]
