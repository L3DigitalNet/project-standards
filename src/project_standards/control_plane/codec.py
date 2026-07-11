"""Canonical semantic digests and TOML codecs for consumer control-plane state."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib

from pydantic import ValidationError

from project_standards.control_plane.diagnostics import (
    ControlPlaneError,
    validation_summary,
)
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    VersionSelector,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import JsonValue

_BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$", re.ASCII)


def _canonical_json(value: JsonValue) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ControlPlaneError("semantic value is not canonical JSON") from exc


def semantic_digest(value: JsonValue) -> Sha256Digest:
    """Hash one validated semantic value using the plan-pinned JSON encoding."""
    return Sha256Digest(f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}")


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_key(value: str) -> str:
    return value if _BARE_TOML_KEY.fullmatch(value) else _toml_string(value)


def _toml_array(values: list[str] | tuple[str, ...]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _selector(value: VersionSelector) -> str:
    return value.value if isinstance(value, PackageVersion) else value


def _finish(lines: list[str]) -> bytes:
    return ("\n".join(lines).rstrip() + "\n").encode()


def render_empty_config(catalog: CatalogMajor | str) -> bytes:
    """Render the exact neutral desired-state scaffold for one catalog major."""
    major = catalog if isinstance(catalog, CatalogMajor) else CatalogMajor(catalog)
    return _finish(
        [
            "[project_standards]",
            'schema_version = "1.0"',
            f"catalog = {_toml_string(major.value)}",
        ]
    )


def _render_catalog(catalog: ConsumerCatalog, *, digest: Sha256Digest | None) -> bytes:
    header = catalog.project_standards
    lines = [
        "[project_standards]",
        'schema_version = "1.0"',
        f"catalog = {_toml_string(header.catalog.value)}",
        f"release = {_toml_string(header.release)}",
    ]
    if digest is not None:
        lines.append(f"digest = {_toml_string(digest.value)}")
    lines.append("")

    for standard_id, standard in catalog.standards.items():
        prefix = f"standards.{_toml_key(standard_id)}"
        lines.extend(
            [
                f"[{prefix}]",
                f"status = {_toml_string(standard.status.value)}",
                f"available = {_toml_array([item.value for item in standard.available])}",
            ]
        )
        if standard.default is not None:
            lines.append(f"default = {_toml_string(standard.default.value)}")
        lines.extend(
            [
                f"candidates = {_toml_array([item.value for item in standard.candidates])}",
                "",
            ]
        )
        for version, entry in standard.versions.items():
            lines.extend(
                [
                    f"[{prefix}.versions.{_toml_string(version)}]",
                    f"channel = {_toml_string(entry.channel.value)}",
                    f"availability = {_toml_string(entry.availability.value)}",
                    f"payload_digest = {_toml_string(entry.payload_digest.value)}",
                    "",
                ]
            )
    return _finish(lines)


def _catalog_digest(catalog: ConsumerCatalog) -> Sha256Digest:
    content = _render_catalog(catalog, digest=None)
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


def bind_catalog_digest(catalog: ConsumerCatalog) -> ConsumerCatalog:
    """Return the catalog with its digest rebound to all other canonical facts."""
    header = catalog.project_standards.model_copy(update={"digest": _catalog_digest(catalog)})
    return catalog.model_copy(update={"project_standards": header})


def render_catalog(catalog: ConsumerCatalog) -> bytes:
    """Render a catalog whose declared self-digest matches its canonical facts."""
    expected = _catalog_digest(catalog)
    if catalog.project_standards.digest != expected:
        raise ControlPlaneError("catalog digest does not match canonical catalog content")
    return _render_catalog(catalog, digest=expected)


def _render_inline_versions(versions: dict[str, PackageVersion]) -> str:
    entries = [
        f"{_toml_key(owner)} = {_toml_string(version.value)}" for owner, version in versions.items()
    ]
    return "{ " + ", ".join(entries) + " }"


def render_lock(lock: CentralLock) -> bytes:
    """Render complete applied state in deterministic, reviewable TOML."""
    header = lock.project_standards
    lines = [
        "[project_standards]",
        'schema_version = "1.0"',
        f"catalog = {_toml_string(header.catalog.value)}",
        f"release = {_toml_string(header.release)}",
        f"catalog_digest = {_toml_string(header.catalog_digest.value)}",
        f"config_digest = {_toml_string(header.config_digest.value)}",
        "",
    ]
    for standard_id, package in lock.standards.items():
        lines.extend(
            [
                f"[standards.{_toml_key(standard_id)}]",
                f"requested = {_toml_string(_selector(package.requested))}",
                f"resolved = {_toml_string(package.resolved.value)}",
                f"selection = {_toml_string(package.selection.value)}",
                f"payload_digest = {_toml_string(package.payload_digest.value)}",
                f"effective_config_digest = {_toml_string(package.effective_config_digest.value)}",
                "",
            ]
        )
    for standard_id, track in lock.accepted_tracks.items():
        lines.extend(
            [
                f"[accepted_tracks.{_toml_key(standard_id)}]",
                f"major = {track.major}",
                f"authorized_catalog = {_toml_string(track.authorized_catalog.value)}",
                "",
            ]
        )
    for artifact in lock.artifacts:
        lines.extend(
            [
                "[[artifacts]]",
                f"path = {_toml_string(artifact.path.original)}",
                f"adapter = {_toml_string(artifact.adapter.value)}",
                f"scope = {_toml_string(artifact.scope)}",
                f"owners = {_toml_array(artifact.owners)}",
                f"versions = {_render_inline_versions(artifact.versions)}",
                f"provenance = {_toml_string(artifact.provenance.value)}",
                f"policy = {_toml_string(artifact.policy.value)}",
                f"semantic_digest = {_toml_string(artifact.semantic_digest.value)}",
                f"content_digest = {_toml_string(artifact.content_digest.value)}",
            ]
        )
        if artifact.mode is not None:
            lines.append(f"mode = {_toml_string(artifact.mode)}")
        lines.extend(
            [
                f"created_container = {'true' if artifact.created_container else 'false'}",
                "",
            ]
        )
    for referenced in lock.referenced_inputs:
        lines.extend(
            [
                "[[referenced_inputs]]",
                f"standard_id = {_toml_string(referenced.standard_id)}",
                f"extension_id = {_toml_string(referenced.extension_id)}",
                f"path = {_toml_string(referenced.path.original)}",
                f"digest = {_toml_string(referenced.digest.value)}",
                "",
            ]
        )
    return _finish(lines)


def _load_toml(content: bytes, *, kind: str) -> dict[str, object]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError(f"{kind} is not valid UTF-8") from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ControlPlaneError(f"{kind} is not valid TOML") from exc


def parse_config(content: bytes) -> DesiredConfig:
    """Parse desired configuration without echoing rejected consumer values."""
    try:
        return DesiredConfig.model_validate(_load_toml(content, kind="config"))
    except ValidationError as exc:
        raise ControlPlaneError(f"config violates its schema: {validation_summary(exc)}") from exc


def parse_catalog(content: bytes) -> ConsumerCatalog:
    """Parse and verify a canonical catalog snapshot and its self-digest."""
    try:
        catalog = ConsumerCatalog.model_validate(_load_toml(content, kind="catalog"))
    except ValidationError as exc:
        raise ControlPlaneError(f"catalog violates its schema: {validation_summary(exc)}") from exc
    if catalog.project_standards.digest != _catalog_digest(catalog):
        raise ControlPlaneError("catalog digest does not match canonical catalog content")
    if render_catalog(catalog) != content:
        raise ControlPlaneError("catalog is not in canonical form")
    return catalog


def parse_lock(content: bytes) -> CentralLock:
    """Parse complete central applied state and require canonical encoding."""
    try:
        lock = CentralLock.model_validate(_load_toml(content, kind="lock"))
    except ValidationError as exc:
        raise ControlPlaneError(f"lock violates its schema: {validation_summary(exc)}") from exc
    if render_lock(lock) != content:
        raise ControlPlaneError("lock is not in canonical form")
    return lock
