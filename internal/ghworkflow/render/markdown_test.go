package render_test

import (
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// Prettier owns markdown formatting in consuming repositories, so the renderer has to
// emit what Prettier would emit or FR-019's gate-clean guarantee fails on the first
// refresh. Prettier pads a table into aligned columns only while the widest resulting
// line fits printWidth, and falls back to single-space cells beyond it. Both sides of
// that boundary are pinned here; testdata/*.md prove the same rule against the real
// formatter.
func TestTableAlignsOnlyWithinPrintWidth(t *testing.T) {
	t.Parallel()

	const printWidth = 88
	header := []string{"A", "B"}

	fits := render.Table(header, [][]string{{"x", strings.Repeat("y", printWidth-10)}})
	for _, line := range strings.Split(strings.TrimSuffix(fits, "\n"), "\n") {
		if len(line) != printWidth {
			t.Errorf("aligned table line width = %d, want %d: %q", len(line), printWidth, line)
		}
	}
	if !strings.Contains(fits, "| --- | ---") || !strings.Contains(fits, "-----") {
		t.Errorf("aligned table did not pad its delimiter row:\n%s", fits)
	}

	overflows := render.Table(header, [][]string{{"x", strings.Repeat("y", printWidth-9)}})
	if !strings.HasPrefix(overflows, "| A | B |\n| --- | --- |\n") {
		t.Errorf("table wider than printWidth did not fall back to the compact form:\n%s", overflows)
	}
}

// A GitHub title is arbitrary text arriving inside a markdown document. Left alone it
// can break the table (a pipe), silently restyle the document (emphasis markers that
// markdownlint pins to one style), inject HTML, or trip the bare-URL rule.
func TestTableEscapesCellText(t *testing.T) {
	t.Parallel()

	table := render.Table(
		[]string{"Title"},
		[][]string{{"a | b *c* _d_ ~~g~~ <e> `f` https://example.test/x"}},
	)
	row := strings.Split(table, "\n")[2]
	for _, want := range []string{`\|`, `\*c\*`, `\_d\_`, `\~\~g\~\~`, `\<e\>`, "`https://example.test/x`"} {
		if !strings.Contains(row, want) {
			t.Errorf("row %q does not contain %q", row, want)
		}
	}
	if strings.Count(row, "|") != strings.Count(row, `\|`)+2 {
		t.Errorf("unescaped pipe leaked into the row and changed its column count: %q", row)
	}
}

// Prettier rewrites `\_` back to `_` between two word characters, so an unconditional
// underscore escape made every ledger refresh carrying a `snake_case` title fail the
// consuming repository's own `prettier --check` gate (#177). The cases below pin the
// boundary of the conditional rule in both directions: an escape Prettier would strip is
// a gate failure downstream, and a missing escape at a word edge lets `_x_` render as
// emphasis, which deletes visible characters from an issue title.
func TestEscapeTextEscapesOnlyUnderscoresPrettierKeeps(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		in   string
		want string
	}{
		{"intraword stays bare", "print_validation", "print_validation"},
		{"every intraword underscore stays bare", "a_b_c_d", "a_b_c_d"},
		{"digits are word characters", "9_9", "9_9"},
		{"leading underscore escapes", "_ab", `\_ab`},
		{"trailing underscore escapes", "ab_", `ab\_`},
		{"emphasis pair escapes", "_ab_", `\_ab\_`},
		{"underscore after punctuation escapes", "a._b", `a.\_b`},
		{"underscore before punctuation escapes", "a_.b", `a\_.b`},
		// A doubled run opens strong emphasis, and Prettier keeps its escape because an
		// underscore is itself punctuation — so `__init__` escapes even intraword.
		{"doubled run escapes intraword", "a__b", `a\_\_b`},
		{"dunder escapes", "__init__", `\_\_init\_\_`},
		{"word edges are whitespace edges", "x a_b _c", `x a_b \_c`},
		// The URL is code-spanned, where an underscore is literal and Prettier does not
		// touch escapes at all.
		{"underscore inside a URL is untouched", "see https://example.test/a_b", "see `https://example.test/a_b`"},
		{"pipe escaping is unaffected", "a_b | c", `a_b \| c`},
	} {
		if got := render.EscapeText(tc.in); got != tc.want {
			t.Errorf("%s: EscapeText(%q) = %q, want %q", tc.name, tc.in, got, tc.want)
		}
	}
}

// The visible ledger has to be unchanged by the escaping change: the same characters an
// operator typed into the GitHub title appear in the cell, and the pipe stays escaped so
// the row keeps its column count (#177).
func TestTableKeepsPipeEscapedAroundBareUnderscores(t *testing.T) {
	t.Parallel()

	const title = "plan.py print_validation | non-integer revision"
	row := strings.Split(render.Table([]string{"Title"}, [][]string{{title}}), "\n")[2]

	if !strings.Contains(row, "print_validation") {
		t.Errorf("intraword underscore did not survive unescaped into the cell: %q", row)
	}
	if !strings.Contains(row, `\|`) {
		t.Errorf("pipe lost its escape: %q", row)
	}
	if strings.Count(row, "|") != strings.Count(row, `\|`)+2 {
		t.Errorf("unescaped pipe leaked into the row and changed its column count: %q", row)
	}
	// Removing the backslashes recovers the operator's title exactly, which is the
	// visible-character invariant the escaping is allowed to touch nothing outside.
	if visible := strings.ReplaceAll(strings.TrimSpace(strings.Trim(row, "|")), `\`, ""); visible != title {
		t.Errorf("rendered cell = %q, want the title's own characters %q", visible, title)
	}
}
