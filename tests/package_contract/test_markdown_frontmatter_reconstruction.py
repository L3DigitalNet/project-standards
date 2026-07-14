from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import (
    ApplyRequest,
    apply_authoring_plan,
    apply_reconciliation,
)
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.models import DesiredConfig
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.control_plane.snapshot import RepositorySnapshot
from project_standards.package_contract import (
    PackageRepository,
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.package_contract.repository import LoadedFamily
from project_standards.validate_frontmatter import validate_file
from project_standards.validate_id import check_file
from project_standards.validate_references import (
    build_index,
    check_adr_sequence,
    check_dates,
    check_id_uniqueness,
    check_reciprocity,
    check_references,
)
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import clone_demo_family, copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_WORKFLOW = (
    _ROOT / "tests/fixtures/package_compatibility/legacy/validate-markdown-frontmatter.yml"
)
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PAYLOAD = _FAMILY / "versions/1.2"
_MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_ZERO_DIGEST = f"sha256:{'0' * 64}"
_HISTORICAL_WORKFLOW_DIGEST = (
    "sha256:82a9ef1cb1e4f48eddc4a6cc43f317ba93aebe6d485fed6d8736e8e9e0aa279e"
)
_CURRENT_WORKFLOW_DIGEST = "sha256:09eb0cc6d6fe20a12b7c7cc5022f9a902ed29d0cdf35ef42c8685c5c93cea036"


def _snapshot_document(path: str, content: bytes) -> JsonObject:
    return {
        "path": path,
        "kind": "regular",
        "mode": "0644",
        "content_base64": base64.b64encode(content).decode("ascii"),
        "precondition_digest": _ZERO_DIGEST,
    }


def _frontmatter_document(
    document_id: str,
    *,
    title: str,
    doc_type: str = "note",
    created: str = "2026-01-01",
    updated: str = "2026-01-02",
    reviewed: str | None = None,
    related: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
    superseded_by: str | None = None,
) -> bytes:
    metadata: dict[str, object] = {
        "schema_version": "1.1",
        "id": document_id,
        "title": title,
        "description": "Fixture document.",
        "doc_type": doc_type,
        "status": "active",
        "created": created,
        "updated": updated,
        "tags": [],
        "aliases": [],
        "related": list(related),
    }
    if reviewed is not None:
        metadata["reviewed"] = reviewed
    if depends_on:
        metadata["depends_on"] = list(depends_on)
    if supersedes:
        metadata["supersedes"] = list(supersedes)
    if superseded_by is not None:
        metadata["superseded_by"] = superseded_by
    lines = ["---", *[f"{key}: {json.dumps(value)}" for key, value in metadata.items()], "---"]
    return ("\n".join(lines) + "\n# Body\n").encode()


def _assert_local_markdown_links_stay_within_payload(payload_root: Path) -> None:
    resolved_root = payload_root.resolve()
    for document in payload_root.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for raw_target in _MARKDOWN_LINK.findall(text):
            path_text = raw_target.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text or "<" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(resolved_root), (
                f"{document.relative_to(payload_root)} link escapes payload: {raw_target}"
            )
            assert target.exists(), (
                f"{document.relative_to(payload_root)} link is missing: {raw_target}"
            )


def _isolated_repository(tmp_path: Path) -> Path:
    root = copy_minimal_repository(tmp_path)
    clone_demo_family(root, "adr")
    clone_demo_family(root, "markdown-tooling")
    family = root / "standards/markdown-frontmatter"
    shutil.copytree(_FAMILY, family)
    manifest = load_payload_manifest(family / "versions/1.2/payload.toml")
    integrity = validate_payload_integrity(family / "versions/1.2", manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-frontmatter"
name = "Markdown Frontmatter Standard"
summary = "Canonical metadata, IDs, references, and formatting for managed Markdown."
status = "active"

[[versions]]
version = "1.2"
payload = "versions/1.2/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    return root


def _repository(tmp_path: Path) -> PackageRepository:
    repository = build_package_repository(
        _isolated_repository(tmp_path),
        family_allowlist={"adr", "markdown-frontmatter", "markdown-tooling"},
    )
    assert validate_package_repository(repository) == ()
    return repository


def _installed_frontmatter_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture_root = tmp_path / "frontmatter-distribution"
    fixture_root.mkdir()
    repository = _isolated_repository(fixture_root)
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    integrity = validate_payload_integrity(_PAYLOAD, manifest)
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "markdown-frontmatter"
version = "1.2"
digest = "{integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture_root / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _frontmatter(repository: PackageRepository) -> LoadedFamily:
    return next(
        family
        for family in repository.families
        if family.manifest.standard.id == "markdown-frontmatter"
    )


def test_frontmatter_options_have_complete_closed_defaults(tmp_path: Path) -> None:
    family = _frontmatter(_repository(tmp_path))
    payload = family.payloads[0]
    schema = load_option_schema(_PAYLOAD, payload.manifest)

    assert payload.manifest.payload.version.value == "1.2"
    assert schema.resolve_options({}) == {
        "contract_version": "1.1",
        "schema": "markdown-frontmatter",
        "schema_path": None,
        "workflow_mode": "caller",
        "required": True,
        "include": ["README.md", "docs/**/*.md"],
        "exclude": [
            "**/*.template.md",
            "AGENTS.md",
            "CLAUDE.md",
            ".agents/**",
            ".claude/**",
            ".codex/**",
            ".github/**",
            "node_modules/**",
        ],
        "references": {"enabled": False},
    }
    assert schema.resolve_options(
        {
            "contract_version": "1.1",
            "schema": "custom",
            "schema_path": ".standards/extensions/markdown-frontmatter/schema.json",
            "required": False,
            "include": ["handbook/**/*.md"],
            "exclude": ["handbook/generated/**"],
            "references": {"enabled": True},
        }
    )["references"] == {"enabled": True}

    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options({"command": "validate-frontmatter"})


def test_package_selector_and_contract_selector_are_independent() -> None:
    desired = DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": {
                "markdown-frontmatter": {
                    "enabled": True,
                    "version": "1.2",
                    "config": {"contract_version": "1.1"},
                }
            },
        }
    )

    package = desired.standards["markdown-frontmatter"]
    assert not isinstance(package.version, str)
    assert package.version.value == "1.2"
    assert package.config["contract_version"] == "1.1"


def test_frontmatter_fresh_plan_composes_workflow_and_managed_skill(tmp_path: Path) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()

    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))

    assert plan.applicable, plan.findings
    workflow = plan.proposed_content(".github/workflows/validate-standards.yml")
    assert workflow is not None
    assert b"frontmatter:" in workflow
    assert b"validate-markdown-frontmatter.yml@v5" in workflow
    assert (
        plan.proposed_content(".agents/skills/markdown-frontmatter/SKILL.md")
        == (_PAYLOAD / "skills/markdown-frontmatter/SKILL.md").read_bytes()
    )


@pytest.mark.parametrize(
    ("workflow_mode", "resource_name", "expected_reference"),
    [
        pytest.param(
            "caller",
            "workflow-job.yml",
            "L3DigitalNet/project-standards/.github/workflows/validate-markdown-frontmatter.yml@v5",
            id="published-ref",
        ),
        pytest.param(
            "self-hosted",
            "workflow-job.self-hosted.yml",
            "./.github/workflows/validate-markdown-frontmatter.yml",
            id="pre-tag-local-ref",
        ),
    ],
)
def test_frontmatter_workflow_modes_render_published_and_pretag_paths(
    tmp_path: Path,
    workflow_mode: str,
    resource_name: str,
    expected_reference: str,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )

    result = invoke_provider(
        ProviderInvocation(
            repo=tmp_path,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="render-workflow-job",
            operation=ProviderOperation.RENDER,
            effective_config={"workflow_mode": workflow_mode},
            snapshots={},
        )
    )

    content = result.content
    assert content == (_PAYLOAD / resource_name).read_bytes()
    assert content is not None
    assert expected_reference.encode() in content
    if workflow_mode == "self-hosted":
        assert b"@v5" not in content


def test_frontmatter_root_workflow_is_the_v5_public_endpoint() -> None:
    root_workflow = _ROOT / ".github/workflows/validate-markdown-frontmatter.yml"
    public_resource = _PAYLOAD / "resources/self-host-validate-markdown-frontmatter.yml"

    root = yaml.safe_load(root_workflow.read_text(encoding="utf-8"))
    public = yaml.safe_load(public_resource.read_text(encoding="utf-8"))
    for event in ("push", "pull_request"):
        root_paths = root[True][event]["paths"]
        assert ".project-standards.yml" in root_paths
    assert set(public[True]) == {"workflow_call"}
    assert root["permissions"] == public["permissions"]
    assert root["jobs"] == public["jobs"]

    for workflow in (root, public):
        call = workflow[True]["workflow_call"]
        assert set(call["inputs"]) == {"standards-ref"}
        assert call["inputs"]["standards-ref"]["default"] == "v5"
        scripts = [
            str(step.get("run", ""))
            for step in workflow["jobs"]["validate"]["steps"]
            if "project-standards validate" in str(step.get("run", ""))
        ]
        assert len(scripts) == 2
        assert all("--config" not in script for script in scripts)


def test_frontmatter_declares_version_selected_validate_inspect_and_fix_providers() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    providers = {provider.id: provider for provider in manifest.providers}
    contracts = {
        provider.id: (provider.operation, provider.phase.value, provider.effect)
        for provider in manifest.providers
    }

    assert contracts == {
        "fix-frontmatter": (
            ProviderOperation.FIX,
            "authoring",
            ProviderEffect.MUTATION_PLAN,
        ),
        "id-next": (ProviderOperation.ID_NEXT, "inspect", ProviderEffect.CONTENT),
        "migrate-legacy": (
            ProviderOperation.MIGRATE,
            "plan",
            ProviderEffect.MIGRATION_REPORT,
        ),
        "render-workflow-job": (
            ProviderOperation.RENDER,
            "plan",
            ProviderEffect.CONTENT,
        ),
        "validate-frontmatter": (
            ProviderOperation.VALIDATE,
            "validate",
            ProviderEffect.FINDINGS,
        ),
    }
    assert providers["validate-frontmatter"].resources == ["frontmatter-schema"]
    assert providers["id-next"].resources == ["frontmatter-schema"]
    assert providers["render-workflow-job"].resources == [
        "workflow-job-caller",
        "workflow-job-self-hosted",
    ]
    assert manifest.migrations[0].affected == [
        "artifact:self-host-workflow",
        "artifact:skill",
        "artifact:skill-new-doc-id",
        "artifact:skill-openai",
        "config:*",
        "contribution:workflow-frontmatter-job",
    ]


def test_frontmatter_fix_provider_returns_complete_plan_without_live_writes(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    document = docs / "example.md"
    original = (
        b"---\n"
        b"schema_version: '1.1'\n"
        b"id: wrong\n"
        b"title: Hello World\n"
        b"description: d\n"
        b"type: note\n"
        b"status: draft\n"
        b"created: '2026-01-01'\n"
        b"updated: '2026-01-02'\n"
        b"tags: []\n"
        b"aliases: []\n"
        b"related: []\n"
        b"---\n# Body\n"
    )
    document.write_bytes(original)
    relative = SafeRelativePath.parse("docs/example.md")
    entry = RepositorySnapshot.capture(repo, (relative,)).entry(relative)
    assert entry.content is not None

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="fix-frontmatter",
            operation=ProviderOperation.FIX,
            effective_config={"contract_version": "1.1", "required": True},
            snapshots={
                "documents": [
                    {
                        "path": relative.original,
                        "kind": entry.kind.value,
                        "mode": entry.mode,
                        "content_base64": base64.b64encode(entry.content).decode("ascii"),
                        "precondition_digest": entry.precondition_digest.value,
                    }
                ],
                "tokens": ["aaaaaa"],
                "today": "2026-07-11",
            },
        )
    )

    assert result.effect is ProviderEffect.MUTATION_PLAN
    assert result.mutation_plan is not None
    assert document.read_bytes() == original
    replacement = result.mutation_plan.actions[0].content_bytes
    assert replacement is not None
    assert b"doc_type: 'note'" in replacement
    assert b"id: 'note-aaaaaa-hello-world'" in replacement
    assert apply_authoring_plan(repo, result.mutation_plan).success
    assert document.read_bytes() == replacement


def test_frontmatter_legacy_migration_maps_yaml_and_exact_signatures(tmp_path: Path) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    signature_digests = {
        signature.id: signature.known_content_digests[0].value
        for signature in manifest.legacy_signatures
    }
    signature_digests["legacy-workflow"] = _HISTORICAL_WORKFLOW_DIGEST

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v4",
                    "markdown": {
                        "frontmatter": {
                            "version": "1.1",
                            "schema": "markdown-frontmatter",
                            "required": True,
                            "include": ["docs/**/*.md"],
                            "exclude": ["README.md"],
                            "references": {"enabled": True},
                        }
                    },
                },
                "legacy_signatures": {
                    "legacy-workflow": {
                        ".github/workflows/validate-markdown-frontmatter.yml": {
                            "digest": signature_digests["legacy-workflow"],
                            "known": True,
                            "content_base64": "",
                        }
                    },
                    "legacy-skill": {
                        ".agents/skills/markdown-frontmatter/SKILL.md": {
                            "digest": signature_digests["legacy-skill"],
                            "known": True,
                            "content_base64": "",
                        }
                    },
                    "legacy-skill-script": {
                        ".agents/skills/markdown-frontmatter/scripts/new-doc-id": {
                            "digest": signature_digests["legacy-skill-script"],
                            "known": True,
                            "content_base64": "",
                        }
                    },
                },
            },
        )
    )

    assert result.migration_report is not None
    report = result.migration_report
    assert report.package.config == {
        "contract_version": "1.1",
        "schema": "markdown-frontmatter",
        "workflow_mode": "self-hosted",
        "required": True,
        "include": ["docs/**/*.md"],
        "exclude": ["**/*.template.md", "README.md"],
        "references": {"enabled": True},
    }
    assert report.package.recognized_settings == (
        "/markdown/frontmatter/exclude",
        "/markdown/frontmatter/include",
        "/markdown/frontmatter/references/enabled",
        "/markdown/frontmatter/required",
        "/markdown/frontmatter/schema",
        "/markdown/frontmatter/version",
    )
    assert {(claim.signature_id, claim.disposition.value) for claim in report.claims} == {
        ("legacy-skill", "adopt"),
        ("legacy-skill-script", "adopt"),
        ("legacy-workflow", "adopt"),
    }


def test_frontmatter_workflow_signature_history_includes_current_v4_release_root() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    signatures = {signature.id: signature for signature in manifest.legacy_signatures}

    assert {digest.value for digest in signatures["legacy-workflow"].known_content_digests} == {
        _HISTORICAL_WORKFLOW_DIGEST,
        _CURRENT_WORKFLOW_DIGEST,
    }
    assert (
        "sha256:"
        + hashlib.sha256(
            (
                _ROOT
                / "tests/fixtures/package_compatibility/legacy/release-root/files/.github/workflows/validate-markdown-frontmatter.yml"
            ).read_bytes()
        ).hexdigest()
        == _CURRENT_WORKFLOW_DIGEST
    )


def test_frontmatter_real_v4_migration_applies_and_converges(tmp_path: Path) -> None:
    distribution = _installed_frontmatter_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
markdown:
  frontmatter:
    version: '1.1'
    schema: markdown-frontmatter
    required: true
    include: ['README.md', 'docs/**/*.md']
    exclude: ['AGENTS.md', '.agents/**']
    references:
      enabled: true
""",
        encoding="utf-8",
    )
    workflow = repo / ".github/workflows/validate-markdown-frontmatter.yml"
    workflow.parent.mkdir(parents=True)
    shutil.copy2(_LEGACY_WORKFLOW, workflow)
    installed_skill = repo / ".agents/skills/markdown-frontmatter"
    installed_skill.mkdir(parents=True)
    shutil.copy2(
        _PAYLOAD / "resources/legacy-markdown-frontmatter-skill.md",
        installed_skill / "SKILL.md",
    )
    (installed_skill / "scripts").mkdir()
    shutil.copy2(
        _FAMILY / "skills/markdown-frontmatter/scripts/new-doc-id",
        installed_skill / "scripts/new-doc-id",
    )

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    assert {
        action.target
        for action in plan.actions
        if action.kind in {ActionKind.UPDATE, ActionKind.REMOVE}
    } >= {
        ".agents/skills/markdown-frontmatter/SKILL.md",
        ".agents/skills/markdown-frontmatter/scripts/new-doc-id",
        ".github/workflows/validate-markdown-frontmatter.yml",
        ".project-standards.yml",
    }
    result = apply_legacy_migration(plan)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    assert (
        workflow.read_bytes()
        == (_PAYLOAD / "resources/self-host-validate-markdown-frontmatter.yml").read_bytes()
    )
    composed = repo / ".github/workflows/validate-standards.yml"
    assert b"./.github/workflows/validate-markdown-frontmatter.yml" in composed.read_bytes()
    assert b"@v5" not in composed.read_bytes()
    assert (installed_skill / "SKILL.md").read_bytes() == (
        _PAYLOAD / "skills/markdown-frontmatter/SKILL.md"
    ).read_bytes()
    assert (installed_skill / "scripts/new-doc-id").read_bytes() == (
        _PAYLOAD / "skills/markdown-frontmatter/scripts/new-doc-id"
    ).read_bytes()
    assert (installed_skill / "agents/openai.yaml").read_bytes() == (
        _PAYLOAD / "skills/markdown-frontmatter/agents/openai.yaml"
    ).read_bytes()
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


@pytest.mark.parametrize(
    "modified_path",
    [
        "SKILL.md",
        "scripts/new-doc-id",
    ],
)
def test_frontmatter_v4_migration_refuses_modified_signed_skill_bytes(
    tmp_path: Path,
    modified_path: str,
) -> None:
    distribution = _installed_frontmatter_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
markdown:
  frontmatter:
    version: '1.1'
    schema: markdown-frontmatter
    required: true
    include: ['README.md', 'docs/**/*.md']
    exclude: ['AGENTS.md', '.agents/**']
""",
        encoding="utf-8",
    )
    workflow = repo / ".github/workflows/validate-markdown-frontmatter.yml"
    workflow.parent.mkdir(parents=True)
    shutil.copy2(_LEGACY_WORKFLOW, workflow)
    installed_skill = repo / ".agents/skills/markdown-frontmatter"
    installed_skill.mkdir(parents=True)
    shutil.copy2(
        _PAYLOAD / "resources/legacy-markdown-frontmatter-skill.md",
        installed_skill / "SKILL.md",
    )
    (installed_skill / "scripts").mkdir()
    shutil.copy2(
        _FAMILY / "skills/markdown-frontmatter/scripts/new-doc-id",
        installed_skill / "scripts/new-doc-id",
    )

    baseline_plan = plan_legacy_migration(repo, distribution, "5")
    assert baseline_plan.applicable, baseline_plan.findings

    changed = installed_skill / modified_path
    changed.write_bytes(changed.read_bytes() + b"\nlocal modification\n")
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


def test_frontmatter_validate_and_id_next_providers_use_snapshot_content(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    document = repo / "note.md"
    document.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'wrong'\n"
        "title: 'Hello World'\n"
        "description: 'd'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-02'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# Body\n",
        encoding="utf-8",
    )
    relative = SafeRelativePath.parse("note.md")
    entry = RepositorySnapshot.capture(repo, (relative,)).entry(relative)
    assert entry.content is not None
    document_snapshot: JsonObject = {
        "path": relative.original,
        "kind": entry.kind.value,
        "mode": entry.mode,
        "content_base64": base64.b64encode(entry.content).decode("ascii"),
        "precondition_digest": entry.precondition_digest.value,
    }

    validation = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="validate-frontmatter",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "schema": "markdown-frontmatter",
                "required": True,
                "references": {"enabled": False},
            },
            snapshots={"documents": [document_snapshot]},
        )
    )
    next_id = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="id-next",
            operation=ProviderOperation.ID_NEXT,
            effective_config={},
            snapshots={
                "doc_type": "note",
                "title": "Hello World",
                "token": "aaaaaa",
            },
        )
    )

    assert [finding.code for finding in validation.findings] == ["FM-ID"]
    assert next_id.content == b"note-aaaaaa-hello-world"


def test_frontmatter_validate_provider_matches_public_schema_date_and_id_passes(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    document = repo / "invalid.md"
    content = b"""---
schema_version: '9.9'
id: wrong
title: ''
description: ''
doc_type: note
status: broken
created: '2026-13-40'
updated: '2026-00-01'
tags: [Bad, Bad]
aliases: []
related: []
unexpected: true
---
# Body
"""
    document.write_bytes(content)
    schema = json.loads(
        (_PAYLOAD / "schemas/markdown-frontmatter.schema.json").read_text(encoding="utf-8")
    )
    public_schema_errors = validate_file(
        document,
        Draft202012Validator(schema),
        require_frontmatter=True,
    )
    public_id_errors = check_file(
        document,
        frozenset(schema["properties"]["doc_type"]["enum"]),
    )

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="validate-frontmatter",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "schema": "markdown-frontmatter",
                "required": True,
                "references": {"enabled": False},
            },
            snapshots={"documents": [_snapshot_document("invalid.md", content)]},
        )
    )

    counts = Counter(finding.code for finding in result.findings)
    calendar_errors = [error for error in public_schema_errors if "real calendar date" in error]
    assert counts["FM-SCHEMA"] == len(public_schema_errors) - len(calendar_errors)
    assert counts["FM-DATE"] == len(calendar_errors)
    assert counts["FM-ID"] == len(public_id_errors)


def test_frontmatter_validate_provider_matches_public_repository_wide_checks(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    docs = repo / "docs"
    docs.mkdir(parents=True)
    corpus = {
        "docs/alpha.md": _frontmatter_document(
            "note-aaaaaa-alpha",
            title="Alpha",
            related=("docs/target.md", "../escape.md", "missing.md", "docs/target.md#part"),
            depends_on=("note-dddddd-missing",),
            supersedes=("note-bbbbbb-beta",),
            superseded_by="note-cccccc-gamma",
        ),
        "docs/alpha-copy.md": _frontmatter_document(
            "note-aaaaaa-alpha",
            title="Alpha copy",
        ),
        "docs/beta.md": _frontmatter_document("note-bbbbbb-beta", title="Beta"),
        "docs/gamma.md": _frontmatter_document("note-cccccc-gamma", title="Gamma"),
        "docs/dates.md": _frontmatter_document(
            "note-dddddd-dates",
            title="Dates",
            created="2026-04-03",
            updated="2026-04-01",
            reviewed="2026-04-02",
        ),
        "docs/adr-one.md": _frontmatter_document(
            "adr-0001-repo-first",
            title="First ADR",
            doc_type="adr",
        ),
        "docs/adr-two.md": _frontmatter_document(
            "adr-00001-repo-second",
            title="Second ADR",
            doc_type="adr",
        ),
        "docs/target.md": _frontmatter_document("note-eeeeee-target", title="Target"),
    }
    for relative, content in corpus.items():
        target = repo / relative
        target.write_bytes(content)
    paths = [repo / relative for relative in corpus]
    index = build_index(paths)
    public_counts = {
        "FM-DUPLICATE-ID": len(check_id_uniqueness(index)),
        "FM-DATE-ORDER": len(check_dates(index)),
        "FM-REFERENCE": len(check_references(index, repo)),
        "FM-RECIPROCITY": len(check_reciprocity(index)),
        "FM-DUPLICATE-ADR": len(check_adr_sequence(index)),
    }

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="validate-frontmatter",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "schema": "markdown-frontmatter",
                "required": True,
                "references": {"enabled": True},
            },
            snapshots={
                "documents": [
                    _snapshot_document(relative, content)
                    for relative, content in sorted(corpus.items())
                ]
            },
        )
    )

    counts = Counter(finding.code for finding in result.findings)
    assert {code: counts[code] for code in public_counts} == public_counts
    reference_identities = {
        finding.identity for finding in result.findings if finding.code == "FM-REFERENCE"
    }
    assert reference_identities == {
        "../escape.md",
        "docs/target.md#part",
        "missing.md",
        "note-dddddd-missing",
    }
    assert "docs/target.md" not in reference_identities
    assert all(
        finding.severity == ("warning" if code in {"FM-REFERENCE", "FM-RECIPROCITY"} else "error")
        for code in public_counts
        for finding in result.findings
        if finding.code == code
    )


def test_frontmatter_validate_provider_reports_malformed_and_nonregular_snapshots(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    malformed = b"---\nid: [broken\n---\n"

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="validate-frontmatter",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "schema": "markdown-frontmatter",
                "required": True,
                "references": {"enabled": True},
            },
            snapshots={
                "documents": [
                    _snapshot_document("malformed.md", malformed),
                    {
                        "path": "directory.md",
                        "kind": "directory",
                        "mode": None,
                        "content_base64": None,
                        "precondition_digest": _ZERO_DIGEST,
                    },
                ]
            },
        )
    )

    assert Counter(finding.code for finding in result.findings) == {
        "FM-PARSE": 1,
        "FM-PATH": 1,
    }


def test_frontmatter_id_next_rejects_doc_type_outside_selected_schema(tmp_path: Path) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()

    with pytest.raises(ControlPlaneError, match="provider failed with ValueError"):
        invoke_provider(
            ProviderInvocation(
                repo=repo,
                payload=payload,
                standard_id="markdown-frontmatter",
                version=manifest.payload.version,
                provider_id="id-next",
                operation=ProviderOperation.ID_NEXT,
                effective_config={},
                snapshots={
                    "doc_type": "blogpost",
                    "title": "Hello World",
                    "token": "aaaaaa",
                },
            )
        )


def test_frontmatter_validate_provider_skips_bundled_id_rules_for_custom_schema(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    document = repo / "custom.md"
    document.write_text(
        "---\nid: custom-id\nrelated: [missing-id]\n---\n# Custom\n",
        encoding="utf-8",
    )
    relative = SafeRelativePath.parse("custom.md")
    entry = RepositorySnapshot.capture(repo, (relative,)).entry(relative)
    assert entry.content is not None
    custom_schema = b'{"type":"object","required":["id"]}'

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="validate-frontmatter",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "schema": "custom",
                "schema_path": ".standards/extensions/markdown-frontmatter/schema.json",
                "required": True,
                "references": {"enabled": True},
            },
            snapshots={
                "documents": [
                    {
                        "path": relative.original,
                        "kind": entry.kind.value,
                        "mode": entry.mode,
                        "content_base64": base64.b64encode(entry.content).decode("ascii"),
                        "precondition_digest": entry.precondition_digest.value,
                    }
                ],
                "referenced_input_content": [
                    {
                        "standard_id": "markdown-frontmatter",
                        "extension_id": "custom-schema",
                        "path": ".standards/extensions/markdown-frontmatter/schema.json",
                        "digest": _ZERO_DIGEST,
                        "content_base64": base64.b64encode(custom_schema).decode("ascii"),
                    }
                ],
            },
        )
    )
    fix = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="markdown-frontmatter",
            version=manifest.payload.version,
            provider_id="fix-frontmatter",
            operation=ProviderOperation.FIX,
            effective_config={"schema": "custom", "required": True},
            snapshots={
                "documents": [
                    {
                        "path": relative.original,
                        "kind": entry.kind.value,
                        "mode": entry.mode,
                        "content_base64": base64.b64encode(entry.content).decode("ascii"),
                        "precondition_digest": entry.precondition_digest.value,
                    }
                ],
                "tokens": ["aaaaaa"],
                "today": "2026-07-11",
            },
        )
    )

    assert result.findings == ()
    assert fix.mutation_plan is not None
    assert fix.mutation_plan.actions == []


def test_frontmatter_fresh_apply_converges_to_a_byte_level_noop(tmp_path: Path) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    control = repo / ".standards"
    control.mkdir(parents=True)
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    request = PlannerRequest(repo, resolution, (payload,))
    first = plan_reconciliation(request)

    result = apply_reconciliation(ApplyRequest(request, first))

    assert result.success
    workflow = repo / ".github/workflows/validate-standards.yml"
    assert workflow.is_file()
    assert b"frontmatter:" in workflow.read_bytes()
    assert (repo / ".agents/skills/markdown-frontmatter/SKILL.md").is_file()
    before = {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }
    second_resolution = resolution_request((payload,), previous_lock=first.next_lock)
    second = plan_reconciliation(PlannerRequest(repo, second_resolution, (payload,)))

    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    assert {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


def test_frontmatter_source_markdown_links_are_relocatable() -> None:
    _assert_local_markdown_links_stay_within_payload(_PAYLOAD)


def test_frontmatter_versioning_distinguishes_package_contract_and_tool_release() -> None:
    readme = (_PAYLOAD / "README.md").read_text(encoding="utf-8")

    assert "Package payload `1.2`" in readme
    assert "Document contract `1.1`" in readme
    assert "Tool/catalog release `5.x`" in readme
    assert "Two version numbers are in play" not in readme


def test_frontmatter_custom_schema_is_tracked_as_consumer_owned_input(
    tmp_path: Path,
) -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    payload = InstalledPayload(
        _PAYLOAD,
        manifest,
        validate_payload_integrity(_PAYLOAD, manifest),
    )
    repo = tmp_path / "consumer"
    schema_path = repo / ".standards/extensions/markdown-frontmatter/schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}\n',
        encoding="utf-8",
    )
    resolution = resolution_request(
        (payload,),
        configs={
            "markdown-frontmatter": {
                "schema": "custom",
                "schema_path": ".standards/extensions/markdown-frontmatter/schema.json",
            }
        },
    )

    plan = plan_reconciliation(PlannerRequest(repo, resolution, (payload,)))

    assert plan.applicable, plan.findings
    assert len(plan.next_lock.referenced_inputs) == 1
    reference = plan.next_lock.referenced_inputs[0]
    assert reference.standard_id == "markdown-frontmatter"
    assert reference.path.original == ".standards/extensions/markdown-frontmatter/schema.json"
    assert schema_path.read_text(encoding="utf-8").startswith('{"$schema"')


def test_frontmatter_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = _isolated_repository(tmp_path)
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
    prefix = "project_standards/payloads/markdown-frontmatter/1.2/"
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {
            name.removeprefix(prefix): archive.read(name)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
        installed = tmp_path / "installed"
        archive.extractall(installed)
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file()
    }

    assert wheel_files == source_files
    _assert_local_markdown_links_stay_within_payload(installed / prefix)
