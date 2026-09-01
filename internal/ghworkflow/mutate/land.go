package mutate

// `gh-workflow land --pr N` (#236 C13): the whole admission of one pull request as a
// single transaction — advance the governing issue out of `Ready`, carry the pull request
// across Ready, admit it, and prove what landed.
//
// It exists because the four-call sequence was being driven by hand once per pull request,
// and the ordering is where that went wrong: a leg whose PR was still blocked was reaped
// as though it had merged, because the operator sequencing the steps had no single receipt
// saying which of them completed. One command with one ordered step record removes the
// class, not just the keystrokes.
//
// Fail-closed is the whole contract. Every step's refusal — a domain finding from either
// gate, a merge method the repository forbids, a failed write — stops the sequence where
// it stands and emits the receipt of what provably completed; nothing after a refusal is
// attempted and nothing before it is rolled back (EC-012). The gates are not merely
// re-run from `ready`'s and `merge`'s implementations, they ARE those implementations:
// readySteps and mergeSteps are called here, so `land` cannot drift into admitting
// something `ready --pr N` followed by `merge --pr N` would have refused.

import (
	"context"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The two boundaries `land` adds to the ready and merge step plans it composes.
const (
	stepAdvanceIssue = "advance-governing-issue"
	stepLandingProof = "landing-proof"
)

// workflowReady is the organization vocabulary's dispatchable-but-not-started value.
//
// It is spelled here rather than taken from relation's constants deliberately: the engine
// declares only the values its predicates reason about, and `Ready` is not one of them —
// it is the value this transaction consumes on the way in. org-schema.yaml is the
// authority for the vocabulary, and the write below is validated against it like every
// other field write, so a schema that renamed the value fails the write rather than
// silently skipping the step.
const workflowReady = "Ready"

func runLand(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("land", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	number := fs.Int("pr", 0, "pull request number to land")
	method := fs.String("method", "", "merge method: merge, squash, or rebase "+
		"(default: the first of squash, rebase, merge the repository permits)")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow land --pr N [--method METHOD] [flags]\n\n"+
		"Runs the whole admission as one transaction: advances a governing issue that is\n"+
		"still Ready to In progress, carries the pull request across Ready, admits it, and\n"+
		"reports the merged commit with the command that proves the head landed. Any\n"+
		"refusal stops the sequence and emits the receipt of what completed.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if *number <= 0 {
		return cli.Usagef("pass --pr with a positive pull request number")
	}
	if *method != "" {
		switch *method {
		case ghapi.MergeMethodMerge, ghapi.MergeMethodSquash, ghapi.MergeMethodRebase:
		default:
			return cli.Usagef("merge method %q is not one of %s, %s, %s",
				*method, ghapi.MergeMethodMerge, ghapi.MergeMethodSquash, ghapi.MergeMethodRebase)
		}
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
	rec := newSteps(stepAdvanceIssue, stepSyncIssue, stepMarkReady, stepVerifyReady,
		stepMerge, stepEnableAutoMerge, stepObserveTerminal, stepConvergeIssue, stepLandingProof)
	envelope := cli.NewEnvelope("land", cli.ResultClear, prTarget(repo, *number, gate.PR.HTMLURL))
	// The reported gate is Merge: it is the last gate this transaction evaluates and the
	// one whose verdict admitted the change. A caller reading `gate` needs to know what
	// the findings beside it were produced by, and a partial run's findings always come
	// from the phase it stopped at, which the steps then name exactly.
	envelope.Gate = cli.Gate(relation.PhaseMerge)

	stepErr := landSteps(ctx, client, repo, schema, gate, *method, rec, &envelope)
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
	switch {
	case stepErr != nil:
		return stepErr
	case envelope.Result == cli.ResultDomainFinding:
		return domainf("%s#%d did not land: %d finding(s); the steps record what completed",
			repo, *number, len(envelope.Findings))
	}
	return nil
}

// landSteps runs the transaction in order, recording every boundary in rec.
//
// The gate is re-loaded twice on purpose. After the issue advance, because the Ready gate
// reads the governing issue's Workflow and would otherwise evaluate the value this
// command just replaced; and after the Ready transition, because the Merge gate must be
// evaluated against the pull request that is now ready for review rather than against the
// draft it was. Composing `ready` and `merge` without those reloads would admit a change
// on evidence that predates the writes this same command performed.
func landSteps(ctx context.Context, client *ghapi.Client, repo render.Repository,
	schema *orgschema.Schema, gate *prGate, method string, rec *steps, envelope *cli.Envelope,
) error {
	number := gate.PR.Number

	advanced, err := advanceGoverningIssue(ctx, client, repo, gate, rec, envelope)
	if err != nil {
		return err
	}
	if advanced {
		// Re-read rather than patch the in-memory topology: the reload is the same
		// phase-bounded read `ready --pr N` performs, so what the Ready gate sees here is
		// what it would have seen had the operator run the two commands by hand.
		reloaded, err := loadPRGate(ctx, client, repo, schema, number, relation.PhaseReady)
		if err != nil {
			return err
		}
		gate = reloaded
	}

	envelope.Findings = append(envelope.Findings, gate.Result.Findings...)
	if !gate.Result.Clear() {
		return domainf("%s#%d does not pass the Ready gate: %d finding(s), and nothing further was written",
			repo, number, len(gate.Result.Findings))
	}
	if err := readySteps(ctx, client, gate, rec, envelope); err != nil {
		return err
	}
	// A Ready step that produced a finding rather than an error — a moved head, an
	// unverified transition — is a refusal too: the pull request is not in the state the
	// Merge gate would be evaluating, so the transaction stops with the writes it made
	// recorded.
	if len(envelope.Findings) > 0 {
		return domainf("%s#%d did not complete the Ready transition; nothing was merged", repo, number)
	}

	merged, err := loadPRGate(ctx, client, repo, schema, number, relation.PhaseMerge)
	if err != nil {
		return err
	}
	envelope.Findings = append(envelope.Findings, merged.Result.Findings...)
	if !merged.Result.Clear() {
		return domainf("%s#%d does not pass the Merge gate: %d finding(s), and nothing was merged",
			repo, number, len(merged.Result.Findings))
	}
	selected, findings := selectMergeMethod(method, merged.Topology.MergeSettings, number)
	if len(findings) > 0 {
		envelope.Findings = append(envelope.Findings, findings...)
		return domainf("%s#%d: no usable merge method, and nothing was merged", repo, number)
	}

	// `--auto` is not offered here. Auto-merge delegates the outcome to GitHub, and a
	// transaction that ends by proving what landed cannot prove anything about a merge
	// that has not happened yet; `merge --pr N --auto` remains the surface for that.
	after, err := mergeSteps(ctx, client, merged, selected, false, rec, envelope)
	if err != nil {
		return err
	}
	if after == nil {
		rec.skip(stepLandingProof, "the pull request did not reach a merged outcome")
		return nil
	}
	return recordLandingProof(ctx, client, repo, merged, after, rec)
}

// advanceGoverningIssue moves a governing issue that is still `Ready` to `In progress`,
// reporting whether it wrote.
//
// This is step one of C13 because it is the step the Ready gate depends on: a Final whose
// issue is still `Ready` fails EC-011, so without it `land` would refuse every pull
// request whose work was dispatched but never marked started. It writes only for that one
// value — an issue already `In progress`, `In review`, or anything else is left alone,
// which is what makes rerunning the command after a partial failure safe.
func advanceGoverningIssue(ctx context.Context, client *ghapi.Client, repo render.Repository,
	gate *prGate, rec *steps, envelope *cli.Envelope,
) (bool, error) {
	switch {
	case !gate.Decl.Relationship.Governed():
		rec.skip(stepAdvanceIssue, "a Standalone pull request governs no issue")
		return false, nil
	case gate.GoverningIssue() == 0:
		rec.skip(stepAdvanceIssue, "no governing issue resolved")
		return false, nil
	case gate.Workflow() != workflowReady:
		rec.skip(stepAdvanceIssue, fmt.Sprintf("issue #%d is already %s",
			gate.GoverningIssue(), quotedOrUnset(gate.Workflow())))
		return false, nil
	}

	values, err := resolveFieldIDs(ctx, client, repo.Owner,
		[]assignment{{Name: render.FieldWorkflow, Value: relation.WorkflowInProgress}})
	if err != nil {
		if finding, drift := driftFinding(err, relation.KindIssue, gate.GoverningIssue()); drift {
			envelope.Findings = append(envelope.Findings, finding)
			rec.fail(stepAdvanceIssue, "the live organization schema has drifted from the baseline")
			return false, domainf("%s: %v", repo, err)
		}
		rec.fail(stepAdvanceIssue, err.Error())
		return false, err
	}
	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, gate.GoverningIssue(), values); err != nil {
		rec.fail(stepAdvanceIssue, fmt.Sprintf(
			"issue #%d is still %s and the pull request is untouched",
			gate.GoverningIssue(), quotedOrUnset(gate.Workflow())))
		return false, err
	}
	rec.complete(stepAdvanceIssue, fmt.Sprintf("issue #%d Workflow = %s",
		gate.GoverningIssue(), relation.WorkflowInProgress))
	return true, nil
}

// recordLandingProof records the merged commit and the command that proves the head's
// content reached the integration branch.
//
// The proof is stated, not performed. This tool never shells out to `git` — it reads a
// checkout's configuration directly and does not require Git to be installed
// (render.OriginRepository says so at the other end of that decision), and running a
// subprocess over operator-controlled paths to answer a question the operator can answer
// in one command would be a new execution surface for no new evidence. So the command is
// emitted with the paths already resolved, and it is the exact diff the manual proof used:
// empty output means every path the pull request changed now reads the same on the
// integration branch as on the head that was admitted.
//
// A failure to read the changed paths degrades to the OID alone rather than failing the
// command: the merge has landed, and reporting the transaction as failed over an
// unavailable proof would send an operator to re-run an admission that already happened.
func recordLandingProof(ctx context.Context, client *ghapi.Client, repo render.Repository,
	gate *prGate, after *ghapi.PullRequest, rec *steps,
) error {
	commit := after.MergeCommitSHA
	if commit == "" {
		commit = "(GitHub reported no merge commit)"
	}
	files, err := client.ListPullRequestFiles(ctx, repo.Owner, repo.Name, after.Number)
	if err != nil {
		rec.complete(stepLandingProof, fmt.Sprintf(
			"merged as %s; the changed paths could not be read (%v), so verify with "+
				"`git diff origin/%s %s`", commit, err, gate.PR.Base.Ref, gate.PR.Head.SHA))
		return nil
	}
	rec.complete(stepLandingProof, fmt.Sprintf("merged as %s; verify with `%s` (empty output is the proof)",
		commit, landingProofCommand(gate.PR.Base.Ref, gate.PR.Head.SHA, files)))
	return nil
}

// landingProofCommand renders the diff that proves the head landed.
//
// Paths are the pull request's own changed files, both names of a rename, deduplicated and
// left in GitHub's order; the head SHA is the commit that was admitted, which survives the
// merge even under a squash, where the merge commit is a different object with the same
// content. `--` separates paths from revisions so a branch and a file sharing a name
// cannot make Git read the argument as the wrong one.
func landingProofCommand(baseRef, headSHA string, files []ghapi.PullRequestFile) string {
	seen := map[string]bool{}
	paths := make([]string, 0, len(files))
	for _, file := range files {
		for _, name := range []string{file.Filename, file.PreviousFilename} {
			if name == "" || seen[name] {
				continue
			}
			seen[name] = true
			paths = append(paths, name)
		}
	}
	command := fmt.Sprintf("git fetch origin %s && git diff origin/%s %s", baseRef, baseRef, headSHA)
	if len(paths) > 0 {
		command += " -- " + strings.Join(paths, " ")
	}
	return command
}
