package render

import (
	"bufio"
	"os"
	"strconv"
	"strings"
	"testing"
)

// The worked examples from #185's width spec, each with the width Prettier itself
// assigns. They are duplicated from testdata/prettier-widths.tsv on purpose: the golden
// file is a bulk oracle dump nobody reads line by line, and these are the cases whose
// answers a maintainer needs to see next to the code that produces them.
func TestDisplayWidthMatchesPrettierOnSpecExamples(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		in   string
		want int
	}{
		{"ascii", "plain ascii", 11},
		{"empty", "", 0},
		// Prettier's fast path is "every code point in 0x20-0x7F", so a TAB drops to the
		// slow path where control characters are worth nothing at all.
		{"tab is a control character", "\ta", 1},
		{"del stays on the ascii fast path", "a\u007Fb", 3},
		{"c1 control", "a\u0085b", 2},
		// The narrow list holds bare code points only. Adding U+FE0F leaves the list and
		// doubles the width; U+FE0E does not, because Prettier's emoji match stops
		// before it and the selector itself is worth nothing.
		{"bare narrow emoji", "✔", 1},
		{"bare warning sign", "⚠", 1},
		{"warning sign with VS16", "⚠️", 2},
		{"copyright with VS15", "©︎", 1},
		{"copyright with VS16", "©️", 2},
		// An emoji sequence is one atomic unit however many code points it spans.
		{"ZWJ family", "\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466", 2},
		{"keycap", "1️⃣", 2},
		{"keycap without VS16", "1⃣", 2},
		{"regional indicator flag", "\U0001F1FA\U0001F1F8", 2},
		{"skin tone modifier", "\U0001F44D\U0001F3FD", 2},
		// A skin tone attaches only to an Emoji_Modifier_Base, which "©" is not, so
		// Prettier scores this as two independent emoji matches — the narrow copyright
		// sign at 1 and the lone modifier at 2 — never as one modified emoji. The 3 is
		// the Node oracle's answer from Prettier 3.9.6's own getStringWidth, confirmed
		// against the padding the real formatter emits.
		//
		// A padding-based probe that reports 2 here has measured the cell in UTF-16
		// units and the probe in code points (or graphemes), which loses one unit per
		// surrogate pair and so misreads every astral code point. Count both sides in
		// the same unit before concluding this row is wrong.
		{"narrow base followed by a skin tone", "©\U0001F3FB", 3},
		{"subdivision flag", "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F", 2},
		// A digit is only an emoji as a keycap base, and a lone regional indicator is
		// not an emoji match at all — both fall through to the per-code-point rule.
		{"bare digit", "1", 1},
		{"lone regional indicator", "\U0001F1FA", 1},
		// East Asian Wide and Fullwidth are the only two classes worth two columns.
		{"CJK", "漢字", 4},
		{"fullwidth latin", "ｆｕｌｌ", 8},
		// Prettier skips U+0300-U+036F and nothing else, so a Hebrew point costs a
		// column even though it is a combining mark. The blanket Mn/Me skip this
		// replaced got that backwards (#185).
		{"combining acute is skipped", "á", 1},
		{"hebrew point is not skipped", "אַ", 2},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := displayWidth(tc.in); got != tc.want {
				t.Errorf("displayWidth(%q) = %d, want %d", tc.in, got, tc.want)
			}
		})
	}
}

// knownEmojiRegexDivergences are the corpus entries where this package deliberately
// disagrees with Prettier; see the emojiUnitEnd doc comment for why. Asserting that each
// one still diverges keeps the exception honest: if a future change makes the scanner
// exact, this test says so instead of silently passing.
var knownEmojiRegexDivergences = map[string]int{
	// Two thumbs-up joined by U+200D is not a sanctioned sequence. emoji-regex matches
	// the two pictographs separately and scores the joiner on its own (2+1+2); the
	// scanner here takes the join at face value.
	"\U0001F44D\u200D\U0001F44D": 2,
}

// The golden file is Prettier's own answer for every case, so this is a differential
// test against the real implementation rather than a restatement of this package's
// behavior. A width table regenerated against a newer Prettier lands here first.
func TestDisplayWidthMatchesPrettierCorpus(t *testing.T) {
	t.Parallel()

	file, err := os.Open("testdata/prettier-widths.tsv")
	if err != nil {
		t.Fatalf("opening the width corpus: %v", err)
	}
	defer func() { _ = file.Close() }()

	checked := 0
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.SplitN(line, "\t", 3)
		if len(fields) != 3 {
			t.Fatalf("malformed corpus line %q", line)
		}
		want, err := strconv.Atoi(fields[0])
		if err != nil {
			t.Fatalf("malformed width in corpus line %q: %v", line, err)
		}
		text := decodeCodePoints(t, fields[1])

		if divergent, ok := knownEmojiRegexDivergences[text]; ok {
			if got := displayWidth(text); got != divergent {
				t.Errorf("known divergence %s (%s): displayWidth = %d, want the recorded %d"+
					" (Prettier says %d) — update knownEmojiRegexDivergences",
					fields[1], fields[2], got, divergent, want)
			}
			continue
		}
		if got := displayWidth(text); got != want {
			t.Errorf("%s (%s): displayWidth = %d, want %d", fields[1], fields[2], got, want)
		}
		checked++
	}
	if err := scanner.Err(); err != nil {
		t.Fatalf("reading the width corpus: %v", err)
	}
	// A truncated or mis-parsed corpus would otherwise pass silently.
	if checked < 500 {
		t.Errorf("corpus checked %d cases, want at least 500", checked)
	}
}

// narrow-emojis 0.0.3 ships exactly this many code points. The count is asserted because
// the table is transcribed rather than derived: a partial paste would go unnoticed —
// every missing entry only doubles one emoji's width, which reads as a plausible answer.
//
// The list is also the one place Prettier 3.8.3 and 3.9.6 disagree: 3.8.3 carries 100
// code points from its own inline narrow-emojis.evaluate.js and 3.9.6 carries these 192,
// with 100 code points in the symmetric difference. This package implements 3.9.6.
func TestNarrowEmojiListIsComplete(t *testing.T) {
	t.Parallel()

	if got, want := len(narrowEmojiRunes), 192; got != want {
		t.Errorf("narrowEmojiRunes has %d entries, want %d", got, want)
	}
	for i := 1; i < len(narrowEmojiRunes); i++ {
		// Sorted order is a precondition of the binary search, not a style choice.
		if narrowEmojiRunes[i] <= narrowEmojiRunes[i-1] {
			t.Fatalf("narrowEmojiRunes is not strictly ascending at index %d (%U after %U)",
				i, narrowEmojiRunes[i], narrowEmojiRunes[i-1])
		}
	}
}

// Every range table is searched by bisection, which silently returns wrong answers on an
// unsorted or overlapping table.
func TestRangeTablesAreOrdered(t *testing.T) {
	t.Parallel()

	for name, table := range map[string][]runeRange{
		"emojiUnitStartRanges":        emojiUnitStartRanges,
		"emojiPresentationBaseRanges": emojiPresentationBaseRanges,
		"emojiModifierBaseRanges":     emojiModifierBaseRanges,
		"eastAsianWideRanges":         eastAsianWideRanges,
	} {
		for i, r := range table {
			if r.lo > r.hi {
				t.Errorf("%s[%d] = %U-%U is inverted", name, i, r.lo, r.hi)
			}
			if i > 0 && r.lo <= table[i-1].hi {
				t.Errorf("%s[%d] = %U-%U overlaps or precedes its predecessor %U-%U",
					name, i, r.lo, r.hi, table[i-1].lo, table[i-1].hi)
			}
		}
	}
}

func decodeCodePoints(t *testing.T, field string) string {
	t.Helper()

	var b strings.Builder
	for _, hex := range strings.Fields(field) {
		cp, err := strconv.ParseUint(hex, 16, 32)
		if err != nil {
			t.Fatalf("malformed code point %q: %v", hex, err)
		}
		b.WriteRune(rune(cp))
	}
	return b.String()
}

// A cell's padding is computed from its display width, so an emoji-bearing title used to
// be padded to a column Prettier measures differently — the ledger then failed the
// consuming repository's own `prettier --check` on a row that was otherwise correct
// (#185).
//
// The expected bytes below are not this renderer's output written down: the same table
// was checked with prettier 3.9.6 and 3.8.3, both of which accept it as already
// formatted. testdata/ledger.md carries the same proof end to end.
func TestTableAlignsEmojiCellsAtPrettierWidth(t *testing.T) {
	t.Parallel()

	// 18 columns: a bare narrow-list emoji at 1, four sequences at 2 each — including a
	// four-person ZWJ family that spans seven code points — the two-ideograph CJK run at
	// 4, and five separating spaces. Written as escapes because the variation selectors
	// and joiners that drive that arithmetic are invisible in a literal.
	const emoji = "\u2714 \u26A0\uFE0F " +
		"\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466 " +
		"1\uFE0F\u20E3 \U0001F1FA\U0001F1F8 \u6F22\u5B57"
	want := "| Title              | State |\n" +
		"| ------------------ | ----- |\n" +
		"| " + emoji + " | open  |\n" +
		"| ascii row          | open  |\n"

	if got := Table([]string{"Title", "State"}, [][]string{{emoji, "open"}, {"ascii row", "open"}}); got != want {
		t.Errorf("Table with an emoji cell =\n%s\nwant\n%s", got, want)
	}
}
