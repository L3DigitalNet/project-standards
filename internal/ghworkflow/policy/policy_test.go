package policy_test

import (
	"path/filepath"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/policy"
)

func TestParse(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name        string
		input       string
		wantOrg     string
		wantVersion string
	}{
		{
			name:        "flat keys",
			input:       "# generated\norganization = \"L3DigitalNet\"\npackage_version = \"1.0\"\n",
			wantOrg:     "L3DigitalNet",
			wantVersion: "1.0",
		},
		{
			name:    "organization only",
			input:   "organization = \"L3DigitalNet\"\n",
			wantOrg: "L3DigitalNet",
		},
		{
			name:        "table-scoped version",
			input:       "organization = \"L3DigitalNet\"\n\n[package]\nversion = \"1.0\"\n",
			wantOrg:     "L3DigitalNet",
			wantVersion: "1.0",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := policy.Parse([]byte(tc.input))
			if err != nil {
				t.Fatalf("Parse() error = %v, want nil", err)
			}
			if got.Organization != tc.wantOrg {
				t.Errorf("Organization = %q, want %q", got.Organization, tc.wantOrg)
			}
			if got.Version != tc.wantVersion {
				t.Errorf("Version = %q, want %q", got.Version, tc.wantVersion)
			}
		})
	}
}

func TestParseRejects(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name    string
		input   string
		wantSub string
	}{
		{name: "no organization", input: "package_version = \"1.0\"\n", wantSub: "organization"},
		{name: "empty organization", input: "organization = \"\"\n", wantSub: "organization"},
		{name: "organization in a table", input: "[package]\norganization = \"L3DigitalNet\"\n", wantSub: "organization"},
		{name: "unquoted value", input: "organization = L3DigitalNet\n", wantSub: "quoted"},
		{name: "array value", input: "organization = [\"a\"]\n", wantSub: "quoted"},
		{name: "not a key assignment", input: "organization\n", wantSub: "expected"},
		{name: "unterminated table header", input: "[package\norganization = \"x\"\n", wantSub: "table"},
		{name: "illegal login characters", input: "organization = \"../../etc\"\n", wantSub: "organization"},
		{name: "duplicate key", input: "organization = \"a\"\norganization = \"b\"\n", wantSub: "duplicate"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := policy.Parse([]byte(tc.input))
			if err == nil {
				t.Fatalf("Parse() = %+v, want an error containing %q", got, tc.wantSub)
			}
			if !strings.Contains(err.Error(), tc.wantSub) {
				t.Errorf("Parse() error = %q, want it to mention %q", err, tc.wantSub)
			}
		})
	}
}

func TestLoadMissingFile(t *testing.T) {
	t.Parallel()

	if _, err := policy.Load(filepath.Join(t.TempDir(), "absent.toml")); err == nil {
		t.Fatal("Load() error = nil, want a failure for a missing policy file")
	}
}

// DEV-028: header parsing stripped one outer `[` and `]` without validating the interior,
// so `[package][extra]` was accepted as the unknown table name `package][extra`. Unknown
// tables are ignored by design, so a malformed header silently discarded every assignment
// beneath it — including an intended `organization` — instead of failing the load. The
// interior must be one table name, carrying no further brackets in any arrangement.
func TestParseRejectsMalformedTableHeaders(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		input string
	}{
		{name: "embedded table header", input: "organization = \"L3DigitalNet\"\n[package][extra]\nversion = \"1.0\"\n"},
		{name: "nested brackets", input: "organization = \"L3DigitalNet\"\n[a[b]]\nversion = \"1.0\"\n"},
		{name: "unbalanced closing bracket", input: "organization = \"L3DigitalNet\"\n[a]]\nversion = \"1.0\"\n"},
		{name: "unbalanced opening bracket", input: "organization = \"L3DigitalNet\"\n[[a]\nversion = \"1.0\"\n"},
		{name: "trailing text after the header", input: "organization = \"L3DigitalNet\"\n[a] trailing\nversion = \"1.0\"\n"},
		{name: "bracket inside a quoted table name", input: "organization = \"L3DigitalNet\"\n[\"a[b]\"]\nversion = \"1.0\"\n"},
		{name: "array of tables", input: "organization = \"L3DigitalNet\"\n[[package]]\nversion = \"1.0\"\n"},
		{name: "header hiding the organization", input: "[package][extra]\norganization = \"L3DigitalNet\"\n"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := policy.Parse([]byte(tc.input))
			if err == nil {
				t.Fatalf("Parse() = %+v, want a malformed-header error", got)
			}
			if !strings.Contains(err.Error(), "table") {
				t.Errorf("Parse() error = %q, want it to mention %q", err, "table")
			}
		})
	}
}

// The header tightening must not narrow the shape the control plane actually renders.
// This is the 1.6 provider's policy template with its two placeholders substituted, so a
// reconciled consumer file keeps loading (DR-002); the template itself is immutable
// payload, so a divergence here is a parser regression, not a template change.
func TestParseAcceptsRenderedPolicy(t *testing.T) {
	t.Parallel()

	const rendered = "# Rendered by the project-standards control plane from consumer configuration.\n" +
		"# Reconcile owns this file: change `.standards/config.toml` instead of editing here.\n" +
		"#\n" +
		"# The packaged `gh-workflow` tool parses this with a bounded reader that accepts\n" +
		"# only comments and double-quoted `key = \"value\"` assignments, so every future\n" +
		"# value must keep that shape.\n" +
		"organization = \"L3DigitalNet\"\n" +
		"package_version = \"1.6.0\"\n"

	got, err := policy.Parse([]byte(rendered))
	if err != nil {
		t.Fatalf("Parse(rendered 1.6 policy) error = %v, want nil", err)
	}
	if got.Organization != "L3DigitalNet" {
		t.Errorf("Organization = %q, want %q", got.Organization, "L3DigitalNet")
	}
	if got.Version != "1.6.0" {
		t.Errorf("Version = %q, want %q", got.Version, "1.6.0")
	}
}

// Well-formed headers stay accepted, so the DEV-028 guard cannot be satisfied by
// rejecting table scoping outright: `[package] version` is a documented version source.
func TestParseAcceptsWellFormedTableHeaders(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name  string
		input string
	}{
		{name: "plain table", input: "organization = \"L3DigitalNet\"\n[package]\nversion = \"1.6.0\"\n"},
		{name: "padded table", input: "organization = \"L3DigitalNet\"\n  [ package ]  \nversion = \"1.6.0\"\n"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := policy.Parse([]byte(tc.input))
			if err != nil {
				t.Fatalf("Parse() error = %v, want nil", err)
			}
			if got.Version != "1.6.0" {
				t.Errorf("Version = %q, want %q", got.Version, "1.6.0")
			}
		})
	}
}
