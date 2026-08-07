// Package ghapi is the tool's GitHub REST client for organization schema.
//
// Two properties are structural rather than conventional:
//
//   - Read-only. The audit compares organization Issue Types and Issue Fields without
//     mutating them (spec FR-016, invariant "org-scoped calls read-only"). This package
//     exposes no mutating call and builds no non-GET request, so there is no org-mutation
//     surface for a caller to reach for.
//   - Injected transport. Every request goes through an http.RoundTripper supplied by
//     the caller (decision D-002), which is how the whole test suite runs offline against
//     a fake and why no test depends on GitHub availability or the operator's account.
package ghapi

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// DefaultBaseURL is the public GitHub REST endpoint.
const DefaultBaseURL = "https://api.github.com"

const (
	apiVersionHeader = "X-GitHub-Api-Version"
	apiVersion       = "2022-11-28"
	acceptJSON       = "application/vnd.github+json"
	userAgent        = "gh-workflow"

	pageSize = 100
	// maxPages bounds pagination so a server that keeps advertising rel="next" cannot
	// spin the audit forever; org schema is two orders of magnitude smaller than this.
	maxPages = 50
	// maxResponseBytes bounds a single response body for the same reason.
	maxResponseBytes = 8 << 20
	// requestTimeout keeps an unreachable API a precondition failure rather than a hang.
	requestTimeout = 30 * time.Second
)

var (
	// ErrUnreachable marks a transport-level failure: DNS, dial, TLS, timeout.
	ErrUnreachable = errors.New("github api is unreachable")
	// ErrUnauthorized marks a credential rejection (401/403).
	ErrUnauthorized = errors.New("github rejected the credentials")
)

// IssueType is one organization Issue Type. A type that exists but is disabled cannot be
// applied to an issue, so IsEnabled is part of the audited state, not decoration.
type IssueType struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	IsEnabled   bool   `json:"is_enabled"`
}

// IssueFieldOption is one selectable value of a single_select Issue Field.
type IssueFieldOption struct {
	Name string `json:"name"`
}

// IssueField is one organization Issue Field.
type IssueField struct {
	Name     string             `json:"name"`
	DataType string             `json:"data_type"`
	Options  []IssueFieldOption `json:"options"`
}

// APIError is a non-2xx response from GitHub.
type APIError struct {
	Status  int
	URL     string
	Message string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("GET %s: %d %s", e.URL, e.Status, e.Message)
}

// Unwrap classifies credential rejections so callers can report an authentication
// precondition failure without matching on status codes themselves.
func (e *APIError) Unwrap() error {
	if e.Status == http.StatusUnauthorized || e.Status == http.StatusForbidden {
		return ErrUnauthorized
	}
	return nil
}

// Client reads organization schema from the GitHub REST API.
type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

// NewClient returns a client authenticating with token. An empty baseURL means the
// public API; a nil transport means the default one. Tests always pass both.
func NewClient(baseURL, token string, transport http.RoundTripper) (*Client, error) {
	if token == "" {
		return nil, errors.New("a GitHub token is required")
	}
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}
	if transport == nil {
		transport = http.DefaultTransport
	}
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		token:   token,
		http:    &http.Client{Transport: transport, Timeout: requestTimeout},
	}, nil
}

// ListIssueTypes returns every Issue Type defined for org.
func (c *Client) ListIssueTypes(ctx context.Context, org string) ([]IssueType, error) {
	return getList[IssueType](ctx, c, "/orgs/"+url.PathEscape(org)+"/issue-types")
}

// ListIssueFields returns every Issue Field defined for org.
func (c *Client) ListIssueFields(ctx context.Context, org string) ([]IssueField, error) {
	return getList[IssueField](ctx, c, "/orgs/"+url.PathEscape(org)+"/issue-fields")
}

// getList reads every page of a JSON array endpoint. Pagination is followed rather than
// assumed away: a truncated first page would present real organization elements as
// "missing" drift, which is the audit failing while looking like it succeeded.
func getList[T any](ctx context.Context, c *Client, path string) ([]T, error) {
	next := fmt.Sprintf("%s%s?per_page=%d", c.baseURL, path, pageSize)
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

// get performs the one and only request shape this package can build.
func (c *Client) get(ctx context.Context, endpoint string) (body []byte, nextURL string, err error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, "", fmt.Errorf("building the request for %s: %w", endpoint, err)
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Accept", acceptJSON)
	req.Header.Set(apiVersionHeader, apiVersion)
	req.Header.Set("User-Agent", userAgent)

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, "", fmt.Errorf("%w: GET %s: %w", ErrUnreachable, endpoint, err)
	}
	defer func() { _ = resp.Body.Close() }()

	body, err = io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return nil, "", fmt.Errorf("%w: reading the response for GET %s: %w", ErrUnreachable, endpoint, err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, "", &APIError{Status: resp.StatusCode, URL: endpoint, Message: apiMessage(body)}
	}
	return body, nextLink(resp.Header.Get("Link")), nil
}

// apiMessage extracts GitHub's own error text, falling back to a bounded excerpt so a
// stray HTML error page cannot flood the operator's terminal.
func apiMessage(body []byte) string {
	var payload struct {
		Message string `json:"message"`
	}
	if err := json.Unmarshal(body, &payload); err == nil && payload.Message != "" {
		return payload.Message
	}
	text := strings.TrimSpace(string(body))
	if len(text) > 200 {
		text = text[:200] + "…"
	}
	if text == "" {
		return "no response body"
	}
	return text
}

// nextLink returns the rel="next" URL from a Link header, or "" when the page is last.
func nextLink(header string) string {
	for _, part := range strings.Split(header, ",") {
		target, params, ok := strings.Cut(strings.TrimSpace(part), ";")
		if !ok {
			continue
		}
		if !strings.Contains(params, `rel="next"`) {
			continue
		}
		target = strings.TrimSpace(target)
		if strings.HasPrefix(target, "<") && strings.HasSuffix(target, ">") {
			return target[1 : len(target)-1]
		}
	}
	return ""
}
