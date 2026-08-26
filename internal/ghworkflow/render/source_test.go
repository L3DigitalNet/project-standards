package render_test

import (
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// A pull-request body is arbitrary operator- or bot-authored text, and the closing-keyword
// pattern puts no bound on the digits it captures. The parsed number is rendered into a
// committed summary and used to cross-reference issues, so a reference no int can hold must
// read as "no governing issue" rather than as whatever an unchecked accumulation produced.
func TestGoverningIssue(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		body string
		want int
	}{
		{name: "closes", body: "Closes #12", want: 12},
		{name: "fixes lowercase", body: "some prose\n\nfixes: #7\n", want: 7},
		{name: "no reference", body: "Refactors the layout engine.", want: 0},
		{
			name: "wider than an int",
			body: "Closes #99999999999999999999",
			want: 0,
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := render.GoverningIssue(tc.body); got != tc.want {
				t.Errorf("GoverningIssue(%q) = %d, want %d", tc.body, got, tc.want)
			}
		})
	}
}
