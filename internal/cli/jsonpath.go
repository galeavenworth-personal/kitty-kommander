package cli

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"testing"

	"github.com/galeavenworth-personal/kitty-kommander/internal/scenario"
)

// assertJSONPaths parses stdout as JSON and checks every JSONPath
// assertion. The path language here is a minimal dotted path with
// bracket indexing, matching the expressions the scenarios use:
//
//	.status                → top-level key
//	.tabs_expected         → top-level key
//	.drift[0].kind         → array index, then key
//	.drift[0].tab          → nested
//
// No wildcards, no slicing, no filter expressions. Scenarios that
// need more can promote the JSONPath type — for now, keeping the
// evaluator small means it is auditable.
//
// Match modes:
//
//	contains → substring match against the stringified value
//	equals   → stringified-value equality
//	matches  → regex match against stringified value
func assertJSONPaths(t *testing.T, stdout string, paths []scenario.JSONPath) {
	t.Helper()
	if len(paths) == 0 {
		return
	}

	var root any
	if err := json.Unmarshal([]byte(stdout), &root); err != nil {
		t.Errorf("stdout is not valid JSON: %v\nstdout: %s", err, stdout)
		return
	}

	for _, p := range paths {
		got, err := evalJSONPath(root, p.Path)
		if err != nil {
			t.Errorf("jsonpath %q: %v", p.Path, err)
			continue
		}
		s := stringifyJSONValue(got)
		switch {
		case p.Contains != "":
			if !strings.Contains(s, p.Contains) {
				t.Errorf("jsonpath %q = %q, want contains %q", p.Path, s, p.Contains)
			}
		case p.Equals != "":
			if s != p.Equals {
				t.Errorf("jsonpath %q = %q, want equals %q", p.Path, s, p.Equals)
			}
		case p.Matches != "":
			re, err := regexp.Compile(p.Matches)
			if err != nil {
				t.Errorf("jsonpath %q: invalid regex %q: %v", p.Path, p.Matches, err)
				continue
			}
			if !re.MatchString(s) {
				t.Errorf("jsonpath %q = %q, want matches /%s/", p.Path, s, p.Matches)
			}
		}
	}
}

// evalJSONPath walks root following a minimal dotted path. Leading
// "." is required (matches scenario convention); empty path returns
// root.
func evalJSONPath(root any, path string) (any, error) {
	if path == "" || path == "." {
		return root, nil
	}
	if !strings.HasPrefix(path, ".") {
		return nil, fmt.Errorf("path must start with '.'")
	}
	cur := root
	rest := path[1:]

	for rest != "" {
		// Read a key (up to next '.' or '[').
		keyEnd := len(rest)
		for i, r := range rest {
			if r == '.' || r == '[' {
				keyEnd = i
				break
			}
		}
		key := rest[:keyEnd]
		rest = rest[keyEnd:]

		if key != "" {
			m, ok := cur.(map[string]any)
			if !ok {
				return nil, fmt.Errorf("key %q: not an object", key)
			}
			v, exists := m[key]
			if !exists {
				return nil, fmt.Errorf("key %q not found", key)
			}
			cur = v
		}

		// Consume any [N] indexers.
		for strings.HasPrefix(rest, "[") {
			close := strings.Index(rest, "]")
			if close < 0 {
				return nil, fmt.Errorf("unclosed '['")
			}
			idxStr := rest[1:close]
			rest = rest[close+1:]

			idx, err := strconv.Atoi(idxStr)
			if err != nil {
				return nil, fmt.Errorf("bad index %q: %w", idxStr, err)
			}
			arr, ok := cur.([]any)
			if !ok {
				return nil, fmt.Errorf("index [%d]: not an array", idx)
			}
			if idx < 0 || idx >= len(arr) {
				return nil, fmt.Errorf("index [%d] out of range (len=%d)", idx, len(arr))
			}
			cur = arr[idx]
		}

		// Skip leading '.' before the next key.
		if strings.HasPrefix(rest, ".") {
			rest = rest[1:]
		}
	}

	return cur, nil
}

// stringifyJSONValue renders a JSON value for substring / equals /
// regex comparison. Numbers become their shortest decimal form (so a
// JSON "4" is "4", not "4.000000"); strings are their literal value;
// bools and null render as their JSON keywords.
func stringifyJSONValue(v any) string {
	switch x := v.(type) {
	case nil:
		return "null"
	case bool:
		if x {
			return "true"
		}
		return "false"
	case string:
		return x
	case float64:
		// JSON numbers come out as float64. If the value is integral,
		// render without decimal point so `{tabs_expected: "4"}`
		// matches 4 cleanly.
		if x == float64(int64(x)) {
			return strconv.FormatInt(int64(x), 10)
		}
		return strconv.FormatFloat(x, 'g', -1, 64)
	default:
		// Compound types: render as JSON.
		b, _ := json.Marshal(v)
		return string(b)
	}
}
