"""Contract for the Project Specification 1.6 workflow-pinning successor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.5"
_SUCCESSOR = _FAMILY / "versions/1.6"
_PREDECESSOR_DIGEST = "sha256:e4286963cf591e3ee1454e5be317519b6610d3257dc61eb08de489d47ba407e1"
_SELF_HOST_WORKFLOW_DIGEST = (
    "sha256:77fda8d63f55b3f2715b0c47b55ccd6306071fa6541d7b5a57decd1291e2c7bb"
)
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/project_spec.py",
        "resources/self-host-validate-specs.yml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def test_project_spec_1_6__successor__pins_the_root_workflow_and_preserves_1_5() -> None:
    """The corrective payload changes only versioned identity and workflow bytes."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.6"
    assert indexed["1.6"].digest == successor_integrity.aggregate_digest
    assert [migration.id for migration in successor_manifest.migrations] == ["legacy-v4-to-1-6"]
    assert [migration.to_endpoint.value for migration in successor_manifest.migrations] == [
        "package:1.6"
    ]

    # 1.7 supersedes this resource as the root workflow's source (runner-labels
    # input, setup-uv v9 bump); 1.6 stays advertised/retained with its own bytes
    # unchanged, so this no longer asserts equality with the live root workflow.
    workflow = (_SUCCESSOR / "resources/self-host-validate-specs.yml").read_bytes()
    resource = next(
        item for item in successor_manifest.resources if item.id == "self-host-workflow"
    )
    assert resource.digest.value == f"sha256:{hashlib.sha256(workflow).hexdigest()}"
    assert resource.digest.value == _SELF_HOST_WORKFLOW_DIGEST


def test_project_spec_1_6__identity_documents_and_schemas__name_the_successor() -> None:
    for relative in ("README.md", "adopt.md", "agent-summary.md"):
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "1.5" not in document
        assert "1.6" in document

    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.6"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.6"


def test_project_spec_1_6__family_index__keeps_the_retained_version_selectable() -> None:
    """Naming 1.7 as the current authority must not drop 1.6 from the family index.

    Family navigation now points at 1.7 (see `test_project_spec_1_7`); what 1.6
    still owes a consumer holding an exact pin is an advertised, digest-bound row.
    """
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")

    assert (
        indexed["1.6"].digest == validate_payload_integrity(_SUCCESSOR, manifest).aggregate_digest
    )


def test_project_spec_1_6__migration__recognizes_its_own_pinned_workflow() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    payload = InstalledPayload(
        _SUCCESSOR,
        manifest,
        validate_payload_integrity(_SUCCESSOR, manifest),
    )
    # The 1.6-era render, not the live root file: after the v5.16.0 reconcile the
    # root workflow carries 1.7's bytes, whose digest 1.6's chain cannot know.
    workflow = (_SUCCESSOR / "resources/self-host-validate-specs.yml").read_bytes()
    workflow_digest = f"sha256:{hashlib.sha256(workflow).hexdigest()}"
    legacy_signature = next(
        item for item in manifest.legacy_signatures if item.id == "legacy-workflow"
    )
    assert workflow_digest in {digest.value for digest in legacy_signature.known_content_digests}
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="project-spec",
            version=manifest.payload.version,
            provider_id="migrate-legacy",
            operation=ProviderOperation.MIGRATE,
            effective_config=load_option_schema(_SUCCESSOR, manifest).resolve_options(
                {}  # type: ignore[arg-type]
            ),
            snapshots={
                "legacy_config": {"spec": {}},
                "legacy_signatures": {
                    "legacy-workflow": {
                        ".github/workflows/validate-specs.yml": {
                            "known": True,
                            "digest": workflow_digest,
                        }
                    }
                },
            },
        )
    )

    assert result.migration_report is not None
    assert result.migration_report.package.config == {"workflow_mode": "self-hosted"}
