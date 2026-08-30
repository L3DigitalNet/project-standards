package mutate_test

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"

	// The subcommands register themselves; importing the package under test is what
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

// issueDatelessTask is the #192 shape: a Task carrying every field its Type pins except
// `Target date`, which the package's own field-vocabulary reference calls a valid and
// expected empty state. Through payload 1.4 `check` refused it, so the issue was
// admitted to Ready with `set` instead — the gate sent an agent around itself.
const issueDatelessTask = `{"number":22,"title":"Cut the payload",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/22",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nShip it.\n\n## Acceptance criteria\n\n- Digests wired.\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"In progress","single_select_option":{"name":"In progress"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}},
		{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
		{"issue_field_name":"Change risk","data_type":"single_select","value":"R2 — Moderate","single_select_option":{"name":"R2 — Moderate"}},
		{"issue_field_name":"Execution mode","data_type":"single_select","value":"Interactive agent","single_select_option":{"name":"Interactive agent"}}]}`

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

// issueDropped is closed for the other reason: reclassifying it with `close --as done` is
// the one terminal transition GitHub will not honor as a single PATCH.
const issueDropped = `{"number":18,"title":"Retire the legacy summary surface",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/18",
	"state":"closed","state_reason":"not_planned",
	"body":"## Acceptance criteria\n\n- The surface is gone.\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Dropped","single_select_option":{"name":"Dropped"}}]}`

const issueCreated = `{"number":31,"title":"Record the frozen flag surface",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/31",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\n## Context\n\n## Scope\n\n## Out of scope\n\n## Acceptance criteria\n\n## Constraints\n\n## Evidence / references\n\n## Verification\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Inbox","single_select_option":{"name":"Inbox"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}}]}`

// issueUntyped carries a null type, which is what GitHub stores for an issue opened
// anywhere the Issue Type is optional — the web UI, or any tool that omits it. It is the
// state `set --type` exists to leave, and the only one that exercises an absent type on
// both sides of the read-back.
const issueUntyped = `{"number":20,"title":"Triage the untyped backlog",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/20",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nEverything carries a Type.\n",
	"type":null,
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Inbox","single_select_option":{"name":"Inbox"}}]}`

// issueOpenTerminalWorkflow is the lifecycle divergence FR-021 exists to prevent, seen
// from the Ready side: the issue is natively open, so the native-state class passes, while
// its Workflow already says the work is finished. It carries every other Ready
// precondition so the run isolates the one incoherent class.
const issueOpenTerminalWorkflow = `{"number":24,"title":"Retire the shim",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/24",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nThe shim is gone.\n\n## Acceptance criteria\n\n- No caller references it.\n",
	"type":{"name":"Task"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"Done","single_select_option":{"name":"Done"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}},
		{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
		{"issue_field_name":"Change risk","data_type":"single_select","value":"R2 — Moderate","single_select_option":{"name":"R2 — Moderate"}},
		{"issue_field_name":"Execution mode","data_type":"single_select","value":"Interactive agent","single_select_option":{"name":"Interactive agent"}}]}`

// pullShapedIssue is what `GET /issues/{n}` returns for a pull request: the issues
// endpoint serves both, and only the `pull_request` member tells them apart (DEV-023).
// Everything else here is deliberately Issue-shaped, so a route that skipped the shape
// read would produce a plausible-looking verdict about the wrong object.
const pullShapedIssue = `{"number":26,"title":"Add the render engine",
	"html_url":"https://github.com/L3DigitalNet/example-repo/pull/26",
	"state":"open","state_reason":null,
	"body":"## Acceptance criteria\n\n- It renders.\n",
	"type":null,
	"pull_request":{"url":"https://api.github.test/repos/L3DigitalNet/example-repo/pulls/26"},
	"issue_field_values":[]}`

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

// patchModel reproduces the two pieces of GitHub's `PATCH /issues/{n}` semantics the
// mutation surface depends on: state_reason is applied only when the state itself
// changes, and a `type` sent without push access to the repository is dropped. Both no-ops
// still answer 200. A fake that echoed the request back instead would report an in-place
// reclassification, or a dropped type, as applied — the exact answers the tool must not
// believe, and therefore the ones this suite has to be able to produce.
//
// The type behavior is GitHub's documented contract, not an inferred one: the `type` body
// parameter of "Update an issue" states that "only users with push access can set the type
// for issues" and that "without push access to the repository, type changes are silently
// dropped" (docs.github.com/en/rest/issues/issues, read 2026-08-08).
type patchModel struct {
	mu     sync.Mutex
	issues map[int]map[string]any

	// dropTypeChanges makes this fake answer as GitHub does for a token without push
	// access: 200, and the type left as it was. Read under the same lock as issues so a
	// test may flip it between calls.
	dropTypeChanges bool
}

func newPatchModel(t *testing.T, bodies map[int]string) *patchModel {
	t.Helper()

	model := &patchModel{issues: make(map[int]map[string]any, len(bodies))}
	for number, body := range bodies {
		var decoded map[string]any
		if err := json.Unmarshal([]byte(body), &decoded); err != nil {
			t.Fatalf("fixture issue %d is not valid JSON: %v", number, err)
		}
		model.issues[number] = decoded
	}
	return model
}

func (m *patchModel) apply(number int, body string) (ghtest.Response, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	issue, known := m.issues[number]
	if !known {
		return ghtest.Response{}, false
	}
	var requested struct {
		State  string `json:"state"`
		Reason string `json:"state_reason"`
		Type   string `json:"type"`
	}
	if err := json.Unmarshal([]byte(body), &requested); err != nil {
		return ghtest.Response{Status: http.StatusBadRequest, Body: `{"message":"Invalid request"}`}, true
	}
	if requested.State != "" && requested.State != issue["state"] {
		issue["state"] = requested.State
		issue["state_reason"] = requested.Reason
	}
	if requested.Type != "" && !m.dropTypeChanges {
		issue["type"] = map[string]any{"name": requested.Type}
	}
	encoded, err := json.Marshal(issue)
	if err != nil {
		return ghtest.Response{Status: http.StatusInternalServerError, Body: `{"message":"fixture"}`}, true
	}
	return ghtest.Response{Status: http.StatusOK, Body: string(encoded)}, true
}

// failPatchAfter fails PATCHes to one path once the leading ones have been served.
//
// It exists because a route override cannot express a sequence: registering a failing
// PATCH for an issue fails the reclassifying reopen too, and the branch under test is the
// one reached only when that reopen succeeded and the close after it did not. The failing
// request is short-circuited rather than passed through, so the fake's issue stays in the
// state the reopen left it — open, which is what the message under test has to report.
type failPatchAfter struct {
	inner http.RoundTripper
	path  string
	serve int

	mu   sync.Mutex
	seen int
}

func (f *failPatchAfter) RoundTrip(req *http.Request) (*http.Response, error) {
	if req.Method != http.MethodPatch || req.URL.Path != f.path {
		return f.inner.RoundTrip(req)
	}
	f.mu.Lock()
	f.seen++
	served := f.seen
	f.mu.Unlock()
	if served <= f.serve {
		return f.inner.RoundTrip(req)
	}
	return &http.Response{
		Status:     http.StatusText(http.StatusServiceUnavailable),
		StatusCode: http.StatusServiceUnavailable,
		Header:     http.Header{"Content-Type": []string{"application/json"}},
		Body:       io.NopCloser(strings.NewReader(`{"message":"Service unavailable"}`)),
		Request:    req,
	}, nil
}

// patchedIssue reads the issue number out of a repository-scoped issue path.
func patchedIssue(path string) (int, bool) {
	rest, ok := strings.CutPrefix(path, fixtureRepo+"/issues/")
	if !ok {
		return 0, false
	}
	number, err := strconv.Atoi(rest)
	if err != nil {
		return 0, false
	}
	return number, true
}

type harness struct {
	env       *cli.Env
	root      string
	stdout    *bytes.Buffer
	stderr    *bytes.Buffer
	transport *recorder
	routes    map[string]ghtest.Response
	// patch is the PATCH model, exposed so a test can put GitHub into the states only it
	// can produce — currently a token without push access, which drops type changes.
	patch *patchModel
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
		"GET " + fixtureRepo + "/issues/22":                         {Status: http.StatusOK, Body: issueDatelessTask},
		"GET " + fixtureRepo + "/issues/22/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/31":                         {Status: http.StatusOK, Body: issueCreated},
		"GET " + fixtureRepo + "/issues/12/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/16/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/14/dependencies/blocked_by": {Status: http.StatusOK,
			Body: `[{"number":9,"title":"Land the transport","state":"open",
				"html_url":"https://github.com/L3DigitalNet/example-repo/issues/9"}]`},
		"GET " + fixtureRepo + "/issues/18":                         {Status: http.StatusOK, Body: issueDropped},
		"GET " + fixtureRepo + "/issues/20":                         {Status: http.StatusOK, Body: issueUntyped},
		"GET " + fixtureRepo + "/issues/20/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/24":                         {Status: http.StatusOK, Body: issueOpenTerminalWorkflow},
		"GET " + fixtureRepo + "/issues/24/dependencies/blocked_by": {Status: http.StatusOK, Body: "[]"},
		"GET " + fixtureRepo + "/issues/26":                         {Status: http.StatusOK, Body: pullShapedIssue},
		"POST " + fixtureRepo + "/issues":                           {Status: http.StatusCreated, Body: issueCreated},
		"POST " + fixtureRepo + "/issues/12/issue-field-values":     {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/14/issue-field-values":     {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/16/issue-field-values":     {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/18/issue-field-values":     {Status: http.StatusOK, Body: "[]"},
		"POST " + fixtureRepo + "/issues/20/issue-field-values":     {Status: http.StatusOK, Body: "[]"},
	}

	// PATCH is served by the model rather than by a canned body, so a response reports the
	// state GitHub would actually hold after the request. A test that needs a different
	// answer — a rejection, or a server that drops the write — registers an explicit route,
	// which wins.
	model := newPatchModel(t, map[int]string{
		12: issueReady, 14: issueNotReady, 16: issueClosed, 18: issueDropped, 22: issueDatelessTask,
		20: issueUntyped, 31: issueCreated,
	})
	inner := &ghtest.Transport{Routes: routes}
	inner.RouteFunc = func(req *http.Request) (ghtest.Response, bool) {
		if req.Method != http.MethodPatch {
			return ghtest.Response{}, false
		}
		if _, overridden := routes[req.Method+" "+req.URL.Path]; overridden {
			return ghtest.Response{}, false
		}
		number, ok := patchedIssue(req.URL.Path)
		if !ok {
			return ghtest.Response{}, false
		}
		raw, err := io.ReadAll(req.Body)
		if err != nil {
			return ghtest.Response{}, false
		}
		return model.apply(number, string(raw))
	}
	transport := &recorder{inner: inner}

	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	return &harness{
		root: root,
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
		patch:     model,
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

// write replaces one of the checkout's delivered artifacts, which is how a test covering a
// field type the shipped schema has no example of builds one.
func (h *harness) write(t *testing.T, rel, body string) {
	t.Helper()

	path := filepath.Join(h.root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		t.Fatalf("MkdirAll(%s) error = %v", path, err)
	}
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatalf("WriteFile(%s) error = %v", path, err)
	}
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

// TestSetRefusesEachSingleSelectFieldAndListsItsFullVocabulary proves FR-005's runtime
// vocabulary surface for every field 1.5 stopped restating in field-vocabulary.md
// (Priority, Size, Change risk, Execution mode, Severity): the refusal for an invalid
// value must still name the whole valid set, because that set is no longer written down
// anywhere else an agent reads. Expected values come from parsing fixtureSchema itself,
// not a second hardcoded copy, so the test tracks the schema instead of racing it.
func TestSetRefusesEachSingleSelectFieldAndListsItsFullVocabulary(t *testing.T) {
	t.Parallel()

	schema, err := orgschema.Parse([]byte(fixtureSchema))
	if err != nil {
		t.Fatalf("parsing fixtureSchema: %v", err)
	}

	for _, name := range []string{"Priority", "Size", "Change risk", "Execution mode", "Severity"} {
		name := name
		t.Run(name, func(t *testing.T) {
			t.Parallel()

			field, ok := schema.Field(name)
			if !ok || field.Type != orgschema.TypeSingleSelect {
				t.Fatalf("fixtureSchema has no single_select field named %q", name)
			}

			h := newHarness(t)
			if code := h.run("set", "--issue", "12", "--field", name+"=Not A Real Value"); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
			}
			wants(t, h.stderr.String(), field.Values...)
			h.assertNoRequests(t)
			h.assertNoMutations(t)
		})
	}
}

// TestSetRefusesAnInvalidTargetDateFormat proves the Target date field's refusal states
// its format — the one thing field-vocabulary.md no longer carries for this field, since
// a date has no enumerable value set for a refusal to recite.
func TestSetRefusesAnInvalidTargetDateFormat(t *testing.T) {
	t.Parallel()

	schema, err := orgschema.Parse([]byte(fixtureSchema))
	if err != nil {
		t.Fatalf("parsing fixtureSchema: %v", err)
	}
	if field, ok := schema.Field("Target date"); !ok || field.Type != orgschema.TypeDate {
		t.Fatalf("fixtureSchema's Target date field is not type date: %+v (ok=%v)", field, ok)
	}

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Target date=not-a-date"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "Target date", "YYYY-MM-DD")
	h.assertNoRequests(t)
	h.assertNoMutations(t)
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

func TestSetRequiresAnIssueAndSomethingToWrite(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		args []string
		want []string
	}{
		{name: "no issue", args: []string{"set", "--field", "Workflow=Ready"},
			want: []string{"--issue"}},
		// Neither flag names anything to write, and the refusal has to name both routes:
		// --field alone would send an operator holding an untyped issue back to a raw `gh`
		// call, which is the very thing --type exists to make unnecessary.
		{name: "no field and no type", args: []string{"set", "--issue", "12"},
			want: []string{"--field Name=Value", "--type"}},
		{name: "no pair", args: []string{"set", "--issue", "12", "--field", "Workflow"},
			want: []string{"Name=Value"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			if code := h.run(tc.args...); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
			}
			wants(t, h.stderr.String(), tc.want...)
			h.assertNoMutations(t)
		})
	}
}

// An issue created outside this tool — the web UI leaves the type optional — can only be
// typed here, so a type-only invocation is complete on its own and must reach GitHub as
// the single PATCH that assigns it. Issue 20 is the untyped fixture, which makes this the
// end-to-end run of the case the flag exists for rather than a retype of a typed issue.
func TestSetAssignsAnIssueTypeOnItsOwn(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "20", "--type", "Feature"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}

	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	if writes[0].Method != http.MethodPatch || writes[0].Path != fixtureRepo+"/issues/20" {
		t.Errorf("wrote to %s %s, want PATCH %s/issues/20", writes[0].Method, writes[0].Path, fixtureRepo)
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
	}
	if payload["type"] != "Feature" {
		t.Errorf("request body = %s, want type Feature", writes[0].Body)
	}
	// Nothing else may ride along on the PATCH: the type change must not restate the
	// issue's state, which would make `set` a lifecycle command by accident.
	if len(payload) != 1 {
		t.Errorf("the type write carried more than the type: %s", writes[0].Body)
	}
	wants(t, h.stdout.String(), "#20", "Type = Feature")
}

func TestSetAssignsAnIssueTypeAndFieldsInOneInvocation(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	code := h.run("set", "--issue", "12", "--type", "Feature", "--field", "Workflow=Ready")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}

	writes := h.transport.mutations()
	if len(writes) != 2 {
		t.Fatalf("want exactly two mutating requests, got %+v", writes)
	}
	// The type is written first, so the field values never land against a classification
	// GitHub declined to record.
	if writes[0].Method != http.MethodPatch || writes[0].Path != fixtureRepo+"/issues/12" {
		t.Errorf("first write = %s %s, want the type PATCH", writes[0].Method, writes[0].Path)
	}
	if writes[1].Method != http.MethodPost || writes[1].Path != fixtureRepo+"/issues/12/issue-field-values" {
		t.Errorf("second write = %s %s, want the field POST", writes[1].Method, writes[1].Path)
	}
	wants(t, writes[0].Body, `"type":"Feature"`)
	wants(t, writes[1].Body, `"field_id":101`, `"value":"Ready"`)
	wants(t, h.stdout.String(), "#12", "Type = Feature", "Workflow = Ready")
}

func TestSetRefusesAnUnknownIssueTypeOffline(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--type", "Epic", "--field", "Workflow=Ready"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), `unknown Issue Type "Epic"`,
		"Bug", "Feature", "Task", "Initiative", "Research")
	h.assertNoRequests(t)
	h.assertNoMutations(t)
}

// GitHub drops a type change from a token without push access and answers 200, so the
// status code cannot be the oracle here — the response body is the only evidence the write
// landed. The refusal must name the issue's actual type, and the pending field values must
// not be written on the strength of a classification that never took.
func TestSetReportsATypeChangeGitHubSilentlyDropped(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.patch.dropTypeChanges = true

	if code := h.run("set", "--issue", "12", "--type", "Feature", "--field", "Workflow=Ready"); code != cli.ExitFailure {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	wants(t, h.stderr.String(), `"Bug"`, `"Feature"`, "no field values were written", "push access")
	if h.stdout.Len() != 0 {
		t.Errorf("a dropped write printed a receipt: %s", h.stdout)
	}
	for _, write := range h.transport.mutations() {
		if write.Method == http.MethodPost {
			t.Errorf("field values were written against a type that never took: %+v", write)
		}
	}
}

// The same drop against the untyped fixture, with no fields pending: the refusal has to
// report an absent type as "unset" rather than as empty quotes, and must not claim field
// values were withheld when none were asked for.
func TestSetReportsADroppedTypeOnAnUntypedIssue(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.patch.dropTypeChanges = true

	if code := h.run("set", "--issue", "20", "--type", "Feature"); code != cli.ExitFailure {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	wants(t, h.stderr.String(), "unset", `"Feature"`, "push access")
	if strings.Contains(h.stderr.String(), "no field values were written") {
		t.Errorf("the refusal withheld field values the invocation never requested: %s", h.stderr)
	}
}

// A failed type write is the one outcome the tool cannot characterize: the PATCH may have
// been applied and its answer lost. The message must therefore claim only what is provable
// — that no field values were written — and say the rest is unknown rather than assert an
// untouched issue the operator would then not think to check.
func TestSetDoesNotClaimAnUntouchedIssueWhenTheTypeWriteFails(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["PATCH "+fixtureRepo+"/issues/12"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := h.run("set", "--issue", "12", "--type", "Feature", "--field", "Workflow=Ready"); code != cli.ExitOperational {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, h.stderr)
	}
	wants(t, h.stderr.String(), "#12", "no field values were written", "unknown")
	if strings.Contains(h.stderr.String(), "nothing changed") {
		t.Errorf("the failure claimed an untouched issue it cannot prove: %s", h.stderr)
	}
	for _, write := range h.transport.mutations() {
		if write.Method == http.MethodPost {
			t.Errorf("field values were written after the type write failed: %+v", write)
		}
	}
}

// The one genuinely half-applied outcome: the type landed and the field write that follows
// it failed. The message is the operator's only account of what changed, so it has to name
// the applied type and the rerun that converges.
func TestSetReportsTheAppliedTypeWhenTheFieldWriteFails(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["POST "+fixtureRepo+"/issues/12/issue-field-values"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := h.run("set", "--issue", "12", "--type", "Feature", "--field", "Workflow=Ready"); code != cli.ExitOperational {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, h.stderr)
	}
	wants(t, h.stderr.String(), "#12", "Issue Type is now", `"Feature"`, "rerun")

	writes := h.transport.mutations()
	if len(writes) != 2 {
		t.Fatalf("want the type PATCH followed by the failing field POST, got %+v", writes)
	}
	if writes[0].Method != http.MethodPatch {
		t.Errorf("the type write did not precede the field write: %+v", writes)
	}
}

// A date field is validated but not enumerated, so the accepting branch is a different
// path from every single_select case above and needs its own proof that a valid value
// reaches GitHub in the format the field stores.
func TestSetAppliesAValidTargetDate(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("set", "--issue", "12", "--field", "Target date=2026-01-01"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	wants(t, writes[0].Body, `"field_id":106`, `"value":"2026-01-01"`)
	wants(t, h.stdout.String(), "#12", "Target date = 2026-01-01")
}

// GitHub types Issue Field values, and a number field rejects the string form. Every flag
// value arrives as text, so the conversion is the tool's job; the delivered schema has no
// number field, hence the synthetic one.
func TestSetSendsANumberFieldAsANumber(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: number\n")
	h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":108,"name":"Effort","data_type":"number","options":[]}]`}

	if code := h.run("set", "--issue", "12", "--field", "Effort=3"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	var payload struct {
		Values []struct {
			FieldID int64           `json:"field_id"`
			Value   json.RawMessage `json:"value"`
		} `json:"issue_field_values"`
	}
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
	}
	if len(payload.Values) != 1 || string(payload.Values[0].Value) != "3" {
		t.Errorf("field values = %+v, want the JSON number 3 rather than a string", payload.Values)
	}
}

// GitHub's number fields are JSON numbers, and JSON numbers are arbitrary-precision text:
// routing the operator's digits through a float64 would round anything past 2^53 into a
// different number and write that instead. The digits are validated, not rewritten.
func TestSetPreservesTheDigitsOfALargeNumberField(t *testing.T) {
	t.Parallel()

	const big = "9007199254740993" // 2^53 + 1: the first integer float64 cannot hold.

	h := newHarness(t)
	h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: number\n")
	h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":108,"name":"Effort","data_type":"number","options":[]}]`}

	if code := h.run("set", "--issue", "12", "--field", "Effort="+big); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	writes := h.transport.mutations()
	if len(writes) != 1 {
		t.Fatalf("want exactly one mutating request, got %+v", writes)
	}
	var payload struct {
		Values []struct {
			Value json.RawMessage `json:"value"`
		} `json:"issue_field_values"`
	}
	if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
		t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
	}
	if len(payload.Values) != 1 || string(payload.Values[0].Value) != big {
		t.Errorf("field values = %+v, want the JSON number %s written verbatim", payload.Values, big)
	}
}

// A live number field the baseline schema types otherwise is drift, not operator error:
// the value passed baseline validation, so blaming the invocation sends the operator to
// fix a flag that is already correct. It fails as a precondition, pointing at the audit.
func TestSetReportsDriftWhenTheLiveFieldTypeDisagreesWithTheBaseline(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: text\n")
	h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":108,"name":"Effort","data_type":"number","options":[]}]`}

	if code := h.run("set", "--issue", "12", "--field", "Effort=three"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	wants(t, h.stderr.String(), "Effort", "number", "gh-workflow audit")
	h.assertNoMutations(t)
}

// A non-numeric value for a number field is a mistyped invocation, refused offline like
// every other vocabulary failure (EC-008).
func TestSetRefusesANonNumericNumberField(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: number\n")

	if code := h.run("set", "--issue", "12", "--field", "Effort=three"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "Effort", "number")
	h.assertNoRequests(t)
}

// Go's float syntax is wider than JSON's number grammar: ".5", "5.", "+3", "0x1p-2" and
// "1_000.5" are all valid Go floats and none of them is a valid JSON number, and a quoted
// "3" is a JSON string. Validating with a float parser and encoding as JSON therefore put
// two different oracles on the same value, and the forms only the parser accepted got
// through validation and died at encode time — after the field-identity read had already
// gone out — as an internal error, where EC-008 promises an offline refusal with nothing
// sent. The refusal is measured here by exit code and by silence on the wire.
func TestSetRefusesNumberFormsOutsideTheJSONGrammar(t *testing.T) {
	t.Parallel()

	for _, value := range []string{".5", "5.", "+3", "0x1p-2", "1_000.5", `"3"`} {
		t.Run(value, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: number\n")

			if code := h.run("set", "--issue", "12", "--field", "Effort="+value); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
			}
			wants(t, h.stderr.String(), "Effort", "number")
			h.assertNoRequests(t)
			h.assertNoMutations(t)
		})
	}
}

// The narrower grammar must not narrow what was already valid: every form JSON does
// accept still reaches the write, and reaches it as the operator's own digits.
func TestSetAppliesEveryJSONNumberForm(t *testing.T) {
	t.Parallel()

	for _, value := range []string{"3", "3.5", "-2", "1e3"} {
		t.Run(value, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			h.write(t, cli.DefaultSchemaPath, fixtureSchema+"\n  Effort:\n    type: number\n")
			h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
				Body: `[{"id":108,"name":"Effort","data_type":"number","options":[]}]`}

			if code := h.run("set", "--issue", "12", "--field", "Effort="+value); code != cli.ExitOK {
				t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
			}
			writes := h.transport.mutations()
			if len(writes) != 1 {
				t.Fatalf("want exactly one mutating request, got %+v", writes)
			}
			var payload struct {
				Values []struct {
					Value json.RawMessage `json:"value"`
				} `json:"issue_field_values"`
			}
			if err := json.Unmarshal([]byte(writes[0].Body), &payload); err != nil {
				t.Fatalf("request body is not the documented shape: %v\n%s", err, writes[0].Body)
			}
			if len(payload.Values) != 1 || string(payload.Values[0].Value) != value {
				t.Errorf("field values = %+v, want the JSON number %s written verbatim", payload.Values, value)
			}
		})
	}
}

// A field the baseline defines and the organization does not is drift, not operator error:
// it fails as a precondition, with the message pointing at the audit that explains it
// rather than at the flag the operator typed correctly.
func TestSetReportsSchemaDriftWhenTheOrganizationLacksTheField(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":101,"name":"Workflow","data_type":"single_select","options":[{"name":"Ready"}]}]`}

	if code := h.run("set", "--issue", "12", "--field", "Priority=P1 — Next"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, h.stderr)
	}
	wants(t, h.stderr.String(), fixtureOrg, `"Priority"`, "gh-workflow audit")
	h.assertNoMutations(t)
}

// The repository is resolved three ways and only the origin-remote fallback is covered by
// the zero-argument test; the other two decide which repository is written to.
func TestRepositoryResolutionFromTheRepoFlag(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name    string
		repo    string
		wantOrg string
	}{
		{name: "owner/name is used verbatim", repo: "OtherOrg/other-repo", wantOrg: "OtherOrg"},
		{name: "a bare name is completed from policy", repo: "other-repo", wantOrg: fixtureOrg},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			wantPath := "/repos/" + tc.wantOrg + "/other-repo/issues/12/issue-field-values"
			h.routes["GET /orgs/"+tc.wantOrg+"/issue-fields"] = ghtest.Response{
				Status: http.StatusOK, Body: fixtureOrgFields}
			h.routes["POST "+wantPath] = ghtest.Response{Status: http.StatusOK, Body: "[]"}

			if code := h.run("set", "--repo", tc.repo, "--issue", "12",
				"--field", "Workflow=Ready"); code != cli.ExitOK {
				t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
			}
			writes := h.transport.mutations()
			if len(writes) != 1 || writes[0].Path != wantPath {
				t.Errorf("wrote to %+v, want POST %s", writes, wantPath)
			}
		})
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

// The receipt comes from a read-back, so it can fail after the issue exists. Losing the
// number of an issue that was just created would be worse than the missing receipt, so the
// failure has to name it — and must not look like a creation that did not happen.
func TestNewNamesTheCreatedIssueWhenTheReceiptReadFails(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["GET "+fixtureRepo+"/issues/31"] = ghtest.Response{
		Status: http.StatusInternalServerError, Body: `{"message":"Server Error"}`}

	if code := h.run("new", "--type", "Task", "--title", "Record the frozen flag surface"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, h.stderr)
	}
	wants(t, h.stderr.String(), "created", "#31",
		"https://github.com/L3DigitalNet/example-repo/issues/31", "could not read it back")
	if h.stdout.Len() != 0 {
		t.Errorf("a failed read-back still wrote a receipt: %s", h.stdout)
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

// Issue #144: the guidance for a missing --type names the vocabulary, and both the count
// and the list come from the schema the command loaded.
func TestNewGuidanceForAMissingTypeEnumeratesTheDeliveredSchema(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("new", "--title", "x"); code != cli.ExitUsage {
		t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
	}
	wants(t, h.stderr.String(), "one of the 5 Issue Types", "Bug", "Feature", "Task", "Initiative", "Research")
	h.assertNoRequests(t)
}

// The same guidance against a schema of a different size. This is the regression the
// issue is actually about: the delivered baseline happens to define five Types today, so
// a hardcoded "five" and a derived count are indistinguishable until the vocabulary
// moves — which it is designed to do, by shipping a new payload version.
func TestNewGuidanceForAMissingTypeCountsTheLoadedSchema(t *testing.T) {
	t.Parallel()

	// Only the type vocabulary varies; the field half of the fixture is reused verbatim so
	// the schema each case writes is otherwise the delivered one.
	_, fixtureFields, found := strings.Cut(fixtureSchema, "issue_fields:")
	if !found {
		t.Fatal("the fixture schema no longer declares issue_fields")
	}

	cases := []struct {
		name  string
		types string
		wants []string
	}{
		{
			name:  "three types",
			types: "issue_types:\n  - Bug\n  - Task\n  - Chore\n\n",
			wants: []string{"one of the 3 Issue Types", "Bug, Task, Chore"},
		},
		{
			// The degenerate case a count-and-list phrasing gets wrong by default:
			// "one of the 1 Issue Types" is not a sentence anyone would ship.
			name:  "a single type",
			types: "issue_types:\n  - Bug\n\n",
			wants: []string{"the one Issue Type the organization schema defines: Bug"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			h.write(t, cli.DefaultSchemaPath, tc.types+"issue_fields:"+fixtureFields)

			if code := h.run("new", "--title", "x"); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, h.stderr)
			}
			wants(t, h.stderr.String(), tc.wants...)
			h.assertNoRequests(t)
		})
	}
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
//
// The partial-failure cases below exit ExitOperational rather than ExitFailure: the write
// that failed did so because the API refused it, and IR-005 reserves exit 1 for a verdict
// the tool actually reached. The completed-step reporting is unchanged — ERR-014 requires
// the message to state what provably landed, and exit 3 says only that no verdict exists.

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

	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, h.stderr)
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
	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitOperational {
		t.Fatalf("first run exit = %d, want %d", code, cli.ExitOperational)
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

	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, h.stderr)
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

// Reclassifying an already-closed issue is the case a single PATCH cannot express: GitHub
// applies state_reason only when the state changes, so closed/not_planned → closed/completed
// answers 200 and changes nothing. Believing that answer and writing `Workflow = Done` on
// top of it would produce a permanent divergence that every rerun reports as fixed, so the
// transition is expressed the way GitHub honors it — reopen, then close with the new reason.
func TestCloseReclassifiesAnIssueClosedForTheOtherReason(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("close", "--issue", "18", "--as", "done"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}

	writes := h.transport.mutations()
	if len(writes) != 3 {
		t.Fatalf("want reopen, close, then the Workflow write; got %+v", writes)
	}
	if writes[0].Method != http.MethodPatch || writes[0].Path != fixtureRepo+"/issues/18" {
		t.Errorf("first write = %s %s, want the reopening PATCH", writes[0].Method, writes[0].Path)
	}
	wants(t, writes[0].Body, `"state":"open"`)
	if writes[1].Method != http.MethodPatch || writes[1].Path != fixtureRepo+"/issues/18" {
		t.Errorf("second write = %s %s, want the reclassifying close", writes[1].Method, writes[1].Path)
	}
	wants(t, writes[1].Body, `"state":"closed"`, `"state_reason":"completed"`)
	if writes[2].Path != fixtureRepo+"/issues/18/issue-field-values" {
		t.Errorf("third write = %s %s, want the Workflow field last", writes[2].Method, writes[2].Path)
	}
	wants(t, writes[2].Body, "Done")
	wants(t, h.stdout.String(), "#18", "completed", "Done")
}

// Once the reclassifying reopen has been applied, the issue has already moved, so a
// failure after it cannot claim the issue is untouched. The operator is left holding an
// open issue and needs to be told exactly that, plus the rerun that finishes the job.
func TestCloseReportsTheOpenIssueWhenTheReclassifyingCloseFails(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	// The reopen is served; the close that should follow it is not.
	h.env.Transport = &failPatchAfter{inner: h.transport, path: fixtureRepo + "/issues/18", serve: 1}

	if code := h.run("close", "--issue", "18", "--as", "done"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s", code, cli.ExitOperational, h.stdout, h.stderr)
	}
	stderr := h.stderr.String()
	wants(t, stderr,
		"#18",                                    // which item
		"reopen",                                 // that the reopen already fired
		"open",                                   // the state the issue is actually in
		"Dropped",                                // the Workflow value that was left alone
		"gh-workflow close --issue 18 --as done") // the rerun that converges
	if strings.Contains(stderr, "nothing diverged") {
		t.Errorf("the message still claims nothing changed though the reopen was applied:\n%s", stderr)
	}
	if h.stdout.Len() != 0 {
		t.Errorf("a failed reclassification reported success on stdout: %s", h.stdout)
	}
	for _, write := range h.transport.mutations() {
		if strings.HasSuffix(write.Path, "/issue-field-values") {
			t.Errorf("the Workflow field was written after the close failed: %+v", write)
		}
	}
}

// The same defect seen from the other side: when GitHub answers 200 and still reports the
// old close reason, the reclassification did not happen. Reporting success there is the
// false-success path; the Workflow field must stay untouched so nothing diverges.
//
// The reopen preceding it was accepted, so this message may not claim the issue is
// unchanged either, and it carries the same rerun hint every other divergence branch does.
func TestCloseReportsDivergenceWhenTheCloseReasonIsNotApplied(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["PATCH "+fixtureRepo+"/issues/18"] = ghtest.Response{Status: http.StatusOK, Body: issueDropped}

	if code := h.run("close", "--issue", "18", "--as", "done"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s", code, cli.ExitFailure, h.stdout, h.stderr)
	}
	stderr := h.stderr.String()
	wants(t, stderr, "#18", "not_planned", "completed", "reopen",
		"gh-workflow close --issue 18 --as done")
	if strings.Contains(stderr, "nothing diverged") {
		t.Errorf("the message still claims nothing changed though the reopen was applied:\n%s", stderr)
	}
	if h.stdout.Len() != 0 {
		t.Errorf("an unapplied close reason reported success on stdout: %s", h.stdout)
	}
	for _, write := range h.transport.mutations() {
		if strings.HasSuffix(write.Path, "/issue-field-values") {
			t.Errorf("the Workflow field was written though the close reason never changed: %+v", write)
		}
	}
}

// Closing an open issue takes no reopen, so when GitHub drops the close reason there the
// issue really is untouched — the counterpart assertion that keeps the reopen-aware
// wording confined to the branch that earned it.
func TestCloseReportsAnUntouchedIssueWhenNoReopenWasNeeded(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	h.routes["PATCH "+fixtureRepo+"/issues/12"] = ghtest.Response{Status: http.StatusOK, Body: issueReady}

	if code := h.run("close", "--issue", "12", "--as", "done"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s", code, cli.ExitFailure, h.stdout, h.stderr)
	}
	wants(t, h.stderr.String(), "#12", "nothing diverged", "gh-workflow close --issue 12 --as done")
	for _, write := range h.transport.mutations() {
		if strings.HasSuffix(write.Path, "/issue-field-values") {
			t.Errorf("the Workflow field was written though the state never changed: %+v", write)
		}
	}
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

// An eligible issue is `clear` and writes nothing. The 1.6 report listed every
// precondition class in both directions; the DR-004 envelope has no member for a passing
// class, so a clear verdict is now the whole statement that each one passed and the
// itemization below covers the unmet direction.
func TestCheckPassesAnEligibleIssue(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "12"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	wants(t, h.stdout.String(), "clear")
	for _, c := range h.transport.recorded() {
		if c.Method != http.MethodGet {
			t.Errorf("check issued a %s request; it is read-only", c.Method)
		}
	}
}

// Issue #192: `Target date` is pinned to Feature, Task, and Initiative, but the package
// documents empty as valid, so its absence cannot block Ready. The cases below fix the
// boundary in both directions — an absent optional pin is eligible, an absent required
// pin is not — so a future edit cannot turn the exemption into "pinned fields are
// advisory".
func TestCheckDoesNotRequireAnOptionalPinnedFieldForReady(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name     string
		issue    string
		wantExit int
		wants    []string
	}{
		{
			name: "task with every required pin and no target date", issue: "22",
			wantExit: cli.ExitOK, wants: []string{"clear"},
		},
		{
			name: "feature missing a required pin", issue: "14",
			wantExit: cli.ExitFailure, wants: []string{"pinned-fields", "Priority"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			if code := h.run("check", "--issue", tc.issue); code != tc.wantExit {
				t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
					code, tc.wantExit, h.stdout, h.stderr)
			}
			wants(t, h.stdout.String(), tc.wants...)
			if strings.Contains(h.stdout.String(), "Target date") {
				t.Errorf("check reported Target date as a readiness gap:\n%s", h.stdout)
			}
			h.assertNoMutations(t)
		})
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
	envelope := decodeEnvelope(t, h.stdout.Bytes())
	if envelope.Result != cli.ResultDomainFinding {
		t.Errorf("result = %q, want %q", envelope.Result, cli.ResultDomainFinding)
	}
	if envelope.Target.Kind != cli.TargetIssue || envelope.Target.Number != 14 {
		t.Errorf("target = %+v, want issue 14", envelope.Target)
	}
	codes := map[string]bool{}
	for _, finding := range envelope.Findings {
		codes[finding.Code] = true
	}
	for _, code := range []string{
		"GHW-ISSUE-READY-PINNED-FIELDS", "GHW-ISSUE-READY-ACCEPTANCE-CRITERIA",
		"GHW-ISSUE-READY-BLOCKED-BY", "GHW-ISSUE-READY-SIZE",
	} {
		if !codes[code] {
			t.Errorf("the envelope carries no %s finding: %+v", code, envelope.Findings)
		}
	}
}

// The three FR-023 classes 1.7 added to the Issue route, each isolated on a fixture that
// fails only it. TestCheckEmitsJSON covers the four content classes an issue shares with
// 1.6; these are the structural and lifecycle ones, which no other Issue-route case
// reaches — a typeless issue, a natively closed one, and an open one whose Workflow
// already claims the work is finished.
func TestCheckReportsTheStructuralAndLifecycleIssueClasses(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		issue string
		want  []string
		// absent names a code the fixture must NOT raise, which is how each case proves it
		// isolates its own class rather than tripping the whole set.
		absent []string
	}{
		{
			name: "a typeless issue has no recognized ordinary Issue Type",
			// issueUntyped carries no acceptance criteria either, so only the type class is
			// asserted; the incoherence being isolated is that its open, nonterminal
			// Workflow must not raise the lifecycle finding.
			issue:  "20",
			want:   []string{"GHW-ISSUE-STRUCTURAL-TYPE-MISSING"},
			absent: []string{"GHW-ISSUE-READY-NATIVE-STATE", "GHW-ISSUE-READY-WORKFLOW-INCOHERENT"},
		},
		{
			name:  "a closed issue fails the native-state class",
			issue: "16",
			// A closed issue converged to Done fails both lifecycle classes at once, which
			// is the coherent pairing `close` writes; reporting only one would understate it.
			want: []string{"GHW-ISSUE-READY-NATIVE-STATE", "GHW-ISSUE-READY-WORKFLOW-INCOHERENT"},
		},
		{
			name:   "an open issue carrying a terminal Workflow is lifecycle-incoherent",
			issue:  "24",
			want:   []string{"GHW-ISSUE-READY-WORKFLOW-INCOHERENT"},
			absent: []string{"GHW-ISSUE-READY-NATIVE-STATE", "GHW-ISSUE-STRUCTURAL-TYPE-MISSING"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			if code := h.run("check", "--issue", tc.issue, "--output", "json"); code != cli.ExitFailure {
				t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
					code, cli.ExitFailure, h.stdout, h.stderr)
			}
			envelope := decodeEnvelope(t, h.stdout.Bytes())
			codes := map[string]bool{}
			for _, finding := range envelope.Findings {
				codes[finding.Code] = true
			}
			for _, code := range tc.want {
				if !codes[code] {
					t.Errorf("the envelope carries no %s finding: %+v", code, envelope.Findings)
				}
			}
			for _, code := range tc.absent {
				if codes[code] {
					t.Errorf("the envelope carries an unexpected %s finding: %+v", code, envelope.Findings)
				}
			}
			h.assertNoMutations(t)
		})
	}
}

// FR-023/IR-005: the Issue route rejects a PR-shaped response. The issues endpoint serves
// pull requests too, so without the shape read the gate would report on an object with no
// Issue Type and no Issue Fields and call every content class missing (DEV-023). The
// refusal is a local one — exit 2, not a domain verdict — because the invocation named the
// wrong route rather than found something wrong with the work.
func TestCheckIssueRejectsAPullRequestShapedResponse(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if code := h.run("check", "--issue", "26"); code != cli.ExitUsage {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s", code, cli.ExitUsage, h.stdout, h.stderr)
	}
	wants(t, h.stderr.String(), "is a pull request, not an issue", "check --pr 26")
	h.assertNoMutations(t)
	// No verdict is rendered at all: a usage refusal must not leave an envelope that reads
	// as a completed evaluation of the wrong object.
	if h.stdout.Len() != 0 {
		t.Errorf("the refusal rendered a report: %s", h.stdout)
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
