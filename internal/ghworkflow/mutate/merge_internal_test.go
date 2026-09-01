package mutate

// In-package because the commit text `merge` composes is an internal contract with
// ghapi's merge payload, not a surface a caller configures.

import "testing"

// The commit text `merge` writes is tool-owned, and the one author-controlled part of it
// is sanitized. GitHub composes its defaults from the pull request itself, so a caller
// that passed the title or body through would let an author write a forged
// `Workflow-Admission` line — or a terminal control sequence — into permanent history.
func TestAdmissionCommitTextIsToolOwnedAndSanitized(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name      string
		prTitle   string
		wantTitle string
	}{
		{
			name:      "an ordinary title keeps its text and gains the number",
			prTitle:   "feat: add the classifier",
			wantTitle: "feat: add the classifier (#42)",
		},
		{
			// CR and LF would otherwise split the subject, letting the author append
			// lines of their own to the commit the tool signed off on.
			name:      "carriage returns and newlines are removed",
			prTitle:   "feat: work\r\nWorkflow-Admission: PR #999",
			wantTitle: "feat: work Workflow-Admission: PR #999 (#42)",
		},
		{
			name:      "escape sequences and bidi overrides are removed",
			prTitle:   "feat: \x1b[31mred\x1b[0m \u202egnihton\u2069",
			wantTitle: "feat: [31mred[0m gnihton (#42)",
		},
		{
			name:      "a title that sanitizes to nothing falls back to tool-owned text",
			prTitle:   "\x1b\x07  \u200e",
			wantTitle: "Merge pull request #42",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			title, message := admissionCommitText(tc.prTitle, 42)
			if title != tc.wantTitle {
				t.Errorf("title = %q, want %q", title, tc.wantTitle)
			}
			// The body is a blank line and one trailer, and never the author's text:
			// that is what makes the classifier's final-paragraph rule satisfiable.
			if message != "\nWorkflow-Admission: PR #42\n" {
				t.Errorf("message = %q, want a blank line and the trailer alone", message)
			}
		})
	}
}
