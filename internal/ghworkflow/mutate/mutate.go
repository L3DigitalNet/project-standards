// Package mutate is the tool's validated write surface: the four subcommands that change
// repository work state — `new`, `set`, `close`, `reopen` — and read-only `check`, which
// verifies the preconditions that make an issue eligible for `Ready` (spec FR-021,
// FR-023).
//
// One rule shapes every path here: validation precedes any mutating call. A value the
// baseline schema does not define is refused before a client is even built, so a refusal
// leaves GitHub untouched by construction rather than by cleanup (spec EC-008). The
// organization schema itself is never written — these subcommands address repositories,
// and schema changes remain human work.
//
// The second shaping rule is FR-021's terminal pairing. `Workflow` and GitHub's native
// open/closed state answer different questions and must agree at the terminals, but they
// live behind two independent API calls, so no atomic transition exists. What does exist
// is an ordered, idempotent sequence — native state with its close reason first, then the
// `Workflow` value — where a failure between the steps is reported as the exact divergence
// it produced and rerunning the same subcommand is the corrective retry.
package mutate

import (
	"errors"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The five subcommands register themselves, so wiring them into the binary is a blank
// import in cmd/gh-workflow rather than an edit to shared dispatch code.
func init() {
	cli.Register(&cli.Command{
		Name:    "new",
		Summary: "create a typed issue with the canonical body headings and initial field values",
		Run:     runNew,
	})
	cli.Register(&cli.Command{
		Name:    "set",
		Summary: "set Issue Field values, validated against the baseline organization schema",
		Run:     runSet,
	})
	cli.Register(&cli.Command{
		Name:    "close",
		Summary: "apply a terminal transition: native close reason first, then the Workflow value",
		Run:     runClose,
	})
	cli.Register(&cli.Command{
		Name:    "reopen",
		Summary: "reopen an issue and restore a nonterminal Workflow value",
		Run:     runReopen,
	})
	cli.Register(&cli.Command{
		Name:    "check",
		Summary: "verify an issue's Ready preconditions and itemize the findings (read-only)",
		Run:     runCheck,
	})
}

// target carries the flags every subcommand here shares: which repository to address,
// where the rendered policy completing a bare repository name lives, and — for the
// subcommands that validate values — where the baseline schema lives.
type target struct {
	repo   *string
	policy *string
	schema *string
}

func addTargetFlags(fs *flag.FlagSet, withSchema bool) *target {
	t := &target{
		repo: fs.String("repo", "", "repository as owner/name, or a bare name to complete "+
			"from policy.toml (default: this checkout's origin remote)"),
		policy: fs.String("policy", "", "path to policy.toml (default: "+cli.DefaultPolicyPath+" in this checkout)"),
	}
	if withSchema {
		t.schema = fs.String("schema", "", "path to org-schema.yaml (default: "+cli.DefaultSchemaPath+" in this checkout)")
	}
	return t
}

// resolve determines the repository to address. An explicit flag wins, a bare name is
// completed from the rendered policy's organization, and otherwise the checkout names
// itself through its origin remote (IR-004).
func (t *target) resolve(env *cli.Env) (render.Repository, error) {
	if *t.repo == "" {
		repo, err := render.OriginRepository(env.WorkDir)
		if err != nil {
			return render.Repository{}, fmt.Errorf("%w; pass --repo owner/name", err)
		}
		return repo, nil
	}
	if strings.Contains(*t.repo, "/") {
		repo, err := render.ParseRepository(*t.repo)
		if err != nil {
			return render.Repository{}, cli.Usagef("%v", err)
		}
		return repo, nil
	}

	path := *t.policy
	if path == "" {
		resolved, err := cli.ResolveRepoFile(env.WorkDir, cli.DefaultPolicyPath)
		if err != nil {
			return render.Repository{}, err
		}
		path = resolved
	}
	consumerPolicy, err := policy.Load(path)
	if err != nil {
		return render.Repository{}, err
	}
	return render.Repository{Owner: consumerPolicy.Organization, Name: *t.repo}, nil
}

// loadSchema reads the baseline vocabulary every value is validated against. It runs
// before anything reaches the network, so a schema the tool cannot read is a precondition
// failure rather than a half-applied mutation.
func (t *target) loadSchema(env *cli.Env) (*orgschema.Schema, error) {
	// A subcommand that validates no values registers no --schema flag, so reaching here
	// without one is a wiring mistake rather than an operator error. It is refused instead
	// of quietly falling back to the delivered default, which would validate against a
	// schema the invocation had no way to name or override.
	if t.schema == nil {
		return nil, errors.New("internal: a subcommand registered without --schema asked for the schema")
	}
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

// requireIssue rejects a missing or nonsensical issue number before any resolution work.
func requireIssue(number int) error {
	if number <= 0 {
		return cli.Usagef("pass --issue with a positive issue number")
	}
	return nil
}

// emit renders in the requested mode and writes once, after every fallible step has
// succeeded (spec FR-016's no-partial-report rule, applied to these surfaces too). The
// human form is a function so JSON mode never pays to build a string it discards.
func emit(env *cli.Env, mode cli.OutputMode, human func() string, report any) error {
	var rendered []byte
	if mode == cli.OutputJSON {
		encoded, err := cli.MarshalJSON(report)
		if err != nil {
			return err
		}
		rendered = encoded
	} else {
		rendered = []byte(human())
	}
	if _, err := env.Stdout.Write(rendered); err != nil {
		return fmt.Errorf("writing the report: %w", err)
	}
	return nil
}
