package render_test

import (
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

func TestSummaryMatchesGolden(t *testing.T) {
	t.Parallel()

	got := render.Summary(fixtureSnapshot(t))
	if want := golden(t, "summary.md"); got != want {
		t.Errorf("Summary() mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
}

// An empty repository still renders every section: the layout is what makes summaries
// comparable across repositories, so sections state their emptiness rather than vanish.
// There is no golden for this shape because the empty lines, not the whole document, are
// the contract summary-format.md states.
func TestSummaryWithNoOpenWorkStillRendersEverySection(t *testing.T) {
	t.Parallel()

	rendered := render.Summary(render.NewSnapshot(fixtureTarget, fixtureReadAt(t), nil, nil))
	cases := []struct {
		name string
		want string
	}{
		{"attention heading", "## Needs attention"},
		{"attention empty line", "Nothing needs attention"},
		{"issues heading", "## Issues"},
		{"issues empty line", "No open issues."},
		{"pull requests heading", "## Pull requests"},
		{"pull requests empty line", "No open pull requests."},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if !strings.Contains(rendered, tc.want) {
				t.Errorf("the empty summary is missing %q:\n%s", tc.want, rendered)
			}
		})
	}
}

// The summary is printed, never committed, so it carries the read timestamp that the
// removed generated-document subcommand deliberately gave up (issue #154). Nothing else in
// the document may move between two reads of unchanged work state.
func TestSummaryCarriesTheReadTimestampAndNothingElseThatMoves(t *testing.T) {
	t.Parallel()

	first := fixtureSnapshot(t)
	later := render.NewSnapshot(fixtureTarget, fixtureReadAt(t).Add(72*time.Hour),
		first.Issues, first.PullRequests)

	if summary := render.Summary(first); !strings.Contains(summary, fixtureRead) {
		t.Errorf("the summary lost its read timestamp:\n%s", summary)
	}
	got := strings.Replace(render.Summary(later), fixtureReadAt(t).Add(72*time.Hour).Format(time.RFC3339), fixtureRead, 1)
	if want := render.Summary(first); got != want {
		t.Errorf("the summary changed by more than its read timestamp\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
}

func TestReceiptsMatchGolden(t *testing.T) {
	t.Parallel()

	snapshot := fixtureSnapshot(t)
	cases := []struct {
		name   string
		item   render.WorkItem
		golden string
	}{
		{"issue without gaps", snapshot.Issues[0], "receipt-issue.txt"},
		{"issue with gaps", snapshot.Issues[1], "receipt-issue-gaps.txt"},
		{"pull request without gaps", snapshot.PullRequests[0], "receipt-pr.txt"},
		{"pull request with gaps", snapshot.PullRequests[1], "receipt-pr-gaps.txt"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got, want := render.Receipt(tc.item), golden(t, tc.golden); got != want {
				t.Errorf("Receipt() mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
			}
		})
	}
}

// The four needs-attention categories are fixed in count and order (summary-format.md).
func TestAttentionCategoriesAreOrdered(t *testing.T) {
	t.Parallel()

	got := []string{}
	for _, item := range fixtureSnapshot(t).Attention() {
		got = append(got, item.Category)
	}
	want := []string{
		render.CategoryBlocked,
		render.CategoryNeedsDefinition,
		render.CategoryNeedsDefinition,
		render.CategoryTerminalMismatch,
		render.CategoryTargetDatePassed,
	}
	if strings.Join(got, "|") != strings.Join(want, "|") {
		t.Errorf("attention categories = %v, want %v", got, want)
	}
}

// A Workflow value that disagrees with the GitHub state is the mismatch class; agreement
// is not reported. Both directions are checked so the rule cannot degrade into "always
// report" or "never report".
func TestTerminalMismatchDetection(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name        string
		workflow    string
		state       string
		stateReason string
		mismatch    bool
	}{
		{"done but open", "Done", "open", "", true},
		{"done and closed as completed", "Done", "closed", "completed", false},
		{"done but closed as not planned", "Done", "closed", "not_planned", true},
		{"dropped and closed as not planned", "Dropped", "closed", "not_planned", false},
		{"in progress but closed", "In progress", "closed", "completed", true},
		{"in progress and open", "In progress", "open", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			item := render.WorkItem{
				Kind: render.KindIssue, Number: 1, Title: "t", Type: "Task",
				State: tc.state, StateReason: tc.stateReason,
				HasAcceptanceCriteria: true,
				Fields:                map[string]string{render.FieldWorkflow: tc.workflow},
			}
			snapshot := render.NewSnapshot(fixtureTarget, fixtureReadAt(t), []render.WorkItem{item}, nil)

			found := false
			for _, attention := range snapshot.Attention() {
				if attention.Category == render.CategoryTerminalMismatch {
					found = true
				}
			}
			if found != tc.mismatch {
				t.Errorf("terminal mismatch reported = %v, want %v", found, tc.mismatch)
			}
		})
	}
}

// A target date is passed relative to the read timestamp, not to wall-clock time at
// render: the summary must describe the state it read.
func TestTargetDatePassedUsesTheReadTimestamp(t *testing.T) {
	t.Parallel()

	item := render.WorkItem{
		Kind: render.KindIssue, Number: 1, Title: "t", Type: "Task", State: "open",
		HasAcceptanceCriteria: true,
		Fields: map[string]string{
			render.FieldWorkflow:   "In progress",
			render.FieldTargetDate: "2026-08-06",
		},
	}
	sameDay := render.NewSnapshot(fixtureTarget, fixtureReadAt(t), []render.WorkItem{item}, nil)
	if len(sameDay.Attention()) != 0 {
		t.Errorf("a target date equal to the read date is not passed: %v", sameDay.Attention())
	}

	later := render.NewSnapshot(fixtureTarget, fixtureReadAt(t).Add(48*time.Hour), []render.WorkItem{item}, nil)
	if len(later.Attention()) != 1 {
		t.Fatalf("attention = %v, want the passed target date", later.Attention())
	}
	if got := later.Attention()[0].Category; got != render.CategoryTargetDatePassed {
		t.Errorf("category = %q, want %q", got, render.CategoryTargetDatePassed)
	}
}

// Gaps are the pinning matrix applied to what is actually set, per Issue Type.
func TestGapsFollowThePinningMatrix(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		item render.WorkItem
		want []string
	}{
		{
			name: "initiative pins neither size nor execution mode",
			item: render.WorkItem{
				Kind: render.KindIssue, Type: "Initiative", HasAcceptanceCriteria: true,
				Fields: map[string]string{
					render.FieldWorkflow:   "Ready",
					render.FieldPriority:   "P1 — Next",
					render.FieldTargetDate: "2026-09-30",
				},
			},
			want: nil,
		},
		{
			name: "bug pins severity and size",
			item: render.WorkItem{
				Kind: render.KindIssue, Type: "Bug", HasAcceptanceCriteria: true,
				Fields: map[string]string{render.FieldWorkflow: "Ready"},
			},
			want: []string{"Priority", "Size", "Change risk", "Execution mode", "Severity"},
		},
		{
			name: "research does not pin change risk and target date",
			item: render.WorkItem{
				Kind: render.KindIssue, Type: "Research",
				Fields: map[string]string{
					render.FieldWorkflow:      "Ready",
					render.FieldPriority:      "P2 — Planned",
					render.FieldSize:          "S",
					render.FieldExecutionMode: "Human only",
				},
			},
			want: []string{"acceptance criteria"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := render.Gaps(tc.item)
			if !slices.Equal(got, tc.want) {
				t.Errorf("Gaps() = %v, want %v", got, tc.want)
			}
		})
	}
}
