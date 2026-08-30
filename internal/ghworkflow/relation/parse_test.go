package relation_test

import (
	"sort"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// codes returns the findings' codes sorted, which is how every table here compares
// results: the parser's emission order is an implementation detail, but the set of
// invariants it reports is the contract.
func codes(findings []relation.Finding) []string {
	out := make([]string, 0, len(findings))
	for _, finding := range findings {
		out = append(out, finding.Code)
	}
	sort.Strings(out)
	return out
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// completeBody is a well-formed Final body. Cases derive from it by substitution so a
// table row shows only the deviation under test.
const completeBody = `## Summary

Adds the thing.

## Governing work

Final: #12

## Acceptance coverage

Covers every criterion.

## Verification

go test ./...
`

func TestParseBodyDeclaration(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name             string
		body             string
		wantRelationship relation.Relationship
		wantIssue        int
		wantRisk         relation.Risk
		wantCodes        []string
	}{
		{
			name:             "canonical final",
			body:             completeBody,
			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
		},
		{
			name:             "canonical supporting",
			body:             strings.Replace(completeBody, "Final: #12", "Supporting: #7", 1),
			wantRelationship: relation.RelationshipSupporting,
			wantIssue:        7,
		},
		{
			name:             "standalone with risk",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone\nChange risk: R2 Moderate", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantRisk:         relation.RiskR2,
		},
		{
			name:      "no governing work section",
			body:      strings.Replace(completeBody, "## Governing work", "## Governing", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "governing work at the wrong heading level",
			body:      strings.Replace(completeBody, "## Governing work", "### Governing work", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "governing work heading with extra internal space",
			body:      strings.Replace(completeBody, "## Governing work", "##  Governing work", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "governing work section declares nothing",
			body:      strings.Replace(completeBody, "Final: #12", "See the tracker.", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:             "two declarations",
			body:             strings.Replace(completeBody, "Final: #12", "Final: #12\nSupporting: #13", 1),
			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
			wantCodes:        []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-DUPLICATE"},
		},
		{
			name:      "lowercase relationship word",
			body:      strings.Replace(completeBody, "Final: #12", "final: #12", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED", "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "missing hash",
			body:      strings.Replace(completeBody, "Final: #12", "Final: 12", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED", "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "cross-repository reference is not canonical",
			body:      strings.Replace(completeBody, "Final: #12", "Final: L3DigitalNet/other#12", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED", "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:      "trailing commentary after a canonical declaration",
			body:      strings.Replace(completeBody, "Final: #12", "Final: #12 (the tracking issue)", 1),
			wantCodes: []string{"GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED", "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING"},
		},
		{
			name:             "surrounding whitespace is tolerated",
			body:             strings.Replace(completeBody, "Final: #12", "   Final: #12   ", 1),
			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
		},
		{
			name:      "missing summary section",
			body:      strings.Replace(completeBody, "## Summary", "## Overview", 1),
			wantCodes: []string{"GHW-PR-READY-SECTION-MISSING"},

			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
		},
		{
			name:             "duplicate required section",
			body:             completeBody + "\n## Verification\n\nAgain.\n",
			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
			wantCodes:        []string{"GHW-PR-READY-SECTION-DUPLICATE"},
		},
		{
			name:             "standalone without a risk line",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantCodes:        []string{"GHW-PR-READY-RISK-MISSING"},
		},
		{
			name:             "standalone with an unrecognized risk value",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone\nChange risk: R5 Apocalyptic", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantCodes:        []string{"GHW-PR-READY-RISK-INVALID"},
		},
		{
			name:             "standalone with an abbreviated risk value",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone\nChange risk: R4", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantCodes:        []string{"GHW-PR-READY-RISK-INVALID"},
		},
		{
			name:             "risk line separated from the declaration",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone\n\nSome prose.\n\nChange risk: R1 Low", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantRisk:         relation.RiskR1,
			wantCodes:        []string{"GHW-PR-READY-RISK-MISPLACED"},
		},
		{
			name:             "blank line between declaration and risk is allowed",
			body:             strings.Replace(completeBody, "Final: #12", "Standalone\n\nChange risk: R1 Low", 1),
			wantRelationship: relation.RelationshipStandalone,
			wantRisk:         relation.RiskR1,
		},
		{
			name:             "governed pr declaring its own risk",
			body:             strings.Replace(completeBody, "Final: #12", "Final: #12\nChange risk: R3 High", 1),
			wantRelationship: relation.RelationshipFinal,
			wantIssue:        12,
			wantRisk:         relation.RiskR3,
			wantCodes:        []string{"GHW-PR-READY-RISK-UNEXPECTED"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			decl, findings := relation.ParseBody(tc.body)
			if decl.Relationship != tc.wantRelationship {
				t.Errorf("relationship = %q, want %q", decl.Relationship, tc.wantRelationship)
			}
			if decl.IssueNumber != tc.wantIssue {
				t.Errorf("issue number = %d, want %d", decl.IssueNumber, tc.wantIssue)
			}
			if decl.Risk != tc.wantRisk {
				t.Errorf("risk = %q, want %q", decl.Risk, tc.wantRisk)
			}
			want := append([]string{}, tc.wantCodes...)
			sort.Strings(want)
			if got := codes(findings); !equalStrings(got, want) {
				t.Errorf("codes = %v, want %v", got, want)
			}
		})
	}
}

// A body quoting the PR template inside a fence must not have the quoted headings,
// declaration, or closing keyword read as its own — otherwise documenting the standard
// inside a PR silently changes that PR's relationship.
func TestParseBodyIgnoresFencedContent(t *testing.T) {
	t.Parallel()

	body := "## Governing work\n\nStandalone\nChange risk: R1 Low\n\n" +
		"```markdown\n## Summary\n\nFinal: #99\nFixes #99\n```\n" +
		"## Summary\n\nReal summary.\n\n## Acceptance coverage\n\nx\n\n## Verification\n\ny\n"

	decl, findings := relation.ParseBody(body)
	if decl.Relationship != relation.RelationshipStandalone {
		t.Errorf("relationship = %q, want standalone", decl.Relationship)
	}
	if len(decl.ClosingKeywords) != 0 {
		t.Errorf("closing keywords = %v, want none", decl.ClosingKeywords)
	}
	if len(findings) != 0 {
		t.Errorf("findings = %v, want none", codes(findings))
	}
}

func TestParseBodyClosingKeywords(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		body string
		want []relation.ClosingKeyword
	}{
		{name: "none", body: completeBody},
		{
			name: "exact closes",
			body: completeBody + "\nCloses #12\n",
			want: []relation.ClosingKeyword{{Text: "Closes", Number: 12}},
		},
		{
			name: "every recognized family is detected",
			body: completeBody + "\nfixes #1 resolved #2 Close #3\n",
			want: []relation.ClosingKeyword{
				{Text: "fixes", Number: 1}, {Text: "resolved", Number: 2}, {Text: "Close", Number: 3},
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			decl, _ := relation.ParseBody(tc.body)
			if len(decl.ClosingKeywords) != len(tc.want) {
				t.Fatalf("closing keywords = %v, want %v", decl.ClosingKeywords, tc.want)
			}
			for i, keyword := range decl.ClosingKeywords {
				if keyword != tc.want[i] {
					t.Errorf("keyword[%d] = %v, want %v", i, keyword, tc.want[i])
				}
			}
		})
	}
}

// The parser must never infer a relationship from a closing keyword (D15): a body whose
// only Issue reference is `Fixes #12` declares nothing.
func TestParseBodyNeverInfersRelationship(t *testing.T) {
	t.Parallel()

	decl, _ := relation.ParseBody("## Governing work\n\nFixes #12\n")
	if decl.Relationship != relation.RelationshipNone || decl.IssueNumber != 0 {
		t.Errorf("relationship = %q #%d, want none", decl.Relationship, decl.IssueNumber)
	}
}

func TestParseBodyR4Evidence(t *testing.T) {
	t.Parallel()

	complete := "## Summary\n\nImplementation plan and rollback approach recorded.\n\n" +
		"## Governing work\n\nStandalone\nChange risk: R4 Critical\n\n" +
		"## Acceptance coverage\n\nNegative testing recorded; independent verification by a second agent.\n\n" +
		"## Verification\n\ngo test ./...\n"

	decl, _ := relation.ParseBody(complete)
	if !decl.R4Evidence.Complete() {
		t.Errorf("R4 evidence = %+v, want complete", decl.R4Evidence)
	}

	// Evidence living outside Summary and Acceptance coverage does not count: FR-028
	// names exactly those two sections.
	elsewhere := strings.Replace(complete, "Negative testing recorded; independent verification by a second agent.", "Covered.", 1)
	elsewhere = strings.Replace(elsewhere, "go test ./...", "Negative testing and independent verification done.", 1)
	decl, _ = relation.ParseBody(elsewhere)
	if decl.R4Evidence.Complete() {
		t.Errorf("R4 evidence = %+v, want incomplete", decl.R4Evidence)
	}
	if got, want := len(decl.R4Evidence.Missing()), 2; got != want {
		t.Errorf("missing controls = %d, want %d", got, want)
	}
}
