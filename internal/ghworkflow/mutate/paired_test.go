package mutate_test

// Fixture-backed command tests for the 1.7 paired operations and PR routes (spec FR-031
// through FR-034), with failure injection at every ordered mutation boundary.
//
// The fake is stateful on purpose. A canned response per route cannot express the two
// facts these commands are built around — that a mark-ready mutation changes what the next
// read of the same pull request reports, and that a merge does — and a suite that could
// not express them would pass while the tool skipped its verification reads entirely.

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
)

// finalBody is a structurally complete Final declaration on issue 12: the four required
// contract sections of FR-028 with the canonical relationship under the exact heading.
// issueInReview is the governing issue for every PR that is past Ready: its Workflow is
// already `In review`, so the Merge and disposition fixtures are not perturbed by the
// synchronization finding a still-`In progress` issue would raise on a ready Final.
const issueInReview = `{"number":13,"title":"Land the transport",
	"html_url":"https://github.com/L3DigitalNet/example-repo/issues/13",
	"state":"open","state_reason":null,
	"body":"## Outcome\n\nShip it.\n\n## Acceptance criteria\n\n- Prior bytes survive.\n",
	"type":{"name":"Bug"},
	"issue_field_values":[
		{"issue_field_name":"Workflow","data_type":"single_select","value":"In review","single_select_option":{"name":"In review"}},
		{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}},
		{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
		{"issue_field_name":"Change risk","data_type":"single_select","value":"R2 — Moderate","single_select_option":{"name":"R2 — Moderate"}},
		{"issue_field_name":"Execution mode","data_type":"single_select","value":"Interactive agent","single_select_option":{"name":"Interactive agent"}},
		{"issue_field_name":"Severity","data_type":"single_select","value":"S2 — Moderate","single_select_option":{"name":"S2 — Moderate"}}]}`

const finalBody = "## Summary\n\nLand the transport.\n\n" +
	"## Governing work\n\nFinal: #12\n\n" +
	"## Acceptance coverage\n\n- Prior bytes survive.\n\n" +
	"## Verification\n\n- go test ./...\n"

// supportingBody declares the same issue without claiming completion, which is what makes
// it the refusal fixture for `close --pr`.
// readyFinalBody governs the already-In-review issue, which is what a Final past Ready
// looks like.
const readyFinalBody = "## Summary\n\nLand the transport.\n\n" +
	"## Governing work\n\nFinal: #13\n\n" +
	"## Acceptance coverage\n\n- Prior bytes survive.\n\n" +
	"## Verification\n\n- go test ./...\n"

const supportingBody = "## Summary\n\nOne slice.\n\n" +
	"## Governing work\n\nSupporting: #13\n\n" +
	"## Acceptance coverage\n\n- Partial.\n\n" +
	"## Verification\n\n- go test ./...\n"

const headSHA = "0f1e2d3c4b5a69788796a5b4c3d2e1f009182736"

// pullState is one pull request the fake serves. Draft, Merged, and Closed move as the
// commands write, which is what makes the verification and observation reads meaningful.
type pullState struct {
	Number    int
	Body      string
	Draft     bool
	Merged    bool
	Closed    bool
	AutoMerge bool
}

// prFixture extends the shared harness with the pull-request surface and the injectable
// failures each ordered boundary needs.
type prFixture struct {
	h *harness

	mu    sync.Mutex
	pulls map[int]*pullState
	// comments is the canned `GET .../issues/N/comments` body per pull request, which is
	// where `close --pr` reads an existing `Final-Disposition:` record from. A pull request
	// with no entry answers with an empty list, so only the idempotence fixtures carry one.
	comments map[int]string

	// failMarkReady, failAutoMerge, and failMerge fail one boundary each. They are separate
	// switches rather than one route override because every mutation but the merge travels
	// as POST /graphql, so a URL-keyed override cannot name which one to fail.
	failMarkReady bool
	failAutoMerge bool
	failMerge     bool
}

func newPRFixture(t *testing.T) *prFixture {
	t.Helper()

	h := newHarness(t)
	// 90, 91, and 92 are the `close --pr` fixtures. 90 and 91 are already closed, which is
	// the resume state EC-014 forbids re-gating; 92 is the open Final whose convergence
	// reaches the field-identity read, so it is the only one that can exercise ERR-011.
	f := &prFixture{h: h, pulls: map[int]*pullState{
		50: {Number: 50, Body: finalBody, Draft: true},
		60: {Number: 60, Body: readyFinalBody},
		70: {Number: 70, Body: readyFinalBody},
		80: {Number: 80, Body: supportingBody},
		90: {Number: 90, Body: readyFinalBody, Closed: true},
		91: {Number: 91, Body: readyFinalBody, Closed: true},
		92: {Number: 92, Body: readyFinalBody},
	}, comments: map[int]string{
		90: `[{"body":"Final-Disposition: in-review\nReason: the first attempt was interrupted\n",
			"created_at":"2026-08-30T00:00:00Z","user":{"login":"agent"}}]`,
	}}

	h.routes["GET "+fixtureRepo+"/issues/13"] = ghtest.Response{Status: http.StatusOK, Body: issueInReview}
	h.routes["POST "+fixtureRepo+"/issues/13/issue-field-values"] = ghtest.Response{Status: http.StatusOK, Body: "[]"}

	previous := h.transport.inner.RouteFunc
	h.transport.inner.RouteFunc = func(req *http.Request) (ghtest.Response, bool) {
		if resp, ok := f.route(req); ok {
			return resp, true
		}
		if previous == nil {
			return ghtest.Response{}, false
		}
		return previous(req)
	}
	return f
}

func (f *prFixture) run(args ...string) int { return f.h.run(args...) }

func (f *prFixture) pull(number int) *pullState {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.pulls[number]
}

// route serves the pull-request surface. Anything it does not recognize falls through to
// the shared harness, so the issue routes keep behaving exactly as the 1.6 tests expect.
func (f *prFixture) route(req *http.Request) (ghtest.Response, bool) {
	path := req.URL.Path
	// An explicit route registered on the shared harness always wins, which is how a test
	// injects a failure at a boundary this fake would otherwise serve successfully.
	if _, overridden := f.h.routes[req.Method+" "+path]; overridden {
		return ghtest.Response{}, false
	}
	if strings.HasSuffix(path, "/comments") {
		if req.Method == http.MethodPost {
			return ghtest.Response{Status: http.StatusCreated,
				Body: `{"body":"recorded","created_at":"2026-08-30T00:00:00Z","user":{"login":"agent"}}`}, true
		}
		body := "[]"
		if number, err := strconv.Atoi(strings.TrimSuffix(
			strings.TrimPrefix(path, fixtureRepo+"/issues/"), "/comments")); err == nil {
			f.mu.Lock()
			if canned, ok := f.comments[number]; ok {
				body = canned
			}
			f.mu.Unlock()
		}
		return ghtest.Response{Status: http.StatusOK, Body: body}, true
	}
	// Issue 13 is served here rather than by the shared patch model, which only knows the
	// 1.6 fixtures: the close echoes the requested state so both terminal directions —
	// `done` after a merge and `not_planned` after a drop — read back correctly.
	if req.Method == http.MethodPatch && path == fixtureRepo+"/issues/13" {
		var payload struct {
			State  string `json:"state"`
			Reason string `json:"state_reason"`
		}
		if err := json.Unmarshal([]byte(readBody(req)), &payload); err != nil {
			return ghtest.Response{Status: http.StatusBadRequest, Body: `{"message":"bad request"}`}, true
		}
		return ghtest.Response{Status: http.StatusOK, Body: fmt.Sprintf(
			`{"number":13,"state":%q,"state_reason":%q,"type":{"name":"Bug"}}`, payload.State, payload.Reason)}, true
	}

	if req.Method == http.MethodPost && path == "/graphql" {
		return f.graphql(req)
	}
	if req.Method == http.MethodGet && path == fixtureRepo+"/pulls" {
		return ghtest.Response{Status: http.StatusOK, Body: "[]"}, true
	}
	if number, ok := pullNumber(path, ""); ok && req.Method == http.MethodGet {
		return f.pullResponse(number)
	}
	if number, ok := pullNumber(path, "/merge"); ok && req.Method == http.MethodPut {
		if f.failMerge {
			return ghtest.Response{Status: http.StatusMethodNotAllowed,
				Body: `{"message":"Pull Request is not mergeable"}`}, true
		}
		f.mu.Lock()
		if state := f.pulls[number]; state != nil {
			state.Merged, state.Closed = true, true
		}
		f.mu.Unlock()
		return ghtest.Response{Status: http.StatusOK,
			Body: `{"sha":"` + headSHA + `","merged":true,"message":"Pull Request successfully merged"}`}, true
	}
	// A pull request is closed through the issues endpoint, which is the same object; the
	// fake serves it here so the PR's own state moves rather than the patch model's issues.
	if req.Method == http.MethodPatch && strings.HasPrefix(path, fixtureRepo+"/issues/") {
		number, err := strconv.Atoi(strings.TrimPrefix(path, fixtureRepo+"/issues/"))
		if err != nil {
			return ghtest.Response{}, false
		}
		f.mu.Lock()
		state := f.pulls[number]
		if state != nil {
			state.Closed = true
		}
		f.mu.Unlock()
		if state == nil {
			return ghtest.Response{}, false
		}
		return ghtest.Response{Status: http.StatusOK, Body: fmt.Sprintf(
			`{"number":%d,"state":"closed","pull_request":{"url":"x"}}`, number)}, true
	}
	switch {
	case req.Method == http.MethodGet && path == fixtureRepo:
		return ghtest.Response{Status: http.StatusOK,
			Body: `{"allow_squash_merge":true,"allow_rebase_merge":true,"allow_merge_commit":false}`}, true
	case req.Method == http.MethodGet && strings.HasPrefix(path, fixtureRepo+"/rules/branches/"):
		return ghtest.Response{Status: http.StatusOK, Body: "[]"}, true
	case req.Method == http.MethodGet && strings.HasSuffix(path, "/protection"):
		return ghtest.Response{Status: http.StatusNotFound, Body: `{"message":"Branch not protected"}`}, true
	case req.Method == http.MethodGet && strings.HasSuffix(path, "/check-runs"):
		return ghtest.Response{Status: http.StatusOK, Body: `{"total_count":0,"check_runs":[]}`}, true
	}
	return ghtest.Response{}, false
}

// graphql dispatches on the operation in the request body, which is the only thing that
// distinguishes the three GraphQL calls: all of them are POST /graphql.
func (f *prFixture) graphql(req *http.Request) (ghtest.Response, bool) {
	var payload struct {
		Query     string         `json:"query"`
		Variables map[string]any `json:"variables"`
	}
	body := readBody(req)
	if err := json.Unmarshal([]byte(body), &payload); err != nil {
		return ghtest.Response{Status: http.StatusBadRequest, Body: `{"message":"bad request"}`}, true
	}
	switch {
	case strings.Contains(payload.Query, "mergeStateStatus"):
		number, _ := payload.Variables["number"].(float64)
		return ghtest.Response{Status: http.StatusOK, Body: fmt.Sprintf(
			`{"data":{"repository":{"pullRequest":{"id":"PR_node_%d","mergeStateStatus":"CLEAN","reviewDecision":""}}}}`,
			int(number))}, true
	case strings.Contains(payload.Query, "markPullRequestReadyForReview"):
		if f.failMarkReady {
			return ghtest.Response{Status: http.StatusOK,
				Body: `{"errors":[{"type":"FORBIDDEN","message":"Resource not accessible"}]}`}, true
		}
		f.mu.Lock()
		if state := f.pulls[nodeNumber(payload.Variables)]; state != nil {
			state.Draft = false
		}
		f.mu.Unlock()
		return ghtest.Response{Status: http.StatusOK, Body: `{"data":{}}`}, true
	case strings.Contains(payload.Query, "enablePullRequestAutoMerge"):
		if f.failAutoMerge {
			return ghtest.Response{Status: http.StatusOK,
				Body: `{"errors":[{"type":"FORBIDDEN","message":"Auto-merge is not allowed"}]}`}, true
		}
		f.mu.Lock()
		if state := f.pulls[nodeNumber(payload.Variables)]; state != nil {
			state.AutoMerge = true
		}
		f.mu.Unlock()
		return ghtest.Response{Status: http.StatusOK, Body: `{"data":{}}`}, true
	}
	return ghtest.Response{Status: http.StatusOK, Body: `{"data":{}}`}, true
}

func (f *prFixture) pullResponse(number int) (ghtest.Response, bool) {
	f.mu.Lock()
	defer f.mu.Unlock()
	state := f.pulls[number]
	if state == nil {
		return ghtest.Response{}, false
	}
	nativeState := "open"
	if state.Closed || state.Merged {
		nativeState = "closed"
	}
	autoMerge := "null"
	if state.AutoMerge {
		autoMerge = `{"merge_method":"squash"}`
	}
	body, err := json.Marshal(state.Body)
	if err != nil {
		return ghtest.Response{}, false
	}
	return ghtest.Response{Status: http.StatusOK, Body: fmt.Sprintf(
		`{"number":%d,"node_id":"PR_node_%d","title":"Land the transport",
		  "html_url":"https://github.com/L3DigitalNet/example-repo/pull/%d",
		  "state":%q,"draft":%t,"merged":%t,"body":%s,
		  "base":{"ref":"main","sha":"basesha"},"head":{"ref":"topic","sha":%q},
		  "mergeable":true,"auto_merge":%s,"labels":[]}`,
		number, number, number, nativeState, state.Draft, state.Merged, body, headSHA, autoMerge)}, true
}

// nodeNumber recovers the pull request from the GraphQL node id the fake hands out, which
// is how a mutation addressed by node id reaches the right fixture.
func nodeNumber(variables map[string]any) int {
	id, _ := variables["id"].(string)
	number, err := strconv.Atoi(strings.TrimPrefix(id, "PR_node_"))
	if err != nil {
		return 0
	}
	return number
}

func pullNumber(path, suffix string) (int, bool) {
	rest, ok := strings.CutPrefix(path, fixtureRepo+"/pulls/")
	if !ok {
		return 0, false
	}
	rest, ok = strings.CutSuffix(rest, suffix)
	if !ok {
		return 0, false
	}
	number, err := strconv.Atoi(rest)
	if err != nil {
		return 0, false
	}
	return number, true
}

func readBody(req *http.Request) string {
	if req.Body == nil {
		return ""
	}
	raw := make([]byte, 0, 512)
	buf := make([]byte, 512)
	for {
		n, err := req.Body.Read(buf)
		raw = append(raw, buf[:n]...)
		if err != nil {
			break
		}
	}
	return string(raw)
}

// assertNoWrites proves a run mutated nothing. The GraphQL merge-state read is excluded by
// shape rather than by method: every GraphQL operation is a POST because that is the only
// method the endpoint accepts, so method alone cannot separate a read from a mutation.
func assertNoWrites(t *testing.T, f *prFixture) {
	t.Helper()
	for _, c := range f.h.transport.recorded() {
		if c.Method == http.MethodGet {
			continue
		}
		if c.Path == "/graphql" && !strings.Contains(c.Body, "mutation") {
			continue
		}
		t.Errorf("the run issued a mutating request: %+v", c)
	}
}

// decodeEnvelope parses stdout as the DR-004 envelope and asserts the members every
// consumer keys off are present and non-null.
func decodeEnvelope(t *testing.T, out []byte) cli.Envelope {
	t.Helper()

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(out, &raw); err != nil {
		t.Fatalf("stdout is not a JSON envelope: %v\n%s", err, out)
	}
	for _, member := range []string{"schema_version", "command", "result", "target", "gate", "findings", "steps"} {
		if _, ok := raw[member]; !ok {
			t.Errorf("the envelope omits the required member %q: %s", member, out)
		}
	}
	// findings and steps are always arrays, never null: a consumer iterating them must not
	// have to special-case an absent collection.
	for _, member := range []string{"findings", "steps"} {
		if string(raw[member]) == "null" {
			t.Errorf("the envelope's %q is null rather than an array: %s", member, out)
		}
	}
	var envelope cli.Envelope
	if err := json.Unmarshal(out, &envelope); err != nil {
		t.Fatalf("the envelope does not decode: %v\n%s", err, out)
	}
	if envelope.SchemaVersion != cli.EnvelopeSchemaVersion {
		t.Errorf("schema_version = %q, want %q", envelope.SchemaVersion, cli.EnvelopeSchemaVersion)
	}
	return envelope
}

// stepStatus returns one named step's status, or "" when the envelope omits it.
func stepStatus(envelope cli.Envelope, name string) cli.StepStatus {
	for _, step := range envelope.Steps {
		if step.Name == name {
			return step.Status
		}
	}
	return ""
}

func assertSteps(t *testing.T, envelope cli.Envelope, want map[string]cli.StepStatus) {
	t.Helper()
	for name, status := range want {
		if got := stepStatus(envelope, name); got != status {
			t.Errorf("step %q = %q, want %q\nsteps: %+v", name, got, status, envelope.Steps)
		}
	}
}

// ---------------------------------------------------------------- check --pr

func TestCheckPullRequestInfersTheGateFromObservedState(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name     string
		number   int
		wantGate string
	}{
		{name: "a draft is working toward Ready", number: 50, wantGate: "ready"},
		{name: "an open non-draft is working toward Merge", number: 60, wantGate: "merge"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			f := newPRFixture(t)
			f.run("check", "--pr", strconv.Itoa(tc.number), "--output", "json")
			envelope := decodeEnvelope(t, f.h.stdout.Bytes())
			if string(envelope.Gate) != tc.wantGate {
				t.Errorf("gate = %q, want %q", envelope.Gate, tc.wantGate)
			}
			if envelope.Target.Kind != cli.TargetPullRequest || envelope.Target.Number != tc.number {
				t.Errorf("target = %+v, want pull request %d", envelope.Target, tc.number)
			}
			assertNoWrites(t, f)
		})
	}
}

// FR-031 is explicit that asking for post-merge on an open PR is a domain finding rather
// than invalid syntax: the invocation is well formed and the answer is about state.
func TestCheckPostMergeOnAnOpenPullRequestIsADomainFinding(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("check", "--pr", "60", "--through", "post-merge", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitFailure, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	if envelope.Result != cli.ResultDomainFinding {
		t.Errorf("result = %q, want %q", envelope.Result, cli.ResultDomainFinding)
	}
}

func TestCheckSelectorsAreMutuallyExclusive(t *testing.T) {
	t.Parallel()

	cases := [][]string{
		{"check", "--issue", "12", "--pr", "50"},
		{"check"},
		{"check", "--issue", "12", "--through", "ready"},
		{"check", "--pr", "50", "--through", "everything"},
	}
	for _, args := range cases {
		t.Run(strings.Join(args, " "), func(t *testing.T) {
			t.Parallel()

			f := newPRFixture(t)
			if code := f.run(args...); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, f.h.stderr)
			}
		})
	}
}

// ---------------------------------------------------------------- ready

// The successful draft → ready path, with the NFR-008 call count asserted exactly: four
// reads to build the topology (the pull request, its GraphQL merge state, the governing
// issue, and the open-PR list the one-open-Final rule needs), two writes (the field
// identity resolution and the Workflow value), the mark-ready mutation, and one
// verification read — eight requests, of which two mutate.
func TestReadyCarriesADraftFinalAcrossReady(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("ready", "--pr", "50", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	if envelope.Result != cli.ResultClear {
		t.Errorf("result = %q, want %q", envelope.Result, cli.ResultClear)
	}
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"synchronize-issue-workflow": cli.StepCompleted,
		"mark-ready":                 cli.StepCompleted,
		"verify-ready":               cli.StepCompleted,
	})
	if f.pull(50).Draft {
		t.Error("the pull request is still a draft")
	}
	if got := len(f.h.transport.recorded()); got != 8 {
		t.Errorf("the Ready chain issued %d requests, want 8:\n%+v", got, f.h.transport.recorded())
	}
	// Three non-GET requests, one of which is the read-only GraphQL merge-state query: every
	// GraphQL operation is a POST, so the two actual writes are the Workflow value and the
	// mark-ready mutation.
	if writes := f.h.transport.mutations(); len(writes) != 3 {
		t.Errorf("the Ready chain issued %d non-GET requests, want 3:\n%+v", len(writes), writes)
	}
}

// A second run has nothing to do, and doing nothing must be visible: the steps say skipped
// rather than completed, and no write leaves the process.
func TestReadyIsIdempotent(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	// The rerun is about the transition, so this fixture governs the already-In-review issue:
	// a still-`In progress` issue would raise the synchronization finding on the second pass
	// and test the engine rather than the command's idempotence.
	f.pull(50).Body = readyFinalBody
	if code := f.run("ready", "--pr", "50"); code != cli.ExitOK {
		t.Fatalf("first run exit = %d, want 0\nstderr: %s", code, f.h.stderr)
	}
	f.h.reset()
	if code := f.run("ready", "--pr", "50", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("rerun exit = %d, want 0\nstderr: %s", code, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"mark-ready":   cli.StepSkipped,
		"verify-ready": cli.StepSkipped,
	})
}

// Failure injection at each ordered Ready boundary. The claim under test is not that the
// command fails — it is that the envelope states exactly which writes landed, that no
// later write was attempted, and that the exit code is the operational 3 rather than a
// domain verdict the tool never reached.
func TestReadyRecordsEveryOrderedBoundaryOnFailure(t *testing.T) {
	t.Parallel()

	t.Run("the issue synchronization fails first", func(t *testing.T) {
		t.Parallel()

		f := newPRFixture(t)
		f.h.routes["POST "+fixtureRepo+"/issues/12/issue-field-values"] = ghtest.Response{
			Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

		if code := f.run("ready", "--pr", "50", "--output", "json"); code != cli.ExitOperational {
			t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, f.h.stderr)
		}
		envelope := decodeEnvelope(t, f.h.stdout.Bytes())
		assertSteps(t, envelope, map[string]cli.StepStatus{
			"synchronize-issue-workflow": cli.StepFailed,
			"mark-ready":                 cli.StepPending,
			"verify-ready":               cli.StepPending,
		})
		if !f.pull(50).Draft {
			t.Error("the pull request was marked ready after the issue write failed")
		}
	})

	t.Run("the mark-ready mutation fails after the issue write landed", func(t *testing.T) {
		t.Parallel()

		f := newPRFixture(t)
		f.failMarkReady = true

		if code := f.run("ready", "--pr", "50", "--output", "json"); code != cli.ExitOperational {
			t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, f.h.stderr)
		}
		envelope := decodeEnvelope(t, f.h.stdout.Bytes())
		assertSteps(t, envelope, map[string]cli.StepStatus{
			"synchronize-issue-workflow": cli.StepCompleted,
			"mark-ready":                 cli.StepFailed,
			"verify-ready":               cli.StepPending,
		})
	})
}

// A Supporting PR never touches issue lifecycle (FR-029/FR-032), so its Ready run marks
// the synchronization step skipped and writes only the draft transition.
func TestReadyDoesNotTouchIssueLifecycleForASupportingPullRequest(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.pull(80).Draft = true
	if code := f.run("ready", "--pr", "80", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{"synchronize-issue-workflow": cli.StepSkipped})
	for _, write := range f.h.transport.mutations() {
		if strings.Contains(write.Path, "/issues/") {
			t.Errorf("a Supporting PR's Ready run wrote to an issue: %+v", write)
		}
	}
}

// ---------------------------------------------------------------- merge

// The successful Merge chain, with its exact call count: four topology reads, four merge
// evidence reads (settings, rulesets, classic protection, check runs), the merge itself,
// the terminal observation, and the four calls the shared `close --issue N --as done`
// sequence makes — fourteen requests, of which three mutate.
func TestMergeAdmitsAFinalAndConvergesItsIssue(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("merge", "--pr", "60", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"merge":                    cli.StepCompleted,
		"enable-auto-merge":        cli.StepSkipped,
		"observe-terminal-state":   cli.StepCompleted,
		"converge-governing-issue": cli.StepCompleted,
	})
	if got := len(f.h.transport.recorded()); got != 14 {
		t.Errorf("the Merge chain issued %d requests, want 14:\n%+v", got, f.h.transport.recorded())
	}
	// Four non-GET requests: the read-only GraphQL merge-state query plus the three writes —
	// the merge, the issue close, and the Workflow value.
	if writes := f.h.transport.mutations(); len(writes) != 4 {
		t.Errorf("the Merge chain issued %d non-GET requests, want 4:\n%+v", len(writes), writes)
	}
}

// The default method is the first live-permitted of squash, rebase, merge — the repository
// fixture forbids merge commits, so a squash is what must go out.
func TestMergeUsesTheFirstPermittedMethodAndHonorsAnExplicitOne(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name       string
		args       []string
		wantMethod string
		wantExit   int
	}{
		{name: "fallback preference", args: []string{"merge", "--pr", "60"}, wantMethod: "squash", wantExit: cli.ExitOK},
		{name: "explicit rebase", args: []string{"merge", "--pr", "60", "--method", "rebase"},
			wantMethod: "rebase", wantExit: cli.ExitOK},
		{name: "explicit method the repository forbids", args: []string{"merge", "--pr", "60", "--method", "merge"},
			wantExit: cli.ExitFailure},
		{name: "unknown method spelling", args: []string{"merge", "--pr", "60", "--method", "rocket"},
			wantExit: cli.ExitUsage},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			f := newPRFixture(t)
			if code := f.run(tc.args...); code != tc.wantExit {
				t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
					code, tc.wantExit, f.h.stdout, f.h.stderr)
			}
			if tc.wantMethod == "" {
				if f.pull(60).Merged {
					t.Error("a refused method still merged the pull request")
				}
				return
			}
			var merged bool
			for _, write := range f.h.transport.mutations() {
				if strings.HasSuffix(write.Path, "/merge") {
					merged = true
					if !strings.Contains(write.Body, `"merge_method":"`+tc.wantMethod+`"`) {
						t.Errorf("merge body = %s, want method %q", write.Body, tc.wantMethod)
					}
					if !strings.Contains(write.Body, headSHA) {
						t.Errorf("merge body = %s, want the validated head SHA", write.Body)
					}
				}
			}
			if !merged {
				t.Error("no merge request was issued")
			}
		})
	}
}

// EC-012: nothing is rolled back after admission. When the issue convergence fails the
// merge stands, the envelope says so, and no compensating write goes out.
func TestMergeNeverRollsBackAfterAdmission(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.h.routes["POST "+fixtureRepo+"/issues/13/issue-field-values"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := f.run("merge", "--pr", "60", "--output", "json"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"merge":                    cli.StepCompleted,
		"observe-terminal-state":   cli.StepCompleted,
		"converge-governing-issue": cli.StepFailed,
	})
	if !f.pull(60).Merged {
		t.Error("the merge was undone after the convergence failed")
	}
}

func TestMergeReportsAFailedAdmissionWithoutTouchingTheIssue(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.failMerge = true

	if code := f.run("merge", "--pr", "60", "--output", "json"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"merge":                    cli.StepFailed,
		"observe-terminal-state":   cli.StepPending,
		"converge-governing-issue": cli.StepPending,
	})
	for _, write := range f.h.transport.mutations() {
		if strings.Contains(write.Path, "/issues/") {
			t.Errorf("a failed merge wrote to an issue: %+v", write)
		}
	}
}

// FR-033: arming auto-merge is never success by itself. The command retains the
// observation responsibility and says so, and the exit code is not zero.
func TestMergeAutoRetainsObservationResponsibility(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("merge", "--pr", "60", "--auto", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
			code, cli.ExitFailure, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"merge":                    cli.StepSkipped,
		"enable-auto-merge":        cli.StepCompleted,
		"converge-governing-issue": cli.StepPending,
	})
	var found bool
	for _, finding := range envelope.Findings {
		if finding.Code == "GHW-PR-MERGE-OUTCOME-PENDING" {
			found = true
		}
	}
	if !found {
		t.Errorf("no pending-outcome finding: %+v", envelope.Findings)
	}
}

// A Supporting merge is lifecycle-neutral: it never authorizes Done and never writes the
// governing issue (FR-029).
func TestMergeLeavesTheIssueAloneForASupportingPullRequest(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("merge", "--pr", "80", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{"converge-governing-issue": cli.StepSkipped})
	for _, write := range f.h.transport.mutations() {
		if strings.Contains(write.Path, "/issues/") {
			t.Errorf("a Supporting merge wrote to an issue: %+v", write)
		}
	}
}

// ---------------------------------------------------------------- close --pr

// The record precedes the close, and the recorded value is the token the engine's
// Post-merge predicate reads back.
func TestClosePullRequestRecordsTheDispositionBeforeClosing(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("close", "--pr", "70", "--as", "blocked",
		"--reason", "waiting on the upstream fix", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepCompleted,
		"close-pull-request":      cli.StepCompleted,
		"converge-issue-workflow": cli.StepCompleted,
	})

	writes := f.h.transport.mutations()
	var commentAt, closeAt = -1, -1
	for i, write := range writes {
		switch {
		case strings.HasSuffix(write.Path, "/issues/70/comments"):
			commentAt = i
			if !strings.Contains(write.Body, "Final-Disposition: blocked") ||
				!strings.Contains(write.Body, "Reason: waiting on the upstream fix") {
				t.Errorf("the disposition record is malformed: %s", write.Body)
			}
		case write.Method == http.MethodPatch && strings.HasSuffix(write.Path, "/issues/70"):
			closeAt = i
		}
	}
	if commentAt < 0 || closeAt < 0 || commentAt > closeAt {
		t.Errorf("the record must precede the close; comment at %d, close at %d:\n%+v",
			commentAt, closeAt, writes)
	}
}

func TestClosePullRequestRefusesTheRoutesItDoesNotOwn(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		args []string
	}{
		{name: "supporting", args: []string{"close", "--pr", "80", "--as", "dropped", "--reason", "no"}},
		{name: "done is not a PR disposition", args: []string{"close", "--pr", "70", "--as", "done", "--reason", "x"}},
		{name: "an empty reason", args: []string{"close", "--pr", "70", "--as", "dropped", "--reason", "  "}},
		{name: "a multi-line reason", args: []string{"close", "--pr", "70", "--as", "dropped", "--reason", "a\nb"}},
		{name: "both selectors", args: []string{"close", "--pr", "70", "--issue", "12", "--as", "dropped"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			f := newPRFixture(t)
			if code := f.run(tc.args...); code != cli.ExitUsage {
				t.Errorf("exit = %d, want %d\nstderr: %s", code, cli.ExitUsage, f.h.stderr)
			}
			assertNoWrites(t, f)
		})
	}
}

// The first canonical record is immutable, so an interrupted close resumes from it and a
// rerun does not write a second one.
func TestClosePullRequestReusesAnExistingRecordOnRerun(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.h.routes["GET "+fixtureRepo+"/issues/70/comments"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"body":"Final-Disposition: dropped\nReason: superseded\n","created_at":"2026-08-01T00:00:00Z",
			"user":{"login":"agent"}}]`}

	if code := f.run("close", "--pr", "70", "--as", "dropped",
		"--reason", "a different sentence", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{"record-disposition": cli.StepSkipped})
	for _, write := range f.h.transport.mutations() {
		if strings.HasSuffix(write.Path, "/comments") {
			t.Errorf("the rerun wrote a second disposition record: %+v", write)
		}
	}
}

// A conflicting record is refused rather than overwritten: terminal evidence is immutable,
// and the contradiction is reported for a human to resolve.
func TestClosePullRequestRefusesAConflictingRecord(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.h.routes["GET "+fixtureRepo+"/issues/70/comments"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"body":"Final-Disposition: dropped\nReason: superseded\n","created_at":"2026-08-01T00:00:00Z",
			"user":{"login":"agent"}}]`}

	if code := f.run("close", "--pr", "70", "--as", "blocked",
		"--reason", "actually blocked", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
			code, cli.ExitFailure, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepFailed,
		"close-pull-request":      cli.StepPending,
		"converge-issue-workflow": cli.StepPending,
	})
	if f.pull(70).Closed {
		t.Error("the pull request was closed despite the conflicting record")
	}
}

// Failure injection at the close boundary: the record stands, the PR stays open, and the
// issue is never converged on the strength of a close that did not happen.
func TestClosePullRequestRecordsAPartialFailure(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.h.routes["PATCH "+fixtureRepo+"/issues/70"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := f.run("close", "--pr", "70", "--as", "dropped",
		"--reason", "superseded", "--output", "json"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstderr: %s", code, cli.ExitOperational, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepCompleted,
		"close-pull-request":      cli.StepFailed,
		"converge-issue-workflow": cli.StepPending,
	})
}

// `dropped` is terminal, so it runs the paired Issue transition rather than writing a
// Workflow value beside an open issue.
func TestClosePullRequestDroppedRunsTheTerminalIssuePairing(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("close", "--pr", "70", "--as", "dropped", "--reason", "superseded"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	var closedIssue, wroteWorkflow bool
	for _, write := range f.h.transport.mutations() {
		if write.Method == http.MethodPatch && strings.HasSuffix(write.Path, "/issues/13") &&
			strings.Contains(write.Body, "not_planned") {
			closedIssue = true
		}
		if strings.HasSuffix(write.Path, "/issues/13/issue-field-values") {
			wroteWorkflow = true
		}
	}
	if !closedIssue || !wroteWorkflow {
		t.Errorf("the dropped disposition did not run the terminal pairing (closed=%t, workflow=%t):\n%+v",
			closedIssue, wroteWorkflow, f.h.transport.mutations())
	}
}

// ---------------------------------------------------------------- ERR-011 schema drift

// ERR-011: the live organization schema is checked before any field write, and a
// disagreement with the baseline stops the operation with a finding rather than an error
// about the operator's invocation — which was validated offline and is correct.
func TestReadyReportsLiveSchemaDriftBeforeWriting(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	// The organization no longer defines Workflow, though the baseline schema still does.
	f.h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":102,"name":"Priority","data_type":"single_select","options":[]}]`}

	if code := f.run("ready", "--pr", "50", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
			code, cli.ExitFailure, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"synchronize-issue-workflow": cli.StepFailed,
		"mark-ready":                 cli.StepPending,
	})
	var found bool
	for _, finding := range envelope.Findings {
		if finding.Code == "GHW-ISSUE-STRUCTURAL-SCHEMA-DRIFT" {
			found = true
		}
	}
	if !found {
		t.Errorf("no schema-drift finding: %+v", envelope.Findings)
	}
	assertNoWrites(t, f)
}

// ERR-011 has a second write path: the disposition route's Workflow convergence. Through
// 1.7-rc it reported every failure of the field-identity read as drift, so an unreachable
// API produced a domain verdict with no finding in it — the operator was sent to
// `gh-workflow audit` over a schema that had never been read.
func TestClosePullRequestReportsALiveSchemaDriftAsAFinding(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	// The organization no longer defines Workflow, though the baseline schema still does.
	f.h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{Status: http.StatusOK,
		Body: `[{"id":102,"name":"Priority","data_type":"single_select","options":[]}]`}

	if code := f.run("close", "--pr", "92", "--as", "blocked", "--reason",
		"waiting on the upstream fix", "--output", "json"); code != cli.ExitFailure {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
			code, cli.ExitFailure, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	if envelope.Result != cli.ResultDomainFinding {
		t.Errorf("result = %q, want %q", envelope.Result, cli.ResultDomainFinding)
	}
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepCompleted,
		"close-pull-request":      cli.StepCompleted,
		"converge-issue-workflow": cli.StepFailed,
	})
	var found bool
	for _, finding := range envelope.Findings {
		if finding.Code == "GHW-ISSUE-STRUCTURAL-SCHEMA-DRIFT" {
			found = true
		}
	}
	if !found {
		t.Errorf("no schema-drift finding: %+v", envelope.Findings)
	}
}

// The other half of the same branch: a 503 on the field-identity read is operational, so
// it exits 3 with no drift finding and no message claiming the schema drifted. The
// disposition record and the close still stand, which is what makes the rerun a resume.
func TestClosePullRequestReportsAFailedFieldIdentityReadAsOperational(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	f.h.routes["GET /orgs/"+fixtureOrg+"/issue-fields"] = ghtest.Response{
		Status: http.StatusServiceUnavailable, Body: `{"message":"Service unavailable"}`}

	if code := f.run("close", "--pr", "92", "--as", "blocked", "--reason",
		"waiting on the upstream fix", "--output", "json"); code != cli.ExitOperational {
		t.Fatalf("exit = %d, want %d\nstdout: %s\nstderr: %s",
			code, cli.ExitOperational, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	if envelope.Result != cli.ResultOperationalFailure {
		t.Errorf("result = %q, want %q", envelope.Result, cli.ResultOperationalFailure)
	}
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepCompleted,
		"close-pull-request":      cli.StepCompleted,
		"converge-issue-workflow": cli.StepFailed,
	})
	for _, finding := range envelope.Findings {
		if finding.Code == "GHW-ISSUE-STRUCTURAL-SCHEMA-DRIFT" {
			t.Errorf("a failed read produced a schema-drift finding: %+v", finding)
		}
	}
	// "drift"/"drifted" is the wording that would send the operator to `gh-workflow audit`
	// over a schema this run never read; the step message and the error must not use it.
	whole := f.h.stdout.String() + f.h.stderr.String()
	if strings.Contains(strings.ToLower(whole), "drift") {
		t.Errorf("an operational failure was reported as drift:\n%s", whole)
	}
}

// ---------------------------------------------------------------- close --pr idempotence

// EC-014/FR-034 resume: rerunning the same disposition against an already-closed Final
// that already carries the matching record writes nothing at all. Every step is skipped
// and the run still succeeds, which is what makes an interrupted first attempt recoverable
// by rerunning the identical invocation.
func TestClosePullRequestIsIdempotentAgainstAnExistingMatchingRecord(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("close", "--pr", "90", "--as", "in-review", "--reason",
		"a different sentence about the same decision", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepSkipped,
		"close-pull-request":      cli.StepSkipped,
		"converge-issue-workflow": cli.StepSkipped,
	})
	assertNoWrites(t, f)
}

// The same already-closed Final without a record is the state the command exists to
// repair: the record is written, and only the close is skipped.
func TestClosePullRequestRecordsADispositionOnAnAlreadyClosedFinal(t *testing.T) {
	t.Parallel()

	f := newPRFixture(t)
	if code := f.run("close", "--pr", "91", "--as", "in-review", "--reason",
		"closed by hand before the record existed", "--output", "json"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout: %s\nstderr: %s", code, f.h.stdout, f.h.stderr)
	}
	envelope := decodeEnvelope(t, f.h.stdout.Bytes())
	assertSteps(t, envelope, map[string]cli.StepStatus{
		"record-disposition":      cli.StepCompleted,
		"close-pull-request":      cli.StepSkipped,
		"converge-issue-workflow": cli.StepSkipped,
	})
	var recorded []call
	for _, write := range f.h.transport.mutations() {
		if write.Method == http.MethodPost && strings.HasSuffix(write.Path, "/issues/91/comments") {
			recorded = append(recorded, write)
		}
	}
	if len(recorded) != 1 {
		t.Fatalf("want exactly one disposition comment, got %d:\n%+v",
			len(recorded), f.h.transport.mutations())
	}
	if !strings.Contains(recorded[0].Body, "Final-Disposition: in-review") {
		t.Errorf("the record does not carry the canonical disposition line: %s", recorded[0].Body)
	}
	// Nothing but the comment: no PATCH closing an already-closed pull request, and no
	// field write against an issue that already holds the target Workflow. The GraphQL
	// merge-state query is excluded by shape, not by method — every GraphQL call is a POST.
	for _, write := range f.h.transport.mutations() {
		switch {
		case write.Path == "/graphql" && !strings.Contains(write.Body, "mutation"):
		case write.Method == http.MethodPost && strings.HasSuffix(write.Path, "/issues/91/comments"):
		default:
			t.Errorf("the resume issued an unexpected mutating request: %+v", write)
		}
	}
}
