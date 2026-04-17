package kitty

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
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
	if len(spec.Windows) > 0 {
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

func (k *KittenExec) List() (*State, error) {
	out, err := k.run("ls")
	if err != nil {
		return nil, err
	}
	// `kitten @ ls` returns an array of oswindow objects; we flatten
	// to our State shape by taking the first os-window's tabs.
	var raw []struct {
		Tabs []struct {
			Title   string `json:"title"`
			Windows []struct {
				Title string            `json:"title"`
				Cmdline []string        `json:"cmdline"`
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
		tab := TabState{Title: t.Title}
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
