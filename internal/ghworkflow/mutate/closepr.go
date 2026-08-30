package mutate

// `gh-workflow close --pr P --as OUTCOME --reason S` (spec FR-034): the sole paired route
// for intentionally closing an open Final pull request unmerged.
//
// The ordering is the whole point of the command. The disposition record is written
// *before* the PR closes, because a comment written after a failed close is recoverable
// evidence while a close without a record leaves a terminal PR whose intent no later read
// can reconstruct — and FR-029 forbids inferring any lifecycle outcome from closure. The
// record is immutable: the first canonical outcome and reason stand, and a same-outcome
// rerun reuses them even when the operator passes a different `--reason`, because the
// evidence describes the decision that was made, not the last sentence typed about it.
//
// The recorded VALUE is the lowercase disposition token (`in-progress`, `in-review`,
// `blocked`, `dropped`), which is the vocabulary internal/ghworkflow/relation's Post-merge
// predicate reads back out of the comment. FR-034's prose spells the value as the Workflow
// name (`In progress`); writing that spelling would make every record this command writes
// unreadable to the engine that validates it, so the two ends are kept in agreement here
// and the spelling difference is a spec question, not a licence to write evidence the
// package cannot parse. Cross-file contract: relation's `dispositionRecord` regexp and
// `dispositionWorkflow` map are the counterpart — change either end and update both.

import (
	"context"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The ordered boundaries of the Final-disposition operation.
const (
	stepRecordDisposition = "record-disposition"
	stepClosePR           = "close-pull-request"
	stepConvergeWorkflow  = "converge-issue-workflow"
)

// dispositionOutcomes maps each accepted `--as` value to the Workflow value the governing
// Issue converges to. It is derived from the engine's own disposition vocabulary so the
// writer and the Post-merge validator cannot drift apart.
var dispositionOutcomes = map[string]string{
	relation.DispositionInProgress: relation.WorkflowInProgress,
	relation.DispositionInReview:   relation.WorkflowInReview,
	relation.DispositionBlocked:    relation.WorkflowBlocked,
	relation.DispositionDropped:    relation.WorkflowDropped,
}

// dispositionOrder fixes the order refusals list the vocabulary in, because a map's
// iteration order would make the same refusal read differently on every run.
var dispositionOrder = []string{
	relation.DispositionInProgress, relation.DispositionInReview,
	relation.DispositionBlocked, relation.DispositionDropped,
}

func closePullRequest(ctx context.Context, env *cli.Env, tgt *target, mode cli.OutputMode,
	number int, as, reason string,
) error {
	outcome := strings.ToLower(strings.TrimSpace(as))
	workflow, ok := dispositionOutcomes[outcome]
	if !ok {
		// `done` is refused by name because it is the plausible mistake: a Final that
		// earned Done is merged, not closed, and accepting it here would let the command
		// record completion for work that was never admitted.
		return cli.Usagef("pass --as with one of %s; a Final PR that earned %q is merged, not closed",
			strings.Join(dispositionOrder, ", "), relation.WorkflowDone)
	}
	trimmed := strings.TrimSpace(reason)
	if trimmed == "" {
		return cli.Usagef("pass --reason with the one-line reason to record before closing the pull request")
	}
	if strings.ContainsAny(trimmed, "\r\n") {
		// The record's shape is fixed at exactly two lines, and the engine reads the
		// disposition from the first: a multi-line reason would push text into a position
		// where a later read cannot tell reason from record.
		return cli.Usagef("--reason must be a single line; the disposition record's shape is fixed")
	}

	schema, err := tgt.loadSchema(env)
	if err != nil {
		return err
	}
	repo, err := tgt.resolve(env)
	if err != nil {
		return err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return err
	}

	gate, err := loadPRGate(ctx, client, repo, schema, number, relation.PhaseStructural)
	if err != nil {
		return err
	}
	if gate.decl.Relationship != relation.RelationshipFinal {
		return cli.Usagef("%s#%d declares %s, and this route closes only a Final PR; "+
			"Supporting and Standalone closure is lifecycle-neutral and needs no disposition record",
			repo, number, relationshipLabel(gate.decl.Relationship))
	}
	if gate.pr.IsMerged() {
		return cli.Usagef("%s#%d is merged, so it has no unmerged disposition to record", repo, number)
	}
	if enabled, _ := gate.pr.AutoMergeEnabled(); enabled {
		return cli.Usagef("%s#%d has auto-merge armed; disable it before recording a disposition, "+
			"or the pull request may merge while the record says it was abandoned", repo, number)
	}

	rec := newSteps(stepRecordDisposition, stepClosePR, stepConvergeWorkflow)
	envelope := cli.NewEnvelope("close", cli.ResultClear, prTarget(repo, number, gate.pr.HTMLURL))
	envelope.Gate = cli.Gate(relation.PhaseStructural)

	// An open PR must be structurally resolvable before its closure is recorded (FR-034).
	// A closed one is not re-gated: its structural findings are immutable terminal evidence
	// (EC-014), and refusing to record the disposition of an already-closed Final would
	// leave exactly the unrecorded terminal state this command exists to prevent.
	if gate.pr.State == stateOpen && !gate.result.Clear() {
		envelope.Findings = gate.result.Findings
		envelope.Result = cli.ResultDomainFinding
		envelope.Steps = rec.list()
		if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
			return writeErr
		}
		return domainf("%s#%d is not a structurally resolvable Final: %d finding(s), and nothing was written",
			repo, number, len(gate.result.Findings))
	}

	stepErr := dispositionSteps(ctx, client, gate, outcome, workflow, trimmed, rec, &envelope)
	envelope.Steps = rec.list()
	switch {
	case stepErr != nil:
		envelope.Result = cli.Classify(stepErr)
	case len(envelope.Findings) > 0:
		envelope.Result = cli.ResultDomainFinding
	}
	if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
		return writeErr
	}
	if stepErr != nil {
		return stepErr
	}
	if envelope.Result == cli.ResultDomainFinding {
		return domainf("%s#%d: the recorded disposition conflicts with this invocation, and nothing was written",
			repo, number)
	}
	return nil
}

// dispositionSteps performs the ordered record, close, and convergence.
func dispositionSteps(ctx context.Context, client *ghapi.Client, gate *prGate,
	outcome, workflow, reason string, rec *steps, envelope *cli.Envelope,
) error {
	repo := gate.repo
	number := gate.pr.Number

	comments, err := client.ListIssueComments(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return err
	}
	recorded := recordedDispositions(comments)
	switch {
	case len(recorded) == 0:
		body := fmt.Sprintf("Final-Disposition: %s\nReason: %s\n", outcome, reason)
		if _, err := client.CreateComment(ctx, repo.Owner, repo.Name, number, body); err != nil {
			rec.fail(stepRecordDisposition, "no disposition was recorded; the pull request is untouched")
			return err
		}
		rec.complete(stepRecordDisposition, "recorded Final-Disposition: "+outcome)
	case len(recorded) == 1 && recorded[0] == outcome:
		// The record is immutable evidence, so a same-outcome rerun reuses it even when the
		// caller passed a different --reason. This is the resume path: the first attempt
		// wrote the record and failed later, and the rerun continues from here.
		rec.skip(stepRecordDisposition, "the pull request already records Final-Disposition: "+outcome)
	default:
		rec.fail(stepRecordDisposition, "the existing disposition record is not this outcome")
		envelope.Findings = append(envelope.Findings, relation.Finding{
			Code: "GHW-PR-POSTMERGE-DISPOSITION-CONFLICT", Phase: relation.PhasePostMerge,
			Category: relation.CategoryDispositionRequired, Effect: relation.EffectRequiresDisposition,
			Kind: relation.KindPullRequest, Number: number,
			Message: fmt.Sprintf("this pull request already records the disposition %s, and %q was requested",
				strings.Join(recorded, ", "), outcome),
			Remediation: "The first canonical record is immutable; resolve the contradiction explicitly rather than recording a second outcome.",
		})
		return nil
	}

	if gate.pr.State == stateClosed {
		rec.skip(stepClosePR, "the pull request is already closed")
	} else {
		// A pull request is closed through the issues endpoint, which is the same object:
		// GitHub serves every pull request as an issue for the shared members, and state is
		// one of them. No close reason is sent — `not_planned` is Issue vocabulary, and the
		// PR's own disposition is the record written above, not a native reason.
		updated, err := client.SetIssueState(ctx, repo.Owner, repo.Name, number, stateClosed, "")
		if err != nil {
			rec.fail(stepClosePR, "the pull request is still open; the disposition record stands and rerunning resumes")
			return err
		}
		if updated.State != stateClosed {
			rec.fail(stepClosePR, "GitHub still reports the pull request as "+quotedOrUnset(updated.State))
			return domainf("%s#%d: GitHub still reports the pull request as %s after the close",
				repo, number, quotedOrUnset(updated.State))
		}
		rec.complete(stepClosePR, "the pull request is closed unmerged")
	}

	if gate.governedIssue() == 0 {
		rec.skip(stepConvergeWorkflow, "no governing issue resolved")
		return nil
	}
	return convergeDisposition(ctx, client, gate, outcome, workflow, rec)
}

// convergeDisposition applies the recorded outcome to the governing Issue.
//
// `dropped` is the one terminal outcome, so it runs the existing paired terminal sequence
// rather than writing a Workflow value beside an open Issue — the divergence FR-021 exists
// to prevent. A nonterminal outcome against a closed Issue runs the same sequence in the
// reopen direction, for the same reason; against an open Issue it is a single field write,
// because the native state already agrees.
func convergeDisposition(ctx context.Context, client *ghapi.Client, gate *prGate,
	outcome, workflow string, rec *steps,
) error {
	repo := gate.repo
	issueNumber := gate.governedIssue()

	if outcome == relation.DispositionDropped {
		move := transition{
			state: stateClosed, reason: "not_planned", workflow: relation.WorkflowDropped,
			rerun: fmt.Sprintf("close --issue %d --as dropped", issueNumber),
		}
		result, err := converge(ctx, client, repo, issueNumber, move, nil)
		if err != nil {
			rec.fail(stepConvergeWorkflow, fmt.Sprintf(
				"the disposition stands; issue #%d did not converge to %s and rerunning retries it",
				issueNumber, relation.WorkflowDropped))
			return err
		}
		rec.complete(stepConvergeWorkflow, result.Message)
		return nil
	}

	if gate.issue != nil && gate.issue.State == stateClosed {
		move := transition{
			state: stateOpen, reason: reasonReopened, workflow: workflow,
			rerun: fmt.Sprintf("reopen --issue %d --workflow %q", issueNumber, workflow),
		}
		result, err := converge(ctx, client, repo, issueNumber, move, nil)
		if err != nil {
			rec.fail(stepConvergeWorkflow, fmt.Sprintf(
				"the disposition stands; issue #%d is still closed and rerunning retries it", issueNumber))
			return err
		}
		rec.complete(stepConvergeWorkflow, result.Message)
		return nil
	}

	if gate.workflow() == workflow {
		rec.skip(stepConvergeWorkflow, fmt.Sprintf("issue #%d is already %q", issueNumber, workflow))
		return nil
	}
	values, err := resolveFieldIDs(ctx, client, repo.Owner,
		[]assignment{{Name: render.FieldWorkflow, Value: workflow}})
	if err != nil {
		rec.fail(stepConvergeWorkflow, "the live organization schema has drifted from the baseline")
		return err
	}
	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, issueNumber, values); err != nil {
		rec.fail(stepConvergeWorkflow, fmt.Sprintf(
			"the disposition stands; issue #%d is still %s and rerunning retries it",
			issueNumber, quotedOrUnset(gate.workflow())))
		return err
	}
	rec.complete(stepConvergeWorkflow, fmt.Sprintf("issue #%d Workflow = %s", issueNumber, workflow))
	return nil
}

// recordedDispositions returns the distinct disposition values already recorded on the
// pull request, in first-seen order. Duplicates of one value are not a contradiction —
// ERR-015 distinguishes repeated evidence from conflicting evidence, and an interrupted
// rerun may legitimately have written the same record twice.
func recordedDispositions(comments []ghapi.Comment) []string {
	seen := map[string]bool{}
	var values []string
	for _, comment := range comments {
		for _, line := range strings.Split(comment.Body, "\n") {
			rest, ok := strings.CutPrefix(strings.TrimSpace(line), "Final-Disposition:")
			if !ok {
				continue
			}
			value := strings.TrimSpace(rest)
			if !seen[value] {
				seen[value] = true
				values = append(values, value)
			}
		}
	}
	return values
}

// relationshipLabel names a parsed relationship the way the PR body declares it.
func relationshipLabel(r relation.Relationship) string {
	switch r {
	case relation.RelationshipFinal:
		return "Final"
	case relation.RelationshipSupporting:
		return "Supporting"
	case relation.RelationshipStandalone:
		return "Standalone"
	case relation.RelationshipNone:
		return "no canonical governing-work relationship"
	default:
		return string(r)
	}
}
