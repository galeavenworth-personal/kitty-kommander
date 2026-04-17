package scenario

import (
	"encoding/json"
	"fmt"
)

// StringOrList accepts either a JSON string or a JSON array of strings,
// mirroring CUE's `cmd: string | [...string]` union. Scenarios can
// write `cmd: "claude"` OR `cmd: ["kommander-ui", "--dag"]`; Go
// consumers always see a []string via Argv().
type StringOrList []string

// UnmarshalJSON handles both forms. Empty JSON / null yield a nil slice.
func (s *StringOrList) UnmarshalJSON(data []byte) error {
	if len(data) == 0 || string(data) == "null" {
		*s = nil
		return nil
	}
	switch data[0] {
	case '"':
		var str string
		if err := json.Unmarshal(data, &str); err != nil {
			return err
		}
		*s = []string{str}
		return nil
	case '[':
		var list []string
		if err := json.Unmarshal(data, &list); err != nil {
			return err
		}
		*s = list
		return nil
	default:
		return fmt.Errorf("StringOrList: expected string or array, got %s", data)
	}
}

// Argv returns the command as a []string. Callers should always use
// this rather than indexing s directly — keeps us free to change the
// underlying representation later.
func (s StringOrList) Argv() []string { return []string(s) }
