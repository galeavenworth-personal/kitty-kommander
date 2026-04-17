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
