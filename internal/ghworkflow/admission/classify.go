// Package admission classifies the commits on a governed branch against the four
// admission classes ADR 0031 defines, and is the enforcement half of the rule
// `references/pr-standard.md` states (issues #203, #218).
//
// The package is deliberately split: this file owns the rules and knows nothing about
// git, flags, or GitHub, so the whole classification is exercised from table-driven
// tests over literal commits. `commits.go` owns the one `git log` invocation that
// produces those commits and `command.go` owns the CLI surface.
//
// Two decisions shape the rules and are easy to undo by accident.
//
// The exempt path set is a compile-time constant, not a policy option. `policy.toml`
// can only switch the handoff class off (`handoff_admission = "none"`); it cannot widen
// the set. An extensible exempt set is a live bypass surface — an agent could add the
// paths its own change touches and admit itself — which is the escalation the skill
// already refuses (ADR 0031 D2).
//
// A commit with no trailer whose paths are all exempt is reported as an *undeclared*
// handoff commit rather than admitted. `git log` cannot express "touched only these
// paths" for a retrospective audit, and a direct commit must carry a declaration its
// author stands behind, so the paths alone never admit anything.
package admission

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// TrailerKey is the commit-trailer name every admitted commit carries.
const TrailerKey = "Workflow-Admission"

// Class is the admission class a commit was classified into. Unadmitted is not a class
// a commit can declare: it is what the classifier reports when no class applies.
type Class string

const (
	ClassT0          Class = "T0"
	ClassPullRequest Class = "pull-request"
	ClassHandoff     Class = "handoff"
	ClassRelease     Class = "release"
	ClassUnadmitted  Class = "unadmitted"
)

// Finding codes. Each names one distinguishable way a commit fails to be admitted, so
// an operator reading the report knows which repair applies without rereading the
// standard: a missing declaration, a declaration that does not match the paths, a
// declaration the repository has switched off, or a spelling no class recognizes.
const (
	CodeMissing          = "GHW-ADMISSION-MISSING"
	CodeHandoffMixed     = "GHW-ADMISSION-HANDOFF-MIXED"
	CodeHandoffUndeclare = "GHW-ADMISSION-HANDOFF-UNDECLARED"
	CodeHandoffDisabled  = "GHW-ADMISSION-HANDOFF-DISABLED"
	CodeTrailerInvalid   = "GHW-ADMISSION-TRAILER-INVALID"
	CodeTrailerConflict  = "GHW-ADMISSION-TRAILER-CONFLICT"
	CodePullRequestState = "GHW-ADMISSION-PR-NOT-MERGED"
)

// HandoffPrefixes and HandoffFiles are the exempt path set, fixed by the standard as
// exactly the document artifacts `agent-handoff` declares as targets. Changing either
// changes the standard, so both ends move together: the same three paths are named in
// `pr-standard.md` and in the managed instruction block the provider renders.
var (
	HandoffPrefixes = []string{"docs/handoff/"}
	HandoffFiles    = []string{"docs/STATUS.md", "docs/TODO.md"}
)

// pullRequestTrailer matches the `PR #N` trailer `merge --pr N` writes. The number is
// captured because an online run verifies it against the merged pull request; offline,
// the well-formed trailer is the whole evidence.
var pullRequestTrailer = regexp.MustCompile(`^PR #(\d+)$`)

// Commit is one commit as the classifier sees it, with no git types in the signature.
//
// Paths is empty for a merge commit: `git log --name-only` reports no diff for a merge
// unless it is asked to pick a parent, and a merge authors no content of its own. The
// consequence is deliberate — a merge commit can never be classified as handoff, so a
// promotion or a GitHub merge commit is admitted by its trailer or not at all.
type Commit struct {
	SHA     string
	Subject string
	Body    string
	Paths   []string
	IsMerge bool
}

// Rules is the repository's configured admission model.
type Rules struct {
	// HandoffEnabled is false when `handoff_admission = "none"`, which removes the
	// class entirely for a consumer that has not adopted `agent-handoff`.
	HandoffEnabled bool
	// ReleaseSubjectPrefix admits a release commit whose subject begins with it even
	// without a trailer, because release tooling that predates 1.9 writes no trailer.
	// Empty means only an explicit `release` trailer admits a release commit.
	ReleaseSubjectPrefix string
}

// Finding is one commit's classification. A Finding whose Class is not ClassUnadmitted
// and whose Code is empty is an admission; every other Finding blocks.
type Finding struct {
	SHA           string `json:"sha"`
	Subject       string `json:"subject"`
	Class         Class  `json:"class"`
	Code          string `json:"code,omitempty"`
	Message       string `json:"message,omitempty"`
	Remediation   string `json:"remediation,omitempty"`
	PullRequest   int    `json:"pull_request,omitempty"`
	OffendingPath string `json:"offending_path,omitempty"`
}

// Admitted reports whether the commit needs no further action.
func (f Finding) Admitted() bool { return f.Code == "" }

// IsHandoffPath reports whether one repository-relative path lies in the exempt set.
func IsHandoffPath(path string) bool {
	for _, prefix := range HandoffPrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	for _, file := range HandoffFiles {
		if path == file {
			return true
		}
	}
	return false
}

// firstNonHandoffPath returns the path that disqualifies a commit from the handoff
// class, or "" when every path is exempt. The offending path is carried into the
// finding because "this commit is mixed" without naming the file leaves the author to
// re-derive the split by hand.
func firstNonHandoffPath(paths []string) string {
	for _, path := range paths {
		if !IsHandoffPath(path) {
			return path
		}
	}
	return ""
}

// Trailer returns the single `Workflow-Admission` value a commit declares.
//
// A second, differing value is an error rather than a last-one-wins choice: two
// declarations mean the author claimed two admission routes, and silently taking one
// would admit a commit on evidence its author did not intend. Repeating the identical
// value is tolerated, because a rebase or a cherry-pick can duplicate a trailer line
// without changing what was declared.
func Trailer(body string) (string, error) {
	var value string
	for _, line := range strings.Split(body, "\n") {
		rest, ok := strings.CutPrefix(strings.TrimSpace(line), TrailerKey+":")
		if !ok {
			continue
		}
		found := strings.TrimSpace(rest)
		if value != "" && found != value {
			return "", fmt.Errorf("commit declares both %q and %q", value, found)
		}
		value = found
	}
	return value, nil
}

// Classify applies the four admission classes to one commit.
//
// Order matters: an explicit trailer is always honored over a subject heuristic, so a
// commit that both declares a class and matches `release_subject_prefix` is judged on
// what its author declared. Subject matching is the fallback only, and only for the
// release class — ADR 0031 rejected subject heuristics for pull-request provenance on
// measured evidence (29 subjects ending in `(#N)` against 4 merged pull requests).
func Classify(commit Commit, rules Rules) Finding {
	finding := Finding{SHA: commit.SHA, Subject: commit.Subject, Class: ClassUnadmitted}

	declared, err := Trailer(commit.Body)
	if err != nil {
		finding.Code = CodeTrailerConflict
		finding.Message = err.Error()
		finding.Remediation = "Amend the commit so it carries exactly one `" + TrailerKey + "` trailer."
		return finding
	}

	switch {
	case declared == "":
		return classifyUndeclared(commit, rules, finding)
	case declared == string(ClassT0):
		finding.Class = ClassT0
		return finding
	case declared == "release":
		finding.Class = ClassRelease
		return finding
	case declared == "handoff":
		return classifyHandoff(commit, rules, finding)
	}

	if match := pullRequestTrailer.FindStringSubmatch(declared); match != nil {
		number, convErr := strconv.Atoi(match[1])
		if convErr != nil || number <= 0 {
			finding.Code = CodeTrailerInvalid
			finding.Message = fmt.Sprintf("%q is not a positive pull request number", declared)
			finding.Remediation = "Rewrite the trailer as `" + TrailerKey + ": PR #N`."
			return finding
		}
		finding.Class = ClassPullRequest
		finding.PullRequest = number
		return finding
	}

	finding.Code = CodeTrailerInvalid
	finding.Message = fmt.Sprintf("%q is not one of T0, PR #N, handoff, release", declared)
	finding.Remediation = "Use one of the four admission classes, or route the change through a pull request."
	return finding
}

// classifyHandoff checks the declared handoff class against the paths and the
// repository's configuration. Both refusals are separate codes because the repairs
// differ completely: a mixed commit is split or routed through a pull request, while a
// disabled class means the repository never had the exemption to claim.
func classifyHandoff(commit Commit, rules Rules, finding Finding) Finding {
	if !rules.HandoffEnabled {
		finding.Code = CodeHandoffDisabled
		finding.Message = "this repository sets `handoff_admission = \"none\"`, so the handoff class does not exist here"
		finding.Remediation = "Route the change through a pull request, or adopt `agent-handoff` and restore the default."
		return finding
	}
	if offending := firstNonHandoffPath(commit.Paths); offending != "" {
		finding.Code = CodeHandoffMixed
		finding.Message = fmt.Sprintf("a handoff commit may touch only the handoff paths; %s is not one of them", offending)
		finding.Remediation = "Split the handoff bookkeeping into its own commit and route the rest through a pull request."
		finding.OffendingPath = offending
		return finding
	}
	if len(commit.Paths) == 0 {
		// An empty or merge commit claiming the exemption has nothing to be exempt
		// about, and admitting it would make the class satisfiable by touching nothing.
		finding.Code = CodeHandoffMixed
		finding.Message = "a handoff commit must touch at least one handoff path"
		finding.Remediation = "Route the change through a pull request."
		return finding
	}
	finding.Class = ClassHandoff
	return finding
}

// classifyUndeclared handles a commit that carries no trailer at all: the release
// subject fallback, the undeclared-handoff report, and otherwise the plain miss.
func classifyUndeclared(commit Commit, rules Rules, finding Finding) Finding {
	if rules.ReleaseSubjectPrefix != "" && strings.HasPrefix(commit.Subject, rules.ReleaseSubjectPrefix) {
		finding.Class = ClassRelease
		return finding
	}
	if rules.HandoffEnabled && len(commit.Paths) > 0 && firstNonHandoffPath(commit.Paths) == "" {
		finding.Code = CodeHandoffUndeclare
		finding.Message = "every path is a handoff path, but the commit declares no admission class"
		finding.Remediation = "Amend the commit to carry `" + TrailerKey + ": handoff`."
		return finding
	}
	finding.Code = CodeMissing
	finding.Message = "the commit carries no `" + TrailerKey + "` trailer"
	finding.Remediation = "Route the change through `merge --pr N`, or declare T0, handoff, or release if one of them applies."
	return finding
}
