from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "lint-markdown.yml"


def _load() -> dict[Any, Any]:
    return cast("dict[Any, Any]", yaml.safe_load(_WF.read_text(encoding="utf-8")))


def test_lint_workflow_is_reusable_with_boolean_markdownlint_input() -> None:
    inputs = _load()[True]["workflow_call"]["inputs"]

    assert inputs["markdownlint"] == {
        "description": "Run the Markdown lint check.",
        "required": False,
        "type": "boolean",
        "default": True,
    }


def test_lint_optout_is_job_level_and_coercion_safe() -> None:
    job = _load()["jobs"]["lint"]

    assert job["if"].strip() == "${{ format('{0}', inputs.markdownlint) != 'false' }}"


def test_lint_workflow_keeps_direct_and_reusable_triggers() -> None:
    triggers = _load()[True]

    assert "push" in triggers
    assert "pull_request" in triggers
    assert "workflow_call" in triggers


def test_lint_workflow_uses_action_v24() -> None:
    steps = _load()["jobs"]["lint"]["steps"]

    assert any(step.get("uses") == "DavidAnson/markdownlint-cli2-action@v24" for step in steps)


@pytest.mark.parametrize(
    ("input_value", "expected_run"),
    [
        (None, True),
        (True, True),
        (False, False),
    ],
)
def test_lint_optout_truth_table(input_value: object, expected_run: bool) -> None:
    rendered = "" if input_value is None else str(input_value).lower()

    assert (rendered != "false") is expected_run
