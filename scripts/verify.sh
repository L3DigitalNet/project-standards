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
#   coverage run, compatibility, performance, report). That is the release-prep
#   cross-check: it is the configuration the coverage baseline was established
#   under, so a disagreement between it and the fast gate is a real signal
#   rather than a parallelism artifact.
#
# Every command runs from `.venv/bin` rather than through `uv run`. Concurrent
# `uv run` invocations contend on the uv cache (the 2026-07-29 failure class);
# invoking the resolved binaries directly makes that class impossible because no
# uv process exists during the run.
#
# Environment the script establishes:
#   PYTHONPATH    the extracted candidate wheel (the dogfood contract; this
#                 script does not build it — see README.md "Developing this
#                 repository"). The preflight proves it is both present and
#                 current, via scripts/wheel-runtime-stamp.sh.
#   PROJECT_STANDARDS_COMPATIBILITY_WHEEL
#                 the one resolved wheel that compatibility rows extract
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
# --fail-fast stops the run at the first red lane and is the default for --full;
# --keep-going restores run-every-lane and is the default for the fast gate. The
# split follows what each mode is for: a serial battery that already knows it is
# red spends its remaining lanes proving nothing (on the 2026-09-01 train roughly
# 35 minutes of compatibility matrix ran after the ordinary lane had failed,
# issue #236 C6), while the fast gate's three lanes start together, so there is
# nothing left to save and a complete picture of every finding is worth more.
# Lanes cut short are reported in the summary as `skipped`, never omitted: a lane
# missing from the table would read as a lane that was never part of the mode.
#
# TEST-ONLY: VERIFY_SMOKE=1 shrinks every pytest lane to a token selection so
# the lane orchestration itself can be exercised in seconds. It proves plumbing,
# never correctness — a smoke run is not a gate run.
# TEST-ONLY: VERIFY_TMP_PARENT gives smoke-mode nested-gate tests their own lock
# and artifacts. The fixed child keeps cleanup scoped even if the parent is set
# too broadly; a nested fixture using the production root would collide with the
# parent gate whose orchestration it is validating.
#
# Worker counts are sized for the machine that actually runs this gate — the
# 40-core / 64 GiB rexec worker — and stay overridable:
#   VERIFY_ORDINARY_WORKERS (16), VERIFY_COMPAT_WORKERS (8),
#   VERIFY_FULL_COMPAT_WORKERS (16)

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_BIN="$REPO_ROOT/.venv/bin"
WHEEL_RUNTIME="$REPO_ROOT/build/wheel-runtime"
RELEASE_WHEEL_DIR="$REPO_ROOT/build/release-wheel"

ORDINARY_WORKERS="${VERIFY_ORDINARY_WORKERS:-16}"
COMPAT_WORKERS="${VERIFY_COMPAT_WORKERS:-8}"
FULL_COMPAT_WORKERS="${VERIFY_FULL_COMPAT_WORKERS:-16}"
SMOKE="${VERIFY_SMOKE:-0}"

MODE="fast"
# Empty until argument parsing finishes, so an explicit flag can be told apart
# from the mode-derived default resolved below.
FAIL_FAST=""

die() {
    printf 'verify: %s\n' "$1" >&2
    exit "${2:-1}"
}

usage() {
    cat <<'EOF'
Usage: scripts/verify.sh [--full] [--fail-fast | --keep-going] [--help]

  (default)     fast gate: statics + ordinary + compatibility concurrently,
                then performance alone, then coverage combine + report
  --full        legacy serial battery (release-prep cross-check)
  --fail-fast   stop at the first red lane; remaining lanes report as skipped
                (default with --full)
  --keep-going  run every lane even after one is red (default for the fast gate)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full) MODE="full" ;;
        --fail-fast) FAIL_FAST=1 ;;
        --keep-going) FAIL_FAST=0 ;;
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

# --full is the release-prep cross-check, where a lane after the first red one
# proves nothing and costs tens of minutes; the fast gate's lanes are already
# running when the first red appears, so it defaults to the full picture. An
# explicit flag in either direction wins over the mode.
if [[ -z "$FAIL_FAST" ]]; then
    if [[ "$MODE" == "full" ]]; then FAIL_FAST=1; else FAIL_FAST=0; fi
fi

# ── Preflight ─────────────────────────────────────────────────────────────
cd "$REPO_ROOT" || die "cannot enter $REPO_ROOT"

if [[ ! -d "$WHEEL_RUNTIME" ]]; then
    die "missing $WHEEL_RUNTIME — build the candidate wheel runtime first:
  scripts/bootstrap-worktree.sh
or by hand:
  uv build --clear --wheel --out-dir build/release-wheel
  rm -rf -- build/wheel-runtime
  uv run python -m zipfile -e build/release-wheel/project_standards-X.Y.Z-py3-none-any.whl build/wheel-runtime
  scripts/wheel-runtime-stamp.sh write"
fi

# Existing is not current (issue #136). A stale extraction runs the gate against
# yesterday's engine, and once this repository's own config selects a family the
# stale copy lacks, it fails as `CP-RESOLUTION: unavailable` — a message that
# points at resolution rather than at the runtime. Checking here converts that
# into its actual cause, before any lane spends time on it.
#
# Fail, do not rebuild. This script's contract is that it does not build the
# runtime (see the header): building here would make the gate's own inputs a
# side effect of running it, and a rebuild racing the lock-holder's PYTHONPATH
# is a worse failure than an accurate refusal. `--full` release-prep runs get
# the same refusal for the same reason.
STAMP_SCRIPT="$SCRIPT_DIR/wheel-runtime-stamp.sh"
[[ -x "$STAMP_SCRIPT" ]] || die "missing $STAMP_SCRIPT"
"$STAMP_SCRIPT" check || die "candidate wheel runtime is not current — see above"

if [[ -d "$RELEASE_WHEEL_DIR" ]]; then
    mapfile -t candidate_wheels < <(
        find "$RELEASE_WHEEL_DIR" -maxdepth 1 -type f -name 'project_standards-*.whl' -print | sort
    )
else
    candidate_wheels=()
fi
if [[ "${#candidate_wheels[@]}" -ne 1 ]]; then
    die "expected exactly one candidate wheel in $RELEASE_WHEEL_DIR; found ${#candidate_wheels[@]}"
fi
COMPATIBILITY_WHEEL="$(realpath -e "${candidate_wheels[0]}")" || die "cannot resolve candidate wheel"
export PROJECT_STANDARDS_COMPATIBILITY_WHEEL="$COMPATIBILITY_WHEEL"

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

if [[ -n "${VERIFY_TMP_PARENT:-}" ]]; then
    [[ "$SMOKE" == "1" ]] || die "VERIFY_TMP_PARENT is test-only and requires VERIFY_SMOKE=1"
    TMP_ROOT="${VERIFY_TMP_PARENT%/}/project-standards-gate"
    TMP_KIND="explicit test override"
elif is_mountpoint /mnt/pytesttmp; then
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

# This wipe already reaps any stale basetemp left by a prior run of THIS
# script (crash, SIGKILL past the EXIT trap, or a run a human aborted after
# manually clearing $LOCK_DIR) — it runs only after the mkdir-based lock
# above proves no concurrent verify.sh holds $TMP_ROOT, so it can never
# destroy another run's live TMPDIR, basetemps, or coverage data (see the
# lock comment). What it does NOT cover is space exhausted WITHIN a single
# run: each pytest lane's --basetemp tree survives until this line runs
# again next time, so three lanes' worth of scratch data can coexist during
# one gate and, on a full tmpfs, starve the coverage/performance lanes that
# run last (observed: 15 GiB in one basetemp tree after repeated runs,
# `printf: write error: No space left on device` mid-lane). The per-lane
# reap_basetemp calls below close that gap by freeing each lane's basetemp
# as soon as that lane succeeds, instead of waiting for the next run.
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
# No import in this battery may leave bytecode beside a payload provider: on a
# workspace-reusing runner those caches survive into the next run's checkout and
# every suite that enumerates a payload source tree then sees an undeclared file
# (hosted `Check` red for four consecutive runs from 1a01038d). tests/payload_tree.py
# makes the enumerations themselves immune; this keeps the caches from appearing at
# all. The compileall pre-warm below is unaffected — py_compile writes explicitly,
# while this variable only stops the *import system* from writing.
export PYTHONDONTWRITEBYTECODE=1
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

# Answers "has any lane recorded so far come back red?" from $RESULT_DIR rather
# than from a shell variable: concurrent lanes run in background subshells, so a
# status set there can never reach this shell. Unrecorded counts as red, matching
# the summary's rule — a lane that died before writing its result is a failure.
gate_has_red() {
    local lane status
    for lane in "${LANE_ORDER[@]}"; do
        status=""
        if [[ -r "$RESULT_DIR/$lane" ]]; then
            IFS=$'\t' read -r status _ <"$RESULT_DIR/$lane" || true
        fi
        [[ "$status" == "0" ]] || return 0
    done
    return 1
}

# Records a lane the run deliberately did not execute. It still joins LANE_ORDER
# and still gets a log and a result file, so the summary shows it as `skipped`
# instead of dropping it: an absent row is indistinguishable from a lane the mode
# never had, which is exactly the confusion a fail-fast run must not create.
skip_lane() {
    LANE_ORDER+=("$1")
    printf 'skipped: an earlier lane failed and --fail-fast is in effect\n' >"$LOG_DIR/$1.log"
    printf 'skipped\t\n' >"$RESULT_DIR/$1"
}

# The fail-fast gate for every serial lane. Concurrent lanes are started before
# any result exists and so are never guarded; under --fail-fast the cut therefore
# begins at the first serial lane, which in fast mode is the performance tail.
serial_lane_unless_red() {
    if [[ "$FAIL_FAST" == "1" ]] && gate_has_red; then
        skip_lane "$1"
        return 0
    fi
    serial_lane "$@"
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

# Frees one lane's --basetemp tree once that lane no longer needs it. Called
# only on the lane's success path (never wired to a failure or non-zero
# return), so a failing lane's scratch tree survives on disk for a human to
# inspect — the reap trades that diagnostic copy for headroom in the
# common (green) case, which is the case that runs the gate repeatedly and
# fills the tmpfs. It touches only $BASETEMP_ROOT/<lane>, never the sibling
# coverage or logs directories under $TMP_ROOT, which later lanes and the
# final report/log dump still need.
reap_basetemp() {
    rm -rf "$1" 2>/dev/null || true
}

lane_ordinary() {
    local args=(
        --source=project_standards -m pytest
        -m "not performance and not compatibility"
        -n "$ORDINARY_WORKERS" --dist load --max-worker-restart=0
        --basetemp="$BASETEMP_ROOT/ordinary"
    )
    [[ "$SMOKE" == "1" ]] && args+=(-k test_repository_workflow)
    "$VENV_BIN/coverage" run "${args[@]}" || return $?
    reap_basetemp "$BASETEMP_ROOT/ordinary"
}

lane_ordinary_serial() {
    local args=(
        --source=project_standards -m pytest
        -m "not performance and not compatibility"
        --basetemp="$BASETEMP_ROOT/ordinary"
    )
    [[ "$SMOKE" == "1" ]] && args+=(-k test_repository_workflow)
    "$VENV_BIN/coverage" run "${args[@]}" || return $?
    reap_basetemp "$BASETEMP_ROOT/ordinary"
}

lane_compatibility() {
    local workers="$1"
    local args=(
        -m compatibility -n "$workers" --dist load --max-worker-restart=0
        --basetemp="$BASETEMP_ROOT/compatibility"
    )
    # Smoke mode collects only because there is no cheap subset, NOT because of
    # the wheel: both distributions are session fixtures
    # (tests/package_compatibility/conftest.py) and the wheel arm additionally
    # honors PROJECT_STANDARDS_COMPATIBILITY_WHEEL, exported above, so the build
    # happens at most once per worker. The cost is the matrix rows themselves —
    # each runs the full adopt/reconcile lifecycle once per distribution — and no
    # `-k` selection of them proves the ownership matrix this lane exists for.
    [[ "$SMOKE" == "1" ]] && args+=(--collect-only -q)
    "$VENV_BIN/pytest" "${args[@]}" || return $?
    reap_basetemp "$BASETEMP_ROOT/compatibility"
}

lane_performance() {
    local args=(-m performance --basetemp="$BASETEMP_ROOT/performance")
    [[ "$SMOKE" == "1" ]] && args+=(--collect-only -q)
    "$VENV_BIN/pytest" "${args[@]}" || return $?
    reap_basetemp "$BASETEMP_ROOT/performance"
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
printf 'verify: mode=%s fail-fast=%s tmp=%s (%s)\n' "$MODE" "$FAIL_FAST" "$TMP_ROOT" "$TMP_KIND"
[[ "$SMOKE" == "1" ]] && printf 'verify: VERIFY_SMOKE=1 — token selections, NOT a gate run\n'
printf 'verify: PYTHONPATH=%s\n\n' "$PYTHONPATH"
printf 'verify: PROJECT_STANDARDS_COMPATIBILITY_WHEEL=%s\n\n' "$PROJECT_STANDARDS_COMPATIBILITY_WHEEL"

# Fresh-clone parity with CI: first-import __pycache__ creation mutates
# parent-dir mtimes mid-run and races the read-only real-root digest proof.
# tests/ plus the src package (clean-env subprocess tests import the
# editable install from src/), EXCLUDING the payloads/bundles resource
# mirrors whose byte-exact proofs a compile would break.
# scripts/ belongs here too: several suites import scripts/*.py as modules
# rather than running them, so on a cold checkout the first such import
# created scripts/__pycache__ mid-battery. The digest prunes __pycache__ but
# still hashes its PARENT, so that lone directory's size and mtime moved
# between the proof's two samples and it reported a phantom write (hosted
# Check 30973008922; an instrumented cold-clone battery showed `scripts` as
# the only changed entry, with no file entry touched).
"$VENV_BIN/python" -m compileall -q tests src/project_standards scripts \
    -x "/(payloads|bundles)/" ||
    die "compileall failed"

"$VENV_BIN/coverage" erase || die "coverage erase failed"

GATE_START="$(date +%s)"

if [[ "$MODE" == "fast" ]]; then
    start_lane statics lane_statics
    start_lane ordinary lane_ordinary
    start_lane compatibility lane_compatibility "$COMPAT_WORKERS"
    wait

    # Timing-sensitive: never concurrent with another lane.
    serial_lane_unless_red performance lane_performance
    serial_lane_unless_red coverage-combine lane_coverage_combine
else
    serial_lane_unless_red statics lane_statics
    serial_lane_unless_red ordinary lane_ordinary_serial
    serial_lane_unless_red compatibility lane_compatibility "$FULL_COMPAT_WORKERS"
    serial_lane_unless_red performance lane_performance
fi

serial_lane_unless_red coverage-report lane_coverage_report

GATE_SECONDS="$(($(date +%s) - GATE_START))"

# ── Report ────────────────────────────────────────────────────────────────
# A lane's result file is written only after its command returns, so a run that
# died mid-lane — the gate exhausting its tmpfs is the observed case — leaves the
# file missing, empty, or truncated to the status field. Arithmetic on the blank
# elapsed value used to abort the summary loop with
# "verify.sh: line N: / 60: syntax error: operand expected", swallowing the lane
# table at exactly the run where it was needed to say which lane died.
format_duration() {
    [[ "$1" =~ ^[0-9]+$ ]] || {
        printf '%s' '—'
        return
    }
    printf '%d:%02d' "$(($1 / 60))" "$(($1 % 60))"
}

exit_status=0

for lane in "${LANE_ORDER[@]}"; do
    printf '\n════ %s ════\n' "$lane"
    cat "$LOG_DIR/$lane.log"
done

printf '\n════ summary ════\n'
for lane in "${LANE_ORDER[@]}"; do
    lane_status=""
    lane_seconds=""
    # A missing result file must not abort the loop either: redirecting from one
    # is a hard error under `set -e`, and `read` reports EOF on an empty file.
    if [[ -r "$RESULT_DIR/$lane" ]]; then
        IFS=$'\t' read -r lane_status lane_seconds <"$RESULT_DIR/$lane" || true
    fi
    if [[ "$lane_status" == "0" ]]; then
        verdict="ok"
    elif [[ "$lane_status" == "skipped" ]]; then
        # Not a failure of its own: the lane that tripped --fail-fast is the one
        # that sets the exit status, and double-counting would hide it.
        verdict="skipped (--fail-fast)"
    elif [[ -z "$lane_status" ]]; then
        # Unrecorded is failed: the lane never reached the line that writes its
        # result, so treating it as anything else would report a green gate for
        # a run that died partway.
        verdict="FAILED (no result recorded)"
        exit_status=1
    else
        verdict="FAILED (exit $lane_status)"
        exit_status=1
    fi
    printf '  %-16s %8s  %s\n' "$lane" "$(format_duration "$lane_seconds")" "$verdict"
done
printf '  %-16s %8s\n' "TOTAL" "$(format_duration "$GATE_SECONDS")"
[[ "$SMOKE" == "1" ]] && printf '  (VERIFY_SMOKE=1 — token selections, NOT a gate run)\n'

exit "$exit_status"
