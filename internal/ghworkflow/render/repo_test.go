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
