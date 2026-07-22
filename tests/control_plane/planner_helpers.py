from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NotRequired, TypedDict

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.models import CentralLock, ConsumerCatalog, DesiredConfig
from project_standards.control_plane.resolution import ResolutionPayload, ResolutionRequest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import (
    ArtifactPolicy,
    JsonValue,
    PayloadManifest,
    load_option_schema,
)

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"


class ArtifactFixture(TypedDict):
    id: str
    target: str
    content: bytes
    policy: NotRequired[str]
    mode: NotRequired[str | None]
    when_any: NotRequired[list[dict[str, object]]]


class ContributionFixture(TypedDict):
    id: str
    target: str
    adapter: str
    scope: str
    content: NotRequired[bytes]
    provider: NotRequired[str]
    shared_identity: NotRequired[str]
    policy: NotRequired[str]
    when_any: NotRequired[list[dict[str, object]]]
    governing_options: NotRequired[list[str]]


class ExtensionFixture(TypedDict):
    id: str
    option: str
    media_type: str
    path_policy: str
    preferred_root: NotRequired[str]


def digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def write_payload(
    root: Path,
    standard_id: str,
    *,
    version: str = "1.0",
    artifacts: Sequence[ArtifactFixture] = (),
    contributions: Sequence[ContributionFixture] = (),
    extensions: Sequence[ExtensionFixture] = (),
    render_providers: Sequence[str] = (),
    verify_providers: Sequence[str] = (),
    option_properties: Mapping[str, object] | None = None,
) -> InstalledPayload:
    root.mkdir(parents=True)
    schema_properties: dict[str, object] = dict(option_properties or {})
    for extension in extensions:
        schema_properties[str(extension["option"])] = {"type": "string"}
    config_schema = json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": schema_properties,
            "required": sorted(schema_properties),
        },
        sort_keys=True,
    ).encode()
    core_files = {
        "README.md": b"# Fixture\n",
        "agent-summary.md": b"Fixture summary.\n",
        "adopt.md": b"Adopt fixture.\n",
        "config.schema.json": config_schema,
    }
    for relative, content in core_files.items():
        path = root / relative
        path.write_bytes(content)

    resources: list[dict[str, object]] = []
    roles = {
        "README.md": ("readme", "canonical-standard", "text/markdown"),
        "agent-summary.md": ("agent-summary", "agent-summary", "text/markdown"),
        "adopt.md": ("adopt", "adoption-guide", "text/markdown"),
        "config.schema.json": (
            "config-schema",
            "config-schema",
            "application/schema+json",
        ),
    }
    for relative, content in core_files.items():
        resource_id, role, media_type = roles[relative]
        resources.append(
            {
                "id": resource_id,
                "role": role,
                "path": relative,
                "media_type": media_type,
                "digest": digest(content),
            }
        )

    artifact_rows: list[dict[str, object]] = []
    for item in artifacts:
        artifact_id = str(item["id"])
        source = f"artifacts/{artifact_id}.bin"
        content = item["content"]
        path = root / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        artifact_row: dict[str, object] = {
            "id": artifact_id,
            "target": item["target"],
            "source": source,
            "digest": digest(content),
            "policy": item.get("policy", ArtifactPolicy.MANAGED.value),
            "mode": item.get("mode", "0644"),
        }
        if "when_any" in item:
            artifact_row["when_any"] = item["when_any"]
        artifact_rows.append(artifact_row)

    contribution_rows: list[dict[str, object]] = []
    for item in contributions:
        contribution_id = str(item["id"])
        contribution_row: dict[str, object] = {
            "id": contribution_id,
            "target": item["target"],
            "adapter": item["adapter"],
            "scope": item["scope"],
            "policy": item.get("policy", ArtifactPolicy.MANAGED.value),
        }
        if "shared_identity" in item:
            contribution_row["shared_identity"] = item["shared_identity"]
        if "when_any" in item:
            contribution_row["when_any"] = item["when_any"]
        if "governing_options" in item:
            contribution_row["governing_options"] = item["governing_options"]
        provider = item.get("provider")
        if provider is not None:
            contribution_row["provider"] = provider
        else:
            source = f"contributions/{contribution_id}.txt"
            content = item.get("content")
            if content is None:
                raise ValueError("static contribution fixture requires content")
            path = root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            contribution_row["source"] = source
            contribution_row["source_digest"] = digest(content)
        contribution_rows.append(contribution_row)

    providers: list[dict[str, object]] = [
        {
            "id": provider_id,
            "operation": "render",
            "kind": "documentation-only",
            "phase": "plan",
            "effect": "content",
            "resources": [],
        }
        for provider_id in render_providers
    ]
    providers.extend(
        {
            "id": provider_id,
            "operation": "verify",
            "kind": "documentation-only",
            "phase": "verify",
            "effect": "findings",
            "resources": [],
        }
        for provider_id in verify_providers
    )
    manifest = PayloadManifest.model_validate(
        {
            "schema_version": "1.0",
            "payload": {
                "standard": standard_id,
                "version": version,
                "availability": "consumer",
            },
            "config": {"schema_resource": "config-schema"},
            "capabilities": {"provides": [], "consumes_platform": []},
            "resources": resources,
            "artifacts": artifact_rows,
            "contributions": contribution_rows,
            "providers": providers,
            "extensions": list(extensions),
        }
    )
    (root / "payload.toml").write_text("fixture = true\n", encoding="utf-8")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def resolution_request(
    payloads: Sequence[InstalledPayload],
    *,
    configs: Mapping[str, Mapping[str, JsonValue]] | None = None,
    previous_lock: CentralLock | None = None,
) -> ResolutionRequest:
    catalog_standards: dict[str, object] = {}
    desired_standards: dict[str, object] = {}
    resolution_payloads: list[ResolutionPayload] = []
    for payload in payloads:
        identity = payload.manifest.payload
        standard_id = identity.standard
        version = identity.version.value
        catalog_standards[standard_id] = {
            "status": "active",
            "available": [version],
            "default": version,
            "candidates": [],
            "versions": {
                version: {
                    "channel": "stable",
                    "availability": "consumer",
                    "payload_digest": payload.integrity.aggregate_digest.value,
                }
            },
        }
        desired_standards[standard_id] = {
            "enabled": True,
            "version": "latest",
            "config": dict((configs or {}).get(standard_id, {})),
        }
        resolution_payloads.append(
            ResolutionPayload(
                standard_id=standard_id,
                version=identity.version,
                payload_digest=payload.integrity.aggregate_digest,
                option_schema=load_option_schema(payload.root, payload.manifest),
            )
        )
    catalog = ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "digest": _DIGEST_A,
            },
            "standards": catalog_standards,
        }
    )
    desired = DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": desired_standards,
        }
    )
    lock = previous_lock or CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": _DIGEST_A,
                "config_digest": _DIGEST_B,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": [],
        }
    )
    return ResolutionRequest(
        desired=desired,
        catalog=catalog,
        previous_lock=lock,
        allowed_majors=frozenset(),
        payloads=tuple(resolution_payloads),
        transition_paths=frozenset(),
    )


def locked_unit(
    *,
    path: str,
    adapter: str,
    scope: str,
    owners: Sequence[str],
    semantic_digest: str,
    content_digest: str,
    created_container: bool = True,
) -> dict[str, object]:
    return {
        "path": path,
        "adapter": adapter,
        "scope": scope,
        "owners": list(owners),
        "versions": dict.fromkeys(owners, "1.0"),
        "provenance": "source",
        "policy": "managed",
        "semantic_digest": semantic_digest,
        "content_digest": content_digest,
        "mode": "0644" if adapter == "whole-file" else None,
        "created_container": created_container,
    }


def previous_lock(*artifacts: Mapping[str, object]) -> CentralLock:
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": _DIGEST_A,
                "config_digest": _DIGEST_B,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": list(artifacts),
            "referenced_inputs": [],
        }
    )


def sha(value: str) -> Sha256Digest:
    return Sha256Digest(value)
