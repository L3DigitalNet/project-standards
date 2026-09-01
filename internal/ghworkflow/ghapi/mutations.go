package ghapi

// Repository-scoped writes: the issue creation, Issue Field value, and lifecycle calls
// the mutation subcommands perform (spec FR-021).
//
// This file holds the tool's only non-GET requests, and the boundary it draws is the one
// the package documentation in ghapi.go states: writes are repository-scoped, and no call
// here addresses an `/orgs/` path with anything but GET. The organization schema stays
// read-only — audits report drift, humans apply it — so there remains no org-mutation
// surface for a caller to reach for.
//
// The one org-scoped read that lives here, ListIssueFieldIdentities, exists because
// GitHub addresses field values by numeric id while every operator-facing surface — the
// vocabulary reference, org-schema.yaml, the CLI flags — names fields by name. Resolving
// one to the other is the write path's first step, not a second schema source.

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

// IssueFieldIdentity pairs an organization Issue Field's API id with its name. It is the
// same field IssueField describes, reduced to what addressing a write requires.
type IssueFieldIdentity struct {
	ID       int64  `json:"id"`
	Name     string `json:"name"`
	DataType string `json:"data_type"`
}

// IssueFieldAssignment is one field value to write, addressed by field id.
type IssueFieldAssignment struct {
	FieldID int64 `json:"field_id"`
	Value   any   `json:"value"`
}

// CreateIssueRequest is the body of an issue creation. Empty optional members are omitted
// rather than sent as empty strings, which GitHub would treat as an explicit clear.
type CreateIssueRequest struct {
	Title  string                 `json:"title"`
	Body   string                 `json:"body,omitempty"`
	Type   string                 `json:"type,omitempty"`
	Fields []IssueFieldAssignment `json:"issue_field_values,omitempty"`
}

// RequestError is a non-2xx response to a write.
//
// APIError predates the write surface and formats every failure as a GET, which would
// misreport a POST or PATCH — and a mutation's error text is exactly where the operator
// looks to learn what did or did not happen. Both types classify credential rejections
// the same way, so callers keep matching on ErrUnauthorized rather than on status codes.
type RequestError struct {
	Method  string
	Status  int
	URL     string
	Message string
	// RateLimited carries the same fact as APIError.RateLimited: the write was still
	// refused for rate limiting after the retries in ratelimit.go were spent.
	RateLimited bool
}

func (e *RequestError) Error() string {
	return fmt.Sprintf("%s %s: %d %s", e.Method, e.URL, e.Status, e.Message)
}

// Unwrap classifies credential rejections, matching APIError — including the rate-limit
// split, which must stay identical on both types so a caller never has to know whether a
// failure came from a read or a write to interpret it.
func (e *RequestError) Unwrap() error {
	switch {
	case e.RateLimited:
		return ErrRateLimited
	case e.Status == http.StatusUnauthorized || e.Status == http.StatusForbidden:
		return ErrUnauthorized
	default:
		return nil
	}
}

// ListIssueFieldIdentities returns every organization Issue Field with its API id. This
// is a GET: the organization surface stays read-only.
func (c *Client) ListIssueFieldIdentities(ctx context.Context, org string) ([]IssueFieldIdentity, error) {
	path, err := orgPath(org, "issue-fields")
	if err != nil {
		return nil, err
	}
	return getList[IssueFieldIdentity](ctx, c, path)
}

// ListBlockingDependencies returns the issues this issue is blocked by, which is one of
// the Ready preconditions `check` verifies (spec FR-023).
func (c *Client) ListBlockingDependencies(ctx context.Context, owner, repo string, number int) ([]Issue, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	return getList[Issue](ctx, c,
		fmt.Sprintf("%s/issues/%d/dependencies/blocked_by", base, number))
}

// CreateIssue creates a typed issue with its body and initial field values in one call.
func (c *Client) CreateIssue(ctx context.Context, owner, repo string, req CreateIssueRequest) (*Issue, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	var created Issue
	if err := c.send(ctx, http.MethodPost, base+"/issues", req, &created); err != nil {
		return nil, err
	}
	return &created, nil
}

// AddIssueFieldValues writes the given field values, leaving every other field untouched.
//
// The endpoint choice is load-bearing. GitHub offers two: PUT replaces the issue's whole
// field set, so writing one field through it would silently clear the other six, and POST
// adds or updates exactly the fields named. Every caller here is a partial update, so PUT
// is not an option regardless of how the operation reads.
//
// An empty assignment list is refused rather than sent: to POST it is the documented way
// to clear every field value, which is the opposite of a caller passing nothing.
func (c *Client) AddIssueFieldValues(ctx context.Context, owner, repo string, number int,
	values []IssueFieldAssignment,
) error {
	if len(values) == 0 {
		return fmt.Errorf("no field values to write for %s/%s#%d", owner, repo, number)
	}
	base, err := repoPath(owner, repo)
	if err != nil {
		return err
	}
	payload := struct {
		Values []IssueFieldAssignment `json:"issue_field_values"`
	}{Values: values}
	return c.send(ctx, http.MethodPost,
		fmt.Sprintf("%s/issues/%d/issue-field-values", base, number), payload, nil)
}

// SetIssueState applies the native open/closed state and its reason. GitHub ignores
// state_reason unless state changes, and reapplying a state the issue already holds is
// accepted, which is what makes this step of the terminal sequence idempotent.
func (c *Client) SetIssueState(ctx context.Context, owner, repo string, number int,
	state, reason string,
) (*Issue, error) {
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	payload := struct {
		State  string `json:"state"`
		Reason string `json:"state_reason,omitempty"`
	}{State: state, Reason: reason}

	var updated Issue
	if err := c.send(ctx, http.MethodPatch,
		fmt.Sprintf("%s/issues/%d", base, number), payload, &updated); err != nil {
		return nil, err
	}
	return &updated, nil
}

// SetIssueType assigns the issue's Issue Type, leaving every other attribute untouched.
//
// It shares the PATCH endpoint with SetIssueState rather than extending that call's
// payload, because the two answer to different subcommands: folding the type in there
// would make every terminal transition carry a type it was never asked to change, and an
// omitted-but-present member is exactly the kind of accidental write the typed payloads
// here exist to prevent.
//
// The updated issue is returned because on this member the status code is not the oracle.
// GitHub documents the type as settable only by a caller with push access and states that
// "without push access to the repository, type changes are silently dropped" — a 200
// carrying the issue's previous type. Only the caller comparing the response against the
// request can tell that write from an applied one.
//
// An empty type is refused rather than sent, matching AddIssueFieldValues: GitHub clears
// the type with a null, and `{"type": ""}` is an undefined request no caller here means.
func (c *Client) SetIssueType(ctx context.Context, owner, repo string, number int,
	issueType string,
) (*Issue, error) {
	if issueType == "" {
		return nil, fmt.Errorf("no Issue Type to set for %s/%s#%d", owner, repo, number)
	}
	base, err := repoPath(owner, repo)
	if err != nil {
		return nil, err
	}
	payload := struct {
		Type string `json:"type"`
	}{Type: issueType}

	var updated Issue
	if err := c.send(ctx, http.MethodPatch,
		fmt.Sprintf("%s/issues/%d", base, number), payload, &updated); err != nil {
		return nil, err
	}
	return &updated, nil
}

// send performs one write. The body is always produced by the JSON encoder from a typed
// value, never assembled as text, so no field value an operator supplies can reshape the
// request it travels in.
func (c *Client) send(ctx context.Context, method, path string, payload, out any) error {
	encoded, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("encoding the %s %s request: %w", method, path, err)
	}
	endpoint := c.baseURL + path

	// A fresh body reader per attempt: doWithRetry may reissue this request, and a reader
	// consumed by the first attempt would send an empty payload on the second.
	resp, body, limited, err := c.doWithRetry(ctx, method+" "+endpoint, func() (*http.Request, error) {
		req, err := http.NewRequestWithContext(ctx, method, endpoint, bytes.NewReader(encoded))
		if err != nil {
			return nil, fmt.Errorf("building the request for %s %s: %w", method, endpoint, err)
		}
		req.Header.Set("Authorization", "Bearer "+c.token)
		req.Header.Set("Accept", acceptJSON)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set(apiVersionHeader, apiVersion)
		req.Header.Set("User-Agent", userAgent)
		return req, nil
	})
	if err != nil {
		return err
	}
	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return &RequestError{
			Method: method, Status: resp.StatusCode, URL: endpoint,
			Message: apiMessage(body), RateLimited: limited,
		}
	}
	if out == nil {
		return nil
	}
	if err := json.Unmarshal(body, out); err != nil {
		return fmt.Errorf("decoding the response for %s %s: %w", method, endpoint, err)
	}
	return nil
}
