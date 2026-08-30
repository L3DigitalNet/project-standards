package render_test

import (
	"fmt"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
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
	later.AddFindings(fixturePullRequestFindings(t)...)

	if summary := render.Summary(first); !strings.Contains(summary, fixtureRead) {
		t.Errorf("the summary lost its read timestamp:\n%s", summary)
	}
	got := strings.Replace(render.Summary(later), fixtureReadAt(t).Add(72*time.Hour).Format(time.RFC3339), fixtureRead, 1)
	if want := render.Summary(first); got != want {
		t.Errorf("the summary changed by more than its read timestamp\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
}

// The receipt header states the observed state, which is the whole of what a finding
// list cannot say: "no findings" means something different for a draft than for a merged
// pull request, and closed-unmerged is not merged however GitHub spells the two (FR-018).
func TestReceiptHeaderStatesTheObservedState(t *testing.T) {
	t.Parallel()

	base := render.WorkItem{
		Kind: render.KindPullRequest, Number: 31, Title: "Add the render engine",
		URL: "https://github.com/L3DigitalNet/example-repo/pull/31", CI: "passing",
		Relationship: "Final", GoverningIssue: 12,
	}
	for _, tc := range []struct {
		name  string
		shape func(render.WorkItem) render.WorkItem
		want  string
	}{
		{"draft Final", func(i render.WorkItem) render.WorkItem {
			i.State, i.Draft = "open", true
			return i
		}, render.StateDraft},
		{"ready Final", func(i render.WorkItem) render.WorkItem {
			i.State = "open"
			return i
		}, render.StateReady},
		{"merged Final", func(i render.WorkItem) render.WorkItem {
			i.State, i.Merged = "closed", true
			return i
		}, render.StateMerged},
		{"closed-unmerged Final without a disposition", func(i render.WorkItem) render.WorkItem {
			i.State = "closed"
			return i
		}, render.StateClosedUnmerged},
		{"Supporting", func(i render.WorkItem) render.WorkItem {
			i.State, i.Relationship, i.GoverningIssue = "open", "Supporting", 14
			return i
		}, render.StateReady},
		{"Standalone R4", func(i render.WorkItem) render.WorkItem {
			i.State, i.Relationship, i.GoverningIssue = "open", "Standalone", 0
			return i
		}, render.StateReady},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			item := tc.shape(base)
			header := render.Receipt(item)
			if !strings.Contains(header, "State: "+tc.want) {
				t.Errorf("header does not state %q:\n%s", tc.want, header)
			}
			// The declared relationship is reported, never inferred: a Standalone PR has
			// no governing issue and the header must show that rather than a number
			// borrowed from a closing keyword (D15).
			wantRelationship := item.Relationship
			if item.GoverningIssue != 0 {
				wantRelationship = fmt.Sprintf("%s: #%d", item.Relationship, item.GoverningIssue)
			}
			if !strings.Contains(header, "Relationship: "+wantRelationship) {
				t.Errorf("header does not state relationship %q:\n%s", wantRelationship, header)
			}
		})
	}
}

// Findings are presented in relation.CategoryOrder, which is the FR-030 display order.
// The order is an operator-visible contract, not formatting: two summaries are compared
// at a glance only when the same class of problem sits in the same place in both.
func TestFindingCategoriesFollowTheDisplayOrder(t *testing.T) {
	t.Parallel()

	got := []relation.Category{}
	for _, finding := range fixtureSnapshot(t).Findings {
		got = append(got, finding.Category)
	}
	// The assertion is on the shape of the sequence, not its length: what FR-030 fixes is
	// that every finding of one category is contiguous and the categories appear in
	// display order, however many findings the fixture happens to produce.
	seen := map[relation.Category]bool{}
	last := relation.Category("")
	rank := map[relation.Category]int{}
	for i, category := range relation.CategoryOrder {
		rank[category] = i
	}
	for _, category := range got {
		if category == last {
			continue
		}
		if seen[category] {
			t.Fatalf("category %q reappears after %q; findings = %v", category, last, got)
		}
		if last != "" && rank[category] <= rank[last] {
			t.Fatalf("category %q follows %q, which is out of display order", category, last)
		}
		seen[category], last = true, category
	}
	for _, want := range []relation.Category{
		relation.CategoryBlocked, relation.CategoryNeedsDefinition,
		relation.CategoryAdmissionBlocked, relation.CategorySynchronizationRequired,
		relation.CategoryTargetDatePassed,
	} {
		if !seen[want] {
			t.Errorf("the fixture produced no %q finding; categories = %v", want, got)
		}
	}
}

// OrderFindings must be a total order over the vocabulary even when a category outside
// it arrives: an unknown category sorting by map iteration would make two renderings of
// one snapshot differ.
func TestOrderFindingsSortsUnknownCategoriesLast(t *testing.T) {
	t.Parallel()

	findings := []relation.Finding{
		{Category: "Invented", Kind: relation.KindIssue, Number: 1},
		{Category: relation.CategoryTargetDatePassed, Kind: relation.KindIssue, Number: 2},
		{Category: relation.CategoryBlocked, Kind: relation.KindPullRequest, Number: 3},
		{Category: relation.CategoryBlocked, Kind: relation.KindIssue, Number: 4},
	}
	var got []string
	for _, finding := range render.OrderFindings(findings) {
		got = append(got, fmt.Sprintf("%s/%s#%d", finding.Category, finding.Kind, finding.Number))
	}
	want := []string{"Blocked/issue#4", "Blocked/pull_request#3", "Target date passed/issue#2", "Invented/issue#1"}
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Errorf("order = %v, want %v", got, want)
	}
}

// The observed-state filter is the whole of FR-017's per-state rule, so it is checked as
// a matrix rather than through one example: a draft must not be judged on Ready content
// it has not claimed to have finished, a terminal PR must not be re-judged on Ready and
// Merge predicates about state that no longer exists, and a finding about the governing
// Issue survives every one of those cuts because it describes an independent work item.
func TestObservedStateFilterMatrix(t *testing.T) {
	t.Parallel()

	findings := []relation.Finding{
		{Code: "S", Phase: relation.PhaseStructural, Kind: relation.KindPullRequest, Number: 1},
		{Code: "R", Phase: relation.PhaseReady, Kind: relation.KindPullRequest, Number: 1},
		{Code: "M", Phase: relation.PhaseMerge, Kind: relation.KindPullRequest, Number: 1},
		{Code: "P", Phase: relation.PhasePostMerge, Kind: relation.KindPullRequest, Number: 1},
		{Code: "I", Phase: relation.PhaseReady, Kind: relation.KindIssue, Number: 9},
	}
	for _, tc := range []struct {
		name string
		pr   relation.PullRequest
		want string
	}{
		{"draft", relation.PullRequest{State: "open", Draft: true}, "S,I"},
		{"open and ready", relation.PullRequest{State: "open"}, "S,R,M,I"},
		{"merged", relation.PullRequest{State: "closed", Merged: true}, "S,P,I"},
		{"closed unmerged", relation.PullRequest{State: "closed"}, "S,P,I"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			var got []string
			for _, finding := range render.FilterByObservedState(tc.pr, findings) {
				got = append(got, finding.Code)
			}
			if strings.Join(got, ",") != tc.want {
				t.Errorf("visible codes = %v, want %s", got, tc.want)
			}
		})
	}
}

// A Workflow value that disagrees with the GitHub state is the synchronization class;
// agreement is not reported. Both directions are checked so the rule cannot degrade into
// "always report" or "never report".
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
			found := false
			for _, finding := range render.IssueFindings(item, fixtureReadAt(t)) {
				if finding.Code == "GHW-ISSUE-STRUCTURAL-TERMINAL-MISMATCH" {
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
	if got := render.IssueFindings(item, fixtureReadAt(t)); len(got) != 0 {
		t.Errorf("a target date equal to the read date is not passed: %v", got)
	}

	later := render.IssueFindings(item, fixtureReadAt(t).Add(48*time.Hour))
	if len(later) != 1 {
		t.Fatalf("findings = %v, want the passed target date", later)
	}
	if got := later[0].Category; got != relation.CategoryTargetDatePassed {
		t.Errorf("category = %q, want %q", got, relation.CategoryTargetDatePassed)
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
