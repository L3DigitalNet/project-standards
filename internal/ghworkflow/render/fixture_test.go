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
// metacharacters and a bare URL, an aligned PR table next to an unalignable issue
// table, and a PR with no governing issue.
const (
	fixtureTarget = "L3DigitalNet/example-repo"
	fixtureRead   = "2026-08-06T12:00:00Z"
)

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
