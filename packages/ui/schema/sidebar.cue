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
// Three scenarios here are the steel thread's UI half:
//   - `sidebar-shows-health` proves the happy path renders every
//     block from a realistic beads fixture (fixture mode).
//   - `sidebar-empty-project` proves the bootstrap-state (total: 0)
//     renders zero, not NaN — the single most common empty-state bug
//     in dashboards that compute percent = closed / total (fixture mode).
//   - `sidebar-reads-real-beads-state` proves the PRODUCTION data
//     path: useBeads shells bd + git log, polls every 30s, and the
//     entry stays alive. This is the 3.E scenario; catches the 3.D
//     regression where the Dashboard tab died on first paint
//     (production mode).
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
				// Per schema/ui/types.cue:112-122 — locator keys SHOULD be
				// [data-testid="..."] attribute selectors, not class names.
				// Class selectors couple the scenario to styling decisions;
				// a CSS rename breaks the test without the feature breaking.
				locator_text: {
					"[data-testid=\"health-bar\"]":                      "60%"
					"[data-testid=\"ready-queue\"] li:first-child": "Fix auth bug"
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
	{
		id:   "sidebar-reads-real-beads-state"
		tags: ["production", "sidebar"]

		story: """
			The operator launches `kommander-ui --sidebar` under the
			cockpit Dashboard tab. useBeads shells the three data
			sources on mount (bd stats for project health, bd ready
			for the queue, git log for recent commits), then re-shells
			every 30 seconds so the sidebar reflects work as agents
			close beads. The process stays alive between polls — the
			3.D regression was renderSidebar() returning synchronously,
			killing the Dashboard tab on first paint.
			"""

		// Production-mode scenarios name the subject hook (or entry)
		// in `component` — no separate `hook` field on the assertion.
		// See types.cue commentary on why the duplication was dropped.
		component:   "useBeads"
		render_mode: "production"

		production: {
			// args_contains (substring match) rather than exact args:
			// the scenario asserts INTENT ("useBeads shells bd for
			// the ready queue"), not IMPLEMENTATION ("uses exactly
			// these flags in this order"). A future refactor that
			// swaps `bd --format=json stats` for `bd stats --json`
			// — same intent, different arg order — should not break
			// this scenario. The substring floor ("ready", "stats",
			// "log") is the narrowest observable that distinguishes
			// the three calls from each other.
			shells: [
				{command: "bd", args_contains:  ["stats"]},
				{command: "bd", args_contains:  ["ready"]},
				{command: "git", args_contains: ["log"]},
			]

			// 30s matches scripts/cockpit_dash.py:465 (sleep(30)) —
			// the cockpit dashboard's established polling floor. Not
			// 10s (would hammer bd on large projects), not 60s (stale
			// enough that an operator closing a bead wouldn't see it
			// reflected before task-switching back). Keep the two
			// polling surfaces (python cockpit, react sidebar) aligned
			// so operators develop one mental model of refresh cadence.
			polling: {
				interval_seconds: 30
			}

			// Catches the 3.D regression directly: ink.tsx's
			// renderSidebar() must not return synchronously. The
			// setInterval inside useBeads' useEffect is what keeps
			// the event loop busy; this flag is how the scenario
			// asserts that invariant without coupling to the
			// specific mechanism (interval vs. stdin subscription
			// vs. explicit ink waitUntilExit).
			stays_alive: true
		}
	},
]
