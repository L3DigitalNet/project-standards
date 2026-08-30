package ghapi

// The pull-request surface the 1.7 paired commands need: the reads that populate the
// relationship engine's topology, and the four mutations `ready`, `merge`, and `close --pr`
// perform (spec FR-032, FR-033, FR-034).
//
// Every method here returns plain typed structs. Assembling them into the engine's
// topology is the command layer's job, deliberately: the engine is pure and must not learn
// about HTTP, and this package must not learn about findings.
//
// Which calls are GraphQL and why is documented in graphql.go; the rest is REST.

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"time"
)

// Comment is one issue or pull-request conversation comment.
type Comment struct {
	Author    string    `json:"-"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"created_at"`
	User      struct {
		Login string `json:"login"`
	} `json:"user"`
}

// AuthorLogin returns the comment author's login, reading through the nested `user` object
// GitHub actually sends. The flat Author member exists for callers constructing fixtures.
func (c Comment) AuthorLogin() string {
	if c.Author != "" {
		return c.Author
	}
	return c.User.Login
}

// PullRequestMergeState carries the two PullRequest facts REST does not expose.
//
// MergeStateStatus is GitHub's own summary of whether protection would presently allow the
// merge (BLOCKED, BEHIND, CLEAN, DIRTY, UNSTABLE, DRAFT, HAS_HOOKS, UNKNOWN); ReviewDecision
// is APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, or empty when the repository requires no
// review. Empty means "GitHub reported nothing", never a satisfied condition — the Merge
// phase treats unknown evidence as a finding (ERR-013), not as a pass.
type PullRequestMergeState struct {
	NodeID           string
	MergeStateStatus string
	ReviewDecision   string
}

const mergeStateQuery = `query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    pullRequest(number:$number){ id mergeStateStatus reviewDecision }
  }
}`

// GetPullRequestMergeState performs the one GraphQL read that completes a PR's Merge-phase
// evidence. Combined with GetPullRequest it is two calls for one pull request.
func (c *Client) GetPullRequestMergeState(ctx context.Context, owner, repo string, number int,
) (*PullRequestMergeState, error) {
	if err := ValidateRepository(owner, repo); err != nil {
		return nil, err
	}
	var data struct {
		Repository struct {
			PullRequest struct {
				ID               string `json:"id"`
				MergeStateStatus string `json:"mergeStateStatus"`
				ReviewDecision   string `json:"reviewDecision"`
			} `json:"pullRequest"`
		} `json:"repository"`
	}
	if err := c.graphql(ctx, mergeStateQuery, map[string]any{
		"owner": owner, "name": repo, "number": number,
	}, &data); err != nil {
		return nil, err
	}
	pr := data.Repository.PullRequest
	return &PullRequestMergeState{
		NodeID:           pr.ID,
		MergeStateStatus: pr.MergeStateStatus,
		ReviewDecision:   pr.ReviewDecision,
	}, nil
}

// ListIssueComments returns every comment on an issue or pull request, across every page.
//
// The issues endpoint is correct for both: GitHub stores a PR's conversation comments as
// issue comments, and the pulls comments endpoint returns review comments on diff lines
// instead — a different collection that would never contain the `Final-Disposition:` record
// FR-034 writes and Post-merge disposition looks for.
func (c *Client) ListIssueComments(ctx context.Context, owner, repo string, number int) ([]Comment, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	return getPaged[Comment](ctx, c, fmt.Sprintf("%s/issues/%d/comments", base, number), url.Values{})
}

// CreateComment posts one comment on an issue or pull request.
//
// FR-034 requires the disposition record to exist before the PR is closed, so this call is
// ordered first in that sequence: a comment written after a failed close is recoverable
// evidence, while a close without the record leaves a terminal PR whose disposition no
// later read can reconstruct.
func (c *Client) CreateComment(ctx context.Context, owner, repo string, number int, body string,
) (*Comment, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	if body == "" {
		return nil, fmt.Errorf("no comment body to post on %s/%s#%d", owner, repo, number)
	}
	payload := struct {
		Body string `json:"body"`
	}{Body: body}

	var created Comment
	if err := c.send(ctx, http.MethodPost,
		fmt.Sprintf("%s/issues/%d/comments", base, number), payload, &created); err != nil {
		return nil, err
	}
	return &created, nil
}

const markReadyMutation = `mutation($id:ID!){
  markPullRequestReadyForReview(input:{pullRequestId:$id}){ pullRequest{ id isDraft } }
}`

// MarkPullRequestReady clears a pull request's draft state (GraphQL; REST cannot).
//
// It is idempotent in the sense the paired `ready` command needs: GitHub accepts the
// mutation on an already-ready PR, so a resumed run after a partial failure converges
// rather than refusing.
func (c *Client) MarkPullRequestReady(ctx context.Context, nodeID string) error {
	if nodeID == "" {
		return fmt.Errorf("no pull-request node id to mark ready")
	}
	return c.graphql(ctx, markReadyMutation, map[string]any{"id": nodeID}, nil)
}

const enableAutoMergeMutation = `mutation($id:ID!,$method:PullRequestMergeMethod!){
  enablePullRequestAutoMerge(input:{pullRequestId:$id,mergeMethod:$method}){
    pullRequest{ id autoMergeRequest{ mergeMethod } }
  }
}`

// EnableAutoMerge arms auto-merge with the given method (GraphQL; REST cannot).
//
// Arming auto-merge hands the outcome to GitHub, which is why FR-033 keeps observation
// responsibility with the caller: this call succeeding means the request was accepted, not
// that the pull request merged.
func (c *Client) EnableAutoMerge(ctx context.Context, nodeID, method string) error {
	if nodeID == "" {
		return fmt.Errorf("no pull-request node id to enable auto-merge on")
	}
	enum, err := graphqlMergeMethod(method)
	if err != nil {
		return err
	}
	return c.graphql(ctx, enableAutoMergeMutation,
		map[string]any{"id": nodeID, "method": enum}, nil)
}

// MergeResult is GitHub's answer to a merge request.
type MergeResult struct {
	SHA     string `json:"sha"`
	Merged  bool   `json:"merged"`
	Message string `json:"message"`
}

// MergePullRequest admits a pull request (REST PUT .../pulls/{n}/merge).
//
// headSHA is sent as `sha` and is not optional in practice: it makes the merge conditional
// on the branch head the caller validated. Without it, a push landing between validation
// and admission would be merged as though it had passed the Merge phase — the exact race
// the paired command exists to close. A mismatch comes back as 409, which the caller
// resolves by revalidating rather than retrying.
func (c *Client) MergePullRequest(ctx context.Context, owner, repo string, number int,
	method, headSHA string,
) (*MergeResult, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	switch method {
	case MergeMethodMerge, MergeMethodSquash, MergeMethodRebase:
	default:
		return nil, fmt.Errorf("merge method %q is not one of merge, squash, rebase", method)
	}
	payload := struct {
		MergeMethod string `json:"merge_method"`
		SHA         string `json:"sha,omitempty"`
	}{MergeMethod: method, SHA: headSHA}

	var result MergeResult
	if err := c.send(ctx, http.MethodPut,
		fmt.Sprintf("%s/pulls/%d/merge", base, number), payload, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// RepositoryMergeSettings is which merge methods the repository permits.
//
// Known distinguishes "the repository said so" from "we could not ask". FR-033's fallback
// preference order picks the first *live-permitted* method, so a caller that read Known
// false must not fall back to a method the repository may forbid.
type RepositoryMergeSettings struct {
	AllowSquash         bool `json:"allow_squash_merge"`
	AllowRebase         bool `json:"allow_rebase_merge"`
	AllowMerge          bool `json:"allow_merge_commit"`
	DeleteBranchOnMerge bool `json:"delete_branch_on_merge"`
	Known               bool `json:"-"`
}

// GetRepositoryMergeSettings reads the repository's permitted merge methods.
func (c *Client) GetRepositoryMergeSettings(ctx context.Context, owner, repo string,
) (*RepositoryMergeSettings, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	settings, err := getObject[RepositoryMergeSettings](ctx, c, base)
	if err != nil {
		return nil, err
	}
	settings.Known = true
	return settings, nil
}

// BranchEnforcement is what the repository currently enforces on a branch.
//
// Known is the load-bearing member. Absent protection and unreadable protection are
// different answers to the Merge phase: the first permits admission, the second is
// evidence-unknown and fails closed (ERR-013). A 404 from either endpoint means the
// resource does not exist — no ruleset, no classic protection — and is therefore knowledge.
// A 403, a 5xx, or a transport failure is not, and returns Known false rather than an
// empty enforcement set that would read identically to "nothing is enforced".
type BranchEnforcement struct {
	Known                bool
	RequiredStatusChecks []string
	RequiresReview       bool
	// Source names where the evidence came from — "rules", "protection", "rules+protection",
	// or "none" — so a finding can say which authority it read.
	Source string
}

// branchRule is one entry of the rules endpoint's flat array of active rules.
type branchRule struct {
	Type       string `json:"type"`
	Parameters struct {
		RequiredStatusChecks []struct {
			Context string `json:"context"`
		} `json:"required_status_checks"`
		RequiredApprovingReviewCount int `json:"required_approving_review_count"`
	} `json:"parameters"`
}

// branchProtection is the classic branch-protection response.
type branchProtection struct {
	RequiredStatusChecks *struct {
		Contexts []string `json:"contexts"`
	} `json:"required_status_checks"`
	RequiredPullRequestReviews *struct {
		RequiredApprovingReviewCount int `json:"required_approving_review_count"`
	} `json:"required_pull_request_reviews"`
}

// GetBranchEnforcement reads both enforcement authorities for a branch and merges them.
//
// Both are read because either can exist alone: rulesets are the current mechanism and
// classic protection is still live on older repositories, and a repository may carry both
// with different required checks. Requirements are unioned rather than preferred, because
// a merge must satisfy every authority that applies, not the one this client happened to
// consult first.
func (c *Client) GetBranchEnforcement(ctx context.Context, owner, repo, branch string,
) (*BranchEnforcement, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	if branch == "" {
		return nil, fmt.Errorf("no branch to read enforcement for in %s/%s", owner, repo)
	}
	escaped := url.PathEscape(branch)
	evidence := &BranchEnforcement{Known: true}
	sources := make([]string, 0, 2)

	rules, err := getPaged[branchRule](ctx, c,
		fmt.Sprintf("%s/rules/branches/%s", base, escaped), url.Values{})
	switch {
	case err != nil && !isNotFound(err):
		return &BranchEnforcement{Known: false}, nil
	case err == nil && len(rules) > 0:
		sources = append(sources, "rules")
		for _, rule := range rules {
			for _, check := range rule.Parameters.RequiredStatusChecks {
				evidence.RequiredStatusChecks = append(evidence.RequiredStatusChecks, check.Context)
			}
			if rule.Type == "pull_request" && rule.Parameters.RequiredApprovingReviewCount > 0 {
				evidence.RequiresReview = true
			}
		}
	}

	protection, err := getObject[branchProtection](ctx, c,
		fmt.Sprintf("%s/branches/%s/protection", base, escaped))
	switch {
	case err != nil && !isNotFound(err):
		return &BranchEnforcement{Known: false}, nil
	case err == nil:
		sources = append(sources, "protection")
		if protection.RequiredStatusChecks != nil {
			evidence.RequiredStatusChecks = append(evidence.RequiredStatusChecks,
				protection.RequiredStatusChecks.Contexts...)
		}
		if protection.RequiredPullRequestReviews != nil &&
			protection.RequiredPullRequestReviews.RequiredApprovingReviewCount > 0 {
			evidence.RequiresReview = true
		}
	}

	evidence.Source = "none"
	if len(sources) > 0 {
		evidence.Source = joinSources(sources)
	}
	return evidence, nil
}

func joinSources(sources []string) string {
	out := sources[0]
	for _, source := range sources[1:] {
		out += "+" + source
	}
	return out
}
