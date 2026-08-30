package render

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"strings"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/topology"
)

// The two rendering subcommands register themselves, so wiring them into the binary is
// a blank import in cmd/gh-workflow rather than an edit to shared dispatch code.
func init() {
	cli.Register(&cli.Command{
		Name:    "summary",
		Summary: "print the attention-first operator summary of open work (read-only)",
		Run:     runSummary,
	})
	cli.Register(&cli.Command{
		Name:    "receipt",
		Summary: "print the observed state and findings of one issue or pull request (read-only)",
		Run:     runReceipt,
	})
}

// target carries the flags every rendering subcommand shares: which repository to read,
// and where to find the rendered policy that completes a bare repository name.
type target struct {
	repo   *string
	policy *string
	schema *string
}

func addTargetFlags(fs *flag.FlagSet) *target {
	return &target{
		repo: fs.String("repo", "", "repository as owner/name, or a bare name to complete "+
			"from policy.toml (default: this checkout's origin remote)"),
		policy: fs.String("policy", "", "path to policy.toml (default: "+cli.DefaultPolicyPath+" in this checkout)"),
		// Both surfaces became schema-dependent at 1.7: an Issue's live type is only
		// "recognized ordinary work" relative to org-schema.yaml, and the engine reads an
		// unrecognized type as none at all. Resolution matches `check` exactly, so the
		// three surfaces cannot be pointed at different vocabularies by accident.
		schema: fs.String("schema", "", "path to org-schema.yaml (default: "+cli.DefaultSchemaPath+" in this checkout)"),
	}
}

// loadSchema reads the baseline vocabulary the Issue-type normalization is resolved
// against.
func (t *target) loadSchema(env *cli.Env) (*orgschema.Schema, error) {
	path := *t.schema
	if path == "" {
		resolved, err := cli.ResolveRepoFile(env.WorkDir, cli.DefaultSchemaPath)
		if err != nil {
			return nil, err
		}
		path = resolved
	}
	return orgschema.Load(path)
}

// resolve determines the repository to read.
//
// The order is deliberate: an explicit flag wins, a bare name is completed from the
// rendered policy's organization, and otherwise the checkout names itself through its
// origin remote. A malformed flag value is the operator's mistake and exits as a usage
// error; an unresolvable checkout is an unmet precondition and exits as a failure with
// the flag that fixes it.
func (t *target) resolve(env *cli.Env) (Repository, error) {
	if *t.repo == "" {
		repo, err := OriginRepository(env.WorkDir)
		if err != nil {
			return Repository{}, asIdentityRefusal(fmt.Errorf("%w; pass --repo owner/name", err))
		}
		return repo, nil
	}

	if strings.Contains(*t.repo, "/") {
		repo, err := ParseRepository(*t.repo)
		if err != nil {
			return Repository{}, cli.Usagef("%v", err)
		}
		return repo, nil
	}

	organization, err := policyOrganization(env, *t.policy)
	if err != nil {
		return Repository{}, asIdentityRefusal(err)
	}
	return Repository{Owner: organization, Name: *t.repo}, nil
}

// asIdentityRefusal reclassifies an identity refusal as a usage error.
//
// IR-005 separates a local refusal (exit 2) from a failure that completed a read and
// found something wrong (exit 1), and a value that is not a GitHub identity is always
// the former — whatever supplied it. Every refusal in ghapi's identity boundary wraps
// ErrInvalidIdentity, so this one test covers the explicit flag, the origin remote, and
// the rendered policy's organization alike; a missing origin remote or an unreadable
// policy file is a genuine precondition failure and passes through untouched.
func asIdentityRefusal(err error) error {
	if errors.Is(err, ghapi.ErrInvalidIdentity) {
		return cli.Usagef("%v", err)
	}
	return err
}

// policyOrganization reads the organization from the rendered consumer policy, which is
// the only place the tool learns it when the repository name alone was given (DR-002).
func policyOrganization(env *cli.Env, explicit string) (string, error) {
	path := explicit
	if path == "" {
		resolved, err := cli.ResolveRepoFile(env.WorkDir, cli.DefaultPolicyPath)
		if err != nil {
			return "", err
		}
		path = resolved
	}
	consumerPolicy, err := policy.Load(path)
	if err != nil {
		return "", err
	}
	return consumerPolicy.Organization, nil
}

func parse(fs *flag.FlagSet, env *cli.Env, args []string, usage string) error {
	fs.SetOutput(env.Stderr)
	fs.Usage = func() {
		_, _ = fmt.Fprint(env.Stderr, usage+"\nFlags:\n")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return err
		}
		return &cli.UsageError{Err: err}
	}
	if fs.NArg() > 0 {
		return cli.Usagef("unexpected argument %q; %s takes flags only", fs.Arg(0), fs.Name())
	}
	return nil
}

// runSummary aggregates: every open work item, each contributing the findings its own
// observed state admits (FR-017).
func runSummary(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("summary", flag.ContinueOnError)
	tgt := addTargetFlags(fs)
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow summary [flags]\n\n"+
		"Prints the attention-first operator summary of open work in the packaged layout,\n"+
		"for relaying verbatim. Read-only: it mutates nothing and writes no file.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}

	repo, schema, client, err := tgt.open(ctx, env)
	if err != nil {
		return err
	}
	read, err := Fetch(ctx, client, repo)
	if err != nil {
		return err
	}
	// Each open pull request costs its own bounded topology load. Deriving PR findings
	// from the list read alone is not an option: mergeability, live enforcement, and the
	// review decision are simply absent from it, and the Merge predicates would report
	// every open PR as "evidence unknown" — a summary that cries wolf on every row.
	for _, pull := range read.PullRequests {
		gate, err := topology.Load(ctx, client, repo.Owner, repo.Name, schema, pull.Number, "")
		if err != nil {
			return err
		}
		read.AddFindings(FilterByObservedState(gate.Topology.PullRequest, gate.Result.Findings)...)
	}

	envelope := cli.NewEnvelope("summary", reportResult(read.Findings),
		cli.Target{Kind: cli.TargetRepository, Repository: repo.String()})
	envelope.Findings = read.Findings
	return emit(env, mode, Summary(read), NewSummaryDocument(envelope, read))
}

// runReceipt describes one work item: the state it is in, and the findings that state
// admits (FR-018).
func runReceipt(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("receipt", flag.ContinueOnError)
	tgt := addTargetFlags(fs)
	issue := fs.Int("issue", 0, "issue number to render a receipt for")
	pull := fs.Int("pr", 0, "pull request number to render a receipt for")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow receipt --issue N | --pr N [flags]\n\n"+
		"Prints the observed state of one issue or pull request and the findings that\n"+
		"state admits. Read-only; exits 0 whenever it renders.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if (*issue == 0) == (*pull == 0) {
		return cli.Usagef("pass exactly one of --issue or --pr")
	}
	if *issue < 0 || *pull < 0 {
		return cli.Usagef("issue and pull request numbers are positive")
	}

	repo, schema, client, err := tgt.open(ctx, env)
	if err != nil {
		return err
	}
	if *issue != 0 {
		return issueReceipt(ctx, env, client, repo, mode, *issue)
	}
	return pullRequestReceipt(ctx, env, client, repo, schema, mode, *pull)
}

// issueReceipt projects one issue read on its own.
func issueReceipt(ctx context.Context, env *cli.Env, client *ghapi.Client,
	repo Repository, mode cli.OutputMode, number int,
) error {
	item, err := FetchIssue(ctx, client, repo, number)
	if err != nil {
		return err
	}
	findings := IssueFindings(item, time.Now().UTC())
	envelope := cli.NewEnvelope("receipt", reportResult(findings),
		cli.Target{Kind: cli.TargetIssue, Number: number, Repository: repo.String(), URL: item.URL})
	envelope.Findings = findings
	return emitReceipt(env, mode, item, envelope)
}

// pullRequestReceipt projects one pull request through the shared engine.
//
// The gate is inferred from observed state and the findings are then filtered to the
// phases that state admits, so a receipt and a bare `check --pr` on the same PR reach the
// same verdict from the same snapshot — that equivalence is what FR-022 buys.
func pullRequestReceipt(ctx context.Context, env *cli.Env, client *ghapi.Client,
	repo Repository, schema *orgschema.Schema, mode cli.OutputMode, number int,
) error {
	gate, err := topology.Load(ctx, client, repo.Owner, repo.Name, schema, number, "")
	if err != nil {
		return err
	}
	item, err := FetchPullRequest(ctx, client, repo, number)
	if err != nil {
		return err
	}
	// Not reordered: the envelope's `findings` stays in the engine's evaluation order, so
	// a receipt and a `check --pr` on the same PR emit the same list in the same order and
	// the cross-surface equivalence is byte-comparable. Display order is applied by the
	// human renderer, which is where it belongs.
	findings := FilterByObservedState(gate.Topology.PullRequest, gate.Result.Findings)
	envelope := cli.NewEnvelope("receipt", reportResult(findings),
		cli.Target{Kind: cli.TargetPullRequest, Number: number, Repository: repo.String(), URL: item.URL})
	envelope.Findings = findings
	return emitReceipt(env, mode, item, envelope)
}

// open resolves the three things both surfaces need before any read: which repository,
// which schema vocabulary, and an authenticated client.
func (t *target) open(ctx context.Context, env *cli.Env) (Repository, *orgschema.Schema, *ghapi.Client, error) {
	repo, err := t.resolve(env)
	if err != nil {
		return Repository{}, nil, nil, err
	}
	schema, err := t.loadSchema(env)
	if err != nil {
		return Repository{}, nil, nil, err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return Repository{}, nil, nil, err
	}
	return repo, schema, client, nil
}

// emitReceipt writes the header and then the shared envelope rendering.
//
// In human mode the two are written as one buffer, so a failed write leaves no header
// stranded without its findings. In JSON mode the header has no place: the envelope's
// `item` projection carries the same state as structured data.
func emitReceipt(env *cli.Env, mode cli.OutputMode, item WorkItem, envelope cli.Envelope) error {
	if mode == cli.OutputJSON {
		return emit(env, mode, "", newReceiptDocument(envelope, item))
	}
	var b strings.Builder
	b.WriteString(Receipt(item))
	b.WriteString("\n")
	if err := cli.WriteEnvelope(envelope, mode, &cli.Env{Stdout: &b}); err != nil {
		return err
	}
	_, err := env.Stdout.Write([]byte(b.String()))
	return err
}

// emit renders in the requested mode and writes once, after every fallible step has
// succeeded (spec FR-016's no-partial-report rule, applied to these surfaces too).
func emit(env *cli.Env, mode cli.OutputMode, human string, report any) error {
	rendered := []byte(human)
	if mode == cli.OutputJSON {
		encoded, err := cli.MarshalJSON(report)
		if err != nil {
			return err
		}
		rendered = encoded
	}
	if _, err := env.Stdout.Write(rendered); err != nil {
		return fmt.Errorf("writing the report: %w", err)
	}
	return nil
}
