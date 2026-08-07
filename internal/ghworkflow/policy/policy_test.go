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
