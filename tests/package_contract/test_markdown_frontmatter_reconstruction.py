from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.models import DesiredConfig
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.package_contract import (
    PackageRepository,
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_option_schema, load_payload_manifest
from project_standards.package_contract.repository import LoadedFamily
from tests.control_plane.planner_helpers import resolution_request
from tests.package_contract.helpers import clone_demo_family, copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PAYLOAD = _FAMILY / "versions/1.2"


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
