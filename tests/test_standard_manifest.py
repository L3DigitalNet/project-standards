from __future__ import annotations

import pytest
from pydantic import ValidationError

from project_standards.standard_manifest import (
    AdoptionMode,
    AuthorityBlock,
    CapabilitiesTable,
    ConfigTable,
    LifecycleStatus,
    ProviderBlock,
    ProviderKind,
    RelationsTable,
    ResourcesTable,
    StandardManifest,
    StandardManifestError,
    StandardTable,
    VersionsTable,
)

_MINIMAL: dict[str, dict[str, object]] = {
    "standard": {"id": "demo", "name": "Demo", "status": "active", "summary": "x", "adoption": "none"},
    "versions": {"supported": [], "latest": ""},
    "config": {"namespaces": []},
    "capabilities": {"provides": [], "consumes_platform": []},
    "resources": {"readme": "README.md"},
}


def test_enums_have_contract_values() -> None:
    assert {m.value for m in AdoptionMode} == {
        "validator",
        "copy-adopt",
        "cli",
        "reference-only",
        "none",
    }
    assert {m.value for m in LifecycleStatus} == {
        "draft",
        "review",
        "active",
        "deprecated",
        "archived",
        "superseded",
    }
    assert {m.value for m in ProviderKind} == {
        "python",
        "command",
        "workflow",
        "documentation-only",
    }


def test_error_is_valueerror() -> None:
    assert issubclass(StandardManifestError, ValueError)


def test_standard_table_valid() -> None:
    t = StandardTable.model_validate(
        {
            "id": "markdown-tooling",
            "name": "Markdown Tooling",
            "status": "active",
            "summary": "Formatting and structural linting.",
            "adoption": "copy-adopt",
        }
    )
    assert t.id == "markdown-tooling"
    assert t.adoption is AdoptionMode.COPY_ADOPT


@pytest.mark.parametrize(
    "override",
    [
        {"id": "Not_Kebab"},  # bad id syntax
        {"adoption": "package-tooling"},  # not in enum
        {"status": "retired"},  # not in enum
        {"requires": "adr"},  # stray reserved key
    ],
)
def test_standard_table_rejects(override: dict[str, str]) -> None:
    base = {
        "id": "markdown-tooling",
        "name": "Markdown Tooling",
        "status": "active",
        "summary": "x",
        "adoption": "copy-adopt",
    }
    with pytest.raises(ValidationError):
        StandardTable.model_validate({**base, **override})


def test_versions_latest_must_be_in_supported() -> None:
    VersionsTable.model_validate({"supported": ["1.0", "1.1"], "latest": "1.1"})
    VersionsTable.model_validate({"supported": [], "latest": ""})
    with pytest.raises(ValidationError):
        VersionsTable.model_validate({"supported": ["1.0"], "latest": "2.0"})


def test_config_accepts_dotted_paths() -> None:
    t = ConfigTable.model_validate({"namespaces": ["markdown.frontmatter", "markdown_tooling"]})
    assert t.namespaces == ["markdown.frontmatter", "markdown_tooling"]
    ConfigTable.model_validate({"namespaces": []})


@pytest.mark.parametrize(
    "namespaces",
    [
        ["standards_version"],  # reserved meta key
        ["markdown..frontmatter"],  # empty segment / bad dotted path
        [".markdown"],  # leading dot
        ["Markdown"],  # uppercase not allowed
        ["spec", "spec"],  # duplicate within manifest
    ],
)
def test_config_rejects(namespaces: list[str]) -> None:
    with pytest.raises(ValidationError):
        ConfigTable.model_validate({"namespaces": namespaces})


def test_capabilities_and_relations_defaults() -> None:
    c = CapabilitiesTable.model_validate({"provides": ["markdown.format"], "consumes_platform": []})
    assert c.provides == ["markdown.format"]
    r = RelationsTable.model_validate({})
    assert r.companions == [] and r.extends == [] and r.conflicts == []


def test_relations_rejects_requires_key() -> None:
    with pytest.raises(ValidationError):
        RelationsTable.model_validate({"requires": ["adr"]})


def test_resources_open_mapping() -> None:
    t = ResourcesTable.model_validate(
        {
            "readme": "README.md",
            "adopt": "adopt.md",
            "agent_summary": "agent-summary.md",
            "template": "templates/standard.toml",
            "rationale": "resources/why.md",  # arbitrary URI-safe id
        }
    )
    assert t.as_dict()["rationale"] == "resources/why.md"


@pytest.mark.parametrize(
    "payload",
    [
        {},  # readme missing
        {"readme": "README.md", "bad id": "x.md"},  # malformed resource id
        {"readme": "../escape.md"},  # unsafe path
        {"readme": "/abs.md"},  # absolute path
        {"readme": "resources/../../x.md"},  # traversal on arbitrary-ish value
        {"readme": "README.md", "count": 5},  # non-string extra value (CR-001)
        {"readme": "README.md", "nested": {"k": "v"}},  # nested table extra
    ],
)
def test_resources_rejects(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ResourcesTable.model_validate(payload)


def test_authority_requires_full_tuple() -> None:
    AuthorityBlock.model_validate(
        {
            "domain": "markdown",
            "target": "**/*.md",
            "concern": "physical-formatting",
            "owner": "prettier",
            "mutates": True,
        }
    )
    with pytest.raises(ValidationError):
        AuthorityBlock.model_validate({"domain": "markdown", "target": "**/*.md"})


def test_provider_valid_shapes() -> None:
    ProviderBlock.model_validate(
        {"operation": "drift-check", "kind": "python", "optional": True, "entrypoint": "pkg.mod:fn"}
    )
    ProviderBlock.model_validate(
        {"operation": "validate", "kind": "command", "optional": False, "entrypoint": "mytool"}
    )
    ProviderBlock.model_validate({"operation": "extract", "kind": "documentation-only", "optional": True})


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "drift-check", "kind": "python", "optional": True},  # executable missing entrypoint
        {
            "operation": "x",
            "kind": "documentation-only",
            "optional": True,
            "entrypoint": "pkg:fn",
        },  # doc-only with entrypoint
        {"operation": "x", "kind": "python", "optional": True, "entrypoint": "pkg/mod.py"},  # filesystem path
        {"operation": "x", "kind": "command", "optional": True, "entrypoint": "do | rm"},  # shell metachars
        {"operation": "x", "kind": "command", "optional": True, "entrypoint": "../up"},  # traversal
        {"operation": "Bad-Op", "kind": "command", "optional": True, "entrypoint": "t"},  # non-kebab operation
    ],
)
def test_provider_rejects(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProviderBlock.model_validate(payload)


def test_manifest_minimal_valid() -> None:
    m = StandardManifest.model_validate(_MINIMAL)
    assert m.standard.id == "demo"
    assert m.relations.companions == []


def test_manifest_adoption_none_forbids_adopt_resource() -> None:
    payload = {**_MINIMAL, "resources": {"readme": "README.md", "adopt": "adopt.md"}}
    with pytest.raises(ValidationError):
        StandardManifest.model_validate(payload)


def test_manifest_rejects_unknown_top_level_table() -> None:
    with pytest.raises(ValidationError):
        StandardManifest.model_validate({**_MINIMAL, "mystery": {}})
