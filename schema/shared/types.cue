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

// BeadsFixture is the POST-PROJECTION view the components and CLI
// subcommands consume — NOT the raw `bd --format=json` envelope.
//
// The `useBeads` hook (packages/ui/src/hooks/useBeads.ts, STACK-v2.md
// Layer 3) and the Go beads.Client wrapper own the translation from
// wire shape to this shape. Concretely:
//
//   Wire:    {"summary": {"total_issues": 228, "closed_issues": 202, ...}}
//   Fixture: {stats: {total: 228, closed: 202, ...}}
//
//   Wire:    bd ready returns full issue objects with description,
//            status, dependencies[], parent, etc.
//   Fixture: ready: [{id, title, priority}] — the projection the
//            ReadyQueue component actually renders.
//
// This is a DECISION, not an oversight: scenarios describe what the
// Sidebar sees, not what `bd` emits. A hook-level test (test/hooks/)
// is the right place to verify the wire→projection translation.
//
// Implication for uib.2: the useBeads hook is responsible for
// projecting bd's envelope into this shape. A component author who
// reads this type gets the contract directly; they don't need to
// care that `bd stats` wraps things in a `summary` key.
//
// All fields optional — a scenario includes only the projection slice
// its subject reads, so the scenario body doubles as minimal demo.
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
