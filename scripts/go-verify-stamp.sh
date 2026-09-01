#!/usr/bin/env bash
# Content key for the committed-Go-artifact reproducibility proof (#227 E3 item 8).
#
# `make go-verify-binary` rebuilds all three committed Go artifacts into scratch and
# byte-compares them, which costs three cold `go build` invocations. It ran on every
# `make go-check`, including the overwhelming majority of gate runs that touch no Go
# source and no committed binary. This script is the single authority for the key that
# decides whether that proof still holds, so the Makefile branch that skips the proof
# and the stamp written after it passes can never disagree about what "unchanged" means.
#
# Key inputs — everything the proof's outcome depends on:
#   internal/**, cmd/**   the Go source the artifacts are built from
#   go.mod, go.sum        the module graph and the pinned toolchain
#   scripts/build-*.sh    what is built, where it lands, and the version stamp
#   scripts/lib/go-*.sh   the pinned build environment and the compare itself
#   the committed artifacts declared by those build scripts
#
# The artifact bytes are load-bearing and not an optimization: without them, replacing a
# committed binary with unrelated bytes while leaving the source untouched would leave a
# matching stamp behind and the gate would skip the one check that catches it. The
# artifact paths are read out of the build scripts rather than restated here so this file
# cannot drift from the scripts that own them.
#
# Content, not mtime, matching scripts/wheel-runtime-stamp.sh: a metadata key would call
# the proof stale after any `git checkout` round-trip that restored identical bytes.
#
# Fail-closed everywhere: any error while enumerating or hashing yields exit 2
# (indeterminate) and never a key, and the Makefile treats anything other than a clean
# `check` as "run the proof". A missing stamp is stale, which is what makes a fresh
# checkout (CI, a new worktree, a `rexec clean`ed workspace) verify rather than trust.
#
# KNOWN GAP under rexec, which is how this repository's gates actually run: the stamp is
# written in the worker workspace and no `build/` exists in the local checkout, so the next
# synchronization removes it and every remote `make go-check` re-runs the proof. Naming the
# stamp in `.rexec.toml` [sync].exclude does NOT fix this and was tried and reverted on
# 2026-09-01: a `[sync].exclude` entry only stops a path being uploaded, it does not protect
# worker-only content from removal. Measured — the long-standing `build/dist` exclude does
# not survive either: a file created there on the worker is gone by the next invocation.
# `.venv` and `node_modules` survive because they are rexec's own built-in excludes, which
# configuration cannot extend. A real fix belongs in rexec or in a stamp location outside
# the mirrored tree; until then the saving lands for local and CI runs only, and the failure
# direction is safe, because an absent stamp verifies.
#
# Requirements: bash, GNU coreutils (`sha256sum`, `sort -z`), findutils, sed.
#
# Usage:
#   scripts/go-verify-stamp.sh compute   print the key
#   scripts/go-verify-stamp.sh write     write build/go-verify.stamp
#   scripts/go-verify-stamp.sh check     0 current, 1 stale/missing, 2 error

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Beside build/wheel-runtime.stamp and gitignored with the rest of build/: the stamp
# records a fact about this working tree, not about the commit, so committing it would
# assert the proof passed on every checkout of that commit.
STAMP_FILE="$REPO_ROOT/build/go-verify.stamp"
STAMP_SCHEMA=1

die() {
    printf 'go-verify-stamp: %s\n' "$1" >&2
    exit "${2:-2}"
}

# Prints the committed artifact paths declared by the build scripts, one per line.
#
# Cross-file contract: each `scripts/build-*.sh` that ships a committed binary declares
# exactly one `ARTIFACT_OUTPUT_PATH="..."` line, which the shared library in
# scripts/lib/go-reproducible-build.sh consumes. A build script that stops matching this
# form drops silently out of the key, so every declared path is required to exist and the
# whole key is refused when the set comes back empty.
declared_artifacts() {
    local paths
    paths="$(cd "$REPO_ROOT" && sed -n 's/^ARTIFACT_OUTPUT_PATH="\([^"]*\)"$/\1/p' scripts/build-*.sh)" || return 1
    [[ -n "$paths" ]] || return 1
    local path
    while IFS= read -r path; do
        # A path containing whitespace would break the NUL-list assembly below, and no
        # committed artifact has ever needed one.
        case "$path" in
            *[[:space:]]*) return 1 ;;
        esac
        [[ -f "$REPO_ROOT/$path" ]] || return 1
    done <<<"$paths"
    printf '%s\n' "$paths"
}

compute_key() {
    local artifacts
    artifacts="$(declared_artifacts)" || return 1

    local required
    for required in internal cmd go.mod go.sum scripts/lib; do
        [[ -e "$REPO_ROOT/$required" ]] || return 1
    done

    local digest
    digest="$(
        cd "$REPO_ROOT" &&
            {
                find internal cmd -type f -print0 &&
                    find scripts -maxdepth 1 -name 'build-*.sh' -type f -print0 &&
                    find scripts/lib -maxdepth 1 -name 'go-*.sh' -type f -print0 &&
                    printf '%s\0' go.mod go.sum &&
                    while IFS= read -r artifact; do printf '%s\0' "$artifact"; done <<<"$artifacts"
            } |
            LC_ALL=C sort -zu |
            xargs -0 -r sha256sum |
            sha256sum
    )" || return 1
    printf '%s\n' "${digest%% *}"
}

read_stamped_key() {
    [[ -f "$STAMP_FILE" ]] || return 1
    local line
    while IFS= read -r line; do
        case "$line" in
            key=*)
                printf '%s\n' "${line#key=}"
                return 0
                ;;
        esac
    done <"$STAMP_FILE"
    return 1
}

COMMAND="${1:-}"
[[ $# -le 1 ]] || die "expected at most one argument" 2

case "$COMMAND" in
    compute)
        key="$(compute_key)" || die "cannot compute the content key (missing Go source, build script, or committed artifact)"
        printf '%s\n' "$key"
        ;;
    write)
        # Written only by the Makefile immediately after `go-verify-binary` succeeds: the
        # stamp asserts "the reproducibility proof passed at this key", so writing it
        # without having run the proof would license skipping it forever.
        key="$(compute_key)" || die "cannot compute the content key (missing Go source, build script, or committed artifact)"
        mkdir -p "$(dirname "$STAMP_FILE")" || die "cannot create $(dirname "$STAMP_FILE")"
        {
            printf '# project-standards go-verify-binary proof stamp\n'
            printf 'schema=%s\n' "$STAMP_SCHEMA"
            printf 'key=%s\n' "$key"
            printf 'stamped=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        } >"$STAMP_FILE" || die "cannot write $STAMP_FILE"
        printf 'go-verify-stamp: wrote %s (key %s)\n' "${STAMP_FILE#"$REPO_ROOT/"}" "${key:0:12}"
        ;;
    check)
        key="$(compute_key)" || die "cannot compute the content key (missing Go source, build script, or committed artifact)"
        if ! stamped="$(read_stamped_key)"; then
            printf 'go-verify-stamp: no proof stamp for key %s\n' "${key:0:12}" >&2
            exit 1
        fi
        if [[ "$stamped" != "$key" ]]; then
            printf 'go-verify-stamp: proof stamp is STALE (stamped %s, current %s)\n' \
                "${stamped:0:12}" "${key:0:12}" >&2
            exit 1
        fi
        printf 'go-verify-stamp: proof stamp is current (key %s)\n' "${key:0:12}"
        ;;
    "" | -h | --help)
        sed -n '/^# Usage:/,/check     0 current/p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
        [[ -n "$COMMAND" ]] || exit 2
        ;;
    *)
        die "unknown command: $COMMAND" 2
        ;;
esac
