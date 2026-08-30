package render

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
)

// Repository is the owner and name of a GitHub repository.
type Repository struct {
	Owner string `json:"owner"`
	Name  string `json:"name"`
}

// String renders the repository as `owner/name`, the form every message and report uses.
func (r Repository) String() string { return r.Owner + "/" + r.Name }

// ParseRepository reads an `owner/name` value and validates both halves as GitHub
// identities.
//
// This is one of the four entry points spec IR-001 requires to share a single identity
// boundary (closing DEV-021): an explicit `--repo owner/name` reaching here, an
// origin-derived owner reaching it through OriginRepository, the rendered policy
// organization, and `audit --org`. The grammar itself lives in ghapi.ValidateRepository,
// which the client also enforces when it builds a request path — validating here as well
// is not redundant, because it is what lets the operator be refused by the flag they typed
// instead of by a URL they never saw.
func ParseRepository(value string) (Repository, error) {
	owner, name, ok := strings.Cut(strings.TrimSpace(value), "/")
	if !ok || owner == "" || name == "" || strings.Contains(name, "/") {
		return Repository{}, fmt.Errorf("repository %q must be in owner/name form", value)
	}
	if err := ghapi.ValidateRepository(owner, name); err != nil {
		return Repository{}, fmt.Errorf("repository %q: %w", value, err)
	}
	return Repository{Owner: owner, Name: name}, nil
}

// checkoutRoot walks up from start to the enclosing Git checkout, which is where the
// `origin` remote that names the repository is configured. It is unexported because
// OriginRepository is the only caller left now that no subcommand writes a file.
func checkoutRoot(start string) (string, error) {
	dir, err := filepath.Abs(start)
	if err != nil {
		return "", fmt.Errorf("resolving the working directory %s: %w", start, err)
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("%s is not inside a Git checkout", start)
		}
		dir = parent
	}
}

// OriginRepository reads the enclosing checkout's `origin` remote.
//
// This is what makes a bare `gh-workflow summary` work: the repository the operator
// means is the one they are standing in, and asking would violate the non-interactive
// contract. Git configuration is read directly rather than by shelling out to `git`,
// which the tool does not require to be installed.
func OriginRepository(start string) (Repository, error) {
	root, err := checkoutRoot(start)
	if err != nil {
		return Repository{}, err
	}
	configPath, err := gitConfigPath(filepath.Join(root, ".git"))
	if err != nil {
		return Repository{}, err
	}
	// #nosec G304 -- the path is derived from the checkout the operator invoked the tool
	// in, which is the file the tool is meant to read.
	data, err := os.ReadFile(configPath)
	if err != nil {
		return Repository{}, fmt.Errorf("reading %s: %w", configPath, err)
	}
	url, err := originURL(string(data))
	if err != nil {
		return Repository{}, fmt.Errorf("%s: %w", configPath, err)
	}
	return repositoryFromURL(url)
}

// gitConfigPath resolves `.git` to the configuration file that actually holds the
// remotes. In a linked worktree `.git` is a file pointing at a per-worktree directory
// whose `commondir` leads back to the shared configuration — agents routinely work in
// one, so following the indirection is not an edge case.
func gitConfigPath(gitPath string) (string, error) {
	info, err := os.Stat(gitPath)
	if err != nil {
		return "", fmt.Errorf("reading %s: %w", gitPath, err)
	}
	if info.IsDir() {
		return filepath.Join(gitPath, "config"), nil
	}

	// #nosec G304 -- see OriginRepository; this is the checkout's own .git pointer file.
	data, err := os.ReadFile(gitPath)
	if err != nil {
		return "", fmt.Errorf("reading %s: %w", gitPath, err)
	}
	gitDir := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(string(data)), "gitdir:"))
	if gitDir == "" {
		return "", fmt.Errorf("%s does not name a git directory", gitPath)
	}
	if !filepath.IsAbs(gitDir) {
		gitDir = filepath.Join(filepath.Dir(gitPath), gitDir)
	}

	commonPath := filepath.Join(gitDir, "commondir")
	// #nosec G304 G703 -- see above; still inside the checkout's own git directory.
	common, err := os.ReadFile(commonPath)
	if err != nil {
		return filepath.Join(gitDir, "config"), nil
	}
	shared := strings.TrimSpace(string(common))
	if !filepath.IsAbs(shared) {
		shared = filepath.Join(gitDir, shared)
	}
	return filepath.Join(shared, "config"), nil
}

// originURL extracts the origin remote's URL from git configuration. The accepted subset
// is section headers and `key = value` assignments, which is all a remote definition
// needs; anything else is skipped rather than parsed.
func originURL(config string) (string, error) {
	inOrigin := false
	for _, raw := range strings.Split(config, "\n") {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		if strings.HasPrefix(line, "[") {
			inOrigin = strings.HasPrefix(line, `[remote "origin"]`)
			continue
		}
		if !inOrigin {
			continue
		}
		if key, value, ok := strings.Cut(line, "="); ok && strings.TrimSpace(key) == "url" {
			return strings.TrimSpace(value), nil
		}
	}
	return "", errors.New("no `origin` remote is configured")
}

// repositoryFromURL accepts the remote URL forms Git writes: scp-like SSH, ssh://, and
// https://.
//
// The host is validated as well as the owner and name, because this is the one path where
// the identity is not typed by the operator: whatever `origin` happens to say becomes the
// repository every subsequent request addresses. A malformed host is refused here rather
// than being silently dropped on the way to building an `owner/name` pair.
func repositoryFromURL(remote string) (Repository, error) {
	trimmed := strings.TrimSuffix(strings.TrimSpace(remote), ".git")
	path, host := trimmed, ""
	switch {
	case strings.Contains(trimmed, "://"):
		_, rest, _ := strings.Cut(trimmed, "://")
		if before, after, ok := strings.Cut(rest, "/"); ok {
			host, path = before, after
		}
	case strings.Contains(trimmed, ":"):
		before, after, _ := strings.Cut(trimmed, ":")
		host, path = before, after
	}
	// An scp-like remote carries `user@host`, and an ssh:// URL may carry a port; both are
	// ordinary and neither is part of the hostname the validator judges.
	if _, after, ok := strings.Cut(host, "@"); ok {
		host = after
	}
	if before, _, ok := strings.Cut(host, ":"); ok {
		host = before
	}
	if host != "" {
		if err := ghapi.ValidateHost(host); err != nil {
			return Repository{}, fmt.Errorf("origin remote %q does not name a GitHub repository: %w", remote, err)
		}
	}
	repo, err := ParseRepository(strings.Trim(path, "/"))
	if err != nil {
		return Repository{}, fmt.Errorf("origin remote %q does not name a GitHub repository", remote)
	}
	return repo, nil
}
