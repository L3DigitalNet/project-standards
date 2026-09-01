package admission

// Reading commits for the classifier. This is the only file in the package that runs a
// subprocess, so the rules in classify.go stay testable without a repository.
//
// The module takes no new dependency for this (`go mod tidy -diff` is a gate), so the
// history is read by shelling out to `git` with a fixed argument vector rather than by
// linking a git implementation. Every user-supplied value — the branch, the floor —
// reaches git as one argv element after `--end-of-options`, never through a shell.

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
)

// The record and field separators the log format below interleaves with the commit
// data. They are ASCII control characters because a commit subject or body may
// legitimately contain any printable character, including every quoting character a
// friendlier delimiter would use; \x01, \x02, and \x03 cannot appear in a git commit
// message, which git stores as text with control characters stripped at commit time.
const (
	recordSeparator = "\x01"
	fieldSeparator  = "\x02"
	bodySeparator   = "\x03"
)

// logFormat asks for one record per commit: SHA, subject, parents, then the full body
// terminated by bodySeparator, after which `--name-only` appends the touched paths.
//
// One invocation covers the whole range on purpose. The measured corpus here is 360+
// commits, and a per-commit `git show` would spawn two processes per commit — slow
// enough that the contract test running this over the repository's own history would
// become a lane nobody wants to run.
const logFormat = recordSeparator + "%H" + fieldSeparator + "%s" + fieldSeparator + "%P" +
	fieldSeparator + "%B" + bodySeparator

// Range is the commit range to classify. Since is the `admission_floor` or an explicit
// `--since`; empty means the branch's whole history.
type Range struct {
	Branch string
	Since  string
}

// spec renders the range as git's two-dot syntax. A floor is exclusive — it names the
// last commit the repository does *not* hold to the rule, so enforcement begins with
// its children rather than with the floor commit itself.
func (r Range) spec() string {
	if r.Since == "" {
		return r.Branch
	}
	return r.Since + ".." + r.Branch
}

// ReadCommits returns every commit in the range, newest first.
//
// A nonzero git exit is returned as an error rather than as an empty result: an unknown
// branch or an unknown floor must fail the run, because reporting "0 commits, all
// admitted" for a range that does not exist is the one failure mode a compliance check
// cannot have.
func ReadCommits(ctx context.Context, workDir string, rng Range) ([]Commit, error) {
	// `--end-of-options` is load-bearing, not decoration: the branch and the floor come
	// from an operator flag or the rendered policy, and without it a value beginning
	// with `-` would be parsed by git as an option rather than as a revision. With it,
	// the worst a hostile value can do is name a revision that does not resolve, which
	// this function already reports as an error.
	//
	// #nosec G204 -- the argv is fixed and git is executed directly with no shell; the
	// only variable element is the revision range, contained by --end-of-options above.
	cmd := exec.CommandContext(ctx, "git", "log",
		"--format="+logFormat, "--name-only", "--end-of-options", rng.spec())
	cmd.Dir = workDir
	var stderr strings.Builder
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		detail := strings.TrimSpace(stderr.String())
		if detail == "" {
			detail = err.Error()
		}
		return nil, fmt.Errorf("reading commits for %s: %s", rng.spec(), detail)
	}
	return parseLog(string(out))
}

// parseLog turns the log stream into commits. It is exported to the package's tests
// through a literal stream rather than a repository, which is what lets the record
// framing be tested against subjects and bodies containing newlines and pipes.
func parseLog(stream string) ([]Commit, error) {
	commits := make([]Commit, 0, 64)
	for _, record := range strings.Split(stream, recordSeparator) {
		if strings.TrimSpace(record) == "" {
			continue
		}
		fields := strings.SplitN(record, fieldSeparator, 4)
		if len(fields) != 4 {
			return nil, fmt.Errorf("malformed commit record %q", truncate(record))
		}
		body, tail, ok := strings.Cut(fields[3], bodySeparator)
		if !ok {
			return nil, fmt.Errorf("commit %s: no body terminator in the log stream", fields[0])
		}
		commits = append(commits, Commit{
			SHA:     fields[0],
			Subject: fields[1],
			Body:    body,
			Paths:   splitPaths(tail),
			IsMerge: len(strings.Fields(fields[2])) > 1,
		})
	}
	return commits, nil
}

func splitPaths(tail string) []string {
	paths := make([]string, 0, 8)
	for _, line := range strings.Split(tail, "\n") {
		if trimmed := strings.TrimSpace(line); trimmed != "" {
			paths = append(paths, trimmed)
		}
	}
	return paths
}

func truncate(value string) string {
	const limit = 60
	if len(value) <= limit {
		return value
	}
	return value[:limit] + "…"
}
