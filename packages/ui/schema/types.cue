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

// UIScenario specifies one render case for one component. The same
// scenario body must satisfy both the TUI and web tiers — if the
// fixtures can only render correctly in one target, the scenario is
// lying about the component.
#UIScenario: {
	// Lowercase-with-dashes; becomes the TUI test name, the
	// Playwright test name, and the golden-file basename.
	id: string & =~"^[a-z][a-z0-9-]*$"

	// Classification. Conventions match the CLI side:
	//   "basic"      — first scenario per component
	//   "common"     — frequent non-trivial state
	//   "edge-case"  — empty, zero, nil — these must NOT crash
	//   "error"      — explicit failure surface
	tags: [...string]

	// The user story. "The operator glances at the Dashboard and
	// sees …" Drives the scenario's content and the test's docstring.
	story: string

	// The React component under test, matching the filename in
	// packages/ui/src/components/ (without extension). Generators
	// use this to import the right module.
	component: string

	// The world the component renders. Same shape the production
	// hooks (useBeads, useGitLog, useCells, …) return, so the
	// component doesn't need a separate fixture-adapter.
	fixtures: shared.#BeadsFixture

	// What the rendered output must (and must not) contain, plus
	// snapshot and Playwright assertions for the three tiers.
	expected: #UIExpected
}

// UIExpected bundles every tier's assertions into one block.
//
// - contains / excludes are checked in BOTH tiers (TUI lastFrame
//   string match, web Playwright page text match).
// - snapshot is the ink-testing-library golden file basename
//   (stored at packages/ui/test/tui/__snapshots__/<snapshot>.txt).
// - playwright is the web-tier block (golden screenshot +
//   locator_text mapping).
//
// A scenario can set `snapshot` without `playwright` (hook or pure-
// logic component) but every visible-surface scenario should set
// both, so tiers 2 and 3 cross-check each other.
#UIExpected: {
	contains: [...string]
	excludes: [...string]
	snapshot?:   string
	playwright?: #PlaywrightAssertion
}

// PlaywrightAssertion drives the web tier of the test generator.
// Both fields are optional so a scenario can pick: golden screenshot
// only, locator assertions only, or both. Most real scenarios want
// both — locators catch semantic regressions, screenshots catch
// layout regressions.
#PlaywrightAssertion: {
	// Filename stored under packages/ui/test/web/screenshots/.
	// Compared pixel-wise with a tolerance that matches Playwright
	// defaults (suggest 0.1 maxDiffPixelRatio for text-heavy UI).
	screenshot?: string

	// CSS selector → expected visible text. The generator produces
	// `await expect(page.locator(sel)).toHaveText(text)` per entry.
	locator_text?: {[string]: string}
}

// scenarios is the aggregate across every UI scenario file. CUE
// unifies partial definitions across files in this package.
//
// Scenarios are nested by component area (sidebar, helm, dag, …) so
// generators can produce one test file per area without re-parsing
// every scenario's `component` field.
scenarios: ui: [string]: [...#UIScenario]
