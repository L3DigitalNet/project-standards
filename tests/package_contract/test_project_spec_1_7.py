"""Contract for the Project Specification 1.7 caller-runner-selection successor.

1.7 adds the optional `runner-labels` input and the setup-uv 9.0.0 pin with
`prune-cache: true` to the self-hosted validation workflow, and appends the new
`sha256:52e058a3` generation to both digest-history chains — the payload's
`legacy-workflow` `known_content_digests` and the provider's own self-host set —
so a consumer still carrying the 1.6 render authenticates rather than tripping an
unknown-content refusal. `adopt.md` gains the SL-STRUCTURE troubleshooting row
for the strict-lint gate landed in the same release.

1.11 superseded 1.7 as the source of this repository's rendered root workflow (the
setup-uv v10 advance, issue #201), so nothing here compares 1.7's resource with
`.github/workflows/validate-specs.yml` any more: that file now carries bytes 1.7's
digest chain cannot know. Root-workflow parity with whichever payload the catalog
marks `default` is asserted catalog-derived in `test_project_spec_reconstruction`.
What 1.7 still owes is its own immutable bytes and their declared digests.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_PREDECESSOR = _FAMILY / "versions/1.6"
_SUCCESSOR = _FAMILY / "versions/1.7"
_PROJECTION = _ROOT / "src/project_standards/payloads/project-spec/1.7"
_PREDECESSOR_DIGEST = "sha256:0f3bc8952fe4ef58e7619fecf1476ebd863a6cbb4eddf93bdbdea758f835be4c"
_WORKFLOW_RESOURCE = "resources/self-host-validate-specs.yml"
_V1_6_WORKFLOW_DIGEST = "sha256:77fda8d63f55b3f2715b0c47b55ccd6306071fa6541d7b5a57decd1291e2c7bb"
_V1_7_WORKFLOW_DIGEST = "sha256:52e058a3de21ef4a89b4fbe3e877b000b07badbd2af5646ea0f4c82caabb2401"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/project_spec.py",
        _WORKFLOW_RESOURCE,
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def test_project_spec_1_7__successor__preserves_1_6_and_indexes_complete_payload() -> None:
    """The successor changes only versioned identity, provider, and workflow bytes."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in payload_tree(_PREDECESSOR)
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in payload_tree(_SUCCESSOR)
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

    assert successor_manifest.payload.version.value == "1.7"
    assert [migration.id for migration in successor_manifest.migrations] == ["legacy-v4-to-1-7"]
    assert [migration.to_endpoint.value for migration in successor_manifest.migrations] == [
        "package:1.7"
    ]


def test_project_spec_1_7__workflow_resource__carries_the_generation_it_declares() -> None:
    """The resource bytes, its manifest digest, and the 1.7 generation agree.

    A released resource is immutable, so the v9.0.0 pin below is a contract and not
    a snapshot: advancing it is what a new cut is for, and editing it here would
    silently re-key every consumer authenticating against `_V1_7_WORKFLOW_DIGEST`.
    """
    workflow = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    resource = next(item for item in manifest.resources if item.id == "self-host-workflow")
    assert resource.digest.value == f"sha256:{hashlib.sha256(workflow).hexdigest()}"
    assert resource.digest.value == _V1_7_WORKFLOW_DIGEST

    text = workflow.decode("utf-8")
    assert "runner-labels:" in text
    assert "uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0" in text
    assert "prune-cache: true" in text


def test_project_spec_1_7__digest_history__still_authenticates_the_1_6_generation() -> None:
    """Appending a generation must not orphan consumers carrying the previous render."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    legacy_signature = next(
        item for item in manifest.legacy_signatures if item.id == "legacy-workflow"
    )
    known = {digest.value for digest in legacy_signature.known_content_digests}

    assert {_V1_6_WORKFLOW_DIGEST, _V1_7_WORKFLOW_DIGEST} <= known

    provider_source = (_SUCCESSOR / "providers/project_spec.py").read_text(encoding="utf-8")
    assert _V1_6_WORKFLOW_DIGEST in provider_source
    assert _V1_7_WORKFLOW_DIGEST in provider_source


def test_project_spec_1_7__identity_documents_and_schemas__name_the_successor() -> None:
    for relative in ("README.md", "adopt.md", "agent-summary.md"):
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "1.6" not in document
        assert "1.7" in document

    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.7"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.7"


def test_project_spec_1_7__catalog_role__stays_retained_behind_the_successor() -> None:
    """1.7 keeps an advertised, non-default row once 1.8 takes the default.

    Which version currently holds `default` is asserted catalog-derived in
    test_catalog_roles.py, not re-pinned by any per-version module.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "project-spec"
    }

    assert roles["1.7"] == "retained"
    assert roles["1.6"] == "retained"
    assert roles["1.5"] == "retained"


def test_project_spec_1_7__payload_projection__matches_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_project_spec_1_7__family_index__keeps_the_retained_version_selectable() -> None:
    """Naming 1.8 as the current authority must not drop 1.7 from the family index.

    Family navigation now points at 1.8 (see `test_project_spec_1_8`); what 1.7
    still owes a consumer holding an exact pin is an advertised, digest-bound
    row.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert indexed["1.7"].digest == integrity.aggregate_digest


def test_project_spec_1_7__migration__recognizes_its_own_pinned_workflow() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    payload = InstalledPayload(
        _SUCCESSOR,
        manifest,
        validate_payload_integrity(_SUCCESSOR, manifest),
    )
    # The 1.7-era render, not the live root file: since the 1.11 reconcile the root
    # workflow carries the setup-uv v10 bytes, a generation 1.7's chain cannot know.
    # A consumer still holding the 1.7 render is exactly who this classification is
    # for, so migrating from the payload's own resource is the real case.
    workflow = (_SUCCESSOR / _WORKFLOW_RESOURCE).read_bytes()
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
