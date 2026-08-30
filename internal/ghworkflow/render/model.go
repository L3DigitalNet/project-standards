// Package render is the tool's one layout engine and the two read-only surfaces that
// present it: `summary` prints the operator summary, and `receipt` prints a
// single-item creation receipt.
//
// One engine, several surfaces, is the point (plan decision D-003, spec FR-022). The
// layouts are defined in the package's own summary-format.md reference, and their value
// is comparability across sessions, agents, and repositories; renderers that happened to
// agree on the day they were written would lose that within one change. So every surface
// here builds the same Snapshot model, derives the same needs-attention findings from
// it, and shares the same table, escaping, and field-formatting code. A single golden
// fixture set drives them all.
//
// Payload 1.5 removed the third surface, the generated-document subcommand, which wrote
// a generated docs/GH-WORKFLOWS.md into the consumer repository. Nothing here writes a file any
// more: both surfaces print, so the atomic-replace machinery and the table of contents
// that only the written file needed are gone. What survives is the Prettier and
// markdownlint fidelity constraint (spec FR-019) — the printed output is still pasted
// into Markdown documents, which is why table layout reproduces Prettier's own alignment
// rule and every cell is escaped rather than trusted.
package render

import (
	"sort"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// Kind distinguishes the two work-item shapes. They share the model because they share
// the layout, but they carry different fields: only issues have an Issue Type and Issue
// Field values, and only pull requests have a draft flag, CI state, and a governing
// issue.
type Kind string

// Work-item kinds. The values are the tokens the receipt layout prints.
const (
	KindIssue       Kind = "issue"
	KindPullRequest Kind = "PR"
)

// The seven organization Issue Fields, named exactly as the organization schema names
// them: these strings are map keys against live API values, not labels.
const (
	FieldWorkflow      = "Workflow"
	FieldPriority      = "Priority"
	FieldSize          = "Size"
	FieldChangeRisk    = "Change risk"
	FieldExecutionMode = "Execution mode"
	FieldTargetDate    = "Target date"
	FieldSeverity      = "Severity"
)

// Terminal Workflow values, which must stay paired with the GitHub closed state and its
// close reason.
const (
	workflowDone            = "Done"
	workflowDropped         = "Dropped"
	workflowBlocked         = "Blocked"
	workflowNeedsDefinition = "Needs definition"
)

// dash is the layout's empty-value token: an unset optional value is shown, never
// invented and never dropped, so the operator can see the hole.
const dash = "—"

// DateLayout is the format GitHub stores and returns date Issue Field values in. It is
// exported because the write path validates operator input against the same format, and
// two independently written copies of a date layout drift silently.
const DateLayout = "2006-01-02"

// WorkItem is one issue or pull request, reduced to what the three layouts present.
type WorkItem struct {
	Kind   Kind   `json:"kind"`
	Number int    `json:"number"`
	Title  string `json:"title"`
	URL    string `json:"url"`
	// Type is the Issue Type; empty for pull requests, which have none.
	Type string `json:"type,omitempty"`
	// State and StateReason are GitHub's native lifecycle, which the Workflow field is
	// checked against rather than trusted to match.
	State       string `json:"state"`
	StateReason string `json:"state_reason,omitempty"`
	// Fields holds Issue Field values by field name; an unset field is absent.
	Fields map[string]string `json:"fields,omitempty"`
	// HasAcceptanceCriteria records whether the body carries a populated acceptance
	// criteria section, which is a gap the receipt and summary both report.
	HasAcceptanceCriteria bool `json:"has_acceptance_criteria"`

	// Pull-request-only state.
	Draft bool `json:"draft,omitempty"`
	// Merged separates a merged pull request from an abandoned one; State closes both,
	// so the receipt header cannot tell them apart without it (FR-018).
	Merged bool   `json:"merged,omitempty"`
	CI     string `json:"ci,omitempty"`
	// Relationship is the declared governing-work relationship ("Final", "Supporting",
	// "Standalone", or "" when the body declares none) and GoverningIssue the Issue it
	// names. Both come from relation.ParseBody, which is the sole authority (D15): the
	// 1.6 closing-keyword heuristic that inferred a governing issue from `Closes #N` is
	// gone, because a closing keyword is evidence about a declaration, never a
	// substitute for one.
	Relationship   string `json:"relationship,omitempty"`
	GoverningIssue int    `json:"governing_issue,omitempty"`
	RiskNotes      string `json:"risk_notes,omitempty"`
}

// Field returns the value of an Issue Field, or the empty string when unset.
func (w WorkItem) Field(name string) string { return w.Fields[name] }

// SizeOrSeverity is the shared Size / Severity column: Severity for Bugs, Size for every
// other Issue Type. They occupy one column because the layout treats them as the same
// question — how big is this — asked differently of defects.
func (w WorkItem) SizeOrSeverity() string {
	if w.Type == "Bug" {
		return w.Field(FieldSeverity)
	}
	return w.Field(FieldSize)
}

// StateLabel is the pull-request State column: a draft is a distinct operator-facing
// state, not a decoration on "open".
func (w WorkItem) StateLabel() string {
	if w.Draft {
		return "Draft"
	}
	if w.State == "" {
		return ""
	}
	// Decoded rather than sliced: State is API text, and capitalizing its first byte would
	// cut a multi-byte rune in half the moment GitHub returns anything but ASCII.
	first, size := utf8.DecodeRuneInString(w.State)
	return string(unicode.ToUpper(first)) + w.State[size:]
}

// Snapshot is one read of a repository's open work: the input every surface renders.
type Snapshot struct {
	Target       string     `json:"target"`
	ReadAt       time.Time  `json:"read_at"`
	Issues       []WorkItem `json:"issues"`
	PullRequests []WorkItem `json:"pull_requests"`
	// Findings is the observed-state finding set the summary presents, in
	// OrderFindings order. NewSnapshot fills in the independent Issue findings, which
	// are derivable from the snapshot alone; the command appends each pull request's
	// engine findings, which are not — they need the per-PR topology.
	Findings []relation.Finding `json:"-"`
}

// AddFindings merges more findings into the snapshot and restores the display order.
//
// It is additive rather than a setter because the two halves arrive from different
// places: dropping the Issue half by assigning over it is exactly the regression FR-017's
// "independent Issue findings remain visible" rules out.
func (s *Snapshot) AddFindings(findings ...relation.Finding) {
	// Deduplicated on identity, because one condition legitimately arrives twice: an
	// Issue's passed Target date is raised by the snapshot's own Issue derivation and
	// again by the engine for every PR that Issue governs. Reporting it once per PR would
	// make a summary's attention count grow with the number of pull requests rather than
	// with the number of problems.
	seen := map[relation.Finding]bool{}
	merged := make([]relation.Finding, 0, len(s.Findings)+len(findings))
	for _, finding := range append(append([]relation.Finding(nil), s.Findings...), findings...) {
		if seen[finding] {
			continue
		}
		seen[finding] = true
		merged = append(merged, finding)
	}
	s.Findings = OrderFindings(merged)
}

// NewSnapshot orders the items and resolves the cross-references between them.
//
// Ordering is deliberate: the API returns issues newest-first, but a generated summary that
// reshuffles its rows on every refresh produces a diff on every commit and stops being
// reviewable. Sorting by number makes the generated file stable under an unchanged
// repository.
func NewSnapshot(target string, readAt time.Time, issues, pulls []WorkItem) *Snapshot {
	snapshot := &Snapshot{
		Target:       target,
		ReadAt:       readAt.UTC(),
		Issues:       append([]WorkItem(nil), issues...),
		PullRequests: append([]WorkItem(nil), pulls...),
	}
	sort.SliceStable(snapshot.Issues, func(i, j int) bool {
		return snapshot.Issues[i].Number < snapshot.Issues[j].Number
	})
	sort.SliceStable(snapshot.PullRequests, func(i, j int) bool {
		return snapshot.PullRequests[i].Number < snapshot.PullRequests[j].Number
	})
	for _, issue := range snapshot.Issues {
		snapshot.AddFindings(IssueFindings(issue, snapshot.ReadAt)...)
	}

	// A pull request has no risk field of its own; the risk that matters is the one
	// already assessed on the work it implements, so it is carried across from the
	// governing issue rather than restated or guessed.
	byNumber := make(map[int]WorkItem, len(snapshot.Issues))
	for _, issue := range snapshot.Issues {
		byNumber[issue.Number] = issue
	}
	for i, pull := range snapshot.PullRequests {
		if pull.RiskNotes != "" || pull.GoverningIssue == 0 {
			continue
		}
		if governing, ok := byNumber[pull.GoverningIssue]; ok {
			snapshot.PullRequests[i].RiskNotes = governing.Field(FieldChangeRisk)
		}
	}
	return snapshot
}

// Timestamp is the read time as it appears in every header.
func (s *Snapshot) Timestamp() string { return s.ReadAt.Format(time.RFC3339) }

// pinnedFields is the field-pinning matrix from the package's field-vocabulary
// reference: which Issue Fields each Issue Type is expected to carry. It is duplicated
// here rather than read from org-schema.yaml because the schema describes the fields and
// their values, not which Type pins which field — that mapping has no machine-readable
// home. Optional pins (Target date on Bug and Research) are not requirements and are
// absent below. An unknown Type falls back to the two fields that apply to every Type.
var pinnedFields = map[string][]string{
	"Bug":        {FieldWorkflow, FieldPriority, FieldSize, FieldChangeRisk, FieldExecutionMode, FieldSeverity},
	"Feature":    {FieldWorkflow, FieldPriority, FieldSize, FieldChangeRisk, FieldExecutionMode, FieldTargetDate},
	"Task":       {FieldWorkflow, FieldPriority, FieldSize, FieldChangeRisk, FieldExecutionMode, FieldTargetDate},
	"Initiative": {FieldWorkflow, FieldPriority, FieldTargetDate},
	"Research":   {FieldWorkflow, FieldPriority, FieldSize, FieldExecutionMode},
}

// fieldOrder is the vocabulary's own field order, used so gap lists read the same way
// every time regardless of which fields happen to be missing.
var fieldOrder = []string{
	FieldWorkflow, FieldPriority, FieldSize, FieldChangeRisk,
	FieldExecutionMode, FieldTargetDate, FieldSeverity,
}

// PinnedFields returns the fields an Issue Type is expected to carry, in vocabulary
// order.
func PinnedFields(issueType string) []string {
	pinned, ok := pinnedFields[issueType]
	if !ok {
		return []string{FieldWorkflow, FieldPriority}
	}
	ordered := make([]string, 0, len(pinned))
	for _, field := range fieldOrder {
		for _, candidate := range pinned {
			if field == candidate {
				ordered = append(ordered, field)
			}
		}
	}
	return ordered
}

// Gaps names what the item is still missing: pinned fields without values and absent
// acceptance criteria for an issue, a missing governing-issue link for a pull request.
// It returns nil when nothing is missing — the receipt reports that as `Gaps: none`
// rather than omitting the line, because a silent receipt is indistinguishable from an
// unchecked one.
func Gaps(item WorkItem) []string {
	if item.Kind == KindPullRequest {
		if item.GoverningIssue == 0 {
			return []string{"a governing issue link"}
		}
		return nil
	}

	var gaps []string
	for _, field := range PinnedFields(item.Type) {
		if item.Field(field) == "" {
			gaps = append(gaps, field)
		}
	}
	if !item.HasAcceptanceCriteria {
		gaps = append(gaps, "acceptance criteria")
	}
	return gaps
}

// joinList renders a list the way the layouts read it out: "a", "a and b", "a, b, and c".
func joinList(items []string) string {
	switch len(items) {
	case 0:
		return ""
	case 1:
		return items[0]
	case 2:
		return items[0] + " and " + items[1]
	default:
		return strings.Join(items[:len(items)-1], ", ") + ", and " + items[len(items)-1]
	}
}

// orDash renders an unset value as the layout's empty token.
func orDash(value string) string {
	if value == "" {
		return dash
	}
	return value
}
