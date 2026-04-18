package scenario

import (
	"fmt"
	"sort"

	"cuelang.org/go/cue"
	"cuelang.org/go/cue/cuecontext"
	"cuelang.org/go/cue/load"
)

// Load parses every *.cue file in schema/cli/ as a single package
// (via CUE's "./schema/cli" import path) and returns the flattened
// scenarios indexed by subcommand name.
//
// rootDir is the kitty-kommander repo root (where cue.mod lives).
// Callers typically pass the binary's working directory after cd-ing
// into the repo — go generate runs in the package dir, so the
// generator composes the repo root from its own file location.
func Load(rootDir string) (map[string][]Scenario, error) {
	ctx := cuecontext.New()

	cfg := &load.Config{
		Dir:        rootDir,
		ModuleRoot: rootDir,
		Package:    "cli",
	}
	instances := load.Instances([]string{"./schema/cli"}, cfg)
	if len(instances) != 1 {
		return nil, fmt.Errorf("expected 1 CUE instance, got %d", len(instances))
	}
	inst := instances[0]
	if inst.Err != nil {
		return nil, fmt.Errorf("cue load: %w", inst.Err)
	}

	val := ctx.BuildInstance(inst)
	if err := val.Err(); err != nil {
		return nil, fmt.Errorf("cue build: %w", err)
	}
	if err := val.Validate(cue.Concrete(true)); err != nil {
		return nil, fmt.Errorf("cue validate: %w", err)
	}

	scenariosVal := val.LookupPath(cue.ParsePath("scenarios"))
	if err := scenariosVal.Err(); err != nil {
		return nil, fmt.Errorf("lookup scenarios: %w", err)
	}

	result := map[string][]Scenario{}

	it, err := scenariosVal.Fields()
	if err != nil {
		return nil, fmt.Errorf("iterate scenarios: %w", err)
	}
	for it.Next() {
		subcmd := it.Selector().String()
		listVal := it.Value()
		var scs []Scenario
		if err := listVal.Decode(&scs); err != nil {
			return nil, fmt.Errorf("decode %q: %w", subcmd, err)
		}
		// Normalize cmd fields: the CUE schema accepts cmd as either
		// string or []string. Go decode fills []string cleanly when
		// the source is a list, and leaves the single-string case
		// packed into a 1-element slice via a separate code path.
		// CUE's Decode lifts scalar-or-list into []string when the
		// Go target is []string (cuelang.org/go handles the union
		// implicitly for us). No post-processing needed in practice.
		result[subcmd] = scs
	}

	// Deterministic test ordering: sort by ID within each subcmd.
	for k := range result {
		sort.SliceStable(result[k], func(i, j int) bool {
			return result[k][i].ID < result[k][j].ID
		})
	}

	// Enforce cross-field invariants CUE cannot express cleanly. The
	// #Scenario shape lets `invocation` default to "" so `steps`-
	// shaped scenarios can omit it; this check catches the misuses
	// CUE permits: both empty (nothing to execute) or both set
	// (ambiguous — is the top-level invocation step 0, or a separate
	// thing?). The mutex lives here rather than as a CUE disjunction
	// to keep #Scenario unified across files; see schema/cli/types.cue
	// `steps` docstring for the trade-off.
	for subcmd, scs := range result {
		for _, sc := range scs {
			hasInv := sc.Invocation != ""
			hasSteps := len(sc.Steps) > 0
			switch {
			case !hasInv && !hasSteps:
				return nil, fmt.Errorf(
					"scenario %s/%s: neither `invocation` nor `steps` set — at least one is required",
					subcmd, sc.ID)
			case hasInv && hasSteps:
				return nil, fmt.Errorf(
					"scenario %s/%s: both `invocation` and `steps` set — mutually exclusive (steps chain requires omitting top-level invocation)",
					subcmd, sc.ID)
			}
		}
	}

	return result, nil
}
