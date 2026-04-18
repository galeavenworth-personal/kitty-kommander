//go:build integration

package cli

import (
	"testing"

	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// RunIntegrationScenario runs a single integration-tier scenario against
// a fresh live kitty instance.
//
// RED-COMMIT STUB: unimplemented. The generated integration_gen_test.go
// calls this function; the test fails with the below t.Fatal message
// until the green commit lands the real-mode runner.
//
// Green-commit contract (see uib.3.F):
//   - Skip cleanly when `kitty` is not on PATH (RequireKitty helper).
//   - Spawn kitty on per-test isolated socket via kitty.SpawnKitty +
//     kitty.WaitForSocket.
//   - Bind a production KittenExec controller to that socket.
//   - Execute sc.Steps in order against a shared Env.
//   - Per-step assertions: exit_code, stdout/stderr contains/excludes,
//     json_paths apply to THAT step's handler output.
//   - kitty_effects [{kind:"no_change"}] under real-kitty asserts
//     pre-step and post-step `kitten @ ls` snapshots are equal.
//   - Post-chain: compare live `kitten @ ls` to
//     sc.Expected.FinalKittyState.
//   - Teardown via t.Cleanup: SIGTERM kitty, remove socket file.
//
// Until then, this stub ensures: (a) the generated integration test
// file compiles under -tags=integration, (b) the scenario fails with
// a specific, grep-able reason, and (c) the mock-path test suite
// under plain `go test ./...` is unaffected (the build tag keeps this
// file out of the default build).
func RunIntegrationScenario(t *testing.T, sc scenario.Scenario) {
	t.Helper()
	t.Fatalf("real_kitty mode not implemented: scenario %q awaits green commit (uib.3.F)", sc.ID)
}
