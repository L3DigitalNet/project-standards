package ghapi

// The one GitHub identity boundary (spec IR-001, closing DEV-021).
//
// Through 1.6 four routes reached the API with different amounts of checking: the
// rendered policy organization went through the policy reader's own login check, while an
// explicit `audit --org`, a full explicit `--repo owner/name`, and an origin-derived owner
// reached the request path with `url.PathEscape` as their only containment. From 1.7 every
// one of those owners passes through ValidateLogin here, and every repository name through
// ValidateRepositoryName, before the client builds a request — the validators are called
// from the request-building helpers in this package, so a caller cannot reach GitHub by
// skipping them.
//
// These refusals are local input rejections, not operational failures: they carry no
// Operational marker, so the CLI classifies them as usage (exit 2) rather than as an
// API/transport failure (exit 3). See operational.go for the other half of that split.
//
// Counterpart: internal/ghworkflow/render/repo.go (ParseRepository/OriginRepository) and
// internal/ghworkflow/policy/policy.go apply the same grammar at their own entry points so
// the operator is refused with a message naming the flag or file that supplied the value.
// policy.go still carries its own copy of the login rule; it is the one site outside this
// package's ownership and is intentionally left to the integration owner to reroute.

import (
	"errors"
	"fmt"
	"strings"
)

// ErrInvalidIdentity marks every value refused by this file, so a caller can classify an
// identity refusal without matching on message text.
var ErrInvalidIdentity = errors.New("not a valid GitHub identity")

// maxLoginLength is GitHub's own account-name ceiling; NFR-003's block measurement is
// taken at exactly this length, so the two must not drift apart.
const maxLoginLength = 39

// maxRepositoryNameLength is GitHub's repository-name ceiling.
const maxRepositoryNameLength = 100

// ValidateLogin accepts a GitHub user or organization login and rejects everything else.
//
// The grammar is GitHub's: 1 to 39 characters of ASCII alphanumerics and hyphens, with no
// leading hyphen, no trailing hyphen, and no doubled hyphen. It is deliberately stricter
// than "safe to put in a URL path" — a login that merely escapes cleanly can still name a
// host-shaped or traversal-shaped value that reaches an unintended organization endpoint
// under the operator's bearer token, and the audit would report that stranger's schema as
// the configured organization's drift.
func ValidateLogin(login string) error {
	if login == "" {
		return fmt.Errorf("%w: an empty GitHub login", ErrInvalidIdentity)
	}
	if len(login) > maxLoginLength {
		return fmt.Errorf("%w: the GitHub login %q is longer than %d characters",
			ErrInvalidIdentity, login, maxLoginLength)
	}
	if strings.HasPrefix(login, "-") || strings.HasSuffix(login, "-") || strings.Contains(login, "--") {
		return fmt.Errorf("%w: the GitHub login %q must not begin, end, or run two hyphens together",
			ErrInvalidIdentity, login)
	}
	for _, r := range login {
		if !isLoginRune(r) {
			return fmt.Errorf("%w: the GitHub login %q may contain only letters, digits, and hyphens",
				ErrInvalidIdentity, login)
		}
	}
	return nil
}

// ValidateRepositoryName accepts a GitHub repository name and rejects everything else.
//
// The alphabet is wider than a login's — letters, digits, `-`, `_`, and `.` — which is
// why `.` and `..` are refused by name: both are legal spellings under that alphabet and
// both would rewrite the request path they are interpolated into rather than address a
// repository.
func ValidateRepositoryName(name string) error {
	if name == "" {
		return fmt.Errorf("%w: an empty repository name", ErrInvalidIdentity)
	}
	if len(name) > maxRepositoryNameLength {
		return fmt.Errorf("%w: the repository name %q is longer than %d characters",
			ErrInvalidIdentity, name, maxRepositoryNameLength)
	}
	if name == "." || name == ".." {
		return fmt.Errorf("%w: %q is a path segment, not a repository name", ErrInvalidIdentity, name)
	}
	for _, r := range name {
		if !isLoginRune(r) && r != '_' && r != '.' {
			return fmt.Errorf("%w: the repository name %q may contain only letters, digits, "+
				"hyphens, underscores, and dots", ErrInvalidIdentity, name)
		}
	}
	return nil
}

// ValidateHost accepts the host part of a Git remote or API base URL.
//
// It validates DNS-label shape only and deliberately does not compare against
// `github.com`: GitHub Enterprise Server installations are legitimate hosts under this
// package's own configurable base URL, so an allowlist would refuse a supported
// deployment. What it does refuse is a host carrying userinfo, a path, or whitespace —
// the shapes that let a crafted `origin` URL steer a request somewhere the operator did
// not name, which is the concrete risk on the origin-derived path.
func ValidateHost(host string) error {
	if host == "" {
		return fmt.Errorf("%w: an empty host", ErrInvalidIdentity)
	}
	if strings.ContainsAny(host, "@/\\ \t?#") {
		return fmt.Errorf("%w: the host %q is not a bare hostname", ErrInvalidIdentity, host)
	}
	for _, label := range strings.Split(host, ".") {
		if label == "" {
			return fmt.Errorf("%w: the host %q has an empty label", ErrInvalidIdentity, host)
		}
		if strings.HasPrefix(label, "-") || strings.HasSuffix(label, "-") {
			return fmt.Errorf("%w: the host %q has a label bounded by a hyphen", ErrInvalidIdentity, host)
		}
		for _, r := range label {
			if !isLoginRune(r) {
				return fmt.Errorf("%w: the host %q contains %q", ErrInvalidIdentity, host, r)
			}
		}
	}
	return nil
}

// ValidateRepository validates both halves of an `owner/name` pair.
func ValidateRepository(owner, name string) error {
	if err := ValidateLogin(owner); err != nil {
		return err
	}
	return ValidateRepositoryName(name)
}

func isLoginRune(r rune) bool {
	switch {
	case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9', r == '-':
		return true
	default:
		return false
	}
}
