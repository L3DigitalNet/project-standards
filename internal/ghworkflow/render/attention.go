package render

import (
	"fmt"
	"time"
)

// The four needs-attention categories, in the fixed order the layout presents them.
// There are exactly four and adding a fifth is a layout change, not an implementation
// detail: the ordering is what lets an operator compare two summaries at a glance.
const (
	CategoryBlocked          = "Blocked"
	CategoryNeedsDefinition  = "Needs definition"
	CategoryTerminalMismatch = "Terminal-sync mismatch"
	CategoryTargetDatePassed = "Target date passed"
)

var categoryOrder = []string{
	CategoryBlocked, CategoryNeedsDefinition, CategoryTerminalMismatch, CategoryTargetDatePassed,
}

// Attention is one needs-attention finding: work that is stuck, underspecified,
// inconsistent, or late.
type Attention struct {
	Category string `json:"category"`
	Kind     Kind   `json:"kind"`
	Number   int    `json:"number"`
	Title    string `json:"title"`
	// Detail is the category-specific "why", already rendered: the blocker, what is
	// missing, the divergent states, or the passed date.
	Detail string `json:"detail"`
}

// Attention derives every finding in category order, and within a category by kind then
// number, so two reads of an unchanged repository produce identical output.
func (s *Snapshot) Attention() []Attention {
	findings := map[string][]Attention{}
	add := func(category string, item WorkItem, detail string) {
		findings[category] = append(findings[category], Attention{
			Category: category,
			Kind:     item.Kind,
			Number:   item.Number,
			Title:    item.Title,
			Detail:   detail,
		})
	}

	for _, issue := range s.Issues {
		switch issue.Field(FieldWorkflow) {
		case workflowBlocked:
			// The blocking dependency is native GitHub state the tool does not read,
			// and the layout forbids inventing a value for an empty slot, so the
			// blocker is reported as unknown rather than guessed at.
			add(CategoryBlocked, issue, dash)
		case workflowNeedsDefinition:
			add(CategoryNeedsDefinition, issue, describeGaps(issue))
		}
		if detail, mismatched := terminalMismatch(issue); mismatched {
			add(CategoryTerminalMismatch, issue, detail)
		}
		if date, passed := targetDatePassed(issue, s.ReadAt); passed {
			add(CategoryTargetDatePassed, issue, date)
		}
	}

	// A pull request with no governing issue is underspecified work in exactly the sense
	// the Needs-definition category covers, and summary-format.md places it in
	// needs-attention. It goes in that category rather than a fifth one because the four
	// categories are fixed. Triviality is a judgment the tool does not make: it reports
	// the missing link and the agent decides.
	for _, pull := range s.PullRequests {
		if pull.GoverningIssue == 0 {
			add(CategoryNeedsDefinition, pull, describeGaps(pull))
		}
	}

	var ordered []Attention
	for _, category := range categoryOrder {
		ordered = append(ordered, findings[category]...)
	}
	return ordered
}

func describeGaps(item WorkItem) string {
	gaps := Gaps(item)
	if len(gaps) == 0 {
		return dash
	}
	return "missing " + joinList(gaps)
}

// terminalMismatch reports a Workflow value that disagrees with GitHub's own state.
//
// The two are maintained by different mechanisms and drift silently, which is precisely
// why the pairing is an invariant: Done means closed as completed, Dropped means closed
// as not planned, and every other value means the issue is still open. An unset Workflow
// is not compared — there is nothing to disagree with.
func terminalMismatch(item WorkItem) (string, bool) {
	workflow := item.Field(FieldWorkflow)
	if workflow == "" || item.State == "" {
		return "", false
	}

	var consistent bool
	switch workflow {
	case workflowDone:
		consistent = item.State == "closed" && item.StateReason == "completed"
	case workflowDropped:
		consistent = item.State == "closed" && item.StateReason == "not_planned"
	default:
		consistent = item.State == "open"
	}
	if consistent {
		return "", false
	}
	return fmt.Sprintf("Workflow %s vs GitHub %s/%s", workflow, item.State, orDash(item.StateReason)), true
}

// targetDatePassed compares the target date against the timestamp of the read, not
// against wall-clock time at render: a summary describes the state it read.
func targetDatePassed(item WorkItem, readAt time.Time) (string, bool) {
	value := item.Field(FieldTargetDate)
	if value == "" {
		return "", false
	}
	target, err := time.Parse(targetDateLayout, value)
	if err != nil {
		// An unparseable date is reported as-is by the table rather than raised here;
		// the tool does not fail a whole summary over one malformed field value.
		return "", false
	}
	read := readAt.UTC()
	today := time.Date(read.Year(), read.Month(), read.Day(), 0, 0, 0, 0, time.UTC)
	if !target.Before(today) {
		return "", false
	}
	return value, true
}
