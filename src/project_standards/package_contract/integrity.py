"""Complete payload inventory and canonical aggregate-digest validation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import (
    SafeRelativePath,
    Sha256Digest,
    validate_path_collection,
)
from project_standards.package_contract.payload import PayloadManifest

_HASH_CHUNK_SIZE = 1024 * 1024
_MEDIA_SUFFIXES: dict[str, frozenset[str]] = {
    "application/json": frozenset({".json"}),
    "application/schema+json": frozenset({".json"}),
    "application/toml": frozenset({".toml"}),
    "application/yaml": frozenset({".yaml", ".yml"}),
    "text/markdown": frozenset({".md"}),
    "text/x-python": frozenset({".py"}),
}


@dataclass(frozen=True, slots=True)
class PayloadInventoryEntry:
    """Bind one canonical payload-relative path to its raw-byte digest."""

    path: SafeRelativePath
    digest: Sha256Digest


@dataclass(frozen=True, slots=True)
class PayloadIntegrity:
    """Return the verified manifest, complete inventory, and aggregate identities."""

    manifest_digest: Sha256Digest
    aggregate_digest: Sha256Digest
    inventory: tuple[PayloadInventoryEntry, ...]


def _sha256_file(path: Path) -> Sha256Digest:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(_HASH_CHUNK_SIZE):
                digest.update(chunk)
    except OSError as exc:
        raise PackageContractError(f"payload file could not be read: {path}") from exc
    return Sha256Digest(f"sha256:{digest.hexdigest()}")


def aggregate_inventory_digest(
    entries: Iterable[PayloadInventoryEntry],
) -> Sha256Digest:
    """Hash the complete path-sorted `PATH NUL DIGEST LF` inventory."""
    materialized = tuple(entries)
    try:
        validate_path_collection(entry.path for entry in materialized)
    except ValueError as exc:
        raise PackageContractError("aggregate inventory contains a path collision") from exc
    ordered = sorted(
        materialized,
        key=lambda entry: entry.path.normalized.as_posix().encode("utf-8"),
    )
    digest = hashlib.sha256()
    for entry in ordered:
        digest.update(entry.path.normalized.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry.digest.value.encode("ascii"))
        digest.update(b"\n")
    return Sha256Digest(f"sha256:{digest.hexdigest()}")


def _declared_files(
    manifest: PayloadManifest,
) -> dict[str, tuple[Sha256Digest, str]]:
    declared: dict[str, tuple[Sha256Digest, str]] = {}

    def add(path: SafeRelativePath, digest: Sha256Digest, identity: str) -> None:
        normalized = path.normalized.as_posix()
        if normalized == "payload.toml" or normalized in declared:
            raise PackageContractError(
                f"{manifest.payload.standard}@{manifest.payload.version.value}: "
                f"duplicate file declaration for {normalized}"
            )
        declared[normalized] = (digest, identity)

    for resource in manifest.resources:
        suffixes = _MEDIA_SUFFIXES.get(resource.media_type)
        if suffixes is not None and resource.path.normalized.suffix.lower() not in suffixes:
            raise PackageContractError(
                f"{manifest.payload.standard}@{manifest.payload.version.value} "
                f"resource:{resource.id}: media type does not match its path"
            )
        add(resource.path, resource.digest, f"resource:{resource.id}")
    for artifact in manifest.artifacts:
        add(artifact.source, artifact.digest, f"artifact:{artifact.id}")
    for contribution in manifest.contributions:
        if contribution.source is not None and contribution.source_digest is not None:
            add(
                contribution.source,
                contribution.source_digest,
                f"contribution:{contribution.id}",
            )
    return declared


def _live_files(payload_dir: Path) -> dict[str, Path]:
    try:
        if payload_dir.is_symlink() or not payload_dir.is_dir():
            raise PackageContractError("payload root must be a regular directory")
        entries = sorted(payload_dir.rglob("*"), key=lambda path: path.as_posix().encode("utf-8"))
    except OSError as exc:
        raise PackageContractError("payload directory could not be inventoried") from exc

    live: dict[str, Path] = {}
    normalized_paths: list[SafeRelativePath] = []
    for entry in entries:
        relative_path = entry.relative_to(payload_dir)
        relative_text = relative_path.as_posix()
        if "__pycache__" in relative_path.parts:
            if entry.is_dir() or entry.suffix == ".pyc":
                continue
            raise PackageContractError(
                f"payload inventory contains undeclared cache content: {relative_text}"
            )
        try:
            relative = SafeRelativePath.parse(relative_text)
        except ValueError as exc:
            raise PackageContractError("payload inventory contains a non-portable path") from exc
        if entry.is_symlink():
            raise PackageContractError(f"payload inventory contains a symlink: {relative_text}")
        try:
            if entry.is_dir():
                continue
            if not entry.is_file():
                raise PackageContractError(
                    f"payload inventory contains an unsupported file type: {relative_text}"
                )
        except OSError as exc:
            raise PackageContractError(
                f"payload inventory entry could not be inspected: {relative_text}"
            ) from exc
        normalized_paths.append(relative)
        live[relative_text] = entry
    try:
        validate_path_collection(normalized_paths)
    except ValueError as exc:
        raise PackageContractError("payload inventory contains a path collision") from exc
    return live


def validate_payload_integrity(
    payload_dir: Path,
    manifest: PayloadManifest,
    *,
    expected_digest: Sha256Digest | None = None,
) -> PayloadIntegrity:
    """Verify every payload byte before returning its canonical aggregate identity."""
    declared = _declared_files(manifest)
    live = _live_files(payload_dir)
    expected_paths = set(declared) | {"payload.toml"}
    live_paths = set(live)
    missing = sorted(expected_paths - live_paths)
    if missing:
        raise PackageContractError(
            f"{manifest.payload.standard}@{manifest.payload.version.value}: "
            f"missing declared file {missing[0]}"
        )
    undeclared = sorted(live_paths - expected_paths)
    if undeclared:
        raise PackageContractError(
            f"{manifest.payload.standard}@{manifest.payload.version.value}: "
            f"undeclared file {undeclared[0]}"
        )

    inventory: list[PayloadInventoryEntry] = []
    for path_text, (declared_digest, identity) in declared.items():
        actual_digest = _sha256_file(live[path_text])
        if actual_digest != declared_digest:
            raise PackageContractError(
                f"{manifest.payload.standard}@{manifest.payload.version.value} "
                f"{identity}: digest mismatch for {path_text}"
            )
        inventory.append(
            PayloadInventoryEntry(
                path=SafeRelativePath.parse(path_text),
                digest=actual_digest,
            )
        )

    manifest_digest = _sha256_file(live["payload.toml"])
    inventory.append(
        PayloadInventoryEntry(
            path=SafeRelativePath.parse("payload.toml"),
            digest=manifest_digest,
        )
    )
    ordered = tuple(sorted(inventory, key=lambda entry: entry.path.original.encode("utf-8")))
    aggregate = aggregate_inventory_digest(ordered)
    if expected_digest is not None and aggregate != expected_digest:
        raise PackageContractError(
            f"{manifest.payload.standard}@{manifest.payload.version.value}: "
            "aggregate digest does not match the family index"
        )
    return PayloadIntegrity(
        manifest_digest=manifest_digest,
        aggregate_digest=aggregate,
        inventory=ordered,
    )
