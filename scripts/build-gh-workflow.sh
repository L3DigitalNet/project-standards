#!/usr/bin/env bash
# Canonical reproducible build for the committed `gh-workflow` binary (spec FR-015,
# NFR-005; plan decision D-004).
#
# The binary ships to consumers as committed bytes inside the github-workflow payload,
# so those bytes are the only thing a consumer can audit. This script is the single
# definition of how they are produced, and `make go-verify-binary` re-runs it to prove
# the committed bytes still match the Go source in the same commit.
#
# The pinned build environment and the rebuild-compare live in the shared library so
# every committed Go artifact is produced identically; this file declares only what is
# built and where it lands.
#
# Usage:
#   scripts/build-gh-workflow.sh              # rebuild the committed binary in place
#   scripts/build-gh-workflow.sh --verify     # rebuild to a temp dir and byte-compare

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_SCRIPT_NAME="scripts/build-gh-workflow.sh"

# The committed artifact path is a cross-file contract: payload.toml declares this same
# path as the `tool-binary` artifact source, and the Makefile reaches the file only
# through this script. Moving it means editing all three together.
ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.10/skills/github-workflow/bin/gh-workflow"
ARTIFACT_PACKAGE="./cmd/gh-workflow"

# NFR-005 pins the tool version stamp to the payload version rather than to a VCS
# describe string; a build-time stamp that varied per commit would make the committed
# bytes change on every unrelated commit and destroy the reproducibility guarantee.
#
# Both values name the payload version under development, never a released one: a
# published payload's bytes are immutable, so this script targets the successor from the
# moment it is cut and stops being able to reproduce its predecessor. That is intended —
# the predecessor's bytes are verified by the release baseline comparison, not here.
# `-s -w` drop the symbol table and DWARF debug information, which cost roughly a third of
# the committed bytes and buy a consumer nothing: the binary ships as an audited artifact,
# not as something anyone debugs with a symbol table. Go's own panic traces still carry
# function names and line numbers — those come from the runtime's pclntab, which neither
# flag strips — so a crash report is as legible as it was unstripped.
#
# Published payload bytes are immutable, so this applies from 1.10 forward only; 1.9 and
# earlier stay unstripped and are never rebuilt.
ARTIFACT_LDFLAGS="-s -w -buildid= -X main.version=1.10"

# shellcheck source=scripts/lib/go-reproducible-build.sh
source "$REPO_ROOT/scripts/lib/go-reproducible-build.sh"

go_artifact_main "$@"
