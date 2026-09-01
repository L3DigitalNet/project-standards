package relation

import "time"

// Topology is the complete live picture one evaluation needs: the pull request, the
// Issue it declares (when it declares one and the read resolved it), the sibling open
// Finals of that Issue, the repository's merge settings, the branch-protection
// evidence, and the clock.
//
// It is a plain value with no methods that fetch anything. The command layer assembles
// it from one bounded set of reads (NFR-008 bounds the call count) and the engine
// answers from that snapshot alone, so a gate never issues a read midway and never
// reaches a verdict from two inconsistent points in time.
//
// Cross-package contract: internal/ghworkflow/ghapi must be able to populate every
// field from GitHub REST/GraphQL. Changing a field here is a change to that client's
// obligations — locate the populating code in ghapi before finishing an edit.
type Topology struct {
	PullRequest PullRequest
	// GoverningIssue is nil when the PR is Standalone, declares nothing, or declares an
	// Issue the read could not resolve. Nil is not "no problem": the structural
	// predicates distinguish the three cases from the parsed declaration.
	GoverningIssue *Issue
	// SiblingOpenFinals holds the numbers of OTHER open PRs whose body declares a Final
	// on the same Issue. The one-open-Final rule of FR-027 is cardinality across PRs,
	// which no single PR's body can show, so the command supplies it.
	SiblingOpenFinals []int
	MergeSettings     RepositoryMergeSettings
	Enforcement       EnforcementEvidence
	// Now is injected rather than read from the clock so Target-date findings are
	// reproducible in tests and identical across the reads of one command.
	Now time.Time
	// TrustedAuthors are the logins whose PR comments count as disposition evidence:
	// the authenticated actor, plus whatever allowlist the caller adds. The engine reads
	// no identity of its own, so a caller that leaves this empty gets no evidence at all
	// — deliberately fail-closed, because the alternative default is the 1.9 behavior
	// where any commenter could record a binding disposition.
	//
	// Comparison is case-insensitive (GitHub logins are case-preserving but not
	// case-sensitive); see trustedAuthor in evaluate.go, which owns the rule.
	TrustedAuthors []string
}

// PullRequest is the observed state of the PR under evaluation.
type PullRequest struct {
	Number int
	// State is GitHub's native state, "open" or "closed". Merged PRs are closed, so
	// State alone never distinguishes merged from abandoned — Merged does.
	State  string
	Draft  bool
	Merged bool
	// MergedAt and ClosedAt are nil when the event has not happened. They are carried
	// for evidence rendering, not for predicate logic, which uses Merged and State.
	MergedAt         *time.Time
	ClosedAt         *time.Time
	Body             string
	Title            string
	BaseRef          string
	HeadRef          string
	HeadSHA          string
	AutoMergeEnabled bool
	AutoMergeMethod  string
	// Mergeable is nil while GitHub is still computing mergeability. Nil is unknown,
	// not mergeable: Merge fails closed on it (ERR-013's fail-closed principle).
	Mergeable *bool
	// MergeStateStatus is the GraphQL mergeStateStatus. "" means the read did not
	// supply it and is treated as unknown rather than as a passing state.
	MergeStateStatus string
	// ReviewDecision is the GraphQL reviewDecision ("APPROVED", "CHANGES_REQUESTED",
	// "REVIEW_REQUIRED", or "" when the repository requires no review).
	ReviewDecision string
	RequiredChecks []CheckState
	Labels         []string
	// Comments are needed only for the Post-merge/disposition predicate, which looks up
	// the `Final-Disposition:` record FR-034 writes. Commands may leave this empty when
	// the gate cannot reach post-merge.
	Comments []Comment
}

// Terminal reports whether the PR has reached an immutable outcome. Terminal PRs carry
// evidence, not obligations: their structural contradictions become evidence-integrity
// findings (EC-014) instead of blocking findings.
func (p PullRequest) Terminal() bool { return p.Merged || p.State == "closed" }

// ClosedUnmerged reports the abandoned-PR case, which FR-029 requires to carry an
// explicit disposition because no lifecycle outcome may be inferred from closure.
func (p PullRequest) ClosedUnmerged() bool { return p.State == "closed" && !p.Merged }

// CheckState is one required status check or check run.
type CheckState struct {
	Name string
	// Status is the run state ("queued", "in_progress", "completed").
	Status string
	// Conclusion is meaningful only once Status is "completed" ("success", "failure",
	// "neutral", "skipped", "cancelled", "timed_out", "action_required").
	Conclusion string
}

// Comment is one PR comment, carried for disposition-record lookup.
type Comment struct {
	Author    string
	Body      string
	CreatedAt time.Time
}

// Issue is the governing Issue as read.
type Issue struct {
	Number int
	State  string
	// StateReason is GitHub's native close reason ("completed", "not_planned", "").
	StateReason string
	// IssueType is the recognized ordinary Issue Type name, or "" when the Issue has no
	// type or carries one the baseline schema does not recognize as ordinary work. The
	// engine never reads org-schema.yaml — recognition happens in the caller, which
	// holds the schema, and the engine treats "" as "no usable type" (FR-023).
	IssueType string
	// Workflow is the field value name, "" when unset.
	Workflow string
	// TargetDate is nil when the field is unset.
	TargetDate *time.Time
	// IsPullRequestShaped records that the Issue read returned an object carrying a
	// `pull_request` member. Issue routes must reject those (FR-023): a PR number
	// answers the Issues API successfully, so without this flag a PR silently
	// impersonates its governing Issue.
	IsPullRequestShaped bool
}

// RepositoryMergeSettings is the repository's allowed merge methods, used by FR-033's
// fixed preference order.
type RepositoryMergeSettings struct {
	AllowSquash bool
	AllowRebase bool
	AllowMerge  bool
	// Known is false when the settings read did not succeed or was not attempted. All
	// three booleans are then meaningless, and Merge must not read "no method allowed"
	// out of three false values.
	Known bool
}

// EnforcementEvidence is the live required-check and review protection in force.
type EnforcementEvidence struct {
	// Known is false when protection could not be established from an otherwise
	// successful read — including NFR-007's unexplained pagination truncation. Merge
	// fails closed on it (ERR-013) and never infers that no protection exists.
	Known                bool
	RequiredStatusChecks []string
	RequiresReview       bool
	// Source names where the evidence came from (for example "branch-protection" or
	// "rulesets"), so a finding can say what was consulted.
	Source string
}
