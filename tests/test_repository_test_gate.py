from __future__ import annotations

import importlib.util
import os
import tomllib
import zipfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _ROOT / "scripts/run_repository_tests.py"


def _load_gate() -> ModuleType:
    assert _SCRIPT.is_file(), "repository test gate script is missing"
    spec = importlib.util.spec_from_file_location("repository_test_gate", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_candidate_wheel(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("project_standards/catalogs/5.toml", "catalog = 5\n")
    return path


def test_gate_separates_covered_phases_before_one_combine() -> None:
    gate = _load_gate()

    commands = cast(
        "tuple[tuple[str, ...], ...]",
        gate.test_commands(workers=4),
    )

    assert commands == (
        ("uv", "run", "coverage", "erase"),
        (
            "uv",
            "run",
            "coverage",
            "run",
            "--parallel-mode",
            "--source=project_standards",
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
            "--source=project_standards",
            "-m",
            "pytest",
            "-m",
            "compatibility",
            "-n",
            "4",
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
            "--source=project_standards",
            "-m",
            "pytest",
            "-m",
            "release_replay",
        ),
        ("uv", "run", "coverage", "combine"),
        ("uv", "run", "coverage", "report"),
        ("uv", "run", "pytest", "-m", "performance"),
    )


def test_gate_builds_one_wheel_before_running_test_phases(tmp_path: Path) -> None:
    gate = _load_gate()
    events: list[tuple[str, object]] = []
    wheel = _write_candidate_wheel(tmp_path / "project_standards-5.0.0-py3-none-any.whl")

    def build(_scratch: Path) -> Path:
        events.append(("build", wheel))
        return wheel

    def execute(command: Sequence[str], environment: Mapping[str, str]) -> int:
        events.append(("command", tuple(command)))
        assert environment["PROJECT_STANDARDS_COMPATIBILITY_WHEEL"] == str(wheel)
        return 0

    result = gate.run_gate(
        tmp_path,
        workers=4,
        coverage_root=tmp_path,
        build_wheel=cast("Callable[[Path], Path]", build),
        execute=cast("Callable[[Sequence[str], Mapping[str, str]], int]", execute),
    )

    assert result == 0
    assert events[0] == ("build", wheel)
    assert [event for event in events if event[0] == "build"] == [("build", wheel)]
    assert len([event for event in events if event[0] == "command"]) == 7


def test_gate__candidate_wheel__is_runtime_authority_for_every_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate()
    wheel = _write_candidate_wheel(tmp_path / "project_standards-5.0.0-py3-none-any.whl")
    environments: list[Mapping[str, str]] = []
    monkeypatch.setenv("PYTHONPATH", "/ambient/source-checkout")

    def execute(_command: Sequence[str], environment: Mapping[str, str]) -> int:
        environments.append(environment)
        return 0

    def build(_scratch: Path) -> Path:
        return wheel

    result = gate.run_gate(
        tmp_path,
        workers=4,
        coverage_root=tmp_path,
        build_wheel=build,
        execute=cast("Callable[[Sequence[str], Mapping[str, str]], int]", execute),
    )

    assert result == 0
    assert len(environments) == 7
    runtime_roots = {environment["PYTHONPATH"] for environment in environments}
    assert len(runtime_roots) == 1
    runtime_root = Path(runtime_roots.pop())
    assert runtime_root == tmp_path / "installed"
    assert (runtime_root / "project_standards/catalogs/5.toml").read_text(
        encoding="utf-8"
    ) == "catalog = 5\n"
    assert all(
        environment["PROJECT_STANDARDS_COMPATIBILITY_WHEEL"] == str(wheel)
        for environment in environments
    )


def test_gate_removes_coverage_data_when_a_phase_fails(tmp_path: Path) -> None:
    gate = _load_gate()
    wheel = _write_candidate_wheel(tmp_path / "project_standards-5.0.0-py3-none-any.whl")
    combined = tmp_path / ".coverage"
    shard = tmp_path / ".coverage.worker"
    combined.touch()
    shard.touch()

    def execute(_command: Sequence[str], _environment: Mapping[str, str]) -> int:
        return 1

    def build(_scratch: Path) -> Path:
        return wheel

    result = gate.run_gate(
        tmp_path,
        workers=4,
        coverage_root=tmp_path,
        build_wheel=build,
        execute=cast("Callable[[Sequence[str], Mapping[str, str]], int]", execute),
    )

    assert result == 1
    assert not combined.exists()
    assert not shard.exists()


def test_gate_configuration_declares_parallelism_without_global_xdist_addopts() -> None:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = project["dependency-groups"]["dev"]
    pytest_config = project["tool"]["pytest"]["ini_options"]
    coverage_run = project["tool"]["coverage"]["run"]
    coverage_paths = project["tool"]["coverage"]["paths"]

    assert "pytest-xdist>=3.8" in dev_dependencies
    assert coverage_run["parallel"] is True
    assert coverage_run["patch"] == ["subprocess"]
    assert coverage_run["source"] == ["src"]
    assert coverage_paths["source"] == [
        "src/project_standards",
        "*/project_standards",
    ]
    assert any(marker.startswith("compatibility:") for marker in pytest_config["markers"])
    assert any(marker.startswith("release_replay:") for marker in pytest_config["markers"])
    assert not any(argument.startswith("-n") for argument in pytest_config["addopts"])


def test_repository_workflow_delegates_all_test_phases_to_the_gate() -> None:
    workflow = yaml.safe_load((_ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["check"]["steps"]
    test_steps = [step for step in steps if step.get("name") == "Test, coverage, and performance"]

    assert test_steps == [
        {
            "name": "Test, coverage, and performance",
            "env": {"PROJECT_STANDARDS_TEST_WORKERS": "4"},
            "run": "uv run python scripts/run_repository_tests.py",
        }
    ]
    assert not any(
        "pytest" in str(step.get("run", "")) or "coverage report" in str(step.get("run", ""))
        for step in steps
        if step not in test_steps
    )


def test_repository_workflow_installs_node_dependencies_before_the_test_gate() -> None:
    workflow = yaml.safe_load((_ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["check"]["steps"]
    setup_node_index = next(
        index
        for index, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/setup-node@")
    )
    npm_ci_index = next(index for index, step in enumerate(steps) if step.get("run") == "npm ci")
    test_gate_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Test, coverage, and performance"
    )

    assert setup_node_index < npm_ci_index < test_gate_index


def test_worker_count_uses_explicit_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate()
    monkeypatch.setenv("PROJECT_STANDARDS_TEST_WORKERS", "3")

    assert gate.configured_workers(os.environ) == 3
