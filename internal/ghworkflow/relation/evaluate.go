package relation

import (
	"fmt"
	"regexp"
	"strings"
)

// InferGate returns the gate a bare `check --pr N` evaluates, derived from observed
// state alone (FR-031): a draft is working toward Ready, an open non-draft PR is
// working toward Merge, and a merged or closed PR has already had its event.
//
// Open state never implies Ready — that is a standing invariant, and it is why a draft
// maps to PhaseReady (the gate it must still cross) rather than to PhaseMerge.
func InferGate(pr PullRequest) Phase {
	switch {
	case pr.Terminal():
		return PhasePostMerge
	case pr.Draft:
		return PhaseReady
	default:
		return PhaseMerge
	}
}

// ObservedStateFilter returns the phases whose findings a summary or receipt shows for
// this PR (FR-017/FR-031). A draft contributes Structural findings only, so ordinary
// unfinished Ready content does not read as failure before the PR claims readiness; an
// open non-draft PR contributes the cumulative pre-event phases; a terminal PR
// contributes its Post-merge/disposition findings plus the Structural phase, which is
// where evidence-integrity findings live (EC-014) and the only way a contradiction in
// immutable terminal evidence stays visible.
func ObservedStateFilter(pr PullRequest) []Phase {
	switch {
	case pr.Terminal():
		return []Phase{PhaseStructural, PhasePostMerge}
	case pr.Draft:
		return []Phase{PhaseStructural}
	default:
		return []Phase{PhaseStructural, PhaseReady, PhaseMerge}
	}
}

// Evaluate derives the findings for one pull request up to and including `through`.
// Pass an empty or unrecognized phase to evaluate the inferred gate.
//
// Ordering is the contract: Structural, then Ready, then Merge — each cumulative over
// the last, because a PR that fails Structural has not earned a Ready verdict. The
// Post-merge group is the exception. It runs against Structural evidence only and never
// replays Ready or Merge, whose predicates are temporal: rerunning "the required checks
// must be green" against a branch that was deleted after merge manufactures findings
// about state that no longer exists and that no action can change (FR-030).
func Evaluate(t Topology, through Phase) Result {
	if through.rank() < 0 {
		through = InferGate(t.PullRequest)
	}
	decl, parsed := ParseBody(t.PullRequest.Body)
	e := &evaluation{topology: t, decl: decl}
	byPhase := map[Phase][]Finding{}
	for _, finding := range parsed {
		byPhase[finding.Phase] = append(byPhase[finding.Phase], finding)
	}

	if through == PhasePostMerge {
		e.add(byPhase[PhaseStructural]...)
		e.structural()
		e.postMerge()
		return Result{Gate: through, Declaration: decl, Findings: e.out}
	}

	for _, phase := range PhaseOrder {
		if phase.rank() > through.rank() {
			break
		}
		e.add(byPhase[phase]...)
		switch phase {
		case PhaseStructural:
			e.structural()
		case PhaseReady:
			e.ready()
		case PhaseMerge:
			e.merge()
		case PhasePostMerge:
		}
	}
	return Result{Gate: through, Declaration: decl, Findings: e.out}
}

// evaluation accumulates findings for one pass. It exists so the predicate groups stay
// small functions over shared state rather than threading a slice through every check.
type evaluation struct {
	topology Topology
	decl     Declaration
	out      []Finding
}

// add appends findings, stamping the work item a body-only finding cannot know and
// applying the terminal-evidence mapping.
//
// On a terminal PR every Structural finding becomes an evidence-integrity report:
// EC-014 forbids editing a terminal PR's canonical relationship, so a finding that told
// the operator to "fix the declaration" would demand a prohibited edit. The stable code
// is kept — it still names the invariant — while the category and effect change to the
// action actually available, which is human handling of contradictory history.
func (e *evaluation) add(findings ...Finding) {
	for _, finding := range findings {
		if finding.Kind == "" {
			finding.Kind = KindPullRequest
		}
		if finding.Kind == KindPullRequest && finding.Number == 0 {
			finding.Number = e.topology.PullRequest.Number
		}
		if finding.Kind == KindPullRequest && finding.Phase == PhaseStructural && e.topology.PullRequest.Terminal() {
			finding.Category = CategoryDispositionRequired
			finding.Effect = EffectEvidenceIntegrity
		}
		e.out = append(e.out, finding)
	}
}

// issue returns the governing Issue, or nil.
func (e *evaluation) issue() *Issue { return e.topology.GoverningIssue }

// structural validates the canonical relationship, the resolution of the governing
// Issue, one-open-Final cardinality, closing-keyword discipline, and the independent
// Issue attention that is visible at every gate.
func (e *evaluation) structural() {
	pr := e.topology.PullRequest
	if e.decl.Relationship.Governed() {
		e.governingIssueEvidence()
	}
	if e.decl.Relationship == RelationshipFinal && !pr.Terminal() && len(e.topology.SiblingOpenFinals) > 0 {
		e.add(Finding{
			Code: "GHW-PR-STRUCTURAL-FINAL-CARDINALITY", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Message: fmt.Sprintf("issue #%d already has open Final %s; an Issue may have at most one open Final PR",
				e.decl.IssueNumber, formatNumbers(e.topology.SiblingOpenFinals)),
			Remediation: "Convert this PR to `Supporting: #N`, or close the competing Final.",
		})
	}
	e.closingKeywords()
	e.targetDate()
}

// governingIssueEvidence checks that the declared Issue resolved to a usable governed
// work item.
func (e *evaluation) governingIssueEvidence() {
	issue := e.issue()
	if issue == nil {
		e.add(Finding{
			Code: "GHW-PR-STRUCTURAL-ISSUE-UNRESOLVED", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Message: fmt.Sprintf("the declared governing issue #%d does not resolve in this repository",
				e.decl.IssueNumber),
			Remediation: "Declare an existing Issue in the same repository; other-repository references are informational only.",
		})
		return
	}
	if issue.IsPullRequestShaped {
		e.add(Finding{
			Code: "GHW-PR-STRUCTURAL-ISSUE-PULL-REQUEST-SHAPED", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Message:     fmt.Sprintf("#%d is a pull request, not an Issue, so it cannot govern work", issue.Number),
			Remediation: "Declare the governing Issue's number, or declare `Standalone`.",
		})
		return
	}
	if issue.IssueType == "" {
		e.add(Finding{
			Code: "GHW-ISSUE-STRUCTURAL-TYPE-MISSING", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Kind: KindIssue, Number: issue.Number,
			Message:     "the governing issue carries no recognized ordinary Issue Type",
			Remediation: "Set an ordinary Issue Type with `gh-workflow set --issue N --type T`.",
		})
	}
	if issue.State == "closed" && !e.topology.PullRequest.Terminal() {
		e.add(Finding{
			Code: "GHW-ISSUE-STRUCTURAL-CLOSED", Phase: PhaseStructural,
			Category: CategorySynchronizationRequired, Effect: EffectRequiresSynchronization,
			Kind: KindIssue, Number: issue.Number,
			Message:     "the governing issue is closed while this PR is still open",
			Remediation: "Reopen the issue with `gh-workflow reopen --issue N --workflow VALUE`, or close this PR.",
		})
	}
}

// closingKeywords enforces FR-027: at most one closing reference, only the exact spelling
// `Closes`, only on a Final, and only naming that Final's own governing Issue.
func (e *evaluation) closingKeywords() {
	accepted := 0
	for _, keyword := range e.decl.ClosingKeywords {
		if e.decl.Relationship == RelationshipFinal && keyword.Text == "Closes" && keyword.Number == e.decl.IssueNumber {
			accepted++
			continue
		}
		e.add(Finding{
			Code: "GHW-PR-STRUCTURAL-CLOSING-KEYWORD", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Message: fmt.Sprintf("the body contains the GitHub closing reference %q #%d, which this relationship does not allow",
				keyword.Text, keyword.Number),
			Remediation: "Remove the closing keyword; only a Final may carry exactly `Closes #N` naming its own governing Issue.",
		})
	}
	if accepted > 1 {
		e.add(Finding{
			Code: "GHW-PR-STRUCTURAL-CLOSING-KEYWORD", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady,
			Message:     fmt.Sprintf("the body repeats `Closes #%d` %d times", e.decl.IssueNumber, accepted),
			Remediation: "Keep at most one closing reference.",
		})
	}
}

// targetDate reports the independent Issue attention that stays visible regardless of
// the PR's own state (FR-031). A closed issue is excluded: a passed date on finished
// work is history, not attention.
func (e *evaluation) targetDate() {
	issue := e.issue()
	if issue == nil || issue.TargetDate == nil || issue.State == "closed" {
		return
	}
	if !e.topology.Now.After(*issue.TargetDate) {
		return
	}
	e.add(Finding{
		Code: "GHW-ISSUE-STRUCTURAL-TARGET-DATE-PASSED", Phase: PhaseStructural,
		Category: CategoryTargetDatePassed, Effect: EffectAdvisory,
		Kind: KindIssue, Number: issue.Number,
		Message:     fmt.Sprintf("the target date %s has passed", issue.TargetDate.Format("2006-01-02")),
		Remediation: "Re-plan the issue or move the Target date to a date you intend to meet.",
	})
}

// ready adds the lifecycle-coherence predicates of FR-029 to the Ready gate. The PR
// contract sections and the Standalone risk line are decided by the parser and enter
// through the same phase.
func (e *evaluation) ready() {
	pr := e.topology.PullRequest
	issue := e.issue()
	if !e.decl.Relationship.Governed() || issue == nil || pr.State != "open" {
		return
	}
	switch issue.Workflow {
	case WorkflowInProgress, WorkflowInReview, WorkflowBlocked:
	default:
		e.add(Finding{
			Code: "GHW-PR-READY-LIFECYCLE-INCOHERENT", Phase: PhaseReady,
			Category: CategorySynchronizationRequired, Effect: EffectBlocksReady,
			Message: fmt.Sprintf("issue #%d is %s, which is incoherent with an open governing PR",
				issue.Number, quotedOrUnset(issue.Workflow)),
			Remediation: fmt.Sprintf("Set the issue to %q, %q, or %q with `gh-workflow set --issue N --field Workflow=VALUE`.",
				WorkflowInProgress, WorkflowInReview, WorkflowBlocked),
		})
		return
	}
	// A draft Final may sit against any of the three coherent states, and the paired
	// `ready` command performs the In progress → In review synchronization itself. The
	// finding therefore fires only for a PR that is already past Ready with the
	// synchronization missing, which is exactly the state EC-011 leaves behind when the
	// Issue write succeeded and the PR write did not — reported, never rolled back.
	if e.decl.Relationship == RelationshipFinal && !pr.Draft && issue.Workflow == WorkflowInProgress {
		e.add(Finding{
			Code: "GHW-PR-READY-FINAL-WORKFLOW", Phase: PhaseReady,
			Category: CategorySynchronizationRequired, Effect: EffectRequiresSynchronization,
			Message:     fmt.Sprintf("this Final PR is ready while issue #%d is still %q", issue.Number, WorkflowInProgress),
			Remediation: fmt.Sprintf("Rerun `gh-workflow ready --pr N`, which sets the issue to %q.", WorkflowInReview),
		})
	}
}

// merge adds the admission predicates: the Blocked asymmetry, R4 execution assurance,
// and the live enforcement evidence. Every unknown is a finding, never a pass — ERR-013
// requires Merge to fail closed rather than infer that no protection exists.
func (e *evaluation) merge() {
	pr := e.topology.PullRequest
	if pr.Draft && pr.State == "open" {
		e.add(Finding{
			Code: "GHW-PR-MERGE-DRAFT", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     "the pull request is still a draft",
			Remediation: "Cross Ready with `gh-workflow ready --pr N` first.",
		})
	}
	e.mergeLifecycle()
	e.mergeRisk()
	e.mergeEvidence()
}

// mergeLifecycle applies the FR-029 Blocked asymmetry: a Blocked Issue stops its Final
// outright, while a Supporting PR may still be admitted when its acceptance coverage
// explains why admission neither resolves nor conceals the blocker.
func (e *evaluation) mergeLifecycle() {
	issue := e.issue()
	if issue == nil || issue.Workflow != WorkflowBlocked {
		return
	}
	switch e.decl.Relationship {
	case RelationshipFinal:
		e.add(Finding{
			Code: "GHW-PR-MERGE-FINAL-BLOCKED", Phase: PhaseMerge,
			Category: CategoryBlocked, Effect: EffectBlocksMerge,
			Message:     fmt.Sprintf("issue #%d is Blocked, and a Final claims every remaining acceptance criterion", issue.Number),
			Remediation: "Resolve the blocker and move the issue to In review, or convert this PR to Supporting.",
		})
	case RelationshipSupporting:
		if !e.decl.BlockedRationale {
			e.add(Finding{
				Code: "GHW-PR-MERGE-SUPPORTING-BLOCKED-RATIONALE", Phase: PhaseMerge,
				Category: CategoryBlocked, Effect: EffectBlocksMerge,
				Message:     fmt.Sprintf("issue #%d is Blocked and this Supporting PR records no rationale for admitting it anyway", issue.Number),
				Remediation: fmt.Sprintf("State in %q why admission neither resolves nor conceals the blocker.", HeadingAcceptanceCoverage),
			})
		}
	case RelationshipNone, RelationshipStandalone:
	}
}

// mergeRisk applies FR-028's R4 Critical controls, which bind at admission rather than
// at Ready. D16 is explicit that they add execution assurance, not permission ceremony:
// no second approval is required and none is checked for here.
func (e *evaluation) mergeRisk() {
	if e.decl.Risk != RiskR4 || e.decl.R4Evidence.Complete() {
		return
	}
	e.add(Finding{
		Code: "GHW-PR-MERGE-R4-EVIDENCE", Phase: PhaseMerge,
		Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
		Message: fmt.Sprintf("this R4 Critical Standalone PR records no %s", strings.Join(e.decl.R4Evidence.Missing(), ", no ")),
		Remediation: fmt.Sprintf("Record the missing evidence in %q or %q before admission.",
			HeadingSummary, HeadingAcceptanceCoverage),
	})
}

// mergeEvidence checks the live enforcement and mergeability evidence.
func (e *evaluation) mergeEvidence() {
	pr := e.topology.PullRequest
	if !e.topology.Enforcement.Known {
		e.add(Finding{
			Code: "GHW-PR-MERGE-ENFORCEMENT-UNKNOWN", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     "required-check and protection evidence could not be established" + sourceSuffix(e.topology.Enforcement.Source),
			Remediation: "Restore authoritative visibility of branch protection and rerun the gate.",
		})
	} else {
		e.requiredChecks()
		if e.topology.Enforcement.RequiresReview && pr.ReviewDecision != "APPROVED" {
			e.add(Finding{
				Code: "GHW-PR-MERGE-REVIEW-REQUIRED", Phase: PhaseMerge,
				Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
				Message:     fmt.Sprintf("the branch requires review and the current decision is %s", quotedOrUnset(pr.ReviewDecision)),
				Remediation: "Obtain the required approval, then rerun the gate.",
			})
		}
	}
	if !e.topology.MergeSettings.Known {
		e.add(Finding{
			Code: "GHW-PR-MERGE-SETTINGS-UNKNOWN", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     "the repository's allowed merge methods could not be read",
			Remediation: "Restore visibility of the repository settings and rerun the gate.",
		})
	} else if !e.topology.MergeSettings.AllowSquash && !e.topology.MergeSettings.AllowRebase && !e.topology.MergeSettings.AllowMerge {
		e.add(Finding{
			Code: "GHW-PR-MERGE-NO-METHOD", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     "the repository permits no merge method",
			Remediation: "Enable a merge method in the repository settings, or admit the change through the repository's authorized manual path.",
		})
	}
	switch {
	case pr.Mergeable == nil:
		e.add(Finding{
			Code: "GHW-PR-MERGE-MERGEABILITY-UNKNOWN", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     "GitHub has not finished computing mergeability",
			Remediation: "Rerun the gate once GitHub reports mergeability.",
		})
	case !*pr.Mergeable:
		e.add(Finding{
			Code: "GHW-PR-MERGE-CONFLICT", Phase: PhaseMerge,
			Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
			Message:     fmt.Sprintf("the pull request does not merge cleanly into %s", quotedOrUnset(pr.BaseRef)),
			Remediation: "Update the branch and rerun the gate.",
		})
	}
}

// requiredChecks compares the live required-check names against the observed runs. A
// required check with no observed run is reported as missing rather than as passing:
// the absent run is exactly what NFR-007's truncated pagination looks like from here.
func (e *evaluation) requiredChecks() {
	observed := map[string]CheckState{}
	for _, check := range e.topology.PullRequest.RequiredChecks {
		observed[check.Name] = check
	}
	for _, name := range e.topology.Enforcement.RequiredStatusChecks {
		check, ok := observed[name]
		switch {
		case !ok:
			e.add(Finding{
				Code: "GHW-PR-MERGE-CHECK-MISSING", Phase: PhaseMerge,
				Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
				Message:     fmt.Sprintf("required check %q has no observed run on this head", name),
				Remediation: "Rerun the gate once the check reports, or investigate why it never ran.",
			})
		case check.Status != "completed":
			e.add(Finding{
				Code: "GHW-PR-MERGE-CHECK-PENDING", Phase: PhaseMerge,
				Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
				Message:     fmt.Sprintf("required check %q is %s", name, quotedOrUnset(check.Status)),
				Remediation: "Wait for the check to complete, then rerun the gate.",
			})
		case !passingConclusion(check.Conclusion):
			e.add(Finding{
				Code: "GHW-PR-MERGE-CHECK-FAILING", Phase: PhaseMerge,
				Category: CategoryAdmissionBlocked, Effect: EffectBlocksMerge,
				Message:     fmt.Sprintf("required check %q concluded %s", name, quotedOrUnset(check.Conclusion)),
				Remediation: "Fix the failing check and rerun the gate.",
			})
		}
	}
}

// passingConclusion reports whether a completed check run permits admission. GitHub
// treats neutral and skipped as satisfying a required check, so treating them as
// failures here would block admissions GitHub itself allows.
func passingConclusion(conclusion string) bool {
	switch conclusion {
	case "success", "neutral", "skipped":
		return true
	default:
		return false
	}
}

// dispositionRecord matches the immutable comment FR-034 writes before closing an
// unmerged Final.
var dispositionRecord = regexp.MustCompile(`(?m)^Final-Disposition:[ \t]*(.*)$`)

// Disposition values accepted by `close --pr --as OUTCOME` (FR-034).
const (
	DispositionInProgress = "in-progress"
	DispositionInReview   = "in-review"
	DispositionBlocked    = "blocked"
	DispositionDropped    = "dropped"
)

// dispositionWorkflow maps each disposition to the Workflow value the governing Issue
// must hold once the disposition is honored.
var dispositionWorkflow = map[string]string{
	DispositionInProgress: WorkflowInProgress,
	DispositionInReview:   WorkflowInReview,
	DispositionBlocked:    WorkflowBlocked,
	DispositionDropped:    WorkflowDropped,
}

// postMerge evaluates the terminal predicates: deterministic convergence after a merged
// Final, and recorded disposition after an abandoned one. Nothing here infers a
// lifecycle outcome from closure (FR-029), and nothing rolls anything back — EC-012 is
// explicit that admitted repository state stays admitted even when synchronization
// fails.
func (e *evaluation) postMerge() {
	pr := e.topology.PullRequest
	if !pr.Terminal() {
		e.add(Finding{
			Code: "GHW-PR-POSTMERGE-OPEN", Phase: PhasePostMerge,
			Category: CategoryNeedsDefinition, Effect: EffectAdvisory,
			Message:     "the post-merge gate was requested for a pull request that has not reached a terminal state",
			Remediation: fmt.Sprintf("Rerun without `--through`, which evaluates the %s gate for this PR.", InferGate(pr)),
		})
		return
	}
	if e.decl.Relationship != RelationshipFinal {
		// Supporting merge or closure is lifecycle-neutral and Standalone owns its own
		// record, so neither has a terminal obligation against an Issue.
		return
	}
	if pr.Merged {
		e.mergedFinalSync()
		return
	}
	e.finalDisposition()
}

// mergedFinalSync reports the convergence a merged Final authorizes but does not itself
// perform.
func (e *evaluation) mergedFinalSync() {
	issue := e.issue()
	if issue == nil {
		return
	}
	if issue.Workflow == WorkflowDone && issue.State == "closed" {
		return
	}
	e.add(Finding{
		Code: "GHW-PR-POSTMERGE-FINAL-SYNC", Phase: PhasePostMerge,
		Category: CategorySynchronizationRequired, Effect: EffectRequiresSynchronization,
		Kind: KindIssue, Number: issue.Number,
		Message: fmt.Sprintf("the Final PR merged while the issue is %s and %s",
			quotedOrUnset(issue.Workflow), quotedOrUnset(issue.State)),
		Remediation: "Run `gh-workflow close --issue N --as done`; the merge stands regardless of the outcome.",
	})
}

// trustedAuthor reports whether login may author disposition evidence.
//
// Case-insensitive because GitHub preserves the case of a login but resolves it
// case-insensitively, so "OctoCat" and "octocat" are one account and a case-sensitive
// comparison would discard the tool's own record. An empty author is never trusted: it is
// what an unattributed read produces, and unattributed evidence is exactly what this guard
// exists to reject.
func (e *evaluation) trustedAuthor(login string) bool {
	if login == "" {
		return false
	}
	for _, trusted := range e.topology.TrustedAuthors {
		if strings.EqualFold(strings.TrimSpace(trusted), login) {
			return true
		}
	}
	return false
}

// finalDisposition applies FR-034 and ERR-015 to a closed, unmerged Final: exactly one
// well-formed disposition record is required, and its value must agree with the Issue.
func (e *evaluation) finalDisposition() {
	var values []string
	for _, comment := range e.topology.PullRequest.Comments {
		// Evidence is attributed, not merely present. A comment from anyone else is
		// ordinary discussion however exactly it imitates the record's shape: honoring it
		// would let a third party either pin a permanent CONFLICT on the PR or supply a
		// terminal outcome the operator never chose.
		if !e.trustedAuthor(comment.Author) {
			continue
		}
		for _, match := range dispositionRecord.FindAllStringSubmatch(comment.Body, -1) {
			values = append(values, strings.TrimSpace(match[1]))
		}
	}
	switch {
	case len(values) == 0:
		e.add(Finding{
			Code: "GHW-PR-POSTMERGE-DISPOSITION-MISSING", Phase: PhasePostMerge,
			Category: CategoryDispositionRequired, Effect: EffectRequiresDisposition,
			Message:     "this Final PR was closed unmerged with no recorded disposition, and no lifecycle outcome may be inferred from closure",
			Remediation: "Record the decision with `gh-workflow close --pr N --as OUTCOME --reason S`.",
		})
		return
	case len(values) > 1 && !allEqual(values):
		e.add(Finding{
			Code: "GHW-PR-POSTMERGE-DISPOSITION-CONFLICT", Phase: PhasePostMerge,
			Category: CategoryDispositionRequired, Effect: EffectRequiresDisposition,
			Message:     fmt.Sprintf("this Final PR carries conflicting disposition records (%s)", strings.Join(values, ", ")),
			Remediation: "Resolve the contradiction explicitly; the package never reinterprets conflicting terminal evidence.",
		})
		return
	}
	workflow, ok := dispositionWorkflow[values[0]]
	if !ok {
		e.add(Finding{
			Code: "GHW-PR-POSTMERGE-DISPOSITION-CONFLICT", Phase: PhasePostMerge,
			Category: CategoryDispositionRequired, Effect: EffectRequiresDisposition,
			Message: fmt.Sprintf("the recorded disposition %s is not one of the accepted outcomes", quotedOrUnset(values[0])),
			Remediation: fmt.Sprintf("Record one of %s, %s, %s, or %s.",
				DispositionInProgress, DispositionInReview, DispositionBlocked, DispositionDropped),
		})
		return
	}
	issue := e.issue()
	if issue == nil || issue.Workflow == workflow {
		return
	}
	e.add(Finding{
		Code: "GHW-PR-POSTMERGE-DISPOSITION-SYNC", Phase: PhasePostMerge,
		Category: CategorySynchronizationRequired, Effect: EffectRequiresSynchronization,
		Kind: KindIssue, Number: issue.Number,
		Message: fmt.Sprintf("the recorded disposition %q wants issue Workflow %q, but the issue is %s",
			values[0], workflow, quotedOrUnset(issue.Workflow)),
		Remediation: "Apply the recorded disposition to the issue; the disposition record itself is immutable evidence.",
	})
}

// allEqual reports whether every value matches the first. Repeating the same record is
// not a contradiction — ERR-015 distinguishes conflicting evidence from duplicated
// evidence, and re-running an idempotent `close --pr` may legitimately write twice.
func allEqual(values []string) bool {
	for _, value := range values[1:] {
		if value != values[0] {
			return false
		}
	}
	return true
}

// quotedOrUnset renders a possibly empty observed value without inventing one.
func quotedOrUnset(value string) string {
	if value == "" {
		return "unset"
	}
	return fmt.Sprintf("%q", value)
}

// sourceSuffix names the consulted evidence source when the read reported one.
func sourceSuffix(source string) string {
	if source == "" {
		return ""
	}
	return " from " + source
}

// formatNumbers renders work-item numbers for a message.
func formatNumbers(numbers []int) string {
	parts := make([]string, 0, len(numbers))
	for _, number := range numbers {
		parts = append(parts, fmt.Sprintf("#%d", number))
	}
	return strings.Join(parts, ", ")
}
