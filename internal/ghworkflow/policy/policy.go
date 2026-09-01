// Package policy reads the rendered consumer configuration at
// `.standards/packages/github-workflow/policy.toml` (spec DR-002), whose only
// load-bearing value for the tool is the GitHub organization login to audit.
//
// Like the org-schema reader, this is a bounded parser rather than a TOML library: the
// file is control-plane-generated with a fixed shape and the tool takes no module
// dependencies (plan A-002). The accepted subset is comments, table headers, and
// double-quoted string assignments; anything else is a parse error.
package policy

import (
	"errors"
	"fmt"
	"os"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
)

// Policy is the parsed consumer configuration.
type Policy struct {
	// Organization is the GitHub login the audit targets. Required.
	Organization string
	// Version is the package version stamped into the rendered file, if present.
	// It is informational: no tool behavior depends on it.
	Version string
	// The admission model ADR 0031 D1 configures. All four are optional and all four
	// default to something meaningful, because a policy rendered by payload 1.8 or
	// earlier carries none of them and must still load: an empty IntegrationBranch is
	// the two-branch topology, an empty AdmissionFloor classifies the whole history,
	// an empty ReleaseSubjectPrefix means only an explicit trailer admits a release,
	// and HandoffAdmission defaults to the class existing.
	IntegrationBranch    string
	ReleaseSubjectPrefix string
	AdmissionFloor       string
	HandoffAdmission     string
}

// Load reads and parses the policy at path.
func Load(path string) (*Policy, error) {
	// #nosec G304 -- the path is the operator's --policy flag or the payload's fixed
	// delivered location; the tool reads whatever checkout it was invoked in.
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("reading policy %s: %w", path, err)
	}
	parsed, err := Parse(data)
	if err != nil {
		return nil, fmt.Errorf("parsing policy %s: %w", path, err)
	}
	return parsed, nil
}

// Parse reads the bounded TOML subset described in the package documentation.
func Parse(data []byte) (*Policy, error) {
	values := map[string]string{}
	table := ""

	for i, raw := range strings.Split(string(data), "\n") {
		n := i + 1
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "[") {
			name, ok := strings.CutSuffix(line, "]")
			if !ok || strings.HasPrefix(line, "[[") {
				return nil, fmt.Errorf("line %d: malformed table header %q", n, line)
			}
			table = strings.TrimSpace(strings.TrimPrefix(name, "["))
			if table == "" {
				return nil, fmt.Errorf("line %d: empty table header", n)
			}
			// The interior must be one table name, so it carries no further brackets.
			// Stripping only the outer delimiters used to accept `[package][extra]` as
			// the unknown table name `package][extra`, and unknown tables are ignored
			// by design — so a malformed header silently discarded every assignment
			// beneath it instead of failing the load (DEV-028). `[[a]` is caught above
			// by the array-of-table guard and `[a] trailing` by the missing suffix.
			if strings.ContainsAny(table, "[]") {
				return nil, fmt.Errorf("line %d: malformed table header %q", n, line)
			}
			continue
		}

		key, rest, ok := strings.Cut(line, "=")
		if !ok {
			return nil, fmt.Errorf("line %d: expected a `key = \"value\"` assignment, got %q", n, line)
		}
		key = strings.TrimSpace(key)
		if key == "" {
			return nil, fmt.Errorf("line %d: expected a key before `=`", n)
		}
		value, err := quotedString(n, strings.TrimSpace(rest))
		if err != nil {
			return nil, err
		}
		if table != "" {
			key = table + "." + key
		}
		if _, dup := values[key]; dup {
			return nil, fmt.Errorf("line %d: duplicate key %q", n, key)
		}
		values[key] = value
	}

	org := values["organization"]
	if org == "" {
		return nil, errors.New("policy is missing a non-empty top-level `organization` key")
	}
	// IR-001 requires one validation boundary for GitHub logins, and this is a containment
	// boundary as well as a spelling check: the organization is interpolated into API
	// request paths, so anything outside the login alphabet must be refused before it can
	// reshape a URL. ghapi owns that validator because every request path is built there;
	// a private copy here was a second implementation free to drift (DEV-021).
	if err := ghapi.ValidateLogin(org); err != nil {
		return nil, fmt.Errorf("policy `organization` value %q is not a valid GitHub login: %w", org, err)
	}

	version := values["package_version"]
	if version == "" {
		version = values["version"]
	}
	if version == "" {
		version = values["package.version"]
	}
	handoff := values["handoff_admission"]
	if handoff == "" {
		handoff = HandoffAdmissionDefault
	}
	if handoff != HandoffAdmissionDefault && handoff != HandoffAdmissionNone {
		return nil, fmt.Errorf("policy `handoff_admission` value %q is not %q or %q",
			handoff, HandoffAdmissionDefault, HandoffAdmissionNone)
	}
	return &Policy{
		Organization:         org,
		Version:              version,
		IntegrationBranch:    values["integration_branch"],
		ReleaseSubjectPrefix: values["release_subject_prefix"],
		AdmissionFloor:       values["admission_floor"],
		HandoffAdmission:     handoff,
	}, nil
}

// The two spellings `handoff_admission` accepts. An unrecognized third value is a load
// error rather than a fallback to the default: a typo that silently keeps the exemption
// on is the one outcome a consumer switching it off cannot detect.
const (
	HandoffAdmissionDefault = "agent-handoff"
	HandoffAdmissionNone    = "none"
)

// quotedString accepts only a fully double-quoted scalar. Bare values, arrays, inline
// tables, and multi-line strings are refused rather than guessed at.
func quotedString(n int, s string) (string, error) {
	if len(s) < 2 || s[0] != '"' || s[len(s)-1] != '"' {
		return "", fmt.Errorf("line %d: value %q must be a double-quoted string", n, s)
	}
	inner := s[1 : len(s)-1]
	if strings.ContainsAny(inner, "\"\\") {
		return "", fmt.Errorf("line %d: escapes inside quoted values are not supported", n)
	}
	return inner, nil
}
