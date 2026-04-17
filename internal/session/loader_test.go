package session

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestLoadDefaultOnly: no project dir, no overlay. The embedded
// default.cue's 4-tab layout is returned verbatim. This is the
// baseline — every other test is a delta on top.
func TestLoadDefaultOnly(t *testing.T) {
	s, overlayPath, err := Load("")
	if err != nil {
		t.Fatalf("Load(\"\") error: %v", err)
	}
	if overlayPath != "" {
		t.Errorf("expected no overlayPath for empty projectDir, got %q", overlayPath)
	}
	wantTitles := []string{"Cockpit", "Driver", "Notebooks", "Dashboard"}
	if len(s.Tabs) != len(wantTitles) {
		t.Fatalf("expected %d tabs, got %d: %+v", len(wantTitles), len(s.Tabs), s.Tabs)
	}
	for i, want := range wantTitles {
		if s.Tabs[i].Title != want {
			t.Errorf("tab[%d].Title: got %q, want %q", i, s.Tabs[i].Title, want)
		}
	}
}

// TestLoadProjectDirNoOverlay: projectDir present but no kommander.cue
// inside. Must fall through to the embedded default silently — missing
// overlay is the common case, not an error.
func TestLoadProjectDirNoOverlay(t *testing.T) {
	dir := t.TempDir()
	s, overlayPath, err := Load(dir)
	if err != nil {
		t.Fatalf("Load(%q) error: %v", dir, err)
	}
	if overlayPath != "" {
		t.Errorf("expected no overlayPath when overlay absent, got %q", overlayPath)
	}
	if len(s.Tabs) != 4 {
		t.Errorf("expected default 4-tab layout, got %d tabs", len(s.Tabs))
	}
}

// TestLoadOverlayReplacesTabs: overlay present with session.tabs.
// Simplest-replace semantics: overlay's tabs FULLY replace the default,
// no merge. This is the cue-config-driven-layout scenario's contract.
func TestLoadOverlayReplacesTabs(t *testing.T) {
	dir := t.TempDir()
	overlay := `package kommander

session: tabs: [
    {title: "Custom", windows: [{cmd: ["my-agent"]}]},
    {title: "Worker", windows: [{cmd: ["worker-process"]}]},
]
`
	if err := os.WriteFile(filepath.Join(dir, ConfigFilename), []byte(overlay), 0o644); err != nil {
		t.Fatalf("write overlay: %v", err)
	}
	s, overlayPath, err := Load(dir)
	if err != nil {
		t.Fatalf("Load error: %v", err)
	}
	if overlayPath != ConfigFilename {
		t.Errorf("overlayPath: got %q, want %q", overlayPath, ConfigFilename)
	}
	if len(s.Tabs) != 2 {
		t.Fatalf("overlay must replace tabs; got %d, want 2: %+v", len(s.Tabs), s.Tabs)
	}
	if s.Tabs[0].Title != "Custom" || s.Tabs[1].Title != "Worker" {
		t.Errorf("tab titles: got [%q %q], want [Custom Worker]",
			s.Tabs[0].Title, s.Tabs[1].Title)
	}
	// No leaking default titles.
	for _, t0 := range s.Tabs {
		switch t0.Title {
		case "Cockpit", "Driver", "Notebooks", "Dashboard":
			t.Errorf("default tab title %q leaked into overlay result", t0.Title)
		}
	}
	// Window cmd shape preserved through decode.
	if len(s.Tabs[0].Windows) != 1 || len(s.Tabs[0].Windows[0].Cmd) != 1 ||
		s.Tabs[0].Windows[0].Cmd[0] != "my-agent" {
		t.Errorf("Custom.Windows[0].Cmd: got %+v, want [my-agent]", s.Tabs[0].Windows)
	}
}

// TestLoadOverlayWithoutTabsFallsBack: overlay present but doesn't set
// session.tabs. Default wins. Future fields (beyond tabs) can be set
// by the overlay; omitting tabs keeps the default layout.
func TestLoadOverlayWithoutTabsFallsBack(t *testing.T) {
	dir := t.TempDir()
	overlay := `package kommander

// Overlay with no session.tabs — unrelated field set.
other_config: "example"
`
	if err := os.WriteFile(filepath.Join(dir, ConfigFilename), []byte(overlay), 0o644); err != nil {
		t.Fatalf("write overlay: %v", err)
	}
	s, overlayPath, err := Load(dir)
	if err != nil {
		t.Fatalf("Load error: %v", err)
	}
	// Overlay was present AND loaded — overlayPath reports it regardless
	// of whether session.tabs existed, so a future "overlay present but
	// ignored" signal is available if ever needed. Currently callers
	// that care only check "is overlayPath non-empty".
	if overlayPath != ConfigFilename {
		t.Errorf("overlayPath: got %q, want %q", overlayPath, ConfigFilename)
	}
	if len(s.Tabs) != 4 {
		t.Errorf("expected default 4-tab layout when overlay omits tabs, got %d", len(s.Tabs))
	}
}

// TestLoadOverlayInvalidSyntax: a broken overlay must return an error,
// not silently fall back to default. A user who wrote a bad overlay
// expects a loud failure — falling back would mask their typo.
func TestLoadOverlayInvalidSyntax(t *testing.T) {
	dir := t.TempDir()
	overlay := `package kommander

session: tabs: [
    {title: "Broken" unterminated
`
	if err := os.WriteFile(filepath.Join(dir, ConfigFilename), []byte(overlay), 0o644); err != nil {
		t.Fatalf("write overlay: %v", err)
	}
	_, _, err := Load(dir)
	if err == nil {
		t.Fatalf("expected error for invalid overlay, got nil")
	}
	if !strings.Contains(err.Error(), "overlay") {
		t.Errorf("error should mention overlay; got: %v", err)
	}
}

// TestEmbeddedSchemaMatchesSource: guards against the internal/session/
// embed copy drifting from schema/session/ (the authoritative source).
// If you updated one and not the other, this fails loudly. Run
// `go generate ./internal/session/` to re-sync.
func TestEmbeddedSchemaMatchesSource(t *testing.T) {
	for _, name := range []string{"types.cue", "default.cue"} {
		embedded, err := schemaFS.ReadFile("schema/" + name)
		if err != nil {
			t.Fatalf("embed read %s: %v", name, err)
		}
		// Walk up to repo root (where cue.mod sits).
		src, err := readFromRepoRoot(t, "schema/session/"+name)
		if err != nil {
			t.Fatalf("repo read %s: %v", name, err)
		}
		if string(embedded) != string(src) {
			t.Errorf("schema drift: internal/session/schema/%s differs from schema/session/%s.\nRun: go generate ./internal/session/", name, name)
		}
	}
}

// readFromRepoRoot walks up from the test's CWD (which is the package
// dir) until cue.mod appears, then reads rel relative to that root.
func readFromRepoRoot(t *testing.T, rel string) ([]byte, error) {
	t.Helper()
	d, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	for {
		if _, err := os.Stat(filepath.Join(d, "cue.mod")); err == nil {
			return os.ReadFile(filepath.Join(d, rel))
		}
		parent := filepath.Dir(d)
		if parent == d {
			return nil, os.ErrNotExist
		}
		d = parent
	}
}
