package render

import (
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// Receipt renders the header of a single-item receipt: what the item is, where it lives,
// and the state it was observed in.
//
// From 1.7 the receipt is an observed-state projection rather than creation ceremony
// (FR-018), so this header is followed by the item's findings in the shared envelope
// rendering — the same bytes `check` produces for the same findings. What the header adds
// is the one thing a finding list cannot state: which state the item was actually in when
// it was read, because "no findings" means something different for a draft than for a
// merged pull request.
//
// It is plain text rather than markdown — it is read in a terminal, not linted into a
// file — so cell escaping deliberately does not apply here. Unset values print as the
// layout's empty token so the operator sees the hole rather than a silently short line.
func Receipt(item WorkItem) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s #%d — %s\n%s\n", item.Kind, item.Number, item.Title, item.URL)

	if item.Kind == KindPullRequest {
		fmt.Fprintf(&b, "State: %s | Relationship: %s | CI: %s\n",
			PullRequestState(item), relationshipLabel(item), orDash(item.CI))
		return b.String()
	}

	fmt.Fprintf(&b, "State: %s | Type: %s | Workflow: %s | Priority: %s\n",
		nativeState(item), orDash(item.Type), orDash(item.Field(FieldWorkflow)),
		orDash(item.Field(FieldPriority)))
	fmt.Fprintf(&b, "Size / Severity: %s | Change risk: %s\n",
		orDash(item.SizeOrSeverity()), orDash(item.Field(FieldChangeRisk)))
	fmt.Fprintf(&b, "Execution mode: %s | Target date: %s\n",
		orDash(item.Field(FieldExecutionMode)), orDash(item.Field(FieldTargetDate)))
	fmt.Fprintf(&b, "Gaps: %s\n", gapsLine(item))
	return b.String()
}

// The four observed pull-request states FR-018 requires a receipt header to distinguish.
// They are not decorations on open/closed: each one admits a different next action, and
// conflating merged with closed-unmerged is exactly the confusion FR-029's disposition
// record exists to prevent.
const (
	StateDraft          = "draft"
	StateReady          = "ready"
	StateMerged         = "merged"
	StateClosedUnmerged = "closed-unmerged"
)

// PullRequestState names the observed state of a pull-request work item.
//
// Merged is tested before closed because GitHub closes a PR when it merges it, so state
// alone never separates the two.
func PullRequestState(item WorkItem) string {
	switch {
	case item.Merged:
		return StateMerged
	case item.State == "closed":
		return StateClosedUnmerged
	case item.Draft:
		return StateDraft
	default:
		return StateReady
	}
}

// relationshipLabel renders the declared governing work, or the empty token when the body
// declares none. An undeclared relationship is a finding, not a blank to be filled in
// with a guess (D15).
func relationshipLabel(item WorkItem) string {
	switch {
	case item.Relationship == "":
		return dash
	case item.GoverningIssue != 0:
		return fmt.Sprintf("%s: #%d", item.Relationship, item.GoverningIssue)
	default:
		return item.Relationship
	}
}

// nativeState renders an issue's GitHub state with its close reason, which is the half of
// the terminal-pairing invariant the Workflow value is checked against.
func nativeState(item WorkItem) string {
	if item.State == "closed" && item.StateReason != "" {
		return "closed/" + item.StateReason
	}
	return orDash(item.State)
}

func gapsLine(item WorkItem) string {
	gaps := Gaps(item)
	if len(gaps) == 0 {
		return "none"
	}
	return "missing " + joinList(gaps)
}

// ReceiptDocument is the JSON form of a receipt: the DR-004 envelope plus the projected
// work item.
//
// The embedded envelope is flattened by encoding/json, so `schema_version`, `command`,
// `result`, `target`, `gate`, `findings`, and `steps` sit at the top level exactly as
// every other command emits them, and `item` is an additive projection alongside — the
// same relationship `items` has to the summary envelope. A consumer that only knows the
// envelope reads this document without special-casing it.
type ReceiptDocument struct {
	cli.Envelope
	Item WorkItem `json:"item"`
	// Gaps is what the item is still missing, always present as an array. A silently
	// absent `gaps` member is indistinguishable from an item with nothing missing, which
	// is the one thing a receipt must never be ambiguous about.
	Gaps []string `json:"gaps"`
}

// newReceiptDocument assembles a receipt document with its gaps list materialized.
func newReceiptDocument(envelope cli.Envelope, item WorkItem) *ReceiptDocument {
	gaps := Gaps(item)
	if gaps == nil {
		gaps = []string{}
	}
	return &ReceiptDocument{Envelope: envelope, Item: item, Gaps: gaps}
}

// SummaryDocument is the JSON form of the operator summary: the DR-004 envelope, whose
// `findings` retains every finding, plus the `items` projection of the work the tables
// present. The projection never omits a finding and no finding is reported only there.
type SummaryDocument struct {
	cli.Envelope
	Items  SummaryItems `json:"items"`
	Counts Counts       `json:"counts"`
	ReadAt string       `json:"read_at"`
}

// SummaryItems is the inventory half of the summary document.
type SummaryItems struct {
	Issues       []WorkItem `json:"issues"`
	PullRequests []WorkItem `json:"pull_requests"`
}

// Counts are the scope-header counts, carried in JSON so a consumer does not have to
// recount what the header already states.
type Counts struct {
	OpenIssues       int `json:"open_issues"`
	OpenPullRequests int `json:"open_pull_requests"`
	Findings         int `json:"findings"`
}

// NewSummaryDocument builds the JSON view of a snapshot around an already-built envelope.
func NewSummaryDocument(envelope cli.Envelope, s *Snapshot) *SummaryDocument {
	items := SummaryItems{Issues: s.Issues, PullRequests: s.PullRequests}
	if items.Issues == nil {
		items.Issues = []WorkItem{}
	}
	if items.PullRequests == nil {
		items.PullRequests = []WorkItem{}
	}
	return &SummaryDocument{
		Envelope: envelope,
		Items:    items,
		Counts: Counts{
			OpenIssues:       len(s.Issues),
			OpenPullRequests: len(s.PullRequests),
			Findings:         len(envelope.Findings),
		},
		ReadAt: s.Timestamp(),
	}
}

// reportResult classifies a rendered report.
//
// `summary` and `receipt` are reports, not gates: IR-005 has them exit 0 whenever they
// successfully render, findings included. The result class still states what was found,
// so a consumer can branch on content without parsing the finding list — the exit code is
// about whether the render succeeded, the class about what it says.
func reportResult(findings []relation.Finding) cli.Result {
	if len(findings) == 0 {
		return cli.ResultClear
	}
	return cli.ResultDomainFinding
}

// NewCreationReceipt builds the receipt document a mutation emits for the item it just
// created or changed.
//
// It carries no findings by construction: the creating command reports what it wrote, and
// FR-018 removed the mandatory creation ceremony that used to gate on it. An operator who
// wants the observed-state verdict runs `receipt` or `check`, which is where the engine
// runs.
func NewCreationReceipt(command string, target cli.Target, item WorkItem) *ReceiptDocument {
	return newReceiptDocument(cli.NewEnvelope(command, cli.ResultClear, target), item)
}

// CreationReceipt renders the human receipt a mutation prints for the item it just
// created or changed: what now exists, what it carries, and what is still missing.
//
// It opens with "Created" and stays a byte contract with payload 1.4 (FR-022). The
// observed-state Receipt above is a different report with a different job — merging the
// two would make one of them lie about what just happened.
func CreationReceipt(item WorkItem) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Created %s #%d — %s\n%s\n\n", item.Kind, item.Number, item.Title, item.URL)
	if item.Kind == KindPullRequest {
		fmt.Fprintf(&b, "Governing issue: %s | Draft: %s | CI: %s\n",
			relationshipLabel(item), yesNo(item.Draft), orDash(item.CI))
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

func yesNo(value bool) string {
	if value {
		return "yes"
	}
	return "no"
}
