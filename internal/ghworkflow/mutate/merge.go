package mutate

// `gh-workflow merge --pr N` (spec FR-033): validated pull-request admission and the Final
// Issue convergence it authorizes.
//
// Two rules shape everything here. Admission fails closed — every unknown in the Merge
// evidence is a finding, never a pass (ERR-013), and the engine has already turned
// unreadable enforcement or unreadable merge settings into blocking findings before the
// first write. And nothing after admission is ever rolled back (EC-012): once the merge
// lands, a failed Issue convergence is reported as the divergence it is and retried by
// rerunning, because reverting admitted repository content to tidy a field would destroy
// work to fix a label.

import (
	"context"
	"flag"
	"fmt"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/admission"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The ordered boundaries of the Merge operation. Admission and auto-merge arming are
// alternatives, so exactly one of them is ever more than `skipped`.
const (
	stepMerge           = "merge"
	stepEnableAutoMerge = "enable-auto-merge"
	stepObserveTerminal = "observe-terminal-state"
	stepConvergeIssue   = "converge-governing-issue"
)

// mergePreference is FR-033's fixed fallback order. It is an operational default, not a
// repository configuration field: the first live-permitted method wins, so a repository
// that forbids squashing gets a rebase without anyone configuring anything.
var mergePreference = []string{ghapi.MergeMethodSquash, ghapi.MergeMethodRebase, ghapi.MergeMethodMerge}

func runMerge(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("merge", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	number := fs.Int("pr", 0, "pull request number to admit")
	method := fs.String("method", "", "merge method: merge, squash, or rebase "+
		"(default: the first of squash, rebase, merge the repository permits)")
	auto := fs.Bool("auto", false, "enable auto-merge instead of merging now; "+
		"observation of the terminal outcome remains the caller's responsibility")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow merge --pr N [--method METHOD] [--auto] [flags]\n\n"+
		"Freshly evaluates the Merge gate, admits the pull request with a live-permitted\n"+
		"method, observes the terminal outcome, and converges a Final PR's governing issue\n"+
		"through the same `close --issue N --as done` sequence. Unknown enforcement or\n"+
		"unknown merge settings fail closed; nothing is rolled back after admission.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if *number <= 0 {
		return cli.Usagef("pass --pr with a positive pull request number")
	}
	if *method != "" {
		switch *method {
		case ghapi.MergeMethodMerge, ghapi.MergeMethodSquash, ghapi.MergeMethodRebase:
		default:
			return cli.Usagef("merge method %q is not one of %s, %s, %s",
				*method, ghapi.MergeMethodMerge, ghapi.MergeMethodSquash, ghapi.MergeMethodRebase)
		}
	}

	schema, err := tgt.loadSchema(env)
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

	gate, err := loadPRGate(ctx, client, repo, schema, *number, relation.PhaseMerge)
	if err != nil {
		return err
	}
	rec := newSteps(stepMerge, stepEnableAutoMerge, stepObserveTerminal, stepConvergeIssue)
	envelope := cli.NewEnvelope("merge", cli.ResultClear, prTarget(repo, *number, gate.PR.HTMLURL))
	envelope.Gate = cli.Gate(relation.PhaseMerge)
	envelope.Findings = gate.Result.Findings

	if !gate.Result.Clear() {
		envelope.Result = cli.ResultDomainFinding
		envelope.Steps = rec.list()
		if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
			return writeErr
		}
		return domainf("%s#%d does not pass the Merge gate: %d finding(s), and nothing was written",
			repo, *number, len(gate.Result.Findings))
	}

	selected, findings := selectMergeMethod(*method, gate.Topology.MergeSettings, *number)
	if len(findings) > 0 {
		envelope.Findings = append(envelope.Findings, findings...)
		envelope.Result = cli.ResultDomainFinding
		envelope.Steps = rec.list()
		if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
			return writeErr
		}
		return domainf("%s#%d: no usable merge method, and nothing was written", repo, *number)
	}

	stepErr := mergeSteps(ctx, client, gate, selected, *auto, rec, &envelope)
	envelope.Steps = rec.list()
	switch {
	case stepErr != nil:
		envelope.Result = cli.Classify(stepErr)
	case len(envelope.Findings) > 0:
		envelope.Result = cli.ResultDomainFinding
	}
	if writeErr := cli.WriteEnvelope(envelope, mode, env); writeErr != nil {
		return writeErr
	}
	switch {
	case stepErr != nil:
		return stepErr
	case envelope.Result == cli.ResultDomainFinding:
		return domainf("%s#%d: admission did not reach a known merged outcome", repo, *number)
	}
	return nil
}

// selectMergeMethod resolves the method to admit with.
//
// FR-033 names three tiers: an explicit `--method`, current repository instructions, and
// the fixed preference order. The middle tier is deliberately absent: version 1.7 changes
// no consumer configuration keys (FR-035), so neither the rendered `policy.toml` nor the
// managed instruction block carries a merge-method declaration, and there is no mechanism
// in this codebase for a repository to select one. Inventing a key here would create the
// per-repository configuration the requirement explicitly refuses.
//
// An explicit method the repository forbids is a domain finding rather than a usage error:
// the invocation is well formed and the refusal comes from live repository state, which is
// exactly the distinction between exit 2 and exit 1.
func selectMergeMethod(explicit string, settings relation.RepositoryMergeSettings, number int,
) (string, []relation.Finding) {
	permitted := map[string]bool{
		ghapi.MergeMethodSquash: settings.AllowSquash,
		ghapi.MergeMethodRebase: settings.AllowRebase,
		ghapi.MergeMethodMerge:  settings.AllowMerge,
	}
	if explicit != "" {
		if permitted[explicit] {
			return explicit, nil
		}
		return "", []relation.Finding{{
			Code: "GHW-PR-MERGE-METHOD-NOT-PERMITTED", Phase: relation.PhaseMerge,
			Category: relation.CategoryAdmissionBlocked, Effect: relation.EffectBlocksMerge,
			Kind: relation.KindPullRequest, Number: number,
			Message:     fmt.Sprintf("the repository does not currently permit the requested %q merge method", explicit),
			Remediation: "Choose a method the repository permits, or omit --method to take the first permitted of squash, rebase, merge.",
		}}
	}
	for _, candidate := range mergePreference {
		if permitted[candidate] {
			return candidate, nil
		}
	}
	// The engine already reports GHW-PR-MERGE-NO-METHOD and GHW-PR-MERGE-SETTINGS-UNKNOWN,
	// so reaching here means the gate was clear and the settings still permit nothing —
	// a contradiction worth reporting rather than merging on a guessed method.
	return "", []relation.Finding{{
		Code: "GHW-PR-MERGE-NO-METHOD", Phase: relation.PhaseMerge,
		Category: relation.CategoryAdmissionBlocked, Effect: relation.EffectBlocksMerge,
		Kind: relation.KindPullRequest, Number: number,
		Message:     "the repository permits no merge method",
		Remediation: "Enable a merge method in the repository settings, or admit the change through the repository's authorized manual path.",
	}}
}

// mergeSteps performs admission, terminal observation, and Final convergence in order,
// recording each boundary.
func mergeSteps(ctx context.Context, client *ghapi.Client, gate *prGate, method string,
	auto bool, rec *steps, envelope *cli.Envelope,
) error {
	repo := render.Repository{Owner: gate.Owner, Name: gate.Name}
	number := gate.PR.Number

	switch {
	case gate.PR.IsMerged():
		// A rerun after a convergence failure re-enters here: the merge is history and the
		// remaining work is the Issue. Re-issuing the merge would answer 405 and tell the
		// operator the command failed when in fact it had already succeeded.
		rec.skip(stepMerge, "the pull request is already merged")
		rec.skip(stepEnableAutoMerge, "the pull request is already merged")
	case auto:
		rec.skip(stepMerge, "--auto arms GitHub's auto-merge instead of merging now")
		// The head SHA the gate validated is what auto-merge is armed against, so a push
		// landing while GitHub holds the request cannot be merged as though it had passed.
		if err := client.EnableAutoMerge(ctx, gate.NodeID, method, gate.PR.Head.SHA); err != nil {
			rec.fail(stepEnableAutoMerge, "auto-merge was not armed; the pull request is unchanged")
			return err
		}
		rec.complete(stepEnableAutoMerge, "auto-merge armed with the "+method+" method")
	default:
		rec.skip(stepEnableAutoMerge, "--auto was not requested")
		title, message := admissionCommitText(gate.PR.Title, number)
		result, err := client.MergePullRequest(ctx, repo.Owner, repo.Name, number, method,
			gate.PR.Head.SHA, title, message)
		if err != nil {
			rec.fail(stepMerge, "the pull request was not merged; the governing issue is untouched")
			return err
		}
		if !result.Merged {
			rec.fail(stepMerge, "GitHub accepted the request without merging: "+result.Message)
			return domainf("%s#%d: GitHub did not merge the pull request: %s", repo, number, result.Message)
		}
		rec.complete(stepMerge, "merged with the "+method+" method")
	}

	// The merge call's own answer is not the terminal outcome: with `--auto` GitHub owns
	// the outcome entirely, and even a direct merge is re-observed so convergence is
	// authorized by observed state rather than by the request that asked for it.
	after, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		rec.fail(stepObserveTerminal, "the terminal outcome could not be observed")
		return err
	}
	if !after.IsMerged() {
		rec.fail(stepObserveTerminal, "the pull request has not reached a merged outcome")
		envelope.Findings = append(envelope.Findings, autoMergePendingFinding(number, method, auto))
		return nil
	}
	rec.complete(stepObserveTerminal, "GitHub reports the pull request merged")

	if gate.Decl.Relationship != relation.RelationshipFinal {
		// FR-029: Supporting and Standalone admission is lifecycle-neutral and never
		// authorizes Done, so this route must not touch an Issue it merely references.
		rec.skip(stepConvergeIssue, "only a Final PR authorizes issue completion")
		return nil
	}
	if gate.GoverningIssue() == 0 {
		rec.skip(stepConvergeIssue, "no governing issue resolved")
		return nil
	}
	move := transition{
		state: stateClosed, reason: "completed", workflow: relation.WorkflowDone,
		rerun: fmt.Sprintf("close --issue %d --as done", gate.GoverningIssue()),
	}
	// The convergence runs the identical sequence `close --issue N --as done` runs, as one
	// recorded step: FR-033 names those semantics, and a second implementation of the
	// terminal pairing would be free to diverge from the one FR-021 governs.
	outcome, err := converge(ctx, client, repo, gate.GoverningIssue(), move, nil)
	if err != nil {
		rec.fail(stepConvergeIssue, fmt.Sprintf(
			"the merge stands; issue #%d did not converge to %s and rerunning this command retries it",
			gate.GoverningIssue(), relation.WorkflowDone))
		return err
	}
	rec.complete(stepConvergeIssue, outcome.Message)
	return nil
}

// admissionCommitText builds the subject and body GitHub writes into the commit this
// command creates: the pull-request admission evidence of ADR 0031 D1.
//
// It is written here, by the tool that already owns merging, because a trailer an author
// has to remember is a trailer that is missing: the measured corpus behind ADR 0031 had
// 0 trailers across 362 commits. Writing it turns pull-request provenance into a fact
// `gh-workflow admission --offline` can read from `git log` with no API call.
//
// The body is tool-owned text and nothing else. GitHub's own default body is composed
// from the pull request — author-controlled — so echoing it would let an author write
// `Workflow-Admission: PR #999` into the commit the tool signs off on, or end the body
// with prose so the real trailer is no longer in a trailer paragraph and the classifier
// reads no declaration at all. The subject is the only author text that survives, and it
// is sanitized: a title carrying CR, ESC, or a bidi override reaches every terminal that
// later prints `git log`.
//
// Two limits travel with this. GitHub applies neither field to a rebase merge, so a
// rebase-admitted pull request contributes commits with no trailer. And the body
// replaces GitHub's default squash body — the list of squashed commit subjects — which
// the pull request itself still records.
func admissionCommitText(prTitle string, number int) (title, message string) {
	subject := sanitizeSubject(prTitle)
	if subject == "" {
		subject = fmt.Sprintf("Merge pull request #%d", number)
	} else {
		subject = fmt.Sprintf("%s (#%d)", subject, number)
	}
	// A leading blank line makes the trailer its own final paragraph even in GitHub's
	// rendering, which is the shape `git interpret-trailers` and the classifier both
	// require; without it a one-line body can be folded onto the subject.
	return subject, fmt.Sprintf("\n%s: PR #%d\n", admission.TrailerKey, number)
}

// sanitizeSubject reduces an author-supplied pull-request title to one safe line.
//
// Removed rather than escaped: C0 and C7 controls (CR and LF would split the subject
// into forged extra lines, ESC drives a terminal), and the Unicode bidi overrides and
// isolates, which can reorder a rendered subject so it reads as something other than
// what was committed. Whitespace is then collapsed so the removals cannot leave a
// subject that looks padded or empty-but-present.
func sanitizeSubject(value string) string {
	cleaned := strings.Map(func(r rune) rune {
		switch {
		case r == '\t', r == '\n', r == '\r':
			// Whitespace, not deletion: dropping a newline outright would join the two
			// words either side of it into one token that was never written.
			return ' '
		case r < 0x20 || r == 0x7f:
			return -1
		case r >= 0x200e && r <= 0x200f, r >= 0x202a && r <= 0x202e, r >= 0x2066 && r <= 0x2069:
			return -1
		default:
			return r
		}
	}, value)
	return strings.Join(strings.Fields(cleaned), " ")
}

// autoMergePendingFinding reports an admission that has not reached a terminal outcome.
//
// It exists because FR-033 forbids reporting a dispatch as success: arming auto-merge
// means GitHub will merge later or not at all, and the caller retains the responsibility
// to observe which. The nonzero domain result is the machine-readable half of that
// statement.
func autoMergePendingFinding(number int, method string, auto bool) relation.Finding {
	message := "the pull request is not merged after the admission request"
	remediation := "Rerun `gh-workflow merge --pr N` once GitHub reports the outcome."
	if auto {
		message = fmt.Sprintf("auto-merge is armed with the %s method and the pull request is not merged yet", method)
		remediation = "Observation is not delegated: watch the pull request and rerun `gh-workflow merge --pr N` " +
			"once it merges, so the governing issue converges."
	}
	return relation.Finding{
		Code: "GHW-PR-MERGE-OUTCOME-PENDING", Phase: relation.PhaseMerge,
		Category: relation.CategorySynchronizationRequired, Effect: relation.EffectRequiresSynchronization,
		Kind: relation.KindPullRequest, Number: number,
		Message: message, Remediation: remediation,
	}
}
