package render

import (
	"regexp"
	"strings"
	"unicode"
)

// printWidth is the markdown-tooling standard's Prettier print width. Prettier owns
// physical markdown formatting in consuming repositories, so generated output has to be
// what Prettier would produce — anything else fails the consumer's own format gate on
// the first refresh (spec FR-019).
const printWidth = 88

// minColumnWidth is the width of Prettier's shortest delimiter cell, `---`.
const minColumnWidth = 3

// Table renders a GitHub-flavored markdown table the way Prettier formats one: columns
// padded into alignment while the widest resulting line still fits printWidth, and the
// compact single-space form once it does not. Reproducing the rule here is what keeps
// `prettier --check` clean over the generated file without a formatting pass.
func Table(header []string, rows [][]string) string {
	escapedHeader := escapeRow(header)
	escapedRows := make([][]string, 0, len(rows))
	for _, row := range rows {
		escapedRows = append(escapedRows, escapeRow(row))
	}

	widths := make([]int, len(escapedHeader))
	for i, cell := range escapedHeader {
		widths[i] = max(minColumnWidth, displayWidth(cell))
	}
	for _, row := range escapedRows {
		for i, cell := range row {
			if i < len(widths) {
				widths[i] = max(widths[i], displayWidth(cell))
			}
		}
	}

	// One `| ` opener, one ` |` closer, and ` | ` between columns: three characters per
	// column plus the leading pipe.
	total := 1
	for _, width := range widths {
		total += width + 3
	}
	if total > printWidth {
		for i := range widths {
			widths[i] = 0
		}
	}

	var b strings.Builder
	writeRow(&b, escapedHeader, widths)
	delimiters := make([]string, len(widths))
	for i, width := range widths {
		delimiters[i] = strings.Repeat("-", max(minColumnWidth, width))
	}
	writeRow(&b, delimiters, widths)
	for _, row := range escapedRows {
		writeRow(&b, row, widths)
	}
	return b.String()
}

// writeRow writes one row, padding each cell to width when widths are set. A zero width
// means the compact form, where cells carry a single surrounding space and nothing more.
func writeRow(b *strings.Builder, cells []string, widths []int) {
	b.WriteString("|")
	for i, cell := range cells {
		b.WriteString(" ")
		b.WriteString(cell)
		if i < len(widths) && widths[i] > displayWidth(cell) {
			b.WriteString(strings.Repeat(" ", widths[i]-displayWidth(cell)))
		}
		b.WriteString(" |")
	}
	b.WriteString("\n")
}

func escapeRow(cells []string) []string {
	escaped := make([]string, 0, len(cells))
	for _, cell := range cells {
		escaped = append(escaped, EscapeText(cell))
	}
	return escaped
}

var (
	urlPattern        = regexp.MustCompile(`https?://[^\s<>` + "`" + `]+`)
	whitespaceRunning = regexp.MustCompile(`\s+`)
	// markdownEscapes are the characters that would otherwise let arbitrary GitHub text
	// act on the document: a pipe silently adds a column, emphasis and link markers
	// restyle content markdownlint pins to one style, a tilde pair opens GFM
	// strikethrough, and an angle bracket opens inline HTML the same linter forbids
	// outright.
	markdownEscapes = strings.NewReplacer(
		`\`, `\\`,
		"|", `\|`,
		"`", "\\`",
		"*", `\*`,
		"_", `\_`,
		"~", `\~`,
		"<", `\<`,
		">", `\>`,
		"[", `\[`,
		"]", `\]`,
	)
)

// EscapeText makes arbitrary GitHub text safe to place inside the generated markdown.
//
// Titles are operator-authored prose that lands verbatim in a linted document, so it is
// neutralized rather than trusted: metacharacters are escaped to render literally, and a
// bare URL — which the markdown linter rejects as an unlinked address — is wrapped in a
// code span, where it is neither a link nor an escape hazard.
func EscapeText(text string) string {
	text = whitespaceRunning.ReplaceAllString(strings.TrimSpace(text), " ")

	var b strings.Builder
	last := 0
	for _, match := range urlPattern.FindAllStringIndex(text, -1) {
		b.WriteString(markdownEscapes.Replace(text[last:match[0]]))
		b.WriteString("`")
		b.WriteString(text[match[0]:match[1]])
		b.WriteString("`")
		last = match[1]
	}
	b.WriteString(markdownEscapes.Replace(text[last:]))
	return b.String()
}

// displayWidth measures a cell the way Prettier's width accounting does: combining marks
// occupy no columns and East Asian wide characters occupy two.
//
// The wide-character set below is an approximation of the full Unicode width tables,
// covering the ranges that appear in issue titles. A miss costs alignment only — the
// document stays valid markdown, and the consumer's formatter would restyle the table
// rather than reject it.
func displayWidth(s string) int {
	width := 0
	for _, r := range s {
		switch {
		case unicode.Is(unicode.Mn, r), unicode.Is(unicode.Me, r):
		case isWide(r):
			width += 2
		default:
			width++
		}
	}
	return width
}

func isWide(r rune) bool {
	switch {
	case r >= 0x1100 && r <= 0x115F, // Hangul Jamo
		r >= 0x2E80 && r <= 0x303E, // CJK radicals, Kangxi, CJK symbols
		r >= 0x3041 && r <= 0x33FF, // kana, Hangul compatibility, CJK compatibility
		r >= 0x3400 && r <= 0x4DBF, // CJK extension A
		r >= 0x4E00 && r <= 0x9FFF, // CJK unified ideographs
		r >= 0xA000 && r <= 0xA4CF, // Yi
		r >= 0xAC00 && r <= 0xD7A3, // Hangul syllables
		r >= 0xF900 && r <= 0xFAFF, // CJK compatibility ideographs
		r >= 0xFE30 && r <= 0xFE6F, // CJK compatibility forms
		r >= 0xFF00 && r <= 0xFF60, // fullwidth forms
		r >= 0xFFE0 && r <= 0xFFE6,
		r >= 0x1F300 && r <= 0x1F64F, // pictographs and emoticons
		r >= 0x1F900 && r <= 0x1F9FF,
		r >= 0x20000 && r <= 0x3FFFD: // CJK extensions B and beyond
		return true
	}
	return false
}

// Anchor is the heading anchor GitHub generates, which is what the ledger's table of
// contents links to.
func Anchor(heading string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(heading) {
		switch {
		case r == ' ':
			b.WriteRune('-')
		case r == '-' || unicode.IsLetter(r) || unicode.IsDigit(r):
			b.WriteRune(r)
		}
	}
	return b.String()
}
