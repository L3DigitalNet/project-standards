package render_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
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
			// Underscore-bearing on purpose: the summary golden this fixture drives has to
			// carry a bare intraword underscore (#177) — a plain title would let a
			// regression that escapes every underscore pass unnoticed.
			Title: "Support runner_labels for python_tooling check.yml",
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
			State: "open", CI: "passing", Relationship: "Final", GoverningIssue: 12,
		},
		{
			Kind: render.KindPullRequest, Number: 22,
			Title: "Tidy the fixture corpus",
			URL:   "https://github.com/L3DigitalNet/example-repo/pull/22",
			State: "open", Draft: true, CI: "failing", Relationship: "Supporting", GoverningIssue: 14,
		},
		{
			Kind: render.KindPullRequest, Number: 23,
			Title: emojiWidthTitle,
			URL:   "https://github.com/L3DigitalNet/example-repo/pull/23",
			State: "open", CI: "passing", Relationship: "Standalone",
		},
	}

	snapshot := render.NewSnapshot(fixtureTarget, fixtureReadAt(t), issues, pulls)
	snapshot.AddFindings(fixturePullRequestFindings(t)...)
	return snapshot
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

// fixtureSchema is the Issue Type and Workflow vocabulary the rendering surfaces resolve
// a live Issue Type against from 1.7. Only the two sections these surfaces consult are
// reproduced: the full delivered schema is `audit`'s oracle, not this package's.
const fixtureSchema = `issue_types:
  - Bug
  - Feature
  - Task
  - Initiative
  - Research

issue_fields:
  Workflow:
    type: single_select
    values:
      - Inbox
      - Needs definition
      - Ready
      - In progress
      - Blocked
      - In review
      - Done
      - Dropped
`

// The three fixture pull-request bodies, as Go strings.
//
// command_test.go carries the same three inside its JSON wire payloads, escaped. The two
// copies are pinned against each other by the summary golden: both tests render it, so a
// body that drifts on one side produces a different finding set and fails one of them.
const (
	pull21Body = "## Governing work\n\nFinal: #12\n\nCloses #12\n"
	pull22Body = "## Governing work\n\nSupporting: #14\n"
	pull23Body = "## Governing work\n\nStandalone\n\n## Change risk\n\nR2 — Moderate\n"
)

// fixturePullRequestFindings reproduces, from the model side, the per-PR engine findings
// the command derives from a live topology.
//
// This is the model half of the same agreement fixtureSnapshot and command_test.go's wire
// payloads already have: one golden, reached twice. The topologies below therefore state
// the evidence the harness serves — squash-only merge settings, branch protection that
// resolves but enforces nothing, and mergeability GitHub has not computed — because a
// model fixture that assumed friendlier evidence would render a golden the command can
// never produce.
func fixturePullRequestFindings(t *testing.T) []relation.Finding {
	t.Helper()

	targetDate := func(value string) *time.Time {
		parsed, err := time.Parse(render.DateLayout, value)
		if err != nil {
			t.Fatalf("time.Parse(%q) error = %v", value, err)
		}
		return &parsed
	}
	issue12 := &relation.Issue{
		Number: 12, State: "open", IssueType: "Bug",
		Workflow: "Blocked", TargetDate: targetDate("2026-08-01"),
	}
	issue14 := &relation.Issue{Number: 14, State: "open", IssueType: "Feature", Workflow: "Needs definition"}
	evidence := relation.EnforcementEvidence{Known: true, Source: "none"}
	settings := relation.RepositoryMergeSettings{AllowSquash: true, Known: true}

	topologies := []relation.Topology{
		{
			PullRequest: relation.PullRequest{Number: 21, State: "open", Body: pull21Body,
				BaseRef: "main", HeadSHA: "aaa111", MergeStateStatus: "CLEAN"},
			GoverningIssue: issue12, MergeSettings: settings, Enforcement: evidence,
			Now: fixtureReadAt(t),
		},
		{
			PullRequest: relation.PullRequest{Number: 22, State: "open", Draft: true, Body: pull22Body,
				BaseRef: "main", HeadSHA: "bbb222", MergeStateStatus: "CLEAN"},
			GoverningIssue: issue14, Now: fixtureReadAt(t),
		},
		{
			PullRequest: relation.PullRequest{Number: 23, State: "open", Body: pull23Body,
				BaseRef: "main", HeadSHA: "ccc333", MergeStateStatus: "CLEAN"},
			MergeSettings: settings, Enforcement: evidence, Now: fixtureReadAt(t),
		},
	}

	var findings []relation.Finding
	for _, topology := range topologies {
		result := relation.Evaluate(topology, "")
		findings = append(findings, render.FilterByObservedState(topology.PullRequest, result.Findings)...)
	}
	return findings
}
