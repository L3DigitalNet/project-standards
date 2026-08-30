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
)

// Policy is the parsed consumer configuration.
type Policy struct {
	// Organization is the GitHub login the audit targets. Required.
	Organization string
	// Version is the package version stamped into the rendered file, if present.
	// It is informational: no tool behavior depends on it.
	Version string
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
	if !validLogin(org) {
		return nil, fmt.Errorf("policy `organization` value %q is not a valid GitHub login", org)
	}

	version := values["package_version"]
	if version == "" {
		version = values["version"]
	}
	if version == "" {
		version = values["package.version"]
	}
	return &Policy{Organization: org, Version: version}, nil
}

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

// validLogin mirrors GitHub's account-name rules. It is also a containment boundary: the
// login is interpolated into the API request path, so anything outside this alphabet is
// refused before it can reshape a URL.
func validLogin(s string) bool {
	if len(s) > 39 || strings.HasPrefix(s, "-") || strings.HasSuffix(s, "-") {
		return false
	}
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9', r == '-':
		default:
			return false
		}
	}
	return true
}
