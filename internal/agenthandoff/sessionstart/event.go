package sessionstart

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"strings"
)

// errInvalidEvent is the single rejection reason surfaced to the harness.
//
// The specific defect is deliberately not reported: the hook writes to a shared stderr
// stream at session start, and a message echoing untrusted input would put attacker text
// in front of the operator before any other output.
var errInvalidEvent = errors.New("invalid SessionStart input")

// validSources is the matcher set the managed registrations subscribe to. An event
// carrying any other source did not come from a registration this package owns.
var validSources = map[string]bool{
	"startup": true,
	"resume":  true,
	"clear":   true,
	"compact": true,
}

// parseEvent validates the SessionStart event and discards it.
//
// Nothing from the event is retained on purpose. The hook reads its repository from its
// own installed path (see repositoryRoot), so parsing exists only to confirm the caller
// is the registration this payload installed — not to obtain data. Returning a value
// here would invite a later change to trust `cwd`.
func parseEvent(stdin io.Reader) error {
	// One byte past the limit distinguishes "at the limit" from "over" it.
	raw, err := io.ReadAll(io.LimitReader(stdin, maxStdinBytes+1))
	if err != nil {
		return errInvalidEvent
	}
	if len(raw) > maxStdinBytes || strings.TrimSpace(string(raw)) == "" {
		return errInvalidEvent
	}

	decoder := json.NewDecoder(bytes.NewReader(raw))
	var parsed any
	if err := decoder.Decode(&parsed); err != nil {
		return errInvalidEvent
	}
	event, ok := parsed.(map[string]any)
	if !ok {
		return errInvalidEvent
	}
	if name, ok := event["hook_event_name"].(string); !ok || name != "SessionStart" {
		return errInvalidEvent
	}
	source, ok := event["source"].(string)
	if !ok || !validSources[source] {
		return errInvalidEvent
	}
	// `cwd` is accepted but never used. A null is tolerated because harnesses omit the
	// field that way; a non-string means the event shape is not what we registered for.
	if cwd, present := event["cwd"]; present && cwd != nil {
		if _, ok := cwd.(string); !ok {
			return errInvalidEvent
		}
	}
	return nil
}
