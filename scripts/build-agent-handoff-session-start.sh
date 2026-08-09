#!/usr/bin/env bash
# Canonical reproducible build for the committed Agent Handoff SessionStart launcher.
#
# Agent Handoff 1.10 replaced the Python hook with this native executable so the launcher
# starts independently of the consumer's Python policy and PATH composition (issue #138).
# The binary ships to consumers as committed bytes inside the payload, so those bytes are
# the only thing a consumer can audit. This script is the single definition of how they
# are produced, and `make go-verify-binary` re-runs it to prove the committed bytes still
# match the Go source in the same commit.
#
# The pinned build environment and the rebuild-compare live in the shared library so
# every committed Go artifact is produced identically; this file declares only what is
# built and where it lands.
#
# Usage:
#   scripts/build-agent-handoff-session-start.sh            # rebuild in place
#   scripts/build-agent-handoff-session-start.sh --verify   # rebuild and byte-compare

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_SCRIPT_NAME="scripts/build-agent-handoff-session-start.sh"

# The committed artifact path is a cross-file contract with three other places:
# payload.toml declares it as the `hook` artifact source, the artifact *target*
# `.agents/hooks/agent-handoff/session-start` fixes the installed depth that
# sessionstart.repositoryRoot walks up, and the Makefile reaches the file only through
# this script. Moving it means editing all of them together.
ARTIFACT_OUTPUT_PATH="standards/agent-handoff/versions/1.10/hooks/session-start/session-start"
ARTIFACT_PACKAGE="./cmd/agent-handoff-session-start"

# The version stamp is pinned to the payload version rather than a VCS describe string; a
# build-time stamp that varied per commit would make the committed bytes change on every
# unrelated commit and destroy the reproducibility guarantee. Consumers read it back with
# `session-start --version` to detect a stale installed launcher.
ARTIFACT_LDFLAGS="-buildid= -X main.version=1.10"

# shellcheck source=scripts/lib/go-reproducible-build.sh
source "$REPO_ROOT/scripts/lib/go-reproducible-build.sh"

go_artifact_main "$@"
