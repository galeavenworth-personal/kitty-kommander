package cli

// go:generate directive: regenerate *_gen_test.go from schema/cli/*.cue.
// Invoke with: go generate ./internal/cli/
//
// Keeping the directive in a non-test file so `go generate ./...`
// picks it up without -tags test gymnastics.
//
//go:generate go run ../scenariogen/cmd/gen
