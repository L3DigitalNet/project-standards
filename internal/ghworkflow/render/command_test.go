package render_test

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"

	// Both subcommands register themselves; importing the package under test is what
	// wires them into the registry, exactly as cmd/gh-workflow does.
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

const (
	fixtureToken  = "gho_fixturetokenvalue"
	fixtureBase   = "https://api.github.test"
	fixturePolicy = "organization = \"L3DigitalNet\"\npackage_version = \"1.0\"\n"
	fixtureGit    = "[core]\n\trepositoryformatversion = 0\n[remote \"origin\"]\n\turl = git@github.test:L3DigitalNet/example-repo.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
)

// The JSON below is the same fixture work-item set as fixtureSnapshot, expressed as the
// GitHub REST payloads the tool actually reads. Driving the command tests from the wire
// shape and the engine tests from the model, then asserting both against one golden, is
// what proves the fetch layer and the layout engine agree.
const (
	issue12 = `{"number":12,"title":"Ledger write leaves a partial file",
		"html_url":"https://github.com/L3DigitalNet/example-repo/issues/12",
		"state":"open","state_reason":null,
		"body":"## Outcome\n\nA failed refresh must not damage the file.\n\n## Acceptance criteria\n\n- Prior bytes survive.\n",
		"type":{"name":"Bug"},
		"issue_field_values":[
			{"issue_field_name":"Workflow","data_type":"single_select","value":"Blocked","single_select_option":{"name":"Blocked"}},
			{"issue_field_name":"Priority","data_type":"single_select","value":"P0 — Immediate","single_select_option":{"name":"P0 — Immediate"}},
			{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
			{"issue_field_name":"Severity","data_type":"single_select","value":"S1 — High","single_select_option":{"name":"S1 — High"}},
			{"issue_field_name":"Change risk","data_type":"single_select","value":"R3 — High","single_select_option":{"name":"R3 — High"}},
			{"issue_field_name":"Execution mode","data_type":"single_select","value":"Interactive agent","single_select_option":{"name":"Interactive agent"}},
			{"issue_field_name":"Target date","data_type":"date","value":"2026-08-01"}]}`

	issue14 = `{"number":14,"title":"Add ledger TOC anchors",
		"html_url":"https://github.com/L3DigitalNet/example-repo/issues/14",
		"state":"open","state_reason":null,
		"body":"## Outcome\n\nNavigate the ledger.\n",
		"type":{"name":"Feature"},
		"issue_field_values":[
			{"issue_field_name":"Workflow","data_type":"single_select","value":"Needs definition","single_select_option":{"name":"Needs definition"}},
			{"issue_field_name":"Priority","data_type":"single_select","value":"P2 — Planned","single_select_option":{"name":"P2 — Planned"}},
			{"issue_field_name":"Size","data_type":"single_select","value":"M","single_select_option":{"name":"M"}},
			{"issue_field_name":"Execution mode","data_type":"single_select","value":"Unattended agent","single_select_option":{"name":"Unattended agent"}}]}`

	issue15 = `{"number":15,"title":"Escape titles with | pipes, *stars*, <angles> and https://example.test/x",
		"html_url":"https://github.com/L3DigitalNet/example-repo/issues/15",
		"state":"open","state_reason":null,
		"body":"## Acceptance criteria\n\n- Titles render literally.\n",
		"type":{"name":"Task"},
		"issue_field_values":[
			{"issue_field_name":"Workflow","data_type":"single_select","value":"Done","single_select_option":{"name":"Done"}},
			{"issue_field_name":"Priority","data_type":"single_select","value":"P3 — Opportunistic","single_select_option":{"name":"P3 — Opportunistic"}},
			{"issue_field_name":"Size","data_type":"single_select","value":"S","single_select_option":{"name":"S"}},
			{"issue_field_name":"Change risk","data_type":"single_select","value":"R1 — Low","single_select_option":{"name":"R1 — Low"}},
			{"issue_field_name":"Execution mode","data_type":"single_select","value":"Human only","single_select_option":{"name":"Human only"}}]}`

	// Title matches fixture_test.go's issue16 exactly — the wire fixture and the model
	// fixture must agree on the one title that pins the summary golden's bare-underscore
	// row (#177).
	issue16 = `{"number":16,"title":"Support runner_labels for python_tooling check.yml",
		"html_url":"https://github.com/L3DigitalNet/example-repo/issues/16",
		"state":"open","state_reason":null,
		"body":"## Acceptance criteria\n\n- The package ships.\n",
		"type":{"name":"Initiative"},
		"issue_field_values":[
			{"issue_field_name":"Workflow","data_type":"single_select","value":"In progress","single_select_option":{"name":"In progress"}},
			{"issue_field_name":"Priority","data_type":"single_select","value":"P1 — Next","single_select_option":{"name":"P1 — Next"}},
			{"issue_field_name":"Target date","data_type":"date","value":"2099-12-31"}]}`

	// The issues endpoint returns pull requests too; this entry proves they are
	// filtered out rather than listed twice under two different layouts.
	issueShapedPull = `{"number":21,"title":"Add the render engine",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/21",
		"state":"open","body":"Closes #12","pull_request":{"url":"https://api.github.test/repos/L3DigitalNet/example-repo/pulls/21"}}`

	// The three PR bodies are the 1.7 declaration matrix the summary has to tell apart:
	// an open Final, a draft Supporting, and an open Standalone. Every one of them is
	// deliberately incomplete against FR-028's four canonical sections, because a summary
	// whose fixtures all pass would never prove that findings reach the report at all.
	pull21 = `{"number":21,"title":"Add the render engine",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/21",
		"state":"open","draft":false,"body":"## Governing work\n\nFinal: #12\n\nCloses #12\n",
		"base":{"ref":"main"},"head":{"sha":"aaa111"}}`

	pull22 = `{"number":22,"title":"Tidy the fixture corpus",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/22",
		"state":"open","draft":true,"body":"## Governing work\n\nSupporting: #14\n",
		"base":{"ref":"main"},"head":{"sha":"bbb222"}}`
)

// pull23 is the emoji-width row (#185). Its title is spliced from emojiWidthTitle rather
// than written out here, so the wire fixture and the model fixture cannot drift into
// disagreeing about the one cell whose padding the golden exists to pin. Every character
// in it is JSON-safe, so no escaping step stands between the constant and the payload.
const pull23 = `{"number":23,"title":"` + emojiWidthTitle + `",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/23",
		"state":"open","draft":false,"body":"## Governing work\n\nStandalone\n\n## Change risk\n\nR2 — Moderate\n",
		"base":{"ref":"main"},"head":{"sha":"ccc333"}}`

type harness struct {
	env       *cli.Env
	stdout    *bytes.Buffer
	stderr    *bytes.Buffer
	transport *ghtest.Transport
	root      string
}

// newHarness builds a consumer checkout carrying the delivered artifacts and an origin
// remote, then runs from a nested directory so a passing zero-argument run proves
// upward resolution (IR-004) rather than a lucky working directory.
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

	const repo = "/repos/L3DigitalNet/example-repo"
	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		repo + "/issues": {Status: http.StatusOK, Body: "[" + strings.Join(
			[]string{issue12, issue14, issue15, issue16, issueShapedPull}, ",") + "]"},
		repo + "/pulls": {Status: http.StatusOK, Body: "[" + pull21 + "," + pull22 + "," + pull23 + "]"},
		// CI arrives on two independent surfaces and a repository may use either, so one
		// fixture pull request reports check runs and the other falls back to commit
		// statuses. Both paths are exercised by the same run.
		repo + "/commits/aaa111/check-runs": {Status: http.StatusOK, Body: `{"total_count":1,
			"check_runs":[{"name":"go-check","status":"completed","conclusion":"success"}]}`},
		repo + "/commits/bbb222/check-runs": {Status: http.StatusOK, Body: `{"total_count":0,"check_runs":[]}`},
		repo + "/commits/bbb222/status":     {Status: http.StatusOK, Body: `{"state":"failure","total_count":1}`},
		repo + "/commits/ccc333/check-runs": {Status: http.StatusOK, Body: `{"total_count":1,
			"check_runs":[{"name":"go-check","status":"completed","conclusion":"success"}]}`},
		repo + "/issues/12": {Status: http.StatusOK, Body: issue12},
		repo + "/issues/14": {Status: http.StatusOK, Body: issue14},
		repo + "/pulls/21":  {Status: http.StatusOK, Body: pull21},
		repo + "/pulls/22":  {Status: http.StatusOK, Body: pull22},
		repo + "/pulls/23":  {Status: http.StatusOK, Body: pull23},
		// The repository's merge settings are one read for the whole run; branch
		// enforcement is deliberately left unrouted, so the 404 exercises the
		// "protection exists but names nothing" path rather than an unknown-evidence one.
		repo: {Status: http.StatusOK, Body: `{"allow_squash_merge":true,"allow_rebase_merge":false,"allow_merge_commit":false}`},
	}}
	// Routes are keyed by "METHOD /path"; building them from the path alone above keeps
	// the table readable, so they are re-keyed here.
	routes := map[string]ghtest.Response{}
	for path, response := range transport.Routes {
		routes[http.MethodGet+" "+path] = response
	}
	// The merge-state read is the one GraphQL call these surfaces make, and it is a
	// query: POST is the transport GitHub requires for a read here, which is why the
	// read-only assertion below tests the operation rather than the HTTP method.
	routes[http.MethodPost+" /graphql"] = ghtest.Response{Status: http.StatusOK, Body: `{"data":{"repository":
		{"pullRequest":{"id":"PR_node","mergeStateStatus":"CLEAN","reviewDecision":""}}}}`}
	transport.Routes = routes

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
	return cli.Run(context.Background(), h.env, args)
}

// files lists every file in the harness checkout, which is what makes "this surface
// writes nothing" assertable: payload 1.5 removed the one subcommand that wrote a file,
// and a regression would land as a new path here rather than as a failed golden.
func (h *harness) files(t *testing.T) []string {
	t.Helper()

	var found []string
	if err := filepath.WalkDir(h.root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.IsDir() {
			found = append(found, path)
		}
		return nil
	}); err != nil {
		t.Fatalf("walking the harness checkout: %v", err)
	}
	sort.Strings(found)
	return found
}

func (h *harness) assertReadOnly(t *testing.T) {
	t.Helper()
	// GraphQL queries are POSTs by protocol, so the invariant is "no mutation", proved
	// from the request body rather than from the method: a `mutation` keyword reaching
	// the transport is a write, and nothing else that is not a GET may.
	for i, method := range h.transport.Methods() {
		if method == http.MethodGet {
			continue
		}
		body := h.transport.Bodies()[i]
		if method != http.MethodPost || strings.Contains(body, "mutation") {
			t.Errorf("a rendering subcommand issued a %s request (%s); these surfaces are reads", method, body)
		}
	}
}

var timestampPattern = regexp.MustCompile(`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z`)

// requireReadTimestamp asserts that rendered carries a read timestamp which is a real,
// recent UTC instant.
func requireReadTimestamp(t *testing.T, rendered string) {
	t.Helper()

	stamps := timestampPattern.FindAllString(rendered, -1)
	if len(stamps) == 0 {
		t.Fatalf("rendered output carries no read timestamp:\n%s", rendered)
	}
	read, err := time.Parse(time.RFC3339, stamps[0])
	if err != nil {
		t.Fatalf("time.Parse(%q) error = %v", stamps[0], err)
	}
	if elapsed := time.Since(read); elapsed < -time.Minute || elapsed > time.Hour {
		t.Errorf("read timestamp %s is not the time of this run", stamps[0])
	}
}

// freeze replaces the read timestamp — the one value a live run cannot repeat — with the
// fixture's, after checking it is a real, recent UTC instant. Everything else must match
// the golden byte for byte.
func freeze(t *testing.T, rendered string) string {
	t.Helper()

	requireReadTimestamp(t, rendered)
	return timestampPattern.ReplaceAllString(rendered, fixtureRead)
}

func TestSummaryZeroArgumentRunMatchesGolden(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	before := h.files(t)
	if got := h.run("summary"); got != cli.ExitOK {
		t.Fatalf("summary = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	if got, want := freeze(t, h.stdout.String()), golden(t, "summary.md"); got != want {
		t.Errorf("summary mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
	if got := h.files(t); !slices.Equal(got, before) {
		t.Errorf("summary changed the checkout's files; it prints and nothing more\n--- got ---\n%v\n--- want ---\n%v", got, before)
	}
	h.assertReadOnly(t)
}

// The JSON summary is the DR-004 envelope with an additive `items` projection: the
// envelope members sit at the top level exactly as every other command emits them, and
// `findings` retains every finding the compressed human view merged into one line per
// work item per category.
func TestSummaryJSONOutput(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if got := h.run("summary", "--output", "json"); got != cli.ExitOK {
		t.Fatalf("summary --output json = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	var decoded struct {
		SchemaVersion string  `json:"schema_version"`
		Command       string  `json:"command"`
		Result        string  `json:"result"`
		Gate          *string `json:"gate"`
		Target        struct {
			Kind       string `json:"kind"`
			Repository string `json:"repository"`
		} `json:"target"`
		Findings []struct {
			Code     string `json:"code"`
			Category string `json:"category"`
			Kind     string `json:"kind"`
			Number   int    `json:"number"`
		} `json:"findings"`
		Steps  []any  `json:"steps"`
		ReadAt string `json:"read_at"`
		Counts struct {
			OpenIssues       int `json:"open_issues"`
			OpenPullRequests int `json:"open_pull_requests"`
			Findings         int `json:"findings"`
		} `json:"counts"`
		Items struct {
			Issues []struct {
				Number int               `json:"number"`
				Type   string            `json:"type"`
				Fields map[string]string `json:"fields"`
			} `json:"issues"`
			PullRequests []struct {
				Number         int    `json:"number"`
				Relationship   string `json:"relationship"`
				GoverningIssue int    `json:"governing_issue"`
				CI             string `json:"ci"`
			} `json:"pull_requests"`
		} `json:"items"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error = %v, output:\n%s", err, h.stdout)
	}
	if decoded.SchemaVersion != cli.EnvelopeSchemaVersion || decoded.Command != "summary" {
		t.Errorf("schema_version/command = %q/%q", decoded.SchemaVersion, decoded.Command)
	}
	// summary is a report, not a gate: it evaluates no single phase, so `gate` is null.
	if decoded.Gate != nil {
		t.Errorf("gate = %q, want null", *decoded.Gate)
	}
	if decoded.Target.Kind != string(cli.TargetRepository) || decoded.Target.Repository != fixtureTarget {
		t.Errorf("target = %+v", decoded.Target)
	}
	if decoded.Steps == nil {
		t.Error("steps is null; the envelope's collections are always arrays")
	}
	if decoded.Counts.OpenIssues != 4 || decoded.Counts.OpenPullRequests != 3 {
		t.Errorf("counts = %+v, want 4 issues and 3 pull requests", decoded.Counts)
	}
	// The human view compresses; JSON does not. Every finding is present individually,
	// which is why the count exceeds the number of lines the summary printed.
	if len(decoded.Findings) != decoded.Counts.Findings || len(decoded.Findings) < 9 {
		t.Errorf("findings = %d entries, count field %d, want every finding",
			len(decoded.Findings), decoded.Counts.Findings)
	}
	if decoded.Result != string(cli.ResultDomainFinding) {
		t.Errorf("result = %q, want %q with findings present", decoded.Result, cli.ResultDomainFinding)
	}
	if len(decoded.Items.Issues) != 4 || decoded.Items.Issues[0].Fields["Workflow"] != "Blocked" {
		t.Errorf("issues = %+v", decoded.Items.Issues)
	}
	if len(decoded.Items.PullRequests) != 3 ||
		decoded.Items.PullRequests[0].Relationship != "Final" ||
		decoded.Items.PullRequests[0].GoverningIssue != 12 ||
		decoded.Items.PullRequests[0].CI != "passing" {
		t.Errorf("pull_requests = %+v", decoded.Items.PullRequests)
	}
	if got := decoded.Items.PullRequests[2].GoverningIssue; got != 0 {
		t.Errorf("the Standalone PR reports governing issue #%d; a declaration is the only authority", got)
	}
}

func TestReceiptRendersOneItemInEitherMode(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		args   []string
		golden string
	}{
		{"issue", []string{"receipt", "--issue", "12"}, "receipt-issue.txt"},
		{"issue with gaps", []string{"receipt", "--issue", "14"}, "receipt-issue-gaps.txt"},
		{"pull request", []string{"receipt", "--pr", "21"}, "receipt-pr.txt"},
		{"pull request with gaps", []string{"receipt", "--pr", "22"}, "receipt-pr-gaps.txt"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			if got := h.run(tc.args...); got != cli.ExitOK {
				t.Fatalf("%v = %d, want %d (stderr: %s)", tc.args, got, cli.ExitOK, h.stderr)
			}
			if got, want := h.stdout.String(), golden(t, tc.golden); got != want {
				t.Errorf("receipt mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
			}
			h.assertReadOnly(t)
		})
	}

	t.Run("json", func(t *testing.T) {
		t.Parallel()

		h := newHarness(t)
		if got := h.run("receipt", "--issue", "14", "--output", "json"); got != cli.ExitOK {
			t.Fatalf("receipt --output json = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
		}
		var decoded struct {
			Item struct {
				Kind   string            `json:"kind"`
				Number int               `json:"number"`
				Fields map[string]string `json:"fields"`
			} `json:"item"`
			Gaps []string `json:"gaps"`
		}
		if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
			t.Fatalf("json.Unmarshal() error = %v, output:\n%s", err, h.stdout)
		}
		if decoded.Item.Kind != "issue" || decoded.Item.Number != 14 {
			t.Errorf("item = %+v", decoded.Item)
		}
		if strings.Join(decoded.Gaps, ",") != "Change risk,Target date,acceptance criteria" {
			t.Errorf("gaps = %v", decoded.Gaps)
		}
	})
}

func TestUsageFailures(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		args []string
	}{
		{"receipt without a selector", []string{"receipt"}},
		{"receipt with both selectors", []string{"receipt", "--issue", "12", "--pr", "21"}},
		{"receipt with a positional argument", []string{"receipt", "12"}},
		{"summary with an unknown output mode", []string{"summary", "--output", "yaml"}},
		{"summary with a malformed repository", []string{"summary", "--repo", "a/b/c"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			h := newHarness(t)
			if got := h.run(tc.args...); got != cli.ExitUsage {
				t.Errorf("%v = %d, want %d (stderr: %s)", tc.args, got, cli.ExitUsage, h.stderr)
			}
			if h.stdout.Len() != 0 {
				t.Errorf("usage failure wrote to stdout: %q", h.stdout)
			}
		})
	}
}

// A bare --repo name is completed from the rendered policy, which is the only place the
// tool learns the organization when the checkout cannot say (IR-004, DR-002).
func TestBareRepositoryNameIsCompletedFromPolicy(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if err := os.Remove(filepath.Join(h.root, ".git", "config")); err != nil {
		t.Fatalf("Remove error = %v", err)
	}
	if got := h.run("summary", "--repo", "example-repo"); got != cli.ExitOK {
		t.Fatalf("summary --repo example-repo = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	if !strings.Contains(h.stdout.String(), fixtureTarget) {
		t.Errorf("summary targeted the wrong repository:\n%s", h.stdout)
	}
}

func TestUnresolvableRepositoryFailsWithoutOutput(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if err := os.Remove(filepath.Join(h.root, ".git", "config")); err != nil {
		t.Fatalf("Remove error = %v", err)
	}
	if got := h.run("summary"); got != cli.ExitFailure {
		t.Fatalf("summary = %d, want %d", got, cli.ExitFailure)
	}
	if h.stdout.Len() != 0 {
		t.Errorf("unmet precondition still produced output: %q", h.stdout)
	}
	if !strings.Contains(h.stderr.String(), "--repo") {
		t.Errorf("the failure does not tell the operator how to proceed: %q", h.stderr)
	}
}

// ---------------------------------------------------------------- NFR-008 call counts

// nfr008Harness narrows the fixture repository to the minimum that still exercises every
// branch of the summary read plan: one issue, one open non-draft Final (which reaches the
// Merge gate and its evidence reads), and one draft Supporting (which stops at Ready).
// The full fixture set would prove the same bound with a number nobody can enumerate.
func nfr008Harness(t *testing.T) *harness {
	t.Helper()

	h := newHarness(t)
	h.transport.Routes[http.MethodGet+" /repos/L3DigitalNet/example-repo/issues"] =
		ghtest.Response{Status: http.StatusOK, Body: "[" + issue12 + "]"}
	h.transport.Routes[http.MethodGet+" /repos/L3DigitalNet/example-repo/pulls"] =
		ghtest.Response{Status: http.StatusOK, Body: "[" + pull21 + "," + pull22 + "]"}
	return h
}

// NFR-008 ("shared live reads are reused within one command") measured on the summary.
// The enumeration below IS the assertion — the number alone would drift into meaning
// nothing, and a reader who cannot map it back to a call cannot tell a new read from a
// reintroduced duplicate.
//
//	1  GET /issues                     the open-issue list
//	2  GET /pulls                      the open-PR list, read ONCE for the whole command
//	3  GET /commits/aaa111/check-runs  CI for #21, retained for its Merge evidence below
//	4  GET /commits/bbb222/check-runs  CI for #22 — empty, so it falls back to
//	5  GET /commits/bbb222/status      the commit-status surface
//	6  GET /pulls/21                   #21's topology: the pull request,
//	7  POST /graphql                   its mergeStateStatus, and
//	8  GET /issues/12                  its governing issue
//	9  GET /repos/{owner}/{repo}       #21 infers the Merge gate, so its evidence follows:
//	10 GET /rules/branches/main        repository merge settings, rulesets, and
//	11 GET /branches/main/protection   classic protection — the required-check runs are
//	                                   call 3 reused, not a fourth read
//	12 GET /pulls/22                   #22's topology: draft, so it stops at Ready —
//	13 POST /graphql                   no merge evidence is read for it
//	14 GET /issues/14                  its governing issue
//
// Calls 2 and 3 are what this bound turns on, and each was a separate duplicate before the
// prefetch: every open non-draft Final re-read the same `state=open` list to answer the
// one-open-Final rule, and re-read the same commit's check runs its CI column already
// consumed. This fixture cost 16; a repository with n such Finals paid 2n avoidable calls.
func TestSummaryReusesSharedReadsWithinOneCommand(t *testing.T) {
	t.Parallel()

	h := nfr008Harness(t)
	if code := h.run("summary"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	if got := h.transport.Count(); got != 14 {
		t.Errorf("summary issued %d requests, want 14:\n%s", got, requestLog(h))
	}
	// The list read is the invariant, not the total: one `state=open` list per command,
	// however many pull requests it then loads.
	if got := countPath(h, "/repos/L3DigitalNet/example-repo/pulls"); got != 1 {
		t.Errorf("the open-PR list was read %d times, want 1:\n%s", got, requestLog(h))
	}
	// Each shared read is pinned on its own, not just through the total: a future call
	// added elsewhere would move the total without telling anyone which reuse broke.
	// aaa111 is #21's head, read for its CI column and consumed again by the Merge gate's
	// required-check predicate.
	if got := countPath(h, "/repos/L3DigitalNet/example-repo/commits/aaa111/check-runs"); got != 1 {
		t.Errorf("#21's check runs were read %d times, want 1:\n%s", got, requestLog(h))
	}
	h.assertReadOnly(t)
}

// The single-gate surface keeps loading everything itself: with one pull request there is
// nothing to share, and a prefetch would only hide the read set from its own call site.
//
//	1  GET /pulls/21                   the pull request,
//	2  POST /graphql                   its mergeStateStatus, and
//	3  GET /issues/12                  its governing issue
//	4  GET /pulls                      the open-PR list, for the one-open-Final rule
//	5  GET /repos/{owner}/{repo}       Merge-gate evidence: merge settings,
//	6  GET /rules/branches/main        rulesets,
//	7  GET /branches/main/protection   classic protection, and
//	8  GET /commits/aaa111/check-runs  the required-check runs
//	9  GET /pulls/21                   the receipt's own projection of the same PR, and
//	10 GET /commits/aaa111/check-runs  its CI state
//
// Calls 9 and 10 restate 1 and 8: the receipt builds its display item through the render
// fetch path rather than from the topology it just loaded, so the two halves each perform
// their own reads. Closing that needs the receipt restructured to project the topology it
// already holds, which is a behavior question this change does not own; the count is
// pinned here so closing it shows up as a deliberate edit to this number.
func TestReceiptPullRequestCallCount(t *testing.T) {
	t.Parallel()

	h := nfr008Harness(t)
	if code := h.run("receipt", "--pr", "21"); code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstderr: %s", code, h.stderr)
	}
	if got := h.transport.Count(); got != 10 {
		t.Errorf("receipt --pr issued %d requests, want 10:\n%s", got, requestLog(h))
	}
	h.assertReadOnly(t)
}

func countPath(h *harness, path string) int {
	count := 0
	for _, req := range h.transport.Requests() {
		if req.URL.Path == path {
			count++
		}
	}
	return count
}

// requestLog renders the recorded calls for a failure message, because a bare count tells
// the next reader which assertion broke but never which call was added or dropped.
func requestLog(h *harness) string {
	var b strings.Builder
	for i, req := range h.transport.Requests() {
		fmt.Fprintf(&b, "  %2d %s %s\n", i+1, req.Method, req.URL.Path)
	}
	return b.String()
}
