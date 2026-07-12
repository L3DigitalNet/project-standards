from __future__ import annotations

import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from project_standards.control_plane.codec import parse_catalog
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.models import CentralLock, DesiredConfig
from project_standards.control_plane.resolution import (
    ResolutionPayload,
    ResolutionRequest,
    resolve_packages,
)
from project_standards.package_contract import (
    PackageRepository,
    PackageVersion,
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
    render_consumer_catalog,
    validate_catalog_source,
)
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    PayloadAvailability,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ProviderPhase,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from project_standards.package_contract.repository import LoadedFamily
from tests.package_contract.helpers import clone_demo_family, copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/python-coding"
_PAYLOAD = _FAMILY / "versions/0.5"
_DIGEST = f"sha256:{'a' * 64}"
_MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def _assert_local_markdown_links_stay_within_payload(payload_root: Path) -> None:
    resolved_root = payload_root.resolve()
    for document in payload_root.glob("*.md"):
        text = document.read_text(encoding="utf-8")
        for raw_target in _MARKDOWN_LINK.findall(text):
            path_text = raw_target.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(resolved_root), (
                f"{document.name} link escapes the relocatable payload: {raw_target}"
            )
            assert target.is_file(), f"{document.name} link is missing: {raw_target}"


def _isolated_repository(tmp_path: Path) -> Path:
    root = copy_minimal_repository(tmp_path)
    clone_demo_family(root, "python-tooling")
    family = root / "standards/python-coding"
    shutil.copytree(_FAMILY, family)
    payload_manifest = family / "versions/0.5/payload.toml"
    assert payload_manifest.is_file()
    manifest = load_payload_manifest(payload_manifest)
    integrity = validate_payload_integrity(family / "versions/0.5", manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "python-coding"
name = "Python Coding Standard"
summary = "Reference guidance for Python code shape, boundaries, typing, tests, and agent behavior."
status = "draft"

[[versions]]
version = "0.5"
payload = "versions/0.5/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    return root


def _repository(tmp_path: Path) -> tuple[Path, PackageRepository]:
    root = _isolated_repository(tmp_path)
    repository = build_package_repository(
        root,
        family_allowlist={"python-coding", "python-tooling"},
    )
    assert validate_package_repository(repository) == ()
    return root, repository


def _python_coding(repository: PackageRepository) -> LoadedFamily:
    return next(
        family for family in repository.families if family.manifest.standard.id == "python-coding"
    )


def test_python_coding_reconstructs_one_reference_only_payload(tmp_path: Path) -> None:
    assert _PAYLOAD.is_dir()
    _root, repository = _repository(tmp_path)
    family = _python_coding(repository)
    payload = family.payloads[0]
    manifest = payload.manifest

    assert [entry.version.value for entry in family.manifest.versions] == ["0.5"]
    assert manifest.payload.availability is PayloadAvailability.REFERENCE_ONLY
    assert manifest.relations.companions == ["python-tooling"]
    assert manifest.relations.extends == []
    assert manifest.relations.conflicts == []
    assert manifest.artifacts == []
    assert manifest.contributions == []
    assert manifest.extensions == []
    assert manifest.migrations == []
    assert {resource.role for resource in manifest.resources} == {
        "canonical-standard",
        "agent-summary",
        "config-schema",
    }
    assert {resource.path.original for resource in manifest.resources} == {
        "README.md",
        "agent-summary.md",
        "config.schema.json",
    }
    assert len(manifest.providers) == 1
    provider = manifest.providers[0]
    assert (
        provider.operation,
        provider.kind,
        provider.phase,
        provider.effect,
        provider.entrypoint,
    ) == (
        ProviderOperation.SEMANTIC_REVIEW,
        ProviderKind.DOCUMENTATION_ONLY,
        ProviderPhase.VALIDATE,
        ProviderEffect.FINDINGS,
        None,
    )

    option_schema = json.loads((_PAYLOAD / "config.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(option_schema)
    assert option_schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {},
    }


def test_python_coding_is_visible_but_cannot_be_enabled_or_write(tmp_path: Path) -> None:
    _root, repository = _repository(tmp_path)
    family = _python_coding(repository)
    payload = family.payloads[0]
    catalog_source = CatalogSource(
        schema_version="1.0",
        catalog_major=5,
        packages=[
            CatalogPackageEntry(
                id="python-coding",
                version=PackageVersion("0.5"),
                digest=payload.integrity.aggregate_digest,
                role=CatalogRole.REFERENCE_ONLY,
            )
        ],
    )
    assert (
        validate_catalog_source(
            catalog_source,
            repository.family_map,
            repository.payload_map,
        )
        == catalog_source
    )
    rendered = render_consumer_catalog(
        catalog_source,
        repository.family_map,
        repository.payload_map,
        tool_release="5.0.0",
    )
    catalog = parse_catalog(rendered)
    assert catalog.standards["python-coding"].default is None
    assert catalog.standards["python-coding"].available == [PackageVersion("0.5")]

    desired = DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": {"python-coding": {"enabled": True, "version": "latest", "config": {}}},
        }
    )
    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": catalog.project_standards.digest,
                "config_digest": _DIGEST,
            }
        }
    )
    request = ResolutionRequest(
        desired=desired,
        catalog=catalog,
        previous_lock=lock,
        allowed_majors=frozenset(),
        payloads=(
            ResolutionPayload(
                standard_id="python-coding",
                version=payload.manifest.payload.version,
                payload_digest=payload.integrity.aggregate_digest,
                option_schema=load_option_schema(_PAYLOAD, payload.manifest),
            ),
        ),
        transition_paths=frozenset(),
    )
    with pytest.raises(ControlPlaneError, match="not consumer-selectable"):
        resolve_packages(request)
    assert payload.manifest.artifacts == []
    assert payload.manifest.contributions == []


def test_python_coding_payload_is_byte_identical_in_built_wheel(tmp_path: Path) -> None:
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
    prefix = "project_standards/payloads/python-coding/0.5/"
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


def test_python_coding_source_markdown_links_are_relocatable() -> None:
    _assert_local_markdown_links_stay_within_payload(_PAYLOAD)
