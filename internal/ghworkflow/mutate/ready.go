package mutate

// `gh-workflow ready --pr N` (spec FR-032): the paired operation that carries an agent's
// draft pull request across the Ready boundary.
//
// The command exists because the check and the mutation must be adjacent. Ready is a real
// boundary only if the state it was granted on is the state that still holds when the
// draft flag clears, and any gap between a separate `check` and a separate mark-ready is a
// window in which the governing Issue, the body, or a sibling Final can change. One
// command closes that window; it does not merely bundle two calls for convenience.

import (
	"context"
	"flag"
	"fmt"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The ordered boundaries of the Ready operation.
//
// The Issue write comes first, and the order is the failure design rather than a
// preference: if the lifecycle write lands and the draft never clears, the result is a
// draft PR against an `In review` Issue, which the next run converges silently. The
// reverse order leaves a ready Final against an `In progress` Issue — the EC-011 state the
// engine reports as GHW-PR-READY-FINAL-WORKFLOW, visible but requiring a second command.
const (
	stepSyncIssue   = "synchronize-issue-workflow"
	stepMarkReady   = "mark-ready"
	stepVerifyReady = "verify-ready"
)

func runReady(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("ready", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	number := fs.Int("pr", 0, "pull request number to carry across Ready")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow ready --pr N [flags]\n\n"+
		"Freshly evaluates the Structural and Ready gates, synchronizes a Final PR's\n"+
		"governing issue from In progress to In review, marks the pull request ready, and\n"+
		"emits one receipt. Domain findings write nothing; a partial failure records which\n"+
		"steps completed and rerunning the same invocation resumes.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if *number <= 0 {
		return cli.Usagef("pass --pr with a positive pull request number")
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

	gate, err := loadPRGate(ctx, client, repo, schema, *number, relation.PhaseReady)
	if err != nil {
		return err
	}
	rec := newSteps(stepSyncIssue, stepMarkReady, stepVerifyReady)
	envelope := cli.NewEnvelope("ready", cli.ResultClear, prTarget(repo, *number, gate.PR.HTMLURL))
	envelope.Gate = cli.Gate(relation.PhaseReady)
	envelope.Findings = gate.Result.Findings

	// Findings stop the operation before its first write, with every step recorded pending:
	// the envelope must show that the gate refused rather than that the writes were skipped.
	if !gate.Result.Clear() {
		envelope.Result = cli.ResultDomainFinding
		envelope.Steps = rec.list()
		if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
			return writeErr
		}
		return domainf("%s#%d does not pass the Ready gate: %d finding(s), and nothing was written",
			repo, *number, len(gate.Result.Findings))
	}

	if stepErr := readySteps(ctx, client, gate, rec, &envelope); stepErr != nil {
		envelope.Steps = rec.list()
		envelope.Result = cli.Classify(stepErr)
		if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
			return writeErr
		}
		return stepErr
	}

	envelope.Steps = rec.list()
	if len(envelope.Findings) > 0 {
		envelope.Result = cli.ResultDomainFinding
	}
	if err := cli.WriteEnvelope(envelope, mode, env); err != nil {
		return err
	}
	if envelope.Result == cli.ResultDomainFinding {
		return domainf("%s#%d: the Ready transition did not verify", repo, *number)
	}
	return nil
}

// readySteps performs the ordered writes. It returns the failure that stopped the
// sequence, having already recorded every step's outcome in rec, so the caller can emit a
// truthful account of a partially applied operation before propagating the error (ERR-014).
func readySteps(ctx context.Context, client *ghapi.Client, gate *prGate, rec *steps,
	envelope *cli.Envelope,
) error {
	repo := render.Repository{Owner: gate.Owner, Name: gate.Name}
	number := gate.PR.Number

	// The conditional guard on the gate-read/mutation window (#234 item 4), and it runs
	// BEFORE the first write on purpose. The gate was evaluated against a specific head;
	// marking the PR ready admits it for review, and GraphQL's
	// markPullRequestReadyForReview takes no expectedHeadOid, so the head is re-observed
	// here and the whole operation refused if it moved. Placed after the issue
	// synchronization — where it lived through 1.10 — a moved head left the governing
	// issue advanced to `In review` for a pull request that was never marked ready, which
	// is the EC-011 divergence this command exists to avoid creating.
	//
	// Residual race, accepted deliberately: this is a compare-then-act, not an atomic
	// conditional write, so a push landing between this read and the mutation below is
	// still admitted. GitHub offers no conditional form of that mutation, so the window
	// cannot be closed here — it is narrowed from "the whole gate evaluation" to the
	// remaining round trips, and `merge` (which does take a head SHA) is the gate that
	// admits content.
	//
	// A pull request that is already ready has no transition to guard: no mutation follows,
	// so re-observing the head would spend a round trip to protect nothing (NFR-008).
	if gate.PR.Draft {
		current, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
		if err != nil {
			rec.fail(stepMarkReady, "the head could not be re-observed; nothing was written")
			return err
		}
		if current.Head.SHA != gate.PR.Head.SHA {
			rec.fail(stepMarkReady, "the head moved after the gate was evaluated; nothing was written")
			envelope.Findings = append(envelope.Findings, relation.Finding{
				Code: "GHW-PR-READY-HEAD-MOVED", Phase: relation.PhaseReady,
				Category: relation.CategoryAdmissionBlocked, Effect: relation.EffectBlocksReady,
				Kind: relation.KindPullRequest, Number: number,
				Message:     "the branch head changed between the Ready gate and the transition, so the gate no longer describes this pull request",
				Remediation: "Rerun `gh-workflow ready --pr N`; the gate is re-evaluated against the new head.",
			})
			rec.skip(stepSyncIssue, "the head moved, so no lifecycle write was made")
			rec.skip(stepVerifyReady, "no transition was attempted")
			return nil
		}
	}

	switch {
	case gate.Decl.Relationship != relation.RelationshipFinal:
		rec.skip(stepSyncIssue, "only a Final PR synchronizes issue lifecycle")
	case gate.Topology.GoverningIssue == nil:
		rec.skip(stepSyncIssue, "no governing issue resolved")
	case gate.Workflow() != relation.WorkflowInProgress:
		rec.skip(stepSyncIssue, fmt.Sprintf("issue #%d is already %s",
			gate.GoverningIssue(), quotedOrUnset(gate.Workflow())))
	default:
		values, err := resolveFieldIDs(ctx, client, repo.Owner,
			[]assignment{{Name: render.FieldWorkflow, Value: relation.WorkflowInReview}})
		if err != nil {
			if finding, drift := driftFinding(err, relation.KindIssue, gate.GoverningIssue()); drift {
				envelope.Findings = append(envelope.Findings, finding)
				rec.fail(stepSyncIssue, "the live organization schema has drifted from the baseline")
				return domainf("%s: %v", repo, err)
			}
			rec.fail(stepSyncIssue, err.Error())
			return err
		}
		if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, gate.GoverningIssue(), values); err != nil {
			rec.fail(stepSyncIssue, fmt.Sprintf("issue #%d is still %s and the pull request is untouched",
				gate.GoverningIssue(), quotedOrUnset(gate.Workflow())))
			return err
		}
		rec.complete(stepSyncIssue, fmt.Sprintf("issue #%d Workflow = %s",
			gate.GoverningIssue(), relation.WorkflowInReview))
	}

	if !gate.PR.Draft {
		// An externally created or already-ready PR is the idempotent case FR-032 requires
		// to converge rather than refuse. The verification read is skipped with it: there
		// is no transition to verify, and spending a round trip to re-observe a fact this
		// run did not change is exactly the repeated read NFR-008 bounds.
		rec.skip(stepMarkReady, "the pull request is already ready for review")
		rec.skip(stepVerifyReady, "no transition to verify")
		return nil
	}
	if err := client.MarkPullRequestReady(ctx, gate.NodeID); err != nil {
		rec.fail(stepMarkReady, "the pull request is still a draft")
		return err
	}
	rec.complete(stepMarkReady, "the pull request is no longer a draft")

	// FR-032 requires the result to be verified rather than inferred from the mutation's
	// acceptance: the GraphQL mutation answering without errors is evidence the request was
	// accepted, and the observed draft flag is evidence the transition happened.
	after, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		rec.fail(stepVerifyReady, "the read-back failed; the transition may still have landed")
		return err
	}
	if after.Draft {
		rec.fail(stepVerifyReady, "GitHub still reports the pull request as a draft")
		envelope.Findings = append(envelope.Findings, relation.Finding{
			Code: "GHW-PR-READY-TRANSITION-UNVERIFIED", Phase: relation.PhaseReady,
			Category: relation.CategoryAdmissionBlocked, Effect: relation.EffectBlocksReady,
			Kind: relation.KindPullRequest, Number: number,
			Message:     "the mark-ready mutation was accepted but GitHub still reports the pull request as a draft",
			Remediation: "Rerun `gh-workflow ready --pr N`; every step is idempotent.",
		})
		return nil
	}
	rec.complete(stepVerifyReady, "GitHub reports the pull request ready for review")
	return nil
}
