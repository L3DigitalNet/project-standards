package ghapi

// Repository-scoped work-item reads: the issues, pull requests, and CI state the
// rendering surfaces (spec FR-019, FR-022) present. It extends this package rather than
// standing up a second HTTP client so the two structural properties the package
// documentation states — read-only, and every request through the injected transport —
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

// PullRequest is one repository pull request.
type PullRequest struct {
	Number  int    `json:"number"`
	Title   string `json:"title"`
	HTMLURL string `json:"html_url"`
	State   string `json:"state"`
	Draft   bool   `json:"draft"`
	Body    string `json:"body"`
	Head    struct {
		SHA string `json:"sha"`
	} `json:"head"`
}

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
	entries, err := getPaged[Issue](ctx, c, repoPath(owner, repo)+"/issues",
		url.Values{"state": {"open"}})
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
func (c *Client) GetIssue(ctx context.Context, owner, repo string, number int) (*Issue, error) {
	return getObject[Issue](ctx, c, fmt.Sprintf("%s/issues/%d", repoPath(owner, repo), number))
}

// ListOpenPullRequests returns every open pull request in the repository.
func (c *Client) ListOpenPullRequests(ctx context.Context, owner, repo string) ([]PullRequest, error) {
	return getPaged[PullRequest](ctx, c, repoPath(owner, repo)+"/pulls", url.Values{"state": {"open"}})
}

// GetPullRequest returns one pull request by number.
func (c *Client) GetPullRequest(ctx context.Context, owner, repo string, number int) (*PullRequest, error) {
	return getObject[PullRequest](ctx, c, fmt.Sprintf("%s/pulls/%d", repoPath(owner, repo), number))
}

// CIState summarizes the CI verdict for a commit.
//
// Two independent mechanisms report it and a repository may use either: check runs (what
// GitHub Actions writes) and commit statuses (what external services write). Check runs
// are consulted first because an Actions-only repository — the common case — reports
// zero commit statuses, and reading only that surface would render every pull request as
// having no CI. A repository with neither reports CIUnknown.
func (c *Client) CIState(ctx context.Context, owner, repo, ref string) (string, error) {
	if ref == "" {
		return CIUnknown, nil
	}

	checks, err := getObject[checkRunsResponse](ctx, c, fmt.Sprintf("%s/commits/%s/check-runs",
		repoPath(owner, repo), url.PathEscape(ref)))
	switch {
	case err != nil && !isNotFound(err):
		return "", err
	case err == nil && len(checks.CheckRuns) > 0:
		return summarizeCheckRuns(checks.CheckRuns), nil
	}

	status, err := getObject[combinedStatus](ctx, c, fmt.Sprintf("%s/commits/%s/status",
		repoPath(owner, repo), url.PathEscape(ref)))
	switch {
	case err != nil && isNotFound(err):
		return CIUnknown, nil
	case err != nil:
		return "", err
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

type checkRun struct {
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
}

type checkRunsResponse struct {
	TotalCount int        `json:"total_count"`
	CheckRuns  []checkRun `json:"check_runs"`
}

type combinedStatus struct {
	State      string `json:"state"`
	TotalCount int    `json:"total_count"`
}

// summarizeCheckRuns collapses many runs into one verdict, failure-dominant: a single
// failing run is the answer the operator needs, whatever the other runs say.
func summarizeCheckRuns(runs []checkRun) string {
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

func repoPath(owner, repo string) string {
	return "/repos/" + url.PathEscape(owner) + "/" + url.PathEscape(repo)
}

func isNotFound(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.Status == http.StatusNotFound
}

// getPaged reads every page of a JSON array endpoint that needs query parameters of its
// own. It is getList with a caller-supplied query; pagination is followed for the same
// reason, since a truncated first page silently under-reports open work.
func getPaged[T any](ctx context.Context, c *Client, path string, query url.Values) ([]T, error) {
	query.Set("per_page", strconv.Itoa(pageSize))
	next := c.baseURL + path + "?" + query.Encode()
	var all []T

	for page := 1; next != ""; page++ {
		if page > maxPages {
			return nil, fmt.Errorf("%s: pagination exceeded %d pages", path, maxPages)
		}
		body, following, err := c.get(ctx, next)
		if err != nil {
			return nil, err
		}
		var chunk []T
		if err := json.Unmarshal(body, &chunk); err != nil {
			return nil, fmt.Errorf("decoding the response for %s: %w", path, err)
		}
		all = append(all, chunk...)
		next = following
	}
	return all, nil
}

// getObject reads a single JSON object endpoint.
func getObject[T any](ctx context.Context, c *Client, path string) (*T, error) {
	body, _, err := c.get(ctx, c.baseURL+path)
	if err != nil {
		return nil, err
	}
	var decoded T
	if err := json.Unmarshal(body, &decoded); err != nil {
		return nil, fmt.Errorf("decoding the response for %s: %w", path, err)
	}
	return &decoded, nil
}
