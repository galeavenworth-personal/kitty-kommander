// Package session loads the desired kitty session layout from CUE.
//
// The default layout (schema/session/default.cue + types.cue) is
// embedded into the binary at compile time. Per-project overlays at
// <dir>/kommander.cue are loaded at runtime. The loader unifies them
// with simplest-replace semantics: when the overlay provides
// session.tabs, the overlay's tabs FULLY REPLACE the default tabs;
// otherwise the default tabs win.
//
// This is the scenarios-before-code implementation of
// cue-config-driven-layout. The test contract is in
// schema/cli/launch.cue; the run harness is internal/cli/runner.go.
//
// Design arbitration points (decided with the leader before implementation):
//   - Loader location: internal/session/ (session schema is its own domain).
//   - Default source: go:embed (self-contained binary, overlay is the
//     supported customization surface).
//   - Overlay semantics: simplest-replace. Done in Go, not via CUE list
//     unification — CUE lists don't merge cleanly on title-identity, so
//     "whole-list swap when overlay sets it" is the minimum that matches
//     the contract.
//   - Discovery: project-root <dir>/kommander.cue only (no env var, no flag).
package session

import (
	"embed"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"

	"cuelang.org/go/cue"
	"cuelang.org/go/cue/cuecontext"
	"cuelang.org/go/cue/load"
)

// schemaFS embeds a copy of schema/session/*.cue at compile time.
// The authoritative files live at the repo's top-level schema/session/
// directory — those are what operators read and what the leader
// edits. The copy under internal/session/schema/ exists because
// go:embed does not accept paths outside the package directory
// (and does not follow symlinks). Drift between the two is guarded
// by TestEmbeddedSchemaMatchesSource in loader_test.go.
//
// If you change schema/session/*.cue, run `go generate ./internal/session/`
// to refresh the embed copy. The generate directive below makes this
// a one-command sync.
//
//go:generate cp ../../schema/session/types.cue schema/types.cue
//go:generate cp ../../schema/session/default.cue schema/default.cue
//
//go:embed schema/types.cue schema/default.cue
var schemaFS embed.FS

// ConfigFilename is the name the loader looks for in the project
// directory. Kept as a package-level const so tests and callers
// (and a future --config flag) reference one source.
const ConfigFilename = "kommander.cue"

// Session is the resolved desired state after default+overlay unification.
// Slug and Socket remain empty — those are runtime-derived from the
// project directory at launch; the loader's job is tabs only.
type Session struct {
	Tabs []Tab
}

// Tab mirrors schema/session/types.cue #Tab. Fields that the Go side
// currently uses are surfaced; Layout is kept for forward-compat with
// tab layout scenarios that land in later subtasks.
type Tab struct {
	Title   string
	Layout  string
	Windows []Window
	Dynamic bool
}

// Window mirrors schema/session/types.cue #Window. Cmd is normalized
// to []string regardless of the string|[...string] form in source CUE.
type Window struct {
	Title    string
	Cmd      []string
	Location string
	Env      map[string]string
	Ink      bool
}

// Load returns the unified desired session. projectDir is the positional
// <dir> arg passed to `kommander launch`; it is read for a sibling
// kommander.cue overlay. If projectDir is empty, only the default is
// returned (no overlay lookup). An empty string for overlayPath in the
// result means "no overlay found or loaded" — callers can condition
// stdout hints on it.
//
// Errors returned by Load indicate a genuine problem: embedded schema
// corruption (impossible in a clean build), overlay present but syntactically
// broken, or overlay unify failure. A missing overlay is NOT an error;
// it is the normal path for projects that accept the default layout.
func Load(projectDir string) (s Session, overlayPath string, err error) {
	ctx := cuecontext.New()

	def, err := loadDefault(ctx)
	if err != nil {
		return Session{}, "", fmt.Errorf("session: load default: %w", err)
	}

	if projectDir == "" {
		return def, "", nil
	}

	overlayFile := filepath.Join(projectDir, ConfigFilename)
	overlayBytes, readErr := os.ReadFile(overlayFile)
	if errors.Is(readErr, fs.ErrNotExist) {
		return def, "", nil
	}
	if readErr != nil {
		return Session{}, "", fmt.Errorf("session: read overlay %s: %w", overlayFile, readErr)
	}

	applied, err := applyOverlay(ctx, def, overlayBytes)
	if err != nil {
		return Session{}, "", fmt.Errorf("session: apply overlay %s: %w", overlayFile, err)
	}
	return applied, ConfigFilename, nil
}

// loadDefault parses the embedded schema/session/ package into a
// Session. Both types.cue and default.cue share `package session`,
// so they must load as one package — CompileBytes won't accept a
// concatenated buffer (duplicate package decl). We use load.Instances
// with an in-memory overlay mapping virtual paths to the embedded
// bytes; CUE's loader treats them as a single package exactly like a
// directory-based load would.
func loadDefault(ctx *cue.Context) (Session, error) {
	typesSrc, err := schemaFS.ReadFile("schema/types.cue")
	if err != nil {
		return Session{}, fmt.Errorf("read embed types.cue: %w", err)
	}
	defaultSrc, err := schemaFS.ReadFile("schema/default.cue")
	if err != nil {
		return Session{}, fmt.Errorf("read embed default.cue: %w", err)
	}

	// Virtual filesystem rooted at /session. load.Instances with
	// Overlay sidesteps the actual filesystem entirely — the binary
	// needs no access to schema/session/ at runtime. Paths in the
	// overlay map are absolute so load's resolver matches them.
	const root = "/session"
	overlay := map[string]load.Source{
		filepath.Join(root, "types.cue"):   load.FromBytes(typesSrc),
		filepath.Join(root, "default.cue"): load.FromBytes(defaultSrc),
	}
	cfg := &load.Config{
		Dir:        root,
		ModuleRoot: root,
		Package:    "session",
		Overlay:    overlay,
	}
	instances := load.Instances([]string{"."}, cfg)
	if len(instances) != 1 {
		return Session{}, fmt.Errorf("embed load: expected 1 instance, got %d", len(instances))
	}
	inst := instances[0]
	if inst.Err != nil {
		return Session{}, fmt.Errorf("embed load: %w", inst.Err)
	}
	val := ctx.BuildInstance(inst)
	if err := val.Err(); err != nil {
		return Session{}, fmt.Errorf("embed build: %w", err)
	}

	defaultVal := val.LookupPath(cue.ParsePath("default"))
	if err := defaultVal.Err(); err != nil {
		return Session{}, fmt.Errorf("lookup default: %w", err)
	}
	return decodeSession(defaultVal)
}

// applyOverlay returns a Session whose tabs come from the overlay IF
// the overlay sets session.tabs, otherwise from the default. Simplest-
// replace semantics: no per-tab keyed merge, no element-wise CUE unify.
// The Go-side swap is deliberate — CUE's list unification has identity
// requirements that don't hold on a title-keyed list, and "whole list
// or none" is exactly what the cue-config-driven-layout scenario asserts.
func applyOverlay(ctx *cue.Context, def Session, overlayBytes []byte) (Session, error) {
	overlayVal := ctx.CompileBytes(overlayBytes, cue.Filename(ConfigFilename))
	if err := overlayVal.Err(); err != nil {
		return Session{}, fmt.Errorf("compile overlay: %w", err)
	}

	tabsVal := overlayVal.LookupPath(cue.ParsePath("session.tabs"))
	if !tabsVal.Exists() {
		return def, nil
	}
	if err := tabsVal.Err(); err != nil {
		return Session{}, fmt.Errorf("overlay session.tabs: %w", err)
	}

	tabs, err := decodeTabs(tabsVal)
	if err != nil {
		return Session{}, fmt.Errorf("decode overlay tabs: %w", err)
	}
	return Session{Tabs: tabs}, nil
}

// decodeSession walks a CUE value shaped like #Session and emits the
// Go Session. Window.Cmd handles both the string and []string forms
// via the union resolver below; the rest is straight Decode.
func decodeSession(v cue.Value) (Session, error) {
	tabsVal := v.LookupPath(cue.ParsePath("tabs"))
	if !tabsVal.Exists() {
		return Session{}, nil
	}
	tabs, err := decodeTabs(tabsVal)
	if err != nil {
		return Session{}, err
	}
	return Session{Tabs: tabs}, nil
}

// decodeTabs decodes a CUE list of #Tab into []Tab. Iterates element-
// wise rather than using cue.Decode(&[]Tab{}) because each #Window.cmd
// is a string|[...string] union that decodeCmd resolves explicitly.
func decodeTabs(listVal cue.Value) ([]Tab, error) {
	it, err := listVal.List()
	if err != nil {
		return nil, fmt.Errorf("tabs not a list: %w", err)
	}
	var out []Tab
	for it.Next() {
		tv := it.Value()
		t := Tab{}
		if v := tv.LookupPath(cue.ParsePath("title")); v.Exists() {
			if s, err := v.String(); err == nil {
				t.Title = s
			}
		}
		if v := tv.LookupPath(cue.ParsePath("layout")); v.Exists() {
			if s, err := v.String(); err == nil {
				t.Layout = s
			}
		}
		if v := tv.LookupPath(cue.ParsePath("dynamic")); v.Exists() {
			if b, err := v.Bool(); err == nil {
				t.Dynamic = b
			}
		}
		wv := tv.LookupPath(cue.ParsePath("windows"))
		if wv.Exists() {
			wins, err := decodeWindows(wv)
			if err != nil {
				return nil, fmt.Errorf("tab %q windows: %w", t.Title, err)
			}
			t.Windows = wins
		}
		out = append(out, t)
	}
	return out, nil
}

// decodeWindows decodes a CUE list of #Window into []Window.
func decodeWindows(listVal cue.Value) ([]Window, error) {
	it, err := listVal.List()
	if err != nil {
		return nil, fmt.Errorf("windows not a list: %w", err)
	}
	var out []Window
	for it.Next() {
		wv := it.Value()
		w := Window{}
		if v := wv.LookupPath(cue.ParsePath("title")); v.Exists() {
			if s, err := v.String(); err == nil {
				w.Title = s
			}
		}
		if v := wv.LookupPath(cue.ParsePath("location")); v.Exists() {
			if s, err := v.String(); err == nil {
				w.Location = s
			}
		}
		if v := wv.LookupPath(cue.ParsePath("ink")); v.Exists() {
			if b, err := v.Bool(); err == nil {
				w.Ink = b
			}
		}
		if v := wv.LookupPath(cue.ParsePath("env")); v.Exists() {
			env := map[string]string{}
			if err := v.Decode(&env); err == nil && len(env) > 0 {
				w.Env = env
			}
		}
		cmdVal := wv.LookupPath(cue.ParsePath("cmd"))
		if cmdVal.Exists() {
			argv, err := decodeCmd(cmdVal)
			if err != nil {
				return nil, fmt.Errorf("window cmd: %w", err)
			}
			w.Cmd = argv
		}
		out = append(out, w)
	}
	return out, nil
}

// decodeCmd resolves the `cmd: string | [...string]` union. Strings
// become a single-element slice (the shell-style "euporie notebook"
// case); lists pass through. The production-side Controller is free
// to splitting shell strings further if needed — the loader returns
// what CUE says, no more.
func decodeCmd(v cue.Value) ([]string, error) {
	if s, err := v.String(); err == nil {
		return []string{s}, nil
	}
	var argv []string
	if err := v.Decode(&argv); err != nil {
		return nil, fmt.Errorf("cmd neither string nor []string: %w", err)
	}
	return argv, nil
}
