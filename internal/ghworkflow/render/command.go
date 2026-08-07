package render

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
)

// The three rendering subcommands register themselves, so wiring them into the binary is
// a blank import in cmd/gh-workflow rather than an edit to shared dispatch code.
func init() {
	cli.Register(&cli.Command{
		Name:    "ledger",
		Summary: "regenerate the repository's docs/GH-WORKFLOWS.md work-state ledger",
		Run:     runLedger,
	})
	cli.Register(&cli.Command{
		Name:    "summary",
		Summary: "print the attention-first operator summary of open work (read-only)",
		Run:     runSummary,
	})
	cli.Register(&cli.Command{
		Name:    "receipt",
		Summary: "print the creation receipt for one issue or pull request (read-only)",
		Run:     runReceipt,
	})
}

// target carries the flags every rendering subcommand shares: which repository to read,
// and where to find the rendered policy that completes a bare repository name.
type target struct {
	repo   *string
	policy *string
}

func addTargetFlags(fs *flag.FlagSet) *target {
	return &target{
		repo: fs.String("repo", "", "repository as owner/name, or a bare name to complete "+
			"from policy.toml (default: this checkout's origin remote)"),
		policy: fs.String("policy", "", "path to policy.toml (default: "+cli.DefaultPolicyPath+" in this checkout)"),
	}
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
			return Repository{}, fmt.Errorf("%w; pass --repo owner/name", err)
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
		return Repository{}, err
	}
	return Repository{Owner: organization, Name: *t.repo}, nil
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

// snapshot performs the whole read. Every fallible step finishes before a caller writes
// anything, so a failed read produces no partial report and no ledger mutation.
func snapshot(ctx context.Context, env *cli.Env, t *target) (*Snapshot, error) {
	repo, err := t.resolve(env)
	if err != nil {
		return nil, err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return nil, err
	}
	return Fetch(ctx, client, repo)
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

func runLedger(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("ledger", flag.ContinueOnError)
	target := addTargetFlags(fs)
	path := fs.String("path", "", "ledger path to write (default: "+LedgerRelPath+" at the checkout root)")
	if err := parse(fs, env, args, "Usage: gh-workflow ledger [flags]\n\n"+
		"Regenerates the repository's work-state ledger from live GitHub state. The file\n"+
		"is owned whole-file by the tool: it is replaced atomically and manual edits are\n"+
		"overwritten. A failed refresh leaves the previous file byte-identical.\n"); err != nil {
		return err
	}

	destination, err := ledgerPath(env, *path)
	if err != nil {
		return err
	}
	read, err := snapshot(ctx, env, target)
	if err != nil {
		return err
	}
	if err := WriteAtomic(destination, []byte(Ledger(read))); err != nil {
		return err
	}

	_, err = fmt.Fprintf(env.Stdout, "Wrote %s: %s, %s, %s needing attention.\n",
		destination,
		plural(len(read.Issues), "open issue", "open issues"),
		plural(len(read.PullRequests), "open PR", "open PRs"),
		plural(len(read.Attention()), "item", "items"))
	return err
}

func ledgerPath(env *cli.Env, explicit string) (string, error) {
	if explicit != "" {
		return explicit, nil
	}
	root, err := CheckoutRoot(env.WorkDir)
	if err != nil {
		return "", fmt.Errorf("%w; pass --path", err)
	}
	return filepath.Join(root, filepath.FromSlash(LedgerRelPath)), nil
}

func runSummary(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("summary", flag.ContinueOnError)
	target := addTargetFlags(fs)
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

	read, err := snapshot(ctx, env, target)
	if err != nil {
		return err
	}
	return emit(env, mode, Summary(read), NewSummaryReport(read))
}

func runReceipt(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("receipt", flag.ContinueOnError)
	target := addTargetFlags(fs)
	issue := fs.Int("issue", 0, "issue number to render a receipt for")
	pull := fs.Int("pr", 0, "pull request number to render a receipt for")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow receipt --issue N | --pr N [flags]\n\n"+
		"Prints the creation receipt for one issue or pull request: the fields actually\n"+
		"set and a line naming what is still missing. Read-only.\n"); err != nil {
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

	repo, err := target.resolve(env)
	if err != nil {
		return err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return err
	}

	var item WorkItem
	if *issue != 0 {
		item, err = FetchIssue(ctx, client, repo, *issue)
	} else {
		item, err = FetchPullRequest(ctx, client, repo, *pull)
	}
	if err != nil {
		return err
	}
	return emit(env, mode, Receipt(item), NewReceiptReport(item))
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
