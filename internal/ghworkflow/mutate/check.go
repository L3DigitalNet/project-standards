package mutate

// `gh-workflow check` (spec FR-023, FR-031): the gate. It decides, where `receipt`
// describes and `summary` aggregates, and it is the only one of the three whose exit code
// is a verdict rather than a report of successful rendering.
//
// Exactly one of `--issue N` and `--pr N` is required, because the two routes answer
// different questions against different authorities. The Issue route asks whether an
// issue may be admitted to `Ready`: a recognized ordinary Issue Type, native open state, a
// nonterminal lifecycle-coherent `Workflow`, and the four content preconditions. The PR
// route hands the pull request to the shared relationship engine at the gate its observed
// state implies, or at the `--through` phase the caller named.
//
// All four IR-005 result classes are reachable here and they are not interchangeable:
// clear (0), domain findings (1), a malformed invocation or local refusal (2), and an
// authentication, API, or transport failure that produced no verdict at all (3). The whole
// point of the last one is that a gate which cannot be evaluated must never read as clear.

import (
	"context"
	"flag"
	"fmt"
	"strconv"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The Ready precondition classes of spec FR-023. Each finding message opens with its
// class, which is the operator-facing name the reference documentation and the 1.6 report
// both used; the DR-004 `code` is the machine-readable identity.
const (
	classPinnedFields = "pinned-fields"
	classAcceptance   = "acceptance-criteria"
	classDependencies = "blocking-dependencies"
	classSize         = "size"
	classIssueType    = "issue-type"
	classNativeState  = "native-state"
	classWorkflow     = "workflow"
)

// sizeTooLarge is the Size value that prohibits direct implementation: XL work is
// decomposed, never dispatched, so it can never be Ready.
const sizeTooLarge = "XL"

func runCheck(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("check", flag.ContinueOnError)
	tgt := addTargetFlags(fs, true)
	issue := fs.Int("issue", 0, "issue number to check for Ready eligibility")
	pull := fs.Int("pr", 0, "pull request number to check against the relationship engine")
	through := fs.String("through", "", "evaluate a pull request through this phase: "+
		"structural, ready, merge, or post-merge (default: the phase its observed state implies)")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow check --issue N [flags]\n"+
		"       gh-workflow check --pr N [--through PHASE] [flags]\n\n"+
		"Read-only: it mutates nothing. Exits 0 when the gate is clear, 1 when validation\n"+
		"completed with findings, 2 for a malformed invocation, and 3 when authentication,\n"+
		"the API, or transport prevented a verdict.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	switch {
	case *issue > 0 && *pull > 0:
		return cli.Usagef("--issue and --pr are mutually exclusive; pass exactly one")
	case *issue <= 0 && *pull <= 0:
		return cli.Usagef("pass exactly one of --issue N or --pr N")
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

	if *pull > 0 {
		return checkPullRequest(ctx, env, client, repo, schema, mode, *pull, *through)
	}
	// `--through` selects among the PR phases, and an Issue has none of them: accepting it
	// silently would let an automation believe it had requested a gate the Issue route
	// never evaluated.
	if *through != "" {
		return cli.Usagef("--through applies to --pr; the issue route has no phases")
	}
	return checkIssue(ctx, env, client, repo, schema, mode, *issue)
}

// checkPullRequest evaluates the relationship engine's gate.
func checkPullRequest(ctx context.Context, env *cli.Env, client *ghapi.Client,
	repo render.Repository, schema *orgschema.Schema, mode cli.OutputMode, number int, through string,
) error {
	var phase relation.Phase
	if through != "" {
		parsed, ok := relation.ParsePhase(through)
		if !ok {
			return cli.Usagef("unknown phase %q; --through takes %s, %s, %s, or %s",
				through, relation.PhaseStructural, relation.PhaseReady,
				relation.PhaseMerge, relation.PhasePostMerge)
		}
		phase = parsed
	}

	gate, err := loadPRGate(ctx, client, repo, schema, number, phase)
	if err != nil {
		return err
	}
	envelope := cli.NewEnvelope("check", cli.ResultClear, prTarget(repo, number, gate.PR.HTMLURL))
	envelope.Gate = cli.Gate(gate.Result.Gate)
	envelope.Findings = gate.Result.Findings
	if !gate.Result.Clear() {
		envelope.Result = cli.ResultDomainFinding
	}
	if err := cli.WriteEnvelope(envelope, mode, env); err != nil {
		return err
	}
	if envelope.Result == cli.ResultDomainFinding {
		// The gate ran and produced a verdict, so the report is owed and already written;
		// the nonzero exit is that verdict rather than a failure to reach one.
		return domainf("%s#%d does not pass the %s gate: %d finding(s)",
			repo, number, gate.Result.Gate, len(gate.Result.Findings))
	}
	return nil
}

// checkIssue evaluates the Ready preconditions of FR-023.
func checkIssue(ctx context.Context, env *cli.Env, client *ghapi.Client,
	repo render.Repository, schema *orgschema.Schema, mode cli.OutputMode, number int,
) error {
	// The shape read comes first and is its own call. The issues endpoint serves pull
	// requests too, so without this an Issue-only route silently reports on a PR that has
	// no Issue Type and no Issue Field values — every content class would read as missing
	// and the verdict would be about the wrong object entirely (DEV-023). The projection
	// render.FetchIssue returns does not carry the `pull_request` member, which is why the
	// object is read here rather than derived from it.
	raw, err := client.GetIssue(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return err
	}
	if raw.IsPullRequest() {
		return cli.Usagef("%s#%d is a pull request, not an issue; check it with `gh-workflow check --pr %d`",
			repo, number, number)
	}

	item, err := render.FetchIssue(ctx, client, repo, number)
	if err != nil {
		return err
	}
	blockers, err := client.ListBlockingDependencies(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return err
	}

	envelope := cli.NewEnvelope("check", cli.ResultClear,
		cli.Target{Kind: cli.TargetIssue, Number: number, Repository: repo.String(), URL: item.URL})
	envelope.Gate = cli.Gate(relation.PhaseReady)
	envelope.Findings = issueReadyFindings(item, blockers, schema, number)
	if len(envelope.Findings) > 0 {
		envelope.Result = cli.ResultDomainFinding
	}
	if err := cli.WriteEnvelope(envelope, mode, env); err != nil {
		return err
	}
	if envelope.Result == cli.ResultDomainFinding {
		return domainf("%s#%d is not eligible for Ready: %d unmet precondition(s)",
			repo, number, len(envelope.Findings))
	}
	return nil
}

// issueReadyFindings derives every unmet Ready precondition, in evaluation order.
//
// Only unmet classes produce findings. The 1.6 report itemized every class in both
// directions, which the DR-004 envelope has no member for: `findings` is what is wrong,
// and a passing class is the absence of a finding. The information the old "ok" lines
// carried survives as the verdict itself — a clear result means every class passed.
func issueReadyFindings(item render.WorkItem, blockers []ghapi.Issue,
	schema *orgschema.Schema, number int,
) []relation.Finding {
	findings := make([]relation.Finding, 0, 4)
	add := func(f relation.Finding) {
		f.Kind, f.Number = relation.KindIssue, number
		findings = append(findings, f)
	}

	if recognizedIssueType(item.Type, schema) == "" {
		add(relation.Finding{
			Code: "GHW-ISSUE-STRUCTURAL-TYPE-MISSING", Phase: relation.PhaseStructural,
			Category: relation.CategoryNeedsDefinition, Effect: relation.EffectBlocksReady,
			Message: fmt.Sprintf("%s: %s carries no recognized ordinary Issue Type", classIssueType,
				typeLabel(item.Type)),
			Remediation: fmt.Sprintf("Set one of %s with `gh-workflow set --issue N --type T`.",
				strings.Join(schema.IssueTypes, ", ")),
		})
	}
	if item.State != stateOpen {
		// A closed issue cannot be admitted to an executable queue, whatever its content
		// says: Ready is a statement about work that is about to start.
		add(relation.Finding{
			Code: "GHW-ISSUE-READY-NATIVE-STATE", Phase: relation.PhaseReady,
			Category: relation.CategorySynchronizationRequired, Effect: relation.EffectBlocksReady,
			Message: fmt.Sprintf("%s: the issue is %s, and only an open issue can be Ready",
				classNativeState, nativeState(item.State, item.StateReason)),
			Remediation: "Reopen it with `gh-workflow reopen --issue N --workflow VALUE` if the work is live.",
		})
	}
	if workflow := item.Field(render.FieldWorkflow); workflow == "" || isTerminalWorkflow(workflow) {
		// A terminal `Workflow` on an issue being gated for Ready is the divergence FR-021
		// keeps paired, and an unset one means the lifecycle authority has never spoken.
		add(relation.Finding{
			Code: "GHW-ISSUE-READY-WORKFLOW-INCOHERENT", Phase: relation.PhaseReady,
			Category: relation.CategorySynchronizationRequired, Effect: relation.EffectBlocksReady,
			Message: fmt.Sprintf("%s: Workflow is %s, which is not a nonterminal lifecycle-coherent value",
				classWorkflow, quotedOrUnset(workflow)),
			Remediation: "Set a nonterminal Workflow with `gh-workflow set --issue N --field Workflow=VALUE`.",
		})
	}

	if finding, ok := pinnedFieldsFinding(item); ok {
		add(finding)
	}
	if !item.HasAcceptanceCriteria {
		add(relation.Finding{
			Code: "GHW-ISSUE-READY-ACCEPTANCE-CRITERIA", Phase: relation.PhaseReady,
			Category: relation.CategoryNeedsDefinition, Effect: relation.EffectBlocksReady,
			Message: classAcceptance + ": the body has no populated acceptance criteria section",
			Remediation: "Write the acceptance criteria; the honest Workflow value for work without them " +
				"is Needs definition.",
		})
	}
	if finding, ok := dependenciesFinding(blockers); ok {
		add(finding)
	}
	if item.Field(render.FieldSize) == sizeTooLarge {
		add(relation.Finding{
			Code: "GHW-ISSUE-READY-SIZE", Phase: relation.PhaseReady,
			Category: relation.CategoryNeedsDefinition, Effect: relation.EffectBlocksReady,
			Message:     classSize + ": Size is XL, which prohibits direct implementation",
			Remediation: "Decompose the work into sub-issues that can be dispatched.",
		})
	}
	return findings
}

// isTerminalWorkflow reports whether a Workflow value is one of the terminal pair. It
// reads the same authority `set`, `close`, and `reopen` read, so the four subcommands
// cannot disagree about what "terminal" means.
func isTerminalWorkflow(value string) bool {
	_, terminal := terminalReason(value)
	return terminal
}

// readinessOptional names pinned fields whose emptiness does not block Ready.
//
// `Target date` is pinned to Feature, Task, and Initiative, but the package's own
// field-vocabulary reference has always said to set it "only when a date carries
// semantic meaning" and that empty is a valid, expected state. Through payload 1.4
// `check` disagreed with that sentence and refused readiness over an absent date, which
// sent agents around the gate — issue #192 was admitted with `set` after `check`
// refused it. Payload 1.5 makes the tool agree with the documented semantics.
//
// The exemption is a name here rather than a flag in the data because the pinning
// matrix has no machine-readable home: render's map is the matrix (see its comment),
// and neither org-schema.yaml nor policy.toml can express "pinned but optional for
// readiness". Only `check` consults this. Gaps() still reports an absent Target date on
// a Type that pins it, because a receipt reports what is missing rather than gating on
// it — and its output is a byte contract with 1.4 (spec FR-022).
var readinessOptional = map[string]bool{render.FieldTargetDate: true}

// pinnedFieldsFinding checks the fields this Issue Type pins. The matrix lives in the
// render engine because the summary and receipt report the same gaps, which is the one
// machine-readable pinning authority FR-023 requires check and receipts to share.
func pinnedFieldsFinding(item render.WorkItem) (relation.Finding, bool) {
	var required, missing []string
	for _, field := range render.PinnedFields(item.Type) {
		if readinessOptional[field] {
			continue
		}
		required = append(required, field)
		if item.Field(field) == "" {
			missing = append(missing, field)
		}
	}
	if len(missing) == 0 {
		return relation.Finding{}, false
	}
	return relation.Finding{
		Code: "GHW-ISSUE-READY-PINNED-FIELDS", Phase: relation.PhaseReady,
		Category: relation.CategoryNeedsDefinition, Effect: relation.EffectBlocksReady,
		Message: fmt.Sprintf("%s: missing %s (of the %d fields %s pins that Ready requires)",
			classPinnedFields, strings.Join(missing, ", "), len(required), typeLabel(item.Type)),
		Remediation: "Set the missing fields with `gh-workflow set --issue N --field Name=Value`.",
	}, true
}

// dependenciesFinding counts only open blockers: a dependency that is already closed no
// longer blocks anything, and reporting it would make readiness unreachable.
func dependenciesFinding(blockers []ghapi.Issue) (relation.Finding, bool) {
	var open []string
	for _, blocker := range blockers {
		if blocker.State == stateOpen {
			open = append(open, "#"+strconv.Itoa(blocker.Number))
		}
	}
	if len(open) == 0 {
		return relation.Finding{}, false
	}
	return relation.Finding{
		Code: "GHW-ISSUE-READY-BLOCKED-BY", Phase: relation.PhaseReady,
		Category: relation.CategoryBlocked, Effect: relation.EffectBlocksReady,
		Message:     fmt.Sprintf("%s: blocked by %s, still open", classDependencies, strings.Join(open, ", ")),
		Remediation: "Close or drop the blocking issues, or remove the dependency.",
	}, true
}

func typeLabel(issueType string) string {
	if issueType == "" {
		return "an issue with no Type"
	}
	return issueType
}
