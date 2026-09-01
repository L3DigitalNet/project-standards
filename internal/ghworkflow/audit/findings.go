// Package audit implements the `audit` subcommand: a read-only comparison of live
// GitHub organization schema against the baseline in `org-schema.yaml` (spec FR-016).
//
// The comparison is a pure function over a parsed baseline and two API responses, which
// is what lets every finding class be proved offline against a fake transport. The
// subcommand around it is thin on purpose: acquire inputs, compare, render.
package audit

import (
	"fmt"
	"sort"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/safetext"
)

// Status is a finding class. These four are the vocabulary FR-016 requires the report to
// distinguish, and they are exhaustive: every baseline element and every live element
// lands in exactly one.
type Status string

// Finding classes.
const (
	// StatusMatch: baseline and live agree.
	StatusMatch Status = "match"
	// StatusMissing: the baseline declares it, the organization does not have it.
	StatusMissing Status = "missing"
	// StatusMismatch: both have it, but their definitions differ.
	StatusMismatch Status = "mismatch"
	// StatusExtra: the organization has it, the baseline does not declare it.
	StatusExtra Status = "extra"
)

// Kind distinguishes the two audited element families.
type Kind string

// Element kinds.
const (
	KindIssueType  Kind = "issue_type"
	KindIssueField Kind = "issue_field"
)

// Finding is one comparison result. The value-drift and type-drift details are separate
// fields rather than prose so the JSON output stays machine-actionable.
type Finding struct {
	Kind          Kind     `json:"kind"`
	Status        Status   `json:"status"`
	Name          string   `json:"name"`
	Detail        string   `json:"detail"`
	ExpectedType  string   `json:"expected_type,omitempty"`
	ActualType    string   `json:"actual_type,omitempty"`
	MissingValues []string `json:"missing_values,omitempty"`
	ExtraValues   []string `json:"extra_values,omitempty"`
}

// Counts summarizes a report by finding class.
type Counts struct {
	Match    int `json:"match"`
	Missing  int `json:"missing"`
	Mismatch int `json:"mismatch"`
	Extra    int `json:"extra"`
}

// Report is the complete audit result. It carries no timestamp: FR-016 calls for a
// deterministic report, so two runs against unchanged state produce identical bytes and
// a diff of two reports shows drift rather than clock movement.
type Report struct {
	Organization string    `json:"organization"`
	SchemaPath   string    `json:"schema_path"`
	Findings     []Finding `json:"findings"`
	Counts       Counts    `json:"counts"`
}

// NewReport tallies findings into a report.
func NewReport(organization, schemaPath string, findings []Finding) *Report {
	report := &Report{Organization: organization, SchemaPath: schemaPath, Findings: findings}
	for _, finding := range findings {
		switch finding.Status {
		case StatusMatch:
			report.Counts.Match++
		case StatusMissing:
			report.Counts.Missing++
		case StatusMismatch:
			report.Counts.Mismatch++
		case StatusExtra:
			report.Counts.Extra++
		}
	}
	return report
}

// HasDrift reports whether the organization diverges from the baseline in any way.
func (r *Report) HasDrift() bool {
	return r.Counts.Missing+r.Counts.Mismatch+r.Counts.Extra > 0
}

// Compare classifies the live organization against the baseline.
//
// Findings come out in a fixed order — issue types then issue fields, baseline order
// first and extras sorted by name — because the report is meant to be diffed between
// runs, and Go map iteration order would make that useless.
func Compare(schema *orgschema.Schema, liveTypes []ghapi.IssueType, liveFields []ghapi.IssueField) []Finding {
	findings := compareIssueTypes(schema.IssueTypes, liveTypes)
	findings = append(findings, compareIssueFields(schema.IssueFields, liveFields)...)
	// Every name and detail below carries live organization text — an Issue Type name, a
	// field name, a single_select option — that an organization owner authored and this
	// tool prints straight to a terminal. Sanitizing once here rather than per renderer
	// covers the human report and the JSON alike; the encoder is idempotent, so baseline
	// names passing through a second time are unchanged.
	for i := range findings {
		findings[i].Name = safetext.SanitizeText(findings[i].Name)
		findings[i].Detail = safetext.SanitizeText(findings[i].Detail)
	}
	return findings
}

func compareIssueTypes(baseline []string, live []ghapi.IssueType) []Finding {
	byName := make(map[string]ghapi.IssueType, len(live))
	for _, issueType := range live {
		byName[issueType.Name] = issueType
	}

	findings := make([]Finding, 0, len(baseline)+len(live))
	declared := make(map[string]bool, len(baseline))
	for _, name := range baseline {
		declared[name] = true
		finding := Finding{Kind: KindIssueType, Name: name}
		switch actual, ok := byName[name]; {
		case !ok:
			finding.Status = StatusMissing
			finding.Detail = "declared in the baseline but absent from the organization"
		case !actual.IsEnabled:
			// A disabled type exists but cannot be applied to an issue, so it is drift
			// an operator must act on, not a match.
			finding.Status = StatusMismatch
			finding.Detail = "present in the organization but disabled"
		default:
			finding.Status = StatusMatch
			finding.Detail = "present and enabled"
		}
		findings = append(findings, finding)
	}

	extras := make([]string, 0, len(live))
	for _, issueType := range live {
		if !declared[issueType.Name] {
			extras = append(extras, issueType.Name)
		}
	}
	sort.Strings(extras)
	for _, name := range extras {
		findings = append(findings, Finding{
			Kind:   KindIssueType,
			Status: StatusExtra,
			Name:   name,
			Detail: "present in the organization but not declared in the baseline",
		})
	}
	return findings
}

func compareIssueFields(baseline []orgschema.Field, live []ghapi.IssueField) []Finding {
	byName := make(map[string]ghapi.IssueField, len(live))
	for _, field := range live {
		byName[field.Name] = field
	}

	findings := make([]Finding, 0, len(baseline)+len(live))
	declared := make(map[string]bool, len(baseline))
	for _, field := range baseline {
		declared[field.Name] = true
		findings = append(findings, compareField(field, byName))
	}

	extras := make([]string, 0, len(live))
	for _, field := range live {
		if !declared[field.Name] {
			extras = append(extras, field.Name)
		}
	}
	sort.Strings(extras)
	for _, name := range extras {
		findings = append(findings, Finding{
			Kind:       KindIssueField,
			Status:     StatusExtra,
			Name:       name,
			ActualType: byName[name].DataType,
			Detail:     "present in the organization but not declared in the baseline",
		})
	}
	return findings
}

func compareField(baseline orgschema.Field, live map[string]ghapi.IssueField) Finding {
	finding := Finding{Kind: KindIssueField, Name: baseline.Name, ExpectedType: baseline.Type}

	actual, ok := live[baseline.Name]
	if !ok {
		finding.Status = StatusMissing
		finding.Detail = "declared in the baseline but absent from the organization"
		return finding
	}
	finding.ActualType = actual.DataType

	if actual.DataType != baseline.Type {
		finding.Status = StatusMismatch
		finding.Detail = fmt.Sprintf("field type is %s, baseline declares %s", actual.DataType, baseline.Type)
		return finding
	}
	if baseline.Type != orgschema.TypeSingleSelect {
		finding.Status = StatusMatch
		finding.Detail = "field type matches the baseline"
		return finding
	}

	// Values are compared as sets: GitHub returns options in its own priority order, so
	// ordering differences are presentation, not drift.
	actualValues := make([]string, 0, len(actual.Options))
	for _, option := range actual.Options {
		actualValues = append(actualValues, option.Name)
	}
	finding.MissingValues = difference(baseline.Values, actualValues)
	finding.ExtraValues = difference(actualValues, baseline.Values)
	if len(finding.MissingValues) == 0 && len(finding.ExtraValues) == 0 {
		finding.Status = StatusMatch
		finding.Detail = "field type and values match the baseline"
		return finding
	}
	finding.Status = StatusMismatch
	finding.Detail = fmt.Sprintf("value drift: %s", summarizeValueDrift(finding.MissingValues, finding.ExtraValues))
	return finding
}

// difference returns the members of a absent from b, preserving a's order.
func difference(a, b []string) []string {
	inB := make(map[string]bool, len(b))
	for _, value := range b {
		inB[value] = true
	}
	var out []string
	for _, value := range a {
		if !inB[value] {
			out = append(out, value)
		}
	}
	return out
}

func summarizeValueDrift(missing, extra []string) string {
	var parts []string
	if len(missing) > 0 {
		parts = append(parts, fmt.Sprintf("%d missing (%s)", len(missing), strings.Join(missing, ", ")))
	}
	if len(extra) > 0 {
		parts = append(parts, fmt.Sprintf("%d unexpected (%s)", len(extra), strings.Join(extra, ", ")))
	}
	return strings.Join(parts, "; ")
}
