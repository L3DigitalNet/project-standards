from __future__ import annotations

import hashlib

import pytest

from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_catalog,
    parse_config,
    parse_lock,
    render_catalog,
    render_empty_config,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.models import CentralLock, ConsumerCatalog
from project_standards.package_contract.payload import JsonValue

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"


def _catalog() -> ConsumerCatalog:
    return ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "digest": _DIGEST_A,
            },
            "standards": {
                "zeta": {
                    "status": "review",
                    "available": ["1.0"],
                    "candidates": [],
                    "versions": {
                        "1.0": {
                            "channel": "internal",
                            "availability": "internal",
                            "payload_digest": _DIGEST_B,
                        }
                    },
                },
                "alpha": {
                    "status": "active",
                    "available": ["2.0", "1.2"],
                    "default": "1.2",
                    "candidates": ["2.0"],
                    "versions": {
                        "2.0": {
                            "channel": "breaking-candidate",
                            "availability": "consumer",
                            "payload_digest": _DIGEST_B,
                        },
                        "1.2": {
                            "channel": "stable",
                            "availability": "consumer",
                            "payload_digest": _DIGEST_A,
                        },
                    },
                },
            },
        }
    )


def _lock() -> CentralLock:
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": _DIGEST_A,
                "config_digest": _DIGEST_B,
            },
            "standards": {
                "alpha": {
                    "requested": "latest",
                    "resolved": "1.2",
                    "selection": "stable",
                    "payload_digest": _DIGEST_A,
                    "effective_config_digest": _DIGEST_B,
                }
            },
            "accepted_tracks": {},
            "artifacts": [
                {
                    "path": "pyproject.toml",
                    "adapter": "toml",
                    "scope": "key:/tool/ruff",
                    "owners": ["alpha"],
                    "versions": {"alpha": "1.2"},
                    "provenance": "source",
                    "policy": "managed",
                    "semantic_digest": _DIGEST_A,
                    "content_digest": _DIGEST_B,
                    "mode": "0644",
                    "created_container": False,
                }
            ],
            "referenced_inputs": [
                {
                    "standard_id": "alpha",
                    "extension_id": "options",
                    "path": ".standards/extensions/alpha/options.toml",
                    "digest": _DIGEST_A,
                }
            ],
        }
    )


def _legacy_empty_lock_content() -> bytes:
    return (
        b"[project_standards]\n"
        b'schema_version = "1.0"\n'
        b'catalog = "5"\n'
        b'release = "5.0.0"\n'
        + f'catalog_digest = "{_DIGEST_A}"\n'.encode()
        + f'config_digest = "{_DIGEST_B}"\n'.encode()
    )


def test_semantic_digest_uses_the_plan_pinned_canonical_json_vector() -> None:
    value: JsonValue = {"z": "é", "a": [True, None, 3]}

    digest = semantic_digest(value)

    assert digest.value == (
        "sha256:eb7bdec6b967d784acd526eec2c836f836a1ce8660c16f0df0b1b585b302b463"
    )


def test_empty_config_rendering_is_exact_and_round_trips() -> None:
    content = render_empty_config("5")

    assert content == (b'[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n')
    parsed = parse_config(content)
    assert parsed.project_standards.catalog.major == 5
    assert parsed.standards == {}


def test_catalog_rendering_is_canonical_self_digesting_and_round_trips() -> None:
    catalog = bind_catalog_digest(_catalog())

    first = render_catalog(catalog)
    second = render_catalog(catalog)
    parsed = parse_catalog(first)

    assert first == second
    assert first.endswith(b"\n")
    assert first.index(b"[standards.alpha]") < first.index(b"[standards.zeta]")
    without_digest = b"".join(
        line for line in first.splitlines(keepends=True) if not line.startswith(b"digest = ")
    )
    independently_computed = "sha256:" + hashlib.sha256(without_digest).hexdigest()
    assert parsed.project_standards.digest.value == independently_computed
    assert render_catalog(parsed) == first


def test_lock_rendering_is_canonical_and_round_trips() -> None:
    lock = _lock()

    first = render_lock(lock)
    parsed = parse_lock(first)

    assert first == render_lock(lock)
    assert first.endswith(b"\n")
    assert parsed.project_standards.schema_version == "1.1"
    assert parse_lock(render_lock(parsed)) == parsed
    assert b'owners = ["alpha"]' in first
    assert b'versions = { alpha = "1.2" }' in first


def test_lock_1_0_reads_and_lock_1_1_round_trips_create_only_absences() -> None:
    legacy_content = _legacy_empty_lock_content()

    legacy = parse_lock(legacy_content)

    assert legacy.project_standards.schema_version == "1.1"
    assert legacy.create_only_absences == []

    current_raw = legacy.model_dump(mode="json")
    current_raw["create_only_absences"] = [
        {
            "path": "zeta.toml",
            "adapter": "toml",
            "scope": "table:/lint",
            "owners": ["alpha"],
            "versions": {"alpha": "1.2"},
            "provenance": "source",
        },
        {
            "path": "alpha.toml",
            "adapter": "toml",
            "scope": "table:/lint",
            "owners": ["zeta", "alpha"],
            "shared_identity": "shared-unit",
            "versions": {"zeta": "1.0", "alpha": "1.2"},
            "provenance": "source",
        },
    ]
    current = CentralLock.model_validate(current_raw)

    rendered = render_lock(current)

    assert rendered.startswith(b'[project_standards]\nschema_version = "1.1"\n')
    assert b"[[create_only_absences]]" in rendered
    assert rendered.index(b'path = "alpha.toml"') < rendered.index(b'path = "zeta.toml"')
    assert b'owners = ["alpha", "zeta"]' in rendered
    assert b'versions = { alpha = "1.2", zeta = "1.0" }' in rendered
    assert b"policy = " not in rendered.split(b"[[create_only_absences]]", 1)[1]
    assert parse_lock(rendered) == current


@pytest.mark.parametrize(
    "content",
    [_legacy_empty_lock_content(), render_lock(_lock())],
    ids=["schema-1.0", "schema-1.1"],
)
def test_lock_loader_rejects_noncanonical_encoding_for_each_supported_schema(
    content: bytes,
) -> None:
    with pytest.raises(ControlPlaneError, match="canonical form"):
        parse_lock(content + b"\n")


@pytest.mark.parametrize("loader", [parse_config, parse_catalog, parse_lock])
def test_control_plane_loaders_reject_invalid_utf8_without_echoing_bytes(loader: object) -> None:
    with pytest.raises(ControlPlaneError, match="UTF-8") as exc_info:
        loader(b"\xffprivate")  # type: ignore[operator]

    assert "private" not in str(exc_info.value)


def test_catalog_loader_rejects_a_stale_self_digest() -> None:
    content = render_catalog(bind_catalog_digest(_catalog()))
    stale = content.replace(b'catalog = "5"', b'catalog = "6"')

    with pytest.raises(ControlPlaneError, match="digest"):
        parse_catalog(stale)
