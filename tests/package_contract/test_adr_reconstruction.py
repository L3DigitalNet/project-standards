from __future__ import annotations

import base64
import re
import shutil
import subprocess
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import apply_legacy_migration, plan_legacy_migration
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract import (
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import clone_demo_family, copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/adr"
_PAYLOAD = _FAMILY / "versions/1.1"
_ZERO_DIGEST = Sha256Digest(f"sha256:{'0' * 64}")
_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def _isolated_repository(tmp_path: Path, *, with_frontmatter: bool) -> Path:
    root = copy_minimal_repository(tmp_path)
    if with_frontmatter:
        clone_demo_family(root, "markdown-frontmatter")
    family = root / "standards/adr"
    shutil.copytree(_FAMILY, family)
    manifest = load_payload_manifest(family / "versions/1.1/payload.toml")
    integrity = validate_payload_integrity(family / "versions/1.1", manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "adr"
name = "Architecture Decision Record Standard"
summary = "MADR-based architecture decision records with optional section validation."
status = "active"

[[versions]]
version = "1.1"
payload = "versions/1.1/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    return root


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return InstalledPayload(_PAYLOAD, manifest, validate_payload_integrity(_PAYLOAD, manifest))


def _frontmatter_payload() -> InstalledPayload:
    root = _ROOT / "standards/markdown-frontmatter/versions/1.2"
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    fixture.mkdir()
    repository = _isolated_repository(fixture, with_frontmatter=True)
    payload = _payload()
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "adr"
version = "1.1"
digest = "{payload.integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _snapshot(path: str, content: bytes) -> JsonObject:
    return {
        "path": path,
        "kind": "regular",
        "mode": "0644",
        "content_base64": base64.b64encode(content).decode("ascii"),
        "precondition_digest": _ZERO_DIGEST.value,
    }


def test_adr_options_are_closed_and_complete() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    schema = load_option_schema(_PAYLOAD, manifest)

    assert schema.resolve_options({}) == {
        "contract_version": "1.0",
        "require_sections": False,
    }
    assert schema.resolve_options({"contract_version": "1.0", "require_sections": True}) == {
        "contract_version": "1.0",
        "require_sections": True,
    }
    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options({"unknown": True})
    with pytest.raises(PackageContractError, match="package options violate schema"):
        schema.resolve_options({"contract_version": "2.0"})


def test_adr_payload_declares_scaffold_providers_and_companion_only() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    resources = {resource.role for resource in manifest.resources}
    providers = {
        provider.id: (provider.operation, provider.effect) for provider in manifest.providers
    }

    assert resources >= {
        "canonical-standard",
        "adoption-guide",
        "agent-summary",
        "config-schema",
        "provider-resource",
        "template",
        "example",
    }
    assert manifest.relations.companions == ["markdown-frontmatter"]
    assert manifest.relations.extends == []
    assert manifest.relations.conflicts == []
    assert "markdown-frontmatter" not in manifest.capabilities.consumes_platform
    assert [
        (artifact.target.original, artifact.policy.value) for artifact in manifest.artifacts
    ] == [("docs/adr/adr.template.md", "create-only")]
    assert providers == {
        "migrate-legacy": (ProviderOperation.MIGRATE, ProviderEffect.MIGRATION_REPORT),
        "validate-adr": (ProviderOperation.VALIDATE, ProviderEffect.FINDINGS),
    }


def test_adr_validates_as_an_independent_package(tmp_path: Path) -> None:
    repository = build_package_repository(
        _isolated_repository(tmp_path, with_frontmatter=True),
        family_allowlist={"adr", "markdown-frontmatter"},
    )

    assert validate_package_repository(repository) == ()
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))
    assert plan.applicable, plan.findings


def test_adr_legacy_provider_maps_yaml_without_fragment_output(tmp_path: Path) -> None:
    payload = _payload()
    manifest_digest = payload.manifest.legacy_signatures[0].known_content_digests[0].value
    repo = tmp_path / "consumer"
    repo.mkdir()

    result = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="adr",
            version=payload.manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config={},
            snapshots={
                "legacy_config": {
                    "standards_version": "v4",
                    "markdown": {"adr": {"version": "1.0", "require_sections": True}},
                },
                "legacy_signatures": {
                    "legacy-adr-template": {
                        "docs/adr/adr.template.md": {
                            "known": True,
                            "digest": manifest_digest,
                        }
                    }
                },
            },
        )
    )

    assert result.migration_report is not None
    assert result.migration_report.package.config == {
        "contract_version": "1.0",
        "require_sections": True,
    }
    assert result.migration_report.package.recognized_settings == (
        "/markdown/adr/require_sections",
        "/markdown/adr/version",
    )
    assert [claim.disposition.value for claim in result.migration_report.claims] == ["preserve"]
    assert not any(path.name.endswith("fragment.yml") for path in _PAYLOAD.rglob("*"))


def test_adr_validate_provider_uses_immutable_snapshots_and_option(tmp_path: Path) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    repo.mkdir()
    content = b"""---
doc_type: adr
---
# Decision

## Context and Problem Statement
"""
    snapshots: JsonObject = {"documents": [_snapshot("docs/adr/adr-0001-example.md", content)]}

    enabled = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="adr",
            version=payload.manifest.payload.version,
            provider_id="validate-adr",
            operation=ProviderOperation.VALIDATE,
            effective_config={"contract_version": "1.0", "require_sections": True},
            snapshots=snapshots,
        )
    )
    disabled = invoke_provider(
        ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id="adr",
            version=payload.manifest.payload.version,
            provider_id="validate-adr",
            operation=ProviderOperation.VALIDATE,
            effective_config={"contract_version": "1.0", "require_sections": False},
            snapshots=snapshots,
        )
    )

    assert {finding.identity for finding in enabled.findings} == {
        "Considered Options",
        "Decision Outcome",
    }
    assert disabled.findings == ()
    assert list(repo.iterdir()) == []


def test_adr_composes_with_frontmatter_without_requiring_it(tmp_path: Path) -> None:
    adr = _payload()
    frontmatter = _frontmatter_payload()
    repo = tmp_path / "consumer"
    repo.mkdir()

    adr_only = plan_reconciliation(
        PlannerRequest(repo, resolution_request((adr,)), (adr, frontmatter))
    )
    together = plan_reconciliation(
        PlannerRequest(
            repo,
            resolution_request((adr, frontmatter)),
            (adr, frontmatter),
        )
    )

    assert adr_only.applicable, adr_only.findings
    assert together.applicable, together.findings
    assert adr_only.resolution.packages[0].standard_id == "adr"


def test_adr_fresh_apply_disable_and_second_apply_preserve_create_only_scaffold(
    tmp_path: Path,
) -> None:
    payload = _payload()
    repo = tmp_path / "consumer"
    control = repo / ".standards"
    control.mkdir(parents=True)
    resolution = resolution_request((payload,))
    (control / "lock.toml").write_bytes(render_lock(resolution.previous_lock))
    request = PlannerRequest(repo, resolution, (payload,))
    first = plan_reconciliation(request)

    applied = apply_reconciliation(ApplyRequest(request, first))

    assert applied.success
    scaffold = repo / "docs/adr/adr.template.md"
    assert scaffold.read_bytes() == (_PAYLOAD / "templates/adr.md").read_bytes()
    second_resolution = resolution_request((payload,), previous_lock=first.next_lock)
    second = plan_reconciliation(PlannerRequest(repo, second_resolution, (payload,)))
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )

    disabled_package = second_resolution.desired.standards["adr"].model_copy(
        update={"enabled": False}
    )
    disabled_desired = second_resolution.desired.model_copy(
        update={"standards": {"adr": disabled_package}}
    )
    disabled_resolution = replace(second_resolution, desired=disabled_desired)
    disabled_request = PlannerRequest(repo, disabled_resolution, (payload,))
    disabled = plan_reconciliation(disabled_request)
    assert any(
        action.kind is ActionKind.PRESERVE and action.target == "docs/adr/adr.template.md"
        for action in disabled.actions
    )
    assert apply_reconciliation(ApplyRequest(disabled_request, disabled)).success
    assert scaffold.is_file()


def test_adr_real_v4_migration_applies_and_converges(tmp_path: Path) -> None:
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text(
        """standards_version: v4
markdown:
  adr:
    version: '1.0'
    require_sections: true
""",
        encoding="utf-8",
    )
    scaffold = repo / "docs/adr/adr.template.md"
    scaffold.parent.mkdir(parents=True)
    shutil.copy2(_PAYLOAD / "templates/adr.md", scaffold)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    result = apply_legacy_migration(plan)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    assert scaffold.read_bytes() == (_PAYLOAD / "templates/adr.md").read_bytes()
    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )


def test_adr_payload_docs_have_only_relocatable_local_links() -> None:
    root = _PAYLOAD.resolve()
    for document in _PAYLOAD.rglob("*.md"):
        for raw in _LINK.findall(document.read_text(encoding="utf-8")):
            path_text = raw.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(root), raw
            assert target.exists(), raw


def test_adr_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
    project = _isolated_repository(tmp_path, with_frontmatter=True)
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
    prefix = "project_standards/payloads/adr/1.1/"
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
