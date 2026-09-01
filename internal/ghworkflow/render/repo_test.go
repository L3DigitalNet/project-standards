package render_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// Zero-argument operation (IR-004) rests on reading the checkout's own origin remote, so
// every URL form a consumer checkout can carry has to resolve to the same repository.
func TestOriginRepository(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		config string
		want   string
	}{
		{"ssh scp form", "[remote \"origin\"]\n\turl = git@github.com:L3DigitalNet/example-repo.git\n", "L3DigitalNet/example-repo"},
		{"https", "[remote \"origin\"]\n\turl = https://github.com/L3DigitalNet/example-repo.git\n", "L3DigitalNet/example-repo"},
		{"https without suffix", "[remote \"origin\"]\n\turl = https://github.com/L3DigitalNet/example-repo\n", "L3DigitalNet/example-repo"},
		{"ssh url form", "[remote \"origin\"]\n\turl = ssh://git@github.com/L3DigitalNet/example-repo.git\n", "L3DigitalNet/example-repo"},
		{"origin after another remote", "[remote \"upstream\"]\n\turl = git@github.com:other/repo.git\n[remote \"origin\"]\n\turl = git@github.com:L3DigitalNet/example-repo.git\n", "L3DigitalNet/example-repo"},
		{"no origin", "[remote \"upstream\"]\n\turl = git@github.com:other/repo.git\n", ""},
		{"no remotes", "[core]\n\tbare = false\n", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			root := t.TempDir()
			gitDir := filepath.Join(root, ".git")
			if err := os.MkdirAll(gitDir, 0o750); err != nil {
				t.Fatalf("MkdirAll error = %v", err)
			}
			if err := os.WriteFile(filepath.Join(gitDir, "config"), []byte(tc.config), 0o600); err != nil {
				t.Fatalf("WriteFile error = %v", err)
			}
			nested := filepath.Join(root, "a", "b")
			if err := os.MkdirAll(nested, 0o750); err != nil {
				t.Fatalf("MkdirAll error = %v", err)
			}

			repo, err := render.OriginRepository(nested)
			if tc.want == "" {
				if err == nil {
					t.Fatalf("OriginRepository() = %v, want an error", repo)
				}
				return
			}
			if err != nil {
				t.Fatalf("OriginRepository() error = %v", err)
			}
			if repo.String() != tc.want {
				t.Errorf("OriginRepository() = %q, want %q", repo, tc.want)
			}
		})
	}
}

// A worktree's .git is a file pointing at the real git directory; the tool runs in one
// whenever an agent works in an isolated checkout, so resolution must follow it.
func TestOriginRepositoryFollowsAWorktreeGitFile(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	common := filepath.Join(root, "main", ".git")
	worktreeGitDir := filepath.Join(common, "worktrees", "wt")
	for _, dir := range []string{common, worktreeGitDir} {
		if err := os.MkdirAll(dir, 0o750); err != nil {
			t.Fatalf("MkdirAll error = %v", err)
		}
	}
	writeFile := func(path, body string) {
		if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
			t.Fatalf("WriteFile(%s) error = %v", path, err)
		}
	}
	writeFile(filepath.Join(common, "config"),
		"[remote \"origin\"]\n\turl = git@github.com:L3DigitalNet/example-repo.git\n")
	writeFile(filepath.Join(worktreeGitDir, "commondir"), "../..\n")

	checkout := filepath.Join(root, "wt")
	if err := os.MkdirAll(checkout, 0o750); err != nil {
		t.Fatalf("MkdirAll error = %v", err)
	}
	writeFile(filepath.Join(checkout, ".git"), "gitdir: "+worktreeGitDir+"\n")

	repo, err := render.OriginRepository(checkout)
	if err != nil {
		t.Fatalf("OriginRepository() error = %v", err)
	}
	if got, want := repo.String(), "L3DigitalNet/example-repo"; got != want {
		t.Errorf("OriginRepository() = %q, want %q", got, want)
	}
}

func TestParseRepository(t *testing.T) {
	t.Parallel()

	if _, err := render.ParseRepository("owner/name/extra"); err == nil {
		t.Error("ParseRepository() accepted a three-segment value")
	}
	if _, err := render.ParseRepository("owner/"); err == nil {
		t.Error("ParseRepository() accepted an empty repository name")
	}
	repo, err := render.ParseRepository("L3DigitalNet/example-repo")
	if err != nil {
		t.Fatalf("ParseRepository() error = %v", err)
	}
	if repo.Owner != "L3DigitalNet" || repo.Name != "example-repo" {
		t.Errorf("ParseRepository() = %+v", repo)
	}
}

// #234 item 5: an origin on another Git host still yields a well-formed owner/name pair,
// and every request the tool then makes goes to the API host — so without this comparison
// a same-named repository on GitHub is what actually gets written.
func TestVerifyAPIHostRefusesAForeignOrigin(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name       string
		host       string
		fromOrigin bool
		apiBase    string
		wantErr    bool
	}{
		{name: "github.com against the public API", host: "github.com", fromOrigin: true,
			apiBase: "https://api.github.com"},
		{name: "enterprise host and its own API path", host: "ghe.example.com", fromOrigin: true,
			apiBase: "https://ghe.example.com/api/v3"},
		{name: "explicit --repo carries no host", host: "", apiBase: "https://api.github.com"},
		{name: "foreign origin", host: "gitlab.com", fromOrigin: true,
			apiBase: "https://api.github.com", wantErr: true},
		// A suffix match would accept this one; the rule is equality or the `api.` prefix.
		{name: "lookalike origin", host: "evil-github.com", fromOrigin: true,
			apiBase: "https://api.github.com", wantErr: true},
		// An origin-derived pair with no host is the bypass: it is indistinguishable from
		// an explicitly typed one unless FromOrigin says otherwise, and it reached the API
		// host having passed no host check at all.
		{name: "origin-derived with no parseable host", host: "", fromOrigin: true,
			apiBase: "https://api.github.com", wantErr: true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			repo := render.Repository{Owner: "L3DigitalNet", Name: "example-repo",
				Host: tc.host, FromOrigin: tc.fromOrigin}
			err := repo.VerifyAPIHost(tc.apiBase)
			if tc.wantErr && err == nil {
				t.Fatalf("VerifyAPIHost(%q) with origin %q = nil, want a refusal", tc.apiBase, tc.host)
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("VerifyAPIHost(%q) with origin %q = %v, want nil", tc.apiBase, tc.host, err)
			}
		})
	}
}

// Git accepts a remote with no host at all, and both spellings previously produced an
// origin-derived repository that skipped ValidateHost (nothing to validate) and then
// VerifyAPIHost (no host to compare) — reaching api.github.com unchecked.
func TestOriginRepositoryMarksAHostlessRemoteAsOriginDerived(t *testing.T) {
	t.Parallel()

	for _, remote := range []string{"owner/repo", ":owner/repo"} {
		t.Run(remote, func(t *testing.T) {
			t.Parallel()

			root := t.TempDir()
			if err := os.MkdirAll(filepath.Join(root, ".git"), 0o750); err != nil {
				t.Fatalf("MkdirAll() error = %v", err)
			}
			config := "[remote \"origin\"]\n\turl = " + remote + "\n"
			if err := os.WriteFile(filepath.Join(root, ".git", "config"), []byte(config), 0o600); err != nil {
				t.Fatalf("WriteFile() error = %v", err)
			}
			repo, err := render.OriginRepository(root)
			if err != nil {
				// A remote this malformed may be refused outright, which closes the hole
				// just as well; what must never happen is a silently accepted pair.
				return
			}
			if err := repo.VerifyAPIHost("https://api.github.com"); err == nil {
				t.Errorf("origin %q resolved to %+v and passed the host check", remote, repo)
			}
		})
	}
}
