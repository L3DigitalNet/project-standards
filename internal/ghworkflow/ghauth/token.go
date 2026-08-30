// Package ghauth acquires a GitHub API token from the operator's existing `gh` CLI
// authentication.
//
// Spec IR-002 is the whole contract here: the tool never embeds, stores, or requests
// credentials. It shells out to `gh auth token` and holds the result in memory for the
// life of one command. There is no configuration file, no environment fallback, and no
// prompt — an unauthenticated operator gets a precondition failure, never an interactive
// detour (IR-004 requires non-interactive operation).
package ghauth

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
)

// ErrUnauthenticated marks every failure to obtain a token, so callers can classify the
// condition as a precondition failure without inspecting the message.
var ErrUnauthenticated error = &unauthenticatedError{}

// unauthenticatedError carries the operational marker package cli classifies as exit 3.
//
// The marker is a structural interface — `interface{ Operational() bool }` — rather than a
// shared type, because this package cannot import cli (cli imports the packages that build
// on this one) and cli cannot import a marker package without the same cycle. Package
// ghapi carries the identical four lines in its operational.go for the same reason; the two
// are ends of one contract, so a change to either needs the other checked in the same edit.
type unauthenticatedError struct{}

func (e *unauthenticatedError) Error() string { return "gh is not authenticated" }

// Operational reports that no token means the tool could not run at all, which is an
// operational failure rather than anything the operator mistyped.
func (e *unauthenticatedError) Operational() bool { return true }

// TokenSource yields a GitHub API token. It is an interface so every test can supply a
// token without depending on the operator's `gh` state or reaching the network.
type TokenSource interface {
	Token(ctx context.Context) (string, error)
}

// CLITokenSource obtains the token by running `gh auth token`.
type CLITokenSource struct {
	// run executes the command and returns its stdout and stderr separately. Tests
	// replace it; production leaves it nil and uses the real `gh` binary.
	run func(ctx context.Context) (stdout, stderr string, err error)
}

// NewCLITokenSource returns a TokenSource backed by the operator's `gh` CLI.
func NewCLITokenSource() *CLITokenSource {
	return &CLITokenSource{}
}

// Token returns the operator's GitHub token.
func (s *CLITokenSource) Token(ctx context.Context) (string, error) {
	run := s.run
	if run == nil {
		run = runGHAuthToken
	}

	stdout, stderr, err := run(ctx)
	if err != nil {
		// Only stderr is quoted. `gh auth token` writes the token itself to stdout, so
		// echoing stdout into a diagnostic would leak the credential into logs and
		// session transcripts — the exact disclosure IR-002 forbids.
		return "", fmt.Errorf("%w: `gh auth token` failed: %s", ErrUnauthenticated, firstLine(stderr))
	}
	token := strings.TrimSpace(stdout)
	if token == "" {
		return "", fmt.Errorf("%w: `gh auth token` returned no token", ErrUnauthenticated)
	}
	return token, nil
}

func runGHAuthToken(ctx context.Context) (string, string, error) {
	var stdout, stderr bytes.Buffer
	cmd := exec.CommandContext(ctx, "gh", "auth", "token")
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	return stdout.String(), stderr.String(), err
}

func firstLine(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return "no diagnostic output; run `gh auth login`"
	}
	if line, _, found := strings.Cut(s, "\n"); found {
		return line
	}
	return s
}
