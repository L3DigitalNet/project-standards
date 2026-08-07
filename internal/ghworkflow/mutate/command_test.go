package mutate_test

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"

	// The five subcommands register themselves; importing the package under test is what
	// wires them into the registry, exactly as cmd/gh-workflow does.
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/mutate"
)

const (
	fixtureToken = "gho_fixturetokenvalue"
	fixtureBase  = "https://api.github.test"
	fixtureOrg   = "L3DigitalNet"
	fixtureRepo  = "/repos/L3DigitalNet/example-repo"

	fixturePolicy = "organization = \"L3DigitalNet\"\npackage_version = \"1.0\"\n"
	fixtureGit    = "[core]\n\trepositoryformatversion = 0\n[remote \"origin\"]\n\t" +
		"url = git@github.com:L3DigitalNet/example-repo.git\n"
)

// fixtureSchema reproduces the delivered org-schema.yaml: it is the oracle every
// validation refusal is measured against, so a trimmed copy would prove less than the
// tool actually promises (spec EC-008 requires the refusal to list the real value set).
const fixtureSchema = `issue_types:
  - Bug
  - Feature
  - Task
  - Initiative
  - Research

issue_fields:
  Workflow:
    type: single_select
    values:
      - Inbox
      - Needs definition
      - Ready
      - In progress
      - Blocked
      - In review
      - Done
      - Dropped

  Priority:
    type: single_select
    values:
      - P0 — Immediate
      - P1 — Next
      - P2 — Planned
      - P3 — Opportunistic
      - P4 — Someday

  Size:
    type: single_select
    values:
      - XS
      - S
      - M
      - L
      - XL

  Change risk:
    type: single_select
    values:
      - R1 — Low
      - R2 — Moderate
      - R3 — High
      - R4 — Critical

  Execution mode:
    type: single_select
    values:
      - Unattended agent
      - Interactive agent
      - Human only

  Target date:
    type: date

  Severity:
    type: single_select
    values:
      - S0 — Critical
      - S1 — High
      - S2 — Moderate
      - S3 — Low
`

// The organization's live Issue Fields carry the numeric ids every write is addressed
// by; the names are the operator-facing handles the subcommands accept.
const fixtureOrgFields = `[
	{"id":101,"name":"Workflow","data_type":"single_select","options":[{"name":"Ready"},{"name":"Done"}]},
	{"id":102,"name":"Priority","data_type":"single_select","options":[{"name":"P1 — Next"}]},
	{"id":103,"name":"Size","data_type":"single_select","options":[{"name":"M"}]},
	{"id":104,"name":"Change risk","data_type":"single_select","options":[{"name":"R2 — Moderate"}]},
	{"id":105,"name":"Execution mode","data_type":"single_select","options":[{"name":"Interactive agent"}]},
	{"id":106,"name":"Target date","data_type":"date","options":[]},
	{"id":107,"name":"Severity","data_type":"single_select","options":[{"name":"S2 — Moderate"}]}
]`

// issueReady satisfies every Ready precondition; issueNotReady fails all four at once, so
// one fixture pair drives both directions of every `check` class.
const issueReady = `{"number":12,"title":"Ledger write leaves a partial file",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/12",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nA failed refresh must not damage the file.\n\n## Acceptance criteria\n\n- Prior bytes survive.\n",
	"type":{"name":"Bug"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"In progress","single_select_option":{"name":"In progress"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}},
		{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
		{"issue_field_name":"Change risk","data_type":"single_select","value":"R2 — Moderate","single_select_option":{"name":"R2 — Moderate"}},
		{"issue_field_name":"Execution mode","data_type":"single_select","value":"Interactive agent","single_select_option":{"name":"Interactive agent"}},
		{"issue_field_name":"Severity","data_type":"single_select","value":"S2 — Moderate","single_select_option":{"name":"S2 — Moderate"}}]}`

const issueNotReady = `{"number":14,"title":"Add ledger TOC anchors",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/14",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nNavigate the ledger.\n",
	"type":{"name":"Feature"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Needs definition","single_select_option":{"name":"Needs definition"}},
		{"issue_field_name":"Size","data_type":"single_select","value":"XL","single_select_option":{"name":"XL"}}]}`

// issueClosed is the converged terminal state: closed as completed with Workflow = Done.
const issueClosed = `{"number":16,"title":"Freeze the CLI surface",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/16",
	"state":"closed","state_reason":"completed",
	"body":"## Acceptance criteria\n\n- Flags recorded.\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Done","single_select_option":{"name":"Done"}}]}`

const issueCreated = `{"number":31,"title":"Record the frozen flag surface",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/31",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\n## Context\n\n## Scope\n\n## Out of scope\n\n## Acceptance criteria\n\n## Constraints\n\n## Evidence / references\n\n## Verification\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Inbox","single_select_option":{"name":"Inbox"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}}]}`

// call is one recorded HTTP request including its body, which the ghtest transport does
// not retain: proving "validation precedes any mutating call" needs the payload, not just
// the method and path.
type call struct {
	Method string
	Path   string
	Body   string
}

// recorder wraps the shared fake transport to capture request bodies before they are
// consumed by the client.
type recorder struct {
	inner *ghtest.Transport

	mu    sync.Mutex
	calls []call
}

func (r *recorder) RoundTrip(req *http.Request) (*http.Response, error) {
	body := ""
	if req.Body != nil {
		raw, err := io.ReadAll(req.Body)
		if err != nil {
			return nil, err
		}
		body = string(raw)
		req.Body = io.NopCloser(bytes.NewReader(raw))
	}
	r.mu.Lock()
	r.calls = append(r.calls, call{Method: req.Method, Path: req.URL.Path, Body: body})
	r.mu.Unlock()
	return r.inner.RoundTrip(req)
}

func (r *recorder) recorded() []call {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]call(nil), r.calls...)
}

// mutations returns every non-GET request, which is the set spec EC-008 requires to be
// empty when a value is refused.
func (r *recorder) mutations() []call {
	var writes []call
	for _, c := range r.recorded() {
		if c.Method != http.MethodGet {
			writes = append(writes, c)
		}
	}
	return writes
}

type harness struct {
	env       *cli.Env
	stdout    *bytes.Buffer
	stderr    *bytes.Buffer
	transport *recorder
	routes    map[string]ghtest.Response
}

// newHarness builds a consumer checkout carrying the delivered artifacts and an origin
// remote, then runs from a nested directory so a zero-argument run proves upward
// resolution (IR-004) rather than a lucky working directory.
func newHarness(t *testing.T) *harness {
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
	write(cli.DefaultPolicyPath, fixturePolicy)
	write(cli.DefaultSchemaPath, fixtureSchema)
	write(".git/config", fixtureGit)

	workDir := filepath.Join(root, "docs", "nested")
	if err := os.MkdirAll(workDir, 0o750); err != nil {
		t.Fatalf("MkdirAll(%s) error = %v", workDir, err)
	}

	routes := map[string]ghtest.Response{
		"GET /orgs/" + fixtureOrg + "/issue-fields":                 {Status: http.StatusOK, Body: fixtureOrgFields},
		"GET " + fixtureRepo + "/issues/12":                         {Status: http.StatusOK, Body: issueReady},
		"GET " + fixtureRepo + "/issues/14":                         {Status: http.StatusOK, Body: issueNotReady},
		"GET " + fixtureRepo + "/issues/16":                         {Status: http.StatusOK, Body: issueClosed},
		"GET " + fixtureRepo + "/issues/31":                         {Status: http.StatusOK, Body: issueCreated},
		"GET " + fixtureRepo + "/issues/12/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/16/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/14/dependencies/blocked_by": {Status: http.StatusOK,
			Body: `[{"number":9,"title":"Land the transport","state":"open",
				"html_url":"https://github.com/L3DigitalNet/example-repo/issues/9"}]`},
		"POST " + fixtureRepo + "/issues":                       {Status: http.StatusCreated, Body: issueCreated},
		"POST " + fixtureRepo + "/issues/12/issue-field-values": {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/14/issue-field-values": {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/16/issue-field-values": {Status: http.StatusOK, Body: "[]"},
		"PATCH " + fixtureRepo + "/issues/12":                   {Status: http.StatusOK, Body: issueReady},
		"PATCH " + fixtureRepo + "/issues/14":                   {Status: http.StatusOK, Body: issueNotReady},
		"PATCH " + fixtureRepo + "/issues/16":                   {Status: http.StatusOK, Body: issueClosed},
	}
	transport := &recorder{inner: &ghtest.Transport{Routes: routes}}

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
		routes:    routes,
	}
}

func (h *harness) run(args ...string) int {
	return cli.Run(context.Background(), h.env, args)
}

func (h *harness) reset() {
	h.stdout.Reset()
	h.stderr.Reset()
	h.transport.mu.Lock()
	h.transport.calls = nil
	h.transport.mu.Unlock()
}

// assertNoMutations is the EC-008 oracle: a refused mutation changes nothing remotely.
func (h *harness) assertNoMutations(t *testing.T) {
	t.Helper()
	if writes := h.transport.mutations(); len(writes) != 0 {
		t.Errorf("refusal issued %d mutating request(s): %+v; nothing may change on GitHub", len(writes), writes)
	}
}

func (h *harness) assertNoRequests(t *testing.T) {
	t.Helper()
	if calls := h.transport.recorded(); len(calls) != 0 {
		t.Errorf("a validation refusal reached the network: %+v", calls)
	}
}

func wants(t *testing.T, got string, fragments ...string) {
	t.Helper()
	for _, fragment := range fragments {
		if !strings.Contains(got, fragment) {
			t.Errorf("output is missing %q; got:\n%s", fragment, got)
		}
	}
}

// ---------------------------------------------------------------- set

func TestSetRefusesAnInvalidValueAndListsTheValidSet(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Priority=Urgent"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `"Urgent" is not a valid Priority value`,
		"P0 — Immediate", "P1 — Next", "P2 — Planned", "P3 — Opportunistic", "P4 — Someday")
	if h.stdout.Len() != 0 {
		t.Errorf("a refusal wrote to stdout: %s", h.stdout)
	}
	h.assertNoRequests(t)
	h.assertNoMutations(t)
}

func TestSetRefusesAnUnknownFieldAndListsTheSchemaFields(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Effort=3"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `unknown Issue Field "Effort"`, "Workflow", "Severity")
	h.assertNoRequests(t)
}

func TestSetRefusesAnInvalidTargetDate(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Target date=next friday"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "Target date", "YYYY-MM-DD")
	h.assertNoRequests(t)
}

// A terminal Workflow value applied through `set` would create exactly the native/field
// divergence the package exists to prevent, so it is refused and routed to `close`.
func TestSetRefusesATerminalWorkflowValue(t *testing.T) {
	t.Parallel()

	for _, value := range []string{"Done", "Dropped"} {
		h := newHarness(t)
		if code := h.run("set", "--issue", "12", "--field", "Workflow="+value); code != cli.ExitUsage {
			t.Errorf("%s: exit = %d, want %d\nstderr: %s", value, code, cli.ExitUsage, h.stderr)
		}
		wants(t, h.stderr.String(), value, "gh-workflow close")
		h.assertNoRequests(t)
	}
}

func TestSetAppliesValidatedValues(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	code := h.run("set", "--issue", "12", "--field", "Workflow=Ready", "--field", "Priority=P1 — Next")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}

	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	if writes[0].Method != http.MethodPost || writes[0].Path != fixtureRepo+"/issues/12/issue-field-values" {
		t.Errorf("wrote to %s %s, want POST %s/issues/12/issue-field-values",
			writes[0].Method, writes[0].Path, fixtureRepo)
	}

	var payload struct {
		Values []struct {
			FieldID int64  `json:"field_id"`
			Value   string `json:"value"`
		} `json:"issue_field_values"`
	}
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
	}
	got := map[int64]string{}
	for _, value := range payload.Values {
		got[value.FieldID] = value.Value
	}
	if got[101] != "Ready" || got[102] != "P1 — Next" {
		t.Errorf("field assignments = %v, want {101:Ready 102:P1 — Next}", got)
	}
	wants(t, h.stdout.String(), "#12", "Workflow = Ready", "Priority = P1 — Next")
}

func TestSetRequiresAnIssueAndAtLeastOneField(t *testing.T) {
	t.Parallel()

	for name, args := range map[string][]string{
		"no issue": {"set", "--field", "Workflow=Ready"},
		"no field": {"set", "--issue", "12"},
		"no pair":  {"set", "--issue", "12", "--field", "Workflow"},
	} {
		h := newHarness(t)
		if code := h.run(args...); code != cli.ExitUsage {
			t.Errorf("%s: exit = %d, want %d\nstderr: %s", name, code, cli.ExitUsage, h.stderr)
		}
		h.assertNoMutations(t)
	}
}

// ---------------------------------------------------------------- new

func TestNewScaffoldsTheCanonicalBodyAndPrintsTheReceipt(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	code := h.run("new", "--type", "Task", "--title", "Record the frozen flag surface",
		"--field", "Workflow=Inbox", "--field", "Priority=P1 — Next")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}

	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	if writes[0].Method != http.MethodPost || writes[0].Path != fixtureRepo+"/issues" {
		t.Errorf("created via %s %s, want POST %s/issues", writes[0].Method, writes[0].Path, fixtureRepo)
	}

	var payload struct {
		Title  string `json:"title"`
		Body   string `json:"body"`
		Type   string `json:"type"`
		Values []struct {
			FieldID int64  `json:"field_id"`
			Value   string `json:"value"`
		} `json:"issue_field_values"`
	}
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
	}
	if payload.Title != "Record the frozen flag surface" || payload.Type != "Task" {
		t.Errorf("title/type = %q/%q", payload.Title, payload.Type)
	}
	for _, heading := range []string{
		"## Outcome", "## Context", "## Scope", "## Out of scope",
		"## Acceptance criteria", "## Constraints", "## Evidence / references", "## Verification",
	} {
		if !strings.Contains(payload.Body, heading) {
			t.Errorf("scaffolded body is missing the canonical heading %q:\n%s", heading, payload.Body)
		}
	}
	if len(payload.Values) != 2 {
		t.Errorf("initial field values = %+v, want two", payload.Values)
	}

	// The receipt is the creation surface's whole point: it must name the item and end
	// with the gaps line rather than reporting a bare success.
	wants(t, h.stdout.String(), "Created issue #31", "Record the frozen flag surface",
		"https://github.com/L3DigitalNet/example-repo/issues/31", "Workflow: Inbox", "Gaps: ")
}

func TestNewWithABodyFileUsesTheAuthoredBody(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	path := filepath.Join(t.TempDir(), "body.md")
	authored := "## Outcome\n\nThe flag surface is recorded.\n\n## Acceptance criteria\n\n- OQ-002 answered.\n"
	if err := os.WriteFile(path, []byte(authored), 0o600); err != nil {
		t.Fatalf("WriteFile error = %v", err)
	}

	if code := h.run("new", "--type", "Task", "--title", "Record the frozen flag surface",
		"--body-file", path); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	var payload struct {
		Body string `json:"body"`
	}
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v", err)
	}
	if payload.Body != authored {
		t.Errorf("body = %q, want the authored body verbatim", payload.Body)
	}
}

func TestNewRefusesAnUnknownIssueType(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("new", "--type", "Chore", "--title", "x"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `unknown Issue Type "Chore"`, "Bug", "Feature", "Task", "Initiative", "Research")
	h.assertNoRequests(t)
}

func TestNewRefusesAnInvalidInitialFieldValue(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("new", "--type", "Task", "--title", "x", "--field", "Size=Huge"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `"Huge" is not a valid Size value`, "XS", "XL")
	h.assertNoRequests(t)
}

func TestNewEmitsTheReceiptAsJSON(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("new", "--type", "Task", "--title", "Record the frozen flag surface",
		"--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	var report struct {
		Item struct {
			Number int               `json:"number"`
			Kind   string            `json:"kind"`
			Fields map[string]string `json:"fields"`
		} `json:"item"`
		Gaps []string `json:"gaps"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &report); err != nil {
		t.Fatalf("stdout is not the receipt report: %v\n%s", err, h.stdout)
	}
	if report.Item.Number != 31 || report.Item.Kind != "issue" {
		t.Errorf("item = %+v, want issue #31", report.Item)
	}
	if report.Gaps == nil {
		t.Error("the JSON receipt omits the gaps list; it is never optional")
	}
}

// ---------------------------------------------------------------- close / reopen

// FR-021 fixes the order: the native state change with its close reason first, then the
// Workflow field. Asserting the recorded sequence is what makes the order a contract.
func TestCloseAppliesTheOrderedTerminalSequence(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		as       string
		reason   string
		workflow string
	}{
		{as: "done", reason: "completed", workflow: "Done"},
		{as: "dropped", reason: "not_planned", workflow: "Dropped"},
	} {
		h := newHarness(t)
		if code := h.run("close", "--issue", "12", "--as", tc.as); code != cli.ExitOK {
			t.Fatalf("%s: exit = %d, want 0\nstderr: %s", tc.as, code, h.stderr)
		}

		writes := h.transport.mutations()
		if len(writes) != 2 {
			t.Fatalf("%s: want two mutating requests, got %+v", tc.as, writes)
		}
		if writes[0].Method != http.MethodPatch || writes[0].Path != fixtureRepo+"/issues/12" {
			t.Errorf("%s: first write = %s %s, want the native state change first",
				tc.as, writes[0].Method, writes[0].Path)
		}
		wants(t, writes[0].Body, `"state":"closed"`, `"state_reason":"`+tc.reason+`"`)
		if writes[1].Method != http.MethodPost || writes[1].Path != fixtureRepo+"/issues/12/issue-field-values" {
			t.Errorf("%s: second write = %s %s, want the Workflow field second",
				tc.as, writes[1].Method, writes[1].Path)
		}
		wants(t, writes[1].Body, tc.workflow)
		wants(t, h.stdout.String(), "#12", tc.reason, tc.workflow)
	}
}

// A failure between the two steps is the case FR-021 exists for: the tool must name the
// exact divergence rather than reporting either success or a bare error.
func TestClosePartialFailureReportsTheDivergentState(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["POST "+fixtureRepo+"/issues/12/issue-field-values"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	wants(t, h.stderr.String(),
		"#12",               // which item diverged
		"closed",            // the native state that did change
		"completed",         // with which close reason
		"In progress",       // the Workflow value that did not change
		"Done",              // the value it should carry
		"gh-workflow close") // the corrective retry
	if h.stdout.Len() != 0 {
		t.Errorf("a partial failure reported success on stdout: %s", h.stdout)
	}
}

func TestCloseRerunConvergesAfterAPartialFailure(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["POST "+fixtureRepo+"/issues/12/issue-field-values"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}
	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitFailure {
		t.Fatalf("first run exit = %d, want %d", code, cli.ExitFailure)
	}

	// The corrective retry: the same invocation, once the transient failure clears.
	h.reset()
	h.routes["POST "+fixtureRepo+"/issues/12/issue-field-values"] = ghtest.Response{
		Status: http.StatusOK, Body: "[]"}
	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitOK {
		t.Fatalf("rerun exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 2 {
		t.Fatalf("the rerun must replay the whole sequence, got %+v", writes)
	}
	wants(t, h.stdout.String(), "#12", "Done")
}

// When the first step fails there is nothing to diverge: the Workflow field must not be
// touched at all.
func TestCloseLeavesTheWorkflowFieldAloneWhenTheStateChangeFails(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["PATCH "+fixtureRepo+"/issues/12"] = ghtest.Response{
		Status: http.StatusForbidden, Body: `{"message":"Forbidden"}`}

	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	for _, write := range h.transport.mutations() {
		if strings.HasSuffix(write.Path, "/issue-field-values") {
			t.Errorf("the Workflow field was written after the state change failed: %+v", write)
		}
	}
}

// A converged issue is already in the requested terminal state, so the rerun that proves
// convergence must not write again.
func TestCloseIsANoOpWhenAlreadyConverged(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("close", "--issue", "16", "--as", "done"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	h.assertNoMutations(t)
	wants(t, h.stdout.String(), "#16", "Done")
}

func TestCloseRefusesAnUnknownTerminal(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("close", "--issue", "12", "--as", "abandoned"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "done", "dropped")
	h.assertNoRequests(t)
}

func TestReopenRestoresANonterminalWorkflowValue(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("reopen", "--issue", "16", "--workflow", "In progress"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 2 {
		t.Fatalf("want two mutating requests, got %+v", writes)
	}
	if writes[0].Method != http.MethodPatch {
		t.Errorf("first write = %s, want the native state change first", writes[0].Method)
	}
	wants(t, writes[0].Body, `"state":"open"`, `"state_reason":"reopened"`)
	wants(t, writes[1].Body, "In progress")
	wants(t, h.stdout.String(), "#16", "In progress")
}

func TestReopenRefusesATerminalWorkflowValue(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("reopen", "--issue", "16", "--workflow", "Done"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "Done", "nonterminal")
	h.assertNoRequests(t)
}

func TestReopenRefusesAValueOutsideTheSchema(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("reopen", "--issue", "16", "--workflow", "Started"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `"Started" is not a valid Workflow value`, "Inbox", "In review")
	h.assertNoRequests(t)
}

// ---------------------------------------------------------------- check

func TestCheckPassesAnEligibleIssueAndItemizesEveryClass(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "12"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	wants(t, h.stdout.String(), "pinned-fields", "acceptance-criteria", "blocking-dependencies", "size")
	for _, c := range h.transport.recorded() {
		if c.Method != http.MethodGet {
			t.Errorf("check issued a %s request; it is read-only", c.Method)
		}
	}
}

func TestCheckItemizesEveryUnmetPrecondition(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "14"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	// Every class is reported, and each unmet one names what is actually missing.
	wants(t, h.stdout.String(),
		"pinned-fields", "Priority",
		"acceptance-criteria",
		"blocking-dependencies", "#9",
		"size", "XL")
	h.assertNoMutations(t)
}

func TestCheckEmitsJSON(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "14", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	var report struct {
		Repository string `json:"repository"`
		Issue      int    `json:"issue"`
		Eligible   bool   `json:"eligible"`
		Findings   []struct {
			Class  string `json:"class"`
			Status string `json:"status"`
			Detail string `json:"detail"`
		} `json:"findings"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &report); err != nil {
		t.Fatalf("stdout is not the check report: %v\n%s", err, h.stdout)
	}
	if report.Issue != 14 || report.Eligible {
		t.Errorf("report = %+v, want issue 14 ineligible", report)
	}
	classes := map[string]string{}
	for _, finding := range report.Findings {
		classes[finding.Class] = finding.Status
	}
	for _, class := range []string{"pinned-fields", "acceptance-criteria", "blocking-dependencies", "size"} {
		if classes[class] != "blocked" {
			t.Errorf("class %q status = %q, want blocked", class, classes[class])
		}
	}
}

func TestCheckRequiresAnIssueNumber(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
}

// ---------------------------------------------------------------- shared surface

// Every subcommand resolves its repository, policy, and schema from the checkout, so a
// run carrying nothing but the issue number must work from a nested directory (IR-004).
func TestZeroArgumentResolutionFromANestedDirectory(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Workflow=Ready"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
}

func TestUnknownOutputModeIsAUsageError(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "12", "--output", "yaml"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
}

func TestSubcommandsRejectPositionalArguments(t *testing.T) {
	t.Parallel()

	for _, name := range []string{"new", "set", "close", "reopen", "check"} {
		h := newHarness(t)
		if code := h.run(name, "12"); code != cli.ExitUsage {
			t.Errorf("%s: exit = %d, want %d\nstderr: %s", name, code, cli.ExitUsage, h.stderr)
		}
	}
}
