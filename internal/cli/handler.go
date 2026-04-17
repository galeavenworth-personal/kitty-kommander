// Package cli holds the subcommand handlers for the `kommander`
// binary. Every handler signature is the same:
//
//	func RunXxx(env *Env) (exitCode int, stdout, stderr string)
//
// This uniform shape lets the generated scenario tests invoke any
// subcommand without branching on type. Handlers do NOT write to
// os.Stdout/os.Stderr directly — they return their output so
// scenario tests can assert on it in-process without capture tricks.
//
// In production, cmd/kommander/main.go wraps the handler: parses
// flags into Env, calls the handler, writes the returned strings to
// the real stdout/stderr, and exits with the returned code.
package cli

import (
	"github.com/galeavenworth-personal/kitty-kommander/internal/kitty"
)

// Env is everything a handler needs. Scenario tests build one from a
// scenario's Setup block; production code builds it from flag args
// and a KittenExec controller.
type Env struct {
	// Args is argv after the subcommand word. E.g. for
	// `kommander launch /home/user/my-app` the subcommand dispatcher
	// strips "launch" and passes ["/home/user/my-app"].
	Args []string

	// Controller is the kitty abstraction. Tests pass a *kitty.Mock;
	// production wires a *kitty.KittenExec.
	Controller kitty.Controller

	// Workdir is the operator's current working directory. Launch
	// uses this if Args is empty. Tests set it to the tmp dir they
	// created for file-system fixtures.
	Workdir string
}

// Handler is the signature every subcommand implements. The exit
// code is the process exit code; stdout / stderr are the strings the
// process would have written.
type Handler func(env *Env) (exitCode int, stdout, stderr string)
