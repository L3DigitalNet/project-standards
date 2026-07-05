from __future__ import annotations

from pathlib import Path

import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "validate-specs.yml"


def test_workflow_exposes_workflow_call_with_config_and_ref() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    call = data[True]["workflow_call"]
    assert set(call["inputs"]) >= {"config-path", "standards-ref", "strict-lint"}


def test_workflow_has_self_repo_and_consumer_branches() -> None:
    text = _WF.read_text(encoding="utf-8")
    assert "uv sync --dev" in text
    assert "uv run project-standards spec validate" in text
    assert "uv tool install" in text


def test_self_repo_steps_do_not_install_published_tag() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    for step in data["jobs"]["validate-specs"]["steps"]:
        if step.get("if", "").strip() == "github.repository == 'L3DigitalNet/project-standards'":
            assert "uv tool install" not in step.get("run", "")
