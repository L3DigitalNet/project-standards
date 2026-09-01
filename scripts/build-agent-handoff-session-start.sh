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
ARTIFACT_OUTPUT_PATH="standards/agent-handoff/versions/1.17/hooks/session-start/session-start"
ARTIFACT_PACKAGE="./cmd/agent-handoff-session-start"

# The version stamp is pinned to the payload version rather than a VCS describe string; a
# build-time stamp that varied per commit would make the committed bytes change on every
# unrelated commit and destroy the reproducibility guarantee. Consumers read it back with
# `session-start --version` to detect a stale installed launcher.
#
# Both values name the payload version under development, never a released one: a
# published payload's bytes are immutable, so this script advances to the newest
# unpublished cut and stops being able to reproduce its predecessors. That is intended —
# released copies are verified by the release baseline comparison, not here. Pointing it
# back at a published version would make `--build` overwrite frozen bytes, which
# `packages check-release` classifies as a forbidden mutation.
#
# Cut-time rule (issue #229): every new payload version re-links the binary with its own
# version stamp, even when the Go source is unchanged, and both values above move
# together in the cutting commit. Byte-copying the predecessor's binary instead — as
# 1.15 and 1.16 did — leaves `--version` answering the version that was last *built*,
# which defeats the stale-launcher diagnostic it exists for. So the bytes of two
# consecutive versions may differ by the stamp alone; that is the intended outcome, not
# an unnecessary rebuild.
#
# `-s -w` strips the symbol table and DWARF (issue #228). `.gopclntab` is untouched, so
# panic traces still carry function names and line numbers; what is lost is `delve` and
# DWARF-based inspection of the shipped binary, which is recovered by rebuilding from
# this script without the flags. Published payload bytes stay unstripped — only versions
# cut from agent-handoff 1.17 onward are stripped, so a size step between neighbouring
# retained versions is expected and is not drift.
ARTIFACT_LDFLAGS="-buildid= -s -w -X main.version=1.17"

# shellcheck source=scripts/lib/go-reproducible-build.sh
source "$REPO_ROOT/scripts/lib/go-reproducible-build.sh"

go_artifact_main "$@"
