package relation_test

import (
	"regexp"
	"sort"
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

var testNow = time.Date(2026, 8, 30, 12, 0, 0, 0, time.UTC)

func boolPtr(v bool) *bool { return &v }

// openTopology is a PR that passes every gate: canonical Final, coherent Issue, known
// enforcement with a green required check. Each test mutates the one field it is about,
// so a finding in the result is unambiguously caused by that mutation.
func openTopology() relation.Topology {
	return relation.Topology{
		PullRequest: relation.PullRequest{
			Number: 40, State: "open", Body: completeBody, BaseRef: "main",
			Mergeable:      boolPtr(true),
			ReviewDecision: "APPROVED",
			RequiredChecks: []relation.CheckState{{Name: "gate", Status: "completed", Conclusion: "success"}},
		},
		GoverningIssue: &relation.Issue{
			Number: 12, State: "open", IssueType: "Task", Workflow: relation.WorkflowInReview,
		},
		MergeSettings: relation.RepositoryMergeSettings{AllowSquash: true, Known: true},
		Enforcement: relation.EnforcementEvidence{
			Known: true, RequiredStatusChecks: []string{"gate"}, RequiresReview: true, Source: "branch-protection",
		},
		Now: testNow,
	}
}

func TestInferGate(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		pr   relation.PullRequest
		want relation.Phase
	}{
		{name: "open draft", pr: relation.PullRequest{State: "open", Draft: true}, want: relation.PhaseReady},
		{name: "open ready", pr: relation.PullRequest{State: "open"}, want: relation.PhaseMerge},
		{name: "merged", pr: relation.PullRequest{State: "closed", Merged: true}, want: relation.PhasePostMerge},
		{name: "closed unmerged", pr: relation.PullRequest{State: "closed"}, want: relation.PhasePostMerge},
		{
			name: "draft that was closed is terminal, not ready",
			pr:   relation.PullRequest{State: "closed", Draft: true},
			want: relation.PhasePostMerge,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := relation.InferGate(tc.pr); got != tc.want {
				t.Errorf("InferGate = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestObservedStateFilter(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		pr   relation.PullRequest
		want []relation.Phase
	}{
		{
			name: "draft contributes structural findings only",
			pr:   relation.PullRequest{State: "open", Draft: true},
			want: []relation.Phase{relation.PhaseStructural},
		},
		{
			name: "ready open pr contributes the cumulative pre-event phases",
			pr:   relation.PullRequest{State: "open"},
			want: []relation.Phase{relation.PhaseStructural, relation.PhaseReady, relation.PhaseMerge},
		},
		{
			name: "terminal pr contributes disposition and evidence integrity",
			pr:   relation.PullRequest{State: "closed", Merged: true},
			want: []relation.Phase{relation.PhaseStructural, relation.PhasePostMerge},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := relation.ObservedStateFilter(tc.pr)
			if len(got) != len(tc.want) {
				t.Fatalf("filter = %v, want %v", got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Fatalf("filter = %v, want %v", got, tc.want)
				}
			}
		})
	}
}

func TestEvaluateClearGate(t *testing.T) {
	t.Parallel()

	result := relation.Evaluate(openTopology(), "")
	if !result.Clear() {
		t.Fatalf("findings = %v, want none", codes(result.Findings))
	}
	if result.Gate != relation.PhaseMerge {
		t.Errorf("gate = %q, want %q", result.Gate, relation.PhaseMerge)
	}
	if result.Declaration.Relationship != relation.RelationshipFinal {
		t.Errorf("relationship = %q, want final", result.Declaration.Relationship)
	}
}

// `--through structural` must stop before the Ready predicates: a diagnostic run at a
// shallower gate reports only what that gate owns.
func TestEvaluateStopsAtRequestedPhase(t *testing.T) {
	t.Parallel()

	topology := openTopology()
	topology.PullRequest.Body = strings.Replace(completeBody, "## Verification", "## Notes", 1)
	topology.GoverningIssue.Workflow = "Inbox"

	if got := codes(relation.Evaluate(topology, relation.PhaseStructural).Findings); len(got) != 0 {
		t.Errorf("structural gate = %v, want no findings", got)
	}
	got := codes(relation.Evaluate(topology, relation.PhaseReady).Findings)
	want := []string{"GHW-PR-READY-LIFECYCLE-INCOHERENT", "GHW-PR-READY-SECTION-MISSING"}
	if !equalStrings(got, want) {
		t.Errorf("ready gate = %v, want %v", got, want)
	}
}

func TestEvaluateStructural(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		mutate  func(*relation.Topology)
		through relation.Phase
		want    []string
	}{
		{
			name:   "declared issue does not resolve",
			mutate: func(tp *relation.Topology) { tp.GoverningIssue = nil },
			want:   []string{"GHW-PR-STRUCTURAL-ISSUE-UNRESOLVED"},
		},
		{
			name:   "declared issue is a pull request",
			mutate: func(tp *relation.Topology) { tp.GoverningIssue.IsPullRequestShaped = true },
			want:   []string{"GHW-PR-STRUCTURAL-ISSUE-PULL-REQUEST-SHAPED"},
		},
		{
			name:   "governing issue has no recognized ordinary type",
			mutate: func(tp *relation.Topology) { tp.GoverningIssue.IssueType = "" },
			want:   []string{"GHW-ISSUE-STRUCTURAL-TYPE-MISSING"},
		},
		{
			name: "governing issue is closed under an open pr",
			mutate: func(tp *relation.Topology) {
				tp.GoverningIssue.State = "closed"
				tp.GoverningIssue.StateReason = "completed"
			},
			want: []string{"GHW-ISSUE-STRUCTURAL-CLOSED"},
		},
		{
			name:   "a second open final on the same issue",
			mutate: func(tp *relation.Topology) { tp.SiblingOpenFinals = []int{41} },
			want:   []string{"GHW-PR-STRUCTURAL-FINAL-CARDINALITY"},
		},
		{
			name:   "the accepted closing keyword is allowed on a final",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Body += "\nCloses #12\n" },
			want:   nil,
		},
		{
			name:   "a closing keyword naming another issue",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Body += "\nCloses #99\n" },
			want:   []string{"GHW-PR-STRUCTURAL-CLOSING-KEYWORD"},
		},
		{
			name:   "a closing keyword in the wrong tense",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Body += "\nFixes #12\n" },
			want:   []string{"GHW-PR-STRUCTURAL-CLOSING-KEYWORD"},
		},
		{
			name:   "the accepted keyword repeated",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Body += "\nCloses #12\nCloses #12\n" },
			want:   []string{"GHW-PR-STRUCTURAL-CLOSING-KEYWORD"},
		},
		{
			name: "a closing keyword on a supporting pr",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Supporting: #12", 1) + "\nCloses #12\n"
			},
			want: []string{"GHW-PR-STRUCTURAL-CLOSING-KEYWORD"},
		},
		{
			name: "a passed target date is independent issue attention",
			mutate: func(tp *relation.Topology) {
				past := testNow.Add(-48 * time.Hour)
				tp.GoverningIssue.TargetDate = &past
			},
			want: []string{"GHW-ISSUE-STRUCTURAL-TARGET-DATE-PASSED"},
		},
		{
			name: "a future target date is not a finding",
			mutate: func(tp *relation.Topology) {
				future := testNow.Add(48 * time.Hour)
				tp.GoverningIssue.TargetDate = &future
			},
			want: nil,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			topology := openTopology()
			tc.mutate(&topology)
			through := tc.through
			if through == "" {
				through = relation.PhaseReady
			}
			want := append([]string{}, tc.want...)
			sort.Strings(want)
			if got := codes(relation.Evaluate(topology, through).Findings); !equalStrings(got, want) {
				t.Errorf("codes = %v, want %v", got, want)
			}
		})
	}
}

// The FR-029 lifecycle matrix: relationship × Issue Workflow × gate.
func TestEvaluateLifecycleMatrix(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name         string
		relationship string
		workflow     string
		draft        bool
		through      relation.Phase
		want         []string
	}{
		{name: "draft final in progress", relationship: "Final: #12", workflow: relation.WorkflowInProgress, draft: true, through: relation.PhaseReady},
		{name: "draft final in review", relationship: "Final: #12", workflow: relation.WorkflowInReview, draft: true, through: relation.PhaseReady},
		{name: "draft final blocked", relationship: "Final: #12", workflow: relation.WorkflowBlocked, draft: true, through: relation.PhaseReady},
		{
			name: "draft final on a ready issue", relationship: "Final: #12", workflow: "Ready", draft: true,
			through: relation.PhaseReady, want: []string{"GHW-PR-READY-LIFECYCLE-INCOHERENT"},
		},
		{
			name: "draft final on a done issue", relationship: "Final: #12", workflow: relation.WorkflowDone, draft: true,
			through: relation.PhaseReady, want: []string{"GHW-PR-READY-LIFECYCLE-INCOHERENT"},
		},
		{
			name: "draft final on an issue with no workflow", relationship: "Final: #12", workflow: "", draft: true,
			through: relation.PhaseReady, want: []string{"GHW-PR-READY-LIFECYCLE-INCOHERENT"},
		},
		{
			name: "ready final still in progress", relationship: "Final: #12", workflow: relation.WorkflowInProgress,
			through: relation.PhaseReady, want: []string{"GHW-PR-READY-FINAL-WORKFLOW"},
		},
		{name: "ready final in review", relationship: "Final: #12", workflow: relation.WorkflowInReview, through: relation.PhaseReady},
		{
			name: "ready supporting still in progress", relationship: "Supporting: #12", workflow: relation.WorkflowInProgress,
			through: relation.PhaseReady,
		},
		{
			name: "merge rejects a final while blocked", relationship: "Final: #12", workflow: relation.WorkflowBlocked,
			through: relation.PhaseMerge, want: []string{"GHW-PR-MERGE-FINAL-BLOCKED"},
		},
		{
			name: "merge rejects a supporting pr with no blocked rationale", relationship: "Supporting: #12",
			workflow: relation.WorkflowBlocked, through: relation.PhaseMerge,
			want: []string{"GHW-PR-MERGE-SUPPORTING-BLOCKED-RATIONALE"},
		},
		{
			name: "standalone ignores issue lifecycle entirely", relationship: "Standalone\nChange risk: R1 Low",
			workflow: relation.WorkflowDone, through: relation.PhaseMerge,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			topology := openTopology()
			topology.PullRequest.Body = strings.Replace(completeBody, "Final: #12", tc.relationship, 1)
			topology.PullRequest.Draft = tc.draft
			topology.GoverningIssue.Workflow = tc.workflow
			if strings.HasPrefix(tc.relationship, "Standalone") {
				topology.GoverningIssue = nil
			}
			if tc.draft {
				// The draft predicate is a Merge-gate finding; these rows are about
				// lifecycle, so they never run past Ready.
				topology.PullRequest.Draft = true
			}
			want := append([]string{}, tc.want...)
			sort.Strings(want)
			if got := codes(relation.Evaluate(topology, tc.through).Findings); !equalStrings(got, want) {
				t.Errorf("codes = %v, want %v", got, want)
			}
		})
	}
}

// A Supporting PR may merge while its Issue is Blocked when Acceptance coverage names
// the blocker (FR-029) — the one asymmetry between Final and Supporting.
func TestEvaluateSupportingBlockedRationale(t *testing.T) {
	t.Parallel()

	topology := openTopology()
	topology.GoverningIssue.Workflow = relation.WorkflowBlocked
	topology.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Supporting: #12", 1)
	topology.PullRequest.Body = strings.Replace(topology.PullRequest.Body,
		"Covers every criterion.", "The blocker is upstream and this change neither resolves nor conceals it.", 1)

	if got := relation.Evaluate(topology, relation.PhaseMerge); !got.Clear() {
		t.Errorf("codes = %v, want none", codes(got.Findings))
	}
}

func TestEvaluateMergeEvidence(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		mutate func(*relation.Topology)
		want   []string
	}{
		{
			name:   "enforcement evidence unknown fails closed",
			mutate: func(tp *relation.Topology) { tp.Enforcement = relation.EnforcementEvidence{} },
			want:   []string{"GHW-PR-MERGE-ENFORCEMENT-UNKNOWN"},
		},
		{
			name:   "merge settings unknown fails closed",
			mutate: func(tp *relation.Topology) { tp.MergeSettings = relation.RepositoryMergeSettings{} },
			want:   []string{"GHW-PR-MERGE-SETTINGS-UNKNOWN"},
		},
		{
			name:   "no permitted merge method",
			mutate: func(tp *relation.Topology) { tp.MergeSettings = relation.RepositoryMergeSettings{Known: true} },
			want:   []string{"GHW-PR-MERGE-NO-METHOD"},
		},
		{
			name:   "a required check with no observed run",
			mutate: func(tp *relation.Topology) { tp.PullRequest.RequiredChecks = nil },
			want:   []string{"GHW-PR-MERGE-CHECK-MISSING"},
		},
		{
			name: "a required check still running",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.RequiredChecks = []relation.CheckState{{Name: "gate", Status: "in_progress"}}
			},
			want: []string{"GHW-PR-MERGE-CHECK-PENDING"},
		},
		{
			name: "a failing required check",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.RequiredChecks = []relation.CheckState{{Name: "gate", Status: "completed", Conclusion: "failure"}}
			},
			want: []string{"GHW-PR-MERGE-CHECK-FAILING"},
		},
		{
			name: "a skipped required check satisfies github",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.RequiredChecks = []relation.CheckState{{Name: "gate", Status: "completed", Conclusion: "skipped"}}
			},
		},
		{
			name:   "review required and not approved",
			mutate: func(tp *relation.Topology) { tp.PullRequest.ReviewDecision = "REVIEW_REQUIRED" },
			want:   []string{"GHW-PR-MERGE-REVIEW-REQUIRED"},
		},
		{
			name: "no review required",
			mutate: func(tp *relation.Topology) {
				tp.Enforcement.RequiresReview = false
				tp.PullRequest.ReviewDecision = ""
			},
		},
		{
			name:   "mergeability not yet computed",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Mergeable = nil },
			want:   []string{"GHW-PR-MERGE-MERGEABILITY-UNKNOWN"},
		},
		{
			name:   "conflicting branch",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Mergeable = boolPtr(false) },
			want:   []string{"GHW-PR-MERGE-CONFLICT"},
		},
		{
			name:   "still a draft at the merge gate",
			mutate: func(tp *relation.Topology) { tp.PullRequest.Draft = true },
			want:   []string{"GHW-PR-MERGE-DRAFT"},
		},
		{
			name: "an r4 standalone missing its execution assurance",
			mutate: func(tp *relation.Topology) {
				tp.GoverningIssue = nil
				tp.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Standalone\nChange risk: R4 Critical", 1)
			},
			want: []string{"GHW-PR-MERGE-R4-EVIDENCE"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			topology := openTopology()
			tc.mutate(&topology)
			want := append([]string{}, tc.want...)
			sort.Strings(want)
			if got := codes(relation.Evaluate(topology, relation.PhaseMerge).Findings); !equalStrings(got, want) {
				t.Errorf("codes = %v, want %v", got, want)
			}
		})
	}
}

func TestEvaluatePostMerge(t *testing.T) {
	t.Parallel()

	dispositionComment := func(value string) relation.Comment {
		return relation.Comment{Author: "agent", Body: "Final-Disposition: " + value + "\nReason: needs rework"}
	}

	cases := []struct {
		name   string
		mutate func(*relation.Topology)
		want   []string
	}{
		{
			name: "merged final synchronized to done",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State, tp.PullRequest.Merged = "closed", true
				tp.GoverningIssue.State, tp.GoverningIssue.StateReason = "closed", "completed"
				tp.GoverningIssue.Workflow = relation.WorkflowDone
			},
		},
		{
			name: "merged final whose issue never converged",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State, tp.PullRequest.Merged = "closed", true
			},
			want: []string{"GHW-PR-POSTMERGE-FINAL-SYNC"},
		},
		{
			name: "merged supporting is lifecycle neutral",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State, tp.PullRequest.Merged = "closed", true
				tp.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Supporting: #12", 1)
			},
		},
		{
			name: "closed unmerged final with no disposition record",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
			},
			want: []string{"GHW-PR-POSTMERGE-DISPOSITION-MISSING"},
		},
		{
			name: "closed unmerged final whose disposition matches the issue",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Comments = []relation.Comment{dispositionComment("in-progress")}
				tp.GoverningIssue.Workflow = relation.WorkflowInProgress
			},
		},
		{
			name: "a repeated identical disposition record is not a contradiction",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Comments = []relation.Comment{dispositionComment("blocked"), dispositionComment("blocked")}
				tp.GoverningIssue.Workflow = relation.WorkflowBlocked
			},
		},
		{
			name: "conflicting disposition records block interpretation",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Comments = []relation.Comment{dispositionComment("blocked"), dispositionComment("dropped")}
			},
			want: []string{"GHW-PR-POSTMERGE-DISPOSITION-CONFLICT"},
		},
		{
			name: "an unrecognized disposition value",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Comments = []relation.Comment{dispositionComment("abandoned")}
			},
			want: []string{"GHW-PR-POSTMERGE-DISPOSITION-CONFLICT"},
		},
		{
			name: "a disposition the issue has not honored",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Comments = []relation.Comment{dispositionComment("dropped")}
			},
			want: []string{"GHW-PR-POSTMERGE-DISPOSITION-SYNC"},
		},
		{
			name: "closed unmerged supporting needs no disposition",
			mutate: func(tp *relation.Topology) {
				tp.PullRequest.State = "closed"
				tp.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Supporting: #12", 1)
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			topology := openTopology()
			tc.mutate(&topology)
			want := append([]string{}, tc.want...)
			sort.Strings(want)
			if got := codes(relation.Evaluate(topology, relation.PhasePostMerge).Findings); !equalStrings(got, want) {
				t.Errorf("codes = %v, want %v", got, want)
			}
		})
	}
}

// Requesting post-merge on an open PR is a domain finding, not invalid syntax
// (FR-031) — and it must not evaluate the terminal predicates against a live PR.
func TestEvaluatePostMergeOnOpenPullRequest(t *testing.T) {
	t.Parallel()

	result := relation.Evaluate(openTopology(), relation.PhasePostMerge)
	if got, want := codes(result.Findings), []string{"GHW-PR-POSTMERGE-OPEN"}; !equalStrings(got, want) {
		t.Fatalf("codes = %v, want %v", got, want)
	}
	if result.Gate != relation.PhasePostMerge {
		t.Errorf("gate = %q, want %q", result.Gate, relation.PhasePostMerge)
	}
}

// EC-014: a terminal PR's structural contradictions are additive evidence-integrity
// findings. The stable code survives; the corrective action changes, because editing a
// terminal PR's declaration is prohibited.
func TestEvaluateTerminalEvidenceIntegrity(t *testing.T) {
	t.Parallel()

	topology := openTopology()
	topology.PullRequest.State, topology.PullRequest.Merged = "closed", true
	topology.PullRequest.Body = strings.Replace(completeBody, "Final: #12", "Final: 12", 1)
	topology.GoverningIssue = nil

	var seen bool
	for _, finding := range relation.Evaluate(topology, relation.PhasePostMerge).Findings {
		if finding.Code != "GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED" {
			continue
		}
		seen = true
		if finding.Category != relation.CategoryDispositionRequired {
			t.Errorf("category = %q, want %q", finding.Category, relation.CategoryDispositionRequired)
		}
		if finding.Effect != relation.EffectEvidenceIntegrity {
			t.Errorf("effect = %q, want %q", finding.Effect, relation.EffectEvidenceIntegrity)
		}
	}
	if !seen {
		t.Fatal("the malformed declaration was not reported on the terminal PR")
	}
}

// Every finding must carry the whole DR-004 shape and a code inside the published
// grammar, and one code must always mean one invariant at one phase for one kind.
func TestFindingShapeAndCodeGrammar(t *testing.T) {
	t.Parallel()

	grammar := regexp.MustCompile(`^GHW-(ISSUE|PR)-(STRUCTURAL|READY|MERGE|POSTMERGE)-[A-Z][A-Z0-9-]*$`)
	type identity struct {
		phase relation.Phase
		kind  relation.Kind
	}
	seen := map[string]identity{}
	// The phase tokens are restated rather than derived from the engine, so a change to
	// the code grammar has to be made in two places deliberately.
	phaseToken := map[relation.Phase]string{
		relation.PhaseStructural: "STRUCTURAL",
		relation.PhaseReady:      "READY",
		relation.PhaseMerge:      "MERGE",
		relation.PhasePostMerge:  "POSTMERGE",
	}

	for _, finding := range allFindings(t) {
		if !grammar.MatchString(finding.Code) {
			t.Errorf("code %q is outside the DR-004 grammar", finding.Code)
			continue
		}
		if !strings.Contains(finding.Code, "-"+phaseToken[finding.Phase]+"-") {
			t.Errorf("code %q does not name its own phase %q", finding.Code, finding.Phase)
		}
		if finding.Message == "" || finding.Remediation == "" {
			t.Errorf("%s: message %q remediation %q, both required", finding.Code, finding.Message, finding.Remediation)
		}
		if finding.Number == 0 {
			t.Errorf("%s: finding carries no work-item number", finding.Code)
		}
		if !validCategory(finding.Category) {
			t.Errorf("%s: category %q is outside the FR-030 vocabulary", finding.Code, finding.Category)
		}
		want := identity{finding.Phase, finding.Kind}
		if got, ok := seen[finding.Code]; ok && got != want {
			t.Errorf("code %q means %+v here and %+v elsewhere", finding.Code, want, got)
		}
		seen[finding.Code] = want
	}
}

func validCategory(category relation.Category) bool {
	for _, known := range relation.CategoryOrder {
		if category == known {
			return true
		}
	}
	return false
}

// allFindings drives the engine across a corpus wide enough to emit every code the
// package can produce, so the grammar and uniqueness assertions above are not vacuous.
func allFindings(t *testing.T) []relation.Finding {
	t.Helper()

	var findings []relation.Finding
	bodies := []string{
		completeBody,
		strings.Replace(completeBody, "## Governing work", "## Governing", 1),
		strings.Replace(completeBody, "Final: #12", "final: #12", 1),
		strings.Replace(completeBody, "Final: #12", "Final: #12\nSupporting: #13", 1),
		strings.Replace(completeBody, "Final: #12", "Final: #12\nChange risk: R1 Low", 1),
		strings.Replace(completeBody, "Final: #12", "Standalone", 1),
		strings.Replace(completeBody, "Final: #12", "Standalone\nChange risk: R4 Critical", 1),
		strings.Replace(completeBody, "Final: #12", "Standalone\n\nprose\n\nChange risk: R9 Nope", 1),
		strings.Replace(completeBody, "## Summary", "## Overview", 1),
		completeBody + "\n## Verification\n\nagain\n",
		completeBody + "\nFixes #99\n",
		strings.Replace(completeBody, "Final: #12", "Supporting: #12", 1),
	}
	states := []func(*relation.Topology){
		func(tp *relation.Topology) {},
		func(tp *relation.Topology) { tp.PullRequest.Draft = true },
		func(tp *relation.Topology) { tp.GoverningIssue = nil },
		func(tp *relation.Topology) { tp.GoverningIssue.IsPullRequestShaped = true },
		func(tp *relation.Topology) { tp.GoverningIssue.IssueType = "" },
		func(tp *relation.Topology) { tp.GoverningIssue.State = "closed" },
		func(tp *relation.Topology) { tp.GoverningIssue.Workflow = relation.WorkflowBlocked },
		func(tp *relation.Topology) { tp.GoverningIssue.Workflow = relation.WorkflowInProgress },
		func(tp *relation.Topology) { tp.GoverningIssue.Workflow = "Inbox" },
		func(tp *relation.Topology) { tp.SiblingOpenFinals = []int{41} },
		func(tp *relation.Topology) { tp.Enforcement = relation.EnforcementEvidence{} },
		func(tp *relation.Topology) { tp.MergeSettings = relation.RepositoryMergeSettings{} },
		func(tp *relation.Topology) { tp.MergeSettings = relation.RepositoryMergeSettings{Known: true} },
		func(tp *relation.Topology) { tp.PullRequest.RequiredChecks = nil },
		func(tp *relation.Topology) {
			tp.PullRequest.RequiredChecks = []relation.CheckState{{Name: "gate", Status: "queued"}}
		},
		func(tp *relation.Topology) {
			tp.PullRequest.RequiredChecks = []relation.CheckState{{Name: "gate", Status: "completed", Conclusion: "failure"}}
		},
		func(tp *relation.Topology) { tp.PullRequest.ReviewDecision = "CHANGES_REQUESTED" },
		func(tp *relation.Topology) { tp.PullRequest.Mergeable = nil },
		func(tp *relation.Topology) { tp.PullRequest.Mergeable = boolPtr(false) },
		func(tp *relation.Topology) {
			past := testNow.Add(-time.Hour)
			tp.GoverningIssue.TargetDate = &past
		},
		func(tp *relation.Topology) { tp.PullRequest.State, tp.PullRequest.Merged = "closed", true },
		func(tp *relation.Topology) { tp.PullRequest.State = "closed" },
		func(tp *relation.Topology) {
			tp.PullRequest.State = "closed"
			tp.PullRequest.Comments = []relation.Comment{{Body: "Final-Disposition: dropped"}}
		},
		func(tp *relation.Topology) {
			tp.PullRequest.State = "closed"
			tp.PullRequest.Comments = []relation.Comment{{Body: "Final-Disposition: nope"}}
		},
		func(tp *relation.Topology) {
			tp.PullRequest.State = "closed"
			tp.PullRequest.Comments = []relation.Comment{{Body: "Final-Disposition: blocked"}, {Body: "Final-Disposition: dropped"}}
		},
	}

	for _, body := range bodies {
		for _, state := range states {
			for _, phase := range relation.PhaseOrder {
				topology := openTopology()
				topology.PullRequest.Body = body
				state(&topology)
				findings = append(findings, relation.Evaluate(topology, phase).Findings...)
			}
		}
	}
	if len(findings) == 0 {
		t.Fatal("the corpus produced no findings")
	}
	return findings
}
