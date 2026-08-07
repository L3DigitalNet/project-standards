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
		[][]string{{"a | b *c* _d_ <e> `f` https://example.test/x"}},
	)
	row := strings.Split(table, "\n")[2]
	for _, want := range []string{`\|`, `\*c\*`, `\_d\_`, `\<e\>`, "`https://example.test/x`"} {
		if !strings.Contains(row, want) {
			t.Errorf("row %q does not contain %q", row, want)
		}
	}
	if strings.Count(row, "|") != strings.Count(row, `\|`)+2 {
		t.Errorf("unescaped pipe leaked into the row and changed its column count: %q", row)
	}
}
