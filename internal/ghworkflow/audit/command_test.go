package audit_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"

	// The audit subcommand registers itself; importing the package under test is what
	// wires it into the registry, exactly as cmd/gh-workflow does.
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/audit"
)

const (
	fixtureToken = "gho_fixturetokenvalue"
	fixtureOrg   = "L3DigitalNet"
	fixtureBase  = "https://api.github.test"

	fixtureSchema = `issue_types:
  - Bug
  - Feature

issue_fields:
  Workflow:
    type: single_select
    values:
      - Ready
      - Done

  Target date:
    type: date
`

	fixturePolicy = "organization = \"L3DigitalNet\"\npackage_version = \"1.0\"\n"

	liveTypes  = `[{"name":"Bug","is_enabled":true},{"name":"Feature","is_enabled":true}]`
	liveFields = `[{"name":"Workflow","data_type":"single_select","options":[{"name":"Ready"},{"name":"Done"}]},
	               {"name":"Target date","data_type":"date"}]`
)

type harness struct {
	env       *cli.Env
	stdout    *bytes.Buffer
	stderr    *bytes.Buffer
	transport *ghtest.Transport
	root      string
}

// newHarness builds a consumer checkout carrying the delivered artifacts at their
// payload locations and runs the command from a nested directory, so a passing run
// proves zero-argument default resolution rather than a lucky working directory.
func newHarness(t *testing.T, schema, policyBody string) *harness {
	t.Helper()

	root := t.TempDir()
	write := func(rel, body string) {
		path := filepath.Join(root, rel)
		if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
			t.Fatalf("MkdirAll(%s) error = %v", path, err)
		}
		if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
			t.Fatalf("WriteFile(%s) error = %v", path, err)
		}
	}
	if schema != "" {
		write(cli.DefaultSchemaPath, schema)
	}
	if policyBody != "" {
		write(cli.DefaultPolicyPath, policyBody)
	}

	workDir := filepath.Join(root, "docs", "nested")
	if err := os.MkdirAll(workDir, 0o750); err != nil {
		t.Fatalf("MkdirAll(%s) error = %v", workDir, err)
	}

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET /orgs/" + fixtureOrg + "/issue-types":  {Status: http.StatusOK, Body: liveTypes},
		"GET /orgs/" + fixtureOrg + "/issue-fields": {Status: http.StatusOK, Body: liveFields},
	}}
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}

	return &harness{
		env: &cli.Env{
			Stdout:    stdout,
			Stderr:    stderr,
			WorkDir:   workDir,
			Tokens:    ghtest.TokenSource{Value: fixtureToken},
			Transport: transport,
			BaseURL:   fixtureBase,
		},
		stdout:    stdout,
		stderr:    stderr,
		transport: transport,
		root:      root,
	}
}

func (h *harness) run(args ...string) int {
	return cli.Run(context.Background(), h.env, append([]string{"audit"}, args...))
}

func TestAuditZeroArgumentRun(t *testing.T) {
	t.Parallel()

	h := newHarness(t, fixtureSchema, fixturePolicy)

	if got := h.run(); got != cli.ExitOK {
		t.Fatalf("audit = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	out := h.stdout.String()
	for _, want := range []string{fixtureOrg, "Issue types", "Issue fields", "Bug", "Workflow", "match"} {
		if !strings.Contains(out, want) {
			t.Errorf("human output missing %q:\n%s", want, out)
		}
	}
	if strings.Contains(out, fixtureToken) || strings.Contains(h.stderr.String(), fixtureToken) {
		t.Error("output contains the token value; IR-002 forbids credential material in output")
	}
	for _, method := range h.transport.Methods() {
		if method != http.MethodGet {
			t.Errorf("audit issued a %s request; organization access must stay read-only", method)
		}
	}
}

func TestAuditJSONOutput(t *testing.T) {
	t.Parallel()

	h := newHarness(t, fixtureSchema, fixturePolicy)

	if got := h.run("--output", "json"); got != cli.ExitOK {
		t.Fatalf("audit --output json = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	var decoded struct {
		Organization string `json:"organization"`
		Findings     []struct {
			Kind   string `json:"kind"`
			Status string `json:"status"`
			Name   string `json:"name"`
		} `json:"findings"`
		Counts struct {
			Match    int `json:"match"`
			Missing  int `json:"missing"`
			Mismatch int `json:"mismatch"`
			Extra    int `json:"extra"`
		} `json:"counts"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error = %v, output:\n%s", err, h.stdout)
	}
	if decoded.Organization != fixtureOrg {
		t.Errorf("organization = %q, want %q", decoded.Organization, fixtureOrg)
	}
	if len(decoded.Findings) != 4 {
		t.Errorf("findings = %d, want 4", len(decoded.Findings))
	}
	if decoded.Counts.Match != 4 {
		t.Errorf("counts.match = %d, want 4", decoded.Counts.Match)
	}
}

func TestAuditReportsEveryFindingClass(t *testing.T) {
	t.Parallel()

	h := newHarness(t, fixtureSchema+"\n  Severity:\n    type: single_select\n    values:\n      - S0\n", fixturePolicy)
	h.transport.Routes["GET /orgs/"+fixtureOrg+"/issue-types"] = ghtest.Response{
		Status: http.StatusOK,
		Body:   `[{"name":"Bug","is_enabled":true},{"name":"Chore","is_enabled":true}]`,
	}
	h.transport.Routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{
		Status: http.StatusOK,
		Body: `[{"name":"Workflow","data_type":"single_select","options":[{"name":"Ready"}]},
		        {"name":"Target date","data_type":"date"}]`,
	}

	if got := h.run("--output", "json"); got != cli.ExitOK {
		t.Fatalf("audit = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	var decoded struct {
		Counts struct {
			Match    int `json:"match"`
			Missing  int `json:"missing"`
			Mismatch int `json:"mismatch"`
			Extra    int `json:"extra"`
		} `json:"counts"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error = %v", err)
	}
	if decoded.Counts.Match == 0 || decoded.Counts.Missing == 0 || decoded.Counts.Mismatch == 0 || decoded.Counts.Extra == 0 {
		t.Errorf("counts = %+v, want every finding class represented", decoded.Counts)
	}
}

func TestAuditFailOnDrift(t *testing.T) {
	t.Parallel()

	h := newHarness(t, fixtureSchema, fixturePolicy)
	h.transport.Routes["GET /orgs/"+fixtureOrg+"/issue-types"] = ghtest.Response{Status: http.StatusOK, Body: `[]`}

	if got := h.run("--fail-on-drift"); got != cli.ExitFailure {
		t.Fatalf("audit --fail-on-drift = %d, want %d", got, cli.ExitFailure)
	}
	// Drift is a completed audit, not a precondition failure: the report is still owed.
	if h.stdout.Len() == 0 {
		t.Error("stdout is empty; a completed audit must still print its findings")
	}
}

// FR-016: unmet preconditions exit nonzero and emit no partial report. Each case below
// is a distinct precondition, and stdout must stay empty in every one of them.
func TestAuditPreconditionFailures(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		setup   func(t *testing.T) *harness
		args    []string
		wantSub string
	}{
		{
			name: "gh is unauthenticated",
			setup: func(t *testing.T) *harness {
				h := newHarness(t, fixtureSchema, fixturePolicy)
				h.env.Tokens = ghtest.TokenSource{Err: errors.New("gh is not authenticated")}
				return h
			},
			wantSub: "authenticated",
		},
		{
			name: "api is unreachable",
			setup: func(t *testing.T) *harness {
				h := newHarness(t, fixtureSchema, fixturePolicy)
				h.transport.Err = errors.New("dial tcp: no such host")
				return h
			},
			wantSub: "unreachable",
		},
		{
			name: "api rejects the credentials",
			setup: func(t *testing.T) *harness {
				h := newHarness(t, fixtureSchema, fixturePolicy)
				h.transport.Routes["GET /orgs/"+fixtureOrg+"/issue-types"] = ghtest.Response{
					Status: http.StatusUnauthorized, Body: `{"message":"Bad credentials"}`,
				}
				return h
			},
			wantSub: "401",
		},
		{
			name:    "schema file is absent",
			setup:   func(t *testing.T) *harness { return newHarness(t, "", fixturePolicy) },
			wantSub: cli.DefaultSchemaPath,
		},
		{
			name: "schema file is malformed",
			setup: func(t *testing.T) *harness {
				return newHarness(t, "issue_types:\n  - Bug\nbogus_key: 1\n", fixturePolicy)
			},
			wantSub: "bogus_key",
		},
		{
			name:    "policy file is absent",
			setup:   func(t *testing.T) *harness { return newHarness(t, fixtureSchema, "") },
			wantSub: cli.DefaultPolicyPath,
		},
		{
			name:    "policy file is malformed",
			setup:   func(t *testing.T) *harness { return newHarness(t, fixtureSchema, "package_version = \"1.0\"\n") },
			wantSub: "organization",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			h := tc.setup(t)

			if got := h.run(tc.args...); got != cli.ExitFailure {
				t.Fatalf("audit = %d, want %d (stderr: %s)", got, cli.ExitFailure, h.stderr)
			}
			if h.stdout.Len() != 0 {
				t.Errorf("stdout = %q, want no partial report on a precondition failure", h.stdout)
			}
			if !strings.Contains(h.stderr.String(), tc.wantSub) {
				t.Errorf("stderr = %q, want it to mention %q", h.stderr, tc.wantSub)
			}
		})
	}
}

// Negative control for PV-T4-001: a transport that always fails must not yield a report.
func TestAuditFailingTransportEmitsNoReport(t *testing.T) {
	t.Parallel()

	for _, mode := range []string{"human", "json"} {
		t.Run(mode, func(t *testing.T) {
			t.Parallel()
			h := newHarness(t, fixtureSchema, fixturePolicy)
			h.transport.Err = errors.New("connection refused")

			if got := h.run("--output", mode); got == cli.ExitOK {
				t.Fatalf("audit --output %s = %d, want a nonzero exit", mode, got)
			}
			if h.stdout.Len() != 0 {
				t.Errorf("stdout = %q, want it empty", h.stdout)
			}
		})
	}
}

func TestAuditUsageErrors(t *testing.T) {
	t.Parallel()

	cases := [][]string{
		{"--output", "yaml"},
		{"--nope"},
		{"stray-argument"},
	}
	for _, args := range cases {
		t.Run(strings.Join(args, " "), func(t *testing.T) {
			t.Parallel()
			h := newHarness(t, fixtureSchema, fixturePolicy)

			if got := h.run(args...); got != cli.ExitUsage {
				t.Errorf("audit %v = %d, want %d", args, got, cli.ExitUsage)
			}
			if h.stdout.Len() != 0 {
				t.Errorf("stdout = %q, want it empty on a usage error", h.stdout)
			}
		})
	}
}

// --org lets an operator audit without a rendered policy; --schema overrides the
// delivered baseline. Both must bypass default resolution entirely.
func TestAuditExplicitFlagsBypassDefaults(t *testing.T) {
	t.Parallel()

	h := newHarness(t, "", "")
	schemaPath := filepath.Join(h.root, "custom-schema.yaml")
	if err := os.WriteFile(schemaPath, []byte(fixtureSchema), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	if got := h.run("--schema", schemaPath, "--org", fixtureOrg); got != cli.ExitOK {
		t.Fatalf("audit = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	if !strings.Contains(h.stdout.String(), fixtureOrg) {
		t.Errorf("stdout = %q, want the audited organization", h.stdout)
	}
}
