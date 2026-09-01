package ghapi_test

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghtest"
)

const (
	repoRoot   = "/repos/L3DigitalNet/example-repo"
	checksPath = repoRoot + "/commits/abc123/check-runs"
)

// DEV-024 regression pin: through 1.6 the check-runs reader took the first page and
// discarded the continuation, so a failing run on page two rendered as `passing`. The
// verdict here is only correct if both pages were read.
func TestCheckRunsPaginateAcrossPages(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{}
	transport.RouteFunc = func(req *http.Request) (ghtest.Response, bool) {
		if req.URL.Path != checksPath {
			return ghtest.Response{}, false
		}
		if req.URL.Query().Get("page") == "2" {
			return ghtest.Response{Status: http.StatusOK, Body: `{"total_count":3,"check_runs":[
				{"name":"gate","status":"completed","conclusion":"failure"}]}`}, true
		}
		next := "https://api.github.test" + checksPath + "?per_page=100&page=2"
		return ghtest.Response{
			Status: http.StatusOK,
			Body: `{"total_count":3,"check_runs":[
				{"name":"lint","status":"completed","conclusion":"success"},
				{"name":"build","status":"completed","conclusion":"success"}]}`,
			Header: http.Header{"Link": []string{fmt.Sprintf(`<%s>; rel="next"`, next)}},
		}, true
	}

	client := newClient(t, transport)
	runs, err := client.ListCheckRunsForRef(context.Background(), "L3DigitalNet", "example-repo", "abc123")
	if err != nil {
		t.Fatalf("ListCheckRunsForRef() error = %v, want nil", err)
	}
	if len(runs) != 3 {
		t.Fatalf("ListCheckRunsForRef() returned %d runs, want 3 across both pages", len(runs))
	}
	if got := transport.Requests()[0].URL.Query().Get("per_page"); got != "100" {
		t.Errorf("per_page = %q, want 100 (NFR-007's largest safe page size)", got)
	}

	state, err := client.CIState(context.Background(), "L3DigitalNet", "example-repo", "abc123")
	if err != nil {
		t.Fatalf("CIState() error = %v, want nil", err)
	}
	if state != ghapi.CIFailing {
		t.Errorf("CIState() = %q, want %q: the failing run is on page two", state, ghapi.CIFailing)
	}
}

// An advertised total the pages never reach is the failure that otherwise looks like
// success, so it must fail closed rather than return the short list.
func TestCheckRunsRefuseAnUnexplainedShortRead(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + checksPath: {Status: http.StatusOK, Body: `{"total_count":7,"check_runs":[
			{"name":"lint","status":"completed","conclusion":"success"}]}`},
	}}

	_, err := newClient(t, transport).ListCheckRunsForRef(
		context.Background(), "L3DigitalNet", "example-repo", "abc123")
	if !errors.Is(err, ghapi.ErrPaginationTruncated) {
		t.Fatalf("ListCheckRunsForRef() error = %v, want ErrPaginationTruncated", err)
	}
	if !ghapi.IsOperational(err) {
		t.Errorf("truncation error = %v, want it marked operational", err)
	}

	// The verdict must not degrade to a cheerful default either: CIState propagates the
	// failure rather than reporting the one decoded run as passing.
	if _, err := newClient(t, transport).CIState(
		context.Background(), "L3DigitalNet", "example-repo", "abc123"); !errors.Is(err, ghapi.ErrPaginationTruncated) {
		t.Errorf("CIState() error = %v, want the truncation to propagate", err)
	}
}

// A total larger than one page is explained by the next link, so a complete walk is not a
// truncation even though page one alone falls short.
func TestListsCompareTheAdvertisedTotalHeader(t *testing.T) {
	t.Parallel()

	commentsPath := repoRoot + "/issues/7/comments"
	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + commentsPath: {
			Status: http.StatusOK,
			Body:   `[{"body":"one","user":{"login":"octocat"}}]`,
			Header: http.Header{"X-Total-Count": []string{"4"}},
		},
	}}

	_, err := newClient(t, transport).ListIssueComments(
		context.Background(), "L3DigitalNet", "example-repo", 7)
	if !errors.Is(err, ghapi.ErrPaginationTruncated) {
		t.Fatalf("ListIssueComments() error = %v, want ErrPaginationTruncated", err)
	}
}

func TestGetPullRequestCarriesTheFullShape(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + repoRoot + "/pulls/12": {Status: http.StatusOK, Body: `{
			"number":12,"node_id":"PR_kwABC","title":"Add ready","state":"open","draft":false,
			"body":"## Governing work\nFinal: #4","merged":false,"merged_at":null,"closed_at":null,
			"base":{"ref":"testing","sha":"base1"},"head":{"ref":"topic","sha":"head1"},
			"mergeable":null,"auto_merge":{"merge_method":"squash"},
			"labels":[{"name":"standards"},{"name":"go"}]}`},
	}}

	pr, err := newClient(t, transport).GetPullRequest(
		context.Background(), "L3DigitalNet", "example-repo", 12)
	if err != nil {
		t.Fatalf("GetPullRequest() error = %v, want nil", err)
	}
	if pr.NodeID != "PR_kwABC" || pr.Base.Ref != "testing" || pr.Head.SHA != "head1" {
		t.Errorf("GetPullRequest() = %+v, want node id and both refs decoded", pr)
	}
	// Mergeable is tri-state: a null must arrive as "not known yet", never as false.
	if pr.Mergeable != nil {
		t.Errorf("Mergeable = %v, want nil for GitHub's pending computation", *pr.Mergeable)
	}
	if enabled, method := pr.AutoMergeEnabled(); !enabled || method != "squash" {
		t.Errorf("AutoMergeEnabled() = %v, %q, want true, \"squash\"", enabled, method)
	}
	if pr.IsMerged() {
		t.Error("IsMerged() = true, want false for an open pull request")
	}
	if got := strings.Join(pr.LabelNames(), ","); got != "standards,go" {
		t.Errorf("LabelNames() = %q, want the response order preserved", got)
	}
}

// GraphQL reports refusals in a 200 response body, so status is not the verdict.
func TestGraphQLErrorArrayIsAFailure(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"POST /graphql": {Status: http.StatusOK, Body: `{"data":null,"errors":[
			{"type":"FORBIDDEN","message":"Resource not accessible by integration"}]}`},
	}}

	err := newClient(t, transport).MarkPullRequestReady(context.Background(), "PR_kwABC")
	if err == nil {
		t.Fatal("MarkPullRequestReady() = nil, want the GraphQL errors reported as a failure")
	}
	if !strings.Contains(err.Error(), "FORBIDDEN") {
		t.Errorf("error = %q, want the GraphQL error type named", err)
	}
	if !ghapi.IsOperational(err) {
		t.Errorf("error = %v, want it marked operational", err)
	}
}

func TestGraphQLMutationsSendTheDocumentedOperations(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"POST /graphql": {Status: http.StatusOK, Body: `{"data":{}}`},
	}}
	client := newClient(t, transport)

	if err := client.MarkPullRequestReady(context.Background(), "PR_kwABC"); err != nil {
		t.Fatalf("MarkPullRequestReady() error = %v, want nil", err)
	}
	if body := transport.LastBody(); !strings.Contains(body, "markPullRequestReadyForReview") {
		t.Errorf("request body = %q, want the markPullRequestReadyForReview mutation", body)
	}

	if err := client.EnableAutoMerge(context.Background(), "PR_kwABC", ghapi.MergeMethodSquash); err != nil {
		t.Fatalf("EnableAutoMerge() error = %v, want nil", err)
	}
	body := transport.LastBody()
	if !strings.Contains(body, "enablePullRequestAutoMerge") {
		t.Errorf("request body = %q, want the enablePullRequestAutoMerge mutation", body)
	}
	// REST spells the method lowercase and GraphQL demands the enum; callers use one
	// spelling and the client converts.
	if !strings.Contains(body, `"SQUASH"`) {
		t.Errorf("request body = %q, want the GraphQL enum spelling", body)
	}

	if err := client.EnableAutoMerge(context.Background(), "PR_kwABC", "fast-forward"); err == nil {
		t.Error("EnableAutoMerge() accepted a method GitHub does not define")
	}
}

func TestGetPullRequestMergeStateReadsTheGraphQLOnlyFields(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"POST /graphql": {Status: http.StatusOK, Body: `{"data":{"repository":{"pullRequest":{
			"id":"PR_kwABC","mergeStateStatus":"BLOCKED","reviewDecision":"REVIEW_REQUIRED"}}}}`},
	}}

	state, err := newClient(t, transport).GetPullRequestMergeState(
		context.Background(), "L3DigitalNet", "example-repo", 12)
	if err != nil {
		t.Fatalf("GetPullRequestMergeState() error = %v, want nil", err)
	}
	if state.MergeStateStatus != "BLOCKED" || state.ReviewDecision != "REVIEW_REQUIRED" {
		t.Errorf("GetPullRequestMergeState() = %+v, want both GraphQL-only fields", state)
	}
	if transport.Count() != 1 {
		t.Errorf("made %d calls, want exactly 1 (NFR-008)", transport.Count())
	}
}

func TestMergePullRequestPinsTheValidatedHead(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"PUT " + repoRoot + "/pulls/12/merge": {
			Status: http.StatusOK,
			Body:   `{"sha":"merged1","merged":true,"message":"Pull Request successfully merged"}`,
		},
	}}
	client := newClient(t, transport)

	const headSHA = "111111111111111111111111111111111111111a"

	result, err := client.MergePullRequest(context.Background(), "L3DigitalNet", "example-repo", 12,
		ghapi.MergeMethodSquash, headSHA, "Workflow-Admission: PR #12\n")
	if err != nil {
		t.Fatalf("MergePullRequest() error = %v, want nil", err)
	}
	if !result.Merged || result.SHA != "merged1" {
		t.Errorf("MergePullRequest() = %+v, want the merge commit reported", result)
	}
	// The head SHA is what makes admission conditional on the state that was validated.
	if body := transport.LastBody(); !strings.Contains(body, `"sha":"`+headSHA+`"`) {
		t.Errorf("request body = %q, want the validated head SHA sent", body)
	}
	// The admission trailer only becomes repository history if it reaches the wire; a
	// caller writing it into a field GitHub ignores would leave the classifier blind.
	if body := transport.LastBody(); !strings.Contains(body, `"commit_message":"Workflow-Admission: PR #12`) {
		t.Errorf("request body = %q, want the admission trailer sent as commit_message", body)
	}

	if _, err := client.MergePullRequest(context.Background(), "L3DigitalNet", "example-repo", 12,
		"fast-forward", headSHA, ""); err == nil {
		t.Error("MergePullRequest() accepted a method GitHub does not define")
	}

	if _, err := client.MergePullRequest(context.Background(), "L3DigitalNet", "example-repo", 12,
		ghapi.MergeMethodSquash, "", ""); err == nil {
		t.Error("MergePullRequest() accepted an empty head SHA")
	} else if transport.Count() != 1 {
		t.Errorf("made %d calls after refusing an empty head SHA, want exactly the 1 from the earlier merge", transport.Count())
	}

	if _, err := client.MergePullRequest(context.Background(), "L3DigitalNet", "example-repo", 12,
		ghapi.MergeMethodSquash, "not-hex", ""); err == nil {
		t.Error("MergePullRequest() accepted a malformed head SHA")
	}
}

// TestMergeMethodNormalizationIsSharedAcrossSurfaces pins the two merge-method acceptors
// (MergePullRequest's REST switch and graphqlMergeMethod, exercised via EnableAutoMerge)
// to the same closed set after case-folding and trimming — a caller-supplied "Squash"
// must not be accepted on one surface and rejected on the other.
func TestMergeMethodNormalizationIsSharedAcrossSurfaces(t *testing.T) {
	t.Parallel()

	const headSHA = "111111111111111111111111111111111111111a"

	restTransport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"PUT " + repoRoot + "/pulls/12/merge": {
			Status: http.StatusOK,
			Body:   `{"sha":"merged1","merged":true,"message":"Pull Request successfully merged"}`,
		},
	}}
	if _, err := newClient(t, restTransport).MergePullRequest(context.Background(),
		"L3DigitalNet", "example-repo", 12, "Squash", headSHA, ""); err != nil {
		t.Fatalf("MergePullRequest() error = %v, want nil for a mixed-case method", err)
	}
	// GitHub's REST endpoint accepts only the lowercase enum; the caller's original
	// casing must never reach the wire, or a locally accepted "Squash" fails remotely.
	if body := restTransport.LastBody(); !strings.Contains(body, `"merge_method":"squash"`) {
		t.Errorf("request body = %q, want the normalized lowercase merge_method", body)
	}

	graphqlTransport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"POST /graphql": {Status: http.StatusOK, Body: `{"data":{}}`},
	}}
	if err := newClient(t, graphqlTransport).EnableAutoMerge(context.Background(),
		"PR_kwABC", "Squash"); err != nil {
		t.Fatalf("EnableAutoMerge() error = %v, want nil for a mixed-case method", err)
	}
	if body := graphqlTransport.LastBody(); !strings.Contains(body, `"SQUASH"`) {
		t.Errorf("request body = %q, want the GraphQL enum spelling", body)
	}
}

func TestGetRepositoryMergeSettings(t *testing.T) {
	t.Parallel()

	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + repoRoot: {Status: http.StatusOK, Body: `{
			"allow_squash_merge":true,"allow_rebase_merge":false,
			"allow_merge_commit":true,"delete_branch_on_merge":true}`},
	}}

	settings, err := newClient(t, transport).GetRepositoryMergeSettings(
		context.Background(), "L3DigitalNet", "example-repo")
	if err != nil {
		t.Fatalf("GetRepositoryMergeSettings() error = %v, want nil", err)
	}
	if !settings.Known {
		t.Error("Known = false after a successful read; the Merge phase would fail closed on nothing")
	}
	if !settings.AllowSquash || settings.AllowRebase || !settings.AllowMerge {
		t.Errorf("GetRepositoryMergeSettings() = %+v, want squash and merge permitted, rebase not", settings)
	}
}

// 404 and 403 are the pair that decides admission: absent protection permits a merge,
// unreadable protection does not.
func TestBranchEnforcementDistinguishesAbsentFromUnreadable(t *testing.T) {
	t.Parallel()

	rulesPath := repoRoot + "/rules/branches/testing"
	protectionPath := repoRoot + "/branches/testing/protection"

	t.Run("no ruleset and no protection is knowledge", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + rulesPath:      {Status: http.StatusNotFound, Body: `{"message":"Not Found"}`},
			"GET " + protectionPath: {Status: http.StatusNotFound, Body: `{"message":"Branch not protected"}`},
		}}
		evidence, err := newClient(t, transport).GetBranchEnforcement(
			context.Background(), "L3DigitalNet", "example-repo", "testing")
		if err != nil {
			t.Fatalf("GetBranchEnforcement() error = %v, want nil", err)
		}
		if !evidence.Known || evidence.Source != "none" || len(evidence.RequiredStatusChecks) != 0 {
			t.Errorf("GetBranchEnforcement() = %+v, want known-and-empty", evidence)
		}
	})

	t.Run("a forbidden read is not knowledge", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + rulesPath:      {Status: http.StatusOK, Body: `[]`},
			"GET " + protectionPath: {Status: http.StatusForbidden, Body: `{"message":"Forbidden"}`},
		}}
		evidence, err := newClient(t, transport).GetBranchEnforcement(
			context.Background(), "L3DigitalNet", "example-repo", "testing")
		if err != nil {
			t.Fatalf("GetBranchEnforcement() error = %v, want nil", err)
		}
		if evidence.Known {
			t.Errorf("GetBranchEnforcement() = %+v, want Known false: a 403 is not 'nothing is enforced'", evidence)
		}
	})

	t.Run("both authorities are unioned", func(t *testing.T) {
		t.Parallel()
		transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
			"GET " + rulesPath: {Status: http.StatusOK, Body: `[
				{"type":"required_status_checks","parameters":{"required_status_checks":[{"context":"gate"}]}},
				{"type":"pull_request","parameters":{"required_approving_review_count":0}}]`},
			"GET " + protectionPath: {Status: http.StatusOK, Body: `{
				"required_status_checks":{"contexts":["legacy-ci"]},
				"required_pull_request_reviews":{"required_approving_review_count":1}}`},
		}}
		evidence, err := newClient(t, transport).GetBranchEnforcement(
			context.Background(), "L3DigitalNet", "example-repo", "testing")
		if err != nil {
			t.Fatalf("GetBranchEnforcement() error = %v, want nil", err)
		}
		if !evidence.Known || evidence.Source != "rules+protection" {
			t.Errorf("GetBranchEnforcement() = %+v, want both sources recorded", evidence)
		}
		if got := strings.Join(evidence.RequiredStatusChecks, ","); got != "gate,legacy-ci" {
			t.Errorf("RequiredStatusChecks = %q, want the union of both authorities", got)
		}
		if !evidence.RequiresReview {
			t.Error("RequiresReview = false, want true from classic protection")
		}
	})
}

func TestIssueCommentsAndCreateComment(t *testing.T) {
	t.Parallel()

	commentsPath := repoRoot + "/issues/12/comments"
	transport := &ghtest.Transport{Routes: map[string]ghtest.Response{
		"GET " + commentsPath: {Status: http.StatusOK, Body: `[
			{"body":"Final-Disposition: blocked","created_at":"2026-08-30T10:00:00Z","user":{"login":"octocat"}}]`},
		"POST " + commentsPath: {Status: http.StatusCreated, Body: `{
			"body":"Final-Disposition: dropped","created_at":"2026-08-30T11:00:00Z","user":{"login":"octocat"}}`},
	}}
	client := newClient(t, transport)

	comments, err := client.ListIssueComments(context.Background(), "L3DigitalNet", "example-repo", 12)
	if err != nil {
		t.Fatalf("ListIssueComments() error = %v, want nil", err)
	}
	if len(comments) != 1 || comments[0].AuthorLogin() != "octocat" {
		t.Fatalf("ListIssueComments() = %+v, want one comment by octocat", comments)
	}
	if comments[0].CreatedAt.IsZero() {
		t.Error("CreatedAt is zero; disposition ordering depends on it")
	}

	created, err := client.CreateComment(context.Background(), "L3DigitalNet", "example-repo", 12,
		"Final-Disposition: dropped")
	if err != nil {
		t.Fatalf("CreateComment() error = %v, want nil", err)
	}
	if created.Body != "Final-Disposition: dropped" {
		t.Errorf("CreateComment() = %+v, want the created comment echoed", created)
	}
	if _, err := client.CreateComment(context.Background(), "L3DigitalNet", "example-repo", 12, ""); err == nil {
		t.Error("CreateComment() accepted an empty body")
	}
}
