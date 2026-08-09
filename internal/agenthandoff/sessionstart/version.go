package sessionstart

// DefaultVersion labels a build that was not stamped by the canonical build script.
//
// It is intentionally not a plausible package version: an unstamped binary must be
// obviously unstamped when `--version` is used to diagnose a stale installation.
const DefaultVersion = "unstamped"

// Version is the Agent Handoff payload version that produced this binary.
//
// The canonical build script overwrites it at link time. It is pinned to the payload
// version rather than a VCS describe string so the committed bytes change only when the
// package version does — a per-commit stamp would break the reproducible-build gate on
// every unrelated commit.
var Version = DefaultVersion
