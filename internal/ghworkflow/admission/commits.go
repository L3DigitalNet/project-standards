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
	"strconv"
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
// terminated by bodySeparator, after which `--name-status` appends the touched paths.
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
	// The diff options are load-bearing for correctness, not for formatting:
	//
	//   --name-status with --no-renames reports BOTH sides of a rename, as a delete of
	//   the old path and an add of the new one. `--name-only` reports a rename as its
	//   destination alone, which admitted a forgery: `git mv <anything> docs/handoff/`
	//   in a commit declaring `Workflow-Admission: handoff` showed only a handoff path,
	//   so an arbitrary file could be moved out of governance under the exemption.
	//
	//   -z makes git emit every token NUL-terminated and, critically, unquoted. Without
	//   it git C-quotes any path containing a non-ASCII or control byte, so a handoff
	//   path would arrive as `"docs/handoff/\303\251.md"` and fail the prefix test.
	//
	//   The trailing `--` terminates revisions: a branch or floor whose name also names
	//   an existing file would otherwise be taken as a pathspec, silently filtering the
	//   history down to that file's commits (or to none) while still exiting 0.
	//
	// #nosec G204 -- the argv is fixed and git is executed directly with no shell; the
	// only variable element is the revision range, contained by --end-of-options above
	// and by the pathspec terminator below.
	cmd := exec.CommandContext(ctx, "git", "log",
		"--format="+logFormat, "-z", "--name-status", "--no-renames",
		"--end-of-options", rng.spec(), "--")
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

// ExcludedByFloor returns how many commits the floor keeps out of the range, after
// proving the floor is genuinely part of the branch's history.
//
// The ancestry check is the load-bearing half. `admission_floor` is the one option that
// silently shrinks what the classifier attests, and a floor on an unrelated branch (a
// stale SHA, a fork's tip, a typo that still resolves) produces a range that is not the
// prefix of history anyone intended — in the worst case an empty one that would read as
// compliance. Refusing an unrelated floor keeps "since the floor" meaning "everything
// after this point on this branch".
//
// The count is reported so a reader can see the size of what was excused. A floor that
// excludes 900 of 1000 commits is a legitimate adoption boundary, but it must be
// visible in the report rather than inferred from a number the report never printed.
func ExcludedByFloor(ctx context.Context, workDir string, rng Range) (int, error) {
	if rng.Since == "" {
		return 0, nil
	}
	// #nosec G204 -- fixed argv; the floor and the branch are contained by
	// --end-of-options and the pathspec terminator, as in ReadCommits above.
	ancestry := exec.CommandContext(ctx, "git", "merge-base", "--is-ancestor",
		"--end-of-options", rng.Since, rng.Branch)
	ancestry.Dir = workDir
	if err := ancestry.Run(); err != nil {
		return 0, fmt.Errorf("%s: %s is not an ancestor of %s, so it cannot be that branch's "+
			"enforcement floor", CodeFloorUnrelated, rng.Since, rng.Branch)
	}
	// #nosec G204 -- see above.
	count := exec.CommandContext(ctx, "git", "rev-list", "--count",
		"--end-of-options", rng.Since, "--")
	count.Dir = workDir
	var stderr strings.Builder
	count.Stderr = &stderr
	out, err := count.Output()
	if err != nil {
		detail := strings.TrimSpace(stderr.String())
		if detail == "" {
			detail = err.Error()
		}
		return 0, fmt.Errorf("counting the commits excluded by %s: %s", rng.Since, detail)
	}
	excluded, err := strconv.Atoi(strings.TrimSpace(string(out)))
	if err != nil {
		return 0, fmt.Errorf("counting the commits excluded by %s: %w", rng.Since, err)
	}
	return excluded, nil
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
		paths, pathErr := splitPaths(tail)
		if pathErr != nil {
			return nil, fmt.Errorf("commit %s: %w", fields[0], pathErr)
		}
		commits = append(commits, Commit{
			SHA:     fields[0],
			Subject: fields[1],
			Body:    body,
			Paths:   paths,
			IsMerge: len(strings.Fields(fields[2])) > 1,
		})
	}
	return commits, nil
}

// splitPaths reads the `--name-status -z` block that follows one commit's message.
//
// The block is a flat NUL-terminated token stream that alternates status letter and
// path: "M\x00a.md\x00D\x00b.md\x00". Rename and copy entries are the only ones that
// would emit two paths for one status, and --no-renames disables both, so the
// alternation is exact — which is what lets every odd token be taken as a path
// regardless of its status letter. An odd token count means git emitted something this
// contract does not describe, and is reported rather than silently half-parsed.
//
// Two prefix bytes precede the block: the NUL that -z uses to terminate the commit
// header, and the newline git writes between a commit and its diff (absent when there
// is no diff at all, as for a merge). Bytes are compared exactly from there on — no
// trimming — because trimming would turn a path like " docs/handoff/x.md", whose
// leading space is part of the filename, into an exempt handoff path.
func splitPaths(tail string) ([]string, error) {
	tail = strings.TrimPrefix(tail, "\x00")
	tail = strings.TrimPrefix(tail, "\n")
	if tail == "" {
		return nil, nil
	}
	tokens := strings.Split(tail, "\x00")
	if last := len(tokens) - 1; tokens[last] == "" {
		tokens = tokens[:last]
	}
	if len(tokens)%2 != 0 {
		return nil, fmt.Errorf("malformed name-status block %q", truncate(tail))
	}
	paths := make([]string, 0, len(tokens)/2)
	for i := 1; i < len(tokens); i += 2 {
		paths = append(paths, tokens[i])
	}
	return paths, nil
}

func truncate(value string) string {
	const limit = 60
	if len(value) <= limit {
		return value
	}
	return value[:limit] + "…"
}
