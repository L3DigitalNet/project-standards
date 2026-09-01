// Package topology is the one place a live pull request becomes the pure engine's
// relation.Topology: a phase-bounded set of GitHub reads, the two normalizations the
// engine cannot perform for itself, and the engine's verdict over the result.
//
// It exists as its own package because five surfaces need the same snapshot — `check`,
// `ready`, `merge`, and `close --pr` gate on it, while `summary` and `receipt` project
// it (FR-022). Assembling it twice is how the renderers and the gates start disagreeing
// about what GitHub said, which is the failure FR-030's single engine is meant to make
// impossible.
//
// The read set is phase-driven rather than fixed. Every caller asks for the gate it
// needs and Load issues only the calls that gate's predicates can consult, which keeps
// the NFR-008 round-trip bound a property of this code rather than of each caller's
// discipline: a Structural check never reads branch protection, and a Ready check never
// reads check runs.
//
// The division of labour with internal/ghworkflow/relation is absolute. Nothing here
// decides whether state is acceptable — it reports what GitHub said, normalizes the two
// facts the engine cannot establish for itself (a recognized ordinary Issue Type, and
// the sibling open Finals no single PR body can show), and hands the snapshot over.
//
// Dependency direction: this package must never import internal/ghworkflow/render.
// render imports it (summary and receipt are built on Load), so an import back would be
// a cycle. That is why the repository is passed as owner and name strings and why the
// two Issue Field names below are declared here rather than reused from render.
package topology

import (
	"context"
	"errors"
	"net/http"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// The two Issue Field names and the date layout this package reads.
//
// Cross-file contract: these must stay byte-identical to render.FieldWorkflow,
// render.FieldTargetDate, and render.DateLayout, which are map keys against live API
// values rather than labels. The duplication buys the one-way dependency described in
// the package comment; topology_test.go pins the equality so a rename in either place
// fails a test instead of silently producing an Issue with no Workflow.
const (
	fieldWorkflow   = "Workflow"
	fieldTargetDate = "Target date"
	dateLayout      = "2006-01-02"
)

// stateOpen is GitHub's own spelling of an open issue's state, which the open-issue memo
// filters on.
const stateOpen = "open"

// Gate is one loaded pull request: the live objects, the assembled topology, and the
// engine's verdict over it.
type Gate struct {
	Owner string
	Name  string
	PR    *ghapi.PullRequest
	// NodeID is the GraphQL node identifier of the pull request, which the auto-merge
	// and mark-ready mutations address it by. It is read here because the same GraphQL
	// call already supplies mergeStateStatus.
	NodeID string
	// Issue is the live governing Issue, nil when the PR declares none or the declared
	// number does not resolve. Callers that write Issue state must branch on nil rather
	// than on the declaration alone.
	Issue    *ghapi.Issue
	Decl     relation.Declaration
	Topology relation.Topology
	Result   relation.Result
}

// GoverningIssue returns the governing Issue's number when one resolved, else 0.
func (g *Gate) GoverningIssue() int {
	if g.Issue == nil {
		return 0
	}
	return g.Issue.Number
}

// Workflow returns the governing Issue's current Workflow value, "" when unset or when
// no Issue resolved.
func (g *Gate) Workflow() string {
	if g.Topology.GoverningIssue == nil {
		return ""
	}
	return g.Topology.GoverningIssue.Workflow
}

// Prefetched memoizes the live reads a single command shares across many gate loads, so
// a command that loads N gates issues each shared read once instead of N times (NFR-008:
// "shared live reads are reused within one command").
//
// Every field is unexported and reached through one accessor that reads on first use and
// records the answer, so a value can never claim a read that did not happen. That is the
// whole safety argument: an earlier design exported the fields and treated a non-nil
// struct as the assertion that every read it named had been performed, which meant a
// caller holding only some of the reads had to pass nil or silently answer the
// one-open-Final rule from an empty list. Seeding is therefore explicit — the two Seed
// methods below record a read the caller genuinely performed — and everything unseeded is
// simply read on demand.
//
// A Prefetched is valid only for the repository and the moment it was built against:
// handing one to a load against another repository would answer cardinality, lifecycle,
// and CI questions from the wrong corpus. It carries no synchronization, because the
// commands that use it are sequential by construction.
type Prefetched struct {
	// openPullRequests is the complete `state=open` pull-request list for this repository,
	// bodies included — the one-open-Final cardinality rule (FR-027) is answered from it.
	openPullRequests     []ghapi.PullRequest
	openPullRequestsRead bool
	// openIssues indexes the repository's open issues by number. GetIssue is served from it
	// for a number it holds; a closed or absent issue falls through to the API, without
	// which a Final governed by a closed issue would read as unresolved and raise
	// GHW-PR-STRUCTURAL-ISSUE-UNRESOLVED against an issue that exists.
	openIssues     map[int]ghapi.Issue
	openIssuesRead bool
	// checkRuns holds the check runs already read, keyed by the commit SHA they were read
	// for. Presence of a key means the read happened; a present-but-empty entry means the
	// commit genuinely has no check runs, which is a different fact from "not read yet".
	checkRuns map[string][]ghapi.CheckRun
	// mergeSettings is repository-level and therefore identical for every gate in one
	// command; non-nil means it was read.
	mergeSettings *ghapi.RepositoryMergeSettings
	// enforcement is branch-level, keyed by base ref: two pull requests targeting the same
	// branch share one answer, two targeting different branches do not.
	enforcement map[string]ghapi.BranchEnforcement
}

// NewPrefetched returns an empty memo. Every read it is asked for happens on first use.
func NewPrefetched() *Prefetched { return &Prefetched{} }

// SeedOpenPullRequests records the `state=open` list the caller already read.
func (p *Prefetched) SeedOpenPullRequests(pulls []ghapi.PullRequest) {
	p.openPullRequests, p.openPullRequestsRead = pulls, true
}

// SeedOpenIssues records the open-issue list the caller already read.
//
// Only open issues belong here: the index is consulted as "this number is open and here
// it is", and seeding a closed issue would let a stale open-state projection satisfy a
// lifecycle predicate that must see the closure.
func (p *Prefetched) SeedOpenIssues(issues []ghapi.Issue) {
	index := make(map[int]ghapi.Issue, len(issues))
	for _, issue := range issues {
		if issue.State == stateOpen {
			index[issue.Number] = issue
		}
	}
	p.openIssues, p.openIssuesRead = index, true
}

// CIState summarizes the CI verdict for a commit, retaining the check runs it read in pre.
//
// This exists so the summary's two consumers of one commit's check runs — the rendered CI
// column and the Merge gate's required-check predicate — cost one read instead of two
// (NFR-008). The verdict itself is not reimplemented: ghapi.SummarizeCheckRuns is the
// single authority, and this function only decides which reads go out.
//
// With no pre there is nothing to reuse, so it delegates to ghapi's own CIState rather than
// running a second copy of the two-surface fallback. That keeps the unshared path — every
// `receipt --pr` — on exactly the code it has always run.
func CIState(ctx context.Context, client *ghapi.Client, owner, name, ref string,
	pre *Prefetched,
) (string, error) {
	if pre == nil {
		return client.CIState(ctx, owner, name, ref)
	}
	runs, err := checkRuns(ctx, client, owner, name, ref, pre)
	if err != nil {
		return ghapi.CIUnknown, err
	}
	if len(runs) > 0 {
		return ghapi.SummarizeCheckRuns(runs), nil
	}

	// Zero check runs is not "no CI": an Actions-only repository reports no commit
	// statuses and a repository driven by external services reports no check runs, so the
	// other surface has to be asked before the answer is unknown. Cross-file contract:
	// this branch mirrors the second half of ghapi.Client.CIState — change either and
	// update both, or the summary and the receipt start disagreeing about one commit.
	status, err := client.GetCombinedStatus(ctx, owner, name, ref)
	switch {
	case err != nil && notFound(err):
		return ghapi.CIUnknown, nil
	case err != nil:
		return ghapi.CIUnknown, err
	case status.TotalCount == 0:
		return ghapi.CIUnknown, nil
	}
	switch status.State {
	case "success":
		return ghapi.CIPassing, nil
	case "pending":
		return ghapi.CIPending, nil
	default:
		return ghapi.CIFailing, nil
	}
}

// checkRuns returns one commit's check runs, reading them at most once per Prefetched.
//
// A 404 is recorded as an empty result rather than propagated: no check-runs resource for
// a commit is knowledge, and both consumers already treat it as "no observed run". Caching
// it matters as much as caching a hit — otherwise a commit GitHub 404s costs one read per
// consumer for an answer that will never change within the command.
func checkRuns(ctx context.Context, client *ghapi.Client, owner, name, ref string,
	pre *Prefetched,
) ([]ghapi.CheckRun, error) {
	if pre != nil {
		if cached, read := pre.checkRuns[ref]; read {
			return cached, nil
		}
	}
	runs, err := client.ListCheckRunsForRef(ctx, owner, name, ref)
	switch {
	case err != nil && notFound(err):
		runs = nil
	case err != nil:
		return nil, err
	}
	if pre != nil {
		if pre.checkRuns == nil {
			pre.checkRuns = map[string][]ghapi.CheckRun{}
		}
		pre.checkRuns[ref] = runs
	}
	return runs, nil
}

// Load performs the phase-bounded read set and evaluates the gate, issuing every read
// itself. See LoadWith for the variant a multi-gate command uses.
func Load(ctx context.Context, client *ghapi.Client, owner, name string,
	schema *orgschema.Schema, number int, through relation.Phase,
) (*Gate, error) {
	return LoadWith(ctx, client, owner, name, schema, number, through, nil)
}

// LoadWith performs the phase-bounded read set and evaluates the gate, reusing whatever
// pre already holds.
//
// through may be empty, in which case the gate is inferred from observed state
// (FR-031). The clock is read once and injected, so every date-sensitive predicate in
// one run answers from the same instant.
//
// pre changes which calls go out, never which phases are loaded or what the engine is
// handed: a reused list must be the same list the unshared path would have read, so the
// verdict is identical either way. render's summary goldens are the equivalence check —
// they are asserted against the same expected findings on both paths, and
// TestSummaryReusesSharedReadsWithinOneCommand pins the call count that proves the reuse
// actually happened rather than being silently skipped.
func LoadWith(ctx context.Context, client *ghapi.Client, owner, name string,
	schema *orgschema.Schema, number int, through relation.Phase, pre *Prefetched,
) (*Gate, error) {
	pr, err := client.GetPullRequest(ctx, owner, name, number)
	if err != nil {
		return nil, err
	}
	mergeState, err := client.GetPullRequestMergeState(ctx, owner, name, number)
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
	g := &Gate{Owner: owner, Name: name, PR: pr, NodeID: mergeState.NodeID, Decl: decl}
	topology := relation.Topology{PullRequest: observed, Now: time.Now().UTC()}

	if decl.Relationship.Governed() && decl.IssueNumber > 0 {
		issue, err := governingIssue(ctx, client, owner, name, decl.IssueNumber, pre)
		switch {
		case err != nil && !notFound(err):
			return nil, err
		case err == nil:
			g.Issue = issue
			topology.GoverningIssue = GoverningIssue(*issue, schema)
		}
	}

	// The one-open-Final rule is cardinality across pull requests, so it costs a list read
	// — and only where it can bind. A terminal PR's relationship is immutable evidence
	// (EC-014), so competing Finals can no longer be resolved by editing it, and the read
	// would buy a finding nobody can act on.
	if decl.Relationship == relation.RelationshipFinal && !observed.Terminal() {
		open, err := openPullRequests(ctx, client, owner, name, pre)
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
		if err := loadMergeEvidence(ctx, client, owner, name, &topology, pre); err != nil {
			return nil, err
		}
	}
	if gate == relation.PhasePostMerge {
		comments, err := client.ListIssueComments(ctx, owner, name, number)
		if err != nil {
			return nil, err
		}
		// The actor is resolved before the evidence is handed to the engine, and its
		// absence fails the read rather than degrading: the engine trusts no author it was
		// not given, so continuing here would silently evaluate the disposition predicate
		// with every comment discarded and report a missing record that exists.
		actor, err := client.AuthenticatedLogin(ctx)
		if err != nil {
			return nil, err
		}
		topology.TrustedAuthors = []string{actor}
		for _, comment := range comments {
			topology.PullRequest.Comments = append(topology.PullRequest.Comments, relation.Comment{
				Author: comment.AuthorLogin(), Body: comment.Body, CreatedAt: comment.CreatedAt,
			})
		}
	}

	g.Topology = topology
	g.Result = relation.Evaluate(topology, gate)
	return g, nil
}

// openPullRequests returns the repository's open pull requests, reading them at most once
// per Prefetched.
func openPullRequests(ctx context.Context, client *ghapi.Client, owner, name string,
	pre *Prefetched,
) ([]ghapi.PullRequest, error) {
	if pre != nil && pre.openPullRequestsRead {
		return pre.openPullRequests, nil
	}
	pulls, err := client.ListOpenPullRequests(ctx, owner, name)
	if err != nil {
		return nil, err
	}
	if pre != nil {
		pre.SeedOpenPullRequests(pulls)
	}
	return pulls, nil
}

// governingIssue reads one issue, serving it from the open-issue index when that index
// holds it.
//
// The fall-through is the load-bearing half. A pull request may declare an issue that is
// closed, that belongs to no open queue, or that does not exist at all, and only the API
// can distinguish those; answering "absent from the open list" as "no such issue" would
// report a Final governed by a closed issue as unresolved. The index is therefore a
// positive cache only, never a negative one.
func governingIssue(ctx context.Context, client *ghapi.Client, owner, name string,
	number int, pre *Prefetched,
) (*ghapi.Issue, error) {
	if pre != nil && pre.openIssuesRead {
		if issue, open := pre.openIssues[number]; open {
			return &issue, nil
		}
	}
	return client.GetIssue(ctx, owner, name, number)
}

// mergeSettings reads the repository's permitted merge methods at most once per
// Prefetched. The answer is repository-level, so every gate in one command shares it.
func mergeSettings(ctx context.Context, client *ghapi.Client, owner, name string,
	pre *Prefetched,
) (*ghapi.RepositoryMergeSettings, error) {
	if pre != nil && pre.mergeSettings != nil {
		return pre.mergeSettings, nil
	}
	settings, err := client.GetRepositoryMergeSettings(ctx, owner, name)
	if err != nil {
		return nil, err
	}
	if pre != nil {
		pre.mergeSettings = settings
	}
	return settings, nil
}

// branchEnforcement reads one base branch's live enforcement at most once per Prefetched.
//
// Keyed by ref rather than cached as a single value: a command may load gates against
// different base branches, and answering a feature branch's admission from `main`'s
// rulesets would report enforcement the pull request is not actually subject to.
func branchEnforcement(ctx context.Context, client *ghapi.Client, owner, name, ref string,
	pre *Prefetched,
) (ghapi.BranchEnforcement, error) {
	if pre != nil {
		if cached, read := pre.enforcement[ref]; read {
			return cached, nil
		}
	}
	evidence, err := client.GetBranchEnforcement(ctx, owner, name, ref)
	if err != nil {
		return ghapi.BranchEnforcement{}, err
	}
	if pre != nil {
		if pre.enforcement == nil {
			pre.enforcement = map[string]ghapi.BranchEnforcement{}
		}
		pre.enforcement[ref] = *evidence
	}
	return *evidence, nil
}

// loadMergeEvidence adds the live admission evidence: what the repository permits, what
// the base branch enforces, and which required checks actually ran on this head.
//
// A failed read is propagated as an operational failure rather than folded into
// Known=false. ERR-013's fail-closed rule covers evidence that an *otherwise successful*
// read could not establish; reporting a transport failure as a domain finding would tell
// the operator the PR is unmergeable when the truth is that nothing was learned.
//
// The two branch- and repository-level reads are memoized in pre when one was supplied:
// the permitted merge methods are a property of the repository and the enforcement of the
// base branch, so a summary loading many pull requests learned the identical answer once
// per pull request before this (NFR-008). The verdict is unchanged either way — the memo
// returns the same bytes the read would have.
func loadMergeEvidence(ctx context.Context, client *ghapi.Client, owner, name string,
	topology *relation.Topology, pre *Prefetched,
) error {
	settings, err := mergeSettings(ctx, client, owner, name, pre)
	if err != nil {
		return err
	}
	topology.MergeSettings = relation.RepositoryMergeSettings{
		AllowSquash: settings.AllowSquash, AllowRebase: settings.AllowRebase,
		AllowMerge: settings.AllowMerge, Known: settings.Known,
	}

	enforcement, err := branchEnforcement(ctx, client, owner, name, topology.PullRequest.BaseRef, pre)
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
	// The check runs are taken from the shared read when one happened. The rendered CI
	// column and this required-check predicate consume the same commit's runs, so without
	// the reuse every ready open pull request in a summary paid for the identical list
	// twice (NFR-008). checkRuns already folds a 404 into an empty result, which is
	// knowledge rather than a failed read: the predicate reports each enforced name as
	// having no observed run.
	runs, err := checkRuns(ctx, client, owner, name, topology.PullRequest.HeadSHA, pre)
	if err != nil {
		return err
	}
	for _, run := range runs {
		topology.PullRequest.RequiredChecks = append(topology.PullRequest.RequiredChecks,
			relation.CheckState{Name: run.Name, Status: run.Status, Conclusion: run.Conclusion})
	}
	return nil
}

// GoverningIssue projects a live Issue into the engine's view, resolving the one fact the
// pure engine cannot: whether the Issue's live type is a recognized ordinary work type.
//
// The schema is the sole authority (FR-023) and it lives in a file the engine never
// reads, so an unrecognized or absent type is normalized to "" here. That is not a
// cosmetic default — the engine reads "" as "no usable type" and raises
// GHW-ISSUE-STRUCTURAL-TYPE-MISSING, so passing a live type name through unchecked would
// let a type the organization retired silently satisfy the predicate.
func GoverningIssue(issue ghapi.Issue, schema *orgschema.Schema) *relation.Issue {
	projected := &relation.Issue{
		Number:              issue.Number,
		State:               issue.State,
		StateReason:         issue.StateReason,
		IssueType:           RecognizedIssueType(issueTypeName(&issue), schema),
		IsPullRequestShaped: issue.IsPullRequest(),
	}
	for _, value := range issue.FieldValues {
		switch value.Name {
		case fieldWorkflow:
			projected.Workflow = value.Display()
		case fieldTargetDate:
			if parsed, err := time.Parse(dateLayout, value.Display()); err == nil {
				projected.TargetDate = &parsed
			}
		}
	}
	return projected
}

// RecognizedIssueType returns name when the baseline schema declares it an ordinary work
// type, and "" otherwise.
func RecognizedIssueType(name string, schema *orgschema.Schema) string {
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

// issueTypeName is the type GitHub reports, or "" for an issue carrying none.
func issueTypeName(issue *ghapi.Issue) string {
	if issue == nil || issue.Type == nil {
		return ""
	}
	return issue.Type.Name
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
