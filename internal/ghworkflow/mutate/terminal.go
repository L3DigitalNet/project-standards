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
	target := addTargetFlags(fs, true)
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
	move := transition{
		state:    stateClosed,
		reason:   terminalWorkflow[workflow],
		workflow: workflow,
		rerun:    fmt.Sprintf("close --issue %d --as %s", *issue, strings.ToLower(*as)),
	}

	schema, err := target.loadSchema(env)
	if err != nil {
		return err
	}
	if err := requireWorkflowValue(schema, workflow); err != nil {
		return err
	}
	return apply(ctx, env, target, *issue, move)
}

func runReopen(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("reopen", flag.ContinueOnError)
	target := addTargetFlags(fs, true)
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

	schema, err := target.loadSchema(env)
	if err != nil {
		return err
	}
	if err := requireWorkflowValue(schema, *workflow); err != nil {
		return err
	}
	if _, terminal := terminalWorkflow[*workflow]; terminal {
		return cli.Usagef("Workflow %q is a terminal value and pairs with a closed issue; "+
			"reopening restores a nonterminal value: %s",
			*workflow, strings.Join(nonterminalWorkflowValues(schema), ", "))
	}
	return apply(ctx, env, target, *issue, transition{
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
func apply(ctx context.Context, env *cli.Env, target *target, number int, move transition) error {
	repo, err := target.resolve(env)
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

	if _, err := client.SetIssueState(ctx, repo.Owner, repo.Name, number, move.state, move.reason); err != nil {
		return fmt.Errorf("%s#%d: the native state change failed, so the Workflow field was left "+
			"untouched and nothing diverged: %w", repo, number, err)
	}

	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, number, values); err != nil {
		return fmt.Errorf("%s#%d is now %s on GitHub but its Workflow field is still %s rather than %q: %w\n"+
			"The terminal pairing has diverged. Rerun `gh-workflow %s` to converge; both steps are idempotent",
			repo, number, nativeState(move.state, move.reason),
			quotedOrUnset(before.Field(render.FieldWorkflow)), move.workflow, err, move.rerun)
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
		if _, terminal := terminalWorkflow[value]; !terminal {
			values = append(values, value)
		}
	}
	return values
}
