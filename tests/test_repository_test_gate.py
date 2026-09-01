from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import cast

import yaml

_ROOT = Path(__file__).resolve().parent.parent


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\nset -u\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def _gate_fixture(
    tmp_path: Path, *, wheel_count: int, stamp: bool = True
) -> tuple[Path, Path, dict[str, str]]:
    """Create a hermetic verify.sh root whose tools expose lane orchestration.

    ``stamp=False`` leaves the extracted runtime unstamped, which is how an
    extraction predating issue #136 presents itself.
    """
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    venv_bin = repo / ".venv" / "bin"
    node_bin = repo / "node_modules" / ".bin"
    wheel_runtime = repo / "build" / "wheel-runtime"
    wheel_dir = repo / "build" / "release-wheel"
    log = tmp_path / "tool-invocations.log"

    scripts.mkdir(parents=True)
    venv_bin.mkdir(parents=True)
    node_bin.mkdir(parents=True)
    wheel_runtime.mkdir(parents=True)
    wheel_dir.mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "project_standards").mkdir(parents=True)
    shutil.copy2(_ROOT / "scripts" / "verify.sh", scripts / "verify.sh")
    # The gate's preflight delegates the staleness check, so the fixture needs
    # the real stamp script rather than a stub: a stub would let the two drift
    # and this fixture would stop proving the preflight it exists to exercise.
    shutil.copy2(_ROOT / "scripts" / "wheel-runtime-stamp.sh", scripts / "wheel-runtime-stamp.sh")
    # Part of the content key, so it must exist before a stamp can be computed.
    (repo / "pyproject.toml").write_text('[project]\nname = "fixture"\n', encoding="utf-8")
    (repo / "src" / "project_standards" / "__init__.py").write_text("", encoding="utf-8")
    if stamp:
        subprocess.run(
            [str(scripts / "wheel-runtime-stamp.sh"), "write"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    for index in range(wheel_count):
        (wheel_dir / f"project_standards-{index}.whl").write_bytes(b"wheel")

    _write_executable(venv_bin / "python", f'exec "{sys.executable}" "$@"')
    for tool in ("basedpyright", "pip-audit"):
        _write_executable(
            venv_bin / tool,
            'printf "%s %s\\n" "${0##*/}" "$*" >> "$VERIFY_FAKE_LOG"',
        )
    _write_executable(
        venv_bin / "ruff",
        """printf "ruff %s\\n" "$*" >> "$VERIFY_FAKE_LOG"
if [[ "${VERIFY_ASSERT_FAST_START:-0}" == "1" && "$*" == "format --check ." ]]; then
    mkdir -p "$VERIFY_START_DIR/statics"
    until [[ -f "$VERIFY_RELEASE_FILE" ]]; do sleep 0.01; done
fi""",
    )
    _write_executable(
        venv_bin / "coverage",
        """printf "coverage %s\\n" "$*" >> "$VERIFY_FAKE_LOG"
if [[ "${VERIFY_ASSERT_FAST_START:-0}" == "1" && "$1" == "run" ]]; then
    mkdir -p "$VERIFY_START_DIR/ordinary"
    until [[ -f "$VERIFY_RELEASE_FILE" ]]; do sleep 0.01; done
fi
if [[ "${VERIFY_ASSERT_FAST_START:-0}" == "1" && "$1" == "combine" ]]; then
    touch "$VERIFY_COVERAGE_COMBINE_FILE"
fi
if [[ "$1" == "run" ]]; then
    exit "${VERIFY_ORDINARY_EXIT:-0}"
fi""",
    )
    for tool in ("prettier", "markdownlint-cli2"):
        _write_executable(
            node_bin / tool,
            'printf "%s %s\\n" "${0##*/}" "$*" >> "$VERIFY_FAKE_LOG"',
        )
    _write_executable(
        venv_bin / "pytest",
        """printf "pytest %s\\n" "$*" >> "$VERIFY_FAKE_LOG"
if [[ "$*" == *"-m compatibility"* ]]; then
    if [[ "${VERIFY_ASSERT_FAST_START:-0}" == "1" ]]; then
        mkdir -p "$VERIFY_START_DIR/compatibility"
        until [[ -f "$VERIFY_RELEASE_FILE" ]]; do sleep 0.01; done
    fi
    [[ "${PROJECT_STANDARDS_COMPATIBILITY_WHEEL:-}" == "$VERIFY_EXPECTED_WHEEL" ]] || exit 97
    exit "${VERIFY_COMPATIBILITY_EXIT:-0}"
fi
if [[ "${VERIFY_ASSERT_FAST_START:-0}" == "1" && "$*" == *"-m performance"* ]]; then
    touch "$VERIFY_PERFORMANCE_FILE"
fi""",
    )

    # Start from the caller's environment minus every `VERIFY_*` override: the gate
    # honours operator knobs such as `VERIFY_FULL_COMPAT_WORKERS`, and a release
    # train exporting one (lever A, docs/research/2026-09-01-release-train-wall-clock.md)
    # otherwise leaks into this fixture and moves the `-n` the lane-order test pins
    # (v5.28.0 battery, 2026-09-01). The fixture sets its own knobs below.
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("VERIFY_")
    } | {
        "VERIFY_FAKE_LOG": str(log),
        "VERIFY_SMOKE": "1",
        "VERIFY_TMP_PARENT": str(tmp_path),
        "VERIFY_EXPECTED_WHEEL": str((wheel_dir / "project_standards-0.whl").resolve()),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    return repo, log, environment


def _run_gate(
    repo: Path, environment: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo / "scripts" / "verify.sh"), *args],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _workflow_steps() -> list[dict[str, object]]:
    workflow = cast(
        "dict[str, object]",
        yaml.safe_load((_ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8")),
    )
    jobs = cast("dict[str, object]", workflow["jobs"])
    check = cast("dict[str, object]", jobs["check"])
    return cast("list[dict[str, object]]", check["steps"])


def test_repository_workflow_runs_direct_test_phases() -> None:
    steps = _workflow_steps()
    commands = [str(step["run"]) for step in steps if "run" in step]
    test_commands = [
        command for command in commands if "coverage" in command or "pytest" in command
    ]

    assert test_commands == [
        "uv run coverage erase",
        (
            "uv run coverage run --source=project_standards -m pytest "
            '-m "not performance and not compatibility" -n 4 --dist load --max-worker-restart=0'
        ),
        # xdist workers write their own `.coverage.*` files; without this the
        # report would only see the controller process.
        "uv run coverage combine",
        "uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0",
        "uv run pytest -m performance",
        "uv run coverage report",
    ]
    assert all("run_repository_tests" not in command for command in commands)
    assert all("release_replay" not in command for command in commands)


def test_repository_workflow_installs_node_dependencies_before_ordinary_tests() -> None:
    steps = _workflow_steps()
    setup_node_index = next(
        index
        for index, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    )
    npm_ci_index = next(index for index, step in enumerate(steps) if step.get("run") == "npm ci")
    npm_audit_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "npm audit --package-lock-only"
    )
    wheel_extract_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Extract candidate wheel"
    )
    ordinary_test_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Ordinary tests with coverage"
    )

    assert (
        setup_node_index
        < npm_ci_index
        < npm_audit_index
        < wheel_extract_index
        < ordinary_test_index
    )


def test_repository_workflow__candidate_wheel__reused_for_compatibility() -> None:
    steps = _workflow_steps()
    build_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Build candidate wheel"
    )
    select_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Select candidate wheel"
    )
    extract_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Extract candidate wheel"
    )
    compatibility_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Compatibility matrix"
    )
    commands = [str(step["run"]) for step in steps if "run" in step]

    assert build_index < select_index < extract_index < compatibility_index
    assert steps[select_index]["shell"] == "bash"
    assert steps[select_index]["run"] == (
        'mapfile -t candidate_wheels < <(find "${{ github.workspace }}/dist" '
        "-maxdepth 1 -type f -name 'project_standards-*.whl' -print)\n"
        'test "${#candidate_wheels[@]}" -eq 1\n'
        'candidate_wheel="$(realpath "${candidate_wheels[0]}")"\n'
        "printf 'PROJECT_STANDARDS_COMPATIBILITY_WHEEL=%s\\n' "
        '"$candidate_wheel" >> "$GITHUB_ENV"\n'
    )
    assert steps[extract_index]["run"] == (
        'python -m zipfile -e "$PROJECT_STANDARDS_COMPATIBILITY_WHEEL" build/wheel-runtime'
    )
    assert [command for command in commands if "uv build" in command] == [
        "uv build --wheel --out-dir dist"
    ]


def test_repository_configuration_keeps_only_retained_test_groups() -> None:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = cast("list[str]", project["dependency-groups"]["dev"])
    pytest_config = cast("dict[str, object]", project["tool"]["pytest"]["ini_options"])
    markers = cast("list[str]", pytest_config["markers"])
    coverage = cast("dict[str, object]", project["tool"]["coverage"])
    coverage_run = cast("dict[str, object]", coverage["run"])

    assert "pytest-xdist>=3.8" in dev_dependencies
    assert any(marker.startswith("compatibility:") for marker in markers)
    assert any(marker.startswith("performance:") for marker in markers)
    assert not any(marker.startswith("release_replay:") for marker in markers)
    assert coverage_run == {"branch": True, "source": ["src"]}
    assert "paths" not in coverage


def test_verify_gate__zero_candidate_wheels__fails_before_lanes(tmp_path: Path) -> None:
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=0)

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    assert "expected exactly one candidate wheel" in completed.stderr
    assert not log.exists()


def test_verify_gate__multiple_candidate_wheels__fails_before_lanes(tmp_path: Path) -> None:
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=2)

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    assert "expected exactly one candidate wheel" in completed.stderr
    assert not log.exists()


def test_verify_gate__unstamped_runtime__fails_before_lanes(tmp_path: Path) -> None:
    """An extraction predating the stamp is stale, never assumed current."""
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1, stamp=False)

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    assert "carries no stamp" in completed.stderr
    assert not log.exists()


def test_verify_gate__stale_runtime__fails_before_lanes_naming_staleness(tmp_path: Path) -> None:
    """A source edit after extraction is refused by its actual cause.

    Without this the same state reaches the lanes and surfaces as
    ``CP-RESOLUTION: unavailable``, which names resolution rather than the
    out-of-date runtime that produced it.
    """
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)
    (repo / "src" / "project_standards" / "__init__.py").write_text("# edited\n", encoding="utf-8")

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    assert "is STALE" in completed.stderr
    assert "scripts/bootstrap-worktree.sh" in completed.stderr
    assert not log.exists()


def test_verify_gate__restored_content__is_current_again(tmp_path: Path) -> None:
    """The key is content, not mtime: a reverted edit needs no rebuild."""
    repo, _log, environment = _gate_fixture(tmp_path, wheel_count=1)
    source = repo / "src" / "project_standards" / "__init__.py"
    original = source.read_text(encoding="utf-8")
    source.write_text("# edited\n", encoding="utf-8")
    source.write_text(original, encoding="utf-8")

    completed = subprocess.run(
        [str(repo / "scripts" / "wheel-runtime-stamp.sh"), "check"],
        cwd=repo,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_verify_gate__tmp_parent__requires_smoke_mode(tmp_path: Path) -> None:
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)
    environment["VERIFY_SMOKE"] = "0"

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    assert "VERIFY_TMP_PARENT is test-only and requires VERIFY_SMOKE=1" in completed.stderr
    assert not log.exists()


def test_verify_gate__one_candidate_wheel__exports_it_and_reports_aggregate_failure(
    tmp_path: Path,
) -> None:
    repo, _log, environment = _gate_fixture(tmp_path, wheel_count=1)
    environment["VERIFY_COMPATIBILITY_EXIT"] = "17"

    completed = _run_gate(repo, environment)

    assert completed.returncode == 1
    wheel = environment["VERIFY_EXPECTED_WHEEL"]
    assert f"verify: PROJECT_STANDARDS_COMPATIBILITY_WHEEL={wheel}" in completed.stdout
    assert "compatibility" in completed.stdout
    assert "FAILED (exit 17)" in completed.stdout
    summary = completed.stdout.index("════ summary ════")
    assert completed.stdout.index("════ statics ════") < summary
    assert completed.stdout.index("════ ordinary ════") < summary
    assert completed.stdout.index("════ compatibility ════") < summary
    assert completed.stdout.index("════ performance ════") < summary
    assert completed.stdout.index("════ coverage-combine ════") < summary
    assert completed.stdout.index("════ coverage-report ════") < summary


def test_verify_gate__fast_mode__starts_parallel_lanes_before_serial_tail(tmp_path: Path) -> None:
    repo, _log, environment = _gate_fixture(tmp_path, wheel_count=1)
    start_dir = tmp_path / "starts"
    release_file = tmp_path / "release-parallel-lanes"
    performance_file = tmp_path / "performance-started"
    coverage_combine_file = tmp_path / "coverage-combine-started"
    environment |= {
        "VERIFY_ASSERT_FAST_START": "1",
        "VERIFY_START_DIR": str(start_dir),
        "VERIFY_RELEASE_FILE": str(release_file),
        "VERIFY_PERFORMANCE_FILE": str(performance_file),
        "VERIFY_COVERAGE_COMBINE_FILE": str(coverage_combine_file),
    }
    process = subprocess.Popen(
        [str(repo / "scripts" / "verify.sh")],
        cwd=repo,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    expected_starts = {"statics", "ordinary", "compatibility"}
    deadline = time.monotonic() + 5
    try:
        while (
            {path.name for path in start_dir.glob("*")} != expected_starts
            and process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)

        assert process.poll() is None
        assert {path.name for path in start_dir.glob("*")} == expected_starts
        assert not performance_file.exists()
        assert not coverage_combine_file.exists()
    finally:
        release_file.touch()

    stdout, stderr = process.communicate(timeout=5)
    assert process.returncode == 0, stdout + stderr
    assert performance_file.exists()
    assert coverage_combine_file.exists()


def test_verify_gate__full_mode__preserves_serial_lane_order(tmp_path: Path) -> None:
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)

    completed = _run_gate(repo, environment, "--full")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    invocations = log.read_text(encoding="utf-8").splitlines()
    assert invocations[0] == "coverage erase"
    assert invocations[1] == "ruff format --check ."
    assert invocations[2] == "ruff check ."
    assert invocations[3].startswith(
        "coverage run --source=project_standards -m pytest -m not performance and not compatibility"
    )
    assert invocations[4].startswith("pytest -m compatibility -n 16")
    assert invocations[5].startswith("pytest -m performance")
    assert invocations[6] == "coverage report --fail-under=0"


def test_verify_gate__full_mode__red_ordinary_lane__skips_the_later_lanes(
    tmp_path: Path,
) -> None:
    """--full is fail-fast by default, and a cut lane is reported, not dropped.

    The compatibility lane is the expensive one: on the 2026-09-01 train it ran
    for roughly 35 minutes after the ordinary lane had already gone red (#236 C6).
    """
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)
    environment["VERIFY_ORDINARY_EXIT"] = "13"

    completed = _run_gate(repo, environment, "--full")

    assert completed.returncode == 1
    invocations = log.read_text(encoding="utf-8").splitlines()
    assert not any(invocation.startswith("pytest -m compatibility") for invocation in invocations)
    assert not any(invocation.startswith("pytest -m performance") for invocation in invocations)
    summary = completed.stdout[completed.stdout.index("════ summary ════") :]
    assert "ordinary" in summary
    assert "FAILED (exit 13)" in summary
    for lane in ("compatibility", "performance", "coverage-report"):
        assert lane in summary
        line = next(row for row in summary.splitlines() if row.strip().startswith(lane))
        assert "skipped (--fail-fast)" in line


def test_verify_gate__full_mode__keep_going__runs_every_lane_after_a_red(
    tmp_path: Path,
) -> None:
    """--keep-going preserves the pre-#236 behaviour of running every lane."""
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)
    environment["VERIFY_ORDINARY_EXIT"] = "13"

    completed = _run_gate(repo, environment, "--full", "--keep-going")

    assert completed.returncode == 1
    invocations = log.read_text(encoding="utf-8").splitlines()
    assert any(invocation.startswith("pytest -m compatibility") for invocation in invocations)
    assert any(invocation.startswith("pytest -m performance") for invocation in invocations)
    summary = completed.stdout[completed.stdout.index("════ summary ════") :]
    assert "FAILED (exit 13)" in summary
    assert "skipped" not in summary


def test_verify_gate__fast_mode__fail_fast__cuts_the_serial_tail(tmp_path: Path) -> None:
    """The fast gate keeps run-every-lane by default; --fail-fast opts in.

    Its three lanes are already running when the first red appears, so the cut
    can only begin at the serial tail.
    """
    repo, log, environment = _gate_fixture(tmp_path, wheel_count=1)
    environment["VERIFY_ORDINARY_EXIT"] = "13"

    kept_going = _run_gate(repo, environment)
    fail_fast = _run_gate(repo, environment, "--fail-fast")

    invocations = log.read_text(encoding="utf-8").splitlines()
    performance_runs = [
        invocation for invocation in invocations if invocation.startswith("pytest -m performance")
    ]
    assert kept_going.returncode == 1
    assert fail_fast.returncode == 1
    # Both runs share one log; only the default run reaches the performance lane.
    assert len(performance_runs) == 1
    assert "skipped" not in kept_going.stdout[kept_going.stdout.index("════ summary ════") :]
    fail_fast_summary = fail_fast.stdout[fail_fast.stdout.index("════ summary ════") :]
    for lane in ("performance", "coverage-combine", "coverage-report"):
        line = next(row for row in fail_fast_summary.splitlines() if row.strip().startswith(lane))
        assert "skipped (--fail-fast)" in line
    # The concurrently started lanes are never cut: they are already running.
    for lane in ("statics", "ordinary", "compatibility"):
        line = next(row for row in fail_fast_summary.splitlines() if row.strip().startswith(lane))
        assert "skipped" not in line
