package ghapi_test

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
)

const (
	typesPath  = "/orgs/L3DigitalNet/issue-types"
	fieldsPath = "/orgs/L3DigitalNet/issue-fields"
)

func newClient(t *testing.T, transport http.RoundTripper) *ghapi.Client {
	t.Helper()
	client, err := ghapi.NewClient("https://api.github.test", "gho_testtoken", transport)
	if err != nil {
		t.Fatalf("NewClient() error = %v, want nil", err)
	}
	return client
}

func TestListIssueTypes(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {Status: http.StatusOK, Body: `[
			{"name":"Bug","is_enabled":true},
			{"name":"Feature","is_enabled":false}
		]`},
	}}

	got, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	if err != nil {
		t.Fatalf("ListIssueTypes() error = %v, want nil", err)
	}
	if len(got) != 2 {
		t.Fatalf("ListIssueTypes() = %+v, want 2 entries", got)
	}
	if got[0].Name != "Bug" || !got[0].IsEnabled {
		t.Errorf("got[0] = %+v, want the enabled Bug type", got[0])
	}
	if got[1].IsEnabled {
		t.Errorf("got[1] = %+v, want IsEnabled false", got[1])
	}
}

func TestListIssueFields(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + fieldsPath: {Status: http.StatusOK, Body: `[
			{"name":"Workflow","data_type":"single_select","options":[{"name":"Ready"},{"name":"Done"}]},
			{"name":"Target date","data_type":"date"}
		]`},
	}}

	got, err := newClient(t, transport).ListIssueFields(context.Background(), "L3DigitalNet")
	if err != nil {
		t.Fatalf("ListIssueFields() error = %v, want nil", err)
	}
	if len(got) != 2 {
		t.Fatalf("ListIssueFields() = %+v, want 2 entries", got)
	}
	if got[0].DataType != "single_select" || len(got[0].Options) != 2 {
		t.Errorf("got[0] = %+v, want a two-option single_select", got[0])
	}
	if got[1].DataType != "date" || len(got[1].Options) != 0 {
		t.Errorf("got[1] = %+v, want a date field with no options", got[1])
	}
}

// Truncated pagination would present absent-but-real elements as "missing" drift, so the
// client must follow Link rel="next" rather than trusting a single page.
func TestListFollowsPagination(t *testing.T) {
	t.Parallel()

	next := "https://api.github.test" + typesPath + "?per_page=100&page=2"
	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {
			Status: http.StatusOK,
			Body:   `[{"name":"Bug","is_enabled":true}]`,
			Header: http.Header{"Link": []string{fmt.Sprintf(`<%s>; rel="next", <%s>; rel="last"`, next, next)}},
		},
	}}
	transport.RouteFunc = func(req *http.Request) (ghtest.Response, bool) {
		if req.URL.Query().Get("page") == "2" {
			return ghtest.Response{Status: http.StatusOK, Body: `[{"name":"Feature","is_enabled":true}]`}, true
		}
		return ghtest.Response{}, false
	}

	got, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	if err != nil {
		t.Fatalf("ListIssueTypes() error = %v, want nil", err)
	}
	if len(got) != 2 || got[1].Name != "Feature" {
		t.Fatalf("ListIssueTypes() = %+v, want both pages concatenated", got)
	}
}

// Every other test in this package injects a fake RoundTripper, which is what keeps the
// suite offline — and also what leaves the client's own net/http path unexercised: header
// construction, connection handling, and body closing are all skipped by a transport that
// never speaks HTTP. One loopback server covers that path end to end without leaving the
// machine.
func TestClientAgainstALoopbackServer(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != typesPath {
			http.Error(w, `{"message":"Not Found"}`, http.StatusNotFound)
			return
		}
		if got := r.Header.Get("Authorization"); got != "Bearer gho_testtoken" {
			http.Error(w, `{"message":"Bad credentials"}`, http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "application/vnd.github+json")
		_, _ = io.WriteString(w, `[{"name":"Bug","is_enabled":true}]`)
	}))
	t.Cleanup(server.Close)

	client, err := ghapi.NewClient(server.URL, "gho_testtoken", nil)
	if err != nil {
		t.Fatalf("NewClient() error = %v, want nil", err)
	}
	got, err := client.ListIssueTypes(context.Background(), "L3DigitalNet")
	if err != nil {
		t.Fatalf("ListIssueTypes() error = %v, want nil", err)
	}
	if len(got) != 1 || got[0].Name != "Bug" {
		t.Errorf("ListIssueTypes() = %+v, want the single Bug type", got)
	}
}

// The Link header is server-controlled text, and every request this client builds carries
// the operator's token in an Authorization header. Go strips credentials across hosts only
// on redirects it follows itself, which is not this path: a rel="next" pointing anywhere
// else would hand the bearer token to that host. Pagination therefore stops at the origin
// it started from, and says so rather than silently truncating the read.
func TestPaginationRefusesACrossOriginNextLink(t *testing.T) {
	t.Parallel()

	const elsewhere = "https://exfiltrate.test" + typesPath + "?per_page=100&page=2"
	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {
			Status: http.StatusOK,
			Body:   `[{"name":"Bug","is_enabled":true}]`,
			Header: http.Header{"Link": []string{fmt.Sprintf(`<%s>; rel="next"`, elsewhere)}},
		},
	}}

	got, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	if err == nil {
		t.Fatalf("ListIssueTypes() = %+v, error = nil; want a refusal of the cross-origin next link", got)
	}
	if !strings.Contains(err.Error(), "exfiltrate.test") {
		t.Errorf("error = %q, want it to name the refused host", err)
	}
	if requests := transport.Requests(); len(requests) != 1 {
		t.Errorf("made %d requests, want 1: the token must never reach %s", len(requests), elsewhere)
	}
}

// The origin guard protects a credential boundary, so it compares origins rather than
// spellings of one. A link that names the default port, and a relative link, both stay on
// the origin the request started from; refusing either would truncate a legitimate read
// and report the missing elements as organization drift.
func TestPaginationAcceptsEquivalentSpellingsOfTheSameOrigin(t *testing.T) {
	t.Parallel()

	for name, next := range map[string]string{
		"default port": "https://api.github.test:443" + typesPath + "?per_page=100&page=2",
		"relative":     typesPath + "?per_page=100&page=2",
	} {
		t.Run(name, func(t *testing.T) {
			t.Parallel()

			transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
				"GET " + typesPath: {
					Status: http.StatusOK,
					Body:   `[{"name":"Bug","is_enabled":true}]`,
					Header: http.Header{"Link": []string{fmt.Sprintf(`<%s>; rel="next"`, next)}},
				},
			}}
			transport.RouteFunc = func(req *http.Request) (ghtest.Response, bool) {
				if req.URL.Query().Get("page") == "2" {
					return ghtest.Response{Status: http.StatusOK, Body: `[{"name":"Feature","is_enabled":true}]`}, true
				}
				return ghtest.Response{}, false
			}

			got, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
			if err != nil {
				t.Fatalf("ListIssueTypes() error = %v, want the link followed", err)
			}
			if len(got) != 2 || got[1].Name != "Feature" {
				t.Errorf("ListIssueTypes() = %+v, want both pages concatenated", got)
			}
		})
	}
}

func TestRequestCarriesAuthAndAPIVersion(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {Status: http.StatusOK, Body: `[]`},
	}}

	if _, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet"); err != nil {
		t.Fatalf("ListIssueTypes() error = %v, want nil", err)
	}

	req := transport.LastRequest()
	if req == nil {
		t.Fatal("LastRequest() = nil, want a recorded request")
	}
	if got, want := req.Header.Get("Authorization"), "Bearer gho_testtoken"; got != want {
		t.Errorf("Authorization = %q, want %q", got, want)
	}
	if got, want := req.Header.Get("X-GitHub-Api-Version"), "2022-11-28"; got != want {
		t.Errorf("X-GitHub-Api-Version = %q, want %q", got, want)
	}
	if !strings.Contains(req.Header.Get("Accept"), "application/vnd.github+json") {
		t.Errorf("Accept = %q, want the GitHub JSON media type", req.Header.Get("Accept"))
	}
}

// The audit is defined as read-only against organization schema (FR-016). The client
// exposes no mutating call, so every request it can produce must be a GET.
func TestClientIssuesOnlyGETRequests(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath:  {Status: http.StatusOK, Body: `[]`},
		"GET " + fieldsPath: {Status: http.StatusOK, Body: `[]`},
	}}
	client := newClient(t, transport)

	if _, err := client.ListIssueTypes(context.Background(), "L3DigitalNet"); err != nil {
		t.Fatalf("ListIssueTypes() error = %v", err)
	}
	if _, err := client.ListIssueFields(context.Background(), "L3DigitalNet"); err != nil {
		t.Fatalf("ListIssueFields() error = %v", err)
	}

	methods := transport.Methods()
	if len(methods) != 2 {
		t.Fatalf("Methods() = %v, want two recorded requests", methods)
	}
	for _, method := range methods {
		if method != http.MethodGet {
			t.Errorf("recorded method %q, want only GET", method)
		}
	}
}

func TestClientErrors(t *testing.T) {
	t.Parallel()

	t.Run("transport failure is unreachable", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Err: errors.New("dial tcp: lookup api.github.test: no such host")}

		_, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
		if err == nil {
			t.Fatal("ListIssueTypes() error = nil, want an unreachable-API failure")
		}
		if !errors.Is(err, ghapi.ErrUnreachable) {
			t.Errorf("error = %v, want it to wrap ErrUnreachable", err)
		}
	})

	t.Run("401 is unauthorized", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + typesPath: {Status: http.StatusUnauthorized, Body: `{"message":"Bad credentials"}`},
		}}

		_, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
		if err == nil {
			t.Fatal("ListIssueTypes() error = nil, want an unauthorized failure")
		}
		if !errors.Is(err, ghapi.ErrUnauthorized) {
			t.Errorf("error = %v, want it to wrap ErrUnauthorized", err)
		}
		var apiErr *ghapi.APIError
		if !errors.As(err, &apiErr) {
			t.Fatalf("error = %v, want an *APIError", err)
		}
		if apiErr.Status != http.StatusUnauthorized {
			t.Errorf("APIError.Status = %d, want %d", apiErr.Status, http.StatusUnauthorized)
		}
	})

	t.Run("500 is a plain API error", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + typesPath: {Status: http.StatusInternalServerError, Body: `{"message":"Server Error"}`},
		}}

		_, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
		if err == nil {
			t.Fatal("ListIssueTypes() error = nil, want a failure")
		}
		if errors.Is(err, ghapi.ErrUnauthorized) {
			t.Errorf("error = %v, must not be classified as unauthorized", err)
		}
	})

	t.Run("malformed JSON fails closed", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + typesPath: {Status: http.StatusOK, Body: `{"not":"a list"}`},
		}}

		if _, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet"); err == nil {
			t.Fatal("ListIssueTypes() error = nil, want a decode failure")
		}
	})
}

func TestNewClientRequiresToken(t *testing.T) {
	t.Parallel()

	if _, err := ghapi.NewClient("https://api.github.test", "", nil); err == nil {
		t.Fatal("NewClient() error = nil, want a failure without a token")
	}
}
