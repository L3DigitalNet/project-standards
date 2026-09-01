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
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/safetext"
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
	Branch  string `json:"branch"`
	Since   string `json:"since,omitempty"`
	Offline bool   `json:"offline"`
	Commits int    `json:"commits"`
	// Excluded is how many commits the floor kept out of the range. It is reported
	// alongside Commits so the scope of the exemption the floor grants is visible in
	// the evidence rather than left to be inferred.
	Excluded int       `json:"excluded"`
	Counts   Counts    `json:"counts"`
	Findings []Finding `json:"findings"`
}

// Counts is the per-class census. It is reported even on a clean run because the shape
// of a repository's admissions is the evidence that the check is not vacuous. An
// all-zero census can no longer accompany a zero exit — an empty range is refused with
// CodeEmptyRange — but the census still shows a reader *what* was attested.
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
	// The floor is validated before the history is read, so an unrelated floor is
	// reported as the configuration error it is rather than as a surprising range.
	excluded, err := ExcludedByFloor(ctx, env.WorkDir, settings.Range)
	if err != nil {
		return err
	}
	commits, err := ReadCommits(ctx, env.WorkDir, settings.Range)
	if err != nil {
		return err
	}
	report := classifyAll(commits, settings.Rules, settings.Range, *offline)
	report.Excluded = excluded
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
	if report.Commits == 0 {
		return fmt.Errorf("%s: the range %s resolves to zero commits, so this run attests nothing",
			CodeEmptyRange, settings.Range.spec())
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
	if len(commits) == 0 {
		// An empty range is the vacuous pass this whole subcommand exists to expose: a
		// typo in `--branch`, a floor that is already the branch tip, or a `--since`
		// swallowed as a pathspec all produce "0 commits, 0 unadmitted", which reads as
		// compliance. The finding carries no SHA because it is about the range itself.
		report.Findings = append(report.Findings, Finding{
			Subject: rng.spec(),
			Class:   ClassUnadmitted,
			Code:    CodeEmptyRange,
			Message: "the range resolves to zero commits, so this run attests nothing",
			Remediation: "Check the branch and the enforcement floor: a range that selects no commits " +
				"cannot demonstrate that the admission rule holds.",
		})
		report.Counts.Unadmitted++
		return report
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
// Distinct numbers are queried once each, not once per commit: a rebase or a cherry-pick
// can spread the same trailer across many commits, and re-asking GitHub per commit would
// turn a large range into a rate limit.
//
// The check is SHA equality, not merely "pull request N is merged". A trailer is only
// evidence about the commit `merge --pr N` actually created, so an authenticated run
// requires the cited pull request's own merge commit to *be* this commit. Without that
// binding, one genuinely merged pull request would admit every commit that names it —
// which is precisely what an author who writes their own trailer is reaching for.
func verifyPullRequests(ctx context.Context, env *cli.Env, repoFlag string, report *Report) error {
	numbers := map[int]string{}
	for _, finding := range report.Findings {
		if finding.Class == ClassPullRequest && finding.Admitted() {
			numbers[finding.PullRequest] = ""
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
		if pr.IsMerged() {
			numbers[number] = pr.MergeCommitSHA
		}
	}
	for i, finding := range report.Findings {
		if finding.Class != ClassPullRequest || !finding.Admitted() {
			continue
		}
		merged := numbers[finding.PullRequest]
		if merged != "" && merged == finding.SHA {
			continue
		}
		message := fmt.Sprintf(
			"the trailer cites pull request #%d, which is not merged in %s", finding.PullRequest, repo)
		if merged != "" {
			message = fmt.Sprintf(
				"the trailer cites pull request #%d, whose merge commit is %s, not this commit",
				finding.PullRequest, shortSHA(merged))
		}
		report.Findings[i].Class = ClassUnadmitted
		report.Findings[i].Code = CodePullRequestState
		report.Findings[i].Message = message
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

func sortedKeys(values map[int]string) []int {
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
		fmt.Fprintf(&b, "Since:   %s (exclusive; %d commits excluded)\n", report.Since, report.Excluded)
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
		if finding.SHA == "" {
			// A range-level finding (CodeEmptyRange) has no commit to identify, so the
			// SHA/subject line would render as leading whitespace.
			fmt.Fprintf(&b, "  %s — %s\n    %s\n", finding.Code,
				safetext.SanitizeText(finding.Message), finding.Remediation)
			continue
		}
		// The subject and the message carry commit text this tool did not author: any
		// author who can land a commit in the classified range controls them, and a
		// subject carrying ESC or a bidi override would repaint the operator's terminal
		// from inside the report that is supposed to expose it. Encoded at the point of
		// printing, which is where the untrusted bytes leave the tool.
		fmt.Fprintf(&b, "  %s %s\n    %s — %s\n    %s\n",
			shortSHA(finding.SHA), safetext.SanitizeText(finding.Subject), finding.Code,
			safetext.SanitizeText(finding.Message), finding.Remediation)
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
