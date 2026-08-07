package mutate

import (
	"context"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// Native state reasons. `reopened` is what GitHub records for a restored issue; the two
// closed reasons are the halves of the terminal pairing the vocabulary reference fixes.
const (
	stateOpen      = "open"
	stateClosed    = "closed"
	reasonReopened = "reopened"
)

// transition is one ordered terminal sequence: the native state and reason to apply
// first, the Workflow value to apply second, and the invocation that reruns it.
type transition struct {
	state    string
	reason   string
	workflow string
	rerun    string
}

func runClose(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("close", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	issue := fs.Int("issue", 0, "issue number to close")
	as := fs.String("as", "", "terminal disposition: done or dropped")
	if err := parse(fs, env, args, "Usage: gh-workflow close --issue N --as done|dropped [flags]\n\n"+
		"Applies the terminal transition as an ordered sequence: the native close with its\n"+
		"reason first, then the matching Workflow value. Both steps are idempotent; if the\n"+
		"second fails, the divergence is reported and rerunning this command converges.\n"); err != nil {
		return err
	}
	if err := requireIssue(*issue); err != nil {
		return err
	}

	var workflow string
	switch strings.ToLower(*as) {
	case "done":
		workflow = "Done"
	case "dropped":
		workflow = "Dropped"
	default:
		return cli.Usagef("pass --as done or --as dropped")
	}
	reason, _ := terminalReason(workflow)
	move := transition{
		state:    stateClosed,
		reason:   reason,
		workflow: workflow,
		rerun:    fmt.Sprintf("close --issue %d --as %s", *issue, strings.ToLower(*as)),
	}

	schema, err := tgt.loadSchema(env)
	if err != nil {
		return err
	}
	if err := requireWorkflowValue(schema, workflow); err != nil {
		return err
	}
	return apply(ctx, env, tgt, *issue, move)
}

func runReopen(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("reopen", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	issue := fs.Int("issue", 0, "issue number to reopen")
	workflow := fs.String("workflow", "", "nonterminal Workflow value to restore")
	if err := parse(fs, env, args, "Usage: gh-workflow reopen --issue N --workflow VALUE [flags]\n\n"+
		"Reopens the issue and restores a nonterminal Workflow value, in that order and\n"+
		"under the same protocol as close: idempotent steps, divergence reported, rerun to\n"+
		"converge. Which value the work returns to is your judgment, so it is required.\n"); err != nil {
		return err
	}
	if err := requireIssue(*issue); err != nil {
		return err
	}
	if *workflow == "" {
		return cli.Usagef("pass --workflow with the nonterminal value to restore")
	}

	schema, err := tgt.loadSchema(env)
	if err != nil {
		return err
	}
	if err := requireWorkflowValue(schema, *workflow); err != nil {
		return err
	}
	if _, terminal := terminalReason(*workflow); terminal {
		return cli.Usagef("Workflow %q is a terminal value and pairs with a closed issue; "+
			"reopening restores a nonterminal value: %s",
			*workflow, strings.Join(nonterminalWorkflowValues(schema), ", "))
	}
	return apply(ctx, env, tgt, *issue, transition{
		state:    stateOpen,
		reason:   reasonReopened,
		workflow: *workflow,
		rerun:    fmt.Sprintf("reopen --issue %d --workflow %q", *issue, *workflow),
	})
}

// requireWorkflowValue checks a Workflow value against the baseline schema. close's own
// values are fixed by the vocabulary, but validating them anyway means a schema that no
// longer carries `Done` is caught before the sequence starts rather than halfway through.
func requireWorkflowValue(schema *orgschema.Schema, value string) error {
	field, ok := schema.Field(render.FieldWorkflow)
	if !ok {
		return fmt.Errorf("the baseline schema defines no %q field", render.FieldWorkflow)
	}
	return validateValue(field, value)
}

// apply runs the ordered failure-safe sequence of spec FR-021.
//
// The order is fixed and the direction matters: the native state moves first, so a
// failure between the steps leaves an issue whose GitHub state is terminal and whose
// Workflow field is not — visible in every listing, and exactly what the divergence
// report names. The reverse order would leave a `Done` field on an open issue, which
// reads as a completed item and hides itself.
func apply(ctx context.Context, env *cli.Env, tgt *target, number int, move transition) error {
	repo, err := tgt.resolve(env)
	if err != nil {
		return err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return err
	}

	before, err := render.FetchIssue(ctx, client, repo, number)
	if err != nil {
		return err
	}
	if before.State == move.state && before.StateReason == move.reason &&
		before.Field(render.FieldWorkflow) == move.workflow {
		// A converged rerun is the normal end of the corrective-retry path, so it reports
		// success and writes nothing: repeating the calls would only add timeline noise
		// and consume the write budget GitHub meters.
		_, err = fmt.Fprintf(env.Stdout, "%s#%d is already %s with Workflow = %s; nothing to change.\n",
			repo, number, nativeState(move.state, move.reason), move.workflow)
		return err
	}

	// Resolving the field id first keeps a drifted schema from stranding the sequence
	// between its two steps: everything that can fail without mutating fails here.
	values, err := resolveFieldIDs(ctx, client, repo.Owner,
		[]assignment{{Name: render.FieldWorkflow, Value: move.workflow}})
	if err != nil {
		return err
	}

	// A closed issue cannot be reclassified in place. GitHub applies state_reason only when
	// the state itself changes, so PATCHing closed/not_planned to closed/completed answers
	// 200 and changes nothing — and writing the matching Workflow value on the strength of
	// that answer would manufacture the exact divergence this sequence exists to prevent,
	// permanently, since the pre-check would then compare against a reason no rerun can
	// reach. The reclassification is therefore expressed as the transition GitHub honors:
	// reopen, then close with the new reason. If the second step fails the issue is left
	// open, which the rerun converges from.
	if move.state == stateClosed && before.State == stateClosed && before.StateReason != move.reason {
		if _, err := client.SetIssueState(ctx, repo.Owner, repo.Name, number,
			stateOpen, reasonReopened); err != nil {
			return fmt.Errorf("%s#%d: reopening to reclassify the close reason from %s to %s failed, "+
				"so the issue is unchanged and nothing diverged: %w",
				repo, number, before.StateReason, move.reason, err)
		}
	}

	updated, err := client.SetIssueState(ctx, repo.Owner, repo.Name, number, move.state, move.reason)
	if err != nil {
		return fmt.Errorf("%s#%d: the native state change failed, so the Workflow field was left "+
			"untouched and nothing diverged: %w", repo, number, err)
	}
	// The API's own answer is the oracle, not the 2xx. A dropped state_reason comes back as
	// a success carrying the old value, and the Workflow field must not be written against
	// a native state GitHub did not actually record. The reason is checked only for a
	// close: `reopened` is a byproduct of the transition, while a close reason is half of
	// the terminal pairing FR-021 keeps synchronized.
	if updated.State != move.state || (move.state == stateClosed && updated.StateReason != move.reason) {
		return fmt.Errorf("%s#%d: GitHub still reports %s after the state change rather than the "+
			"requested %s, so the Workflow field was left untouched and nothing diverged; "+
			"reclassify the issue in GitHub, then rerun `gh-workflow %s`",
			repo, number, nativeState(updated.State, updated.StateReason),
			nativeState(move.state, move.reason), move.rerun)
	}

	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, number, values); err != nil {
		return fmt.Errorf("%s#%d is now %s on GitHub but its Workflow field is still %s rather than %q.\n"+
			"The terminal pairing has diverged. Rerun `gh-workflow %s` to converge; both steps are "+
			"idempotent: %w",
			repo, number, nativeState(move.state, move.reason),
			quotedOrUnset(before.Field(render.FieldWorkflow)), move.workflow, move.rerun, err)
	}

	_, err = fmt.Fprintf(env.Stdout, "%s#%d: GitHub state %s; Workflow = %s.\n",
		repo, number, nativeState(move.state, move.reason), move.workflow)
	return err
}

// nativeState renders the state and its reason the way GitHub names them, because that is
// the vocabulary the operator will see in the issue and in any follow-up API call.
func nativeState(state, reason string) string {
	if reason == "" {
		return state
	}
	return state + "/" + reason
}

func quotedOrUnset(value string) string {
	if value == "" {
		return "unset"
	}
	return fmt.Sprintf("%q", value)
}

// nonterminalWorkflowValues names what reopening may restore to. It is derived from the
// schema in file order rather than listed here, so a vocabulary change cannot leave the
// advice stale.
func nonterminalWorkflowValues(schema *orgschema.Schema) []string {
	field, ok := schema.Field(render.FieldWorkflow)
	if !ok {
		return nil
	}
	values := make([]string, 0, len(field.Values))
	for _, value := range field.Values {
		if _, terminal := terminalReason(value); !terminal {
			values = append(values, value)
		}
	}
	return values
}
