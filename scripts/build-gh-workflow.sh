#!/usr/bin/env bash
# Canonical reproducible build for the committed `gh-workflow` binary (spec FR-015,
# NFR-005; plan decision D-004).
#
# The binary ships to consumers as committed bytes inside the github-workflow payload,
# so those bytes are the only thing a consumer can audit. This script is the single
# definition of how they are produced, and `make go-verify-binary` re-runs it to prove
# the committed bytes still match the Go source in the same commit.
#
# Usage:
#   scripts/build-gh-workflow.sh              # rebuild the committed binary in place
#   scripts/build-gh-workflow.sh --verify     # rebuild to a temp dir and byte-compare
#
# Requirements: bash, GNU coreutils (`cmp`, `mktemp`, `sha256sum`), and the Go toolchain
# pinned by the `toolchain` line in go.mod. No network access is needed once the module
# cache is warm; the tool's own package tree is stdlib-only.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# The committed artifact path is a cross-file contract: payload.toml declares this same
# path as the `tool-binary` artifact source, and the Makefile reaches the file only
# through this script. Moving it means editing all three together.
readonly OUTPUT_PATH="standards/github-workflow/versions/1.0/skills/github-workflow/bin/gh-workflow"
readonly PACKAGE="./cmd/gh-workflow"

# NFR-005 pins the tool version stamp to the payload version rather than to a VCS
# describe string; a build-time stamp that varied per commit would make the committed
# bytes change on every unrelated commit and destroy the reproducibility guarantee.
readonly LDFLAGS="-buildid= -X main.version=1.0"

# Derived from go.mod so the pin has exactly one source of truth. A newer local toolchain
# satisfies go.mod's minimum and would otherwise build silently — producing valid but
# byte-different output that surfaces only as an unexplained `--verify` failure.
TOOLCHAIN="$(awk '$1 == "toolchain" { print $2 }' go.mod)"
if [[ -z "$TOOLCHAIN" ]]; then
    echo "error: go.mod has no 'toolchain' line; cannot pin the build toolchain." >&2
    exit 1
fi

# GOEXPERIMENT must be pinned explicitly, not left to the environment.
#
# The go command records the *raw* GOEXPERIMENT value in the binary's build info and
# resolves it from $GOROOT/go.env when the variable is unset. Distributions set it there:
# Fedora's go.env carries GOEXPERIMENT=nodwarf5, which changes the emitted DWARF and
# produced a binary 253 KiB smaller than an upstream-default build of the same source.
# An unpinned build is therefore reproducible only among identically packaged toolchains,
# which would make this repository's own gate fail on GitHub-hosted CI.
#
# `dwarf5` is the upstream baseline, so pinning it changes no code generation — a binary
# built this way reports a plain `go1.26.5` toolchain version, not the `-X:nodwarf5`
# variant. Verified: the upstream and Fedora toolchains produce byte-identical output
# under this pin. Setting the variable to the empty string does NOT work, because the go
# command falls back to go.env whenever the environment value is empty.
#
# When a future toolchain retires the experiment, this fails loudly at build time rather
# than silently producing different bytes; drop the pin in the same change that moves the
# toolchain and rebuild the committed binary.
readonly GOEXPERIMENT_PIN="dwarf5"

actual_toolchain="$(go version | awk '{ print $3 }')"
if [[ "$actual_toolchain" != "$TOOLCHAIN" && "$actual_toolchain" != "$TOOLCHAIN"-* ]]; then
    echo "error: toolchain mismatch: go.mod pins $TOOLCHAIN but 'go version' reports $actual_toolchain." >&2
    echo "       Install the pinned toolchain or set GOTOOLCHAIN=$TOOLCHAIN." >&2
    exit 1
fi

# GOFLAGS is prepended to every go invocation and can add build tags or change the module
# mode, silently altering the output of the fixed command below.
goflags="$(go env GOFLAGS)"
if [[ -n "$goflags" ]]; then
    echo "error: GOFLAGS is set to '$goflags'; it would perturb the pinned build." >&2
    echo "       Clear it (go env -u GOFLAGS, or unset the variable) and retry." >&2
    exit 1
fi

# The complete build invocation fixed by NFR-005. Callers pass the destination only; every
# other operand is part of the pinned contract and must not become configurable.
build_to() {
    local destination="$1"
    GOEXPERIMENT="$GOEXPERIMENT_PIN" \
        GOOS=linux GOARCH=amd64 GOAMD64=v1 CGO_ENABLED=0 \
        go build -trimpath -buildvcs=false -ldflags "$LDFLAGS" -o "$destination" "$PACKAGE"
}

case "${1:---build}" in
--build)
    mkdir -p "$(dirname "$OUTPUT_PATH")"
    build_to "$OUTPUT_PATH"
    # Explicit rather than umask-dependent: the payload declares mode 0755 and reconcile
    # delivers the committed mode, so a 0644 build here would ship a non-executable tool.
    chmod 0755 "$OUTPUT_PATH"
    echo "built $OUTPUT_PATH ($(sha256sum "$OUTPUT_PATH" | cut -d' ' -f1))"
    ;;
--verify)
    if [[ ! -f "$OUTPUT_PATH" ]]; then
        echo "error: committed binary is missing at $OUTPUT_PATH." >&2
        echo "       Run scripts/build-gh-workflow.sh and commit the result." >&2
        exit 1
    fi

    scratch="$(mktemp -d)"
    trap 'rm -rf "$scratch"' EXIT
    build_to "$scratch/gh-workflow"

    if ! cmp -s "$scratch/gh-workflow" "$OUTPUT_PATH"; then
        echo "error: committed binary does not match a rebuild from this commit's source." >&2
        echo "       committed: $(sha256sum "$OUTPUT_PATH" | cut -d' ' -f1)" >&2
        echo "       rebuilt:   $(sha256sum "$scratch/gh-workflow" | cut -d' ' -f1)" >&2
        echo "       Run scripts/build-gh-workflow.sh and commit the result." >&2
        exit 1
    fi
    echo "verified $OUTPUT_PATH matches a rebuild ($(sha256sum "$OUTPUT_PATH" | cut -d' ' -f1))"
    ;;
*)
    echo "usage: ${BASH_SOURCE[0]} [--build | --verify]" >&2
    exit 2
    ;;
esac
