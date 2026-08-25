package render_test

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"

	// The three subcommands register themselves; importing the package under test is
	// what wires them into the registry, exactly as cmd/gh-workflow does.
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

const (
	fixtureToken  = "gho_fixturetokenvalue"
	fixtureBase   = "https://api.github.test"
	fixturePolicy = "organization = \"L3DigitalNet\"\npackage_version = \"1.0\"\n"
	fixtureGit    = "[core]\n\trepositoryformatversion = 0\n[remote \"origin\"]\n\turl = git@github.com:L3DigitalNet/example-repo.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n"

	ledgerRelPath = "docs/GH-WORKFLOWS.md"
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
	// fixture must agree on the one title that pins the ledger golden's bare-underscore
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

	pull21 = `{"number":21,"title":"Add the render engine",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/21",
		"state":"open","draft":false,"body":"Closes #12","head":{"sha":"aaa111"}}`

	pull22 = `{"number":22,"title":"Tidy the fixture corpus",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/22",
		"state":"open","draft":true,"body":"Housekeeping only.","head":{"sha":"bbb222"}}`
)

// pull23 is the emoji-width row (#185). Its title is spliced from emojiWidthTitle rather
// than written out here, so the wire fixture and the model fixture cannot drift into
// disagreeing about the one cell whose padding the golden exists to pin. Every character
// in it is JSON-safe, so no escaping step stands between the constant and the payload.
const pull23 = `{"number":23,"title":"` + emojiWidthTitle + `",
		"html_url":"https://github.com/L3DigitalNet/example-repo/pull/23",
		"state":"open","draft":false,"body":"Closes #14","head":{"sha":"ccc333"}}`

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
	}}
	// Routes are keyed by "METHOD /path"; building them from the path alone above keeps
	// the table readable, so they are re-keyed here.
	routes := map[string]ghtest.Response{}
	for path, response := range transport.Routes {
		routes[http.MethodGet+" "+path] = response
	}
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

func (h *harness) ledgerPath() string {
	return filepath.Join(h.root, filepath.FromSlash(ledgerRelPath))
}

func (h *harness) assertReadOnly(t *testing.T) {
	t.Helper()
	for _, method := range h.transport.Methods() {
		if method != http.MethodGet {
			t.Errorf("a rendering subcommand issued a %s request; these surfaces are reads", method)
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
//
// Only the summary needs this now: the ledger carries no timestamp, so its live output is
// compared to its golden unfrozen (issue #154).
func freeze(t *testing.T, rendered string) string {
	t.Helper()

	requireReadTimestamp(t, rendered)
	return timestampPattern.ReplaceAllString(rendered, fixtureRead)
}

func TestLedgerZeroArgumentRunWritesTheGoldenFile(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if got := h.run("ledger"); got != cli.ExitOK {
		t.Fatalf("ledger = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	data, err := os.ReadFile(h.ledgerPath())
	if err != nil {
		t.Fatalf("the ledger was not written to %s: %v", ledgerRelPath, err)
	}
	// Unfrozen: a live run of an unchanged repository must reproduce the golden exactly,
	// timestamp substitution included — that is issue #154's whole guarantee.
	if got, want := string(data), golden(t, "ledger.md"); got != want {
		t.Errorf("ledger file mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}

	out := h.stdout.String()
	for _, want := range []string{ledgerRelPath, "4 open issues", "3 open PRs"} {
		if !strings.Contains(out, want) {
			t.Errorf("confirmation line %q missing %q", out, want)
		}
	}
	// The read time did not vanish with the file header; it moved to stdout, which the
	// consumer does not commit.
	requireReadTimestamp(t, out)
	if strings.Contains(out, fixtureToken) || strings.Contains(h.stderr.String(), fixtureToken) {
		t.Error("output contains the token value; IR-002 forbids credential material in output")
	}
	h.assertReadOnly(t)
}

// Issue #154: regenerating against unchanged work state must produce no diff. This is
// the end-to-end form of the unit-level guarantee — two real runs of the command, minutes
// or milliseconds apart, writing the same bytes — because the churn the consumer reported
// was observed here, at `git diff`, not in the renderer.
func TestLedgerRegeneratedAgainstUnchangedStateWritesIdenticalBytes(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if got := h.run("ledger"); got != cli.ExitOK {
		t.Fatalf("first ledger = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	first, err := os.ReadFile(h.ledgerPath())
	if err != nil {
		t.Fatalf("reading the first ledger: %v", err)
	}

	if got := h.run("ledger"); got != cli.ExitOK {
		t.Fatalf("second ledger = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	second, err := os.ReadFile(h.ledgerPath())
	if err != nil {
		t.Fatalf("reading the second ledger: %v", err)
	}

	if !bytes.Equal(first, second) {
		t.Errorf("regeneration changed the file\n--- first ---\n%s\n--- second ---\n%s", first, second)
	}
}

func TestLedgerFailingTransportLeavesThePriorFileIntact(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if err := os.MkdirAll(filepath.Dir(h.ledgerPath()), 0o750); err != nil {
		t.Fatalf("MkdirAll error = %v", err)
	}
	const prior = "# prior ledger\n"
	if err := os.WriteFile(h.ledgerPath(), []byte(prior), 0o600); err != nil {
		t.Fatalf("WriteFile error = %v", err)
	}
	h.transport.Err = http.ErrServerClosed

	if got := h.run("ledger"); got != cli.ExitFailure {
		t.Fatalf("ledger = %d, want %d", got, cli.ExitFailure)
	}
	data, err := os.ReadFile(h.ledgerPath())
	if err != nil {
		t.Fatalf("ReadFile error = %v", err)
	}
	if string(data) != prior {
		t.Errorf("a failed read rewrote the ledger:\n%s", data)
	}
	if h.stdout.Len() != 0 {
		t.Errorf("failed run wrote to stdout: %q", h.stdout)
	}
}

func TestSummaryZeroArgumentRunMatchesGolden(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if got := h.run("summary"); got != cli.ExitOK {
		t.Fatalf("summary = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}
	if got, want := freeze(t, h.stdout.String()), golden(t, "summary.md"); got != want {
		t.Errorf("summary mismatch\n--- got ---\n%s\n--- want ---\n%s", got, want)
	}
	if _, err := os.Stat(h.ledgerPath()); !os.IsNotExist(err) {
		t.Error("summary wrote the ledger file; it prints and nothing more")
	}
	h.assertReadOnly(t)
}

func TestSummaryJSONOutput(t *testing.T) {
	t.Parallel()

	h := newHarness(t)
	if got := h.run("summary", "--output", "json"); got != cli.ExitOK {
		t.Fatalf("summary --output json = %d, want %d (stderr: %s)", got, cli.ExitOK, h.stderr)
	}

	var decoded struct {
		Target string `json:"target"`
		ReadAt string `json:"read_at"`
		Counts struct {
			OpenIssues       int `json:"open_issues"`
			OpenPullRequests int `json:"open_pull_requests"`
			NeedsAttention   int `json:"needs_attention"`
		} `json:"counts"`
		NeedsAttention []struct {
			Category string `json:"category"`
			Number   int    `json:"number"`
		} `json:"needs_attention"`
		Issues []struct {
			Number int               `json:"number"`
			Type   string            `json:"type"`
			Fields map[string]string `json:"fields"`
		} `json:"issues"`
		PullRequests []struct {
			Number         int    `json:"number"`
			GoverningIssue int    `json:"governing_issue"`
			CI             string `json:"ci"`
		} `json:"pull_requests"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("json.Unmarshal() error = %v, output:\n%s", err, h.stdout)
	}
	if decoded.Target != fixtureTarget {
		t.Errorf("target = %q, want %q", decoded.Target, fixtureTarget)
	}
	if decoded.Counts.OpenIssues != 4 || decoded.Counts.OpenPullRequests != 3 {
		t.Errorf("counts = %+v, want 4 issues and 3 pull requests", decoded.Counts)
	}
	if decoded.Counts.NeedsAttention != len(decoded.NeedsAttention) || len(decoded.NeedsAttention) != 5 {
		t.Errorf("needs_attention = %d entries, count field %d, want 5",
			len(decoded.NeedsAttention), decoded.Counts.NeedsAttention)
	}
	if len(decoded.Issues) != 4 || decoded.Issues[0].Fields["Workflow"] != "Blocked" {
		t.Errorf("issues = %+v", decoded.Issues)
	}
	if len(decoded.PullRequests) != 3 || decoded.PullRequests[0].GoverningIssue != 12 ||
		decoded.PullRequests[0].CI != "passing" {
		t.Errorf("pull_requests = %+v", decoded.PullRequests)
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
