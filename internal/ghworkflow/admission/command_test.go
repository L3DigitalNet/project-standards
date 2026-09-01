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
	// breaks any framing built from newlines or printable delimiters. The path blocks
	// reproduce git's `-z --name-status` framing exactly — the NUL that terminates the
	// commit header, the newline before the diff, then status/path token pairs.
	stream := recordSeparator + "abc123" + fieldSeparator + "fix: a | b" + fieldSeparator + "p1" +
		fieldSeparator + "fix: a | b\n\nDetail line.\n\nWorkflow-Admission: T0\n" + bodySeparator +
		"\x00\nM\x00README.md\x00M\x00docs/TODO.md\x00" +
		recordSeparator + "def456" + fieldSeparator + "merge" + fieldSeparator + "p1 p2" +
		fieldSeparator + "merge\n" + bodySeparator + "\x00"

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

// The path block is where the handoff exemption is decided, so its parsing is pinned
// case by case rather than through the classifier.
func TestSplitPathsReadsEveryPathOfTheNameStatusBlockByExactBytes(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		tail string
		want []string
	}{
		{
			// A merge, or any commit git shows no diff for: the header's NUL is the
			// whole block and there is no newline, because there is no diff to precede.
			name: "no diff at all",
			tail: "\x00",
			want: nil,
		},
		{
			// --no-renames splits a rename into its delete and its add, so a `git mv`
			// into an exempt directory can no longer present only the destination.
			name: "rename reported as both of its paths",
			tail: "\x00\nD\x00src/app.py\x00A\x00docs/handoff/app.py\x00",
			want: []string{"src/app.py", "docs/handoff/app.py"},
		},
		{
			// The status letter never decides anything: a deleted non-exempt path
			// disqualifies a handoff claim exactly as a modified one does.
			name: "deletion of a non-handoff path",
			tail: "\x00\nD\x00src/app.py\x00",
			want: []string{"src/app.py"},
		},
		{
			// The leading space belongs to the filename. Trimming it would produce
			// "docs/handoff/x.md" and admit a file that is not in the exempt set.
			name: "leading space is part of the path",
			tail: "\x00\nM\x00 docs/handoff/x.md\x00",
			want: []string{" docs/handoff/x.md"},
		},
		{
			// -z suppresses git's C-quoting, so a non-ASCII exempt path arrives raw and
			// still matches the prefix instead of arriving as "docs/handoff/\303\251.md".
			name: "non-ASCII path under the exempt prefix",
			tail: "\x00\nM\x00docs/handoff/é.md\x00",
			want: []string{"docs/handoff/é.md"},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got, err := splitPaths(tc.tail)
			if err != nil {
				t.Fatalf("splitPaths(%q) error = %v", tc.tail, err)
			}
			if len(got) != len(tc.want) {
				t.Fatalf("splitPaths(%q) = %q, want %q", tc.tail, got, tc.want)
			}
			for i := range got {
				if got[i] != tc.want[i] {
					t.Errorf("path %d = %q, want %q", i, got[i], tc.want[i])
				}
			}
		})
	}

	// An unpaired token means git emitted a shape the status/path alternation does not
	// describe. Reporting it beats silently classifying half a commit's paths.
	if _, err := splitPaths("\x00\nM\x00a.md\x00D\x00"); err == nil {
		t.Error("splitPaths() accepted an odd token count; a malformed block must be reported")
	}
}

// The F1 forgery, at the layer that reads git: a commit that moves an arbitrary file
// into `docs/handoff/` while declaring the handoff class. Under `--name-only` the log
// collapsed the rename to its destination and the commit read as pure handoff.
func TestAdmissionRefusesAHandoffCommitThatRenamesAFileIntoTheExemptTree(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n", "src/app.py": "x = 1\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))

	if err := os.MkdirAll(filepath.Join(repo.dir, "docs", "handoff"), 0o755); err != nil {
		t.Fatal(err)
	}
	repo.run("mv", "src/app.py", "docs/handoff/app.py")
	repo.run("commit", "-m", "docs(handoff): note\n\nWorkflow-Admission: handoff\n")

	code, stdout, _ := repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d, want 1: moving a file into the exempt tree must not be admitted\n%s", code, stdout)
	}
	if !strings.Contains(stdout, CodeHandoffMixed) || !strings.Contains(stdout, "src/app.py") {
		t.Errorf("report does not name %s and the source path it left behind:\n%s", CodeHandoffMixed, stdout)
	}
}

// The exempt prefix is matched against raw bytes, so a non-ASCII handoff document is
// still a handoff document. With git's default C-quoting it would arrive escaped and
// the commit would be misreported as mixed.
func TestAdmissionAdmitsAHandoffCommitTouchingANonASCIIPath(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	base := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.commit("docs(handoff): note\n\nWorkflow-Admission: handoff\n",
		map[string]string{"docs/handoff/état.md": "state\n"})

	code, stdout, stderr := repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout:\n%s\nstderr:\n%s", code, stdout, stderr)
	}
	if !strings.Contains(stdout, "1 handoff") {
		t.Errorf("report does not count the handoff commit:\n%s", stdout)
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

	// `main` at the same floor holds nothing, which the classifier reports as an empty
	// range rather than as a clean one — the branch flag decides what was examined, and
	// examining nothing is never a verdict.
	code, stdout, _ = repo.exec(t, "admission", "--branch", "main", "--since", base, "--offline")
	if code != cli.ExitFailure || !strings.Contains(stdout, CodeEmptyRange) {
		t.Errorf("exit = %d on the empty range, want 1 naming %s:\n%s", code, CodeEmptyRange, stdout)
	}
}

// F2: "0 commits, 0 unadmitted, exit 0" is indistinguishable from compliance, so a
// range that selects nothing is refused instead of reported clean.
func TestAdmissionRefusesARangeThatResolvesToZeroCommits(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	head := strings.TrimSpace(repo.run("rev-parse", "HEAD"))

	code, stdout, _ := repo.exec(t, "admission", "--branch", "main", "--since", head, "--offline")
	if code != cli.ExitFailure {
		t.Fatalf("exit = %d for a floor at the branch tip, want 1\n%s", code, stdout)
	}
	if !strings.Contains(stdout, CodeEmptyRange) {
		t.Errorf("report does not name %s:\n%s", CodeEmptyRange, stdout)
	}
}

// F2: without the `--` pathspec terminator git reads a revision it cannot resolve as a
// pathspec, so `--branch docs` in a repository holding a `docs/` directory logged the
// commits that touched it and exited 0 — a verdict about a branch that does not exist.
func TestAdmissionRefusesABranchNameThatOnlyMatchesAnExistingDirectory(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("docs: seed\n\nWorkflow-Admission: T0\n", map[string]string{"docs/guide.md": "seed\n"})

	code, stdout, _ := repo.exec(t, "admission", "--branch", "docs", "--offline")
	if code == cli.ExitOK {
		t.Fatalf("exit = 0 for `docs`, which is a directory and not a branch\n%s", stdout)
	}
}

// F3: a floor off the branch's own history bounds nothing on that branch, so the range
// it produces is not the "everything after adoption" the option promises.
func TestAdmissionRefusesAFloorThatIsNotAnAncestorOfTheBranch(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	repo.run("checkout", "-q", "-b", "sidetrack")
	repo.commit("chore: elsewhere", map[string]string{"other.md": "x\n"})
	unrelated := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.run("checkout", "-q", "main")
	repo.commit("feat: work\n\nWorkflow-Admission: T0\n", map[string]string{"src/app.py": "x = 1\n"})

	code, stdout, stderr := repo.exec(t, "admission", "--branch", "main", "--since", unrelated, "--offline")
	if code == cli.ExitOK {
		t.Fatalf("exit = 0 for a floor that is not on the branch\n%s", stdout)
	}
	if !strings.Contains(stderr, CodeFloorUnrelated) {
		t.Errorf("stderr does not name %s:\n%s", CodeFloorUnrelated, stderr)
	}
}

// F3: the floor silently shrinks the attested range, so the report states how much it
// excused rather than leaving a reader to compare counts against the branch by hand.
func TestAdmissionReportsHowManyCommitsTheFloorExcluded(t *testing.T) {
	repo := newGitRepo(t)
	repo.commit("chore: seed", map[string]string{"README.md": "seed\n"})
	repo.commit("chore: more", map[string]string{"README.md": "seed.\n"})
	floor := strings.TrimSpace(repo.run("rev-parse", "HEAD"))
	repo.commit("feat: work\n\nWorkflow-Admission: T0\n", map[string]string{"src/app.py": "x = 1\n"})

	code, stdout, stderr := repo.exec(t, "admission", "--branch", "main", "--since", floor, "--offline")
	if code != cli.ExitOK {
		t.Fatalf("exit = %d, want 0\nstdout:\n%s\nstderr:\n%s", code, stdout, stderr)
	}
	if !strings.Contains(stdout, "(exclusive; 2 commits excluded)") {
		t.Errorf("report does not state what the floor excluded:\n%s", stdout)
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
