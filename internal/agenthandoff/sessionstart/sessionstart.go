// Package sessionstart implements the Agent Handoff SessionStart hook as a native
// executable.
//
// It replaces the Python hook shipped through Agent Handoff 1.9. The protocol is
// unchanged — a JSON event on stdin, a bounded context block on stdout, diagnostics on
// stderr, and the same exit codes — but the launcher no longer resolves an interpreter
// at run time. That resolution was the entire failure class this package exists to
// remove: a consumer whose first `python3` on PATH is a policy shim (as `uv-strict-python`
// deploys) saw the hook exit non-zero before running any of its own code, and no managed
// registration could work around it without creating drift (issue #138).
//
// Exit codes are part of the contract:
//
//	0  context emitted, or emitted in degraded form after a recoverable failure
//	2  the event on stdin is not a SessionStart event this payload registered for
//
// There is deliberately no failing exit path for repository problems. A missing state
// document, an absent Git, or a broken checkout all degrade to a marker inside the
// context block, because a hook that fails the session start is strictly worse for the
// operator than one that reports thin context.
package sessionstart

import (
	"fmt"
	"io"
	"os"
)

// Env is the process environment the hook depends on, injected so tests exercise the
// real entry point rather than a reimplementation of it.
type Env struct {
	Stdin  io.Reader
	Stdout io.Writer
	Stderr io.Writer
	// LookupEnv resolves harness environment variables. It selects the output transport
	// and nothing else; it never selects a filesystem root.
	LookupEnv func(string) (string, bool)
}

// DefaultEnv binds Env to the real process.
func DefaultEnv() Env {
	return Env{
		Stdin:     os.Stdin,
		Stdout:    os.Stdout,
		Stderr:    os.Stderr,
		LookupEnv: os.LookupEnv,
	}
}

// detectHarness picks the transport from the harness's own marker variable.
//
// Codex is the default rather than an error case: it sets no distinguishing variable,
// and emitting the bare block to an unknown harness degrades more gracefully than
// emitting a Claude envelope it cannot parse.
func detectHarness(lookupEnv func(string) (string, bool)) string {
	if _, ok := lookupEnv("CLAUDE_PROJECT_DIR"); ok {
		return harnessClaude
	}
	return harnessCodex
}

// Run executes the hook and returns its process exit code.
func Run(env Env, arguments []string) int {
	// `--version` exists for stale-binary detection: the payload ships committed bytes,
	// so an operator needs a way to ask an installed launcher which package version
	// produced it without reading the digest out of the lock.
	if len(arguments) == 1 && arguments[0] == "--version" {
		_, _ = fmt.Fprintf(env.Stdout, "agent-handoff session-start %s\n", Version)
		return 0
	}
	if len(arguments) > 0 {
		_, _ = fmt.Fprintln(env.Stderr, "agent-handoff: unexpected arguments")
		return 2
	}

	if err := parseEvent(env.Stdin); err != nil {
		_, _ = fmt.Fprintf(env.Stderr, "agent-handoff: %s\n", err)
		return 2
	}
	emit(env.Stdout, buildContext(), detectHarness(env.LookupEnv))
	return 0
}
