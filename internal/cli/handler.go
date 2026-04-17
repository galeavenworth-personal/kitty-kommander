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
	// strips "launch" and passes ["/home/user/my-app"]. Flags like
	// --attach are consumed by main BEFORE Args is populated here, so
	// handlers see a flag-free positional-arg list.
	Args []string

	// Controller is the kitty abstraction. Tests pass a *kitty.Mock;
	// production wires a *kitty.KittenExec.
	Controller kitty.Controller

	// Workdir is the operator's current working directory. Launch
	// uses this if Args is empty. Tests set it to the tmp dir they
	// created for file-system fixtures.
	Workdir string

	// Socket is the actual kitty socket the Controller is bound to, in
	// `unix:/path` form. main populates it from the slug (spawn mode)
	// OR $KITTY_LISTEN_ON (attach mode) so RunLaunch prints the TRUE
	// socket, not one recomputed from the positional dir — which would
	// diverge from the controller's real target in attach mode. Empty
	// in scenario tests; launch.go falls back to the slug-derived path
	// so launch-basic's stdout_contains continues to pass.
	Socket string

	// Mode is "spawn" (fresh kitty started by main) or "attach"
	// (controller bound to an existing $KITTY_LISTEN_ON via --attach).
	// Empty in scenario tests — mock runs are implicitly spawn-like;
	// launch.go omits the mode line when Mode is empty so the
	// launch-basic mock scenario's stdout_contains remains stable.
	Mode string
}

// Handler is the signature every subcommand implements. The exit
// code is the process exit code; stdout / stderr are the strings the
// process would have written.
type Handler func(env *Env) (exitCode int, stdout, stderr string)
