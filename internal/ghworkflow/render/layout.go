package render

import (
	"fmt"
	"strings"
)

// Section headings, fixed and in this order. summary-format.md (spec FR-017) declares
// them as the summary's normative layout, so changing one changes the contract with
// every consumer relaying the output verbatim.
const (
	sectionAttention = "Needs attention"
	sectionIssues    = "Issues"
	sectionPulls     = "Pull requests"
)

// The empty-section lines. A section with nothing in it says so in one line rather than
// disappearing: a layout whose shape depends on the data is not comparable across reads.
const (
	noAttention = "Nothing needs attention: no blocked, underspecified, out-of-sync, or overdue work."
	noIssues    = "No open issues."
	noPulls     = "No open pull requests."
)

var (
	issueColumns = []string{"Issue", "Type", "Title", "Workflow", "Priority", "Size / Severity", "Execution mode"}
	pullColumns  = []string{"PR", "Title", "Governing issue", "State", "CI", "Risk notes"}
)

type section struct {
	heading string
	body    string
}

// Summary renders the operator summary: attention first, then the inventories. It is a
// read and prints to stdout for the agent to relay verbatim.
//
// The 1.6 layout ended with a "Discovered follow-ups" tail that the tool could never
// populate — it reports live GitHub state and discovers nothing — so every summary
// carried a section whose only content was a sentence explaining its own emptiness.
// 1.7 removes it (FR-017): creation and follow-up ceremony is not observed state, and a
// fixed section that is always empty trains readers to skip the tail of the report.
func Summary(s *Snapshot) string {
	return document(s, []string{"Read " + s.scopeLine()})
}

// scopeLine is the timestamp and the counts the tables below cover.
func (s *Snapshot) scopeLine() string {
	return s.Timestamp() + " · " + s.countsLine()
}

// countsLine is the scope without the timestamp: what the tables below cover, and
// nothing that moves when the underlying work state has not.
func (s *Snapshot) countsLine() string {
	return fmt.Sprintf("%s · %s",
		plural(len(s.Issues), "open issue", "open issues"),
		plural(len(s.PullRequests), "open PR", "open PRs"))
}

func document(s *Snapshot, header []string) string {
	sections := []section{
		{sectionAttention, attentionBody(s)},
		{sectionIssues, issuesBody(s)},
		{sectionPulls, pullsBody(s)},
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# %s — work state\n", s.Target)
	for _, line := range header {
		fmt.Fprintf(&b, "\n%s\n", line)
	}
	for _, sec := range sections {
		fmt.Fprintf(&b, "\n## %s\n\n%s", sec.heading, sec.body)
	}
	return b.String()
}

func attentionBody(s *Snapshot) string {
	findings := s.Attention()
	if len(findings) == 0 {
		return noAttention + "\n"
	}
	var b strings.Builder
	for _, finding := range findings {
		fmt.Fprintf(&b, "- **%s** — #%d %s: %s\n",
			finding.Category, finding.Number, EscapeText(finding.Title), EscapeText(finding.Detail))
	}
	return b.String()
}

func issuesBody(s *Snapshot) string {
	if len(s.Issues) == 0 {
		return noIssues + "\n"
	}
	rows := make([][]string, 0, len(s.Issues))
	for _, issue := range s.Issues {
		rows = append(rows, []string{
			fmt.Sprintf("#%d", issue.Number),
			orDash(issue.Type),
			issue.Title,
			orDash(issue.Field(FieldWorkflow)),
			orDash(issue.Field(FieldPriority)),
			orDash(issue.SizeOrSeverity()),
			orDash(issue.Field(FieldExecutionMode)),
		})
	}
	return Table(issueColumns, rows)
}

func pullsBody(s *Snapshot) string {
	if len(s.PullRequests) == 0 {
		return noPulls + "\n"
	}
	rows := make([][]string, 0, len(s.PullRequests))
	for _, pull := range s.PullRequests {
		governing := dash
		if pull.GoverningIssue != 0 {
			governing = fmt.Sprintf("#%d", pull.GoverningIssue)
		}
		rows = append(rows, []string{
			fmt.Sprintf("#%d", pull.Number),
			pull.Title,
			governing,
			orDash(pull.StateLabel()),
			orDash(pull.CI),
			orDash(pull.RiskNotes),
		})
	}
	return Table(pullColumns, rows)
}

func plural(count int, singular, many string) string {
	if count == 1 {
		return fmt.Sprintf("%d %s", count, singular)
	}
	return fmt.Sprintf("%d %s", count, many)
}
