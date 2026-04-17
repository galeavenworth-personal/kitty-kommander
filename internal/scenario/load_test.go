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
		"launch": 4,
		"doctor": 2,
		"reload": 2,
	}
	for subcmd, want := range expected {
		got := len(scenarios[subcmd])
		if got != want {
			t.Errorf("scenarios[%q] = %d, want %d", subcmd, got, want)
		}
	}

	// Spot-check one scenario field per subcommand to confirm the
	// decode worked on all three — not just that the count matched.
	wantIDs := map[string][]string{
		"launch": {"cue-config-driven-layout", "launch-basic", "launch-missing-dir", "launch-multi-window-tab"},
		"doctor": {"doctor-drift-detected", "doctor-healthy"},
		"reload": {"reload-noop", "reload-reconcile"},
	}
	for subcmd, ids := range wantIDs {
		for i, id := range ids {
			if scenarios[subcmd][i].ID != id {
				t.Errorf("scenarios[%q][%d].ID = %q, want %q",
					subcmd, i, scenarios[subcmd][i].ID, id)
			}
		}
	}
}
