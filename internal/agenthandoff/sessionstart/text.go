package sessionstart

import (
	"strings"
	"unicode/utf8"
)

// This file ports the Python hook's byte-budget arithmetic. Every limit in the protocol
// is expressed in UTF-8 *bytes* while the truncation points must land on rune
// boundaries, so the two decoders below are not interchangeable and neither may be
// replaced with a naive slice:
//
//   - validPrefix implements Python's strict `bytes.decode("utf-8")` retry loop, which
//     yields the longest valid prefix and silently drops a partial trailing rune.
//   - decodeReplace implements `bytes.decode("utf-8", errors="replace")`, which keeps
//     every byte position accounted for by substituting U+FFFD.
//
// Swapping one for the other changes the emitted context, and the payload's conformance
// tests compare against the 1.9 Python output byte for byte.

// validPrefix returns the longest prefix of data that decodes as strict UTF-8.
//
// A truncated multi-byte rune at the end of data is dropped entirely rather than
// replaced: the caller is cutting a byte budget, not repairing damaged input.
func validPrefix(data []byte) []byte {
	for i := 0; i < len(data); {
		r, size := utf8.DecodeRune(data[i:])
		// size > 1 admits a legitimately encoded U+FFFD, which is not an error.
		if r == utf8.RuneError && size <= 1 {
			return data[:i]
		}
		i += size
	}
	return data
}

// truncateUTF8 clips data to at most limit bytes on a rune boundary.
func truncateUTF8(data []byte, limit int) string {
	if limit < 0 {
		limit = 0
	}
	if limit > len(data) {
		limit = len(data)
	}
	return string(validPrefix(data[:limit]))
}

// maximalSubpart returns the length of the maximal ill-formed subsequence at the head of
// data, per the Unicode 16.0 §3.9 recommendation that CPython's replace handler follows.
//
// The distinction matters: a truncated three-byte rune such as {0xE2, 0x82} is ONE
// ill-formed subpart and yields a single U+FFFD, whereas decoding byte-by-byte would
// yield two. Go's utf8.DecodeRune reports the byte-by-byte answer, so this range table
// cannot be replaced by a DecodeRune call.
func maximalSubpart(data []byte) int {
	lead := data[0]
	var want int
	lo, hi := byte(0x80), byte(0xBF)
	switch {
	case lead >= 0xC2 && lead <= 0xDF:
		want = 2
	case lead == 0xE0:
		want, lo = 3, 0xA0
	case lead >= 0xE1 && lead <= 0xEC:
		want = 3
	case lead == 0xED:
		want, hi = 3, 0x9F
	case lead >= 0xEE && lead <= 0xEF:
		want = 3
	case lead == 0xF0:
		want, lo = 4, 0x90
	case lead >= 0xF1 && lead <= 0xF3:
		want = 4
	case lead == 0xF4:
		want, hi = 4, 0x8F
	default:
		// Continuation bytes, 0xC0/0xC1, and 0xF5..0xFF never begin a sequence.
		return 1
	}
	n := 1
	for n < want && n < len(data) {
		c := data[n]
		if n == 1 {
			if c < lo || c > hi {
				break
			}
		} else if c < 0x80 || c > 0xBF {
			break
		}
		n++
	}
	return n
}

// decodeReplace decodes data as UTF-8, substituting U+FFFD for each ill-formed
// subsequence.
func decodeReplace(data []byte) string {
	var out strings.Builder
	out.Grow(len(data))
	for i := 0; i < len(data); {
		r, size := utf8.DecodeRune(data[i:])
		if r != utf8.RuneError || size > 1 {
			out.Write(data[i : i+size])
			i += size
			continue
		}
		out.WriteRune(utf8.RuneError)
		i += maximalSubpart(data[i:])
	}
	return out.String()
}

// clampText trims text to limit bytes, appending note when anything was removed.
//
// note is charged against the same budget, so an oversized note legitimately consumes
// the entire allowance and leaves an empty body.
func clampText(text string, limit int, note string) string {
	if len(text) <= limit {
		return text
	}
	bodyLimit := limit - len(note)
	if bodyLimit < 0 {
		bodyLimit = 0
	}
	return truncateUTF8([]byte(text), bodyLimit) + note
}

// clampWrapped trims context to limit bytes while preserving the session_context
// envelope.
//
// The envelope is load-bearing: the harness treats the tags as the data boundary, so a
// naive tail cut would ship an unterminated block and let repository text escape into
// the instruction stream. When the tags are absent — the degraded path where an earlier
// failure already replaced the body — there is no envelope to preserve and the text is
// clamped whole.
func clampWrapped(context string, limit int) string {
	if len(context) <= limit {
		return context
	}
	note := truncationNote
	if !strings.HasPrefix(context, openTag) || !strings.HasSuffix(context, closeTag) {
		return clampText(context, limit, note)
	}
	inner := context[len(openTag) : len(context)-len(closeTag)]
	innerLimit := limit - len(openTag) - len(closeTag)
	if innerLimit < 0 {
		innerLimit = 0
	}
	return openTag + clampText(inner, innerLimit, note) + closeTag
}
