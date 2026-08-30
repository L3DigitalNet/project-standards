package render

// The observed-state finding derivation the two read-only surfaces share (FR-017,
// FR-018, FR-030).
//
// Payload 1.6 had its own four-value needs-attention vocabulary here
// ("Terminal-sync mismatch" and friends) and its own idea of what a pull request's
// governing issue was. Both are gone: relation.CategoryOrder is now the only category
// vocabulary, relation.Finding the only finding shape, and relation.ParseBody the only
// authority on a PR's governing work. What remains in this file is the part the pure
// engine cannot derive, because it is about an Issue observed on its own rather than
// through a pull request: an Issue with no PR still appears in a summary, and its
// Blocked, underspecified, out-of-sync, and overdue states are exactly the "independent
// Issue findings" FR-017 requires to stay visible.

import (
	"fmt"
	"sort"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// IssueFindings derives the observed-state findings of one issue read on its own.
//
// now is the read timestamp rather than wall-clock time at render, so a summary reports
// the state it read and two renderings of one snapshot cannot disagree about what is
// overdue.
//
// These four codes are as stable as the engine's own: automation branches on them, and
// GHW-ISSUE-STRUCTURAL-TARGET-DATE-PASSED is deliberately the same code the engine
// raises for a governing Issue's passed target date, so the same condition never reaches
// an operator under two names.
func IssueFindings(item WorkItem, now time.Time) []relation.Finding {
	if item.Kind != KindIssue {
		return nil
	}
	var findings []relation.Finding
	add := func(f relation.Finding) {
		f.Kind, f.Number = relation.KindIssue, item.Number
		findings = append(findings, f)
	}

	switch item.Field(FieldWorkflow) {
	case workflowBlocked:
		add(relation.Finding{
			Code: "GHW-ISSUE-STRUCTURAL-BLOCKED", Phase: relation.PhaseStructural,
			Category: relation.CategoryBlocked, Effect: relation.EffectBlocksReady,
			// The blocking dependency is native GitHub state this read does not fetch,
			// and inventing one would be worse than naming none.
			Message:     "the issue is Blocked",
			Remediation: "Resolve or record the blocker, then set a nonterminal Workflow.",
		})
	case workflowNeedsDefinition:
		add(relation.Finding{
			Code: "GHW-ISSUE-STRUCTURAL-DEFINITION-INCOMPLETE", Phase: relation.PhaseStructural,
			Category: relation.CategoryNeedsDefinition, Effect: relation.EffectBlocksReady,
			Message:     "the issue is Needs definition: " + describeGaps(item),
			Remediation: "Complete the definition, then set a nonterminal Workflow.",
		})
	}

	if detail, mismatched := terminalMismatch(item); mismatched {
		add(relation.Finding{
			Code: "GHW-ISSUE-STRUCTURAL-TERMINAL-MISMATCH", Phase: relation.PhaseStructural,
			Category: relation.CategorySynchronizationRequired,
			Effect:   relation.EffectRequiresSynchronization,
			Message:  detail,
			Remediation: "Close, reopen, or re-set Workflow through `gh-workflow close`, `reopen`, " +
				"or `set` so the two agree.",
		})
	}
	if date, passed := targetDatePassed(item, now); passed {
		add(relation.Finding{
			Code: "GHW-ISSUE-STRUCTURAL-TARGET-DATE-PASSED", Phase: relation.PhaseStructural,
			Category: relation.CategoryTargetDatePassed, Effect: relation.EffectAdvisory,
			Message:     fmt.Sprintf("the target date %s has passed", date),
			Remediation: "Re-plan the issue or move the Target date to a date you intend to meet.",
		})
	}
	return findings
}

// FilterByObservedState keeps the findings a summary or receipt shows for a pull request
// in the state it was read in (FR-017, FR-031).
//
// Two rules, and the second is not a special case of the first. Phase filtering follows
// relation.ObservedStateFilter, so ordinary unfinished Ready content on a draft does not
// read as failure before the PR claims readiness. Findings about the governing Issue are
// then kept whatever their phase, because they describe an independent work item whose
// problems are real regardless of how far this PR has travelled — dropping them would
// hide a closed or untyped governing Issue behind a draft.
func FilterByObservedState(pr relation.PullRequest, findings []relation.Finding) []relation.Finding {
	visible := map[relation.Phase]bool{}
	for _, phase := range relation.ObservedStateFilter(pr) {
		visible[phase] = true
	}
	kept := make([]relation.Finding, 0, len(findings))
	for _, finding := range findings {
		if finding.Kind == relation.KindIssue || visible[finding.Phase] {
			kept = append(kept, finding)
		}
	}
	return kept
}

// describeGaps renders the pinned fields and acceptance criteria an issue is missing.
func describeGaps(item WorkItem) string {
	gaps := Gaps(item)
	if len(gaps) == 0 {
		return "nothing is missing from the pinned fields"
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
	return fmt.Sprintf("Workflow %s contradicts GitHub %s/%s",
		workflow, item.State, orDash(item.StateReason)), true
}

// targetDatePassed compares the target date against the timestamp of the read, not
// against wall-clock time at render: a summary describes the state it read.
func targetDatePassed(item WorkItem, readAt time.Time) (string, bool) {
	value := item.Field(FieldTargetDate)
	if value == "" {
		return "", false
	}
	target, err := time.Parse(DateLayout, value)
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

// OrderFindings sorts findings into the FR-030 display order: category first in
// relation.CategoryOrder, then kind, then work-item number.
//
// Cross-file contract: this is the same ordering cli.compressFindings applies to the
// envelope's human view. The two must agree, because the cross-surface equivalence tests
// compare a summary item against `check` on the same pull request — a different order
// here would make one surface's report unreadable next to the other's. A category outside
// the vocabulary sorts last rather than sharing rank 0, so ordering never depends on map
// iteration.
func OrderFindings(findings []relation.Finding) []relation.Finding {
	rank := map[relation.Category]int{}
	for i, category := range relation.CategoryOrder {
		rank[category] = i
	}
	of := func(c relation.Category) int {
		if r, ok := rank[c]; ok {
			return r
		}
		return len(relation.CategoryOrder)
	}
	ordered := append([]relation.Finding(nil), findings...)
	sort.SliceStable(ordered, func(i, j int) bool {
		switch {
		case of(ordered[i].Category) != of(ordered[j].Category):
			return of(ordered[i].Category) < of(ordered[j].Category)
		case ordered[i].Kind != ordered[j].Kind:
			return ordered[i].Kind < ordered[j].Kind
		default:
			return ordered[i].Number < ordered[j].Number
		}
	})
	return ordered
}
