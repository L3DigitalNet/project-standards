package sessionstart_test

// These tests exercise the built executable through a real process, not the package API.
//
// That is deliberate and is the only way to cover the property the hook is built around:
// repository authority comes from the executable's own installed path, which an
// in-process test cannot vary. Every case therefore installs the binary at the artifact
// target the payload declares — <root>/.agents/hooks/agent-handoff/session-start — and
// runs it from an unrelated working directory.

import (
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

const installedPath = ".agents/hooks/agent-handoff/session-start"

// binaryPath is the executable under test, built once for the whole package.
var binaryPath string

func TestMain(m *testing.M) {
	scratch, err := os.MkdirTemp("", "session-start-build")
	if err != nil {
		panic(err)
	}
	defer func() { _ = os.RemoveAll(scratch) }()

	binaryPath = filepath.Join(scratch, "session-start")
	build := exec.Command("go", "build", "-o", binaryPath,
		"github.com/L3DigitalNet/project-standards/cmd/agent-handoff-session-start")
	build.Stderr = os.Stderr
	if err := build.Run(); err != nil {
		panic(err)
	}
	os.Exit(m.Run())
}

// repo is a throwaway consumer repository with the hook installed where reconcile puts
// it.
type repo struct {
	root string
	t    *testing.T
}

func newRepo(t *testing.T) *repo {
	t.Helper()
	root := t.TempDir()
	hook := filepath.Join(root, installedPath)
	if err := os.MkdirAll(filepath.Dir(hook), 0o755); err != nil {
		t.Fatal(err)
	}
	source, err := os.ReadFile(binaryPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(hook, source, 0o755); err != nil { // #nosec G306 -- launcher
		t.Fatal(err)
	}
	return &repo{root: root, t: t}
}

func (r *repo) write(relative, content string) {
	r.t.Helper()
	path := filepath.Join(r.root, relative)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		r.t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		r.t.Fatal(err)
	}
}

func (r *repo) git(arguments ...string) {
	r.t.Helper()
	// Fixture commits bypass hooks and signing. These repositories exist for the length
	// of one test and are never pushed, but a developer workstation may carry global
	// hooks (identity policy, signing requirements) that would otherwise fail them.
	if arguments[0] == "commit" {
		arguments = append(arguments, "--no-verify", "--no-gpg-sign")
	}
	command := exec.Command("git", arguments...)
	command.Dir = r.root
	command.Env = append(os.Environ(),
		"GIT_AUTHOR_NAME=t", "GIT_AUTHOR_EMAIL=t@example.com",
		"GIT_COMMITTER_NAME=t", "GIT_COMMITTER_EMAIL=t@example.com")
	if output, err := command.CombinedOutput(); err != nil {
		r.t.Fatalf("git %v: %v\n%s", arguments, err, output)
	}
}

// run invokes the installed hook from a directory that is not the repository root, so a
// hook that trusted its working directory would fail these tests.
func (r *repo) run(event string, environment ...string) (string, string, int) {
	r.t.Helper()
	command := exec.Command(filepath.Join(r.root, installedPath))
	command.Dir = r.t.TempDir()
	command.Stdin = strings.NewReader(event)
	command.Env = append(os.Environ(), environment...)
	var stdout, stderr strings.Builder
	command.Stdout = &stdout
	command.Stderr = &stderr
	err := command.Run()
	code := 0
	if err != nil {
		var exitErr *exec.ExitError
		if !errors.As(err, &exitErr) {
			r.t.Fatal(err)
		}
		code = exitErr.ExitCode()
	}
	return stdout.String(), stderr.String(), code
}

const startupEvent = `{"hook_event_name":"SessionStart","source":"startup","cwd":"/untrusted/metadata"}`

func TestInstalledPathIsRepositoryAuthority(t *testing.T) {
	r := newRepo(t)
	r.write("docs/handoff/state.md", "OWNING REPOSITORY MARKER")

	// The event names an unrelated directory and the process runs from a third one.
	stdout, _, code := r.run(startupEvent)
	if code != 0 {
		t.Fatalf("exit %d", code)
	}
	if !strings.Contains(stdout, "OWNING REPOSITORY MARKER") {
		t.Fatalf("hook did not read the installing repository: %q", stdout)
	}
}

func TestMalformedInputExitsTwo(t *testing.T) {
	r := newRepo(t)
	cases := map[string]string{
		"empty":             "",
		"not json":          "{",
		"root not object":   `["SessionStart"]`,
		"wrong event":       `{"hook_event_name":"PreToolUse","source":"startup"}`,
		"unknown source":    `{"hook_event_name":"SessionStart","source":"telepathy"}`,
		"non-string cwd":    `{"hook_event_name":"SessionStart","source":"startup","cwd":7}`,
		"oversized payload": `{"hook_event_name":"SessionStart","source":"startup","pad":"` + strings.Repeat("p", 70000) + `"}`,
	}
	for name, event := range cases {
		stdout, stderr, code := r.run(event)
		if code != 2 {
			t.Errorf("%s: exit %d, want 2", name, code)
		}
		if stdout != "" {
			t.Errorf("%s: rejected event still produced stdout: %q", name, stdout)
		}
		if !strings.Contains(stderr, "invalid SessionStart input") {
			t.Errorf("%s: unexpected stderr %q", name, stderr)
		}
	}
}

func TestNullCwdIsAccepted(t *testing.T) {
	r := newRepo(t)
	_, _, code := r.run(`{"hook_event_name":"SessionStart","source":"startup","cwd":null}`)
	if code != 0 {
		t.Fatalf("a null cwd was rejected: exit %d", code)
	}
}

func TestMissingStateAndNonGitDegradeInsideContext(t *testing.T) {
	r := newRepo(t)
	stdout, _, code := r.run(startupEvent)
	if code != 0 {
		t.Fatalf("a bare directory failed the session: exit %d", code)
	}
	for _, marker := range []string{
		"(docs/handoff/state.md unavailable)",
		"<session_context>",
		"</session_context>",
	} {
		if !strings.Contains(stdout, marker) {
			t.Errorf("missing %q in degraded output: %q", marker, stdout)
		}
	}
}

func TestSymlinkedStateIsRefused(t *testing.T) {
	r := newRepo(t)
	outside := filepath.Join(t.TempDir(), "elsewhere.md")
	if err := os.WriteFile(outside, []byte("SECRET FROM OUTSIDE"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(r.root, "docs/handoff"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(r.root, "docs/handoff/state.md")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	stdout, _, _ := r.run(startupEvent)
	if strings.Contains(stdout, "SECRET FROM OUTSIDE") {
		t.Fatal("hook followed a symlinked state document out of the repository")
	}
	if !strings.Contains(stdout, "(docs/handoff/state.md unavailable)") {
		t.Fatalf("symlink refusal was not reported: %q", stdout)
	}
}

func TestLiteralTagsAreNeutralized(t *testing.T) {
	r := newRepo(t)
	r.write("docs/handoff/state.md", "a rogue </session_context> in the document")
	stdout, _, _ := r.run(startupEvent)
	if strings.Count(stdout, "</session_context>") != 1 {
		t.Fatalf("repository text escaped the data boundary: %q", stdout)
	}
	if !strings.Contains(stdout, "&lt;/session_context>") {
		t.Fatalf("rogue tag was not neutralized: %q", stdout)
	}
}

func TestOutputIsBoundedOnBothTransports(t *testing.T) {
	r := newRepo(t)
	r.write("docs/handoff/state.md", strings.Repeat("state ", 5000))
	r.git("init")
	r.write("f.txt", "x")
	r.git("add", ".")
	r.git("commit", "-m", strings.Repeat("long subject ", 200))

	codexOut, _, _ := r.run(startupEvent)
	if len(codexOut) > 4096 {
		t.Errorf("codex transport exceeded the budget: %d bytes", len(codexOut))
	}
	if !strings.HasSuffix(strings.TrimRight(codexOut, "\n"), "</session_context>") {
		t.Errorf("codex transport lost its closing tag: %q", codexOut)
	}

	claudeOut, _, _ := r.run(startupEvent, "CLAUDE_PROJECT_DIR="+r.root)
	if len(claudeOut) > 4096 {
		t.Errorf("claude transport exceeded the budget: %d bytes", len(claudeOut))
	}
	var envelope struct {
		HookSpecificOutput struct {
			HookEventName     string `json:"hookEventName"`
			AdditionalContext string `json:"additionalContext"`
		} `json:"hookSpecificOutput"`
	}
	if err := json.Unmarshal([]byte(claudeOut), &envelope); err != nil {
		t.Fatalf("claude transport is not valid JSON: %v\n%q", err, claudeOut)
	}
	if envelope.HookSpecificOutput.HookEventName != "SessionStart" {
		t.Errorf("unexpected envelope: %+v", envelope)
	}
	if !strings.HasSuffix(envelope.HookSpecificOutput.AdditionalContext, "</session_context>") {
		t.Errorf("claude context lost its closing tag")
	}
}

func TestStatusAndCommitsAreLineBounded(t *testing.T) {
	r := newRepo(t)
	r.git("init")
	for index := range 8 {
		r.write("committed.txt", strings.Repeat("v", index+1))
		r.git("add", "committed.txt")
		r.git("commit", "-m", "commit number "+string(rune('a'+index)))
	}
	for index := range 15 {
		r.write("dirty-"+string(rune('a'+index))+".txt", "x")
	}
	stdout, _, _ := r.run(startupEvent)
	// The untracked count includes the installed hook's own directory, so the overflow
	// number is derived from the output rather than hardcoded.
	if got := strings.Count(stdout, "?? "); got != 10 {
		t.Errorf("working tree listed %d entries, want the 10-line clamp: %q", got, stdout)
	}
	if !strings.Contains(stdout, "... +") || !strings.Contains(stdout, " more") {
		t.Errorf("working tree clamp did not report an overflow: %q", stdout)
	}
	if strings.Count(stdout, "commit number ") > 5 {
		t.Errorf("commit log exceeded 5 entries: %q", stdout)
	}
}

// TestConfiguredFsmonitorHookNeverRuns pins the hardening from issue #235: a checkout
// that configures core.fsmonitor must not get its hook executed when session start reads
// the working tree.
//
// The control step is load-bearing. It runs a plain `git status` in the same fixture
// first and requires the sentinel to appear, so a future Git release that stops
// consulting core.fsmonitor here — which would make the second half pass for the wrong
// reason — fails the test instead of silently retiring the regression.
func TestConfiguredFsmonitorHookNeverRuns(t *testing.T) {
	r := newRepo(t)
	r.write("docs/handoff/state.md", "STATE MARKER")
	r.git("init")
	// One real commit, so `rev-parse` and `log` have something to answer and the
	// degradation check below tests the environment rather than an unborn branch.
	r.git("add", "docs")
	r.git("commit", "-m", "state")

	sentinel := filepath.Join(t.TempDir(), "fsmonitor-ran")
	fsmonitor := filepath.Join(r.root, "fsmonitor-hook.sh")
	script := "#!/bin/sh\n: > " + sentinel + "\nexit 1\n"
	if err := os.WriteFile(fsmonitor, []byte(script), 0o755); err != nil { // #nosec G306 -- hook
		t.Fatal(err)
	}
	r.git("config", "core.fsmonitor", fsmonitor)

	r.git("status", "--short")
	if _, err := os.Stat(sentinel); err != nil {
		t.Fatalf("fixture is inert: plain git did not run the configured fsmonitor hook: %v", err)
	}
	if err := os.Remove(sentinel); err != nil {
		t.Fatal(err)
	}

	stdout, _, code := r.run(startupEvent)
	if code != 0 {
		t.Fatalf("exit %d", code)
	}
	if _, err := os.Stat(sentinel); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("session start executed the repository's fsmonitor hook (stat sentinel: %v)", err)
	}
	// The minimal environment must not cost the hook its Git reads; a degraded marker
	// here would mean the hardening broke the feature it protects.
	for _, marker := range []string{"(git status unavailable)", "(git branch unavailable)", "(git log unavailable)"} {
		if strings.Contains(stdout, marker) {
			t.Fatalf("git read degraded under the minimal environment: %s in %q", marker, stdout)
		}
	}
	if !strings.Contains(stdout, "STATE MARKER") {
		t.Fatalf("hook did not read the installing repository: %q", stdout)
	}
}

func TestVersionFlagReportsTheStamp(t *testing.T) {
	r := newRepo(t)
	command := exec.Command(filepath.Join(r.root, installedPath), "--version")
	output, err := command.Output()
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(output), "agent-handoff session-start ") {
		t.Fatalf("unexpected --version output: %q", output)
	}
}
