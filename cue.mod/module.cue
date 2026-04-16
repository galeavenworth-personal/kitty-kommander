// CUE module for kitty-kommander v2.
//
// The schema directory trees (`schema/` for CLI, `packages/ui/schema/` for UI)
// share a single `#BeadsFixture` type via `schema/shared`. Both CLI and UI
// scenarios drive test generation, help-text compilation, and documentation
// for the kommander binary and kommander-ui React package.
module: "github.com/galeavenworth-personal/kitty-kommander"

language: {
	version: "v0.9.0"
}
