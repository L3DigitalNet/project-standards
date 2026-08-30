package relation

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// Relationship is the canonical governing-work relationship of FR-027. Exactly one is
// declared per PR; RelationshipNone means the body declared none, which is itself the
// structural finding, never a default.
type Relationship string

// The three canonical relationships.
const (
	RelationshipNone       Relationship = ""
	RelationshipFinal      Relationship = "final"
	RelationshipSupporting Relationship = "supporting"
	RelationshipStandalone Relationship = "standalone"
)

// Governed reports whether the relationship resolves a governing Issue. Standalone owns
// its own contract and lifecycle and resolves none.
func (r Relationship) Governed() bool {
	return r == RelationshipFinal || r == RelationshipSupporting
}

// Risk is a Standalone PR's authoritative Change risk value. The four spellings are the
// whole vocabulary (FR-028); a governed PR inherits risk from its Issue and declares
// none.
type Risk string

// The four Change risk values.
const (
	RiskR1 Risk = "R1 Low"
	RiskR2 Risk = "R2 Moderate"
	RiskR3 Risk = "R3 High"
	RiskR4 Risk = "R4 Critical"
)

// Risks lists the accepted Change risk values in ascending order.
var Risks = []Risk{RiskR1, RiskR2, RiskR3, RiskR4}

// The four required Ready contract sections of FR-028, spelled exactly as the headings
// must appear. Presence is order-insensitive; the spelling is not.
const (
	HeadingSummary            = "## Summary"
	HeadingGoverningWork      = "## Governing work"
	HeadingAcceptanceCoverage = "## Acceptance coverage"
	HeadingVerification       = "## Verification"
)

// requiredSections is the FR-028 set. Adding a fifth required section is a package
// version change, not an implementation detail.
var requiredSections = []string{
	HeadingSummary, HeadingGoverningWork, HeadingAcceptanceCoverage, HeadingVerification,
}

// R4Evidence records which of the four R4 Critical technical controls FR-028 requires
// were detectable in Summary or Acceptance coverage. Detection is deliberately
// mechanical keyword matching over those two sections: the alternative — judging whether
// prose truly documents a rollback approach — is not decidable by a parser, and D16
// forbids compensating with a ceremonial approval gate. A false positive here is
// therefore possible by design; the review ladder, not this parser, is the semantic
// authority.
type R4Evidence struct {
	Plan                    bool
	Recovery                bool
	NegativeTesting         bool
	IndependentVerification bool
}

// Complete reports whether all four controls were detected.
func (e R4Evidence) Complete() bool {
	return e.Plan && e.Recovery && e.NegativeTesting && e.IndependentVerification
}

// Missing names the undetected controls, in a stable order, for the finding message.
func (e R4Evidence) Missing() []string {
	var missing []string
	for _, control := range []struct {
		found bool
		name  string
	}{
		{e.Plan, "an implementation plan"},
		{e.Recovery, "a recovery or rollback approach"},
		{e.NegativeTesting, "recorded negative testing"},
		{e.IndependentVerification, "independent verification"},
	} {
		if !control.found {
			missing = append(missing, control.name)
		}
	}
	return missing
}

// ClosingKeyword is one GitHub-recognized closing reference found in the body.
type ClosingKeyword struct {
	// Text is the keyword exactly as written, because FR-027 accepts only the exact
	// spelling `Closes` and rejects every case and tense variant.
	Text   string
	Number int
}

// Declaration is everything the parser can establish from the PR body alone. Anything
// requiring another object — whether the Issue exists, whether a sibling Final is open,
// what the Issue's Workflow is — is not here; that is Topology's job.
type Declaration struct {
	Relationship Relationship
	// IssueNumber is the declared Issue for Final and Supporting, 0 otherwise.
	IssueNumber int
	// Risk is the parsed Standalone Change risk, "" when absent or unrecognized.
	Risk Risk
	// RiskDeclared records that a `Change risk:` line was present under Governing work
	// at all, which separates "missing" from "malformed" and catches the governed PR
	// that duplicates its Issue's risk.
	RiskDeclared bool
	// Sections holds the exact required headings present in the body.
	Sections map[string]bool
	// ClosingKeywords holds every GitHub-recognized closing reference outside fenced
	// code blocks, accepted or not, so Structural can judge each one.
	ClosingKeywords []ClosingKeyword
	R4Evidence      R4Evidence
	// BlockedRationale records an explicit blocker statement in Acceptance coverage,
	// the only thing that lets a Supporting PR merge while its Issue is Blocked
	// (FR-029).
	BlockedRationale bool
}

// Has reports whether an exact required heading was present.
func (d Declaration) Has(heading string) bool { return d.Sections[heading] }

var (
	finalLine       = regexp.MustCompile(`^Final: #(\d+)$`)
	supportingLine  = regexp.MustCompile(`^Supporting: #(\d+)$`)
	declarationLike = regexp.MustCompile(`(?i)^(final|supporting|standalone)\b`)
	riskLine        = regexp.MustCompile(`^Change risk:\s*(.*)$`)
	// Alternatives are ordered longest-first because Go's regexp is leftmost-first, so
	// `close` listed before `closes` would capture only the shorter prefix and report
	// the keyword text wrongly in the finding message.
	closingKeyword = regexp.MustCompile(`(?i)\b(closes|closed|close|fixes|fixed|fix|resolves|resolved|resolve)\s+#(\d+)\b`)
)

// ParseBody extracts the canonical declaration and reports every finding decidable from
// the body alone: structural findings about the relationship declaration and closing
// keywords, and Ready findings about the four required sections and the Standalone risk
// line. Findings carry no work-item number — the body does not know it — so Evaluate
// stamps the PR number before returning them.
//
// It never infers a relationship. A body full of `Fixes #12` with no `## Governing work`
// section parses as RelationshipNone plus a structural finding, because canonical
// declarations alone establish package authority (D15).
func ParseBody(body string) (Declaration, []Finding) {
	decl := Declaration{Sections: map[string]bool{}}
	var findings []Finding

	sections, duplicates := splitSections(body)
	for _, heading := range requiredSections {
		if _, ok := sections[heading]; ok {
			decl.Sections[heading] = true
		}
	}
	for _, heading := range duplicates {
		findings = append(findings, Finding{
			Code: "GHW-PR-READY-SECTION-DUPLICATE", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     fmt.Sprintf("the body repeats the required section heading %q", heading),
			Remediation: "Merge the duplicated section so each required heading appears exactly once.",
		})
	}

	findings = append(findings, parseGoverningWork(sections[HeadingGoverningWork], &decl)...)
	decl.R4Evidence = detectR4Evidence(sections[HeadingSummary], sections[HeadingAcceptanceCoverage])
	decl.BlockedRationale = detectBlockedRationale(sections[HeadingAcceptanceCoverage])
	decl.ClosingKeywords = findClosingKeywords(body)

	for _, heading := range requiredSections {
		// Governing work is reported as a missing relationship, not a missing section:
		// its absence is a Structural failure and a Ready one, and the earliest
		// applicable phase owns the finding (FR-030).
		if heading == HeadingGoverningWork || decl.Sections[heading] {
			continue
		}
		findings = append(findings, Finding{
			Code: "GHW-PR-READY-SECTION-MISSING", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     fmt.Sprintf("the body has no %q section", heading),
			Remediation: fmt.Sprintf("Add an exact %q heading with its content before marking the PR ready.", heading),
		})
	}

	return decl, findings
}

// splitSections returns the lines of each level-two section keyed by its exact heading
// line, plus the headings that appeared more than once.
//
// Fenced code blocks are skipped wholesale: a body that quotes an example PR template
// inside a fence must not have that example's headings, declarations, or closing
// keywords read as its own. Both fence spellings are honored because GitHub accepts
// both.
func splitSections(body string) (map[string][]string, []string) {
	sections := map[string][]string{}
	var duplicates []string
	seen := map[string]bool{}

	current := ""
	inFence := false
	for _, raw := range strings.Split(body, "\n") {
		line := strings.TrimRight(raw, " \t\r")
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "```") || strings.HasPrefix(trimmed, "~~~") {
			inFence = !inFence
			continue
		}
		if inFence {
			continue
		}
		if strings.HasPrefix(line, "## ") {
			current = line
			if seen[current] {
				duplicates = append(duplicates, current)
			}
			seen[current] = true
			if _, ok := sections[current]; !ok {
				sections[current] = nil
			}
			continue
		}
		if current != "" {
			sections[current] = append(sections[current], line)
		}
	}
	return sections, duplicates
}

// parseGoverningWork reads the canonical declaration out of the Governing work section
// and reports the structural and risk findings it can decide alone.
func parseGoverningWork(lines []string, decl *Declaration) []Finding {
	var findings []Finding
	if !decl.Sections[HeadingGoverningWork] {
		return append(findings, Finding{
			Code: "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message: fmt.Sprintf("the body has no exact %q heading, so it declares no governing-work relationship", HeadingGoverningWork),
			Remediation: fmt.Sprintf("Add a %q section declaring exactly one of `Final: #N`, `Supporting: #N`, or `Standalone`.",
				HeadingGoverningWork),
		})
	}

	declared := 0
	standaloneAt := -1
	var malformed []string
	for i, raw := range lines {
		line := strings.TrimSpace(raw)
		if line == "" {
			continue
		}
		switch {
		case line == "Standalone":
			declared++
			standaloneAt = i
			if decl.Relationship == RelationshipNone {
				decl.Relationship = RelationshipStandalone
			}
		case finalLine.MatchString(line):
			declared++
			if decl.Relationship == RelationshipNone {
				decl.Relationship = RelationshipFinal
				decl.IssueNumber = mustAtoi(finalLine.FindStringSubmatch(line)[1])
			}
		case supportingLine.MatchString(line):
			declared++
			if decl.Relationship == RelationshipNone {
				decl.Relationship = RelationshipSupporting
				decl.IssueNumber = mustAtoi(supportingLine.FindStringSubmatch(line)[1])
			}
		case riskLine.MatchString(line):
			decl.RiskDeclared = true
			decl.Risk = parseRisk(riskLine.FindStringSubmatch(line)[1])
		case declarationLike.MatchString(line):
			// A line that opens with a relationship word but does not match a canonical
			// form — wrong case, a missing `#`, a trailing comment, a cross-repository
			// `owner/repo#N` — is reported rather than ignored, because silently
			// treating it as prose turns an intended declaration into "no declaration"
			// with no explanation of why.
			malformed = append(malformed, line)
		}
	}

	for _, line := range malformed {
		findings = append(findings, Finding{
			Code: "GHW-PR-STRUCTURAL-RELATIONSHIP-MALFORMED", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     fmt.Sprintf("%q is not a canonical governing-work declaration", line),
			Remediation: "Use exactly `Final: #N`, `Supporting: #N`, or `Standalone`; other Issue references are informational only.",
		})
	}
	switch {
	case declared == 0 && decl.Sections[HeadingGoverningWork]:
		findings = append(findings, Finding{
			Code: "GHW-PR-STRUCTURAL-RELATIONSHIP-MISSING", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     fmt.Sprintf("the %q section declares no canonical relationship", HeadingGoverningWork),
			Remediation: "Declare exactly one of `Final: #N`, `Supporting: #N`, or `Standalone`.",
		})
	case declared > 1:
		findings = append(findings, Finding{
			Code: "GHW-PR-STRUCTURAL-RELATIONSHIP-DUPLICATE", Phase: PhaseStructural,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message: fmt.Sprintf("the %q section declares %d relationships; exactly one is allowed",
				HeadingGoverningWork, declared),
			Remediation: "Keep the one intended declaration and delete the others.",
		})
	}

	findings = append(findings, riskFindings(lines, standaloneAt, decl)...)
	return findings
}

// riskFindings applies the FR-028 risk rules: Standalone owns an authoritative
// `Change risk:` line immediately after its declaration, and a governed PR declares
// none because it inherits the Issue's.
func riskFindings(lines []string, standaloneAt int, decl *Declaration) []Finding {
	var findings []Finding
	if decl.Relationship.Governed() && decl.RiskDeclared {
		return append(findings, Finding{
			Code: "GHW-PR-READY-RISK-UNEXPECTED", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     "a governed PR declares its own Change risk, which duplicates the governing Issue's authoritative value",
			Remediation: "Delete the `Change risk:` line; Final and Supporting inherit risk from the Issue.",
		})
	}
	if decl.Relationship != RelationshipStandalone {
		return findings
	}
	if !decl.RiskDeclared {
		return append(findings, Finding{
			Code: "GHW-PR-READY-RISK-MISSING", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     "a Standalone PR declares no authoritative `Change risk:` value",
			Remediation: "Add `Change risk: R1 Low`, `R2 Moderate`, `R3 High`, or `R4 Critical` immediately after `Standalone`.",
		})
	}
	if decl.Risk == "" {
		findings = append(findings, Finding{
			Code: "GHW-PR-READY-RISK-INVALID", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     "the `Change risk:` value is not one of the four accepted values",
			Remediation: "Use exactly `R1 Low`, `R2 Moderate`, `R3 High`, or `R4 Critical`.",
		})
	}
	// "Immediately after" is checked against the next non-empty line so a blank line
	// between the two does not fail a well-formed body, while an intervening sentence
	// does: the adjacency is what makes the risk line unambiguously the Standalone
	// declaration's own value rather than prose quoting a risk elsewhere.
	if standaloneAt >= 0 && !riskLine.MatchString(nextNonEmpty(lines, standaloneAt+1)) {
		findings = append(findings, Finding{
			Code: "GHW-PR-READY-RISK-MISPLACED", Phase: PhaseReady,
			Category: CategoryNeedsDefinition, Effect: EffectBlocksReady, Kind: KindPullRequest,
			Message:     "the `Change risk:` line does not immediately follow `Standalone`",
			Remediation: "Move the `Change risk:` line so it is the first line after `Standalone`.",
		})
	}
	return findings
}

// nextNonEmpty returns the first non-blank trimmed line at or after i, or "".
func nextNonEmpty(lines []string, i int) string {
	for ; i < len(lines); i++ {
		if line := strings.TrimSpace(lines[i]); line != "" {
			return line
		}
	}
	return ""
}

// parseRisk maps a declared value to a Risk, returning "" for anything outside the
// vocabulary rather than accepting an abbreviation: `R4` alone is not the authoritative
// spelling and must be reported, not silently upgraded.
func parseRisk(value string) Risk {
	value = strings.TrimSpace(value)
	for _, risk := range Risks {
		if string(risk) == value {
			return risk
		}
	}
	return ""
}

// detectR4Evidence scans the two sections FR-028 permits the evidence to live in.
func detectR4Evidence(summary, coverage []string) R4Evidence {
	text := strings.ToLower(strings.Join(append(append([]string{}, summary...), coverage...), "\n"))
	contains := func(needles ...string) bool {
		for _, needle := range needles {
			if strings.Contains(text, needle) {
				return true
			}
		}
		return false
	}
	return R4Evidence{
		Plan:                    contains("plan"),
		Recovery:                contains("rollback", "recovery", "revert"),
		NegativeTesting:         contains("negative test"),
		IndependentVerification: contains("independent verification", "independently verified"),
	}
}

// detectBlockedRationale looks for an explicit statement about the blocker in Acceptance
// coverage. FR-029 requires the rationale to explain why admission neither resolves nor
// conceals the blocker, which no parser can confirm; requiring the blocker to be named
// at all is the mechanical part, and the reviewer owns the rest.
func detectBlockedRationale(coverage []string) bool {
	text := strings.ToLower(strings.Join(coverage, "\n"))
	return strings.Contains(text, "blocker") || strings.Contains(text, "blocked")
}

// findClosingKeywords returns every GitHub-recognized closing reference outside fenced
// code blocks. It reports all of them, including the accepted form, because the
// structural predicate needs to count them: two `Closes #12` lines are as wrong as one
// `Fixes #12`.
func findClosingKeywords(body string) []ClosingKeyword {
	var found []ClosingKeyword
	inFence := false
	for _, raw := range strings.Split(body, "\n") {
		trimmed := strings.TrimSpace(raw)
		if strings.HasPrefix(trimmed, "```") || strings.HasPrefix(trimmed, "~~~") {
			inFence = !inFence
			continue
		}
		if inFence {
			continue
		}
		for _, match := range closingKeyword.FindAllStringSubmatch(raw, -1) {
			found = append(found, ClosingKeyword{Text: match[1], Number: mustAtoi(match[2])})
		}
	}
	return found
}

// mustAtoi converts a regexp-captured `\d+` run. The capture guarantees digits, so the
// only reachable failure is an overflowing number, which degrades to 0 — an Issue
// number that can never resolve, which the structural predicate already reports.
func mustAtoi(s string) int {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}
