from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_REPO = Path(__file__).resolve().parent.parent


# PyYAML parses the top-level `on:` key as boolean True, so workflow mappings
# cannot honestly be typed as string-keyed dictionaries.
def _load(name: str) -> dict[Any, Any]:
    return cast(
        "dict[Any, Any]",
        yaml.safe_load((_REPO / name).read_text(encoding="utf-8")),
    )


def _uses_steps(workflow: dict[Any, Any]) -> dict[str, dict[Any, Any]]:
    job = next(iter(workflow["jobs"].values()))
    return {step["uses"].split("@", 1)[0]: step for step in job["steps"] if "uses" in step}


def test_repository_graph_workflow_contract() -> None:
    workflow = _load(".github/workflows/validate-standards-graph.yml")
    reusable_gate = _load(".github/workflows/check.yml")
    triggers = workflow[True]

    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main", "testing"]
    assert all("paths" not in trigger for trigger in triggers.values() if isinstance(trigger, dict))

    job = workflow["jobs"]["standards-graph"]
    assert job["name"] == "Standards graph and catalog"
    commands = [step.get("run") for step in job["steps"]]
    assert "uv sync --locked --all-groups" in commands
    assert (
        "uv run project-standards standards validate-graph --root . --require-all-manifests"
    ) in commands
    assert "uv run project-standards standards render-catalog --root . --check" in commands
    baseline = next(step for step in job["steps"] if step.get("id") == "v2-baseline")
    assert baseline["shell"] == "bash"
    assert "git for-each-ref" in baseline["run"]
    assert "git ls-tree" in baseline["run"]
    assert 'git diff --quiet "$baseline" -- catalogs standards' in baseline["run"]
    assert 'baseline=""' in baseline["run"]
    release_gate = next(
        step for step in job["steps"] if step.get("name") == "Check released V2 payloads"
    )
    assert release_gate["if"] == "steps.v2-baseline.outputs.ref != ''"
    assert release_gate["run"] == (
        "uv run project-standards packages check-release --root . "
        '--baseline "${{ steps.v2-baseline.outputs.ref }}"'
    )

    actual = _uses_steps(workflow)
    expected = _uses_steps(reusable_gate)
    for action in ("actions/checkout", "actions/setup-python", "astral-sh/setup-uv"):
        assert actual[action]["uses"] == expected[action]["uses"]
    assert actual["actions/checkout"]["with"]["fetch-depth"] == 0
    assert (
        actual["astral-sh/setup-uv"]["with"]["version"]
        == expected["astral-sh/setup-uv"]["with"]["version"]
    )
