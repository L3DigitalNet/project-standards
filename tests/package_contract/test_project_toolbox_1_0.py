"""Package-contract proof for Project Toolbox 1.0, the family's sole version.

Every other family in this catalog has a predecessor in-repo, so its contract
test pins a successor's byte-level diff against that predecessor (see
`test_agent_handoff_1_15.py` for the shape this mirrors). Project Toolbox has
none: 1.0 is the family's first and only cut, so there is nothing to diff
against. This test instead proves the payload's own declared inventory
(resources, artifacts) against the bytes actually on disk, the aggregate
digest against both the family index and the catalog pin, the projection
symlink farm, and the family-root navigation — the same guarantees the diff
tests give their families, just anchored to the payload directly rather than
to a predecessor.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-toolbox"
_VERSION = _FAMILY / "versions/1.0"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-toolbox/1.0"
_AGGREGATE_DIGEST = "sha256:48020eacd25a34578b6cc9c2cd7314af14bc6a808bd6d21531df29726c754bf8"


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_project_toolbox_1_0__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_VERSION / "payload.toml")
    integrity = validate_payload_integrity(_VERSION, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.0"
    assert integrity.aggregate_digest.value == _AGGREGATE_DIGEST
    assert indexed["1.0"].digest == integrity.aggregate_digest

    # A new family has no predecessor to migrate from (payload.toml's own
    # comment records this as a deliberate omission, not a gap), so no
    # migrations are declared.
    assert manifest.migrations == []

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-toolbox"
    }
    assert roles == {"1.0": "default"}
    assert "| [`project-toolbox`](project-toolbox/README.md) | active | 1.0 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_project_toolbox_1_0__declared_inventory__matches_the_bytes_on_disk() -> None:
    """Pin the resource/artifact declarations against the payload's own README claim
    of "a repository-housekeeping sweep, a drift-detection sweep, and the routing
    skill" plus its two-harness skill-descriptor duplication (ADR 0021, issue #170).
    """
    manifest = load_payload_manifest(_VERSION / "payload.toml")

    resource_paths = {resource.path.normalized.as_posix() for resource in manifest.resources}
    assert resource_paths == {
        "README.md",
        "agent-summary.md",
        "config.schema.json",
        "adopt.md",
    }
    roles = {resource.id: resource.role for resource in manifest.resources}
    assert roles == {
        "readme": "canonical-standard",
        "agent-summary": "agent-summary",
        "config-schema": "config-schema",
        "adopt": "adoption-guide",
    }

    artifact_targets = {
        artifact.id: artifact.target.normalized.as_posix() for artifact in manifest.artifacts
    }
    assert artifact_targets == {
        "workflow-repo-housekeeping": ".standards/packages/project-toolbox/workflows/repo-housekeeping.md",
        "workflow-drift-detection": ".standards/packages/project-toolbox/workflows/drift-detection.md",
        "skill": ".agents/skills/project-toolbox/SKILL.md",
        "skill-openai": ".agents/skills/project-toolbox/agents/openai.yaml",
        "skill-claude": ".claude/skills/project-toolbox/SKILL.md",
        "skill-openai-claude": ".claude/skills/project-toolbox/agents/openai.yaml",
    }
    assert {artifact.policy.value for artifact in manifest.artifacts} == {"managed"}

    # The Claude/Codex skill-descriptor pair must stay byte-identical: both are
    # copies of the same source, gated only by target harness (see payload.toml's
    # own comment). A divergence here would mean the two harnesses see different
    # skill bodies.
    by_id = {artifact.id: artifact for artifact in manifest.artifacts}
    assert by_id["skill"].source == by_id["skill-claude"].source
    assert by_id["skill"].digest == by_id["skill-claude"].digest
    assert by_id["skill-openai"].source == by_id["skill-openai-claude"].source
    assert by_id["skill-openai"].digest == by_id["skill-openai-claude"].digest

    # Every declared resource and artifact digest must match the bytes actually
    # committed at its declared path, not just an internally-consistent aggregate.
    for resource in manifest.resources:
        digest_hex = resource.digest.value.removeprefix("sha256:")
        actual = hashlib.sha256((_VERSION / resource.path.normalized).read_bytes()).hexdigest()
        assert actual == digest_hex, f"{resource.path.normalized} digest mismatch"
    for artifact in manifest.artifacts:
        digest_hex = artifact.digest.value.removeprefix("sha256:")
        actual = hashlib.sha256((_VERSION / artifact.source.normalized).read_bytes()).hexdigest()
        assert actual == digest_hex, f"{artifact.source.normalized} digest mismatch"

    assert manifest.relations.companions == []
    assert manifest.relations.extends == []
    assert manifest.relations.conflicts == []
    assert manifest.capabilities.provides == ["project-toolbox.workflows"]
    assert manifest.capabilities.consumes_platform == ["project-standards.reconcile"]


def test_project_toolbox_1_0__schemas__carry_no_dangling_payload_reference() -> None:
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []


def test_project_toolbox_1_0__payload_projection__matches_the_versioned_source() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_VERSION).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the 1.0 payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
