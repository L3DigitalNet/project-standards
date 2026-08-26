package mutate

import (
	"context"
	"flag"
	"fmt"
	"strconv"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// The Ready precondition classes of spec FR-023, in report order. Every class appears in
// every report whether met or not: a report that listed only failures would be
// indistinguishable from one where a class was never evaluated.
const (
	classPinnedFields = "pinned-fields"
	classAcceptance   = "acceptance-criteria"
	classDependencies = "blocking-dependencies"
	classSize         = "size"
)

// Finding statuses.
const (
	statusOK      = "ok"
	statusBlocked = "blocked"
)

// sizeTooLarge is the Size value that prohibits direct implementation: XL work is
// decomposed, never dispatched, so it can never be Ready.
const sizeTooLarge = "XL"

// Finding is one precondition class and its verdict.
type Finding struct {
	Class  string `json:"class"`
	Status string `json:"status"`
	Detail string `json:"detail"`
}

// CheckReport is the machine-readable form of a readiness check.
type CheckReport struct {
	Repository string    `json:"repository"`
	Issue      int       `json:"issue"`
	Title      string    `json:"title"`
	URL        string    `json:"url"`
	Type       string    `json:"type"`
	Eligible   bool      `json:"eligible"`
	Findings   []Finding `json:"findings"`
}

func runCheck(ctx context.Context, env *cli.Env, args []string) error {
	fs := flag.NewFlagSet("check", flag.ContinueOnError)
	tgt := addTargetFlags(fs, false)
	issue := fs.Int("issue", 0, "issue number to check")
	output := fs.String("output", string(cli.OutputHuman), "output format: human or json")
	if err := parse(fs, env, args, "Usage: gh-workflow check --issue N [flags]\n\n"+
		"Verifies the preconditions an issue must satisfy to be Ready and itemizes every\n"+
		"one. Read-only: it mutates nothing. Exits zero when the issue is eligible and\n"+
		"nonzero when any precondition is unmet.\n"); err != nil {
		return err
	}
	mode, err := cli.ParseOutputMode(*output)
	if err != nil {
		return cli.Usagef("%v", err)
	}
	if err := requireIssue(*issue); err != nil {
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
	report, err := inspect(ctx, client, repo, *issue)
	if err != nil {
		return err
	}
	if err := emit(env, mode, func() string { return renderCheck(report) }, report); err != nil {
		return err
	}

	if !report.Eligible {
		// The check itself succeeded, so the report is owed and already written; the
		// nonzero exit is the eligibility verdict, not a precondition failure.
		return fmt.Errorf("%s#%d is not eligible for Ready: %s",
			report.Repository, report.Issue, strings.Join(unmetClasses(report), ", "))
	}
	return nil
}

// inspect gathers live state and derives every class verdict. Both reads finish before
// any verdict is formed, so a partial read produces no partial report.
func inspect(ctx context.Context, client *ghapi.Client, repo render.Repository, number int) (*CheckReport, error) {
	item, err := render.FetchIssue(ctx, client, repo, number)
	if err != nil {
		return nil, err
	}
	blockers, err := client.ListBlockingDependencies(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return nil, err
	}

	report := &CheckReport{
		Repository: repo.String(),
		Issue:      item.Number,
		Title:      item.Title,
		URL:        item.URL,
		Type:       item.Type,
		Findings: []Finding{
			pinnedFieldsFinding(item),
			acceptanceFinding(item),
			dependenciesFinding(blockers),
			sizeFinding(item),
		},
	}
	report.Eligible = len(unmetClasses(report)) == 0
	return report, nil
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
// render engine because the summary and receipt report the same gaps; readiness is the
// same question asked as a gate rather than as a report.
func pinnedFieldsFinding(item render.WorkItem) Finding {
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
	if len(missing) > 0 {
		return Finding{Class: classPinnedFields, Status: statusBlocked,
			Detail: fmt.Sprintf("missing %s (of the %d fields %s pins that Ready requires)",
				strings.Join(missing, ", "), len(required), typeLabel(item.Type))}
	}
	return Finding{Class: classPinnedFields, Status: statusOK,
		Detail: fmt.Sprintf("all %d fields %s pins that Ready requires carry values",
			len(required), typeLabel(item.Type))}
}

func acceptanceFinding(item render.WorkItem) Finding {
	if !item.HasAcceptanceCriteria {
		return Finding{Class: classAcceptance, Status: statusBlocked,
			Detail: "the body has no populated acceptance criteria section; the honest " +
				"Workflow value for work without them is Needs definition"}
	}
	return Finding{Class: classAcceptance, Status: statusOK,
		Detail: "the body carries a populated acceptance criteria section"}
}

// dependenciesFinding counts only open blockers: a dependency that is already closed no
// longer blocks anything, and reporting it would make readiness unreachable.
func dependenciesFinding(blockers []ghapi.Issue) Finding {
	var open []string
	for _, blocker := range blockers {
		if blocker.State == stateOpen {
			open = append(open, "#"+strconv.Itoa(blocker.Number))
		}
	}
	if len(open) > 0 {
		return Finding{Class: classDependencies, Status: statusBlocked,
			Detail: fmt.Sprintf("blocked by %s, still open", strings.Join(open, ", "))}
	}
	return Finding{Class: classDependencies, Status: statusOK, Detail: "no open blocking dependencies"}
}

func sizeFinding(item render.WorkItem) Finding {
	if item.Field(render.FieldSize) == sizeTooLarge {
		return Finding{Class: classSize, Status: statusBlocked,
			Detail: "Size is XL, which prohibits direct implementation; decompose into sub-issues"}
	}
	return Finding{Class: classSize, Status: statusOK, Detail: "Size does not prohibit direct implementation"}
}

func unmetClasses(report *CheckReport) []string {
	var unmet []string
	for _, finding := range report.Findings {
		if finding.Status == statusBlocked {
			unmet = append(unmet, finding.Class)
		}
	}
	return unmet
}

func renderCheck(report *CheckReport) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s#%d — %s\n%s\nType: %s\n\n",
		report.Repository, report.Issue, report.Title, report.URL, orNone(report.Type))
	for _, finding := range report.Findings {
		fmt.Fprintf(&b, "  %-8s %-22s %s\n", finding.Status, finding.Class, finding.Detail)
	}
	if report.Eligible {
		b.WriteString("\nReady preconditions met. Admitting the issue to the executable queue remains your decision.\n")
	} else {
		unmet := unmetClasses(report)
		fmt.Fprintf(&b, "\nNot eligible for Ready: %d of %d preconditions unmet (%s).\n",
			len(unmet), len(report.Findings), strings.Join(unmet, ", "))
	}
	return b.String()
}

func typeLabel(issueType string) string {
	if issueType == "" {
		return "an issue with no Type"
	}
	return issueType
}

func orNone(value string) string {
	if value == "" {
		return "(none)"
	}
	return value
}
