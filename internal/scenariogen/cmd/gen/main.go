// Command gen is the entry point for `go generate ./internal/cli/`.
// It resolves the repo root (walking up from cwd until cue.mod is
// found) and emits *_gen_test.go files for every subcommand.
package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/galeavenworth-personal/kitty-kommander/internal/scenariogen"
)

func main() {
	root, err := findRepoRoot()
	if err != nil {
		log.Fatalf("find repo root: %v", err)
	}
	outDir := filepath.Join(root, "internal", "cli")
	if err := scenariogen.Generate(root, outDir); err != nil {
		log.Fatalf("generate: %v", err)
	}
	fmt.Printf("scenariogen: wrote generated tests to %s\n", outDir)
}

func findRepoRoot() (string, error) {
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
			return "", fmt.Errorf("cue.mod not found walking up from %s", d)
		}
		d = parent
	}
}
