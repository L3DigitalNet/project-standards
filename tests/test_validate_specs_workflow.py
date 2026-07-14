from __future__ import annotations

from pathlib import Path

import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "validate-specs.yml"
_SELF_HOST_WF = (
    Path(__file__).resolve().parent.parent
    / "standards/project-spec/versions/1.1/resources/self-host-validate-specs.yml"
)


def test_workflow_exposes_workflow_call_with_ref_and_strict_lint() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    call = data[True]["workflow_call"]
    assert set(call["inputs"]) == {"standards-ref", "strict-lint"}
    assert call["inputs"]["standards-ref"]["default"] == "v5"
    assert call["inputs"]["strict-lint"]["default"] is True


def test_workflow_triggers_on_v5_and_transitional_dogfood_config() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    for event in ("push", "pull_request"):
        paths = data[True][event]["paths"]
        assert ".standards/config.toml" in paths
        assert ".project-standards.yml" in paths


def test_workflow_has_self_repo_and_consumer_branches() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    job = data["jobs"]["validate-specs"]
    text = _WF.read_text(encoding="utf-8")

    assert "env" not in job
    assert "uv sync --dev" in text
    assert "uv run project-standards spec validate" in text
    assert "uv tool install" in text


def test_direct_events_leave_config_selection_to_the_cli() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    steps = data["jobs"]["validate-specs"]["steps"]
    commands = [
        str(step.get("run", ""))
        for step in steps
        if "spec validate" in str(step.get("run", "")) or "spec lint" in str(step.get("run", ""))
    ]

    assert commands
    assert all("--config" not in command for command in commands)
    assert all("config_args" not in command for command in commands)
    assert all("PROJECT_STANDARDS_SPEC_CONFIG" not in command for command in commands)


def test_self_repo_steps_do_not_install_published_tag() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    for step in data["jobs"]["validate-specs"]["steps"]:
        if step.get("if", "").strip() == "github.repository == 'L3DigitalNet/project-standards'":
            assert "uv tool install" not in step.get("run", "")


def test_consumer_install_treats_the_requested_ref_as_data() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    step = next(
        item
        for item in data["jobs"]["validate-specs"]["steps"]
        if item.get("name") == "Install (consuming repo)"
    )

    assert step["env"] == {
        "PROJECT_STANDARDS_REF": (
            "${{ github.event_name == 'workflow_call' && inputs.standards-ref || 'v5' }}"
        )
    }
    assert "${{ inputs.standards-ref }}" not in step["run"]
    assert step["run"] == (
        'uv tool install "git+https://github.com/'
        'L3DigitalNet/project-standards@${PROJECT_STANDARDS_REF}"'
    )


def test_direct_events_use_published_ref_and_run_strict_lint() -> None:
    for workflow in (_WF, _SELF_HOST_WF):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        steps = data["jobs"]["validate-specs"]["steps"]
        install = next(item for item in steps if item.get("name") == "Install (consuming repo)")
        lint_steps = [item for item in steps if "strict" in str(item.get("name", "")).lower()]

        assert install["env"] == {
            "PROJECT_STANDARDS_REF": (
                "${{ github.event_name == 'workflow_call' && inputs.standards-ref || 'v5' }}"
            )
        }
        assert len(lint_steps) == 2
        assert all(
            "github.event_name != 'workflow_call' || inputs.strict-lint" in str(step["if"])
            for step in lint_steps
        )


def test_workflow_does_not_parse_legacy_yaml_to_decide_provider_execution() -> None:
    data = yaml.safe_load(_WF.read_text(encoding="utf-8"))
    scripts = [str(step.get("run", "")) for step in data["jobs"]["validate-specs"]["steps"]]

    assert not any("grep" in script or "^spec:" in script for script in scripts)
    assert any("project-standards spec validate" in script for script in scripts)
    assert all(".project-standards.yml" not in script for script in scripts)
