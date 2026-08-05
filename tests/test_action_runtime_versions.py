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
    "actions/setup-node": ("820762786026740c76f36085b0efc47a31fe5020", "v7.0.0"),
    "actions/setup-go": ("924ae3a1cded613372ab5595356fb5720e22ba16", "v6"),
    "actions/setup-python": ("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0"),
    "astral-sh/setup-uv": ("c771a70e6277c0a99b617c7a806ffedaca235ff9", "v9.0.0"),
    "DavidAnson/markdownlint-cli2-action": ("6bf21b07787794f89a243495939cd651942aeabe", "v24"),
}
# Transitional map for the v5.15.0 -> v5.16.0 window: these root workflows are
# installed payload resources whose released bytes still carry the previous
# reviewed pins, and CP-MODIFIED-MANAGED forbids advancing the installed copies
# ahead of their packages. They converge to _EXTERNAL_ACTIONS when the v5.16.0
# release-prep reconcile re-renders the managed workflows from the
# markdown-tooling 1.13, markdown-frontmatter 1.9, and project-spec 1.7
# payloads; delete this map and its lookups in that same change.
_RELEASED_PAYLOAD_PINS = {
    ("format.yml", "actions/setup-node"): ("249970729cb0ef3589644e2896645e5dc5ba9c38", "v6"),
    ("validate-markdown-frontmatter.yml", "astral-sh/setup-uv"): (
        "11f9893b081a58869d3b5fccaea48c9e9e46f990",
        "v8.3.2",
    ),
    ("validate-specs.yml", "astral-sh/setup-uv"): (
        "11f9893b081a58869d3b5fccaea48c9e9e46f990",
        "v8.3.2",
    ),
}
_CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
_SETUP_NODE = "actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38"
_SETUP_NODE_CURRENT = "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020"
_SETUP_UV = "astral-sh/setup-uv@11f9893b081a58869d3b5fccaea48c9e9e46f990"
_SETUP_UV_CURRENT = "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9"
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

            expected_ref, expected_version = _RELEASED_PAYLOAD_PINS.get(
                (workflow.name, action), _EXTERNAL_ACTIONS[action]
            )
            assert match["ref"] == expected_ref, f"{workflow}: {action}"
            assert match["version"] == expected_version, f"{workflow}: {action}"


def test_dependabot_version_updates_stay_disabled() -> None:
    """Dependabot version updates are off by decision; re-adding the config is a regression.

    This repository is a standards *producer*. Four root workflows are installed payload
    resources byte-locked to published package versions, and the external action pins plus
    the Node tool pins are reviewed gates (`_EXTERNAL_ACTIONS`, `tests/coherence/test_pins.py`).
    Dependabot models none of that, and fails two distinct ways. Against a payload-managed
    workflow it rewrites the *installed* file rather than the canonical payload under
    `standards/**`, tripping CP-MODIFIED-MANAGED (#33, #110). Against the Node deps it moves a
    version this repository documents behaviorally in shipped prose, tripping the coherence
    pins (#112, #113). Neither is mergeable without the payload work Dependabot cannot do.

    Scoping Dependabot to unmanaged paths was rejected: the ignore list would have to track
    which workflows are payload-managed, and that set changes whenever a package claims or
    relinquishes a path — a second source of truth that would silently rot against the lock.

    Dependency currency is not abandoned, it moves to the payload cycle, where a pin bump is
    reviewed alongside the prose that documents its behavior. Dependabot *alerts* remain
    enabled at the repository level; they raise no pull requests and are unaffected.
    """
    assert not (_ROOT / ".github" / "dependabot.yml").exists()


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

    name = relative_path.rsplit("/", 1)[-1]
    expected = (
        _SETUP_UV if (name, "astral-sh/setup-uv") in _RELEASED_PAYLOAD_PINS else _SETUP_UV_CURRENT
    )
    assert setup_uv == [expected]


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

    # format.yml stays on _SETUP_NODE until the release-prep reconcile; see
    # _RELEASED_PAYLOAD_PINS.
    assert format_setup == {
        "name": "Set up Node",
        "uses": _SETUP_NODE,
        "with": {"node-version": "24", "package-manager-cache": False},
    }
    assert coherence_setup["uses"] == _SETUP_NODE_CURRENT
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
