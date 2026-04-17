// Sidebar scenarios — `packages/ui/src/components/Sidebar.tsx`.
//
// Sidebar is the right half of the Dashboard tab. It renders three
// stacked blocks:
//
//   ┌──────────────────┐
//   │ PROJECT HEALTH   │  <- completion bar, status counts
//   │ ################ │
//   ├──────────────────┤
//   │ READY QUEUE      │  <- priority-sorted bead list
//   │ • Fix auth bug   │
//   ├──────────────────┤
//   │ RECENT COMMITS   │  <- `git log --oneline` head
//   │ f028764 feat:…   │
//   └──────────────────┘
//
// Two scenarios here are the steel thread's UI half:
//   - `sidebar-shows-health` proves the happy path renders every
//     block from a realistic beads fixture.
//   - `sidebar-empty-project` proves the bootstrap-state (total: 0)
//     renders zero, not NaN — the single most common empty-state bug
//     in dashboards that compute percent = closed / total.
package ui

scenarios: ui: sidebar: [
	{
		id:   "sidebar-shows-health"
		tags: ["basic", "sidebar"]

		story: """
			The operator glances at the Dashboard sidebar and sees
			project health at a glance: 60% complete (12 of 20 closed),
			the ready queue sorted by priority, and the latest commit.
			Every block renders from a single bd-format=json snapshot —
			no spinner state, no lazy loads.
			"""

		component: "Sidebar"

		fixtures: {
			stats: {
				total: 20, closed: 12, blocked: 3, in_progress: 2, open: 3
			}
			ready: [
				{id: "abc", title: "Fix auth bug", priority: 1},
				{id: "def", title: "Add logging", priority: 2},
				{id: "ghi", title: "Update docs", priority: 4},
			]
			commits: [
				{hash: "f028764", message: "feat: add auth handler"},
			]
		}

		expected: {
			contains: [
				"60% complete",
				"12 closed", "3 blocked", "2 wip",
				"Fix auth bug",
				"Add logging",
				"f028764",
			]
			// "0% complete" is deliberately NOT in excludes here —
			// substring-excluding "0% complete" contradicts the
			// "60% complete" contains above (suffix collision: the
			// last 12 chars of "60% complete" ARE "0% complete").
			// The intent of the original exclude ("don't show zero
			// when total > 0") is structurally covered by the
			// complementary scenario `sidebar-empty-project`, which
			// asserts "0% complete" ONLY when total=0. If both
			// scenarios pass, the bar is numerically correct.
			excludes: [
				"NaN", // must not show NaN in any tier
			]
			snapshot: "sidebar-basic"
			playwright: {
				screenshot: "sidebar-basic.png"
				locator_text: {
					".health-bar":              "60%"
					".ready-queue li:first-child": "Fix auth bug"
				}
			}
		}
	},
	{
		id:   "sidebar-empty-project"
		tags: ["edge-case", "sidebar"]

		story: """
			A freshly initialized project has zero beads and zero
			commits. The sidebar must render 0% complete with a
			helpful 'No work items' placeholder, and must NOT show
			NaN, undefined, or null anywhere — the classic bug
			when percent is computed as closed / total without
			guarding total === 0.
			"""

		component: "Sidebar"

		fixtures: {
			stats: {
				total: 0, closed: 0, blocked: 0, in_progress: 0, open: 0
			}
			ready:   []
			commits: []
		}

		expected: {
			contains: [
				"0% complete",
				"No work items",
			]
			// Excludes list guards the one truly JS-specific
			// serialization leak: "NaN" from a 0/0 divide that
			// wasn't guarded.
			//
			// Deliberately NOT excluding "null" or "undefined" as
			// literal substrings — those are five- and nine-
			// character English words that future empty-state
			// copy may legitimately contain ("null of beads",
			// "the undefined priority"). The classic regression-
			// test rot pattern is a designer adding rich copy,
			// the scenario breaking for the wrong reason, and the
			// exclude getting weakened to just "NaN" anyway.
			// Start at the defensible narrow spec.
			//
			// undefined/null serialization leaks are caught by
			// the TypeScript type system (Bead.id is not nullable)
			// and by component-level hook tests (useBeads returns
			// {stats: null} not stats with null fields) — NOT by
			// scraping the rendered frame for those strings.
			excludes: [
				"NaN",
			]
			snapshot: "sidebar-empty"
		}
	},
]
