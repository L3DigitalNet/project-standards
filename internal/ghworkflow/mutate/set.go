package mutate

import (
	"context"
	"flag"
	"fmt"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
)

func runSet(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("set", flag.ContinueOnError)
	target := addTargetFlags(fs, true)
	issue := fs.Int("issue", 0, "issue number to update")
	fields := addFieldFlag(fs, "Issue Field assignment as Name=Value; repeat for several fields")
	if err := parse(fs, env, args, "Usage: gh-workflow set --issue N --field Name=Value [flags]\n\n"+
		"Sets Issue Field values after validating every one against org-schema.yaml. An\n"+
		"invalid value is refused with the valid list and nothing is sent to GitHub.\n"+
		"Fields not named here keep their current values.\n"); err != nil {
		return err
	}
	if err := requireIssue(*issue); err != nil {
		return err
	}
	if len(fields.items) == 0 {
		return cli.Usagef("pass at least one --field Name=Value")
	}

	// Validation first, and entirely offline: after this point the invocation is known
	// good, so anything that fails is the environment rather than the request (EC-008).
	schema, err := target.loadSchema(env)
	if err != nil {
		return err
	}
	if err := fields.validate(schema, false); err != nil {
		return err
	}

	repo, err := target.resolve(env)
	if err != nil {
		return err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return err
	}
	values, err := resolveFieldIDs(ctx, client, repo.Owner, fields.items)
	if err != nil {
		return err
	}
	if err := client.AddIssueFieldValues(ctx, repo.Owner, repo.Name, *issue, values); err != nil {
		return err
	}

	_, err = fmt.Fprintf(env.Stdout, "%s#%d: %s\n", repo, *issue, describe(fields.items))
	return err
}
