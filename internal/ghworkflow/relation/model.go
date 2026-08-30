// Package relation is the shared relationship-validation engine of spec FR-030: it
// parses a pull request's canonical governing-work declaration, derives the Structural,
// Ready, Merge, and Post-merge/disposition predicates over an injected topology, and
// returns one typed finding set that every presentation surface consumes.
//
// The package is deliberately pure. It imports no GitHub client, no net/http, and no
// CLI package, and it performs no I/O: callers assemble a Topology from live reads and
// pass it in. That is what lets check, ready, merge, receipt, and summary reach exactly
// the same verdict from one implementation (FR-022) instead of each renderer
// reimplementing policy, and it is why the whole engine is testable as table data.
//
// Two design constraints from the spec are load-bearing here and must not be
// "simplified" away:
//
// Phase is derived, never persisted (D17). A Phase value exists only inside a Result
// and on a Finding, as the earliest gate at which the invariant applies. Nothing in
// this package stores or accepts a current-phase field on a work item, and adding one
// would recreate the second lifecycle store the design rejected.
//
// Relationship comes only from the canonical declaration (D15). The parser never infers
// Final, Supporting, or Standalone from closing keywords, branch names, titles, or free
// text; a closing keyword is only ever validated against an already-declared
// relationship, never used to establish one.
package relation

// Kind identifies the work item a finding is about. It is the `kind` member of the
// DR-004 envelope finding and the second token of a finding code.
type Kind string

// The two work-item kinds this engine reports on.
const (
	KindIssue       Kind = "issue"
	KindPullRequest Kind = "pull_request"
)

// Phase is one of the four derived predicate groups of FR-030. The zero value is not a
// valid phase; use ParsePhase for operator-supplied input.
type Phase string

// The four predicate groups, in evaluation order. Ready includes Structural, Merge
// includes Ready, and Post-merge is the terminal-state group rather than a replay of
// the pre-event predicates against changed post-event state.
const (
	PhaseStructural Phase = "structural"
	PhaseReady      Phase = "ready"
	PhaseMerge      Phase = "merge"
	PhasePostMerge  Phase = "post-merge"
)

// PhaseOrder lists the phases in cumulative evaluation order. Evaluate walks it, so a
// new phase is added here and nowhere else.
var PhaseOrder = []Phase{PhaseStructural, PhaseReady, PhaseMerge, PhasePostMerge}

// ParsePhase validates a `--through PHASE` value.
func ParsePhase(s string) (Phase, bool) {
	for _, phase := range PhaseOrder {
		if Phase(s) == phase {
			return phase, true
		}
	}
	return "", false
}

// rank returns the phase's position in PhaseOrder, or -1 for an unknown phase.
func (p Phase) rank() int {
	for i, phase := range PhaseOrder {
		if p == phase {
			return i
		}
	}
	return -1
}

// Category is the FR-030 action category. Classification follows the corrective action
// the operator must take, not the invariant that failed — two different invariants
// resolved by the same action share a category on purpose, because the human rendering
// compresses to one line per work item per category.
type Category string

// The six categories. CategoryOrder, not this block, is the display order.
const (
	CategoryBlocked                 Category = "Blocked"
	CategoryNeedsDefinition         Category = "Needs definition"
	CategoryAdmissionBlocked        Category = "PR admission blocked"
	CategorySynchronizationRequired Category = "Synchronization required"
	CategoryDispositionRequired     Category = "Disposition required"
	CategoryTargetDatePassed        Category = "Target date passed"
)

// CategoryOrder is the FR-030 display order. Renderers must present categories in this
// sequence; changing it changes operator-visible output contract, not formatting.
var CategoryOrder = []Category{
	CategoryBlocked,
	CategoryNeedsDefinition,
	CategoryAdmissionBlocked,
	CategorySynchronizationRequired,
	CategoryDispositionRequired,
	CategoryTargetDatePassed,
}

// Effect is the DR-004 `effect` member: what the finding does to the work item's
// forward transition. The spec fixes the member, not its vocabulary; these six values
// are this implementation's vocabulary and are as stable as the finding codes, because
// automation branches on them.
type Effect string

// The effect vocabulary.
const (
	// EffectBlocksReady prevents the PR from crossing Ready.
	EffectBlocksReady Effect = "blocks-ready"
	// EffectBlocksMerge prevents Merge admission but not Ready.
	EffectBlocksMerge Effect = "blocks-merge"
	// EffectRequiresSynchronization marks state that a deterministic paired operation
	// can converge without judgment.
	EffectRequiresSynchronization Effect = "requires-synchronization"
	// EffectRequiresDisposition marks state that needs an operator decision recorded
	// before it can converge.
	EffectRequiresDisposition Effect = "requires-disposition"
	// EffectEvidenceIntegrity marks a contradiction in immutable terminal evidence. It
	// never blocks anything: the transition already happened, and EC-014 forbids
	// rewriting the terminal PR's canonical relationship.
	EffectEvidenceIntegrity Effect = "evidence-integrity"
	// EffectAdvisory marks attention that blocks no transition.
	EffectAdvisory Effect = "advisory"
)

// Finding is one validation result. It carries no rendering: `message` states the
// observed contradiction and `remediation` states the action, and the human and JSON
// surfaces both project from these fields (FR-022).
type Finding struct {
	Code        string   `json:"code"`
	Phase       Phase    `json:"phase"`
	Category    Category `json:"category"`
	Effect      Effect   `json:"effect"`
	Kind        Kind     `json:"kind"`
	Number      int      `json:"number"`
	Message     string   `json:"message"`
	Remediation string   `json:"remediation"`
}

// Result is one evaluation of one pull request.
type Result struct {
	// Gate is the deepest phase actually evaluated, which is the envelope's `gate`.
	Gate Phase
	// Declaration is the parsed canonical declaration, exposed so a command can report
	// the relationship without reparsing the body.
	Declaration Declaration
	// Findings are in evaluation order — structural first, then ready, merge, and
	// post-merge. Renderers group by CategoryOrder; automation reads the whole slice.
	Findings []Finding
}

// Clear reports whether the gate passed with no findings, which is the `clear` result
// class and exit 0.
func (r Result) Clear() bool { return len(r.Findings) == 0 }

// Workflow values of the baseline org schema that the lifecycle rules of FR-029 name
// directly. These are exactly the values the coherence predicates branch on; the engine
// deliberately does not carry the full vocabulary, because `org-schema.yaml` is its sole
// authority and this pure package never reads it. A value outside this set is treated as
// "not lifecycle-coherent" rather than being guessed at.
const (
	WorkflowInProgress = "In progress"
	WorkflowInReview   = "In review"
	WorkflowBlocked    = "Blocked"
	WorkflowDone       = "Done"
)

// WorkflowDropped is the terminal Workflow value a dropped disposition converges to.
const WorkflowDropped = "Dropped"
