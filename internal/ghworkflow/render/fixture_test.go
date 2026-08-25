package render_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The fixture work-item set is the single input behind every golden in this package.
// One set feeding all three surfaces is what makes "same layout engine" (spec FR-022,
// plan decision D-003) a checkable property rather than three parallel renderers that
// happen to agree today. It deliberately covers every category the layout has a rule
// for: each of the four needs-attention classes, a Bug (Severity in the shared
// Size / Severity column), an Initiative (neither pinned), a title carrying markdown
// metacharacters and a bare URL, a title whose cell width depends on every branch of
// Prettier's emoji and East Asian width rule, an aligned PR table next to an unalignable
// issue table, and a PR with no governing issue.
const (
	fixtureTarget = "L3DigitalNet/example-repo"
	fixtureRead   = "2026-08-06T12:00:00Z"
)

// emojiWidthTitle is the widest cell in the one table this fixture renders in aligned
// form, so its padding — and therefore every branch of Prettier's width rule — is what
// `prettier --check` over testdata/*.md actually verifies (#185). Each token is a
// distinct case in getStringWidth: a bare narrow-list emoji, the same class of character
// forced to emoji presentation by U+FE0F, U+FE0E text presentation, a ZWJ sequence, a
// keycap, a regional-indicator flag, East Asian wide characters, and a Hebrew combining
// point that is NOT in the U+0300-U+036F range Prettier skips.
//
// Every token is scored identically by Prettier 3.8.3 and 3.9.6. Those two ship
// different narrow-emoji lists — 100 code points differ, U+270C and U+24C2 among them —
// so a token drawn from that difference would leave this golden un-checkable under one
// of the two versions.
//
// command_test.go's pull23 wire payload carries this same title; the two must stay
// identical or the fetch layer and the layout engine stop agreeing on one golden.
const emojiWidthTitle = "\u2714 \u26A0\uFE0F \u00A9\uFE0E \u00A9\uFE0F " +
	"\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466 " +
	"1\uFE0F\u20E3 \U0001F1FA\U0001F1F8 \u6F22\u5B57 \u05D0\u05B7"

func fixtureReadAt(t *testing.T) time.Time {
	t.Helper()
	at, err := time.Parse(time.RFC3339, fixtureRead)
	if err != nil {
		t.Fatalf("time.Parse(%q) error = %v", fixtureRead, err)
	}
	return at
}

func fixtureSnapshot(t *testing.T) *render.Snapshot {
	t.Helper()

	issues := []render.WorkItem{
		{
			Kind: render.KindIssue, Number: 12,
			Title: "Ledger write leaves a partial file",
			URL:   "https://github.com/L3DigitalNet/example-repo/issues/12",
			Type:  "Bug", State: "open",
			HasAcceptanceCriteria: true,
			Fields: map[string]string{
				render.FieldWorkflow:      "Blocked",
				render.FieldPriority:      "P0 — Immediate",
				render.FieldSize:          "M",
				render.FieldSeverity:      "S1 — High",
				render.FieldChangeRisk:    "R3 — High",
				render.FieldExecutionMode: "Interactive agent",
				render.FieldTargetDate:    "2026-08-01",
			},
		},
		{
			Kind: render.KindIssue, Number: 14,
			Title: "Add ledger TOC anchors",
			URL:   "https://github.com/L3DigitalNet/example-repo/issues/14",
			Type:  "Feature", State: "open",
			Fields: map[string]string{
				render.FieldWorkflow:      "Needs definition",
				render.FieldPriority:      "P2 — Planned",
				render.FieldSize:          "M",
				render.FieldExecutionMode: "Unattended agent",
			},
		},
		{
			Kind: render.KindIssue, Number: 15,
			Title: "Escape titles with | pipes, *stars*, <angles> and https://example.test/x",
			URL:   "https://github.com/L3DigitalNet/example-repo/issues/15",
			Type:  "Task", State: "open",
			HasAcceptanceCriteria: true,
			Fields: map[string]string{
				render.FieldWorkflow:      "Done",
				render.FieldPriority:      "P3 — Opportunistic",
				render.FieldSize:          "S",
				render.FieldChangeRisk:    "R1 — Low",
				render.FieldExecutionMode: "Human only",
			},
		},
		{
			Kind: render.KindIssue, Number: 16,
			Title: "Ship the github-workflow package",
			URL:   "https://github.com/L3DigitalNet/example-repo/issues/16",
			Type:  "Initiative", State: "open",
			HasAcceptanceCriteria: true,
			Fields: map[string]string{
				render.FieldWorkflow: "In progress",
				render.FieldPriority: "P1 — Next",
				// Far enough out that the fixture stays "not passed" for the life of
				// this test, whatever the clock says when a command-level run reads it.
				render.FieldTargetDate: "2099-12-31",
			},
		},
	}

	pulls := []render.WorkItem{
		{
			Kind: render.KindPullRequest, Number: 21,
			Title: "Add the render engine",
			URL:   "https://github.com/L3DigitalNet/example-repo/pull/21",
			State: "open", CI: "passing", GoverningIssue: 12,
		},
		{
			Kind: render.KindPullRequest, Number: 22,
			Title: "Tidy the fixture corpus",
			URL:   "https://github.com/L3DigitalNet/example-repo/pull/22",
			State: "open", Draft: true, CI: "failing",
		},
		{
			Kind: render.KindPullRequest, Number: 23,
			Title: emojiWidthTitle,
			URL:   "https://github.com/L3DigitalNet/example-repo/pull/23",
			State: "open", CI: "passing", GoverningIssue: 14,
		},
	}

	return render.NewSnapshot(fixtureTarget, fixtureReadAt(t), issues, pulls)
}

func golden(t *testing.T, name string) string {
	t.Helper()
	// #nosec G304 G703 -- the name is a literal from this package's own test table.
	data, err := os.ReadFile(filepath.Join("testdata", name))
	if err != nil {
		t.Fatalf("reading golden %s: %v", name, err)
	}
	return string(data)
}
