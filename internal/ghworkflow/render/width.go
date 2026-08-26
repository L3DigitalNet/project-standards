package render

// Prettier-conforming display width for generated markdown table cells.
//
// Table pads every cell to its column width. The consumer's own `prettier --check` gate
// recomputes that padding with Prettier's `getStringWidth`, so any code point where this
// file disagrees with Prettier produces a byte diff on an otherwise correct summary and
// fails the consumer's format gate on the first refresh (#185, same failure class as
// #177). Width is therefore a reproduction of Prettier's rule, not a terminal-display
// approximation: matching a terminal is explicitly not the goal, and where the two
// disagree Prettier wins.
//
// Reference implementation: prettier 3.9.6 src/utilities/get-string-width.js
// (sha256 37f49dbe5815f5b191c246499e38887b2869eae3c12b4df31c7b5c6bba6802cf, fetched
// 2026-08-25 from https://cdn.jsdelivr.net/gh/prettier/prettier@3.9.6/). Prettier 3.8.3
// runs the same algorithm with a different narrow-emoji list; see narrowEmojiRunes in
// width_tables.go and the divergence note on emojiUnitEnd below.
//
// Rejected alternative: golang.org/x/text/width plus github.com/rivo/uniseg. Both would
// answer from their own vendored Unicode version, which is not the version Prettier's
// dependencies carry, so every table skew between them would reappear here as exactly
// the alignment diff this file exists to prevent. The generated tables in
// width_tables.go instead hold the JavaScript dependencies' own answers. Avoiding two
// new module requirements is a secondary benefit: the reproducible payload build
// (scripts/lib/go-reproducible-build.sh) states it needs no network once the module
// cache is warm, and each added module widens what a build host must already hold.

import (
	"strings"
	"unicode/utf8"
)

// Emoji-sequence joiners and continuation ranges, named because their numeric values
// appear in several places in the scanner below.
const (
	variationSelector1  = 0xFE00 // first of the (non-emoji) text/variation selectors Prettier still skips
	variationSelector16 = 0xFE0F // emoji presentation selector
	zeroWidthJoiner     = 0x200D
	combiningKeycap     = 0x20E3
	skinToneFirst       = 0x1F3FB
	skinToneLast        = 0x1F3FF
	regionalIndicatorLo = 0x1F1E6
	regionalIndicatorHi = 0x1F1FF
	subdivisionFlagBase = 0x1F3F4
	tagSpec             = 0xE0020 // first of the tag characters used by subdivision flags
	tagSpecLast         = 0xE007E
	tagTerminator       = 0xE007F
)

// displayWidth reports the column width Prettier's getStringWidth assigns to s.
//
// The rule has two passes in Prettier: emoji sequences are matched and removed first,
// each contributing 1 if the matched text is a bare narrow emoji and 2 otherwise, and
// only then are the surviving code points measured individually. This function fuses the
// two into a single left-to-right scan, which is equivalent because Prettier's regex
// replacement is itself leftmost-first and never rejoins text across a removed match.
func displayWidth(s string) int {
	// Prettier's own shortcut, reproduced exactly rather than loosened to "no rune above
	// 0x7F": a control character such as TAB falls outside 0x20-0x7F and so takes the
	// slow path, where the control-character rule below gives it width 0.
	if isPrettierASCII(s) {
		return len(s)
	}

	width := 0
	for i := 0; i < len(s); {
		if end, ok := emojiUnitEnd(s, i); ok {
			width += emojiUnitWidth(s[i:end])
			i = end
			continue
		}

		r, size := utf8.DecodeRuneInString(s[i:])
		i += size
		switch {
		case r <= 0x1F, r >= 0x7F && r <= 0x9F: // control characters
		case r >= 0x300 && r <= 0x36F: // combining marks — this range only
		case r >= variationSelector1 && r <= variationSelector16: // variation selectors
		case inRanges(eastAsianWideRanges, r):
			width += 2
		default:
			width++
		}
	}
	return width
}

// isPrettierASCII reports whether every code point of s lies in 0x20-0x7F, the condition
// under which Prettier returns the string's length untouched.
func isPrettierASCII(s string) bool {
	return !strings.ContainsFunc(s, func(r rune) bool { return r < 0x20 || r > 0x7F })
}

// emojiUnitWidth scores one matched emoji sequence.
//
// Prettier tests the whole matched text against the narrow list, and every entry in that
// list is a single bare code point — so a sequence of two or more code points can never
// be narrow, and neither can a narrow-list character followed by U+FE0F. That asymmetry
// is deliberate upstream and load-bearing here: "©" is 1 but "©️" is 2.
func emojiUnitWidth(unit string) int {
	r, size := utf8.DecodeRuneInString(unit)
	if size == len(unit) && inRunes(narrowEmojiRunes, r) {
		return 1
	}
	return 2
}

// emojiUnitEnd reports the end offset of the emoji sequence starting at s[start], and
// whether one starts there at all. A true result always reports an offset strictly past
// start, which is what keeps displayWidth's scan advancing.
//
// This reproduces the shape of emoji-regex's grammar — keycap, regional-indicator pair,
// or a pictograph with its presentation selector, skin tone, tag sequence and any
// ZWJ-joined continuations — rather than the generated regex's full enumeration of every
// sanctioned ZWJ combination. The consequence is one bounded, deliberate divergence: a
// ZWJ join that Unicode does not sanction (say two thumbs-up joined by U+200D) is one
// unit here and three pieces to Prettier. Every sequence in emoji-test.txt is scored
// identically, which is what the differential corpus in testdata/prettier-widths.tsv
// pins; issue titles carry real emoji, not synthetic joins.
//
// Widening this to "any grapheme cluster" would be wrong in the other direction: a
// cluster like "A" plus U+20E3 is not an emoji match to Prettier, which scores its parts
// separately.
func emojiUnitEnd(s string, start int) (int, bool) {
	r, size := utf8.DecodeRuneInString(s[start:])
	if size == 0 {
		return start, false
	}
	i := start + size

	// Keycaps are the one place emoji-regex accepts an ASCII base, and it accepts it
	// only when the terminator is present — a bare "1" must stay width 1.
	if r == '#' || r == '*' || (r >= '0' && r <= '9') {
		j := i
		if next, nextSize := utf8.DecodeRuneInString(s[j:]); nextSize > 0 && next == variationSelector16 {
			j += nextSize
		}
		if next, nextSize := utf8.DecodeRuneInString(s[j:]); nextSize > 0 && next == combiningKeycap {
			return j + nextSize, true
		}
		return start, false
	}

	// Flags are matched as a pair; a lone regional indicator is not an emoji match and
	// falls through to the per-code-point pass.
	if r >= regionalIndicatorLo && r <= regionalIndicatorHi {
		if next, nextSize := utf8.DecodeRuneInString(s[i:]); nextSize > 0 &&
			next >= regionalIndicatorLo && next <= regionalIndicatorHi {
			return i + nextSize, true
		}
		return start, false
	}

	if !inRanges(emojiUnitStartRanges, r) {
		return start, false
	}

	i = emojiElementEnd(s, r, i)
	for {
		next, nextSize := utf8.DecodeRuneInString(s[i:])
		if nextSize == 0 || next != zeroWidthJoiner {
			return i, true
		}
		joined, joinedSize := utf8.DecodeRuneInString(s[i+nextSize:])
		if joinedSize == 0 || !inRanges(emojiUnitStartRanges, joined) {
			// A trailing joiner belongs to no sequence; leave it for the per-code-point
			// pass, which is where Prettier measures it too.
			return i, true
		}
		i = emojiElementEnd(s, joined, i+nextSize+joinedSize)
	}
}

// emojiElementEnd consumes the modifiers that may follow a pictograph base: the
// emoji-presentation selector, a skin tone, or a subdivision-flag tag sequence. base is
// the pictograph already consumed and i is the offset just past it.
//
// The selector and the skin tone are alternatives, not a sequence, and each is admitted
// only for the bases emoji-regex actually admits it for. Accepting a skin tone after any
// base is the trap here: "©" followed by U+1F3FB is two separate matches to Prettier
// (1 + 2), not one modified emoji.
func emojiElementEnd(s string, base rune, i int) int {
	if r, size := utf8.DecodeRuneInString(s[i:]); size > 0 {
		switch {
		case r == variationSelector16 && inRanges(emojiPresentationBaseRanges, base):
			i += size
		case r >= skinToneFirst && r <= skinToneLast && inRanges(emojiModifierBaseRanges, base):
			i += size
		}
	}

	// Tag sequences exist only for subdivision flags, whose sole base is U+1F3F4
	// (confirmed by enumerating the whole code point space against emoji-regex), and only
	// when terminated: an unterminated run of tag characters is not part of the match, so
	// it must not be consumed here.
	if base != subdivisionFlagBase {
		return i
	}
	j := i
	for {
		r, size := utf8.DecodeRuneInString(s[j:])
		if size == 0 || r < tagSpec || r > tagSpecLast {
			break
		}
		j += size
	}
	if j > i {
		if r, size := utf8.DecodeRuneInString(s[j:]); size > 0 && r == tagTerminator {
			return j + size
		}
	}
	return i
}
