package ghapi_test

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
)

func TestValidateLogin(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		login string
		valid bool
	}{
		{"ordinary organization", "L3DigitalNet", true},
		{"single character", "a", true},
		{"internal hyphen", "octo-org", true},
		{"maximum length", strings.Repeat("a", 39), true},
		{"empty", "", false},
		{"one over the ceiling", strings.Repeat("a", 40), false},
		{"leading hyphen", "-octo", false},
		{"trailing hyphen", "octo-", false},
		{"doubled hyphen", "octo--org", false},
		{"underscore", "octo_org", false},
		{"dot", "octo.org", false},
		// Each of the next three is a value that survives url.PathEscape unchanged or
		// nearly so, which is why escaping was never the boundary this validator is.
		{"path traversal", "..", false},
		{"host-shaped", "evil.test", false},
		{"whitespace", "octo org", false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			err := ghapi.ValidateLogin(tc.login)
			if tc.valid && err != nil {
				t.Fatalf("ValidateLogin(%q) = %v, want nil", tc.login, err)
			}
			if !tc.valid {
				if err == nil {
					t.Fatalf("ValidateLogin(%q) = nil, want a refusal", tc.login)
				}
				if !errors.Is(err, ghapi.ErrInvalidIdentity) {
					t.Errorf("ValidateLogin(%q) error = %v, want ErrInvalidIdentity in the chain", tc.login, err)
				}
			}
		})
	}
}

func TestValidateRepositoryName(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		value string
		valid bool
	}{
		{"hyphenated", "example-repo", true},
		{"underscored", "example_repo", true},
		{"dotted", "example.repo", true},
		{"dot-prefixed", ".github", true},
		{"empty", "", false},
		{"current directory", ".", false},
		{"parent directory", "..", false},
		{"slash", "owner/name", false},
		{"space", "example repo", false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			err := ghapi.ValidateRepositoryName(tc.value)
			if tc.valid != (err == nil) {
				t.Fatalf("ValidateRepositoryName(%q) = %v, want valid = %v", tc.value, err, tc.valid)
			}
		})
	}
}

func TestValidateHost(t *testing.T) {
	t.Parallel()

	// GitHub Enterprise hosts are supported, so the validator judges shape rather than
	// membership of a github.com allowlist.
	for _, host := range []string{"github.com", "github.example-corp.com", "ghe"} {
		if err := ghapi.ValidateHost(host); err != nil {
			t.Errorf("ValidateHost(%q) = %v, want nil", host, err)
		}
	}
	for _, host := range []string{"", "user@github.com", "github.com/evil", "git hub.com", "github..com"} {
		if err := ghapi.ValidateHost(host); err == nil {
			t.Errorf("ValidateHost(%q) = nil, want a refusal", host)
		}
	}
}

// The boundary is only worth having if it stops a request. Every repository- and
// organization-scoped call builds its URL through the validating path helpers, so an
// invalid identity must fail before the transport sees anything.
func TestInvalidIdentityIsRefusedBeforeAnyRequest(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{}}
	client := newClient(t, transport)
	ctx := context.Background()

	calls := map[string]func() error{
		"ListIssueTypes": func() error {
			_, err := client.ListIssueTypes(ctx, "evil.test")
			return err
		},
		"ListIssueFieldIdentities": func() error {
			_, err := client.ListIssueFieldIdentities(ctx, "../../orgs")
			return err
		},
		"GetIssue": func() error {
			_, err := client.GetIssue(ctx, "octo--org", "example-repo", 1)
			return err
		},
		"GetPullRequest": func() error {
			_, err := client.GetPullRequest(ctx, "L3DigitalNet", "..", 1)
			return err
		},
		"ListCheckRunsForRef": func() error {
			_, err := client.ListCheckRunsForRef(ctx, "-bad", "example-repo", "abc")
			return err
		},
		"MergePullRequest": func() error {
			_, err := client.MergePullRequest(ctx, "L3DigitalNet", "bad repo", 1, ghapi.MergeMethodSquash, "abc")
			return err
		},
		"CreateComment": func() error {
			_, err := client.CreateComment(ctx, "L3DigitalNet", "bad repo", 1, "hello")
			return err
		},
	}

	for name, call := range calls {
		err := call()
		if err == nil {
			t.Errorf("%s() = nil error, want an identity refusal", name)
			continue
		}
		if !errors.Is(err, ghapi.ErrInvalidIdentity) {
			t.Errorf("%s() error = %v, want ErrInvalidIdentity", name, err)
		}
		// An identity refusal is the operator's input error and must stay exit 2, so it
		// carries no operational marker.
		if ghapi.IsOperational(err) {
			t.Errorf("%s() error = %v, want it NOT marked operational", name, err)
		}
	}
	if transport.Count() != 0 {
		t.Errorf("made %d requests, want 0: no invalid identity may reach GitHub", transport.Count())
	}
}

// Every failure class the CLI must map to exit 3 carries the marker; the classifier lives
// in package cli and matches this interface structurally, so a regression here is silent
// there.
func TestOperationalMarking(t *testing.T) {
	t.Parallel()

	ctx := context.Background()

	transportErr := errors.New("dial tcp: connection refused")
	unreachable := newClient(t, &ghtest.Transport{Err: transportErr})
	if _, err := unreachable.ListIssueTypes(ctx, "L3DigitalNet"); !ghapi.IsOperational(err) {
		t.Errorf("transport failure error = %v, want it marked operational", err)
	}

	forbidden := newClient(t, &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {Status: http.StatusForbidden, Body: `{"message":"Forbidden"}`},
	}})
	_, err := forbidden.ListIssueTypes(ctx, "L3DigitalNet")
	if !ghapi.IsOperational(err) {
		t.Errorf("403 error = %v, want it marked operational", err)
	}
	if !errors.Is(err, ghapi.ErrUnauthorized) {
		t.Errorf("403 error = %v, want ErrUnauthorized in the chain", err)
	}

	malformed := newClient(t, &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {Status: http.StatusOK, Body: `{"not":"an array"}`},
	}})
	decodeErr := func() error {
		_, err := malformed.ListIssueTypes(ctx, "L3DigitalNet")
		return err
	}()
	if !errors.Is(decodeErr, ghapi.ErrDecode) || !ghapi.IsOperational(decodeErr) {
		t.Errorf("decode error = %v, want ErrDecode and the operational marker", decodeErr)
	}

	crossOrigin := newClient(t, &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + typesPath: {
			Status: http.StatusOK,
			Body:   `[]`,
			Header: http.Header{"Link": []string{`<https://exfiltrate.test/x>; rel="next"`}},
		},
	}})
	if _, err := crossOrigin.ListIssueTypes(ctx, "L3DigitalNet"); !ghapi.IsOperational(err) {
		t.Errorf("cross-origin refusal = %v, want it marked operational", err)
	}
}
