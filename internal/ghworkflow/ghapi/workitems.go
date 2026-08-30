package ghapi

// Repository-scoped work-item reads: the issues, pull requests, and CI state the
// rendering surfaces (spec FR-019, FR-022) present. It extends this package rather than
// standing up a second HTTP client so the two structural properties the package
// documentation states — scoped writes, and every request through the injected transport —
// keep holding for all of the tool's GitHub access. Every request built here is a GET;
// nothing in this file can mutate a repository, an issue, or organization schema.

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// IssueTypeRef is the Issue Type attached to one issue. It is the org-level IssueType
// seen from the issue side, where only the name is load-bearing for rendering.
type IssueTypeRef struct {
	Name string `json:"name"`
}

// IssueFieldOptionRef is a selected option of a single- or multi-select Issue Field.
type IssueFieldOptionRef struct {
	Name string `json:"name"`
}

// IssueFieldValue is one Issue Field value set on an issue. The API models `value` as a
// string, a number, or an array depending on the field's data type, so it is decoded
// lazily and rendered through Display rather than assumed to be a string.
type IssueFieldValue struct {
	Name               string                `json:"issue_field_name"`
	DataType           string                `json:"data_type"`
	Value              json.RawMessage       `json:"value"`
	SingleSelectOption *IssueFieldOptionRef  `json:"single_select_option"`
	MultiSelectOptions []IssueFieldOptionRef `json:"multi_select_options"`
}

// Display renders the value as the operator sees it in GitHub, preferring the resolved
// option name over the raw value so a renamed option cannot show a stale literal.
func (v IssueFieldValue) Display() string {
	if v.SingleSelectOption != nil && v.SingleSelectOption.Name != "" {
		return v.SingleSelectOption.Name
	}
	if len(v.MultiSelectOptions) > 0 {
		names := make([]string, 0, len(v.MultiSelectOptions))
		for _, option := range v.MultiSelectOptions {
			names = append(names, option.Name)
		}
		return strings.Join(names, ", ")
	}

	var text string
	if err := json.Unmarshal(v.Value, &text); err == nil {
		return strings.TrimSpace(text)
	}
	var number float64
	if err := json.Unmarshal(v.Value, &number); err == nil {
		return strconv.FormatFloat(number, 'f', -1, 64)
	}
	return ""
}

// Issue is one repository issue. The issues endpoint also returns pull requests, which
// carry a non-nil PullRequest and must be read through the pulls endpoint instead — they
// have no Issue Type or Issue Field values, and their draft and CI state live elsewhere.
type Issue struct {
	Number      int               `json:"number"`
	Title       string            `json:"title"`
	HTMLURL     string            `json:"html_url"`
	State       string            `json:"state"`
	StateReason string            `json:"state_reason"`
	Body        string            `json:"body"`
	Type        *IssueTypeRef     `json:"type"`
	FieldValues []IssueFieldValue `json:"issue_field_values"`
	PullRequest *struct {
		URL string `json:"url"`
	} `json:"pull_request"`
}

// IsPullRequest reports whether this entry is a pull request wearing an issue's shape.
func (i Issue) IsPullRequest() bool { return i.PullRequest != nil }

// PullRequest is one repository pull request as REST reports it.
//
// The 1.7 relationship engine consumes every member here, so the shape is the REST half of
// the topology contract rather than the rendering subset 1.6 needed. Two absences are
// deliberate: `mergeStateStatus` and `reviewDecision` have no REST representation at all
// and arrive through GetPullRequestMergeState, and no member here is derived — the client
// reports what GitHub said and the engine decides what it means.
type PullRequest struct {
	Number  int    `json:"number"`
	NodeID  string `json:"node_id"`
	Title   string `json:"title"`
	HTMLURL string `json:"html_url"`
	State   string `json:"state"`
	Draft   bool   `json:"draft"`
	Body    string `json:"body"`
	// Merged and MergedAt disagree on a closed-unmerged PR only in that MergedAt is null;
	// both are carried because the list endpoint omits `merged` while the single-PR
	// endpoint sets it, so a caller reading a list must fall back to MergedAt != nil.
	Merged   bool       `json:"merged"`
	MergedAt *time.Time `json:"merged_at"`
	ClosedAt *time.Time `json:"closed_at"`
	Base     GitRef     `json:"base"`
	Head     GitRef     `json:"head"`
	// Mergeable is a tri-state: GitHub computes it asynchronously and returns null while
	// the computation is pending. Nil means "not known yet", never "not mergeable" — a
	// caller that collapses the two admits a PR on evidence GitHub had not produced.
	Mergeable *bool `json:"mergeable"`
	// AutoMerge is non-nil exactly when auto-merge is enabled; its MergeMethod names the
	// method GitHub will use when the conditions clear.
	AutoMerge *AutoMergeRequest `json:"auto_merge"`
	Labels    []Label           `json:"labels"`
}

// GitRef is the branch end of a pull request.
type GitRef struct {
	Ref string `json:"ref"`
	SHA string `json:"sha"`
}

// AutoMergeRequest is GitHub's record of an enabled auto-merge.
type AutoMergeRequest struct {
	MergeMethod string `json:"merge_method"`
}

// Label is one label attached to a pull request or issue.
type Label struct {
	Name string `json:"name"`
}

// LabelNames returns the label names in response order.
func (p PullRequest) LabelNames() []string {
	names := make([]string, 0, len(p.Labels))
	for _, label := range p.Labels {
		names = append(names, label.Name)
	}
	return names
}

// AutoMergeEnabled reports whether auto-merge is armed, and with which method.
func (p PullRequest) AutoMergeEnabled() (bool, string) {
	if p.AutoMerge == nil {
		return false, ""
	}
	return true, p.AutoMerge.MergeMethod
}

// IsMerged reports whether the PR was merged, tolerating the list endpoint's omission of
// the `merged` member by treating a non-null `merged_at` as authoritative.
func (p PullRequest) IsMerged() bool { return p.Merged || p.MergedAt != nil }

// CI conclusions, normalized across the two independent GitHub surfaces that report
// them so callers never branch on which mechanism a repository happens to use.
const (
	CIPassing = "passing"
	CIFailing = "failing"
	CIPending = "pending"
	// CIUnknown is the honest answer when a commit carries neither check runs nor
	// commit statuses: "no CI reported", not "CI passed".
	CIUnknown = ""
)

// ListOpenIssues returns every open issue in the repository, pull requests excluded.
func (c *Client) ListOpenIssues(ctx context.Context, owner, repo string) ([]Issue, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	entries, err := getPaged[Issue](ctx, c, base+"/issues", url.Values{"state": {"open"}})
	if err != nil {
		return nil, err
	}
	issues := make([]Issue, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsPullRequest() {
			issues = append(issues, entry)
		}
	}
	return issues, nil
}

// GetIssue returns one issue by number.
//
// The issues endpoint also serves pull requests, so a caller on an Issue-only route must
// reject a response whose IsPullRequest reports true (spec IR-005, closing DEV-023); this
// method reports the shape rather than deciding the route.
func (c *Client) GetIssue(ctx context.Context, owner, repo string, number int) (*Issue, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	return getObject[Issue](ctx, c, fmt.Sprintf("%s/issues/%d", base, number))
}

// ListOpenPullRequests returns every open pull request in the repository, bodies included.
//
// The list response carries each PR's body, which is what lets the one-open-Final rule
// (FR-027) be answered from this single paginated read instead of one GetPullRequest per
// open PR — the round-trip discipline NFR-008 requires.
func (c *Client) ListOpenPullRequests(ctx context.Context, owner, repo string) ([]PullRequest, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	return getPaged[PullRequest](ctx, c, base+"/pulls", url.Values{"state": {"open"}})
}

// GetPullRequest returns one pull request by number.
//
// This is one REST call and it carries everything except mergeStateStatus and
// reviewDecision, which REST does not expose at all; GetPullRequestMergeState fetches
// those in one further GraphQL call. A complete Merge-phase read of one PR is therefore
// two calls, which is the number NFR-008's Merge bound is measured against.
func (c *Client) GetPullRequest(ctx context.Context, owner, repo string, number int) (*PullRequest, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	return getObject[PullRequest](ctx, c, fmt.Sprintf("%s/pulls/%d", base, number))
}

// CIState summarizes the CI verdict for a commit.
//
// Two independent mechanisms report it and a repository may use either: check runs (what
// GitHub Actions writes) and commit statuses (what external services write). Check runs
// are consulted first because an Actions-only repository — the common case — reports
// zero commit statuses, and reading only that surface would render every pull request as
// having no CI. A repository with neither reports CIUnknown.
// A truncated check set is never summarized: ListCheckRunsForRef fails closed on an
// unexplained short read (NFR-007), so a failing run on a later page can no longer be
// rendered as `passing` the way DEV-024 recorded through 1.6.
func (c *Client) CIState(ctx context.Context, owner, repo, ref string) (string, error) {
	if err := ValidateRef(ref); err != nil {
		return CIUnknown, err
	}

	runs, err := c.ListCheckRunsForRef(ctx, owner, repo, ref)
	switch {
	case err != nil && !isNotFound(err):
		return CIUnknown, err
	case err == nil && len(runs) > 0:
		return summarizeCheckRuns(runs), nil
	}

	status, err := c.GetCombinedStatus(ctx, owner, repo, ref)
	switch {
	case err != nil && isNotFound(err):
		return CIUnknown, nil
	case err != nil:
		return CIUnknown, err
	case status.TotalCount == 0:
		return CIUnknown, nil
	}
	switch status.State {
	case "success":
		return CIPassing, nil
	case "pending":
		return CIPending, nil
	default:
		return CIFailing, nil
	}
}

// CheckRun is one check run reported for a commit. Name is carried because the Merge phase
// matches required-check names against enforcement evidence, not just counts.
type CheckRun struct {
	Name       string `json:"name"`
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
}

// checkRunsPage is one page of the check-runs endpoint: a JSON object wrapping the list,
// with the collection size the truncation guard compares against.
type checkRunsPage struct {
	TotalCount int        `json:"total_count"`
	CheckRuns  []CheckRun `json:"check_runs"`
}

// total and items satisfy getPagedEnvelope's type constraint; the generic instantiation
// at ListCheckRunsForRef is their only "call site", which golangci-lint's `unused` pass
// does not follow — hence the suppression. Deleting them does not remove dead code, it
// breaks the build.
//
//nolint:unused // satisfies the getPagedEnvelope[CheckRun, checkRunsPage] constraint.
func (p checkRunsPage) total() int { return p.TotalCount }

//nolint:unused // satisfies the getPagedEnvelope[CheckRun, checkRunsPage] constraint.
func (p checkRunsPage) items() []CheckRun { return p.CheckRuns }

// CombinedStatus is the commit-status surface external CI services write.
type CombinedStatus struct {
	State      string `json:"state"`
	TotalCount int    `json:"total_count"`
}

// ListCheckRunsForRef returns every check run for a commit, across every page.
//
// Completeness is the point: the Merge phase decides admission from this list, so a short
// read is not a smaller answer but a wrong one. The reader follows same-origin pagination
// at per_page=100 and refuses to return a list shorter than the response's own
// `total_count` when no next page explains the difference (ErrPaginationTruncated).
func (c *Client) ListCheckRunsForRef(ctx context.Context, owner, repo, ref string) ([]CheckRun, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	if err := ValidateRef(ref); err != nil {
		return nil, err
	}
	return getPagedEnvelope[CheckRun, checkRunsPage](ctx, c,
		fmt.Sprintf("%s/commits/%s/check-runs", base, url.PathEscape(ref)), url.Values{})
}

// GetCombinedStatus returns the commit-status rollup for a commit.
func (c *Client) GetCombinedStatus(ctx context.Context, owner, repo, ref string) (*CombinedStatus, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	if err := ValidateRef(ref); err != nil {
		return nil, err
	}
	return getObject[CombinedStatus](ctx, c,
		fmt.Sprintf("%s/commits/%s/status", base, url.PathEscape(ref)))
}

// summarizeCheckRuns collapses many runs into one verdict, failure-dominant: a single
// failing run is the answer the operator needs, whatever the other runs say.
func summarizeCheckRuns(runs []CheckRun) string {
	verdict := CIPassing
	for _, run := range runs {
		if run.Status != "completed" {
			verdict = CIPending
			continue
		}
		switch run.Conclusion {
		case "success", "neutral", "skipped":
		default:
			return CIFailing
		}
	}
	return verdict
}

// repoPath builds a repository-scoped request path, validating both identity halves first.
//
// Like orgPath, it is the choke point rather than a convenience: every repository call in
// this package builds its URL here, so an explicit `--repo owner/name` and an
// origin-derived owner cannot reach GitHub without passing IR-001's validator, whatever
// the calling command forgot to check.
func repoPath(owner, repo string) (string, error) {
	if err := ValidateRepository(owner, repo); err != nil {
		return "", err
	}
	return "/repos/" + url.PathEscape(owner) + "/" + url.PathEscape(repo), nil
}

func isNotFound(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.Status == http.StatusNotFound
}

// getPaged reads every page of a JSON array endpoint at the largest page size GitHub
// accepts, following same-origin `rel="next"` links to exhaustion (NFR-007).
//
// It never returns a short list quietly: a page ceiling, a refused link, and an advertised
// total the decoded entries do not reach are all read failures. A silently truncated list
// is the one failure that looks like success — under-reported open work, a missing
// organization element read as drift, an unseen failing check read as a clear gate.
func getPaged[T any](ctx context.Context, c *Client, path string, query url.Values) ([]T, error) {
	all, err := walkPages(ctx, c, path, query, func(body []byte) ([]T, int, bool, error) {
		var chunk []T
		if err := json.Unmarshal(body, &chunk); err != nil {
			return nil, 0, false, fmt.Errorf("%w: the response for %s: %w", ErrDecode, path, err)
		}
		return chunk, 0, false, nil
	})
	return all, err
}

// getPagedEnvelope reads every page of an endpoint whose pages are JSON *objects* wrapping
// a list plus a `total_count` — the check-runs shape.
//
// The envelope is what makes the truncation guard sharp here: the server states the
// collection size in the body of every page, so a disagreement with the decoded count is
// evidence of truncation rather than an inference. Through 1.6 this endpoint was read
// through the single-object decoder, which discarded both the next link and the total
// (DEV-024); routing it through the paginating reader is what closes that defect.
func getPagedEnvelope[T any, E interface {
	total() int
	items() []T
}](ctx context.Context, c *Client, path string, query url.Values,
) ([]T, error) {
	return walkPages(ctx, c, path, query, func(body []byte) ([]T, int, bool, error) {
		var page E
		if err := json.Unmarshal(body, &page); err != nil {
			return nil, 0, false, fmt.Errorf("%w: the response for %s: %w", ErrDecode, path, err)
		}
		return page.items(), page.total(), true, nil
	})
}

// walkPages is the one pagination loop: page ceiling, origin-checked continuation, and the
// truncation comparison all live here so no reader can accidentally omit one.
//
// decode returns the page's entries plus the collection total the page advertised, with
// hasTotal false when the shape carries none. The total from the *first* page is the one
// compared, because GitHub reports the whole-collection size on every page and a later
// page's copy adds nothing.
func walkPages[T any](ctx context.Context, c *Client, path string, query url.Values,
	decode func(body []byte) (entries []T, total int, hasTotal bool, err error),
) ([]T, error) {
	query.Set("per_page", strconv.Itoa(pageSize))
	next := c.baseURL + path + "?" + query.Encode()

	var all []T
	advertised, known := 0, false

	for page := 1; next != ""; page++ {
		if page > maxPages {
			return nil, fmt.Errorf("%w: %s exceeded %d pages", ErrPaginationLimit, path, maxPages)
		}
		body, meta, err := c.get(ctx, next)
		if err != nil {
			return nil, err
		}
		entries, total, hasTotal, err := decode(body)
		if err != nil {
			return nil, err
		}
		if page == 1 {
			switch {
			case hasTotal:
				advertised, known = total, true
			case meta.hasTotal:
				advertised, known = meta.total, true
			}
		}
		all = append(all, entries...)
		next = meta.next
	}

	// Only an exhausted walk is compared. More entries than advertised is accepted: the
	// total can legitimately grow between page reads, and refusing a read for having seen
	// too much would fail closed on nothing. Fewer is the truncation NFR-007 refuses to
	// present as evidence.
	if known && len(all) < advertised {
		return nil, fmt.Errorf("%w: %s advertised %d entries but %d were returned across every page",
			ErrPaginationTruncated, path, advertised, len(all))
	}
	return all, nil
}

// getObject reads a single JSON object endpoint. It is for genuinely single resources; an
// object that wraps a paginating list belongs in getPagedEnvelope, which is the distinction
// DEV-024 was lost in.
func getObject[T any](ctx context.Context, c *Client, path string) (*T, error) {
	body, _, err := c.get(ctx, c.baseURL+path)
	if err != nil {
		return nil, err
	}
	var decoded T
	if err := json.Unmarshal(body, &decoded); err != nil {
		return nil, fmt.Errorf("%w: the response for %s: %w", ErrDecode, path, err)
	}
	return &decoded, nil
}
