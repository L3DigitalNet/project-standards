package audit

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
)

// The subcommand registers itself, so wiring it into the binary is a blank import in
// cmd/gh-workflow rather than an edit to shared dispatch code.
func init() {
	cli.Register(&cli.Command{
		Name:    "audit",
		Summary: "compare live organization Issue Types and Issue Fields to the baseline (read-only)",
		Run:     run,
	})
}

func run(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("audit", flag.ContinueOnError)
	fs.SetOutput(env.Stderr)
	var (
		schemaPath  = fs.String("schema", "", "path to org-schema.yaml (default: "+cli.DefaultSchemaPath+" in this checkout)")
		policyPath  = fs.String("policy", "", "path to policy.toml (default: "+cli.DefaultPolicyPath+" in this checkout)")
		org         = fs.String("org", "", "organization login to audit (default: the organization in policy.toml)")
		output      = fs.String("output", string(cli.OutputHuman), "output format: human or json")
		failOnDrift = fs.Bool("fail-on-drift", false, "exit nonzero when the audit finds any drift")
	)
	fs.Usage = func() {
		_, _ = fmt.Fprint(env.Stderr, "Usage: gh-workflow audit [flags]\n\n"+
			"Compares the organization's live Issue Types and Issue Fields to the\n"+
			"baseline schema. Read-only: it never mutates organization schema.\n\nFlags:\n")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return err
		}
		return &cli.UsageError{Err: err}
	}
	if fs.NArg() > 0 {
		return cli.Usagef("unexpected argument %q; audit takes flags only", fs.Arg(0))
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}

	// Everything below is a precondition. FR-016 requires that an unmet precondition
	// exit nonzero with no partial report, so the report is rendered into memory and
	// written to stdout only once every fallible step has succeeded.
	report, err := collect(ctx, env, *schemaPath, *policyPath, *org)
	if err != nil {
		return err
	}

	var rendered []byte
	if mode == cli.OutputJSON {
		if rendered, err = cli.MarshalJSON(report); err != nil {
			return err
		}
	} else {
		rendered = []byte(renderHuman(report))
	}
	if _, err := env.Stdout.Write(rendered); err != nil {
		return fmt.Errorf("writing the audit report: %w", err)
	}

	if *failOnDrift && report.HasDrift() {
		// The audit itself succeeded, so the report is owed and already written; the
		// nonzero exit is the requested drift signal, not a precondition failure.
		return fmt.Errorf("organization schema has drifted from the baseline: %d missing, %d mismatched, %d unexpected",
			report.Counts.Missing, report.Counts.Mismatch, report.Counts.Extra)
	}
	return nil
}

func collect(ctx context.Context, env *cli.Env, schemaFlag, policyFlag, orgFlag string) (*Report, error) {
	resolvedSchema, err := resolve(env, schemaFlag, cli.DefaultSchemaPath)
	if err != nil {
		return nil, err
	}
	schema, err := orgschema.Load(resolvedSchema)
	if err != nil {
		return nil, err
	}

	organization := orgFlag
	if organization == "" {
		// An explicit --org makes policy.toml unnecessary; without it the rendered
		// policy is the only source of the organization login, so its absence is a
		// precondition failure rather than a prompt (IR-004: non-interactive).
		resolvedPolicy, err := resolve(env, policyFlag, cli.DefaultPolicyPath)
		if err != nil {
			return nil, err
		}
		consumerPolicy, err := policy.Load(resolvedPolicy)
		if err != nil {
			return nil, err
		}
		organization = consumerPolicy.Organization
	}

	client, err := env.Client(ctx)
	if err != nil {
		return nil, err
	}
	liveTypes, err := client.ListIssueTypes(ctx, organization)
	if err != nil {
		return nil, err
	}
	liveFields, err := client.ListIssueFields(ctx, organization)
	if err != nil {
		return nil, err
	}

	return NewReport(organization, resolvedSchema, Compare(schema, liveTypes, liveFields)), nil
}

// resolve honors an explicit flag and otherwise searches upward for the delivered
// artifact, which is what makes a bare `gh-workflow audit` work from anywhere in a
// consumer checkout (IR-004).
func resolve(env *cli.Env, explicit, deliveredPath string) (string, error) {
	if explicit != "" {
		return explicit, nil
	}
	return cli.ResolveRepoFile(env.WorkDir, deliveredPath)
}

func renderHuman(report *Report) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Organization: %s\n", report.Organization)
	fmt.Fprintf(&b, "Baseline:     %s\n", report.SchemaPath)

	writeSection(&b, "Issue types", report.Findings, KindIssueType)
	writeSection(&b, "Issue fields", report.Findings, KindIssueField)

	fmt.Fprintf(&b, "\nSummary: %d match, %d missing, %d mismatch, %d extra\n",
		report.Counts.Match, report.Counts.Missing, report.Counts.Mismatch, report.Counts.Extra)
	if !report.HasDrift() {
		b.WriteString("The organization matches the baseline schema.\n")
	} else {
		b.WriteString("Schema changes are applied by a human in the GitHub UI or API; this audit never mutates.\n")
	}
	return b.String()
}

func writeSection(b *strings.Builder, title string, findings []Finding, kind Kind) {
	fmt.Fprintf(b, "\n%s\n", title)
	written := 0
	for _, finding := range findings {
		if finding.Kind != kind {
			continue
		}
		fmt.Fprintf(b, "  %-9s %s — %s\n", finding.Status, finding.Name, finding.Detail)
		written++
	}
	if written == 0 {
		b.WriteString("  (none)\n")
	}
}
