package render_test

import (
	"regexp"
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

func TestLedgerMatchesGolden(t *testing.T) {
	t.Parallel()

	got := render.Ledger(fixtureSnapshot(t))
	if want := golden(t, "ledger.md"); got != want {
		t.Errorf("Ledger() mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
}

// An empty repository still renders every section: the layout is what makes summaries
// comparable across repositories, so sections state their emptiness rather than vanish.
func TestLedgerWithNoOpenWorkMatchesGolden(t *testing.T) {
	t.Parallel()

	empty := render.NewSnapshot(fixtureTarget, fixtureReadAt(t), nil, nil)
	if got, want := render.Ledger(empty), golden(t, "ledger-empty.md"); got != want {
		t.Errorf("Ledger() mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
}

// FR-019 requires the generated-file header to carry the tool version and a do-not-edit
// notice, and the summary to carry neither.
func TestLedgerHeaderCarriesVersionAndNotice(t *testing.T) {
	t.Parallel()

	ledger := render.Ledger(fixtureSnapshot(t))
	for _, want := range []string{render.Version, "Do not edit"} {
		if !strings.Contains(ledger, want) {
			t.Errorf("ledger header missing %q:\n%s", want, ledger)
		}
	}
	if summary := render.Summary(fixtureSnapshot(t)); strings.Contains(summary, "Do not edit") {
		t.Error("summary carries the ledger's generated-file notice; only the written file is generated content")
	}
}

// Issue #154: the committed file must be a function of work state alone. The read time
// is the only input that moves between two reads of an unchanged repository, so a ledger
// that renders identically across a shifting read timestamp is a ledger that produces no
// diff on regeneration — which is the property the consumer actually needs.
//
// The summary is checked in the same test as the deliberate contrast: it is printed, not
// committed, so it keeps the timestamp the ledger gave up.
func TestLedgerBodyIsIndependentOfTheReadTimestamp(t *testing.T) {
	t.Parallel()

	first := fixtureSnapshot(t)
	later := render.NewSnapshot(fixtureTarget, fixtureReadAt(t).Add(72*time.Hour),
		first.Issues, first.PullRequests)

	if got, want := render.Ledger(later), render.Ledger(first); got != want {
		t.Errorf("the ledger changed with the read timestamp alone\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
	if ledger := render.Ledger(first); strings.Contains(ledger, fixtureRead) {
		t.Errorf("the ledger body carries the read timestamp:\n%s", ledger)
	}
	if summary := render.Summary(first); !strings.Contains(summary, fixtureRead) {
		t.Errorf("the summary lost its read timestamp:\n%s", summary)
	}
}

var (
	headingPattern = regexp.MustCompile(`(?m)^## (.+)$`)
	tocPattern     = regexp.MustCompile(`(?m)^- \[(.+)\]\(#(.+)\)$`)
)

// FR-019: a table of contents of anchor links to every section. Deriving the expectation
// from the rendered headings rather than a hardcoded list is what keeps a future section
// from silently escaping the contract.
func TestLedgerTableOfContentsCoversEverySection(t *testing.T) {
	t.Parallel()

	ledger := render.Ledger(fixtureSnapshot(t))

	anchors := map[string]string{}
	for _, match := range tocPattern.FindAllStringSubmatch(ledger, -1) {
		anchors[match[1]] = match[2]
	}

	sections := 0
	for _, match := range headingPattern.FindAllStringSubmatch(ledger, -1) {
		heading := match[1]
		if heading == "Contents" {
			// The table of contents does not link to itself.
			continue
		}
		sections++
		anchor, ok := anchors[heading]
		if !ok {
			t.Errorf("section %q has no table-of-contents entry", heading)
			continue
		}
		if want := slug(heading); anchor != want {
			t.Errorf("section %q anchor = %q, want %q", heading, anchor, want)
		}
	}
	if sections != 4 {
		t.Errorf("rendered %d linkable sections, want 4", sections)
	}
	if len(anchors) != sections {
		t.Errorf("table of contents has %d entries for %d sections", len(anchors), sections)
	}
	if strings.Contains(render.Summary(fixtureSnapshot(t)), "## Contents") {
		t.Error("summary carries a table of contents; the TOC is a navigation aid for the written file only")
	}
}

// slug reproduces GitHub's heading-anchor rule for the headings this layout emits.
func slug(heading string) string {
	return strings.ToLower(strings.ReplaceAll(heading, " ", "-"))
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
