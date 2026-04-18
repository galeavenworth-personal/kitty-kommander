package kitty

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"
)

// KittenExec shells out to `kitten @ --to $KITTY_LISTEN_ON <verb>`.
// It is the production Controller. Constructed via NewKittenExec,
// which errors if $KITTY_LISTEN_ON is not set — hardcoding the socket
// is explicitly forbidden by CLAUDE.md, and a zero-socket
// KittenExec would silently target the default kitty instance.
type KittenExec struct {
	socket string
}

// NewKittenExec reads $KITTY_LISTEN_ON and returns a Controller that
// targets that socket. Returns an error rather than falling back to a
// default so a misconfigured environment fails loudly.
func NewKittenExec() (*KittenExec, error) {
	sock := os.Getenv("KITTY_LISTEN_ON")
	if sock == "" {
		return nil, fmt.Errorf("KITTY_LISTEN_ON is not set — kommander must run inside a kitty instance launched with --listen-on")
	}
	return &KittenExec{socket: sock}, nil
}

// NewKittenExecForSocket constructs a KittenExec bound to an explicit
// socket path. Used by `kommander launch` after spawning a fresh kitty
// process — the caller already knows the socket it created kitty with,
// so we skip the KITTY_LISTEN_ON env check. Socket is expected in the
// `unix:/path` form kitty uses.
func NewKittenExecForSocket(socket string) *KittenExec {
	return &KittenExec{socket: socket}
}

// SpawnKitty starts a fresh kitty process listening on socket (e.g.
// "unix:/tmp/kitty-kommander-my-app") and returns the started *exec.Cmd
// so the caller can track the pid for orphan cleanup. The child is
// detached (Setsid) so it survives the kommander process exiting, and
// its stdio is attached to /dev/null so it does not share kommander's
// terminal.
//
// Does NOT wait for the socket to appear — callers must poll via
// WaitForSocket before attempting kitten @ commands. Does NOT check for
// socket-file collisions — callers must pre-flight that (refuse-hard,
// per uib.3.D arbitration).
//
// Returns an error if the kitty binary is not on PATH or the fork
// fails. On success the child is alive; the caller owns cleanup on any
// subsequent failure.
func SpawnKitty(socket string) (*exec.Cmd, error) {
	cmd := exec.Command("kitty", "--listen-on", socket)
	devnull, err := os.OpenFile(os.DevNull, os.O_RDWR, 0)
	if err != nil {
		return nil, fmt.Errorf("open /dev/null: %w", err)
	}
	cmd.Stdin = devnull
	cmd.Stdout = devnull
	cmd.Stderr = devnull
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := cmd.Start(); err != nil {
		devnull.Close()
		return nil, fmt.Errorf("spawn kitty: %w", err)
	}
	// devnull stays open for the child's lifetime; parent dup'd the fd
	// on Start so we can drop our reference. The child keeps its own
	// fd alive until it exits.
	devnull.Close()
	return cmd, nil
}

// WaitForSocket polls until the unix socket file at `socket` exists,
// or timeout elapses. Socket is in `unix:/path` form; the `unix:`
// prefix is stripped for the filesystem check.
//
// Poll interval is 50ms. Timeout is 5s per uib.3.D arbitration. If this
// proves flaky in practice, bump the cap.
func WaitForSocket(socket string, timeout time.Duration) error {
	path := strings.TrimPrefix(socket, "unix:")
	deadline := time.Now().Add(timeout)
	for {
		if _, err := os.Stat(path); err == nil {
			return nil
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("socket %s did not appear within %s", path, timeout)
		}
		time.Sleep(50 * time.Millisecond)
	}
}

func (k *KittenExec) run(args ...string) ([]byte, error) {
	full := append([]string{"@", "--to", k.socket}, args...)
	cmd := exec.Command("kitten", full...)
	var out, errBuf bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &errBuf
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("kitten %v: %w: %s", args, err, errBuf.String())
	}
	return out.Bytes(), nil
}

func (k *KittenExec) LaunchTab(spec TabSpec) error {
	args := []string{"launch", "--type=tab", "--tab-title", spec.Title}
	// Pass --title for the first window when the CUE contract declares
	// one. Kitty treats --title at launch as a persistent override that
	// survives any OSC 0 escape the child process emits later (claude's
	// spinner, euporie's process name), so the title kitten @ ls reports
	// post-launch equals the CUE-declared title — which is what doctor's
	// winKey compares against. uib.3.C Option A; see schema/cli/doctor.cue
	// "doctor-healthy-real-titles" for the executable contract.
	//
	// The `--title` arg goes BEFORE the command argv because kitten @
	// launch treats the first non-flag positional as the start of the
	// child command — anything after that is argv for the child, not a
	// kitten flag.
	if len(spec.Windows) > 0 {
		if spec.Windows[0].Title != "" {
			args = append(args, "--title", spec.Windows[0].Title)
		}
		args = append(args, spec.Windows[0].Cmd...)
	}
	_, err := k.run(args...)
	return err
}

func (k *KittenExec) LaunchWindow(targetTab string, spec WindowSpec) error {
	args := []string{
		"launch", "--type=window",
		"--match", "title:" + targetTab,
	}
	if spec.Title != "" {
		args = append(args, "--title", spec.Title)
	}
	args = append(args, spec.Cmd...)
	_, err := k.run(args...)
	return err
}

func (k *KittenExec) CloseWindow(selector string) error {
	_, err := k.run("close-window", "--match", selector)
	return err
}

func (k *KittenExec) SendText(selector, text string) error {
	cmd := exec.Command("kitten", "@", "--to", k.socket,
		"send-text", "--match", selector, "--stdin")
	cmd.Stdin = bytes.NewBufferString(text)
	var errBuf bytes.Buffer
	cmd.Stderr = &errBuf
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("kitten send-text: %w: %s", err, errBuf.String())
	}
	return nil
}

func (k *KittenExec) FocusTab(selector string) error {
	_, err := k.run("focus-tab", "--match", selector)
	return err
}

func (k *KittenExec) CloseTab(selector string) error {
	_, err := k.run("close-tab", "--match", selector)
	return err
}

func (k *KittenExec) List() (*State, error) {
	out, err := k.run("ls")
	if err != nil {
		return nil, err
	}
	// `kitten @ ls` returns an array of oswindow objects; we flatten
	// to our State shape by taking the first os-window's tabs.
	var raw []struct {
		Tabs []struct {
			ID      int    `json:"id"`
			Title   string `json:"title"`
			Windows []struct {
				Title   string            `json:"title"`
				Cmdline []string          `json:"cmdline"`
				Env     map[string]string `json:"env"`
			} `json:"windows"`
		} `json:"tabs"`
	}
	if err := json.Unmarshal(out, &raw); err != nil {
		return nil, fmt.Errorf("parse kitten ls: %w", err)
	}
	s := &State{}
	if len(raw) == 0 {
		return s, nil
	}
	for _, t := range raw[0].Tabs {
		tab := TabState{ID: t.ID, Title: t.Title}
		for _, w := range t.Windows {
			tab.Windows = append(tab.Windows, WindowState{
				Title: w.Title,
				Cmd:   w.Cmdline,
				Env:   w.Env,
			})
		}
		s.Tabs = append(s.Tabs, tab)
	}
	return s, nil
}
