#!/usr/bin/env bash
# Bring a fresh checkout or execute-plan worktree to the state scripts/verify.sh
# requires (issue #135).
#
# The cost this removes is agent round-trips, not machine time. Measurement
# (docs/research/2026-08-07-plan-execution-efficiency.md) puts the whole
# sequence at 20.5 s under gate contention and ~3 s uncontended — `uv`
# reflinks .venv from the warm cache, so a "fresh" environment materializes
# essentially free. What actually cost minutes was five separate inference
# turns per worker, plus re-deriving the sequence from verify.sh's preflight
# failure message. One command is the fix; sharing environments between
# worktrees (the originally proposed remedy) was rejected because it buys ~15 s
# and costs cross-worktree coupling and absolute-path fragility in .venv.
#
# Deliberately NOT idempotence by skipping: every step is safe to repeat and is
# repeated. `uv build --clear` and the `rm -rf` before extraction are what keep
# build/release-wheel at exactly one wheel, which verify.sh requires; a
# "already looks done, skip it" shortcut is precisely how a stale runtime
# survives into a gate run.
#
# Usage:
#   scripts/bootstrap-worktree.sh            full bootstrap
#   scripts/bootstrap-worktree.sh --no-go    skip the Go toolchain install

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

WITH_GO=1
STEP=""

die() {
    printf '\nbootstrap: FAILED at step: %s\n' "${STEP:-preflight}" >&2
    printf 'bootstrap: %s\n' "$1" >&2
    exit "${2:-1}"
}

usage() {
    cat <<'EOF'
Usage: scripts/bootstrap-worktree.sh [--no-go] [--help]

  Prepares .venv, node_modules, build/release-wheel, build/wheel-runtime,
  its staleness stamp, and .tools — everything scripts/verify.sh checks for —
  and installs the tracked Git hooks.

  --no-go   skip `make go-tools` (Python/Markdown work only)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-go) WITH_GO=0 ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            die "unknown argument: $1" 2
            ;;
    esac
    shift
done

cd "$REPO_ROOT" || die "cannot enter $REPO_ROOT"

# Each step announces itself before running so a failure's context is on screen
# without needing the exit trap to reconstruct it.
step() {
    STEP="$1"
    shift
    printf '\n── %s ──\n' "$STEP"
    "$@" || die "step exited $?"
}

# First, and before anything that can fail: .git/hooks is untracked, so the
# `main` commit guard exists only where this ran. A checkout that dies in
# `npm ci` still has to be a checkout an agent cannot develop on `main` in.
step "install git hooks" \
    "$SCRIPT_DIR/install-githooks.sh"

step "uv sync --all-groups --locked" \
    uv sync --all-groups --locked

step "npm ci" \
    npm ci

# Before the build, not after: the projection is what the wheel packages, so a
# drifted projection would otherwise be baked into the runtime and only surface
# as a confusing failure several lanes into the gate.
step "payload projection check" \
    uv run project-standards standards sync-payload-projection --root . --check --json

step "uv build --wheel" \
    uv build --clear --wheel --out-dir build/release-wheel

STEP="extract candidate wheel"
printf '\n── %s ──\n' "$STEP"
mapfile -t built_wheels < <(
    find build/release-wheel -maxdepth 1 -type f -name 'project_standards-*.whl' -print | sort
)
# `--clear` should already guarantee this; asserting it here means a surprising
# build layout fails with its own name rather than as verify.sh's later and less
# specific "expected exactly one candidate wheel".
[[ "${#built_wheels[@]}" -eq 1 ]] ||
    die "expected exactly one wheel in build/release-wheel; found ${#built_wheels[@]}"
rm -rf -- build/wheel-runtime || die "cannot remove build/wheel-runtime"
uv run python -m zipfile -e "${built_wheels[0]}" build/wheel-runtime ||
    die "extraction exited $?"

# Last, so the stamp can only exist over a completed extraction.
step "stamp the runtime" \
    "$SCRIPT_DIR/wheel-runtime-stamp.sh" write

if [[ "$WITH_GO" == "1" ]]; then
    step "make go-tools" \
        make go-tools
fi

cat <<EOF

bootstrap: ready. The gate needs the runtime first on PYTHONPATH:

  export PYTHONPATH="$REPO_ROOT/build/wheel-runtime"
  scripts/verify.sh

Rebuild the runtime (rerun this script) after any change under src/** or to a
payload under standards/**; scripts/verify.sh now refuses a stale one by name.
EOF
