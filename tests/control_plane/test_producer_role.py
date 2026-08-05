"""Declare a producing repository through the config header (TC-T40-001).

REQ-908: a repository that produces the catalog spends every release train with
an installed catalog ahead of its committed ``.standards/catalog.toml`` at an
unchanged tool release. Issue #123 scoped the release-lineage assertion to the
commands that publish a catalog; this module proves the second half — that such
a repository may say so, once, in ``[project_standards]``, and that saying so
relaxes nothing but the equal-release publication window.
"""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from project_standards.control_plane.catalog_refresh import (
    CatalogAdvance,
    plan_catalog_refresh,
)
from project_standards.control_plane.codec import bind_catalog_digest, parse_config
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    ControlHeader,
    DesiredConfig,
)

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"
_LINEAGE_REFUSAL = "catalog changed but its tool release did not advance"


def _payload_digest(version: str) -> str:
    return f"sha256:{hashlib.sha256(version.encode()).hexdigest()}"


def _catalog(
    release: str,
    *,
    major: str = "5",
    candidates: tuple[str, ...] = (),
) -> ConsumerCatalog:
    versions: dict[str, object] = {
        "1.1": {
            "channel": "stable",
            "availability": "consumer",
            "payload_digest": _payload_digest("1.1"),
        }
    }
    versions.update(
        {
            version: {
                "channel": "breaking-candidate",
                "availability": "consumer",
                "payload_digest": _payload_digest(version),
            }
            for version in candidates
        }
    )
    catalog = ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": major,
                "release": release,
                "digest": _DIGEST_A,
            },
            "standards": {
                "demo": {
                    "status": "active",
                    "available": list(versions),
                    "default": "1.1",
                    "candidates": list(candidates),
                    "versions": versions,
                }
            },
        }
    )
    return bind_catalog_digest(catalog)


def _desired(*, schema_version: str = "1.0", role: str | None = None) -> DesiredConfig:
    header: dict[str, str] = {"schema_version": schema_version, "catalog": "5"}
    if role is not None:
        header["role"] = role
    return DesiredConfig.model_validate(
        {
            "project_standards": header,
            "standards": {"demo": {"enabled": True, "version": "latest", "config": {}}},
        }
    )


def _lock(catalog: ConsumerCatalog) -> CentralLock:
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.1",
                "catalog": "5",
                "release": catalog.project_standards.release,
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": _DIGEST_B,
            },
            "standards": {
                "demo": {
                    "requested": "latest",
                    "resolved": "1.1",
                    "selection": "stable",
                    "payload_digest": _payload_digest("1.1"),
                    "effective_config_digest": _DIGEST_A,
                }
            },
        }
    )


def test_control_header_accepts_both_config_schema_versions() -> None:
    """1.1 is additive: the predecessor stays valid and both default to consumer."""
    assert (
        ControlHeader.model_validate({"schema_version": "1.0", "catalog": "5"}).role == "consumer"
    )
    assert (
        ControlHeader.model_validate({"schema_version": "1.1", "catalog": "5"}).role == "consumer"
    )
    assert (
        ControlHeader.model_validate(
            {"schema_version": "1.1", "catalog": "5", "role": "producer"}
        ).role
        == "producer"
    )


def test_role_is_rejected_before_config_schema_1_1() -> None:
    """The key is gated on the version that introduces it, and its values stay closed."""
    with pytest.raises(ValidationError):
        ControlHeader.model_validate({"schema_version": "1.0", "catalog": "5", "role": "producer"})
    with pytest.raises(ValidationError):
        ControlHeader.model_validate({"schema_version": "1.1", "catalog": "5", "role": "author"})


def test_producer_config_parses_from_its_committed_toml() -> None:
    config = parse_config(
        b'[project_standards]\nschema_version = "1.1"\ncatalog = "5"\nrole = "producer"\n'
    )

    assert config.project_standards.role == "producer"


def test_producer_publishes_a_changed_catalog_at_an_unchanged_release() -> None:
    """The whole point: the mid-release-train state stops being a refusal."""
    committed = _catalog("5.0.0")
    changed = _catalog("5.0.0", candidates=("2.0",))

    plan = plan_catalog_refresh(
        committed,
        changed,
        _desired(schema_version="1.1", role="producer"),
        _lock(committed),
        advance=CatalogAdvance.ADVANCING,
    )

    assert plan.changed
    assert plan.after.release == "5.0.0"


def test_consumer_still_refuses_the_identical_state() -> None:
    """Default behavior is unchanged, whether the default is implied or written."""
    committed = _catalog("5.0.0")
    changed = _catalog("5.0.0", candidates=("2.0",))

    for desired in (_desired(), _desired(schema_version="1.1")):
        with pytest.raises(ControlPlaneError, match=_LINEAGE_REFUSAL):
            plan_catalog_refresh(
                committed,
                changed,
                desired,
                _lock(committed),
                advance=CatalogAdvance.ADVANCING,
            )


def test_producer_relaxes_no_other_lineage_rule() -> None:
    """Downgrade, catalog-major, and lock-lineage agreement are role-independent."""
    producer = _desired(schema_version="1.1", role="producer")
    committed = _catalog("5.0.1")

    with pytest.raises(ControlPlaneError, match="older"):
        plan_catalog_refresh(
            committed,
            _catalog("5.0.0"),
            producer,
            _lock(committed),
            advance=CatalogAdvance.ADVANCING,
        )
    with pytest.raises(ControlPlaneError, match="catalog major"):
        plan_catalog_refresh(
            committed,
            _catalog("6.0.0", major="6"),
            producer,
            _lock(committed),
            advance=CatalogAdvance.ADVANCING,
        )

    lock = _lock(committed)
    stale = lock.model_copy(
        update={
            "project_standards": lock.project_standards.model_copy(
                update={"catalog_digest": _DIGEST_A}
            )
        }
    )
    with pytest.raises(ControlPlaneError, match=r"lock.*catalog"):
        plan_catalog_refresh(
            committed,
            _catalog("5.1.0"),
            producer,
            stale,
            advance=CatalogAdvance.ADVANCING,
        )


def test_producer_still_asserts_release_policy_once_the_release_advances() -> None:
    """The relaxation is the equal-release window, not the release policy itself."""
    committed = _catalog("5.0.0", candidates=("2.0",))
    removed = _catalog("5.1.0")

    with pytest.raises(ControlPlaneError, match="PC-RELEASE-PAYLOAD-DELETED"):
        plan_catalog_refresh(
            committed,
            removed,
            _desired(schema_version="1.1", role="producer"),
            _lock(committed),
            advance=CatalogAdvance.ADVANCING,
        )


def test_declaring_a_role_is_not_a_desired_state_change() -> None:
    """`config_digest` hashes this dump; a local role declaration must not move it."""
    assert _desired(schema_version="1.1", role="producer").model_dump(mode="json") == _desired(
        schema_version="1.1"
    ).model_dump(mode="json")
