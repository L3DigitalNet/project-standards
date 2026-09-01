package admission

// The git reader and the command's end-to-end behavior over a real, throwaway
// repository. These are in-package because the log framing (`parseLog`) is an internal
// contract with the format string above it, not something a consumer configures.

import (
	"bytes"
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
)

func TestParseLogFramesSubjectsAndBodiesContainingControlText(t *testing.T) {
	t.Parallel()

	// A subject with a pipe and a body with blank lines and a trailer: the shape that
	// breaks any framing built from newlines or printable delimiters.
	stream := recordSeparator + "abc123" + fieldSeparator + "fix: a | b" + fieldSeparator + "p1" +
		fieldSeparator + "fix: a | b\n\nDetail line.\n\nWorkflow-Admission: T0\n" + bodySeparator +
		"README.md\ndocs/TODO.md\n" +
		recordSeparator + "def456" + fieldSeparator + "merge" + fieldSeparator + "p1 p2" +
		fieldSeparator + "merge\n" + bodySeparator + "\n"

	commits, err := parseLog(stream)
	if err != nil {
		t.Fatalf("parseLog() error = %v", err)
	}
	if len(commits) != 2 {
		t.Fatalf("parseLog() returned %d commits, want 2", len(commits))
	}
	if commits[0].Subject != "fix: a | b" {
		t.Errorf("Subject = %q, want the pipe preserved", commits[0].Subject)
	}
	if got := commits[0].Paths; len(got) != 2 || got[0] != "README.md" || got[1] != "docs/TODO.md" {
		t.Errorf("Paths = %v, want both files", got)
	}
	if commits[0].IsMerge {
		t.Error("a single-parent commit was reported as a merge")
	}
	// A merge reports two parents and no paths, which is why the handoff class can
	// never apply to one.
	if !commits[1].IsMerge || len(commits[1].Paths) != 0 {
		t.Errorf("merge commit = %+v, want IsMerge with no paths", commits[1])
	}
}

// git is the throwaway repository builder. Each helper commits with a fixed identity so
// the fixture never depends on the developer's or the worker's git configuration.
type gitRepo struct {
	t   *testing.T
	dir string
}

func newGitRepo(t *testing.T) *gitRepo {
	t.Helper()
	repo := &gitRepo{t: t, dir: t.TempDir()}
	repo.run("init", "--initial-branch=main")
	repo.run("config", "user.email", "fixture@example.invalid")
	repo.run("config", "user.name", "Fixture")
	// A repository-local commit.gpgsign=false keeps a developer's global signing
	// configuration from making every fixture commit prompt or fail.
	repo.run("config", "commit.gpgsign", "false")
	// Point core.hooksPath at an empty directory. A developer's global hooks path is
	// inherited by every `git init`, and this workstation's global pre-commit hook
	// refuses any author email but the owner's — which would fail this fixture on one
	// machine and pass it on CI. The fixture must depend on git, not on git's
	// configuration.
	hooks := filepath.Join(repo.dir, ".empty-hooks")
	if err := os.MkdirAll(hooks, 0o755); err != nil {
		t.Fatal(err)
	}
	repo.run("config", "core.hooksPath", hooks)
	return repo
}

func (g *gitRepo) run(args ...string) string {
	g.t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = g.dir
	out, err := cmd.CombinedOutput()
	if err != nil {
		g.t.Fatalf("git %s: %v\n%s", strings.Join(args, " "), err, out)
	}
	return string(out)
}

func (g *gitRepo) commit(message string, files map[string]string) {
	g.t.Helper()
	for relative, content := range files {
		path := filepath.Join(g.dir, filepath.FromSlash(relative))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			g.t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			g.t.Fatal(err)
		}
	}
	g.run("add", "-A")
	g.run("commit", "-m", message)
}

func (g *gitRepo) exec(t *testing.T, args ...string) (int, string, string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	env := &cli.Env{Stdout: &stdout, Stderr: &stderr, WorkDir: g.dir}
	code := cli.Run(context.Background(), env, args)
	return code, stdout.String(), stderr.String()
}

// The negative control ADR 0031's confirmation section requires: a corpus where every
// commit is admitted exits 0, and removing one trailer makes the same corpus exit 1.
func TestAdmissionExitsCleanOnAFullyAdmittedHistoryAndFailsWhenOneTrailerIsRemoved(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))

	repo.commit("fix: typo\n\nWorkflow-Admission: T0\n", map[string]string{"README.md": "seed.\n"})
	repo.commit("feat: real work\n\nWorkflow-Admission: PR #7\n", map[string]string{"src/app.py": "x = 1\n"})
	repo.commit("docs(handoff): close out\n\nWorkflow-Admission: handoff\n",
		map[string]string{"docs/handoff/state.md": "state\n"})
	repo.commit("release: prepare v1.0.0\n\nWorkflow-Admission: release\n",
		map[string]string{"pyproject.toml": "[project]\n"})

	code, stdout, stderr := repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout:\n%s\nstderr:\n%s", code, stdout, stderr)
	}
	for _, want := range []string{"1 T0", "1 pull request", "1 handoff", "1 release", "0 unadmitted"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("report omits %q:\n%s", want, stdout)
		}
	}

	// Removing exactly one trailer must move the verdict. A control that stays green
	// when the rule is broken proves nothing about the corpus it just passed.
	repo.run("commit", "--amend", "--no-edit", "-m", "release: prepare v1.0.0")
	code, stdout, _ = repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d after removing a trailer, want 1\n%s", code, stdout)
	}
	if !strings.Contains(stdout, "1 unadmitted") {
		t.Errorf("report does not count the unadmitted commit:\n%s", stdout)
	}
}

// A release-class commit with no trailer is still admitted when the repository declares
// the subject prefix, which is what lets a consumer adopt 1.9 without rewriting the
// release tooling in the same change.
func TestAdmissionHonorsTheReleaseSubjectPrefixFromPolicy(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.commit("release: prepare v1.0.0", map[string]string{"pyproject.toml": "[project]\n"})

	policyPath := filepath.Join(repo.dir, "policy.toml")
	if err := os.WriteFile(policyPath, []byte(
		"organization = \"ExampleOrg\"\nrelease_subject_prefix = \"release: prepare v\"\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, stdout, stderr := repo.exec(t,
		"admission", "--branch", "main", "--since", base, "--offline", "--policy", policyPath)
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout:\n%s\nstderr:\n%s", code, stdout, stderr)
	}

	// Without the prefix configured, the same commit is unadmitted: the option is
	// load-bearing rather than decorative.
	code, _, _ = repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d with no release prefix configured, want 1", code)
	}
}

// `handoff_admission = "none"` removes the class for a consumer that never adopted
// `agent-handoff` and whose `docs/TODO.md` is an ordinary document.
func TestAdmissionHandoffClassCanBeSwitchedOff(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.commit("docs: roadmap\n\nWorkflow-Admission: handoff\n", map[string]string{"docs/TODO.md": "todo\n"})

	policyPath := filepath.Join(repo.dir, "policy.toml")
	if err := os.WriteFile(policyPath, []byte(
		"organization = \"ExampleOrg\"\nhandoff_admission = \"none\"\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, stdout, _ := repo.exec(t,
		"admission", "--branch", "main", "--since", base, "--offline", "--policy", policyPath)
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d, want 1 when the handoff class is switched off\n%s", code, stdout)
	}
	if !strings.Contains(stdout, CodeHandoffDisabled) {
		t.Errorf("report does not name %s:\n%s", CodeHandoffDisabled, stdout)
	}
}

// #203's requirement that the check target the branch where work actually lands: the
// branch is a flag, and naming a branch that is not checked out still works.
func TestAdmissionTargetsANamedBranchThatIsNotCheckedOut(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.run("checkout", "-b", "testing")
	repo.commit("feat: work", map[string]string{"src/app.py": "x = 1\n"})
	repo.run("checkout", "main")

	code, stdout, _ := repo.exec(t, "admission", "--branch", "testing", "--since", base, "--offline")
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d, want 1 for the unadmitted commit on `testing`\n%s", code, stdout)
	}
	if !strings.Contains(stdout, "Branch:  testing") {
		t.Errorf("report does not name the branch it classified:\n%s", stdout)
	}

	// `main` at the same floor holds nothing, so the same invocation is clean there —
	// which is what makes the branch flag meaningful rather than incidental.
	if code, _, _ := repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline"); code != cli.ExitOK {
		t.Errorf("exit = %d on the empty range, want 0", code)
	}
}

func TestAdmissionRefusesAnUnknownBranchRatherThanReportingItClean(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})

	code, stdout, _ := repo.exec(t, "admission", "--branch", "no-such-branch", "--offline")
	if code == cli.ExitOK {
		t.Fatalf("exit = 0 for an unknown branch; a nonexistent range must never read as compliant\n%s", stdout)
	}
}

func TestAdmissionRefusesWithNoBranchAndNoConfiguredIntegrationBranch(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})

	if code, _, _ := repo.exec(t, "admission", "--offline"); code != cli.ExitUsage {
		t.Errorf("exit = %d with no branch named, want %d", code, cli.ExitUsage)
	}
}
