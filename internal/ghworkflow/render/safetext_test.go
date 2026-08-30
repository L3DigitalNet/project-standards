package render_test

import (
	"errors"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// Each case pins one way untrusted GitHub text can rewrite the rendered report rather
// than merely look odd in it: cursor control, line control, and visual reordering.
func TestSanitizeTextNeutralizesTerminalControl(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		in   string
		want string
	}{
		{"ordinary text is untouched", "Ledger write leaves a partial file", "Ledger write leaves a partial file"},
		{"non-ASCII content survives", "漢字 אַ ✔ 👨‍👩‍👧‍👦", "漢字 אַ ✔ 👨‍👩‍👧‍👦"},
		{"ansi colour escape", "safe\x1b[31mred\x1b[0m", "safe�[31mred�[0m"},
		{"screen-clearing sequence", "title\x1b[2J\x1b[H", "title�[2J�[H"},
		{"carriage return overwrite", "real title\rfake title", "real title�fake title"},
		{"embedded newline splits a row", "line one\nline two", "line one�line two"},
		{"tab breaks column measurement", "a\tb", "a�b"},
		{"one marker per run", "a\x1b\x1b\x1bb", "a�b"},
		{"bidi override reorders", "fix ‮gnitset‬", "fix �gnitset�"},
		{"zero-width space", "he​llo", "he�llo"},
		{"c1 control", "xAm", "x�Am"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := render.SanitizeText(tc.in); got != tc.want {
				t.Errorf("SanitizeText(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

// Sanitizing must be idempotent: the model is sanitized on ingestion and rendered more
// than once, and a second pass that changed the text would make the JSON envelope and
// the human view disagree about the same work item.
func TestSanitizeTextIsIdempotent(t *testing.T) {
	t.Parallel()

	once := render.SanitizeText("a\x1b[31mb\rc‮d")
	if twice := render.SanitizeText(once); twice != once {
		t.Errorf("second pass = %q, want %q", twice, once)
	}
}

// Sanitized titles must reach both surfaces, because an agent relays the human output
// into Markdown and a consumer pipes the JSON back through a terminal. This asserts the
// rendered artifacts, not the helper.
func TestRenderedSurfacesCarryNoTerminalControl(t *testing.T) {
	t.Parallel()

	item := render.WorkItem{
		Kind: render.KindIssue, Number: 1, Title: render.SanitizeText("t\x1b[2Jitle"),
		Type: "Task", State: "open", HasAcceptanceCriteria: true,
		Fields: map[string]string{render.FieldWorkflow: "In progress"},
	}
	snapshot := render.NewSnapshot(fixtureTarget, fixtureReadAt(t), []render.WorkItem{item}, nil)

	for name, rendered := range map[string]string{
		"summary": render.Summary(snapshot),
		"receipt": render.Receipt(item),
	} {
		if strings.ContainsAny(rendered[strings.Index(rendered, "t"):], "\x1b\r") {
			t.Errorf("%s carries a terminal control character:\n%q", name, rendered)
		}
	}
}

// IR-005 exit classification: a value that is not a GitHub identity is a local refusal
// wherever it came from, so every refusal this file produces must stay recognizable as
// one after wrapping. The command layer's asIdentityRefusal branches on exactly this.
func TestRepositoryRefusalsAreIdentityErrors(t *testing.T) {
	t.Parallel()

	for _, value := range []string{"", "no-slash", "owner/", "/name", "own er/name", "owner/na me"} {
		if _, err := render.ParseRepository(value); !errors.Is(err, ghapi.ErrInvalidIdentity) {
			t.Errorf("ParseRepository(%q) error = %v, want it to wrap ErrInvalidIdentity", value, err)
		}
	}
}
