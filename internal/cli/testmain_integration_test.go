//go:build integration

package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

// pkgMainBinary is the path to the kommander binary TestMain compiles
// for this package's integration test pass. Empty when compilation
// failed; RunIntegrationScenario checks for that and fails with a
// diagnostic rather than returning a confusing "no such file" error
// from the subprocess.
//
// Shared across every subtest in the package so the 10-15 seconds of
// `go build` cost amortizes across the scenario count. The binary
// file is cleaned up by t.Cleanup registered in TestMain.
var pkgMainBinary string

// TestMain compiles cmd/kommander once per test invocation and stores
// the path in pkgMainBinary. Every integration subtest shells out to
// this binary instead of dispatching handlers in-process — D2 per the
// uib.3.F green-commit arbitration.
//
// Why subprocess instead of handler dispatch: the generated test runs
// the SAME binary path contributors type on the command line, so
// production-only code (os.Exit, main.go's buildController, initial-
// tab-close plumbing, cleanupOrphan wiring) is on the tested path.
// A handler-dispatch runner would skip all of main.go and quietly
// regress that surface under a refactor.
//
// Why TestMain instead of per-test `go build`: build cost is ~10-15
// seconds; amortizing over N scenarios keeps the loop fast.
func TestMain(m *testing.M) {
	bin, cleanup, err := buildKommanderBinary()
	if err != nil {
		fmt.Fprintf(os.Stderr, "TestMain: build kommander: %v\n", err)
		// Leave pkgMainBinary empty; RunIntegrationScenario produces
		// a specific diagnostic instead of the opaque "file not
		// found" that a bad bin path would yield on subprocess run.
		code := m.Run()
		os.Exit(code)
	}
	pkgMainBinary = bin
	code := m.Run()
	cleanup()
	os.Exit(code)
}

// buildKommanderBinary runs `go build` on cmd/kommander into a temp
// dir and returns the resulting binary path plus a cleanup function.
// The binary inherits the test's build env (PATH, GOCACHE, module
// mode) so it sees the same Go toolchain configuration the developer
// or CI invoked `go test` under.
func buildKommanderBinary() (string, func(), error) {
	tmp, err := os.MkdirTemp("", "kommander-integration-*")
	if err != nil {
		return "", nil, fmt.Errorf("mkdir temp: %w", err)
	}
	bin := filepath.Join(tmp, "kommander")
	cmd := exec.Command("go", "build", "-o", bin, "./cmd/kommander")
	// cd to repo root (two levels up from internal/cli) so `go build`
	// resolves the ./cmd/kommander relative path correctly regardless
	// of where `go test` was invoked from.
	root, rerr := findRepoRootFromTest()
	if rerr != nil {
		os.RemoveAll(tmp)
		return "", nil, fmt.Errorf("find repo root: %w", rerr)
	}
	cmd.Dir = root
	out, err := cmd.CombinedOutput()
	if err != nil {
		os.RemoveAll(tmp)
		return "", nil, fmt.Errorf("go build: %w\n%s", err, out)
	}
	return bin, func() { os.RemoveAll(tmp) }, nil
}

// findRepoRootFromTest walks upward from the test's working directory
// (which go test sets to the package directory, internal/cli) until
// cue.mod is found. Mirrors cmd/kommander/main.go's findRepoRoot but
// rooted at os.Getwd rather than receiving a caller-provided path.
func findRepoRootFromTest() (string, error) {
	d, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(d, "cue.mod")); err == nil {
			return d, nil
		}
		parent := filepath.Dir(d)
		if parent == d {
			return "", fmt.Errorf("cue.mod not found above %s", d)
		}
		d = parent
	}
}
