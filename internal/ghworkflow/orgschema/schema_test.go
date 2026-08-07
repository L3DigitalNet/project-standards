package orgschema_test

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
)

func TestParseBaseline(t *testing.T) {
	t.Parallel()

	schema, err := orgschema.Load(filepath.Join("testdata", "org-schema.yaml"))
	if err != nil {
		t.Fatalf("Load() error = %v, want nil", err)
	}

	wantTypes := []string{"Bug", "Feature", "Task", "Initiative", "Research"}
	if len(schema.IssueTypes) != len(wantTypes) {
		t.Fatalf("IssueTypes = %v, want %v", schema.IssueTypes, wantTypes)
	}
	for i, want := range wantTypes {
		if schema.IssueTypes[i] != want {
			t.Errorf("IssueTypes[%d] = %q, want %q", i, schema.IssueTypes[i], want)
		}
	}

	if got, want := len(schema.IssueFields), 7; got != want {
		t.Fatalf("len(IssueFields) = %d, want %d", got, want)
	}
	if got, want := schema.IssueFields[0].Name, "Workflow"; got != want {
		t.Errorf("IssueFields[0].Name = %q, want %q (file order must be preserved)", got, want)
	}

	priority, ok := schema.Field("Priority")
	if !ok {
		t.Fatal("Field(\"Priority\") not found")
	}
	if priority.Type != "single_select" {
		t.Errorf("Priority.Type = %q, want %q", priority.Type, "single_select")
	}
	if got, want := len(priority.Values), 5; got != want {
		t.Errorf("len(Priority.Values) = %d, want %d", got, want)
	}
	if len(priority.Values) > 0 && priority.Values[0] != "P0 — Immediate" {
		t.Errorf("Priority.Values[0] = %q, want %q (multi-byte scalars must survive)", priority.Values[0], "P0 — Immediate")
	}

	target, ok := schema.Field("Target date")
	if !ok {
		t.Fatal("Field(\"Target date\") not found")
	}
	if target.Type != "date" {
		t.Errorf("Target date.Type = %q, want %q", target.Type, "date")
	}
	if len(target.Values) != 0 {
		t.Errorf("Target date.Values = %v, want empty", target.Values)
	}
}

// The parser is deliberately bounded (plan A-002). Every construct outside the subset
// must fail closed: a schema this parser silently misreads would produce a false audit.
func TestParseRejects(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		input   string
		wantSub string
	}{
		{
			name:    "unknown top-level key",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    type: date\nextra_key:\n  - nope\n",
			wantSub: "unknown top-level key",
		},
		{
			name:    "missing issue_fields",
			input:   "issue_types:\n  - Bug\n",
			wantSub: "issue_fields",
		},
		{
			name:    "missing issue_types",
			input:   "issue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "issue_types",
		},
		{
			name:    "tab indentation",
			input:   "issue_types:\n\t- Bug\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "tab",
		},
		{
			name:    "odd indentation",
			input:   "issue_types:\n   - Bug\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "indentation",
		},
		{
			name:    "unknown field key",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    type: date\n    colour: red\n",
			wantSub: "colour",
		},
		{
			name:    "field without a type",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    values:\n      - Inbox\n",
			wantSub: "type",
		},
		{
			name:    "single_select without values",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    type: single_select\n",
			wantSub: "values",
		},
		{
			name:    "non-select carrying values",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Target date:\n    type: date\n    values:\n      - nope\n",
			wantSub: "values",
		},
		{
			name:    "duplicate field",
			input:   "issue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    type: date\n  Workflow:\n    type: date\n",
			wantSub: "duplicate",
		},
		{
			name:    "duplicate issue type",
			input:   "issue_types:\n  - Bug\n  - Bug\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "duplicate",
		},
		{
			name:    "flow sequence",
			input:   "issue_types: [Bug, Feature]\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "inline value",
		},
		{
			name:    "anchor",
			input:   "issue_types:\n  - &anchor Bug\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "unsupported",
		},
		{
			name:    "empty scalar",
			input:   "issue_types:\n  -\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "empty",
		},
		{
			name:    "content before any top-level key",
			input:   "  - Bug\nissue_types:\n  - Bug\nissue_fields:\n  Workflow:\n    type: date\n",
			wantSub: "top-level",
		},
		{
			name:    "empty document",
			input:   "# only a comment\n",
			wantSub: "issue_types",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := orgschema.Parse([]byte(tc.input))
			if err == nil {
				t.Fatalf("Parse() = %+v, want an error containing %q", got, tc.wantSub)
			}
			if !strings.Contains(err.Error(), tc.wantSub) {
				t.Errorf("Parse() error = %q, want it to mention %q", err, tc.wantSub)
			}
		})
	}
}

// A consumer checkout on a CRLF-normalizing platform delivers org-schema.yaml with
// carriage returns. The parser measures indentation and trims trailing whitespace itself,
// so an untrimmed \r rides into every scalar: the baseline becomes "Bug\r" against a live
// "Bug", and the audit reports the entire organization as both missing and extra — the
// confidently-wrong answer the parser's fail-closed design exists to prevent.
func TestParseToleratesCRLFLineEndings(t *testing.T) {
	t.Parallel()

	data, err := os.ReadFile(filepath.Join("testdata", "org-schema.yaml"))
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}
	unix, err := orgschema.Parse(data)
	if err != nil {
		t.Fatalf("Parse(LF) error = %v, want nil", err)
	}
	windows, err := orgschema.Parse([]byte(strings.ReplaceAll(string(data), "\n", "\r\n")))
	if err != nil {
		t.Fatalf("Parse(CRLF) error = %v, want nil", err)
	}
	if !reflect.DeepEqual(unix, windows) {
		// Quoted, because the whole difference is invisible otherwise.
		t.Errorf("CRLF parse diverges from the LF parse\nissue types = %q\n       want = %q",
			windows.IssueTypes, unix.IssueTypes)
	}
}

func TestLoadMissingFile(t *testing.T) {
	t.Parallel()

	if _, err := orgschema.Load(filepath.Join(t.TempDir(), "absent.yaml")); err == nil {
		t.Fatal("Load() error = nil, want a failure for a missing schema file")
	}
}
