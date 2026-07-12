from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    ContributionDeclaration,
    MaterializationPredicate,
    PayloadManifest,
    SemanticAddress,
    WholeArtifactDeclaration,
)

_PAYLOAD_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures/package_contract/valid/minimal/standards/demo/versions/1.2/payload.toml"
)


def _payload_data() -> dict[str, object]:
    return tomllib.loads(_PAYLOAD_PATH.read_text(encoding="utf-8"))


def _resources(data: dict[str, object]) -> list[dict[str, object]]:
    value = data["resources"]
    assert isinstance(value, list)
    return cast("list[dict[str, object]]", value)


def _contribution(
    *,
    contribution_id: str = "ruff-config",
    target: str = "pyproject.toml",
    adapter: str = "toml",
    scope: str = "table:/tool/ruff",
    source: str | None = "resources/ruff.toml",
    provider: str | None = None,
    shared_identity: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": contribution_id,
        "target": target,
        "adapter": adapter,
        "scope": scope,
        "policy": "managed",
    }
    if source is not None:
        result["source"] = source
        result["source_digest"] = f"sha256:{'a' * 64}"
    if provider is not None:
        result["provider"] = provider
    if shared_identity is not None:
        result["shared_identity"] = shared_identity
    return result


def test_whole_artifact_declares_exclusive_source_target_policy_and_mode() -> None:
    data = _payload_data()
    data["artifacts"] = [
        {
            "id": "python-version",
            "target": ".python-version",
            "source": "artifacts/python-version",
            "digest": f"sha256:{'a' * 64}",
            "policy": "create-only",
            "mode": "0644",
        }
    ]

    manifest = PayloadManifest.model_validate(data)
    artifact = manifest.artifacts[0]

    assert artifact.id == "python-version"
    assert artifact.target.original == ".python-version"
    assert artifact.source.original == "artifacts/python-version"
    assert artifact.policy is ArtifactPolicy.CREATE_ONLY
    assert artifact.mode == "0644"


def test_outputs_accept_closed_option_predicates_for_conditional_materialization() -> None:
    artifact = WholeArtifactDeclaration.model_validate(
        {
            "id": "hook",
            "target": ".agents/hooks/session_start.py",
            "source": "artifacts/session_start.py",
            "digest": f"sha256:{'a' * 64}",
            "policy": "managed",
            "when_any": [{"option": "startup", "equals": "automatic"}],
        }
    )
    contribution = ContributionDeclaration.model_validate(
        {
            **_contribution(),
            "when_any": [
                {"option": "startup", "equals": "manual"},
                {"option": "harnesses", "contains": "codex"},
            ],
        }
    )

    assert artifact.materializes({"startup": "automatic"})
    assert not artifact.materializes({"startup": "manual"})
    assert contribution.materializes({"startup": "manual", "harnesses": []})
    assert contribution.materializes({"startup": "automatic", "harnesses": ["codex"]})
    assert not contribution.materializes({"startup": "automatic", "harnesses": ["claude-code"]})
    assert not MaterializationPredicate(option="level", equals=1).matches({"level": True})


@pytest.mark.parametrize(
    "predicate",
    [
        {},
        {"option": "startup"},
        {"option": "startup", "equals": "automatic", "contains": "automatic"},
        {"option": "", "equals": "automatic"},
        {"option": "startup", "equals": {"nested": True}},
        {"option": "harnesses", "contains": ["codex"]},
    ],
)
def test_materialization_predicate_rejects_ambiguous_or_non_scalar_contracts(
    predicate: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        MaterializationPredicate.model_validate(predicate)


@pytest.mark.parametrize("mode", ["644", "0999", "06444", "-0644", 0o644])
def test_whole_artifact_rejects_invalid_posix_modes(mode: str | int) -> None:
    data = _payload_data()
    data["artifacts"] = [
        {
            "id": "python-version",
            "target": ".python-version",
            "source": "artifacts/python-version",
            "digest": f"sha256:{'a' * 64}",
            "policy": "managed",
            "mode": mode,
        }
    ]

    with pytest.raises(ValidationError):
        PayloadManifest.model_validate(data)


@pytest.mark.parametrize(
    ("adapter", "scope"),
    [
        ("whole-file", "$file"),
        ("toml", "key:/project/requires-python"),
        ("toml", "table:/tool/ruff"),
        ("json", "key:/editor/formatOnSave"),
        ("json", "set:/recommendations#value=ms-python.python"),
        ("jsonc", "keyed-set:/tasks#label=lint"),
        ("yaml", "key:/jobs/check"),
        ("yaml", "keyed-set:/hooks#id=session-start"),
        ("editorconfig", "property:$global#root"),
        ("editorconfig", "property:*.py#indent_size"),
        ("editorconfig", "property:docs/*.md#indent_size"),
        ("markdown-block", "block:agent-handoff-instructions"),
        ("markdown-block", "block:café"),
    ],
)
def test_contribution_accepts_every_v1_adapter_selector(adapter: str, scope: str) -> None:
    declaration = ContributionDeclaration.model_validate(
        _contribution(adapter=adapter, scope=scope)
    )

    assert declaration.adapter is AdapterKind(adapter)
    assert declaration.scope == scope
    assert declaration.address == SemanticAddress(
        target=declaration.target,
        adapter=declaration.adapter,
        scope=scope,
    )


@pytest.mark.parametrize(
    ("adapter", "scope"),
    [
        ("whole-file", "file"),
        ("toml", "tool.ruff"),
        ("toml", "table:tool/ruff"),
        ("toml", "key:/tool/~2bad"),
        ("json", "set:/recommendations#value="),
        ("json", "set:/recommendations#value=raw#delimiter"),
        ("jsonc", "keyed-set:/tasks#label="),
        ("yaml", "set:/hooks#value=x"),
        ("editorconfig", "property:*.py"),
        ("editorconfig", "property:*.py#bad#key"),
        ("markdown-block", "block:bad#id"),
    ],
)
def test_contribution_rejects_invalid_or_ambiguous_selectors(adapter: str, scope: str) -> None:
    with pytest.raises(ValidationError):
        ContributionDeclaration.model_validate(_contribution(adapter=adapter, scope=scope))


@pytest.mark.parametrize(
    "overrides",
    [
        {"source": None, "provider": None},
        {"source": "resources/value.txt", "provider": "render-value"},
        {"source": None, "provider": "render-value", "source_digest": f"sha256:{'a' * 64}"},
    ],
)
def test_contribution_requires_exactly_one_static_source_or_provider(
    overrides: dict[str, object],
) -> None:
    payload = _contribution()
    payload.update(overrides)
    if overrides.get("source") is None:
        payload.pop("source", None)

    with pytest.raises(ValidationError):
        ContributionDeclaration.model_validate(payload)


def test_provider_contribution_has_no_static_digest() -> None:
    declaration = ContributionDeclaration.model_validate(
        _contribution(source=None, provider="render-value")
    )

    assert declaration.provider == "render-value"
    assert declaration.source is None
    assert declaration.source_digest is None


@pytest.mark.parametrize(
    "contributions",
    [
        [
            _contribution(contribution_id="one"),
            _contribution(contribution_id="two"),
        ],
        [
            _contribution(contribution_id="parent", scope="table:/tool/ruff"),
            _contribution(contribution_id="child", scope="key:/tool/ruff/line-length"),
        ],
        [
            _contribution(contribution_id="toml-owner"),
            _contribution(contribution_id="json-owner", adapter="json", scope="key:/tool/ruff"),
        ],
    ],
)
def test_payload_rejects_duplicate_parent_child_or_adapter_mismatched_ownership(
    contributions: list[dict[str, object]],
) -> None:
    data = _payload_data()
    data["contributions"] = contributions

    with pytest.raises(ValidationError, match=r"overlap|adapter"):
        PayloadManifest.model_validate(data)


def test_payload_accepts_distinct_set_entries_in_one_shared_container() -> None:
    data = _payload_data()
    data["contributions"] = [
        _contribution(
            contribution_id="python-recommendation",
            target=".vscode/extensions.json",
            adapter="jsonc",
            scope="set:/recommendations#value=ms-python.python",
        ),
        _contribution(
            contribution_id="ruff-recommendation",
            target=".vscode/extensions.json",
            adapter="jsonc",
            scope="set:/recommendations#value=charliermarsh.ruff",
        ),
    ]

    manifest = PayloadManifest.model_validate(data)

    assert len(manifest.contributions) == 2


def test_payload_rejects_whole_artifact_and_contribution_target_collision() -> None:
    data = _payload_data()
    data["artifacts"] = [
        {
            "id": "whole-pyproject",
            "target": "pyproject.toml",
            "source": "artifacts/pyproject.toml",
            "digest": f"sha256:{'b' * 64}",
            "policy": "managed",
        }
    ]
    data["contributions"] = [_contribution()]

    with pytest.raises(ValidationError, match="whole artifact"):
        PayloadManifest.model_validate(data)


def test_payload_rejects_shared_identity_with_different_normalized_value() -> None:
    data = _payload_data()
    shared = "project-standards/editorconfig/root/true"
    data["contributions"] = [
        _contribution(
            contribution_id="first",
            target=".editorconfig",
            adapter="editorconfig",
            scope="property:$global#root",
            shared_identity=shared,
        ),
        _contribution(
            contribution_id="second",
            target="other.editorconfig",
            adapter="editorconfig",
            scope="property:$global#root",
            shared_identity=shared,
        ),
    ]

    with pytest.raises(ValidationError, match="shared identity"):
        PayloadManifest.model_validate(data)


def test_payload_requires_version_documentation_and_conditional_adoption_roles() -> None:
    data = _payload_data()
    resources = _resources(data)
    data["resources"] = [item for item in resources if item["role"] != "agent-summary"]

    with pytest.raises(ValidationError, match="required resource role"):
        PayloadManifest.model_validate(data)

    reference_data = _payload_data()
    payload = reference_data["payload"]
    assert isinstance(payload, dict)
    payload["availability"] = "reference-only"
    reference_resources = _resources(reference_data)
    reference_data["resources"] = [
        item for item in reference_resources if item["role"] != "adoption-guide"
    ]
    manifest = PayloadManifest.model_validate(reference_data)
    assert manifest.payload.availability.value == "reference-only"


def test_reference_only_payload_rejects_adoption_guide() -> None:
    data = _payload_data()
    payload = data["payload"]
    assert isinstance(payload, dict)
    payload["availability"] = "internal"

    with pytest.raises(ValidationError, match="adoption-guide"):
        PayloadManifest.model_validate(data)


def test_required_resource_roles_enforce_media_types() -> None:
    data = _payload_data()
    resources = _resources(data)
    config_schema = next(item for item in resources if item["role"] == "config-schema")
    config_schema["media_type"] = "text/markdown"

    with pytest.raises(ValidationError, match="media type"):
        PayloadManifest.model_validate(data)


def test_payload_rejects_ambiguous_duplicate_required_resource_roles() -> None:
    data = _payload_data()
    resources = _resources(data)
    resources.append(
        {
            "id": "alternate-readme",
            "role": "canonical-standard",
            "path": "alternate-README.md",
            "media_type": "text/markdown",
            "digest": f"sha256:{'b' * 64}",
        }
    )

    with pytest.raises(ValidationError, match="exactly one"):
        PayloadManifest.model_validate(data)
