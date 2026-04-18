package scenario

import (
	"path/filepath"
	"runtime"
	"testing"
)

// repoRoot resolves the kitty-kommander repo root by walking up from
// this file's location. internal/scenario/load_test.go → ../..
func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	return filepath.Join(filepath.Dir(file), "..", "..")
}

// TestLoadScenarios verifies the CUE loader reads every scenario we
// expect to be present. If a scenario is added to schema/cli/ but the
// count check here isn't updated, this test fails — a small but real
// guard against silent drops in scenario loading.
func TestLoadScenarios(t *testing.T) {
	scenarios, err := Load(repoRoot(t))
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	expected := map[string]int{
		"launch":      4,
		"doctor":      3,
		"reload":      2,
		"integration": 1,
	}
	for subcmd, want := range expected {
		got := len(scenarios[subcmd])
		if got != want {
			t.Errorf("scenarios[%q] = %d, want %d", subcmd, got, want)
		}
	}

	// Spot-check one scenario field per subcommand to confirm the
	// decode worked on all four — not just that the count matched.
	wantIDs := map[string][]string{
		"launch":      {"cue-config-driven-layout", "launch-basic", "launch-missing-dir", "launch-multi-window-tab"},
		"doctor":      {"doctor-drift-detected", "doctor-healthy", "doctor-healthy-real-titles"},
		"reload":      {"reload-noop", "reload-reconcile"},
		"integration": {"launch-then-doctor-clean"},
	}
	for subcmd, ids := range wantIDs {
		for i, id := range ids {
			if scenarios[subcmd][i].ID != id {
				t.Errorf("scenarios[%q][%d].ID = %q, want %q",
					subcmd, i, scenarios[subcmd][i].ID, id)
			}
		}
	}

	// Every loaded scenario must have non-empty RunModes. The CUE
	// schema enforces this via [_, ...T], the loader re-checks it,
	// and this test pins the invariant from the consumer side: if
	// a future schema refactor reintroduces a default (say, during
	// a "reduce boilerplate" cleanup), this test catches it before
	// the silent-skip hazard reappears.
	for subcmd, scs := range scenarios {
		for _, sc := range scs {
			if len(sc.RunModes) == 0 {
				t.Errorf("scenario %s/%s: RunModes is empty after load",
					subcmd, sc.ID)
			}
		}
	}
}

// TestLoadRejectsEmptyRunModes confirms the loader's belt-and-braces
// check fires when a Scenario struct with empty RunModes reaches the
// post-decode validation loop. The CUE vet layer already rejects this,
// but the loader defends the Go-side boundary for callers who construct
// Scenario values directly (scenariogen tests, future tools).
//
// Strategy: build the minimum Scenario that would otherwise pass (ID,
// invocation, expected are present; RunModes is nil); run it through
// the same validation loop the loader uses. If we ever refactor that
// loop into a method on Scenario, this test pins the behavior.
func TestLoadRejectsEmptyRunModes(t *testing.T) {
	sc := Scenario{
		ID:         "probe",
		Invocation: "kommander launch /tmp/x",
		Expected:   Expected{ExitCode: 0},
		RunModes:   nil,
	}
	err := validateScenario("launch", sc)
	if err == nil {
		t.Fatal("expected error for empty RunModes, got nil")
	}
	if got := err.Error(); !contains(got, "run_modes is empty") {
		t.Errorf("error %q does not mention run_modes", got)
	}
}

func contains(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

// TestValidateScenarioMutex exercises every branch of validateScenario's
// invocation/steps mutex + run_modes presence check. validateScenario
// has three failure conditions; only the RunModes branch had direct
// coverage (TestLoadRejectsEmptyRunModes). Auditor finding #5 on
// b15043a: with three branches and one test, two branches rely on the
// CUE-loaded scenarios to exercise them transitively — a refactor that
// swaps the mutex logic could pass every loader test while breaking
// the error surface. This table pins each branch explicitly.
//
// Shape choices here:
// - baseline Scenario carries valid RunModes so each row isolates the
//   field it's testing (invocation/steps combos don't trip the RunModes
//   check accidentally)
// - positive rows return no error; negative rows return a specific
//   substring in the error message so a future error-message rewrite
//   that drops load-bearing language (e.g. "both ... set" losing the
//   "exclusive" word) is caught here, not at a user report
func TestValidateScenarioMutex(t *testing.T) {
	base := Scenario{
		ID:       "probe",
		Expected: Expected{ExitCode: 0},
		RunModes: []string{"mock"},
	}

	cases := []struct {
		name       string
		sc         Scenario
		wantErr    bool
		errMustHas string
	}{
		{
			name: "invocation-only / valid",
			sc: func() Scenario {
				s := base
				s.Invocation = "kommander launch /tmp/x"
				return s
			}(),
			wantErr: false,
		},
		{
			name: "steps-only / valid",
			sc: func() Scenario {
				s := base
				s.Steps = []Step{{
					Invocation: "kommander launch /tmp/x",
					Expected:   Expected{ExitCode: 0},
				}}
				return s
			}(),
			wantErr: false,
		},
		{
			name:       "neither invocation nor steps / rejected",
			sc:         base,
			wantErr:    true,
			errMustHas: "neither `invocation` nor `steps` set",
		},
		{
			name: "both invocation and steps / rejected",
			sc: func() Scenario {
				s := base
				s.Invocation = "kommander launch /tmp/x"
				s.Steps = []Step{{
					Invocation: "kommander doctor",
					Expected:   Expected{ExitCode: 0},
				}}
				return s
			}(),
			wantErr:    true,
			errMustHas: "mutually exclusive",
		},
		{
			name: "empty run_modes on otherwise-valid scenario / rejected",
			sc: func() Scenario {
				s := base
				s.Invocation = "kommander launch /tmp/x"
				s.RunModes = nil
				return s
			}(),
			wantErr:    true,
			errMustHas: "run_modes is empty",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := validateScenario("launch", tc.sc)
			switch {
			case tc.wantErr && err == nil:
				t.Fatalf("expected error, got nil")
			case !tc.wantErr && err != nil:
				t.Fatalf("unexpected error: %v", err)
			case tc.wantErr && tc.errMustHas != "" && !contains(err.Error(), tc.errMustHas):
				t.Errorf("error %q missing substring %q", err.Error(), tc.errMustHas)
			}
		})
	}
}
