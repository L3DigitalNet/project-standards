"""Locked, bounded edits and read-only views for consumer desired state."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter, ValidationError

from project_standards.control_plane.adapters.base import UnitChange
from project_standards.control_plane.adapters.toml import (
    TomlAdapter,
    TomlStatement,
    scan_toml_statements,
)
from project_standards.control_plane.codec import (
    parse_catalog,
    parse_config,
    parse_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import (
    InstalledDistribution,
    resolution_payloads,
)
from project_standards.control_plane.locking import (
    LockedControlDirectory,
    LockMode,
    control_plane_lock,
    reserved_temporary_name,
)
from project_standards.control_plane.models import (
    AppliedPackage,
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
)
from project_standards.control_plane.resolution import ResolutionPayload
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import KebabId
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import JsonValue

_ID_ADAPTER = cast("TypeAdapter[str]", TypeAdapter(KebabId))


def _standard_id(value: str) -> str:
    try:
        return _ID_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ControlPlaneError("standard ID must use canonical kebab-case") from exc


def _selector(value: str) -> str:
    if value == "latest":
        return value
    try:
        return PackageVersion(value).value
    except ValueError as exc:
        raise ControlPlaneError("version must be latest or canonical MAJOR.MINOR") from exc


def _target_assignment(
    statements: tuple[TomlStatement, ...],
    standard_id: str,
    key: str,
) -> TomlStatement | None:
    matches = [
        statement
        for statement in statements
        if statement.kind == "assignment"
        and statement.key is not None
        and (*statement.table, *statement.key) == ("standards", standard_id, key)
    ]
    if len(matches) > 1:
        raise ControlPlaneError("desired config contains a duplicate package field")
    return matches[0] if matches else None


def _quoted_like(existing: str, value: str) -> str:
    stripped = existing.strip()
    if stripped.startswith("'") and stripped.endswith("'"):
        return f"'{value}'"
    return json.dumps(value, ensure_ascii=False)


def _append_standard(
    text: str,
    standard_id: str,
    *,
    enabled: bool,
    version: str,
) -> str:
    prefix = text if text.endswith("\n") else f"{text}\n"
    return (
        f"{prefix}\n[standards.{standard_id}]\n"
        f"enabled = {'true' if enabled else 'false'}\n"
        f"version = {json.dumps(version)}\n"
    )


def _replace_value(text: str, statement: TomlStatement, value: str) -> str:
    return f"{text[: statement.value_start]}{value}{text[statement.value_end :]}"


def _replace_values(
    text: str,
    replacements: list[tuple[TomlStatement, str]],
) -> str:
    updated = text
    for statement, value in sorted(
        replacements,
        key=lambda item: item[0].value_start,
        reverse=True,
    ):
        updated = _replace_value(updated, statement, value)
    return updated


def _changed_config_leaves(
    before: JsonValue,
    after: JsonValue,
    prefix: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], bool, JsonValue]]:
    if isinstance(before, dict) and isinstance(after, dict):
        removed = set(before) - set(after)
        if removed:
            raise ControlPlaneError("configuration transform cannot remove a package option")
        changes: list[tuple[tuple[str, ...], bool, JsonValue]] = []
        for key, value in after.items():
            if key not in before:
                if isinstance(value, dict):
                    changes.extend(_changed_config_leaves({}, value, (*prefix, key)))
                else:
                    changes.append(((*prefix, key), False, value))
            else:
                changes.extend(_changed_config_leaves(before[key], value, (*prefix, key)))
        return changes
    if semantic_digest(before) == semantic_digest(after):
        return []
    return [(prefix, True, after)]


def _toml_scalar(value: JsonValue) -> bytes:
    if value is None or isinstance(value, (dict, list)):
        raise ControlPlaneError("configuration transform must change a TOML scalar leaf")
    rendered = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return rendered.encode()


def _json_pointer(path: tuple[str, ...]) -> str:
    return "/" + "/".join(component.replace("~", "~0").replace("/", "~1") for component in path)


def changed_package_config_pointers(
    before: dict[str, JsonValue],
    after: dict[str, JsonValue],
) -> tuple[str, ...]:
    """Return canonical changed leaf pointers, rejecting removals."""
    return tuple(
        sorted(
            (
                _json_pointer(path)
                for path, _present, _value in _changed_config_leaves(before, after)
            ),
            key=str.encode,
        )
    )


def render_package_config_transform(
    original: bytes,
    standard_id: str,
    transformed_config: dict[str, JsonValue],
    declared_pointers: tuple[str, ...],
) -> bytes:
    """Render one allowlisted package-config leaf diff without normalizing the file."""
    normalized_id = _standard_id(standard_id)
    desired = parse_config(original)
    package = desired.standards.get(normalized_id)
    if package is None:
        raise ControlPlaneError("configuration transform package is absent from desired state")
    changes = sorted(
        _changed_config_leaves(package.config, transformed_config),
        key=lambda item: _json_pointer(item[0]).encode(),
    )
    declared = set(declared_pointers)
    pointers = set(changed_package_config_pointers(package.config, transformed_config))
    if not pointers.issubset(declared):
        raise ControlPlaneError("configuration transform changed an undeclared option")
    base = ("standards", normalized_id, "config")
    unit_changes = tuple(
        UnitChange(
            kind=ActionKind.UPDATE if present else ActionKind.CREATE,
            scope="key:" + _json_pointer((*base, *path)),
            content=_toml_scalar(value),
            value=value,
        )
        for path, present, value in changes
    )
    adapter = TomlAdapter()
    rendered = original
    for change in unit_changes:
        state = adapter.inspect(rendered, (change.scope,))
        rendered = adapter.render(state, (change,))
    parsed = parse_config(rendered)
    expected_package = package.model_copy(update={"config": transformed_config})
    expected = desired.model_copy(
        update={
            "standards": {
                **desired.standards,
                normalized_id: expected_package,
            }
        }
    )
    parsed_json = cast(JsonValue, parsed.model_dump(mode="json"))
    expected_json = cast(JsonValue, expected.model_dump(mode="json"))
    if semantic_digest(parsed_json) != semantic_digest(expected_json):
        raise ControlPlaneError("configuration transform changed unrelated desired state")
    return rendered


def _atomic_replace_config(
    control: LockedControlDirectory,
    content: bytes,
) -> None:
    temporary = reserved_temporary_name()
    try:
        current_mode = (
            os.stat(
                "config.toml",
                dir_fd=control.descriptor,
                follow_symlinks=False,
            ).st_mode
            & 0o7777
        )
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=control.descriptor,
        )
    except OSError as exc:
        raise ControlPlaneError("desired config could not be staged") from exc
    try:
        os.fchmod(descriptor, current_mode)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("zero-byte write while staging desired config")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except OSError as exc:
        os.close(descriptor)
        with suppress(OSError):
            os.unlink(temporary, dir_fd=control.descriptor)
        raise ControlPlaneError("desired config could not be staged") from exc
    os.close(descriptor)
    if not control.is_current():
        with suppress(OSError):
            os.unlink(temporary, dir_fd=control.descriptor)
        raise ControlPlaneError("control-plane directory changed during config edit")
    try:
        os.replace(
            temporary,
            "config.toml",
            src_dir_fd=control.descriptor,
            dst_dir_fd=control.descriptor,
        )
        os.fsync(control.descriptor)
    except OSError as exc:
        with suppress(OSError):
            os.unlink(temporary, dir_fd=control.descriptor)
        raise ControlPlaneError("desired config could not be replaced atomically") from exc


def _edit_config(
    repo: Path,
    standard_id: str,
    edit: Callable[[str, tuple[TomlStatement, ...], str], str],
) -> DesiredConfig:
    normalized_id = _standard_id(standard_id)
    try:
        with control_plane_lock(repo, LockMode.WRITE) as control:
            content = control.read_bytes("config.toml")
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ControlPlaneError("desired config is not valid UTF-8") from exc
            parse_config(content)
            statements = scan_toml_statements(text)
            updated = edit(text, statements, normalized_id)
            parsed = parse_config(updated.encode())
            if updated != text:
                _atomic_replace_config(control, updated.encode())
            return parsed
    except ControlPlaneError:
        raise
    except ValueError as exc:
        raise ControlPlaneError("desired config could not be edited safely") from exc


def set_standard_enabled(repo: Path, standard_id: str, enabled: bool) -> DesiredConfig:
    """Set one package's enabled flag while preserving every unrelated byte."""

    return set_standard_selection(repo, standard_id, enabled=enabled)


def set_standard_selection(
    repo: Path,
    standard_id: str,
    *,
    enabled: bool | None = None,
    version: str | None = None,
) -> DesiredConfig:
    """Apply one atomic package selection edit through bounded value splices."""
    normalized_version = _selector(version) if version is not None else None

    def edit(text: str, statements: tuple[TomlStatement, ...], normalized_id: str) -> str:
        enabled_target = _target_assignment(statements, normalized_id, "enabled")
        version_target = _target_assignment(statements, normalized_id, "version")
        if enabled_target is None and version_target is None:
            return _append_standard(
                text,
                normalized_id,
                enabled=enabled if enabled is not None else False,
                version=normalized_version or "latest",
            )
        if enabled_target is None or version_target is None:
            raise ControlPlaneError("desired package record is incomplete")
        replacements: list[tuple[TomlStatement, str]] = []
        if enabled is not None:
            replacements.append((enabled_target, "true" if enabled else "false"))
        if normalized_version is not None:
            existing = text[version_target.value_start : version_target.value_end]
            replacements.append((version_target, _quoted_like(existing, normalized_version)))
        return _replace_values(text, replacements)

    return _edit_config(repo, standard_id, edit)


def set_standard_version(repo: Path, standard_id: str, version: str) -> DesiredConfig:
    """Set one package selector while preserving enablement, options, and layout."""
    return set_standard_selection(repo, standard_id, version=version)


def load_control_state(repo: Path) -> tuple[DesiredConfig, ConsumerCatalog, CentralLock]:
    """Load desired, catalog, and applied facts under one shared directory lock."""
    try:
        with control_plane_lock(repo, LockMode.READ) as control:
            return (
                parse_config(control.read_bytes("config.toml")),
                parse_catalog(control.read_bytes("catalog.toml")),
                parse_lock(control.read_bytes("lock.toml")),
            )
    except ControlPlaneError:
        raise
    except ValueError as exc:
        raise ControlPlaneError("control-plane state could not be inspected") from exc


def _config_paths(
    value: dict[str, JsonValue],
    prefix: tuple[str, ...] = (),
) -> list[str]:
    paths: list[str] = []
    for key, child in value.items():
        path = (*prefix, key)
        if isinstance(child, dict):
            paths.extend(_config_paths(child, path))
        else:
            paths.append(".".join(path))
    return paths


def _applied_option_schemas(
    config: DesiredConfig,
    catalog: ConsumerCatalog,
    lock: CentralLock,
    distribution: InstalledDistribution | None,
) -> dict[tuple[str, str], ResolutionPayload]:
    """Return installed payload facts for resolving applied packages' effective options.

    Loading the wheel is skipped entirely when nothing is applied, so the common
    inspection and edit paths on an unreconciled repository stay free of payload
    integrity verification. An installation that cannot be verified degrades to an
    empty mapping rather than failing inspection; every caller then falls back to
    the as-authored digest.
    """
    if not lock.standards:
        return {}
    try:
        selected = distribution or InstalledDistribution.current()
        installed = selected.load_catalog(
            config.project_standards.catalog,
            recorded_release=catalog.project_standards.release,
        )
    except PackageContractError, OSError, ValueError:
        return {}
    return {
        (payload.standard_id, payload.version.value): payload
        for payload in resolution_payloads(installed)
    }


def _package_config_digest(
    standard_id: str,
    package_config: dict[str, JsonValue],
    applied: AppliedPackage | None,
    schemas: Mapping[tuple[str, str], ResolutionPayload],
) -> str:
    """Digest package options the way the lock's resolution digested them.

    The lock authenticates the schema-resolved effective configuration
    (`resolve_packages` in resolution.py), so reporting the raw as-authored
    configuration made `standards show` contradict the lock whenever a schema
    supplied defaults. Packages the lock does not authenticate - disabled, never
    reconciled, or applied from a payload this installation cannot reproduce
    byte-for-byte - keep the as-authored digest: the lock records no effective
    digest for them, so no comparison can be contradicted.
    """
    authored = semantic_digest(cast(JsonValue, package_config)).value
    if applied is None:
        return authored
    payload = schemas.get((standard_id, applied.resolved.value))
    if payload is None or payload.payload_digest != applied.payload_digest:
        return authored
    try:
        effective = payload.option_schema.resolve_options(package_config)
    except PackageContractError:
        return authored
    return semantic_digest(cast(JsonValue, effective)).value


def standard_views(
    repo: Path,
    *,
    distribution: InstalledDistribution | None = None,
) -> list[dict[str, object]]:
    """Return deterministic JSON-safe catalog, desired, and applied package facts."""
    config, catalog, lock = load_control_state(repo)
    schemas = _applied_option_schemas(config, catalog, lock, distribution)
    views: list[dict[str, object]] = []
    for standard_id, standard in catalog.standards.items():
        desired = config.standards.get(standard_id)
        applied = lock.standards.get(standard_id)
        selectable = any(
            entry.availability.value == "consumer" for entry in standard.versions.values()
        )
        availability = sorted({entry.availability.value for entry in standard.versions.values()})
        requested: str | None = None
        if desired is not None:
            requested = (
                desired.version if isinstance(desired.version, str) else desired.version.value
            )
        package_config = desired.config if desired is not None else {}
        views.append(
            {
                "id": standard_id,
                "status": standard.status.value,
                "selectable": selectable,
                "availability": availability,
                "available": [version.value for version in standard.available],
                "default": standard.default.value if standard.default is not None else None,
                "candidates": [version.value for version in standard.candidates],
                "enabled": desired.enabled if desired is not None else False,
                "requested": requested,
                "resolved": applied.resolved.value if applied is not None else None,
                "config_paths": _config_paths(package_config),
                "config_digest": _package_config_digest(
                    standard_id,
                    package_config,
                    applied,
                    schemas,
                ),
            }
        )
    return views
