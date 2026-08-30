package mutate

import (
	"context"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

func runSet(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("set", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	issue := fs.Int("issue", 0, "issue number to update")
	issueType := fs.String("type", "", "Issue Type to assign, from the organization schema's vocabulary")
	fields := addFieldFlag(fs, "Issue Field assignment as Name=Value; repeat for several fields")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow set --issue N [--type TYPE] [--field Name=Value ...] [flags]\n\n"+
		"Sets the Issue Type and Issue Field values after validating every one against\n"+
		"org-schema.yaml. An invalid value is refused with the valid list and nothing is\n"+
		"sent to GitHub. Anything not named here keeps its current value.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if err := requireIssue(*issue); err != nil {
		return err
	}
	// Either flag alone is a complete invocation. The older rule — at least one --field —
	// would make --type reachable only alongside a field assignment the operator may have
	// no reason to make, which is no route at all for the case this flag exists to close:
	// an issue created outside the tool, where GitHub leaves the type optional.
	if len(fields.items) == 0 && *issueType == "" {
		return cli.Usagef("pass at least one --field Name=Value or --type TYPE")
	}

	// Validation first, and entirely offline: after this point the invocation is known
	// good, so anything that fails is the environment rather than the request (EC-008).
	schema, err := tgt.loadSchema(env)
	if err != nil {
		return err
	}
	if *issueType != "" {
		if err := validateIssueType(schema, *issueType); err != nil {
			return err
		}
	}
	if err := fields.validate(schema, false); err != nil {
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
	// Resolving the field ids before the first write keeps a drifted schema from stranding a
	// combined invocation between its two calls: everything that can fail without mutating
	// fails here, exactly as the terminal sequence orders it.
	values, err := resolveFieldIDs(ctx, client, repo.Owner, fields.items)
	if err != nil {
		return err
	}

	// The two writes are ordered boundaries like every other paired sequence: the type
	// first, the field values second, so a failure between them is reported as the exact
	// half-applied state it produced (ERR-014) rather than as a bare error.
	rec := newSteps(stepIssueType, stepFieldValues)
	writeErr := setWrites(ctx, client, repo, *issue, *issueType, values, rec)

	if mode == cli.OutputJSON {
		envelope := cli.NewEnvelope("set", cli.Classify(writeErr),
			cli.Target{Kind: cli.TargetIssue, Number: *issue, Repository: repo.String()})
		envelope.Steps = rec.list()
		if err := cli.WriteEnvelope(envelope, mode, env); err != nil {
			return err
		}
		return writeErr
	}
	if writeErr != nil {
		return writeErr
	}
	_, err = fmt.Fprintf(env.Stdout, "%s#%d: %s\n", repo, *issue, describeSet(*issueType, fields.items))
	return err
}

// The ordered boundaries of a `set` invocation.
const (
	stepIssueType   = "issue-type"
	stepFieldValues = "field-values"
)

// setWrites performs the two ordered writes, recording each boundary.
func setWrites(ctx context.Context, client *ghapi.Client, repo render.Repository, number int,
	issueType string, values []ghapi.IssueFieldAssignment, rec *steps,
) error {
	if issueType == "" {
		rec.skip(stepIssueType, "no --type was requested")
	} else {
		if err := applyIssueType(ctx, client, repo, number, issueType, len(values) > 0); err != nil {
			rec.fail(stepIssueType, "whether the Issue Type change reached GitHub is unknown")
			return err
		}
		rec.complete(stepIssueType, "Type = "+issueType)
	}
	if len(values) == 0 {
		rec.skip(stepFieldValues, "no --field was requested")
		return nil
	}
	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, number, values); err != nil {
		rec.fail(stepFieldValues, "the requested field values are untouched")
		if issueType != "" {
			return fmt.Errorf("%s#%d: the Issue Type is now %q but the field assignments that "+
				"follow it failed, so those fields are untouched; rerun the same invocation to "+
				"converge, since setting a type the issue already carries changes nothing: %w",
				repo, number, issueType, err)
		}
		return err
	}
	rec.complete(stepFieldValues, "the requested field values are written")
	return nil
}

// applyIssueType writes the type and verifies GitHub actually recorded it.
//
// The read-back is not defensive padding, and it is the one place `set` needs an oracle
// that the field write does not. GitHub documents the type as settable only with push
// access, and that "without push access to the repository, type changes are silently
// dropped" — a 200 carrying the issue's previous type. Field values have no such quiet
// path here: resolveFieldIDs already resolved every name against the live organization
// before the first write, so a name the organization does not define has failed while
// nothing had mutated. The type name gets no equivalent live resolution, which leaves the
// PATCH's own response body as the only evidence that the write landed. Pre-resolving it
// through ListIssueTypes was rejected: it buys nothing — the type PATCH is the first write,
// so its failure strands no half-applied issue — and costs a GET on every invocation.
//
// pendingFields reports whether field assignments are still waiting behind this call. Only
// that half is claimed in the failure text: the field write is ordered after this one and
// therefore provably has not happened, while what became of the type itself is not always
// knowable — a transport failure can be a request that landed and an answer that was lost.
func applyIssueType(ctx context.Context, client *ghapi.Client, repo render.Repository,
	number int, issueType string, pendingFields bool,
) error {
	updated, err := client.SetIssueType(ctx, repo.Owner, repo.Name, number, issueType)
	if err != nil {
		return fmt.Errorf("%s#%d: setting the Issue Type failed%s, and whether the change reached "+
			"GitHub is unknown; rerun the same invocation to converge: %w",
			repo, number, unwrittenFieldsClause(pendingFields), err)
	}
	if applied := issueTypeName(updated); applied != issueType {
		return fmt.Errorf("%s#%d: GitHub reports the Issue Type as %s after the change rather than "+
			"the requested %q%s. A type change made without push access to the repository is "+
			"silently dropped, so check this token's access to the repository and rerun",
			repo, number, quotedOrUnset(applied), issueType, unwrittenFieldsClause(pendingFields))
	}
	return nil
}

// unwrittenFieldsClause is the sentence fragment naming field values a failed type write
// leaves unsent, and nothing when the invocation requested none.
func unwrittenFieldsClause(pending bool) string {
	if pending {
		return ", so no field values were written"
	}
	return ""
}

// issueTypeName is the type GitHub reports, or "" for an issue carrying none — the state
// every issue created outside this tool starts in, and the one --type exists to leave.
func issueTypeName(issue *ghapi.Issue) string {
	if issue == nil || issue.Type == nil {
		return ""
	}
	return issue.Type.Name
}

// describeSet renders the receipt's applied list. The Issue Type is not an Issue Field and
// travels through a different endpoint, but it reads out in the same `Name = Value` form
// because the line answers one question — what this issue now carries — and a type-only
// invocation would otherwise print an empty receipt.
func describeSet(issueType string, items []assignment) string {
	parts := make([]string, 0, 2)
	if issueType != "" {
		parts = append(parts, "Type = "+issueType)
	}
	if len(items) > 0 {
		parts = append(parts, describe(items))
	}
	return strings.Join(parts, ", ")
}
