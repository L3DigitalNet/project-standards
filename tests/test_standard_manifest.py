from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from project_standards.standard_manifest import (
    AdoptionMode,
    AuthorityBlock,
    CapabilitiesTable,
    ConfigTable,
    LifecycleStatus,
    ProviderBlock,
    ProviderKind,
    ProviderOperation,
    RelationsTable,
    ResourcesTable,
    StandardManifest,
    StandardManifestError,
    StandardTable,
    VersionsTable,
    load_standard_manifest,
    standard_schema,
    standard_schema_json,
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "src/project_standards/schemas/standard.schema.json"
)

_MINIMAL: dict[str, dict[str, object]] = {
    "standard": {
        "id": "demo",
        "name": "Demo",
        "status": "active",
        "summary": "x",
        "adoption": "none",
    },
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
    assert {m.value for m in ProviderOperation} == {
        "validate",
        "fix",
        "lint",
        "drift-check",
        "id-next",
        "extract",
        "render",
        "scaffold",
        "upgrade",
        "semantic-review",
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
    ProviderBlock.model_validate(
        {"operation": "extract", "kind": "documentation-only", "optional": True}
    )


def test_provider_python_single_letter_module_entrypoint() -> None:
    # "a:main" is a legitimate module:object entrypoint (module `a`), not a Windows
    # drive-letter path — the drive check must require a separator after the colon.
    ProviderBlock.model_validate(
        {"operation": "drift-check", "kind": "python", "optional": True, "entrypoint": "a:main"}
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "operation": "drift-check",
            "kind": "python",
            "optional": True,
        },  # executable missing entrypoint
        {
            "operation": "validate-frontmatter",
            "kind": "documentation-only",
            "optional": True,
        },  # standard-specific operation instead of a generic provider operation
        {
            "operation": "validate",
            "kind": "documentation-only",
            "optional": True,
            "entrypoint": "pkg:fn",
        },  # doc-only with entrypoint
        {
            "operation": "validate",
            "kind": "python",
            "optional": True,
            "entrypoint": "pkg/mod.py",
        },  # filesystem path
        {
            "operation": "validate",
            "kind": "command",
            "optional": True,
            "entrypoint": "do | rm",
        },  # shell metachars
        {
            "operation": "validate",
            "kind": "command",
            "optional": True,
            "entrypoint": "../up",
        },  # traversal
        {
            "operation": "Bad-Op",
            "kind": "command",
            "optional": True,
            "entrypoint": "t",
        },  # non-kebab operation
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


_MINIMAL_TOML = """
[standard]
id = "demo"
name = "Demo"
status = "active"
summary = "x"
adoption = "none"

[versions]
supported = []
latest = ""

[config]
namespaces = []

[capabilities]
provides = []
consumes_platform = []

[resources]
readme = "README.md"
"""


def _write_bundle(root: Path, dirname: str, toml: str) -> Path:
    bundle = root / dirname
    bundle.mkdir(parents=True)
    manifest = bundle / "standard.toml"
    manifest.write_text(toml, encoding="utf-8")
    (bundle / "README.md").write_text("# demo\n", encoding="utf-8")
    return manifest


def test_loader_valid(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "demo", _MINIMAL_TOML)
    m = load_standard_manifest(manifest)
    assert m.standard.id == "demo"


def test_loader_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StandardManifestError):
        load_standard_manifest(tmp_path / "nope" / "standard.toml")


def test_loader_malformed_toml(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "demo", "this is = = not toml")
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)


def test_loader_id_must_match_directory(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "wrong-dir", _MINIMAL_TOML)  # id is "demo"
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)


def test_loader_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    toml = _MINIMAL_TOML.replace('readme = "README.md"', 'readme = "README.md"\nleak = "sneaky.md"')
    manifest = _write_bundle(tmp_path, "demo", toml)
    (manifest.parent / "sneaky.md").symlink_to(outside)
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)


def test_loader_missing_resource_file(tmp_path: Path) -> None:
    toml = _MINIMAL_TOML.replace('readme = "README.md"', 'readme = "MISSING.md"')
    bundle = tmp_path / "demo"
    bundle.mkdir(parents=True)
    (bundle / "standard.toml").write_text(toml, encoding="utf-8")  # MISSING.md deliberately absent
    with pytest.raises(StandardManifestError):
        load_standard_manifest(bundle / "standard.toml")


def test_resources_rejects_embedded_null_byte() -> None:
    with pytest.raises(ValidationError):
        ResourcesTable.model_validate({"readme": "README.md", "leak": "foo\x00bar.md"})


def test_loader_rejects_embedded_null_byte_resource_path(tmp_path: Path) -> None:
    # \u0000 is a valid TOML basic-string escape; tomllib decodes it to a literal
    # null byte in the resulting Python str, reproducing the reviewer's repro.
    toml = _MINIMAL_TOML.replace(
        'readme = "README.md"', 'readme = "README.md"\nleak = "foo\\u0000bar.md"'
    )
    manifest = _write_bundle(tmp_path, "demo", toml)
    with pytest.raises(StandardManifestError) as exc_info:
        load_standard_manifest(manifest)
    assert exc_info.type is StandardManifestError


def test_loader_rejects_invalid_utf8(tmp_path: Path) -> None:
    # UnicodeDecodeError subclasses ValueError, not OSError — the read-path
    # exception handler must catch it explicitly or it escapes the loader
    # boundary raw, violating "StandardManifestError is the only exception
    # load_standard_manifest may raise" (sibling of the null-byte escape fix).
    bundle = tmp_path / "demo"
    bundle.mkdir(parents=True)
    (bundle / "README.md").write_text("# demo\n", encoding="utf-8")
    manifest = bundle / "standard.toml"
    manifest.write_bytes(b"\xff\xfe" + _MINIMAL_TOML.encode("utf-8"))
    with pytest.raises(StandardManifestError) as exc_info:
        load_standard_manifest(manifest)
    assert exc_info.type is StandardManifestError


def test_schema_has_metadata() -> None:
    schema = standard_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert str(schema["$id"]).endswith("/schemas/standard.schema.json")


def test_committed_schema_matches_model() -> None:
    assert _SCHEMA_PATH.read_text(encoding="utf-8") == standard_schema_json()


def test_committed_schema_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(  # pyright: ignore[reportUnknownMemberType]
        json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    )


_FIXTURES = Path(__file__).resolve().parent / "fixtures/standards_manifests"


@pytest.mark.parametrize(
    "toml_path", sorted((_FIXTURES / "valid").glob("*.toml")), ids=lambda p: p.name
)
def test_valid_fixtures_load(toml_path: Path) -> None:
    StandardManifest.model_validate(_load_toml(toml_path))


@pytest.mark.parametrize(
    "toml_path", sorted((_FIXTURES / "invalid").glob("*.toml")), ids=lambda p: p.name
)
def test_invalid_fixtures_reject(toml_path: Path) -> None:
    with pytest.raises(ValidationError):
        StandardManifest.model_validate(_load_toml(toml_path))


def _load_toml(path: Path) -> dict[str, object]:
    import tomllib

    return tomllib.loads(path.read_text(encoding="utf-8"))


_REAL_MANIFESTS = sorted(
    (Path(__file__).resolve().parent.parent / "standards").glob("*/standard.toml")
)


@pytest.mark.parametrize("real", _REAL_MANIFESTS, ids=lambda p: p.parent.name)
def test_real_manifests_validate(real: Path) -> None:
    load_standard_manifest(real)


# --- schema-vs-fixture semantic tests (the generated schema is a permissive view) ---
# Invalid fixtures the JSON Schema ALSO rejects. The remaining invalid fixtures are model-only:
# cross-field or custom-validator rules Pydantic does not emit to JSON Schema (latest-in-supported,
# reserved/duplicate namespace, adopt-on-none, per-kind entrypoint, path safety, resource-id key
# syntax). Those still fail the model (test_invalid_fixtures_reject) but pass the raw schema.
_SCHEMA_ENFORCED = {
    "bad-adoption.toml",
    "bad-status.toml",
    "bad-id.toml",
    "bad-operation.toml",
    "malformed-namespace.toml",
    "unknown-key.toml",
    "stray-requires.toml",
    "missing-required.toml",
    "non-string-resource.toml",
    "missing-versions-table.toml",
}


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.parametrize(
    "toml_path", sorted((_FIXTURES / "valid").glob("*.toml")), ids=lambda p: p.name
)
def test_valid_fixtures_pass_generated_schema(toml_path: Path) -> None:
    _schema_validator().validate(_load_toml(toml_path))  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.parametrize(
    "toml_path",
    sorted(p for p in (_FIXTURES / "invalid").glob("*.toml") if p.name in _SCHEMA_ENFORCED),
    ids=lambda p: p.name,
)
def test_schema_enforced_invalids_fail_generated_schema(toml_path: Path) -> None:
    from jsonschema import ValidationError as SchemaValidationError

    with pytest.raises(SchemaValidationError):
        _schema_validator().validate(_load_toml(toml_path))  # pyright: ignore[reportUnknownMemberType]


@pytest.mark.parametrize(
    "toml_path",
    sorted(p for p in (_FIXTURES / "invalid").glob("*.toml") if p.name not in _SCHEMA_ENFORCED),
    ids=lambda p: p.name,
)
def test_model_only_invalids_pass_generated_schema(toml_path: Path) -> None:
    # Symmetric guard to test_schema_enforced_invalids_fail_generated_schema: every
    # invalid fixture NOT in _SCHEMA_ENFORCED is model-only (cross-field/custom-
    # validator rules Pydantic doesn't emit to JSON Schema). The raw generated
    # schema must NOT reject it — locking the enforced-vs-model-only split against
    # future schema drift (e.g. a schema change that starts rejecting one of these).
    _schema_validator().validate(_load_toml(toml_path))  # pyright: ignore[reportUnknownMemberType]
