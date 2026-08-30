// Package ghapi is the tool's GitHub REST client: organization schema reads, repository
// work-item reads, and the repository-scoped writes the mutation subcommands perform.
//
// Two properties are structural rather than conventional:
//
//   - Scoped writes. Organization-scoped calls are GET-only (spec FR-016, invariant
//     "org-scoped calls read-only"): the audit reports schema drift and humans apply it,
//     so no call here addresses an `/orgs/` path with anything but GET. Every mutating
//     call lives in mutations.go and addresses a repository, which is the only surface
//     the tool writes to.
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
	"net"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
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
	// maxMessageBytes bounds the error excerpt shown when a response carries no JSON
	// message of its own, so a stray HTML error page cannot flood the terminal.
	maxMessageBytes = 200
	// requestTimeout keeps an unreachable API a precondition failure rather than a hang.
	requestTimeout = 30 * time.Second
)

// The operational-failure sentinels this package returns live in operational.go, where
// their exit-3 contract with package cli is documented.

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

// Error renders the failed request the way the operator would reproduce it.
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
	path, err := orgPath(org, "issue-types")
	if err != nil {
		return nil, err
	}
	return getList[IssueType](ctx, c, path)
}

// ListIssueFields returns every Issue Field defined for org.
func (c *Client) ListIssueFields(ctx context.Context, org string) ([]IssueField, error) {
	path, err := orgPath(org, "issue-fields")
	if err != nil {
		return nil, err
	}
	return getList[IssueField](ctx, c, path)
}

// orgPath builds an organization-scoped request path, validating the login first.
//
// Validation happens here rather than at each caller because this is the last point every
// organization read passes through: `audit --org`, the rendered policy organization, and
// the mutation path's resolved repository owner all converge on it, which is what makes
// IR-001's "one boundary" claim mechanical instead of a convention (closes DEV-021).
// PathEscape is retained behind the validator as defense in depth, not as the boundary.
func orgPath(org string, resource string) (string, error) {
	if err := ValidateLogin(org); err != nil {
		return "", err
	}
	return "/orgs/" + url.PathEscape(org) + "/" + resource, nil
}

// getList reads every page of a JSON array endpoint. Pagination is followed rather than
// assumed away: a truncated first page would present real organization elements as
// "missing" drift, which is the audit failing while looking like it succeeded.
func getList[T any](ctx context.Context, c *Client, path string) ([]T, error) {
	return getPaged[T](ctx, c, path, url.Values{})
}

// pageMeta is what one response says about the collection it is a page of: where the next
// page is, and how large the server claims the whole collection to be.
type pageMeta struct {
	next string
	// total is the collection size advertised by `X-Total-Count`, and hasTotal says
	// whether the header was present at all. Zero is a legitimate advertised total, so
	// the two cannot be collapsed into one field.
	total    int
	hasTotal bool
}

// get performs the one and only GET request shape this package can build.
func (c *Client) get(ctx context.Context, endpoint string) (body []byte, meta pageMeta, err error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, pageMeta{}, fmt.Errorf("building the request for %s: %w", endpoint, err)
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	req.Header.Set("Accept", acceptJSON)
	req.Header.Set(apiVersionHeader, apiVersion)
	req.Header.Set("User-Agent", userAgent)

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, pageMeta{}, fmt.Errorf("%w: GET %s: %w", ErrUnreachable, endpoint, err)
	}
	defer func() { _ = resp.Body.Close() }()

	body, err = io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return nil, pageMeta{}, fmt.Errorf("%w: reading the response for GET %s: %w", ErrUnreachable, endpoint, err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, pageMeta{}, &APIError{Status: resp.StatusCode, URL: endpoint, Message: apiMessage(body)}
	}
	next, err := c.nextPageURL(resp.Header.Get("Link"))
	if err != nil {
		return nil, pageMeta{}, err
	}
	meta = pageMeta{next: next}
	if raw := resp.Header.Get("X-Total-Count"); raw != "" {
		if total, convErr := strconv.Atoi(strings.TrimSpace(raw)); convErr == nil {
			meta.total, meta.hasTotal = total, true
		}
		// A malformed X-Total-Count is ignored rather than failed on: the header is an
		// optional hint, and refusing the read because a proxy wrote nonsense into it
		// would turn a working page into an operational failure. The truncation guard
		// still holds wherever the endpoint carries a `total_count` member in its body.
	}
	return body, meta, nil
}

// nextPageURL returns the rel="next" URL to follow, refusing one that leaves the API
// origin this client was built for.
//
// The check is a credential boundary, not tidiness. The Link header is server-controlled
// text, and every request built here attaches the operator's token as a bearer header. Go
// strips credentials across hosts only on redirects it follows itself; this URL is read
// from a header and handed to a fresh request, so nothing else would stop the token from
// reaching whatever host the header names. A link outside the origin fails the read rather
// than ending pagination quietly, because a silently short page is exactly the truncation
// getList refuses to present as organization drift.
//
// What the guard compares is the origin, not the spelling of it: the link is resolved
// against the base first, so a relative rel="next" — which the Link header permits, and
// which a proxy in front of the API may well emit — is followed rather than refused as
// though it named another host.
func (c *Client) nextPageURL(header string) (string, error) {
	target := nextLink(header)
	if target == "" {
		return "", nil
	}
	next, err := url.Parse(target)
	if err != nil {
		return "", fmt.Errorf("the pagination link %q is not a usable URL: %w", target, err)
	}
	base, err := url.Parse(c.baseURL)
	if err != nil {
		return "", fmt.Errorf("the API base URL %q is not a usable URL: %w", c.baseURL, err)
	}
	resolved := base.ResolveReference(next)
	if !strings.EqualFold(resolved.Scheme, base.Scheme) || originHost(resolved) != originHost(base) {
		return "", fmt.Errorf("%w: refusing the pagination link %q: it leaves the API origin %s://%s, "+
			"where the request's credentials belong", ErrPaginationRefused, target, base.Scheme, base.Host)
	}
	return resolved.String(), nil
}

// originHost renders a URL's host the way an origin comparison has to read it: lowercased,
// with a port that only restates the scheme's default dropped.
//
// `api.github.com:443` and `api.github.com` are one origin over https, so comparing the
// raw Host refuses a legitimate page for spelling the port out. Every other port survives,
// which is what keeps the guard fail-closed: another port is another origin.
func originHost(u *url.URL) string {
	host, port := strings.ToLower(u.Hostname()), u.Port()
	scheme := strings.ToLower(u.Scheme)
	if (scheme == "https" && port == "443") || (scheme == "http" && port == "80") {
		port = ""
	}
	if port == "" {
		return host
	}
	return net.JoinHostPort(host, port)
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
	if len(text) > maxMessageBytes {
		// Cutting at a fixed byte offset can land inside a multi-byte rune, and the half
		// rune prints as U+FFFD: the operator reads corruption where the tool meant to
		// show a truncated message. Back up to a rune boundary first.
		cut := maxMessageBytes
		for cut > 0 && !utf8.RuneStart(text[cut]) {
			cut--
		}
		text = text[:cut] + "…"
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
