from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_EXTERNAL_ACTIONS = {
    "actions/checkout": ("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7"),
    "actions/setup-node": ("249970729cb0ef3589644e2896645e5dc5ba9c38", "v6"),
    "actions/setup-python": ("ece7cb06caefa5fff74198d8649806c4678c61a1", "v6"),
    "astral-sh/setup-uv": ("11f9893b081a58869d3b5fccaea48c9e9e46f990", "v8.3.2"),
    "DavidAnson/markdownlint-cli2-action": ("6bf21b07787794f89a243495939cd651942aeabe", "v24"),
}
_CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
_SETUP_NODE = "actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38"
_SETUP_UV = "astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990"
_CURRENT_V2_CHECKOUT = "actions/checkout@v7"
_CURRENT_V2_SETUP_NODE = "actions/setup-node@v6"
_LEGACY_CLI_DIGEST = "3059b84e8730775e021b3e9ce14e819ef4bd0084fbd5ac996d811ede99e5baf8"
_LEGACY_PYTHON_DIGEST = "16a65f2bdc06adfc814786201ec32937bad4b5930cbf2bf722489007150c933e"

_ROOT_WORKFLOWS = (
    ".github/workflows/check.yml",
    ".github/workflows/coherence.yml",
    ".github/workflows/format.yml",
    ".github/workflows/lint-markdown.yml",
    ".github/workflows/validate-markdown-frontmatter.yml",
    ".github/workflows/validate-specs.yml",
    ".github/workflows/validate-standards-graph.yml",
)
_UV_ROOT_WORKFLOWS = (
    ".github/workflows/check.yml",
    ".github/workflows/coherence.yml",
    ".github/workflows/validate-markdown-frontmatter.yml",
    ".github/workflows/validate-specs.yml",
    ".github/workflows/validate-standards-graph.yml",
)
_CURRENT_V2_WORKFLOWS = (
    "standards/markdown-tooling/versions/1.2/resources/self-host-format.yml",
    "standards/markdown-tooling/versions/1.2/resources/self-host-lint-markdown.yml",
    "standards/markdown-frontmatter/versions/1.2/resources/self-host-validate-markdown-frontmatter.yml",
    "standards/project-spec/versions/1.1/resources/self-host-validate-specs.yml",
    "standards/python-tooling/versions/1.1/resources/check.yml",
)
_LEGACY_CLI_WORKFLOWS = (
    "standards/cli-documentation/versions/1.1/resources/legacy-cli-docs-check.yml",
    "standards/cli-documentation/templates/cli-docs-check.yml",
    "src/project_standards/bundles/cli-documentation/cli-docs-check.yml",
)
_EXTERNAL_ACTION_USE = re.compile(
    r"^\s*(?:-\s+)?uses:\s+(?P<action>[^@\s]+)@(?P<ref>[^\s#]+)\s*(?:#\s*(?P<version>\S.*))?$",
    re.MULTILINE,
)


def _load(relative_path: str) -> dict[Any, Any]:
    return cast(
        "dict[Any, Any]",
        yaml.safe_load((_ROOT / relative_path).read_text(encoding="utf-8")),
    )


def _uses(relative_path: str) -> list[dict[Any, Any]]:
    workflow = _load(relative_path)
    return [step for job in workflow["jobs"].values() for step in job["steps"] if "uses" in step]


def test_live_workflow_external_actions_are_sha_pinned_with_version_comments() -> None:
    for workflow in sorted((_ROOT / ".github" / "workflows").glob("*.yml")):
        for match in _EXTERNAL_ACTION_USE.finditer(workflow.read_text(encoding="utf-8")):
            action = match["action"]
            if action.startswith("./"):
                continue

            expected_ref, expected_version = _EXTERNAL_ACTIONS[action]
            assert match["ref"] == expected_ref, f"{workflow}: {action}"
            assert match["version"] == expected_version, f"{workflow}: {action}"


def test_dependabot_updates_actions_and_lockfile_backed_node_dependencies() -> None:
    config = cast(
        "dict[str, object]",
        yaml.safe_load((_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")),
    )
    updates = cast("list[dict[str, object]]", config["updates"])

    assert updates == [
        {
            "package-ecosystem": "github-actions",
            "directory": "/",
            "schedule": {"interval": "weekly"},
        },
        {
            "package-ecosystem": "npm",
            "directory": "/",
            "schedule": {"interval": "weekly"},
        },
    ]


@pytest.mark.parametrize("relative_path", _ROOT_WORKFLOWS)
def test_live_root_workflows_use_reviewed_checkout_pin(relative_path: str) -> None:
    checkout = [
        step["uses"]
        for step in _uses(relative_path)
        if step["uses"].startswith("actions/checkout@")
    ]

    assert checkout == [_CHECKOUT]


@pytest.mark.parametrize("relative_path", _UV_ROOT_WORKFLOWS)
def test_live_root_workflows_use_reviewed_setup_uv_pin(relative_path: str) -> None:
    setup_uv = [
        step["uses"]
        for step in _uses(relative_path)
        if step["uses"].startswith("astral-sh/setup-uv@")
    ]

    assert setup_uv == [_SETUP_UV]


def test_live_node_workflows_use_node_24_generation_and_intended_cache_policy() -> None:
    format_setup = next(
        step
        for step in _uses(".github/workflows/format.yml")
        if step["uses"].startswith("actions/setup-node@")
    )
    coherence_setup = next(
        step
        for step in _uses(".github/workflows/coherence.yml")
        if step["uses"].startswith("actions/setup-node@")
    )

    assert format_setup == {
        "name": "Set up Node",
        "uses": _SETUP_NODE,
        "with": {"node-version": "24", "package-manager-cache": False},
    }
    assert coherence_setup["uses"] == _SETUP_NODE
    assert coherence_setup["with"] == {"node-version": "24", "cache": "npm"}


@pytest.mark.parametrize("relative_path", _CURRENT_V2_WORKFLOWS)
def test_current_v2_workflows_remain_at_checkout_v7(relative_path: str) -> None:
    checkout = [
        step["uses"]
        for step in _uses(relative_path)
        if step["uses"].startswith("actions/checkout@")
    ]

    assert checkout == [_CURRENT_V2_CHECKOUT]


def test_current_v2_workflows_use_reviewed_runtime_contracts() -> None:
    format_setup = next(
        step
        for step in _uses("standards/markdown-tooling/versions/1.2/resources/self-host-format.yml")
        if step["uses"].startswith("actions/setup-node@")
    )
    assert format_setup == {
        "name": "Set up Node",
        "uses": _CURRENT_V2_SETUP_NODE,
        "with": {"node-version": "24", "package-manager-cache": False},
    }

    for relative_path in (
        "standards/markdown-frontmatter/versions/1.2/resources/self-host-validate-markdown-frontmatter.yml",
        "standards/project-spec/versions/1.1/resources/self-host-validate-specs.yml",
        "standards/python-tooling/versions/1.1/resources/check.yml",
    ):
        setup_uv = [
            step["uses"]
            for step in _uses(relative_path)
            if step["uses"].startswith("astral-sh/setup-uv@")
        ]
        assert setup_uv == [_SETUP_UV]


@pytest.mark.parametrize("relative_path", _LEGACY_CLI_WORKFLOWS)
def test_registered_legacy_cli_workflow_bytes_remain_frozen(relative_path: str) -> None:
    content = (_ROOT / relative_path).read_bytes()

    assert hashlib.sha256(content).hexdigest() == _LEGACY_CLI_DIGEST
    assert b"actions/checkout@v6" in content
    assert b"astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39" in content


def test_registered_legacy_python_workflow_bytes_remain_frozen() -> None:
    content = (_ROOT / "src/project_standards/bundles/python-tooling/check.yml").read_bytes()

    assert hashlib.sha256(content).hexdigest() == _LEGACY_PYTHON_DIGEST
    assert b"actions/checkout@v6" in content
    assert b"astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39" in content
