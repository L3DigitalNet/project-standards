from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

import yaml

_ROOT = Path(__file__).resolve().parent.parent


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
        'uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"',
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
    wheel_extract_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Extract candidate wheel"
    )
    ordinary_test_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Ordinary tests with coverage"
    )

    assert setup_node_index < npm_ci_index < wheel_extract_index < ordinary_test_index


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
