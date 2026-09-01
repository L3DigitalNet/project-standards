package ghapi_test

import (
	"context"
	"errors"
	"net/http"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
)

// Every rate-limit response in this file carries `Retry-After: 0`, which is a real value
// GitHub can send and keeps the retry immediate: the test proves the retry happens, not
// how long it waited.
func rateLimitHeader(values map[string]string) http.Header {
	header := http.Header{}
	for name, value := range values {
		header.Set(name, value)
	}
	return header
}

// A 403 whose headers say "rate limit" is waited out and retried, not reported. Before
// this the first refusal ended the read as ErrUnauthorized, which sends an operator to
// re-authenticate a token GitHub never rejected (#234 item 8).
func TestRateLimitedReadIsRetried(t *testing.T) {
	t.Parallel()

	attempts := 0
	transport := &ghtest.Transport{}
	transport.RouteFunc = func(*http.Request) (ghtest.Response, bool) {
		attempts++
		if attempts == 1 {
			return ghtest.Response{
				Status: http.StatusForbidden,
				Body:   `{"message":"API rate limit exceeded"}`,
				Header: rateLimitHeader(map[string]string{"Retry-After": "0"}),
			}, true
		}
		return ghtest.Response{Status: http.StatusOK, Body: `[{"name":"Bug","is_enabled":true}]`}, true
	}

	types, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	if err != nil {
		t.Fatalf("ListIssueTypes() error = %v, want nil", err)
	}
	if len(types) != 1 || attempts != 2 {
		t.Fatalf("types = %+v after %d attempts, want one type after 2", types, attempts)
	}
}

// A write is retried on the same terms: 403 and 429 are returned before the mutation is
// applied, so reissuing it cannot double-apply anything.
func TestRateLimitedWriteIsRetried(t *testing.T) {
	t.Parallel()

	attempts := 0
	transport := &ghtest.Transport{}
	transport.RouteFunc = func(*http.Request) (ghtest.Response, bool) {
		attempts++
		if attempts == 1 {
			return ghtest.Response{
				Status: http.StatusTooManyRequests,
				Body:   `{"message":"You have exceeded a secondary rate limit"}`,
				Header: rateLimitHeader(map[string]string{"Retry-After": "0"}),
			}, true
		}
		return ghtest.Response{Status: http.StatusOK, Body: `{"number":12,"state":"closed"}`}, true
	}

	if _, err := newClient(t, transport).SetIssueState(
		context.Background(), "L3DigitalNet", "example-repo", 12, "closed", ""); err != nil {
		t.Fatalf("SetIssueState() error = %v, want nil", err)
	}
	if attempts != 2 {
		t.Fatalf("attempts = %d, want 2", attempts)
	}
}

// A rate limit that outlasts the retries is classified as one. The negative half of the
// assertion is the point: ErrUnauthorized is what 1.9 reported here.
func TestPersistentRateLimitIsNotACredentialRejection(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{}
	transport.RouteFunc = func(*http.Request) (ghtest.Response, bool) {
		return ghtest.Response{
			Status: http.StatusForbidden,
			Body:   `{"message":"API rate limit exceeded"}`,
			Header: rateLimitHeader(map[string]string{"Retry-After": "0", "X-RateLimit-Remaining": "0"}),
		}, true
	}

	_, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	switch {
	case err == nil:
		t.Fatal("ListIssueTypes() error = nil, want a rate-limit failure")
	case !errors.Is(err, ghapi.ErrRateLimited):
		t.Errorf("error = %v, want ErrRateLimited", err)
	case errors.Is(err, ghapi.ErrUnauthorized):
		t.Errorf("error = %v, want it NOT classified as a credential rejection", err)
	case !ghapi.IsOperational(err):
		t.Errorf("error = %v, want the operational marker so it still exits 3", err)
	}
}

// A 403 that is a genuine permission refusal carries none of the rate-limit headers: it
// must still unwrap to ErrUnauthorized and must not be retried, because retrying a
// refusal that will never change only multiplies it.
func TestPermissionRefusalIsNeitherRetriedNorReclassified(t *testing.T) {
	t.Parallel()

	attempts := 0
	transport := &ghtest.Transport{}
	transport.RouteFunc = func(*http.Request) (ghtest.Response, bool) {
		attempts++
		return ghtest.Response{Status: http.StatusForbidden, Body: `{"message":"Resource not accessible"}`}, true
	}

	_, err := newClient(t, transport).ListIssueTypes(context.Background(), "L3DigitalNet")
	if !errors.Is(err, ghapi.ErrUnauthorized) {
		t.Fatalf("error = %v, want ErrUnauthorized", err)
	}
	if errors.Is(err, ghapi.ErrRateLimited) {
		t.Errorf("error = %v, want it NOT classified as a rate limit", err)
	}
	if attempts != 1 {
		t.Errorf("attempts = %d, want 1: a permission refusal is not retried", attempts)
	}
}
