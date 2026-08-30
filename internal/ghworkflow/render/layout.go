package render

import (
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
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

// attentionBody renders the needs-attention section: one line per work item per
// category, in relation.CategoryOrder (FR-030).
//
// The compression is the contract, not a formatting preference. An operator scanning the
// section acts once per work item per required action, so three findings on one PR that
// all resolve the same way are one line; the JSON envelope still carries every finding
// separately. The messages are joined in the order the engine produced them, which is
// evaluation order.
func attentionBody(s *Snapshot) string {
	if len(s.Findings) == 0 {
		return noAttention + "\n"
	}
	titles := map[itemKey]string{}
	for _, item := range append(append([]WorkItem{}, s.Issues...), s.PullRequests...) {
		titles[keyOf(item)] = item.Title
	}

	var b strings.Builder
	var current itemKey
	var messages []string
	flush := func() {
		if len(messages) == 0 {
			return
		}
		fmt.Fprintf(&b, "- **%s** — %s #%d %s: %s\n", current.category, current.kind,
			current.number, EscapeText(titles[itemKey{kind: current.kind, number: current.number}]), EscapeText(strings.Join(messages, "; ")))
		messages = nil
	}
	for _, finding := range s.Findings {
		if key := findingKey(finding); key != current {
			flush()
			current = key
		}
		messages = append(messages, finding.Message)
	}
	flush()
	return b.String()
}

// itemKey is one compressed line's identity: the work item and the action category. The
// title is looked up separately because a finding carries no title — the engine reports
// on numbers, and only the snapshot knows what they are called.
type itemKey struct {
	category relation.Category
	kind     relation.Kind
	number   int
}

func findingKey(f relation.Finding) itemKey {
	return itemKey{category: f.Category, kind: f.Kind, number: f.Number}
}

// keyOf is the title-lookup key for a work item, with the category left zero: a title
// belongs to the item, not to the category it is reported under.
func keyOf(item WorkItem) itemKey {
	kind := relation.KindIssue
	if item.Kind == KindPullRequest {
		kind = relation.KindPullRequest
	}
	return itemKey{kind: kind, number: item.Number}
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
