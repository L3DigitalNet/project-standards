#!/usr/bin/env bash
# Canonical local release gate for this repository.
#
# Default (fast gate, adopted 2026-07-31 — see
# docs/research/2026-07-31-release-gate-wall-clock-spike.md):
#   three concurrent lanes — statics, ordinary suite under coverage, and the
#   compatibility matrix — then a serial tail of the performance lane alone
#   (its assertions are timing-sensitive and must not share the machine),
#   then `coverage combine` + `coverage report`.
#
#   --full runs the legacy serial sequence instead (statics, serial ordinary
#   coverage run, compatibility at -n 4, performance, report). That is the
#   release-prep cross-check: it is the configuration the coverage baseline was
#   established under, so a disagreement between it and the fast gate is a real
#   signal rather than a parallelism artifact.
#
# Every command runs from `.venv/bin` rather than through `uv run`. Concurrent
# `uv run` invocations contend on the uv cache (the 2026-07-29 failure class);
# invoking the resolved binaries directly makes that class impossible because no
# uv process exists during the run.
#
# Environment the script establishes:
#   PYTHONPATH    the extracted candidate wheel (the dogfood contract; this
#                 script does not build it — see README.md "Developing this
#                 repository")
#   TMPDIR        a dedicated 4M-inode tmpfs at /mnt/pytesttmp when mounted,
#                 otherwise a disk-backed path under the user cache. The MCP
#                 fixture suites exhaust the default /tmp by inodes
#                 (docs/handoff/conventions.md §14).
#   COVERAGE_FILE off the repository root. xdist workers save `.coverage.<pid>`
#                 next to the data file; in-root they race the read-only digest
#                 proofs and the wheel-source copytree.
#   COVERAGE_CORE sysmon in the fast gate only (proved report-identical to the
#                 serial trace core). --full keeps the default trace core so the
#                 cross-check varies the core as well as the parallelism —
#                 otherwise a sysmon-specific divergence would be undetectable
#                 by the very lane documented to catch it.
#
# Usage:
#   scripts/verify.sh            fast gate (default)
#   scripts/verify.sh --full     legacy serial battery / release-prep cross-check
#
# TEST-ONLY: VERIFY_SMOKE=1 shrinks every pytest lane to a token selection so
# the lane orchestration itself can be exercised in seconds. It proves plumbing,
# never correctness — a smoke run is not a gate run.
#
# Worker counts are tuned for the 21-core workstation the spike measured and are
# overridable while controlled-condition benchmarking is still open:
#   VERIFY_ORDINARY_WORKERS (16), VERIFY_COMPAT_WORKERS (8),
#   VERIFY_FULL_COMPAT_WORKERS (4)

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_BIN="$REPO_ROOT/.venv/bin"
WHEEL_RUNTIME="$REPO_ROOT/build/wheel-runtime"

ORDINARY_WORKERS="${VERIFY_ORDINARY_WORKERS:-16}"
COMPAT_WORKERS="${VERIFY_COMPAT_WORKERS:-8}"
FULL_COMPAT_WORKERS="${VERIFY_FULL_COMPAT_WORKERS:-4}"
SMOKE="${VERIFY_SMOKE:-0}"

MODE="fast"

die() {
    printf 'verify: %s\n' "$1" >&2
    exit "${2:-1}"
}

usage() {
    cat <<'EOF'
Usage: scripts/verify.sh [--full] [--help]

  (default)  fast gate: statics + ordinary + compatibility concurrently,
             then performance alone, then coverage combine + report
  --full     legacy serial battery (release-prep cross-check)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full) MODE="full" ;;
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

# ── Preflight ─────────────────────────────────────────────────────────────
cd "$REPO_ROOT" || die "cannot enter $REPO_ROOT"

if [[ ! -d "$WHEEL_RUNTIME" ]]; then
    die "missing $WHEEL_RUNTIME — build the candidate wheel runtime first:
  uv build --wheel --out-dir dist
  uv run python -m zipfile -e dist/project_standards-*.whl build/wheel-runtime"
fi

for tool in coverage pytest ruff basedpyright pip-audit; do
    [[ -x "$VENV_BIN/$tool" ]] || die "missing $VENV_BIN/$tool — run: uv sync --all-groups"
done
# The resolved binaries, not npx: a partial node_modules would make npx fall
# back to a registry fetch or an interactive prompt inside a redirected lane.
NODE_BIN="$REPO_ROOT/node_modules/.bin"
for tool in prettier markdownlint-cli2; do
    [[ -x "$NODE_BIN/$tool" ]] || die "missing $NODE_BIN/$tool — run: npm ci"
done

# ── Temporary-file root ───────────────────────────────────────────────────
# A bind-mounted or symlinked directory would not report a distinct device, so
# comparing st_dev against the parent is the check that actually answers "is a
# separate filesystem mounted here" without depending on util-linux.
is_mountpoint() {
    local path="$1" device parent_device
    [[ -d "$path" ]] || return 1
    device="$(stat -c %d "$path" 2>/dev/null)" || return 1
    parent_device="$(stat -c %d "$path/.." 2>/dev/null)" || return 1
    [[ "$device" != "$parent_device" ]]
}

if is_mountpoint /mnt/pytesttmp; then
    TMP_ROOT="/mnt/pytesttmp/project-standards-gate"
    TMP_KIND="dedicated tmpfs /mnt/pytesttmp"
else
    TMP_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/project-standards-gate"
    TMP_KIND="disk-backed fallback (conventions §14)"
fi

# One gate at a time per machine: TMP_ROOT is a fixed path and the cleanup
# below would destroy a concurrent run's TMPDIR, basetemps, and coverage data
# mid-flight. mkdir is the atomic test-and-set; the trap releases it on any
# exit path.
LOCK_DIR="${TMP_ROOT}.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    die "another verify.sh appears to be running (lock: $LOCK_DIR); if that is stale, remove it"
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

rm -rf "$TMP_ROOT" || die "cannot clean $TMP_ROOT"
LOG_DIR="$TMP_ROOT/logs"
RESULT_DIR="$TMP_ROOT/results"
BASETEMP_ROOT="$TMP_ROOT/basetemp"
# BASETEMP_ROOT must exist before pytest runs: pytest recreates the --basetemp
# leaf itself with a plain mkdir and fails if the parent is missing.
mkdir -p "$TMP_ROOT/tmp" "$TMP_ROOT/coverage" "$LOG_DIR" "$RESULT_DIR" "$BASETEMP_ROOT" ||
    die "cannot create $TMP_ROOT"

export PYTHONPATH="$WHEEL_RUNTIME"
export TMPDIR="$TMP_ROOT/tmp"
export COVERAGE_FILE="$TMP_ROOT/coverage/.coverage"
# `uv run` prepends .venv/bin to PATH; invoking the venv binaries directly
# skips that, so test-spawned subprocesses calling bare `python3` would
# resolve into whatever shim the workstation puts first (the v5.12.0 CI
# sandbox defect class). Restore the venv-first PATH the serial gate had.
export PATH="$VENV_BIN:$PATH"
# Fast gate only — --full must keep the default trace core (see header).
if [[ "$MODE" == "fast" ]]; then
    export COVERAGE_CORE="sysmon"
else
    unset COVERAGE_CORE
fi

# ── Lane bookkeeping ──────────────────────────────────────────────────────
LANE_ORDER=()

# Runs one lane to completion, capturing its output and wall time. Called in the
# background for concurrent lanes and in the foreground for the serial tail, so
# every lane records its result the same way regardless of mode.
run_lane() {
    local name="$1" start end status
    shift
    start="$(date +%s)"
    "$@" >"$LOG_DIR/$name.log" 2>&1 </dev/null
    status=$?
    end="$(date +%s)"
    printf '%s\t%s\n' "$status" "$((end - start))" >"$RESULT_DIR/$name"
    return "$status"
}

start_lane() {
    LANE_ORDER+=("$1")
    run_lane "$@" &
}

serial_lane() {
    LANE_ORDER+=("$1")
    run_lane "$@"
}

# ── Lanes ─────────────────────────────────────────────────────────────────
# The statics lane runs every step even after one fails: a single pass should
# surface all style findings, not just the first.
statics_step() {
    local label="$1"
    shift
    printf '\n=== %s ===\n' "$label"
    "$@"
}

lane_statics() {
    local status=0
    statics_step "ruff format --check" "$VENV_BIN/ruff" format --check . || status=1
    statics_step "ruff check" "$VENV_BIN/ruff" check . || status=1
    if [[ "$SMOKE" == "1" ]]; then
        # Smoke proves lane plumbing; ruff alone is enough signal in seconds.
        printf '\n(smoke: basedpyright/prettier/markdownlint/pip-audit skipped)\n'
        return "$status"
    fi
    statics_step "basedpyright" "$VENV_BIN/basedpyright" || status=1
    statics_step "prettier" "$NODE_BIN/prettier" --check . --cache || status=1
    statics_step "markdownlint" "$NODE_BIN/markdownlint-cli2" || status=1
    statics_step "pip-audit" "$VENV_BIN/pip-audit" || status=1
    return "$status"
}

lane_ordinary() {
    local args=(
        --source=project_standards -m pytest
        -m "not performance and not compatibility"
        -n "$ORDINARY_WORKERS" --dist load --max-worker-restart=0
        --basetemp="$BASETEMP_ROOT/ordinary"
    )
    [[ "$SMOKE" == "1" ]] && args+=(-k test_repository_workflow)
    "$VENV_BIN/coverage" run "${args[@]}"
}

lane_ordinary_serial() {
    local args=(
        --source=project_standards -m pytest
        -m "not performance and not compatibility"
        --basetemp="$BASETEMP_ROOT/ordinary"
    )
    [[ "$SMOKE" == "1" ]] && args+=(-k test_repository_workflow)
    "$VENV_BIN/coverage" run "${args[@]}"
}

lane_compatibility() {
    local workers="$1"
    local args=(
        -m compatibility -n "$workers" --dist load --max-worker-restart=0
        --basetemp="$BASETEMP_ROOT/compatibility"
    )
    # The compatibility matrix installs wheels per case; there is no cheap
    # subset, so smoke mode proves the lane runs by collecting only.
    [[ "$SMOKE" == "1" ]] && args+=(--collect-only -q)
    "$VENV_BIN/pytest" "${args[@]}"
}

lane_performance() {
    local args=(-m performance --basetemp="$BASETEMP_ROOT/performance")
    [[ "$SMOKE" == "1" ]] && args+=(--collect-only -q)
    "$VENV_BIN/pytest" "${args[@]}"
}

lane_coverage_combine() {
    "$VENV_BIN/coverage" combine
}

lane_coverage_report() {
    local args=()
    # A token selection can never clear the real fail-under, and a permanently
    # red report lane would hide genuine orchestration failures in the summary.
    [[ "$SMOKE" == "1" ]] && args+=(--fail-under=0)
    "$VENV_BIN/coverage" report "${args[@]}"
}

# ── Run ───────────────────────────────────────────────────────────────────
printf 'verify: mode=%s tmp=%s (%s)\n' "$MODE" "$TMP_ROOT" "$TMP_KIND"
[[ "$SMOKE" == "1" ]] && printf 'verify: VERIFY_SMOKE=1 — token selections, NOT a gate run\n'
printf 'verify: PYTHONPATH=%s\n\n' "$PYTHONPATH"

# Fresh-clone parity with CI: first-import __pycache__ creation mutates
# parent-dir mtimes mid-run and races the read-only real-root digest proof.
# tests/ ONLY — the battery imports the package from build/wheel-runtime,
# and compiling src/ litters the symlink-only payload projection, failing
# the projection and wheel-content proofs.
"$VENV_BIN/python" -m compileall -q tests || die "compileall failed"

"$VENV_BIN/coverage" erase || die "coverage erase failed"

GATE_START="$(date +%s)"

if [[ "$MODE" == "fast" ]]; then
    start_lane statics lane_statics
    start_lane ordinary lane_ordinary
    start_lane compatibility lane_compatibility "$COMPAT_WORKERS"
    wait

    # Timing-sensitive: never concurrent with another lane.
    serial_lane performance lane_performance
    serial_lane coverage-combine lane_coverage_combine
else
    serial_lane statics lane_statics
    serial_lane ordinary lane_ordinary_serial
    serial_lane compatibility lane_compatibility "$FULL_COMPAT_WORKERS"
    serial_lane performance lane_performance
fi

serial_lane coverage-report lane_coverage_report

GATE_SECONDS="$(($(date +%s) - GATE_START))"

# ── Report ────────────────────────────────────────────────────────────────
format_duration() {
    printf '%d:%02d' "$(($1 / 60))" "$(($1 % 60))"
}

exit_status=0

for lane in "${LANE_ORDER[@]}"; do
    printf '\n════ %s ════\n' "$lane"
    cat "$LOG_DIR/$lane.log"
done

printf '\n════ summary ════\n'
for lane in "${LANE_ORDER[@]}"; do
    IFS=$'\t' read -r lane_status lane_seconds <"$RESULT_DIR/$lane"
    if [[ "$lane_status" == "0" ]]; then
        verdict="ok"
    else
        verdict="FAILED (exit $lane_status)"
        exit_status=1
    fi
    printf '  %-16s %8s  %s\n' "$lane" "$(format_duration "$lane_seconds")" "$verdict"
done
printf '  %-16s %8s\n' "TOTAL" "$(format_duration "$GATE_SECONDS")"
[[ "$SMOKE" == "1" ]] && printf '  (VERIFY_SMOKE=1 — token selections, NOT a gate run)\n'

exit "$exit_status"
