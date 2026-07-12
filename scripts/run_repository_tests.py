"""Run repository tests in coverage-safe serial and parallel phases.

Only the isolated source/wheel compatibility matrix uses pytest-xdist. Ordinary
tests and release replay stay serial, and performance thresholds run without
coverage or worker contention.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_WORKER_ENV = "PROJECT_STANDARDS_TEST_WORKERS"
_WHEEL_ENV = "PROJECT_STANDARDS_COMPATIBILITY_WHEEL"
_DEFAULT_WORKERS = 4

BuildWheel = Callable[[Path], Path]
Execute = Callable[[Sequence[str], Mapping[str, str]], int]


def configured_workers(environment: Mapping[str, str]) -> int:
    """Return the explicit positive worker count selected for the matrix phase."""
    raw = environment.get(_WORKER_ENV, str(_DEFAULT_WORKERS))
    try:
        workers = int(raw)
    except ValueError as exc:
        raise ValueError(f"{_WORKER_ENV} must be a positive integer") from exc
    if workers < 1:
        raise ValueError(f"{_WORKER_ENV} must be a positive integer")
    return workers


def test_commands(*, workers: int) -> tuple[tuple[str, ...], ...]:
    """Return the ordered repository test phases for one worker count."""
    return (
        ("uv", "run", "coverage", "erase"),
        (
            "uv",
            "run",
            "coverage",
            "run",
            "--parallel-mode",
            "-m",
            "pytest",
            "-m",
            "not performance and not compatibility and not release_replay",
        ),
        (
            "uv",
            "run",
            "coverage",
            "run",
            "--parallel-mode",
            "-m",
            "pytest",
            "-m",
            "compatibility",
            "-n",
            str(workers),
            "--dist",
            "load",
            "--max-worker-restart=0",
        ),
        (
            "uv",
            "run",
            "coverage",
            "run",
            "--parallel-mode",
            "-m",
            "pytest",
            "-m",
            "release_replay",
        ),
        ("uv", "run", "coverage", "combine"),
        ("uv", "run", "coverage", "report"),
        ("uv", "run", "pytest", "-m", "performance"),
    )


def _build_compatibility_wheel(scratch: Path) -> Path:
    output = scratch / "dist"
    subprocess.run(
        ["uv", "build", "--offline", "--wheel", "--out-dir", str(output)],
        cwd=_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = tuple(output.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"compatibility build produced {len(wheels)} wheels")
    return wheels[0].resolve()


def _execute(command: Sequence[str], environment: Mapping[str, str]) -> int:
    print(f"\n$ {' '.join(command)}", flush=True)
    completed = subprocess.run(
        command,
        cwd=_ROOT,
        env=dict(environment),
        check=False,
    )
    return completed.returncode


def _remove_coverage_data(root: Path) -> None:
    """Remove combined and parallel coverage data without matching config files."""
    for path in (root / ".coverage", *root.glob(".coverage.*")):
        path.unlink(missing_ok=True)


def run_gate(
    scratch: Path,
    *,
    workers: int,
    coverage_root: Path,
    build_wheel: BuildWheel = _build_compatibility_wheel,
    execute: Execute = _execute,
) -> int:
    """Build one shared wheel, then stop at the first failing test phase."""
    _remove_coverage_data(coverage_root)
    try:
        wheel = build_wheel(scratch)
        environment = {**os.environ, _WHEEL_ENV: str(wheel)}
        for command in test_commands(workers=workers):
            if return_code := execute(command, environment):
                return return_code
        return 0
    finally:
        # A failed covered phase exits before `coverage combine`; always remove
        # its process shards so the repository stays clean between gate runs.
        _remove_coverage_data(coverage_root)


def main() -> int:
    """Run the repository test gate with a bounded explicit worker count."""
    try:
        workers = configured_workers(os.environ)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="project-standards-tests-") as temporary:
        return run_gate(Path(temporary), workers=workers, coverage_root=_ROOT)


if __name__ == "__main__":
    sys.exit(main())
