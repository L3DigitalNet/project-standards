package admission

// `gh-workflow admission --branch B` (ADR 0031 D3): the classifier that gives the
// admission rule an enforcement mechanism it had none of through payload 1.8.
//
// The subcommand registers itself, so wiring it into the binary is a blank import in
// cmd/gh-workflow rather than an edit to shared dispatch code.

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"sort"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

func init() {
	cli.Register(&cli.Command{
		Name:    "admission",
		Summary: "classify how each commit on a governed branch was admitted (offline-capable)",
		Run:     run,
	})
}

// Report is the whole result of one run, in the shape the JSON output marshals.
type Report struct {
	Branch   string    `json:"branch"`
	Since    string    `json:"since,omitempty"`
	Offline  bool      `json:"offline"`
	Commits  int       `json:"commits"`
	Counts   Counts    `json:"counts"`
	Findings []Finding `json:"findings"`
}

// Counts is the per-class census. It is reported even on a clean run because the shape
// of a repository's admissions is the evidence that the check is not vacuous: an
// all-zero census with a zero exit means the range was empty, not that the rule holds.
type Counts struct {
	T0          int `json:"t0"`
	PullRequest int `json:"pull_request"`
	Handoff     int `json:"handoff"`
	Release     int `json:"release"`
	Unadmitted  int `json:"unadmitted"`
}

func run(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("admission", flag.ContinueOnError)
	fs.SetOutput(env.Stderr)
	var (
		branch     = fs.String("branch", "", "governed branch to classify (default: the configured integration branch)")
		since      = fs.String("since", "", "commit-ish enforcement floor, exclusive (default: the configured admission_floor)")
		policyPath = fs.String("policy", "", "path to policy.toml (default: "+cli.DefaultPolicyPath+" in this checkout)")
		repoFlag   = fs.String("repo", "", "owner/name to verify PR trailers against (default: this checkout's origin)")
		offline    = fs.Bool("offline", false, "classify without any GitHub call; PR trailers are taken at face value")
		output     = fs.String("output", string(cli.OutputHuman), "output format: human or json")
	)
	fs.Usage = func() {
		_, _ = fmt.Fprint(env.Stderr, "Usage: gh-workflow admission --branch B [--since REF] [--offline] [flags]\n\n"+
			"Classifies every commit in the range against the four admission classes and\n"+
			"exits 1 listing the commits no class admits. Read-only: it never writes to the\n"+
			"repository or to GitHub.\n\nFlags:\n")
		fs.PrintDefaults()
	}
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return err
		}
		return &cli.UsageError{Err: err}
	}
	if fs.NArg() > 0 {
		return cli.Usagef("unexpected argument %q; admission takes flags only", fs.Arg(0))
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}

	settings, err := loadSettings(env, *policyPath, *branch, *since)
	if err != nil {
		return err
	}
	commits, err := ReadCommits(ctx, env.WorkDir, settings.Range)
	if err != nil {
		return err
	}
	report := classifyAll(commits, settings.Rules, settings.Range, *offline)
	if !*offline {
		// PR provenance is verified against live state when it can be: the trailer is
		// written by `merge`, but a hand-written one is exactly the forgery an offline
		// check cannot see. A failure here is operational and aborts, rather than
		// silently degrading to the offline answer under a name that promised more.
		if err := verifyPullRequests(ctx, env, *repoFlag, report); err != nil {
			return err
		}
	}

	if err := write(report, mode, env); err != nil {
		return err
	}
	if report.Counts.Unadmitted > 0 {
		return fmt.Errorf("%d of %d commits on %s are not admitted by any class",
			report.Counts.Unadmitted, report.Commits, settings.Range.Branch)
	}
	return nil
}

// settings is the resolved configuration for one run: which range, under which rules.
type settings struct {
	Range Range
	Rules Rules
}

// loadSettings resolves flags against the rendered policy.
//
// An explicit flag always wins, and the policy supplies the rest. A run with neither a
// `--branch` nor an `integration_branch` is a usage error rather than a default to the
// checkout's current HEAD: classifying whatever branch happened to be checked out would
// report a verdict about a branch the caller never named.
func loadSettings(env *cli.Env, policyPath, branch, since string) (*settings, error) {
	resolved, err := resolvePolicy(env, policyPath)
	if err != nil {
		return nil, err
	}
	if branch == "" {
		branch = resolved.IntegrationBranch
	}
	if branch == "" {
		return nil, cli.Usagef("pass --branch, or set `integration_branch` in policy.toml")
	}
	if since == "" {
		since = resolved.AdmissionFloor
	}
	return &settings{
		Range: Range{Branch: branch, Since: since},
		Rules: Rules{
			HandoffEnabled:       resolved.HandoffAdmission != policy.HandoffAdmissionNone,
			ReleaseSubjectPrefix: resolved.ReleaseSubjectPrefix,
		},
	}, nil
}

// resolvePolicy loads the rendered policy, tolerating its absence.
//
// Unlike `audit`, this subcommand has a complete and correct behavior with no policy at
// all: the four options all default, and `--branch` can supply the only value that has
// no default. Requiring the file would make the classifier unusable in exactly the
// place it is most useful — a fresh checkout, or a repository mid-adoption.
func resolvePolicy(env *cli.Env, explicit string) (*policy.Policy, error) {
	path := explicit
	if path == "" {
		found, err := cli.ResolveRepoFile(env.WorkDir, cli.DefaultPolicyPath)
		if err != nil {
			return &policy.Policy{HandoffAdmission: policy.HandoffAdmissionDefault}, nil
		}
		path = found
	}
	return policy.Load(path)
}

func classifyAll(commits []Commit, rules Rules, rng Range, offline bool) *Report {
	report := &Report{
		Branch:   rng.Branch,
		Since:    rng.Since,
		Offline:  offline,
		Commits:  len(commits),
		Findings: make([]Finding, 0, len(commits)),
	}
	for _, commit := range commits {
		finding := Classify(commit, rules)
		report.Findings = append(report.Findings, finding)
		switch {
		case !finding.Admitted():
			report.Counts.Unadmitted++
		case finding.Class == ClassT0:
			report.Counts.T0++
		case finding.Class == ClassPullRequest:
			report.Counts.PullRequest++
		case finding.Class == ClassHandoff:
			report.Counts.Handoff++
		case finding.Class == ClassRelease:
			report.Counts.Release++
		}
	}
	return report
}

// verifyPullRequests turns each distinct `PR #N` trailer into a live check.
//
// Distinct numbers are queried once each, not once per commit: a squashed pull request
// contributes one commit, but a rebase or a cherry-pick can spread the same trailer
// across many, and re-asking GitHub per commit would turn a large range into a rate
// limit. A number that is not a merged pull request in this repository demotes every
// commit that cited it, because the trailer's whole value is that it is checkable.
func verifyPullRequests(ctx context.Context, env *cli.Env, repoFlag string, report *Report) error {
	numbers := map[int]bool{}
	for _, finding := range report.Findings {
		if finding.Class == ClassPullRequest && finding.Admitted() {
			numbers[finding.PullRequest] = false
		}
	}
	if len(numbers) == 0 {
		return nil
	}
	repo, err := resolveRepository(env.WorkDir, repoFlag)
	if err != nil {
		return err
	}
	client, err := env.Client(ctx)
	if err != nil {
		return err
	}
	for _, number := range sortedKeys(numbers) {
		pr, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
		if err != nil {
			return err
		}
		numbers[number] = pr.IsMerged()
	}
	for i, finding := range report.Findings {
		if finding.Class != ClassPullRequest || !finding.Admitted() || numbers[finding.PullRequest] {
			continue
		}
		report.Findings[i].Class = ClassUnadmitted
		report.Findings[i].Code = CodePullRequestState
		report.Findings[i].Message = fmt.Sprintf(
			"the trailer cites pull request #%d, which is not merged in %s", finding.PullRequest, repo)
		report.Findings[i].Remediation = "Correct the trailer to the pull request that actually admitted this commit."
		report.Counts.PullRequest--
		report.Counts.Unadmitted++
	}
	return nil
}

// resolveRepository honors an explicit --repo and otherwise reads this checkout's
// origin, which is the same precedence every other subcommand applies.
func resolveRepository(workDir, explicit string) (render.Repository, error) {
	if explicit != "" {
		return render.ParseRepository(explicit)
	}
	return render.OriginRepository(workDir)
}

func sortedKeys(values map[int]bool) []int {
	keys := make([]int, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Ints(keys)
	return keys
}

func write(report *Report, mode cli.OutputMode, env *cli.Env) error {
	var rendered []byte
	if mode == cli.OutputJSON {
		marshalled, err := cli.MarshalJSON(report)
		if err != nil {
			return err
		}
		rendered = marshalled
	} else {
		rendered = []byte(renderHuman(report))
	}
	if _, err := env.Stdout.Write(rendered); err != nil {
		return fmt.Errorf("writing the admission report: %w", err)
	}
	return nil
}

// renderHuman prints only the unadmitted commits plus the census.
//
// Listing every admitted commit would bury the finding set under hundreds of lines in
// exactly the case the report matters — a first run over an unenforced history — so the
// admitted commits are represented by their counts.
func renderHuman(report *Report) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Branch:  %s\n", report.Branch)
	if report.Since != "" {
		fmt.Fprintf(&b, "Since:   %s (exclusive)\n", report.Since)
	}
	fmt.Fprintf(&b, "Commits: %d\n", report.Commits)

	unadmitted := 0
	for _, finding := range report.Findings {
		if finding.Admitted() {
			continue
		}
		if unadmitted == 0 {
			b.WriteString("\nUnadmitted commits\n")
		}
		unadmitted++
		fmt.Fprintf(&b, "  %s %s\n    %s — %s\n    %s\n",
			shortSHA(finding.SHA), finding.Subject, finding.Code, finding.Message, finding.Remediation)
	}

	fmt.Fprintf(&b, "\nSummary: %d T0, %d pull request, %d handoff, %d release, %d unadmitted\n",
		report.Counts.T0, report.Counts.PullRequest, report.Counts.Handoff,
		report.Counts.Release, report.Counts.Unadmitted)
	if report.Counts.Unadmitted == 0 {
		b.WriteString("Every commit in the range is admitted by a declared class.\n")
	}
	return b.String()
}

func shortSHA(sha string) string {
	const short = 8
	if len(sha) <= short {
		return sha
	}
	return sha[:short]
}
