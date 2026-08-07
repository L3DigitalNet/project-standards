package mutate

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// canonicalBody is the issue-structure reference's body contract as a scaffold: the eight
// headings in their fixed order, with nothing under them.
//
// The tool supplies the skeleton and never the content — what the work is remains the
// agent's judgment. Every heading is emitted even though the reference calls most of them
// optional, because an absent heading in a scaffold reads as "not applicable" while an
// empty one reads as "not filled in yet", and the second is the honest state of a
// just-created issue.
const canonicalBody = `## Outcome

## Context

## Scope

## Out of scope

## Acceptance criteria

## Constraints

## Evidence / references

## Verification
`

func runNew(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("new", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	title := fs.String("title", "", "issue title")
	issueType := fs.String("type", "", "Issue Type: one of the five in the organization schema")
	bodyFile := fs.String("body-file", "", "file holding the authored issue body "+
		"(default: the canonical heading scaffold)")
	fields := addFieldFlag(fs, "initial Issue Field assignment as Name=Value; repeat for several fields")
	output := fs.String("output", string(cli.OutputHuman), "receipt format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow new --type TYPE --title TITLE [flags]\n\n"+
		"Creates a typed issue carrying the canonical body headings and the initial field\n"+
		"values given, then prints the creation receipt. The Issue Type and every field\n"+
		"value is validated against org-schema.yaml before anything is created.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if *title == "" {
		return cli.Usagef("pass --title")
	}
	if *issueType == "" {
		return cli.Usagef("pass --type with one of the organization's Issue Types")
	}

	schema, err := tgt.loadSchema(env)
	if err != nil {
		return err
	}
	if err := validateIssueType(schema, *issueType); err != nil {
		return err
	}
	if err := fields.validate(schema, false); err != nil {
		return err
	}
	body, err := issueBody(*bodyFile)
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
	values, err := resolveFieldIDs(ctx, client, repo.Owner, fields.items)
	if err != nil {
		return err
	}

	created, err := client.CreateIssue(ctx, repo.Owner, repo.Name, ghapi.CreateIssueRequest{
		Title:  *title,
		Body:   body,
		Type:   *issueType,
		Fields: values,
	})
	if err != nil {
		return err
	}

	// The receipt reports what is actually set, not what was requested, so it is built
	// from a fresh read rather than from the creation response — the two differ whenever
	// GitHub drops a value the caller had no permission to apply. A failed read-back
	// still has to name the issue that now exists; losing its number would be worse than
	// the missing receipt.
	item, err := render.FetchIssue(ctx, client, repo, created.Number)
	if err != nil {
		return fmt.Errorf("created %s#%d (%s) but could not read it back for the receipt: %w",
			repo, created.Number, created.HTMLURL, err)
	}
	return emit(env, mode, func() string { return render.Receipt(item) }, render.NewReceiptReport(item))
}

func issueBody(path string) (string, error) {
	if path == "" {
		return canonicalBody, nil
	}
	// #nosec G304 -- the path is the operator's --body-file flag; reading the file they
	// named is the whole point of the flag.
	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("reading the issue body %s: %w", path, err)
	}
	return string(data), nil
}
