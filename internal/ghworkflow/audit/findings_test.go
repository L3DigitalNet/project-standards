package audit_test

import (
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/audit"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
)

func baseline() *orgschema.Schema {
	return &orgschema.Schema{
		IssueTypes: []string{"Bug", "Feature", "Task"},
		IssueFields: []orgschema.Field{
			{Name: "Workflow", Type: "single_select", Values: []string{"Ready", "Done"}},
			{Name: "Target date", Type: "date"},
			{Name: "Severity", Type: "single_select", Values: []string{"S0", "S1"}},
		},
	}
}

func find(t *testing.T, findings []audit.Finding, kind audit.Kind, name string) audit.Finding {
	t.Helper()
	for _, f := range findings {
		if f.Kind == kind && f.Name == name {
			return f
		}
	}
	t.Fatalf("no %s finding for %q in %+v", kind, name, findings)
	return audit.Finding{}
}

func TestCompareIssueTypeClasses(t *testing.T) {
	t.Parallel()

	live := []ghapi.IssueType{
		{Name: "Bug", IsEnabled: true},      // match
		{Name: "Feature", IsEnabled: false}, // mismatch: present but disabled
		{Name: "Chore", IsEnabled: true},    // extra
		// "Task" absent: missing
	}

	findings := audit.Compare(baseline(), live, nil)

	cases := map[string]audit.Status{
		"Bug":     audit.StatusMatch,
		"Feature": audit.StatusMismatch,
		"Task":    audit.StatusMissing,
		"Chore":   audit.StatusExtra,
	}
	for name, want := range cases {
		got := find(t, findings, audit.KindIssueType, name)
		if got.Status != want {
			t.Errorf("issue type %q status = %q, want %q", name, got.Status, want)
		}
		if got.Detail == "" {
			t.Errorf("issue type %q has an empty detail", name)
		}
	}
}

func TestCompareIssueFieldClasses(t *testing.T) {
	t.Parallel()

	live := []ghapi.IssueField{
		{Name: "Workflow", DataType: "single_select", Options: []ghapi.IssueFieldOption{{Name: "Done"}, {Name: "Ready"}}},
		{Name: "Target date", DataType: "single_select"},
		{Name: "Estimate", DataType: "number"},
		// "Severity" absent: missing
	}

	findings := audit.Compare(baseline(), nil, live)

	// Workflow matches: value comparison is set-based, so option order is not drift.
	if got := find(t, findings, audit.KindIssueField, "Workflow"); got.Status != audit.StatusMatch {
		t.Errorf("Workflow status = %q, want %q (option order must not count as drift)", got.Status, audit.StatusMatch)
	}

	targetDate := find(t, findings, audit.KindIssueField, "Target date")
	if targetDate.Status != audit.StatusMismatch {
		t.Errorf("Target date status = %q, want %q", targetDate.Status, audit.StatusMismatch)
	}
	if targetDate.ExpectedType != "date" || targetDate.ActualType != "single_select" {
		t.Errorf("Target date types = %q/%q, want date/single_select", targetDate.ExpectedType, targetDate.ActualType)
	}

	if got := find(t, findings, audit.KindIssueField, "Severity"); got.Status != audit.StatusMissing {
		t.Errorf("Severity status = %q, want %q", got.Status, audit.StatusMissing)
	}
	if got := find(t, findings, audit.KindIssueField, "Estimate"); got.Status != audit.StatusExtra {
		t.Errorf("Estimate status = %q, want %q", got.Status, audit.StatusExtra)
	}
}

func TestCompareReportsValueDrift(t *testing.T) {
	t.Parallel()

	live := []ghapi.IssueField{
		{Name: "Workflow", DataType: "single_select", Options: []ghapi.IssueFieldOption{
			{Name: "Ready"}, {Name: "Shipped"},
		}},
	}

	got := find(t, audit.Compare(baseline(), nil, live), audit.KindIssueField, "Workflow")
	if got.Status != audit.StatusMismatch {
		t.Fatalf("Workflow status = %q, want %q", got.Status, audit.StatusMismatch)
	}
	if len(got.MissingValues) != 1 || got.MissingValues[0] != "Done" {
		t.Errorf("MissingValues = %v, want [Done]", got.MissingValues)
	}
	if len(got.ExtraValues) != 1 || got.ExtraValues[0] != "Shipped" {
		t.Errorf("ExtraValues = %v, want [Shipped]", got.ExtraValues)
	}
}

func TestCompareSingleSelectWithNoOptions(t *testing.T) {
	t.Parallel()

	live := []ghapi.IssueField{{Name: "Workflow", DataType: "single_select"}}

	got := find(t, audit.Compare(baseline(), nil, live), audit.KindIssueField, "Workflow")
	if got.Status != audit.StatusMismatch {
		t.Fatalf("Workflow status = %q, want %q", got.Status, audit.StatusMismatch)
	}
	if len(got.MissingValues) != 2 {
		t.Errorf("MissingValues = %v, want every baseline value", got.MissingValues)
	}
}

// FR-016 requires a deterministic report: baseline order first, then extras sorted by
// name, so two runs against the same state are byte-identical.
func TestCompareIsDeterministic(t *testing.T) {
	t.Parallel()

	live := []ghapi.IssueType{{Name: "Zeta", IsEnabled: true}, {Name: "Alpha", IsEnabled: true}, {Name: "Bug", IsEnabled: true}}
	liveFields := []ghapi.IssueField{{Name: "Zulu", DataType: "text"}, {Name: "Alfa", DataType: "text"}}

	findings := audit.Compare(baseline(), live, liveFields)

	var order []string
	for _, f := range findings {
		order = append(order, string(f.Kind)+"/"+f.Name)
	}
	want := []string{
		"issue_type/Bug", "issue_type/Feature", "issue_type/Task", "issue_type/Alpha", "issue_type/Zeta",
		"issue_field/Workflow", "issue_field/Target date", "issue_field/Severity", "issue_field/Alfa", "issue_field/Zulu",
	}
	if len(order) != len(want) {
		t.Fatalf("finding order = %v, want %v", order, want)
	}
	for i := range want {
		if order[i] != want[i] {
			t.Fatalf("finding order = %v, want %v", order, want)
		}
	}
}

func TestReportCountsAndDrift(t *testing.T) {
	t.Parallel()

	clean := audit.NewReport("L3DigitalNet", "org-schema.yaml", audit.Compare(baseline(),
		[]ghapi.IssueType{{Name: "Bug", IsEnabled: true}, {Name: "Feature", IsEnabled: true}, {Name: "Task", IsEnabled: true}},
		[]ghapi.IssueField{
			{Name: "Workflow", DataType: "single_select", Options: []ghapi.IssueFieldOption{{Name: "Ready"}, {Name: "Done"}}},
			{Name: "Target date", DataType: "date"},
			{Name: "Severity", DataType: "single_select", Options: []ghapi.IssueFieldOption{{Name: "S0"}, {Name: "S1"}}},
		},
	))
	if clean.HasDrift() {
		t.Errorf("HasDrift() = true for a conforming organization: %+v", clean.Findings)
	}
	if clean.Counts.Match != 6 {
		t.Errorf("Counts.Match = %d, want 6", clean.Counts.Match)
	}

	drifted := audit.NewReport("L3DigitalNet", "org-schema.yaml", audit.Compare(baseline(), nil, nil))
	if !drifted.HasDrift() {
		t.Error("HasDrift() = false for an empty organization")
	}
	if drifted.Counts.Missing != 6 {
		t.Errorf("Counts.Missing = %d, want 6", drifted.Counts.Missing)
	}
}
