#!/usr/bin/env bash
# Content key for the extracted candidate-wheel runtime (issue #136).
#
# The dogfood contract puts `build/wheel-runtime` first on PYTHONPATH, but
# nothing tied that extraction to the sources it was built from. A stale
# runtime does not announce itself: once this repository's own
# `.standards/config.toml` selects a family the stale copy does not carry, the
# failure surfaces as `CP-RESOLUTION: unavailable`, which names resolution when
# the actual cause is an out-of-date extraction. This script is the single
# authority for the key that closes that gap, so the builder that writes the
# stamp and the gate that checks it can never compute it differently.
#
# Key inputs — everything that changes the wheel's contents:
#   src/**          resolved through the payload projection's symlinks, so a
#                   payload edit under standards/** moves the key exactly as a
#                   hand-written change to src/project_standards/ does
#                   (conventions §11: the projection is symlink-only)
#   pyproject.toml  packaging metadata and the release version. The version
#                   matters on its own: mid-train it is what makes an otherwise
#                   current runtime report CP-RESOLUTION until the bump lands.
#
# Content, not mtime. A metadata key would call the runtime stale after any
# `git checkout` round-trip that restored identical bytes, and this repository
# already reasons in byte-exact digests everywhere else. Hashing the resolved
# tree costs ~70 ms against a ~12-minute gate, so the accuracy is free.
#
# Fail-closed: any error while walking or hashing yields exit 2 (indeterminate),
# never a key. A broken symlink in the projection is the expected instance —
# `sync-payload-projection --check` owns that fault, and this script must not
# paper over it by silently hashing a smaller tree.
#
# Usage:
#   scripts/wheel-runtime-stamp.sh compute   print the key
#   scripts/wheel-runtime-stamp.sh write     write build/wheel-runtime.stamp
#   scripts/wheel-runtime-stamp.sh check     0 current, 1 stale/missing, 2 error

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WHEEL_RUNTIME="$REPO_ROOT/build/wheel-runtime"
# Beside the extraction, never inside it: `build/wheel-runtime` is a byte-exact
# expansion of the candidate wheel, and a stamp within it would be an
# unpackaged file in a tree whose whole purpose is to match the wheel.
STAMP_FILE="$REPO_ROOT/build/wheel-runtime.stamp"
STAMP_SCHEMA=1

die() {
    printf 'wheel-runtime-stamp: %s\n' "$1" >&2
    exit "${2:-2}"
}

# Hashes the resolved source tree. `-L` follows the projection symlinks so the
# payload bytes themselves enter the key; `sha256sum` embeds each path, so a
# rename moves the key even when no content changed.
#
# Runs from REPO_ROOT with relative operands on purpose. `sha256sum` prints the
# path it was given, so absolute operands would fold the checkout location into
# the key and every execute-plan worktree — the exact place this check has to
# work — would disagree with the primary checkout over identical bytes.
compute_key() {
    local digest
    digest="$(
        cd "$REPO_ROOT" &&
            find -L src pyproject.toml \
                -type f -not -path '*/__pycache__/*' -print0 |
            LC_ALL=C sort -z |
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

rebuild_hint() {
    cat <<'EOF'
rebuild the candidate wheel runtime:
  scripts/bootstrap-worktree.sh
or, by hand (README.md "Developing this repository"):
  uv run project-standards standards sync-payload-projection --root . --check --json
  uv build --clear --wheel --out-dir build/release-wheel
  rm -rf -- build/wheel-runtime
  uv run python -m zipfile -e build/release-wheel/project_standards-*.whl build/wheel-runtime
  scripts/wheel-runtime-stamp.sh write
EOF
}

COMMAND="${1:-}"
[[ $# -le 1 ]] || die "expected at most one argument" 2

case "$COMMAND" in
    compute)
        key="$(compute_key)" || die "cannot compute the content key (unreadable source or broken projection symlink)"
        printf '%s\n' "$key"
        ;;
    write)
        [[ -d "$WHEEL_RUNTIME" ]] || die "missing $WHEEL_RUNTIME — extract the candidate wheel before stamping it"
        key="$(compute_key)" || die "cannot compute the content key (unreadable source or broken projection symlink)"
        mkdir -p "$(dirname "$STAMP_FILE")" || die "cannot create $(dirname "$STAMP_FILE")"
        # Written last, after the extraction it describes exists: a stamp that
        # could outlive a failed extraction would assert currency for a runtime
        # that was never produced.
        {
            printf '# project-standards candidate-wheel runtime stamp\n'
            printf 'schema=%s\n' "$STAMP_SCHEMA"
            printf 'key=%s\n' "$key"
            printf 'stamped=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        } >"$STAMP_FILE" || die "cannot write $STAMP_FILE"
        printf 'wheel-runtime-stamp: wrote %s (key %s)\n' "${STAMP_FILE#"$REPO_ROOT/"}" "${key:0:12}"
        ;;
    check)
        [[ -d "$WHEEL_RUNTIME" ]] || {
            printf 'wheel-runtime-stamp: missing %s\n' "${WHEEL_RUNTIME#"$REPO_ROOT/"}" >&2
            exit 1
        }
        key="$(compute_key)" || die "cannot compute the content key (unreadable source or broken projection symlink)"
        # A missing or unparsable stamp is stale, not current: extractions made
        # before this check existed carry no stamp, and treating them as current
        # would reintroduce the exact silent-staleness failure.
        if ! stamped="$(read_stamped_key)"; then
            printf 'wheel-runtime-stamp: %s carries no stamp — treating the runtime as stale\n' \
                "${WHEEL_RUNTIME#"$REPO_ROOT/"}" >&2
            rebuild_hint >&2
            exit 1
        fi
        if [[ "$stamped" != "$key" ]]; then
            printf 'wheel-runtime-stamp: %s is STALE — src/** or pyproject.toml changed since it was built\n' \
                "${WHEEL_RUNTIME#"$REPO_ROOT/"}" >&2
            printf '  stamped key %s\n  current key %s\n' "${stamped:0:12}" "${key:0:12}" >&2
            rebuild_hint >&2
            exit 1
        fi
        ;;
    "" | -h | --help)
        sed -n '/^# Usage:/,/check     0 current/p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
        [[ -n "$COMMAND" ]] || exit 2
        ;;
    *)
        die "unknown command: $COMMAND" 2
        ;;
esac
