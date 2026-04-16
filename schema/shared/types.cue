// Package shared holds types used by both the CLI scenario suite
// (schema/cli) and the UI scenario suite (packages/ui/schema). The
// one type here is #BeadsFixture — beads state used as setup for CLI
// scenarios (via #Setup.beads_state) and as the entire world for UI
// scenarios (via #UIScenario.fixtures).
//
// Keeping a single source of truth means a ReadyQueue rendered in the
// Sidebar uses the same fixture shape as a `doctor` scenario that cares
// about ready-queue content, so the two sides can't drift.
package shared

// BeadsFixture mirrors the JSON envelope that `bd --format=json` returns
// across the subcommands kommander actually shells to:
//   - bd stats          → stats
//   - bd ready -n 100   → ready
//   - bd blocked        → blocked
//   - git log --oneline → commits (kept next to beads for Dashboard)
//   - bd log            → mutations (audit trail)
//   - ~/.claude/teams/  → agents (roster via config.json reads)
//   - cell federation   → cells, gates
//
// All fields optional: a scenario includes only what the component or
// command under test will actually read. Unused fields stay absent so
// the scenario body doubles as a minimal demonstration.
#BeadsFixture: {
	stats?: {
		total:       int
		closed:      int
		blocked:     int
		in_progress: int
		open:        int
	}

	ready?: [...{
		id:       string
		title:    string
		priority: int // 0 = P0/critical … 4 = P4/backlog
	}]

	blocked?: [...{
		id:         string
		title:      string
		blocked_by: string
	}]

	commits?: [...{
		hash:    string
		message: string
	}]

	mutations?: [...{
		time:       string
		id:         string
		transition: string
		actor:      string
	}]

	agents?: [...{
		name:   string
		role:   string
		status: string
		bead?:  string
	}]

	cells?: [...{
		name:       string
		health:     string
		group_type: string // Pounce | Clowder | Glaring | Nuisance
	}]

	gates?: [...{
		id:     string
		source: string
		status: string
	}]
}
