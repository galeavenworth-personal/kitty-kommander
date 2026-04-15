package kommander

// Claude Code launch configuration for kitty-kommander.
// Edit values below, then restart the session to apply.
// If cue is not installed, scripts/launch-claude.sh uses matching defaults.
// Environment variables (CLAUDE_MODEL, CLAUDE_AGENT, CLAUDE_SKIP_PERMISSIONS)
// override everything.

claude: {
	// Model for the driver session.
	model: *"opus" | "sonnet" | "haiku"

	// Agent definition to load.
	agent: *"cell-leader" | string

	// Skip interactive permission prompts.
	// Required for autonomous agent team operation.
	dangerouslySkipPermissions: *true | bool
}
