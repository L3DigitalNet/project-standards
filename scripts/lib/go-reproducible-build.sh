# shellcheck shell=bash
#
# Shared reproducible-build contract for every Go artifact this repository ships as
# committed payload bytes.
#
# Each artifact keeps its own thin build script — that script is the single definition of
# *what* is built and where it lands, and the spec for each package names it by path. This
# library owns the part that must never differ between them: the pinned build environment
# and the rebuild-and-compare verification. Duplicating that per artifact is how one
# binary silently acquires a different toolchain pin than its sibling.
#
# A caller sources this file, sets the three required variables, then calls
# `go_artifact_main "$@"`:
#
#   ARTIFACT_OUTPUT_PATH  committed path of the binary, relative to the repository root
#   ARTIFACT_PACKAGE      Go package to build (e.g. ./cmd/foo)
#   ARTIFACT_LDFLAGS      link flags, including the version stamp
#
# Requirements: bash, GNU coreutils (`cmp`, `mktemp`, `sha256sum`), and the Go toolchain
# pinned by the `toolchain` line in go.mod. No network access is needed once the module
# cache is warm.

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
# built this way reports a plain `go1.26.6` toolchain version, not the `-X:nodwarf5`
# variant. Verified: the upstream and Fedora toolchains produce byte-identical output
# under this pin. Setting the variable to the empty string does NOT work, because the go
# command falls back to go.env whenever the environment value is empty.
#
# When a future toolchain retires the experiment, this fails loudly at build time rather
# than silently producing different bytes; drop the pin in the same change that moves the
# toolchain and rebuild every committed binary.
readonly GOEXPERIMENT_PIN="dwarf5"

# go_artifact_preflight rejects an environment that would perturb the pinned build.
go_artifact_preflight() {
    # Derived from go.mod so the pin has exactly one source of truth. A newer local
    # toolchain satisfies go.mod's minimum and would otherwise build silently — producing
    # valid but byte-different output that surfaces only as an unexplained `--verify`
    # failure.
    local toolchain
    toolchain="$(awk '$1 == "toolchain" { print $2 }' go.mod)"
    if [[ -z "$toolchain" ]]; then
        echo "error: go.mod has no 'toolchain' line; cannot pin the build toolchain." >&2
        exit 1
    fi

    local actual
    actual="$(go version | awk '{ print $3 }')"
    if [[ "$actual" != "$toolchain" && "$actual" != "$toolchain"-* ]]; then
        echo "error: toolchain mismatch: go.mod pins $toolchain but 'go version' reports $actual." >&2
        echo "       Install the pinned toolchain or set GOTOOLCHAIN=$toolchain." >&2
        exit 1
    fi

    # GOFLAGS is prepended to every go invocation and can add build tags or change the
    # module mode, silently altering the output of the fixed command below.
    local goflags
    goflags="$(go env GOFLAGS)"
    if [[ -n "$goflags" ]]; then
        echo "error: GOFLAGS is set to '$goflags'; it would perturb the pinned build." >&2
        echo "       Clear it (go env -u GOFLAGS, or unset the variable) and retry." >&2
        exit 1
    fi
}

# go_artifact_build_to runs the complete pinned build invocation.
#
# Callers pass the destination only; every other operand is part of the contract and must
# not become configurable.
go_artifact_build_to() {
    local destination="$1"
    GOEXPERIMENT="$GOEXPERIMENT_PIN" \
        GOOS=linux GOARCH=amd64 GOAMD64=v1 CGO_ENABLED=0 \
        go build -trimpath -buildvcs=false -ldflags "$ARTIFACT_LDFLAGS" \
        -o "$destination" "$ARTIFACT_PACKAGE"
}

# go_artifact_main implements the shared `--build` / `--verify` interface.
go_artifact_main() {
    go_artifact_preflight

    case "${1:---build}" in
    --build)
        mkdir -p "$(dirname "$ARTIFACT_OUTPUT_PATH")"
        go_artifact_build_to "$ARTIFACT_OUTPUT_PATH"
        # Explicit rather than umask-dependent: the payload declares mode 0755 and
        # reconcile delivers the committed mode, so a 0644 build here would ship a
        # non-executable artifact.
        chmod 0755 "$ARTIFACT_OUTPUT_PATH"
        echo "built $ARTIFACT_OUTPUT_PATH ($(sha256sum "$ARTIFACT_OUTPUT_PATH" | cut -d' ' -f1))"
        ;;
    --verify)
        if [[ ! -f "$ARTIFACT_OUTPUT_PATH" ]]; then
            echo "error: committed binary is missing at $ARTIFACT_OUTPUT_PATH." >&2
            echo "       Run $BUILD_SCRIPT_NAME and commit the result." >&2
            exit 1
        fi

        local scratch
        scratch="$(mktemp -d)"
        # shellcheck disable=SC2064  # expand scratch now, not at trap time
        trap "rm -rf '$scratch'" EXIT
        go_artifact_build_to "$scratch/artifact"

        if ! cmp -s "$scratch/artifact" "$ARTIFACT_OUTPUT_PATH"; then
            echo "error: committed binary does not match a rebuild from this commit's source." >&2
            echo "       committed: $(sha256sum "$ARTIFACT_OUTPUT_PATH" | cut -d' ' -f1)" >&2
            echo "       rebuilt:   $(sha256sum "$scratch/artifact" | cut -d' ' -f1)" >&2
            echo "       Run $BUILD_SCRIPT_NAME and commit the result." >&2
            exit 1
        fi
        echo "verified $ARTIFACT_OUTPUT_PATH matches a rebuild ($(sha256sum "$ARTIFACT_OUTPUT_PATH" | cut -d' ' -f1))"
        ;;
    *)
        echo "usage: $BUILD_SCRIPT_NAME [--build | --verify]" >&2
        exit 2
        ;;
    esac
}
