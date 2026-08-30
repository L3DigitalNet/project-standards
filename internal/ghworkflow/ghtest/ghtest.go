// Package ghtest provides the offline doubles every gh-workflow test runs against.
//
// It exists as an ordinary package rather than a _test.go file because several packages
// need the same fake, and because decision D-002 makes the transport the single seam
// where GitHub enters the tool: keeping one fake here is what makes "no test touches the
// network" checkable rather than aspirational.
package ghtest

import (
	"context"
	"io"
	"net/http"
	"strings"
	"sync"
)

// Response is a canned reply keyed by "METHOD /path".
type Response struct {
	Status int
	Body   string
	Header http.Header
}

// TokenSource is a ghauth.TokenSource double. It satisfies the interface structurally,
// so ghtest stays free of a dependency on the package it doubles.
type TokenSource struct {
	Value string
	Err   error
}

// Token returns the configured token or error.
func (s TokenSource) Token(context.Context) (string, error) {
	if s.Err != nil {
		return "", s.Err
	}
	return s.Value, nil
}

// Transport is an http.RoundTripper serving canned responses and recording every
// request, so tests can assert both what came back and what went out — the latter is how
// the read-only invariant is proved rather than asserted.
//
// The recorder is also the measuring instrument for spec NFR-008: command tests assert a
// bounded number of API calls for a successful Ready, Merge, summary, or receipt run, and
// Count is that number. Request bodies are captured too, because a GraphQL test cannot
// distinguish two mutations by URL — every one of them is POST /graphql.
type Transport struct {
	// Routes maps "METHOD /path" (query ignored) to a canned response.
	Routes map[string]Response
	// RouteFunc handles requests Routes does not, for cases like pagination where the
	// query string selects the response.
	RouteFunc func(req *http.Request) (Response, bool)
	// Err, when set, fails every request the way an unreachable API would.
	Err error

	mu       sync.Mutex
	requests []*http.Request
	bodies   []string
}

// RoundTrip implements http.RoundTripper.
func (t *Transport) RoundTrip(req *http.Request) (*http.Response, error) {
	// The body is read here and replaced, not consumed: an http.Request body is a
	// one-shot reader, so recording it without putting it back would hand the route
	// handlers an empty body and make every RouteFunc that inspects a GraphQL query fail.
	body := ""
	if req.Body != nil {
		if raw, err := io.ReadAll(req.Body); err == nil {
			body = string(raw)
			req.Body = io.NopCloser(strings.NewReader(body))
		}
	}

	t.mu.Lock()
	clone := req.Clone(req.Context())
	clone.Body = io.NopCloser(strings.NewReader(body))
	t.requests = append(t.requests, clone)
	t.bodies = append(t.bodies, body)
	t.mu.Unlock()

	if t.Err != nil {
		return nil, t.Err
	}

	resp, ok := t.lookup(req)
	if !ok {
		resp = Response{Status: http.StatusNotFound, Body: `{"message":"Not Found"}`}
	}
	header := resp.Header.Clone()
	if header == nil {
		header = http.Header{}
	}
	header.Set("Content-Type", "application/json")
	return &http.Response{
		Status:     http.StatusText(resp.Status),
		StatusCode: resp.Status,
		Header:     header,
		Body:       io.NopCloser(strings.NewReader(resp.Body)),
		Request:    req,
	}, nil
}

func (t *Transport) lookup(req *http.Request) (Response, bool) {
	if t.RouteFunc != nil {
		if resp, ok := t.RouteFunc(req); ok {
			return resp, true
		}
	}
	resp, ok := t.Routes[req.Method+" "+req.URL.Path]
	return resp, ok
}

// Requests returns every recorded request in order.
func (t *Transport) Requests() []*http.Request {
	t.mu.Lock()
	defer t.mu.Unlock()
	return append([]*http.Request(nil), t.requests...)
}

// LastRequest returns the most recent recorded request, or nil.
func (t *Transport) LastRequest() *http.Request {
	t.mu.Lock()
	defer t.mu.Unlock()
	if len(t.requests) == 0 {
		return nil
	}
	return t.requests[len(t.requests)-1]
}

// Count returns how many requests were made. It is the NFR-008 call-count assertion's
// instrument; assert on it directly rather than on len(Requests()) so the intent survives.
func (t *Transport) Count() int {
	t.mu.Lock()
	defer t.mu.Unlock()
	return len(t.requests)
}

// Bodies returns the request body of every recorded request, in order, with an empty
// string for a request that carried none.
func (t *Transport) Bodies() []string {
	t.mu.Lock()
	defer t.mu.Unlock()
	return append([]string(nil), t.bodies...)
}

// LastBody returns the most recent recorded request body, or "".
func (t *Transport) LastBody() string {
	t.mu.Lock()
	defer t.mu.Unlock()
	if len(t.bodies) == 0 {
		return ""
	}
	return t.bodies[len(t.bodies)-1]
}

// Methods returns the HTTP method of every recorded request, in order.
func (t *Transport) Methods() []string {
	requests := t.Requests()
	methods := make([]string, 0, len(requests))
	for _, req := range requests {
		methods = append(methods, req.Method)
	}
	return methods
}
