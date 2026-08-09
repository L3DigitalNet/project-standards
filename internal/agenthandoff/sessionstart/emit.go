package sessionstart

import (
	"bytes"
	"encoding/json"
	"io"
	"strings"
)

// Harness identifiers. The transport differs per harness and is not negotiable: Claude
// Code reads a JSON envelope on stdout, Codex reads the bare context block.
const (
	harnessClaude = "claude"
	harnessCodex  = "codex"
)

// claudeEnvelope is Claude Code's documented SessionStart transport.
//
// Field order matters for byte-comparison against the 1.9 Python output, and Go marshals
// struct fields in declaration order, so these declarations mirror the Python dict
// literal exactly.
type claudeEnvelope struct {
	HookSpecificOutput claudePayload `json:"hookSpecificOutput"`
}

type claudePayload struct {
	HookEventName     string `json:"hookEventName"`
	AdditionalContext string `json:"additionalContext"`
}

// renderClaude wraps context in the JSON envelope, shrinking until the *encoded* form
// fits the output budget.
//
// The loop is necessary because JSON escaping is not length-preserving: quotes,
// backslashes and control characters each expand, so clamping the context to the budget
// and then encoding can still overflow. Shrinking by the observed excess converges in a
// couple of iterations rather than one byte at a time.
func renderClaude(context string) string {
	original := context
	limit := len(context)
	floor := len(openTag) + len(closeTag)
	for {
		candidate := clampWrapped(original, limit)
		rendered := encodeJSON(claudeEnvelope{
			HookSpecificOutput: claudePayload{
				HookEventName:     "SessionStart",
				AdditionalContext: candidate,
			},
		})
		// Reserve one byte for the newline the caller appends.
		if len(rendered)+1 <= maxOutputBytes {
			return rendered
		}
		if limit <= floor {
			// The envelope alone exceeds the budget, which cannot happen with the
			// constants above. Returning here keeps a future constant change from
			// hanging the session on an unbounded loop.
			return rendered
		}
		excess := len(rendered) + 1 - maxOutputBytes
		limit = max(floor, limit-max(1, excess))
	}
}

// encodeJSON produces compact JSON with HTML escaping disabled.
//
// Disabling it is required, not cosmetic: the context is wrapped in literal
// `<session_context>` tags, and Go's default encoder would rewrite every `<`, `>` and
// `&` as <-style escapes. The harness would still parse them, but the payload's
// conformance tests compare against the Python encoder's output, which leaves them
// literal.
//
// One residual difference is accepted: Go escapes U+2028/U+2029 unconditionally where
// Python's ensure_ascii=False emits them raw. The decoded value is identical, so only
// the encoded length differs, and the shrink loop above measures the encoded form.
func encodeJSON(value any) string {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return ""
	}
	// Encode always appends a newline; the transport owns that byte.
	return strings.TrimSuffix(buffer.String(), "\n")
}

// emit writes the context through the harness's transport.
func emit(stdout io.Writer, context string, harness string) {
	var line string
	if harness == harnessClaude {
		line = renderClaude(context)
	} else {
		line = clampWrapped(context, maxOutputBytes-1)
	}
	// A failed write is ignored deliberately: the harness closing stdout must not turn a
	// best-effort context injection into a failed session start.
	_, _ = io.WriteString(stdout, line+"\n")
}
