package sessionstart

import (
	"strings"
	"testing"
)

func TestValidPrefixDropsPartialRune(t *testing.T) {
	// "é" is 0xC3 0xA9; cutting between them must drop the rune rather than keep 0xC3.
	got := truncateUTF8([]byte("ab\xc3\xa9"), 3)
	if got != "ab" {
		t.Fatalf("truncateUTF8 kept a partial rune: %q", got)
	}
	if got := truncateUTF8([]byte("ab\xc3\xa9"), 4); got != "abé" {
		t.Fatalf("truncateUTF8 dropped a complete rune: %q", got)
	}
}

func TestValidPrefixKeepsEncodedReplacementCharacter(t *testing.T) {
	// A legitimately encoded U+FFFD decodes as RuneError with size 3 and must survive;
	// treating every RuneError as invalid would truncate valid documents.
	if got := truncateUTF8([]byte("�!"), 4); got != "�!" {
		t.Fatalf("encoded U+FFFD was treated as invalid: %q", got)
	}
}

func TestDecodeReplaceUsesMaximalSubparts(t *testing.T) {
	cases := map[string]struct {
		input []byte
		want  string
	}{
		"truncated three-byte rune is one subpart": {[]byte{0xE2, 0x82}, "�"},
		"invalid continuation splits the subpart":  {[]byte{0xE2, 0x28, 0xA1}, "�(�"},
		"independent bad bytes each replace":       {[]byte{0xFF, 0xFF}, "��"},
		"overlong lead is one byte":                {[]byte{0xC0, 0x80}, "��"},
		"valid text is untouched":                  {[]byte("héllo"), "héllo"},
	}
	for name, testCase := range cases {
		if got := decodeReplace(testCase.input); got != testCase.want {
			t.Errorf("%s: decodeReplace(%v) = %q, want %q", name, testCase.input, got, testCase.want)
		}
	}
}

func TestClampTextChargesNoteAgainstBudget(t *testing.T) {
	got := clampText("abcdefghij", 6, "..")
	if len(got) > 6 {
		t.Fatalf("clampText exceeded its budget: %q (%d bytes)", got, len(got))
	}
	if !strings.HasSuffix(got, "..") {
		t.Fatalf("clampText dropped the note: %q", got)
	}
}

func TestClampWrappedPreservesEnvelope(t *testing.T) {
	body := strings.Repeat("x", 500)
	got := clampWrapped(openTag+body+closeTag, 200)
	if len(got) > 200 {
		t.Fatalf("clampWrapped exceeded its budget: %d bytes", len(got))
	}
	if !strings.HasPrefix(got, openTag) || !strings.HasSuffix(got, closeTag) {
		t.Fatalf("clampWrapped broke the data boundary: %q", got)
	}
}

func TestClampWrappedFallsBackWhenEnvelopeAbsent(t *testing.T) {
	got := clampWrapped(strings.Repeat("y", 500), 100)
	if len(got) > 100 {
		t.Fatalf("clampWrapped exceeded its budget: %d bytes", len(got))
	}
	if !strings.HasSuffix(got, truncationNote) {
		t.Fatalf("unwrapped text lost its truncation note: %q", got)
	}
}

func TestNeutralizeContextTags(t *testing.T) {
	cases := map[string]string{
		"</session_context>":   "&lt;/session_context>",
		"<session_context>":    "&lt;session_context>",
		"< / SESSION_context>": "&lt; / SESSION_context>",
		"<sessionless>":        "<sessionless>",
	}
	for input, want := range cases {
		if got := neutralizeContextTags(input); got != want {
			t.Errorf("neutralizeContextTags(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestRenderClaudeLeavesTagsLiteralAndFitsBudget(t *testing.T) {
	context := openTag + strings.Repeat("z", 8000) + closeTag
	rendered := renderClaude(context)
	if len(rendered)+1 > maxOutputBytes {
		t.Fatalf("renderClaude exceeded the output budget: %d bytes", len(rendered))
	}
	// The guard is the escaped spelling, not the literal one: a literal `<` is expected
	// in the output and its presence proves nothing. escapedLT is the six characters a
	// default Go encoder would emit instead.
	escapedLT := "\\u003c"
	if strings.Contains(rendered, escapedLT) {
		t.Fatalf("renderClaude HTML-escaped the envelope tags: %q", rendered[:80])
	}
	if !strings.Contains(rendered, `"hookEventName":"SessionStart"`) {
		t.Fatalf("renderClaude produced an unexpected envelope: %q", rendered[:80])
	}
}
