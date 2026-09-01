package admission_test

// The classification rules of ADR 0031 D1 and D2, exercised over literal commits.
//
// Every case here answers "what does this commit's evidence admit?", never "what does
// git do?" — the git reader has its own test over a literal log stream, and the two are
// kept apart so a change to either is one failing suite rather than two.

import (
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/admission"
)

// defaultRules is a consumer that has adopted `agent-handoff` and declares a release
// subject prefix, which is this repository's own configuration and the shape most of
// the cases below are about.
var defaultRules = admission.Rules{HandoffEnabled: true, ReleaseSubjectPrefix: "release: prepare v"}

func trailer(value string) string {
	return "subject\n\nbody text\n\n" + admission.TrailerKey + ": " + value + "\n"
}

func TestClassify(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		commit admission.Commit
		rules  admission.Rules
		want   admission.Class
		code   string
	}{
		{
			name:   "T0 trailer admits a prose repair",
			commit: admission.Commit{SHA: "a1", Body: trailer("T0"), Paths: []string{"README.md"}},
			rules:  defaultRules,
			want:   admission.ClassT0,
		},
		{
			name:   "PR trailer admits and carries the number",
			commit: admission.Commit{SHA: "a2", Body: trailer("PR #216"), Paths: []string{"src/app.py"}},
			rules:  defaultRules,
			want:   admission.ClassPullRequest,
		},
		{
			name: "handoff trailer admits a commit touching only handoff paths",
			commit: admission.Commit{SHA: "a3", Body: trailer("handoff"), Paths: []string{
				"docs/handoff/state.md", "docs/handoff/sessions/2026-09.md", "docs/STATUS.md", "docs/TODO.md",
			}},
			rules: defaultRules,
			want:  admission.ClassHandoff,
		},
		{
			// Issue #218 AC2: the exemption must not become a wrapper for other work.
			name: "handoff trailer refuses a mixed commit",
			commit: admission.Commit{SHA: "a4", Body: trailer("handoff"), Paths: []string{
				"docs/handoff/state.md", "src/project_standards/cli.py",
			}},
			rules: defaultRules,
			want:  admission.ClassUnadmitted,
			code:  admission.CodeHandoffMixed,
		},
		{
			name:   "handoff trailer refuses a commit touching no handoff path at all",
			commit: admission.Commit{SHA: "a5", Body: trailer("handoff"), Paths: nil},
			rules:  defaultRules,
			want:   admission.ClassUnadmitted,
			code:   admission.CodeHandoffMixed,
		},
		{
			name:   "handoff_admission none removes the class",
			commit: admission.Commit{SHA: "a6", Body: trailer("handoff"), Paths: []string{"docs/TODO.md"}},
			rules:  admission.Rules{HandoffEnabled: false},
			want:   admission.ClassUnadmitted,
			code:   admission.CodeHandoffDisabled,
		},
		{
			name:   "release trailer admits",
			commit: admission.Commit{SHA: "a7", Body: trailer("release"), Paths: []string{"pyproject.toml"}},
			rules:  defaultRules,
			want:   admission.ClassRelease,
		},
		{
			name: "release subject prefix admits a trailerless release commit",
			commit: admission.Commit{
				SHA: "a8", Subject: "release: prepare v5.28.0",
				Body: "release: prepare v5.28.0\n", Paths: []string{"pyproject.toml"},
			},
			rules: defaultRules,
			want:  admission.ClassRelease,
		},
		{
			name: "an unconfigured release prefix admits nothing by subject",
			commit: admission.Commit{
				SHA: "a9", Subject: "release: prepare v5.28.0",
				Body: "release: prepare v5.28.0\n", Paths: []string{"pyproject.toml"},
			},
			rules: admission.Rules{HandoffEnabled: true},
			want:  admission.ClassUnadmitted,
			code:  admission.CodeMissing,
		},
		{
			// The subject heuristic ADR 0031 rejected: 29 subjects ended in `(#N)` over
			// a range with 4 merged pull requests, so a suffix admits nothing.
			name: "a PR-shaped subject suffix does not admit",
			commit: admission.Commit{
				SHA: "b1", Subject: "docs(handoff): record the queue triage (#216)",
				Body: "docs(handoff): record the queue triage (#216)\n", Paths: []string{"src/app.py"},
			},
			rules: defaultRules,
			want:  admission.ClassUnadmitted,
			code:  admission.CodeMissing,
		},
		{
			name: "a handoff-only commit without a trailer is its own finding",
			commit: admission.Commit{
				SHA: "b2", Subject: "docs(handoff): close out the session",
				Body: "docs(handoff): close out the session\n", Paths: []string{"docs/handoff/state.md"},
			},
			rules: defaultRules,
			want:  admission.ClassUnadmitted,
			code:  admission.CodeHandoffUndeclare,
		},
		{
			name:   "an unrecognized trailer value is refused rather than ignored",
			commit: admission.Commit{SHA: "b3", Body: trailer("trivial"), Paths: []string{"README.md"}},
			rules:  defaultRules,
			want:   admission.ClassUnadmitted,
			code:   admission.CodeTrailerInvalid,
		},
		{
			name:   "a PR trailer with no number is refused",
			commit: admission.Commit{SHA: "b4", Body: trailer("PR #"), Paths: []string{"README.md"}},
			rules:  defaultRules,
			want:   admission.ClassUnadmitted,
			code:   admission.CodeTrailerInvalid,
		},
		{
			name: "two different declarations are a conflict, not a last-one-wins choice",
			commit: admission.Commit{
				SHA:   "b5",
				Body:  "subject\n\n" + admission.TrailerKey + ": T0\n" + admission.TrailerKey + ": handoff\n",
				Paths: []string{"README.md"},
			},
			rules: defaultRules,
			want:  admission.ClassUnadmitted,
			code:  admission.CodeTrailerConflict,
		},
		{
			name: "a duplicated identical declaration survives a cherry-pick",
			commit: admission.Commit{
				SHA:   "b6",
				Body:  "subject\n\n" + admission.TrailerKey + ": T0\n" + admission.TrailerKey + ": T0\n",
				Paths: []string{"README.md"},
			},
			rules: defaultRules,
			want:  admission.ClassT0,
		},
		{
			// A path that merely starts with the same characters is not inside the
			// exempt directory; `docs/handoffs/` is a different directory entirely.
			name:   "a lookalike prefix is not a handoff path",
			commit: admission.Commit{SHA: "b7", Body: trailer("handoff"), Paths: []string{"docs/handoffs/other.md"}},
			rules:  defaultRules,
			want:   admission.ClassUnadmitted,
			code:   admission.CodeHandoffMixed,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got := admission.Classify(tc.commit, tc.rules)
			if got.Class != tc.want {
				t.Errorf("Class = %q, want %q (code %q)", got.Class, tc.want, got.Code)
			}
			if got.Code != tc.code {
				t.Errorf("Code = %q, want %q", got.Code, tc.code)
			}
			if tc.code == "" && !got.Admitted() {
				t.Error("Admitted() = false for a commit that should be admitted")
			}
			if tc.code != "" {
				if got.Message == "" || got.Remediation == "" {
					t.Errorf("finding %s carries no message or remediation: %+v", got.Code, got)
				}
			}
		})
	}
}

// The mixed-commit finding must name the path that disqualified the commit; "this is
// mixed" alone leaves the author to re-derive the split by reading the diff.
func TestMixedCommitNamesTheOffendingPath(t *testing.T) {
	t.Parallel()

	got := admission.Classify(admission.Commit{
		SHA:   "c1",
		Body:  trailer("handoff"),
		Paths: []string{"docs/handoff/state.md", "CHANGELOG.md"},
	}, defaultRules)

	if got.OffendingPath != "CHANGELOG.md" {
		t.Errorf("OffendingPath = %q, want CHANGELOG.md", got.OffendingPath)
	}
	if !strings.Contains(got.Message, "CHANGELOG.md") {
		t.Errorf("Message = %q, want it to name the offending path", got.Message)
	}
}

func TestIsHandoffPath(t *testing.T) {
	t.Parallel()

	exempt := []string{"docs/handoff/state.md", "docs/handoff/sessions/2026-09.md", "docs/STATUS.md", "docs/TODO.md"}
	for _, path := range exempt {
		if !admission.IsHandoffPath(path) {
			t.Errorf("IsHandoffPath(%q) = false, want true", path)
		}
	}
	// The set is exactly three entries wide. A README beside them, or the same file
	// name at the repository root, is ordinary content that any consumer may own.
	notExempt := []string{"docs/README.md", "STATUS.md", "TODO.md", "docs/handoffs/x.md", "docs/handoff.md"}
	for _, path := range notExempt {
		if admission.IsHandoffPath(path) {
			t.Errorf("IsHandoffPath(%q) = true, want false", path)
		}
	}
}
