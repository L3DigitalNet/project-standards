package render

import (
	"fmt"
	"strings"
)

// Receipt renders the single-item creation receipt: header, the field values actually
// set, and the gaps line.
//
// It is plain text rather than markdown — it is read in a terminal, not linted into a
// file — so cell escaping deliberately does not apply here. The layout reports what is
// set rather than what was intended, showing an unset field as the empty token so the
// operator sees the hole, and it always ends with the gaps line: a receipt that silently
// omitted it would be indistinguishable from one where nothing was missing.
func Receipt(item WorkItem) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Created %s #%d — %s\n%s\n\n", item.Kind, item.Number, item.Title, item.URL)

	if item.Kind == KindPullRequest {
		governing := dash
		if item.GoverningIssue != 0 {
			governing = fmt.Sprintf("#%d", item.GoverningIssue)
		}
		fmt.Fprintf(&b, "Governing issue: %s | Draft: %s | CI: %s\n",
			governing, yesNo(item.Draft), orDash(item.CI))
	} else {
		fmt.Fprintf(&b, "Type: %s | Workflow: %s | Priority: %s\n",
			orDash(item.Type), orDash(item.Field(FieldWorkflow)), orDash(item.Field(FieldPriority)))
		fmt.Fprintf(&b, "Size / Severity: %s | Change risk: %s\n",
			orDash(item.SizeOrSeverity()), orDash(item.Field(FieldChangeRisk)))
		fmt.Fprintf(&b, "Execution mode: %s | Target date: %s\n",
			orDash(item.Field(FieldExecutionMode)), orDash(item.Field(FieldTargetDate)))
	}

	fmt.Fprintf(&b, "\nGaps: %s\n", gapsLine(item))
	return b.String()
}

func gapsLine(item WorkItem) string {
	gaps := Gaps(item)
	if len(gaps) == 0 {
		return "none"
	}
	return "missing " + joinList(gaps)
}

func yesNo(value bool) string {
	if value {
		return "yes"
	}
	return "no"
}

// ReceiptReport is the machine-readable form of the same receipt.
type ReceiptReport struct {
	Item WorkItem `json:"item"`
	Gaps []string `json:"gaps"`
}

// NewReceiptReport builds the JSON view of an item's receipt.
func NewReceiptReport(item WorkItem) *ReceiptReport {
	gaps := Gaps(item)
	if gaps == nil {
		gaps = []string{}
	}
	return &ReceiptReport{Item: item, Gaps: gaps}
}

// SummaryReport is the machine-readable form of the operator summary.
type SummaryReport struct {
	Target         string      `json:"target"`
	ReadAt         string      `json:"read_at"`
	Counts         Counts      `json:"counts"`
	NeedsAttention []Attention `json:"needs_attention"`
	Issues         []WorkItem  `json:"issues"`
	PullRequests   []WorkItem  `json:"pull_requests"`
}

// Counts are the scope-header counts, carried in JSON so a consumer does not have to
// recount what the header already states.
type Counts struct {
	OpenIssues       int `json:"open_issues"`
	OpenPullRequests int `json:"open_pull_requests"`
	NeedsAttention   int `json:"needs_attention"`
}

// NewSummaryReport builds the JSON view of a snapshot.
func NewSummaryReport(s *Snapshot) *SummaryReport {
	attention := s.Attention()
	if attention == nil {
		attention = []Attention{}
	}
	report := &SummaryReport{
		Target: s.Target,
		ReadAt: s.Timestamp(),
		Counts: Counts{
			OpenIssues:       len(s.Issues),
			OpenPullRequests: len(s.PullRequests),
			NeedsAttention:   len(attention),
		},
		NeedsAttention: attention,
		Issues:         s.Issues,
		PullRequests:   s.PullRequests,
	}
	if report.Issues == nil {
		report.Issues = []WorkItem{}
	}
	if report.PullRequests == nil {
		report.PullRequests = []WorkItem{}
	}
	return report
}
