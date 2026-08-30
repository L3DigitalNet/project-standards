package render

import "strings"

// Safe encoding of untrusted GitHub text (titles, bodies, field values, finding
// messages) for both rendered surfaces.
//
// The threat is concrete and not hypothetical: an issue title is authored by anyone who
// can open an issue, `summary` and `receipt` print it to a terminal, and the agent
// relays that output verbatim into a Markdown document. Untreated, a title carrying
// ANSI CSI sequences repaints or erases the surrounding report, a bare carriage return
// overwrites the line already written, and a bidirectional override reorders the visible
// text so the rendered issue number no longer matches the one the tool read. All three
// change what the operator sees without changing what the tool decided, which is exactly
// the failure the encoding exists to prevent.
//
// Sanitization happens where untrusted text enters the model (see source.go) rather than
// per surface, so the JSON envelope carries the same bytes the human view prints. A
// consumer that pipes the JSON through `jq` into a terminal is as exposed as the human
// view, so "JSON is machine-readable" is not a reason to leave it untreated.
//
// This is not Markdown escaping. EscapeText owns the Prettier/markdownlint fidelity rule
// for table cells; the two compose, and neither substitutes for the other.

// replacement stands in for every removed run. A visible marker rather than deletion is
// deliberate: silently dropping the bytes would render a title that reads as ordinary
// prose while differing from the one stored on GitHub, and a reader comparing the report
// against the issue would have no way to tell which characters the tool removed.
const replacement = "�"

// SanitizeText returns text with every control and layout-directing code point that
// could rewrite the surrounding report replaced by a single replacement character per
// run.
//
// Three classes are removed, and each for its own reason:
//
//   - C0 and C1 control characters, including ESC, DEL, CR, LF, and TAB. Line and cell
//     structure is the layout's to decide: a newline inside a title splits one table row
//     into two, and a tab breaks Prettier's own column measurement.
//   - The Unicode bidirectional overrides and isolates (U+202A–U+202E, U+2066–U+2069),
//     which reorder rendered text independently of its byte order.
//   - Interlinear annotation and zero-width layout controls that survive as invisible
//     content (U+FFF9–U+FFFB, U+200B, U+2028, U+2029).
//
// Rejected alternative: percent- or backslash-encoding each offending code point. It
// preserves more information, but it expands one code point into several visible
// characters, which changes the display width EscapeText and the table layout compute
// from the same string — and width fidelity against Prettier is a gate this package
// already pays for.
func SanitizeText(text string) string {
	if !needsSanitizing(text) {
		return text
	}
	var b strings.Builder
	b.Grow(len(text))
	removing := false
	for _, r := range text {
		if unsafeRune(r) {
			if !removing {
				b.WriteString(replacement)
				removing = true
			}
			continue
		}
		removing = false
		b.WriteRune(r)
	}
	return b.String()
}

// needsSanitizing keeps the common case allocation-free: nearly every real title is
// already safe, and this function runs on every field of every work item in a summary.
func needsSanitizing(text string) bool {
	for _, r := range text {
		if unsafeRune(r) {
			return true
		}
	}
	return false
}

// unsafeRune reports whether r may rewrite or reorder the rendered report.
//
// The check is a positive enumeration rather than "not unicode.IsPrint": IsPrint also
// rejects ordinary spaces and accepts nothing about bidi behavior, so using it would
// both mangle innocent titles and miss the reordering class entirely.
func unsafeRune(r rune) bool {
	switch {
	case r < 0x20 || r == 0x7F:
		return true
	case r >= 0x80 && r <= 0x9F:
		return true
	case r >= 0x202A && r <= 0x202E:
		return true
	case r >= 0x2066 && r <= 0x2069:
		return true
	case r == 0x200B || r == 0x2028 || r == 0x2029:
		return true
	case r >= 0xFFF9 && r <= 0xFFFB:
		return true
	default:
		return false
	}
}
