package mutate

// The pull-request plumbing shared by `check --pr`, `ready`, `merge`, and `close --pr`:
// one bounded set of live reads assembled into the pure engine's topology, the DR-004
// envelope those routes emit, and the ordered-step record ERR-014 requires a partially
// applied paired operation to leave behind.
//
// The read set is phase-driven rather than fixed. Every route asks for the gate it needs
// and this file issues only the calls that gate's predicates can consult, which is what
// keeps the NFR-008 round-trip bound a property of the code rather than of the caller's
// discipline: a Structural check never reads branch protection, and a Ready check never
// reads check runs.
//
// The division of labour with internal/ghworkflow/relation is absolute. Nothing here
// decides whether state is acceptable — it reports what GitHub said, normalizes the two
// facts the engine cannot establish for itself (a recognized ordinary Issue Type, and the
// sibling open Finals no single PR body can show), and hands the snapshot over.

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// domainError is a completed evaluation that found something, which IR-005 classifies as
// `domain-finding` and exit 1.
//
// It is a distinct type rather than a bare fmt.Errorf only so the intent is greppable:
// cli.Classify already maps any unmarked error to the domain class, and the danger this
// names is the opposite direction — an operational failure that reaches Classify without
// its marker would be reported as a verdict the tool never actually reached.
type domainError struct{ message string }

func (e *domainError) Error() string { return e.message }

func domainf(format string, args ...any) error {
	return &domainError{message: fmt.Sprintf(format, args...)}
}

// notFound reports whether err is GitHub's 404. A declared governing Issue that does not
// exist is evidence the engine reports (GHW-PR-STRUCTURAL-ISSUE-UNRESOLVED), not a failed
// read: returning it as an error would exit 3 and hide the finding the operator needs.
func notFound(err error) bool {
	var apiErr *ghapi.APIError
	return errors.As(err, &apiErr) && apiErr.Status == http.StatusNotFound
}

// phaseRank is the position of p in the engine's cumulative phase order, or -1 for a
// value that is not a phase. The engine keeps its own rank private, so this is the local
// copy the read planner compares against; relation.PhaseOrder remains the single source
// of the order itself.
func phaseRank(p relation.Phase) int {
	for i, phase := range relation.PhaseOrder {
		if p == phase {
			return i
		}
	}
	return -1
}

// prGate is one loaded pull request: the live objects, the assembled topology, and the
// engine's verdict over it.
type prGate struct {
	repo   render.Repository
	pr     *ghapi.PullRequest
	nodeID string
	// issue is the live governing Issue, nil when the PR declares none or the declared
	// number does not resolve. Callers that write Issue state must branch on nil rather
	// than on the declaration alone.
	issue    *ghapi.Issue
	decl     relation.Declaration
	topology relation.Topology
	result   relation.Result
}

// governedIssue returns the governing Issue's number when one resolved, else 0.
func (g *prGate) governedIssue() int {
	if g.issue == nil {
		return 0
	}
	return g.issue.Number
}

// workflow returns the governing Issue's current Workflow value, "" when unset or when no
// Issue resolved.
func (g *prGate) workflow() string {
	if g.topology.GoverningIssue == nil {
		return ""
	}
	return g.topology.GoverningIssue.Workflow
}

// loadPRGate performs the phase-bounded read set and evaluates the gate.
//
// through may be empty, in which case the gate is inferred from observed state (FR-031).
// The clock is read once and injected, so every date-sensitive predicate in one run
// answers from the same instant.
func loadPRGate(ctx context.Context, client *ghapi.Client, repo render.Repository,
	schema *orgschema.Schema, number int, through relation.Phase,
) (*prGate, error) {
	pr, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return nil, err
	}
	mergeState, err := client.GetPullRequestMergeState(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return nil, err
	}

	autoEnabled, autoMethod := pr.AutoMergeEnabled()
	observed := relation.PullRequest{
		Number:           pr.Number,
		State:            pr.State,
		Draft:            pr.Draft,
		Merged:           pr.IsMerged(),
		MergedAt:         pr.MergedAt,
		ClosedAt:         pr.ClosedAt,
		Body:             pr.Body,
		Title:            pr.Title,
		BaseRef:          pr.Base.Ref,
		HeadRef:          pr.Head.Ref,
		HeadSHA:          pr.Head.SHA,
		AutoMergeEnabled: autoEnabled,
		AutoMergeMethod:  autoMethod,
		Mergeable:        pr.Mergeable,
		MergeStateStatus: mergeState.MergeStateStatus,
		ReviewDecision:   mergeState.ReviewDecision,
		Labels:           pr.LabelNames(),
	}

	gate := through
	if phaseRank(gate) < 0 {
		gate = relation.InferGate(observed)
	}
	decl, _ := relation.ParseBody(pr.Body)
	g := &prGate{repo: repo, pr: pr, nodeID: mergeState.NodeID, decl: decl}
	topology := relation.Topology{PullRequest: observed, Now: time.Now().UTC()}

	if decl.Relationship.Governed() && decl.IssueNumber > 0 {
		issue, err := client.GetIssue(ctx, repo.Owner, repo.Name, decl.IssueNumber)
		switch {
		case err != nil && !notFound(err):
			return nil, err
		case err == nil:
			g.issue = issue
			topology.GoverningIssue = governingIssue(*issue, schema)
		}
	}

	// The one-open-Final rule is cardinality across pull requests, so it costs a list read
	// — and only where it can bind. A terminal PR's relationship is immutable evidence
	// (EC-014), so competing Finals can no longer be resolved by editing it, and the read
	// would buy a finding nobody can act on.
	if decl.Relationship == relation.RelationshipFinal && !observed.Terminal() {
		open, err := client.ListOpenPullRequests(ctx, repo.Owner, repo.Name)
		if err != nil {
			return nil, err
		}
		for _, other := range open {
			if other.Number == number {
				continue
			}
			otherDecl, _ := relation.ParseBody(other.Body)
			if otherDecl.Relationship == relation.RelationshipFinal &&
				otherDecl.IssueNumber == decl.IssueNumber {
				topology.SiblingOpenFinals = append(topology.SiblingOpenFinals, other.Number)
			}
		}
	}

	if gate == relation.PhaseMerge {
		if err := loadMergeEvidence(ctx, client, repo, &topology); err != nil {
			return nil, err
		}
	}
	if gate == relation.PhasePostMerge {
		comments, err := client.ListIssueComments(ctx, repo.Owner, repo.Name, number)
		if err != nil {
			return nil, err
		}
		for _, comment := range comments {
			topology.PullRequest.Comments = append(topology.PullRequest.Comments, relation.Comment{
				Author: comment.AuthorLogin(), Body: comment.Body, CreatedAt: comment.CreatedAt,
			})
		}
	}

	g.topology = topology
	g.result = relation.Evaluate(topology, gate)
	return g, nil
}

// loadMergeEvidence adds the live admission evidence: what the repository permits, what
// the base branch enforces, and which required checks actually ran on this head.
//
// A failed read is propagated as an operational failure rather than folded into
// Known=false. ERR-013's fail-closed rule covers evidence that an *otherwise successful*
// read could not establish; reporting a transport failure as a domain finding would tell
// the operator the PR is unmergeable when the truth is that nothing was learned.
func loadMergeEvidence(ctx context.Context, client *ghapi.Client, repo render.Repository,
	topology *relation.Topology,
) error {
	settings, err := client.GetRepositoryMergeSettings(ctx, repo.Owner, repo.Name)
	if err != nil {
		return err
	}
	topology.MergeSettings = relation.RepositoryMergeSettings{
		AllowSquash: settings.AllowSquash, AllowRebase: settings.AllowRebase,
		AllowMerge: settings.AllowMerge, Known: settings.Known,
	}

	enforcement, err := client.GetBranchEnforcement(ctx, repo.Owner, repo.Name, topology.PullRequest.BaseRef)
	if err != nil {
		return err
	}
	topology.Enforcement = relation.EnforcementEvidence{
		Known: enforcement.Known, RequiredStatusChecks: enforcement.RequiredStatusChecks,
		RequiresReview: enforcement.RequiresReview, Source: enforcement.Source,
	}

	if topology.PullRequest.HeadSHA == "" {
		return nil
	}
	runs, err := client.ListCheckRunsForRef(ctx, repo.Owner, repo.Name, topology.PullRequest.HeadSHA)
	switch {
	case err != nil && notFound(err):
		// No check-runs resource for this commit is knowledge, not a failed read: the
		// required-check predicate reports each enforced name as having no observed run.
		return nil
	case err != nil:
		return err
	}
	for _, run := range runs {
		topology.PullRequest.RequiredChecks = append(topology.PullRequest.RequiredChecks,
			relation.CheckState{Name: run.Name, Status: run.Status, Conclusion: run.Conclusion})
	}
	return nil
}

// governingIssue projects a live Issue into the engine's view, resolving the one fact the
// pure engine cannot: whether the Issue's live type is a recognized ordinary work type.
//
// The schema is the sole authority (FR-023) and it lives in a file the engine never
// reads, so an unrecognized or absent type is normalized to "" here. That is not a
// cosmetic default — the engine reads "" as "no usable type" and raises
// GHW-ISSUE-STRUCTURAL-TYPE-MISSING, so passing a live type name through unchecked would
// let a type the organization retired silently satisfy the predicate.
func governingIssue(issue ghapi.Issue, schema *orgschema.Schema) *relation.Issue {
	projected := &relation.Issue{
		Number:              issue.Number,
		State:               issue.State,
		StateReason:         issue.StateReason,
		IssueType:           recognizedIssueType(issueTypeName(&issue), schema),
		IsPullRequestShaped: issue.IsPullRequest(),
	}
	for _, value := range issue.FieldValues {
		switch value.Name {
		case render.FieldWorkflow:
			projected.Workflow = value.Display()
		case render.FieldTargetDate:
			if parsed, err := time.Parse(render.DateLayout, value.Display()); err == nil {
				projected.TargetDate = &parsed
			}
		}
	}
	return projected
}

// recognizedIssueType returns name when the baseline schema declares it an ordinary work
// type, and "" otherwise.
func recognizedIssueType(name string, schema *orgschema.Schema) string {
	if name == "" || schema == nil {
		return ""
	}
	for _, candidate := range schema.IssueTypes {
		if candidate == name {
			return name
		}
	}
	return ""
}

// prTarget builds the envelope target for a pull-request route.
func prTarget(repo render.Repository, number int, url string) cli.Target {
	return cli.Target{Kind: cli.TargetPullRequest, Number: number, Repository: repo.String(), URL: url}
}

// steps records the ordered mutation boundaries of a paired command.
//
// The plan is declared up front and every unreached step stays `pending`, which is what
// makes a partially applied operation reportable rather than merely failed (ERR-014): the
// envelope states which writes provably landed and which provably did not, and the rerun
// that resumes reads the same statuses. A step recorded only when it runs would leave the
// steps after a failure absent, and absent reads as "not part of this operation".
type steps struct {
	order  []string
	status map[string]cli.Step
}

func newSteps(names ...string) *steps {
	s := &steps{order: names, status: make(map[string]cli.Step, len(names))}
	for _, name := range names {
		s.status[name] = cli.Step{Name: name, Status: cli.StepPending}
	}
	return s
}

// mark sets one declared step's outcome. Marking an undeclared step panics, because the
// step plan is the operation's contract with its own envelope and a typo would silently
// drop a boundary from the record.
//
// A nil recorder is a no-op, so a shared write path can be called both from a paired
// command that reports steps and from a 1.6 subcommand that does not.
func (s *steps) mark(name string, status cli.StepStatus, message string) {
	if s == nil {
		return
	}
	if _, declared := s.status[name]; !declared {
		panic("mutate: undeclared step " + name)
	}
	s.status[name] = cli.Step{Name: name, Status: status, Message: message}
}

func (s *steps) complete(name, message string) { s.mark(name, cli.StepCompleted, message) }
func (s *steps) skip(name, message string)     { s.mark(name, cli.StepSkipped, message) }
func (s *steps) fail(name, message string)     { s.mark(name, cli.StepFailed, message) }

// list returns the steps in declared order.
func (s *steps) list() []cli.Step {
	out := make([]cli.Step, 0, len(s.order))
	for _, name := range s.order {
		out = append(out, s.status[name])
	}
	return out
}

// applied reports whether any step actually wrote. It is what separates "nothing was
// attempted" from a partial application in the human summary a failing run returns.
func (s *steps) applied() bool {
	for _, step := range s.status {
		if step.Status == cli.StepCompleted {
			return true
		}
	}
	return false
}
