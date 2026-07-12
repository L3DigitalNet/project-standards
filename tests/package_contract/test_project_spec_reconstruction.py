from __future__ import annotations

import base64
import hashlib
import json
import shutil
import socket
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    ArtifactPolicy,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.specs import registry as spec_registry
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PAYLOAD = _FAMILY / "versions/1.1"
_MARKDOWN_FAMILY = _ROOT / "standards/markdown-tooling"
_MARKDOWN_PAYLOAD = _MARKDOWN_FAMILY / "versions/1.2"


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _installed_distribution(
    tmp_path: Path,
    *,
    include_markdown_tooling: bool = False,
) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/project-spec"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "project-spec"
name = "Project Specification Standard"
summary = "Tiered version-selected project specifications."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    catalog_entries = f'''[[packages]]
id = "project-spec"
version = "1.1"
digest = "{payload.integrity.aggregate_digest.value}"
role = "default"
'''
    if include_markdown_tooling:
        markdown_family = repository / "standards/markdown-tooling"
        shutil.copytree(_MARKDOWN_FAMILY, markdown_family)
        markdown_manifest = load_payload_manifest(_MARKDOWN_PAYLOAD / "payload.toml")
        markdown = InstalledPayload(
            _MARKDOWN_PAYLOAD,
            markdown_manifest,
            validate_payload_integrity(_MARKDOWN_PAYLOAD, markdown_manifest),
        )
        (markdown_family / "standard.toml").write_text(
            f'''schema_version = "2.0"

[standard]
id = "markdown-tooling"
name = "Markdown Tooling Standard"
summary = "Prettier and markdownlint with semantic editor configuration."
status = "active"

[[versions]]
version = "1.2"
payload = "versions/1.2/payload.toml"
digest = "{markdown.integrity.aggregate_digest.value}"
''',
            encoding="utf-8",
        )
        catalog_entries += f'''
[[packages]]
id = "markdown-tooling"
version = "1.2"
digest = "{markdown.integrity.aggregate_digest.value}"
role = "default"
'''
    (repository / "catalogs/5.toml").write_text(
        f"""schema_version = "1.0"
catalog_major = 5

{catalog_entries}
""",
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _invoke(
    provider_id: str,
    operation: ProviderOperation,
    *,
    config: JsonObject | None = None,
    snapshots: JsonObject | None = None,
):
    payload = _payload()
    return invoke_provider(
        ProviderInvocation(
            repo=_ROOT,
            payload=payload,
            standard_id="project-spec",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=operation,
            effective_config=config
            or {
                "contract_version": "1.1",
                "include_patterns": ["docs/specs/**/*.md"],
                "reference_prefixes": [],
                "default_profile": "standard",
                "ci": True,
            },
            snapshots=snapshots or {},
        )
    )


def test_project_spec_payload_exists_and_is_integrity_complete() -> None:
    assert _PAYLOAD.is_dir()
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    assert validate_payload_integrity(_PAYLOAD, manifest).inventory


def test_project_spec_options_are_closed_and_explicit() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    schema = load_option_schema(_PAYLOAD, manifest)

    assert schema.resolve_options({}) == {
        "contract_version": "1.1",
        "include_patterns": ["docs/specs/**/*.md"],
        "reference_prefixes": [],
        "default_profile": "standard",
        "ci": True,
    }


def test_project_spec_declares_independent_document_schemas_and_providers() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    resources = {resource.id: resource for resource in manifest.resources}
    assert callable(spec_registry.registry_from_templates)

    assert {
        resources[f"schema-{profile}"].path.original for profile in ("light", "standard", "full")
    } == {
        "schemas/spec-light.schema.json",
        "schemas/spec-standard.schema.json",
        "schemas/spec-full.schema.json",
    }
    assert {
        provider.id: (provider.operation, provider.effect) for provider in manifest.providers
    } == {
        "extract": (ProviderOperation.EXTRACT, ProviderEffect.CONTENT),
        "id-next": (ProviderOperation.ID_NEXT, ProviderEffect.CONTENT),
        "lint": (ProviderOperation.LINT, ProviderEffect.FINDINGS),
        "migrate-legacy": (ProviderOperation.MIGRATE, ProviderEffect.MIGRATION_REPORT),
        "render-preview": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "render-workflow": (ProviderOperation.RENDER, ProviderEffect.CONTENT),
        "scaffold": (ProviderOperation.SCAFFOLD, ProviderEffect.MUTATION_PLAN),
        "upgrade": (ProviderOperation.UPGRADE, ProviderEffect.MUTATION_PLAN),
        "validate": (ProviderOperation.VALIDATE, ProviderEffect.FINDINGS),
    }


def test_project_spec_document_schemas_cover_the_complete_independent_frontmatter() -> None:
    example = (_PAYLOAD / "examples/spec.example.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(example.split("---", 2)[1])
    expected = {
        "spec_id",
        "title",
        "status",
        "profile",
        "owner",
        "implementer",
        "created",
        "last_reviewed",
        "supersedes",
        "superseded_by",
        "related",
    }

    for profile in ("light", "standard", "full"):
        schema = json.loads(
            (_PAYLOAD / f"schemas/spec-{profile}.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        assert set(schema["properties"]) == expected
        validator = Draft202012Validator(schema)
        validator.validate(  # pyright: ignore[reportUnknownMemberType]
            {**frontmatter, "profile": profile}
        )
        with pytest.raises(ValidationError):
            validator.validate(  # pyright: ignore[reportUnknownMemberType]
                {**frontmatter, "profile": profile, "doc_type": "spec"}
            )


def test_project_spec_manages_only_the_workflow_and_keeps_payload_templates() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    assert manifest.artifacts == []
    assert [
        (contribution.target.original, contribution.policy)
        for contribution in manifest.contributions
    ] == [(".github/workflows/validate-specs.yml", ArtifactPolicy.MANAGED)]
    template_paths = {
        resource.path.original for resource in manifest.resources if resource.role == "template"
    }
    assert template_paths == {
        "templates/spec-light-template.md",
        "templates/spec-standard-template.md",
        "templates/spec-full-template.md",
    }


def test_project_spec_declares_the_exact_rendered_v4_workflow_only() -> None:
    payload = _payload()
    signatures = {signature.id: signature for signature in payload.manifest.legacy_signatures}
    rendered_v4 = (
        (_ROOT / "src/project_standards/bundles/project-spec/validate-specs.caller.yml")
        .read_bytes()
        .replace(b"{{ref}}", b"v4")
    )

    assert set(signatures) == {"legacy-workflow"}
    assert (_PAYLOAD / "resources/legacy-validate-specs.yml").read_bytes() == rendered_v4
    assert b"{{ref}}" not in rendered_v4
    assert signatures["legacy-workflow"].known_content_digests[0].value == (
        f"sha256:{hashlib.sha256(rendered_v4).hexdigest()}"
    )


def test_project_spec_root_v1_manifest_is_unchanged() -> None:
    digest = hashlib.sha256((_FAMILY / "standard.toml").read_bytes()).hexdigest()

    assert digest == "c39f455234f3201df671b0f158630e55af21a175d6ece19a30136896c03b2993"


def test_project_spec_v2_docs_describe_only_the_v5_control_plane() -> None:
    documents = {
        path.name: path.read_text(encoding="utf-8")
        for path in (_PAYLOAD / "README.md", _PAYLOAD / "adopt.md", _PAYLOAD / "agent-summary.md")
    }
    combined = "\n".join(documents.values())

    for stale in (
        "@v4",
        "v4.0.0",
        ".project-standards.yml",
        "project-standards adopt",
        "```yaml",
        "spec.reference_prefixes",
        "spec.version",
    ):
        assert stale not in combined
    for expected in (
        ".standards/config.toml",
        "project-standards standards enable project-spec --version 1.1",
        "project-standards reconcile --apply",
        "include_patterns",
        "reference_prefixes",
        "default_profile",
        "ci",
    ):
        assert expected in combined


def test_project_spec_validate_and_lint_use_payload_templates() -> None:
    content = (_PAYLOAD / "examples/spec.example.md").read_bytes()
    snapshots: JsonObject = {
        "documents": [
            {
                "path": "docs/specs/example.md",
                "kind": "regular",
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        ]
    }

    validated = _invoke("validate", ProviderOperation.VALIDATE, snapshots=snapshots)
    linted = _invoke("lint", ProviderOperation.LINT, snapshots=snapshots)

    assert validated.findings == ()
    assert linted.findings == ()


def test_project_spec_inspection_providers_return_typed_metadata() -> None:
    content = (_PAYLOAD / "examples/spec.example.md").read_bytes()
    document: JsonObject = {
        "path": "docs/specs/example.md",
        "kind": "regular",
        "content_base64": base64.b64encode(content).decode("ascii"),
    }

    extracted = _invoke(
        "extract",
        ProviderOperation.EXTRACT,
        snapshots={"document": document, "selector": "§7"},
    )
    next_id = _invoke(
        "id-next",
        ProviderOperation.ID_NEXT,
        snapshots={"document": document, "prefix": "FR"},
    )

    extracted_output = extracted.structured_output
    next_output = next_id.structured_output
    assert extracted_output is not None
    assert next_output is not None
    markdown = extracted_output["markdown"]
    generated_id = next_output["next_id"]
    assert isinstance(markdown, str)
    assert isinstance(generated_id, str)
    assert extracted_output == {
        "content": markdown,
        "file": "docs/specs/example.md",
        "selector": "§7",
        "kind": "section",
        "found": True,
        "markdown": markdown,
    }
    assert markdown.startswith("## 7. Requirements")
    assert next_output == {
        "content": generated_id,
        "file": "docs/specs/example.md",
        "prefix": "FR",
        "next_id": generated_id,
    }


def test_project_spec_inspection_output_schemas_require_operation_metadata() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    resources = {resource.id: resource for resource in manifest.resources}
    providers = {provider.id: provider for provider in manifest.providers}

    for provider_id, resource_id in (
        ("extract", "provider-extract"),
        ("id-next", "provider-id-next"),
    ):
        assert providers[provider_id].output_schema == resource_id
        schema = json.loads(
            (_PAYLOAD / resources[resource_id].path.normalized).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        with pytest.raises(ValidationError):
            validator.validate(  # pyright: ignore[reportUnknownMemberType]
                {"content": "untyped"}
            )

    extract_schema = json.loads(
        (_PAYLOAD / resources["provider-extract"].path.normalized).read_text(encoding="utf-8")
    )
    extract_validator = Draft202012Validator(extract_schema)
    base = {
        "content": "",
        "file": "spec.md",
        "selector": "§7",
        "kind": "section",
    }
    for contradictory in (
        {**base, "found": True, "markdown": None},
        {**base, "found": False, "markdown": "unexpected"},
    ):
        with pytest.raises(ValidationError):
            extract_validator.validate(  # pyright: ignore[reportUnknownMemberType]
                contradictory
            )


def test_project_spec_scaffold_returns_typed_mutation_plan(tmp_path: Path) -> None:
    target = SafeRelativePath.parse("docs/specs/new.md")
    entry = RepositorySnapshot.capture(tmp_path, (target,)).entries[0]
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=tmp_path,
            payload=payload,
            standard_id="project-spec",
            version=payload.manifest.payload.version,
            provider_id="scaffold",
            operation=ProviderOperation.SCAFFOLD,
            effective_config={
                "contract_version": "1.1",
                "include_patterns": ["docs/specs/**/*.md"],
                "reference_prefixes": [],
                "default_profile": "light",
                "ci": True,
            },
            snapshots={
                "authoring": {
                    "target": target.original,
                    "kind": "missing",
                    "precondition_digest": entry.precondition_digest.value,
                    "mode": "0644",
                    "overwrite": False,
                    "spec_id": "SPEC-7F3Q",
                    "today": "2026-07-11",
                }
            },
        )
    )

    assert result.mutation_plan is not None
    action = result.mutation_plan.actions[0]
    assert action.target == target
    assert action.kind.value == "create"
    assert b"spec_id: SPEC-7F3Q" in (action.content_bytes or b"")


def test_project_spec_workflow_ci_false_is_a_stable_noop_caller() -> None:
    result = _invoke(
        "render-workflow",
        ProviderOperation.RENDER,
        config={
            "contract_version": "1.1",
            "include_patterns": ["docs/specs/**/*.md"],
            "reference_prefixes": [],
            "default_profile": "standard",
            "ci": False,
        },
    )

    assert result.content is not None
    assert b"workflow_dispatch:" in result.content
    assert b"if: ${{ false }}" in result.content


def test_project_spec_scaffold_preview_returns_content_without_a_target() -> None:
    result = _invoke(
        "render-preview",
        ProviderOperation.RENDER,
        snapshots={
            "preview": {
                "operation": "scaffold",
                "profile": "light",
                "spec_id": "SPEC-7F3Q",
                "today": "2026-07-11",
                "title": "Preview",
            }
        },
    )

    assert result.content is not None
    assert b"spec_id: SPEC-7F3Q" in result.content
    assert b"title: 'Preview'" in result.content


def test_project_spec_migration_normalizes_v1_and_preserves_ambiguity() -> None:
    exact = _invoke(
        "migrate-legacy",
        ProviderOperation.MIGRATE,
        snapshots={
            "legacy_config": {
                "spec": {
                    "version": "1.0",
                    "include": "docs/specs/**/*.md",
                    "exclude": [],
                    "reference_prefixes": ["EXT"],
                }
            },
            "legacy_signatures": {},
        },
    )
    assert exact.migration_report is not None
    assert exact.migration_report.package.config == {
        "contract_version": "1.1",
        "include_patterns": ["docs/specs/**/*.md"],
        "reference_prefixes": ["EXT"],
    }
    assert "/spec/exclude" in exact.migration_report.package.recognized_settings
    assert exact.migration_report.findings == ()

    ambiguous = _invoke(
        "migrate-legacy",
        ProviderOperation.MIGRATE,
        snapshots={
            "legacy_config": {
                "spec": {
                    "version": "1.0",
                    "include": ["docs/specs/**/*.md"],
                    "exclude": ["docs/specs/generated/**"],
                }
            },
            "legacy_signatures": {},
        },
    )
    assert ambiguous.migration_report is not None
    assert [finding.code for finding in ambiguous.migration_report.findings] == [
        "SPEC-LEGACY-EXCLUDE"
    ]


def test_project_spec_migration_claims_only_its_semantic_config_block_and_workflow() -> None:
    payload = _payload()
    signature = payload.manifest.legacy_signatures[0]
    result = _invoke(
        "migrate-legacy",
        ProviderOperation.MIGRATE,
        snapshots={
            "legacy_config": {
                "standards_version": "v4",
                "markdown_tooling": {"version": "1.1"},
                "spec": {
                    "version": "1.0",
                    "include": ["docs/specs/**/*.md"],
                    "exclude": [],
                },
            },
            "legacy_signatures": {
                "legacy-workflow": {
                    ".github/workflows/validate-specs.yml": {
                        "known": True,
                        "digest": signature.known_content_digests[0].value,
                    }
                }
            },
        },
    )

    assert result.migration_report is not None
    assert result.migration_report.package.recognized_settings == (
        "/spec/exclude",
        "/spec/include",
        "/spec/version",
    )
    assert [
        (claim.signature_id, claim.target.original) for claim in result.migration_report.claims
    ] == [("legacy-workflow", ".github/workflows/validate-specs.yml")]


def test_project_spec_fresh_apply_second_apply_and_disable_converge(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "project-spec", True)

    request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(request)
    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(request, first)).success
    workflow = repo / ".github/workflows/validate-specs.yml"
    assert b".standards/config.toml" in workflow.read_bytes()

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    assert apply_reconciliation(ApplyRequest(second_request, second)).success

    set_standard_enabled(repo, "project-spec", False)
    disabled_request = build_planner_request(repo, distribution, frozenset())
    disabled = plan_reconciliation(disabled_request)
    assert disabled.applicable, disabled.findings
    assert apply_reconciliation(ApplyRequest(disabled_request, disabled)).success
    assert not workflow.exists()


def test_project_spec_migration_preview_is_read_only_and_apply_retires_legacy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    workflow = repo / ".github/workflows/validate-specs.yml"
    workflow.parent.mkdir(parents=True)
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
spec:
  version: "1.0"
  include:
    - "docs/specs/**/*.md"
  exclude: []
""",
        encoding="utf-8",
    )
    workflow.write_bytes((_PAYLOAD / "resources/legacy-validate-specs.yml").read_bytes())

    def deny_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("migration preview attempted network access")

    monkeypatch.setattr(socket, "socket", deny_network)
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }
    plan = plan_legacy_migration(repo, distribution, "5")
    assert plan.applicable, plan.findings
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before

    result = apply_legacy_migration(plan)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    assert b".standards/config.toml" in workflow.read_bytes()


def test_project_spec_real_multi_standard_migration_preserves_semantics_and_converges(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path, include_markdown_tooling=True)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
markdown_tooling:
  version: "1.1"
spec:
  version: "1.0"
  include:
    - "docs/specs/**/*.md"
  exclude: []
""",
        encoding="utf-8",
    )
    sources = {
        ".markdownlint.json": _MARKDOWN_PAYLOAD / "artifacts/markdownlint.json",
        ".prettierrc.json": _MARKDOWN_PAYLOAD / "artifacts/prettierrc.json",
        ".editorconfig": _MARKDOWN_PAYLOAD / "resources/legacy-editorconfig",
        ".vscode/extensions.json": (_MARKDOWN_PAYLOAD / "resources/legacy-vscode-extensions.json"),
        ".github/workflows/lint-markdown.yml": (
            _MARKDOWN_PAYLOAD / "resources/legacy-lint-markdown.caller.yml"
        ),
        ".github/workflows/format.yml": (_MARKDOWN_PAYLOAD / "resources/legacy-format.caller.yml"),
        ".github/workflows/validate-specs.yml": (_PAYLOAD / "resources/legacy-validate-specs.yml"),
    }
    for target, source in sources.items():
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    plan = plan_legacy_migration(repo, distribution, "5")
    assert plan.applicable, plan.findings
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before
    assert {report.package.standard_id for report in plan.reports} == {
        "markdown-tooling",
        "project-spec",
    }
    assert apply_legacy_migration(plan).success
    assert not (repo / ".project-standards.yml").exists()
    config = (repo / ".standards/config.toml").read_text(encoding="utf-8")
    assert "[standards.markdown-tooling]" in config
    assert "[standards.project-spec]" in config

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


def test_project_spec_modified_v4_workflow_is_ambiguous_without_mutating_config(
    tmp_path: Path,
) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    legacy = repo / ".project-standards.yml"
    legacy.write_text(
        """standards_version: v4
spec:
  version: "1.0"
  include: ["docs/specs/**/*.md"]
  exclude: []
""",
        encoding="utf-8",
    )
    workflow = repo / ".github/workflows/validate-specs.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(
        (_PAYLOAD / "resources/legacy-validate-specs.yml").read_bytes() + b"# local edit\n"
    )
    before = legacy.read_bytes()

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-LEGACY-DIGEST" in {finding.code for finding in plan.findings}
    assert legacy.read_bytes() == before
    assert not (repo / ".standards").exists()


def test_project_spec_provider_uses_resources_from_the_selected_payload_version(
    tmp_path: Path,
) -> None:
    newer_root = tmp_path / "project-spec/versions/1.2"
    shutil.copytree(_PAYLOAD, newer_root)
    template = newer_root / "templates/spec-light-template.md"
    marker = "\n<!-- payload-version-1.2 -->\n"
    template.write_text(template.read_text(encoding="utf-8") + marker, encoding="utf-8")
    template_digest = hashlib.sha256(template.read_bytes()).hexdigest()
    input_schema = newer_root / "schemas/provider-input.schema.json"
    input_schema.write_text(
        input_schema.read_text(encoding="utf-8").replace(
            '"version": { "const": "1.1" }',
            '"version": { "const": "1.2" }',
        ),
        encoding="utf-8",
    )
    input_digest = hashlib.sha256(input_schema.read_bytes()).hexdigest()
    manifest_path = newer_root / "payload.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text = manifest_text.replace('version = "1.1"', 'version = "1.2"', 1)
    manifest_text = manifest_text.replace('to = "package:1.1"', 'to = "package:1.2"')
    manifest_text = manifest_text.replace(
        "sha256:3692873eec9a6f98fc1b64bbb0b0d3ecf807d365a8102305aa5b195c859d8571",
        f"sha256:{template_digest}",
    )
    manifest_text = manifest_text.replace(
        "sha256:c1634043b608303d2a6d2f1284854d9b0a236c78be4e8f9944e67db25a6b58cb",
        f"sha256:{input_digest}",
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")
    newer_manifest = load_payload_manifest(manifest_path)
    newer = InstalledPayload(
        newer_root,
        newer_manifest,
        validate_payload_integrity(newer_root, newer_manifest),
    )
    snapshots: JsonObject = {
        "preview": {
            "operation": "scaffold",
            "profile": "light",
            "spec_id": "SPEC-7F3Q",
            "today": "2026-07-11",
        }
    }

    baseline = _invoke("render-preview", ProviderOperation.RENDER, snapshots=snapshots)
    selected = invoke_provider(
        ProviderInvocation(
            repo=tmp_path,
            payload=newer,
            standard_id="project-spec",
            version=newer.manifest.payload.version,
            provider_id="render-preview",
            operation=ProviderOperation.RENDER,
            effective_config={
                "contract_version": "1.1",
                "include_patterns": ["docs/specs/**/*.md"],
                "reference_prefixes": [],
                "default_profile": "standard",
                "ci": True,
            },
            snapshots=snapshots,
        )
    )
    assert baseline.content is not None and marker.encode() not in baseline.content
    assert selected.content is not None and marker.encode() in selected.content


def test_project_spec_payload_is_byte_identical_and_executable_from_built_wheel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = copy_minimal_repository(tmp_path)
    family = project / "standards/project-spec"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "project-spec"
name = "Project Specification Standard"
summary = "Tiered version-selected project specifications."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    package = project / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    distribution = project / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(distribution)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = distribution.glob("*.whl")
    prefix = "project_standards/payloads/project-spec/1.1/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }
    assert wheel_files == source_files

    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(extracted)
    extracted_root = extracted / prefix
    extracted_manifest = payload.manifest
    extracted_payload = InstalledPayload(
        extracted_root,
        extracted_manifest,
        validate_payload_integrity(extracted_root, extracted_manifest),
    )
    provider_repo = tmp_path / "provider-consumer"
    provider_repo.mkdir()
    example = (_PAYLOAD / "examples/spec.example.md").read_bytes()
    upgrade_source = (_ROOT / "tests/fixtures/specs/upgrade_light.md").read_bytes()

    def document(content: bytes = example) -> JsonObject:
        return {
            "path": "docs/specs/example.md",
            "kind": "regular",
            "content_base64": base64.b64encode(content).decode("ascii"),
        }

    new_target = SafeRelativePath.parse("new.md")
    new_entry = RepositorySnapshot.capture(provider_repo, (new_target,)).entries[0]
    upgrade_target = SafeRelativePath.parse("upgraded.md")
    upgrade_entry = RepositorySnapshot.capture(provider_repo, (upgrade_target,)).entries[0]
    cases: dict[str, tuple[ProviderOperation, JsonObject]] = {
        "validate": (ProviderOperation.VALIDATE, {"documents": [document()]}),
        "lint": (ProviderOperation.LINT, {"documents": [document()]}),
        "extract": (
            ProviderOperation.EXTRACT,
            {"document": document(), "selector": "§7"},
        ),
        "id-next": (
            ProviderOperation.ID_NEXT,
            {"document": document(), "prefix": "FR"},
        ),
        "scaffold": (
            ProviderOperation.SCAFFOLD,
            {
                "authoring": {
                    "target": new_target.original,
                    "kind": "missing",
                    "precondition_digest": new_entry.precondition_digest.value,
                    "mode": "0644",
                    "overwrite": False,
                    "profile": "light",
                    "spec_id": "SPEC-7F3Q",
                    "today": "2026-07-11",
                }
            },
        ),
        "upgrade": (
            ProviderOperation.UPGRADE,
            {
                "authoring": {
                    "target": upgrade_target.original,
                    "kind": "missing",
                    "precondition_digest": upgrade_entry.precondition_digest.value,
                    "mode": "0644",
                    "overwrite": False,
                    "content_base64": base64.b64encode(upgrade_source).decode("ascii"),
                    "target_profile": "standard",
                }
            },
        ),
        "render-workflow": (ProviderOperation.RENDER, {}),
        "render-preview": (
            ProviderOperation.RENDER,
            {
                "preview": {
                    "operation": "scaffold",
                    "profile": "light",
                    "spec_id": "SPEC-7F3Q",
                    "today": "2026-07-11",
                }
            },
        ),
        "migrate-legacy": (
            ProviderOperation.MIGRATE,
            {
                "legacy_config": {
                    "standards_version": "v4",
                    "spec": {
                        "version": "1.0",
                        "include": ["docs/specs/**/*.md"],
                        "exclude": [],
                    },
                },
                "legacy_signatures": {},
            },
        ),
    }

    def deny_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("wheel payload execution attempted network access")

    monkeypatch.setattr(socket, "socket", deny_network)
    expected_effects = {provider.id: provider.effect for provider in extracted_manifest.providers}
    before = tuple(provider_repo.rglob("*"))
    for selected_payload in (payload, extracted_payload):
        for provider_id, (operation, snapshots) in cases.items():
            result = invoke_provider(
                ProviderInvocation(
                    repo=provider_repo,
                    payload=selected_payload,
                    standard_id="project-spec",
                    version=selected_payload.manifest.payload.version,
                    provider_id=provider_id,
                    operation=operation,
                    effective_config={
                        "contract_version": "1.1",
                        "include_patterns": ["docs/specs/**/*.md"],
                        "reference_prefixes": [],
                        "default_profile": "standard",
                        "ci": True,
                    },
                    snapshots=snapshots,
                )
            )
            assert result.effect is expected_effects[provider_id]
            assert tuple(provider_repo.rglob("*")) == before
