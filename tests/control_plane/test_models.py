from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    actions_to_jsonable,
    findings_to_jsonable,
    validation_summary,
)
from project_standards.control_plane.models import (
    AcceptedTrack,
    AppliedPackage,
    CatalogHeader,
    CatalogStandard,
    CatalogVersion,
    CentralLock,
    ConsumerCatalog,
    ControlHeader,
    DesiredConfig,
    DesiredPackage,
    LockedInput,
    LockedUnit,
    LockHeader,
    SelectionKind,
    UnitProvenance,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.package_contract.paths import PackageVersion

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"
_DIGEST_C = f"sha256:{'c' * 64}"


def _header() -> dict[str, str]:
    return {"schema_version": "1.0", "catalog": "5"}


def _lock_header() -> dict[str, str]:
    return {
        **_header(),
        "release": "5.0.0",
        "catalog_digest": _DIGEST_A,
        "config_digest": _DIGEST_B,
    }


def _applied() -> dict[str, str]:
    return {
        "requested": "latest",
        "resolved": "2.0",
        "selection": "breaking-candidate",
        "payload_digest": _DIGEST_A,
        "effective_config_digest": _DIGEST_B,
    }


def _unit(
    *,
    path: str = "pyproject.toml",
    scope: str = "table:/tool/ruff",
    owners: list[str] | None = None,
) -> dict[str, object]:
    selected_owners = ["python-tooling"] if owners is None else owners
    unit: dict[str, object] = {
        "path": path,
        "adapter": "toml",
        "scope": scope,
        "owners": selected_owners,
        "versions": dict.fromkeys(selected_owners, "1.1"),
        "provenance": "source",
        "policy": "managed",
        "semantic_digest": _DIGEST_A,
        "content_digest": _DIGEST_B,
        "mode": "0644",
        "created_container": False,
    }
    if len(selected_owners) > 1:
        unit["shared_identity"] = "shared-unit"
    return unit


def _absence(
    *,
    path: str = "pyproject.toml",
    scope: str = "table:/tool/ruff",
    owners: list[str] | None = None,
) -> dict[str, object]:
    selected_owners = ["python-tooling"] if owners is None else owners
    absence: dict[str, object] = {
        "path": path,
        "adapter": "toml",
        "scope": scope,
        "owners": selected_owners,
        "versions": dict.fromkeys(selected_owners, "1.1"),
        "provenance": "source",
    }
    if len(selected_owners) > 1:
        absence["shared_identity"] = "shared-unit"
    return absence


def test_desired_config_is_strict_frozen_and_deterministically_ordered() -> None:
    config = DesiredConfig.model_validate(
        {
            "project_standards": _header(),
            "standards": {
                "python-tooling": {
                    "enabled": True,
                    "version": "1.1",
                    "config": {"contract_version": "1.0"},
                },
                "markdown-tooling": {
                    "enabled": False,
                    "version": "latest",
                    "config": {},
                },
            },
        }
    )

    assert list(config.standards) == ["markdown-tooling", "python-tooling"]
    version = config.standards["python-tooling"].version
    assert isinstance(version, PackageVersion)
    assert version.value == "1.1"
    with pytest.raises(ValidationError):
        config.project_standards = ControlHeader.model_validate(
            {"schema_version": "1.0", "catalog": "6"}
        )


def _table(raw: dict[str, object], key: str) -> dict[str, object]:
    return cast(dict[str, object], raw[key])


def _add_header_extra(raw: dict[str, object]) -> None:
    _table(raw, "project_standards")["extra"] = True


def _set_noncanonical_catalog(raw: dict[str, object]) -> None:
    _table(raw, "project_standards")["catalog"] = "05"


def _add_standard(raw: dict[str, object], standard_id: str, config: object) -> None:
    _table(raw, "standards")[standard_id] = config


def _add_bad_package_id(raw: dict[str, object]) -> None:
    _add_standard(raw, "Bad_ID", {"enabled": True, "version": "latest", "config": {}})


def _add_bad_selector(raw: dict[str, object]) -> None:
    _add_standard(raw, "demo", {"enabled": True, "version": "1", "config": {}})


def _add_executable_config(raw: dict[str, object]) -> None:
    _add_standard(
        raw,
        "demo",
        {"enabled": True, "version": "latest", "config": {"command": "x"}},
    )


def _add_remote_config(raw: dict[str, object]) -> None:
    _add_standard(
        raw,
        "demo",
        {
            "enabled": True,
            "version": "latest",
            "config": {"artifact_url": "https://example.invalid/payload"},
        },
    )


def _add_secret_config(raw: dict[str, object]) -> None:
    _add_standard(
        raw,
        "demo",
        {
            "enabled": True,
            "version": "latest",
            "config": {"password": "never-print-this"},
        },
    )


@pytest.mark.parametrize(
    "mutate",
    [
        _add_header_extra,
        _set_noncanonical_catalog,
        _add_bad_package_id,
        _add_bad_selector,
        _add_executable_config,
        _add_remote_config,
        _add_secret_config,
    ],
    ids=[
        "extra-header-key",
        "noncanonical-catalog",
        "bad-package-id",
        "bad-selector",
        "executable-key",
        "remote-artifact",
        "secret-value",
    ],
)
def test_desired_config_rejects_untrusted_control_values_without_echo(
    mutate: Callable[[dict[str, object]], None],
) -> None:
    raw: dict[str, object] = {"project_standards": _header(), "standards": {}}
    mutate(raw)

    with pytest.raises(ValidationError) as exc_info:
        DesiredConfig.model_validate(raw)

    summary = validation_summary(exc_info.value)
    assert "never-print-this" not in summary
    assert "https://example.invalid/payload" not in summary


def test_consumer_catalog_normalizes_packages_versions_and_channels() -> None:
    catalog = ConsumerCatalog.model_validate(
        {
            "project_standards": {
                **_header(),
                "release": "5.0.0",
                "digest": _DIGEST_A,
            },
            "standards": {
                "demo": {
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
                }
            },
        }
    )

    standard = catalog.standards["demo"]
    assert [version.value for version in standard.available] == ["1.2", "2.0"]
    assert list(standard.versions) == ["1.2", "2.0"]
    assert standard.default is not None and standard.default.value == "1.2"


@pytest.mark.parametrize(
    "change",
    [
        {"available": ["1.2", "1.2"]},
        {"available": ["1.2"], "default": "2.0"},
        {"available": ["1.2", "2.0"], "default": "1.2", "candidates": ["1.2"]},
        {
            "available": ["1.2"],
            "default": "1.2",
            "versions": {
                "2.0": {
                    "channel": "stable",
                    "availability": "consumer",
                    "payload_digest": _DIGEST_A,
                }
            },
        },
    ],
)
def test_catalog_rejects_inconsistent_version_indexes(change: dict[str, object]) -> None:
    raw: dict[str, object] = {
        "status": "active",
        "available": ["1.2"],
        "default": "1.2",
        "candidates": [],
        "versions": {
            "1.2": {
                "channel": "stable",
                "availability": "consumer",
                "payload_digest": _DIGEST_A,
            }
        },
    }
    raw.update(change)
    with pytest.raises(ValidationError):
        CatalogStandard.model_validate(raw)


def test_central_lock_keeps_applied_and_authorized_state_separate() -> None:
    lock = CentralLock.model_validate(
        {
            "project_standards": _lock_header(),
            "standards": {"demo": _applied()},
            "accepted_tracks": {"demo": {"major": 2, "authorized_catalog": "5"}},
            "artifacts": [
                _unit(path="z.toml", scope="key:/z", owners=["zeta", "alpha"]),
                _unit(path="a.toml", scope="key:/a"),
            ],
            "referenced_inputs": [
                {
                    "standard_id": "demo",
                    "extension_id": "local-options",
                    "path": ".standards/extensions/demo/options.toml",
                    "digest": _DIGEST_C,
                }
            ],
        }
    )

    assert list(lock.standards) == ["demo"]
    assert list(lock.accepted_tracks) == ["demo"]
    assert [unit.path.original for unit in lock.artifacts] == ["a.toml", "z.toml"]
    assert lock.artifacts[1].owners == ("alpha", "zeta")
    assert lock.artifacts[1].shared_identity == "shared-unit"
    assert lock.accepted_tracks["demo"].major == 2


@pytest.mark.parametrize(
    "payload",
    [
        {**_applied(), "enabled": False},
        {**_applied(), "accepted_major": 2},
    ],
    ids=["disabled-tombstone", "embedded-accepted-track"],
)
def test_applied_package_rejects_disabled_or_authorization_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AppliedPackage.model_validate(payload)


def test_applied_package_rejects_a_noncanonical_digest() -> None:
    with pytest.raises(ValidationError):
        AppliedPackage.model_validate({**_applied(), "payload_digest": f"sha256:{'A' * 64}"})


@pytest.mark.parametrize(
    "artifacts",
    [
        [_unit(), _unit()],
        [_unit(owners=["demo", "demo"])],
        [{**_unit(owners=["demo"]), "versions": {"other": "1.0"}}],
    ],
    ids=["duplicate-unit", "duplicate-owner", "owner-version-mismatch"],
)
def test_lock_rejects_duplicate_or_inconsistent_artifact_ownership(
    artifacts: list[dict[str, object]],
) -> None:
    with pytest.raises(ValidationError):
        CentralLock.model_validate(
            {
                "project_standards": _lock_header(),
                "standards": {},
                "accepted_tracks": {},
                "artifacts": artifacts,
                "referenced_inputs": [],
            }
        )


@pytest.mark.parametrize(
    ("artifacts", "create_only_absences"),
    [
        ([_unit()], [_absence()]),
        ([], [_absence(), _absence()]),
    ],
    ids=["cross-partition", "within-absence-partition"],
)
def test_lock_rejects_duplicate_keys_across_artifacts_and_create_only_absences(
    artifacts: list[dict[str, object]],
    create_only_absences: list[dict[str, object]],
) -> None:
    with pytest.raises(
        ValidationError,
        match="duplicate artifact or create-only absence",
    ):
        CentralLock.model_validate(
            {
                "project_standards": {**_lock_header(), "schema_version": "1.1"},
                "standards": {},
                "accepted_tracks": {},
                "artifacts": artifacts,
                "create_only_absences": create_only_absences,
                "referenced_inputs": [],
            }
        )


@pytest.mark.parametrize(
    "absence",
    [
        _absence(owners=["demo", "demo"]),
        {**_absence(owners=["demo"]), "versions": {"other": "1.1"}},
        {**_absence(owners=["alpha", "demo"]), "shared_identity": None},
        {
            **_absence(owners=["alpha", "demo"]),
            "adapter": "whole-file",
            "scope": "$file",
        },
        _absence(
            path=".standards/packages/demo/state.toml",
            owners=["other"],
        ),
    ],
    ids=[
        "duplicate-owner",
        "owner-version-mismatch",
        "missing-shared-identity",
        "shared-whole-file",
        "package-namespace-owner-mismatch",
    ],
)
def test_lock_rejects_inconsistent_create_only_absence_ownership(
    absence: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CentralLock.model_validate(
            {
                "project_standards": {**_lock_header(), "schema_version": "1.1"},
                "standards": {},
                "accepted_tracks": {},
                "artifacts": [],
                "create_only_absences": [absence],
                "referenced_inputs": [],
            }
        )


def test_lock_schema_1_0_rejects_create_only_absences() -> None:
    with pytest.raises(ValidationError, match=r"schema 1\.0"):
        CentralLock.model_validate(
            {
                "project_standards": _lock_header(),
                "standards": {},
                "accepted_tracks": {},
                "artifacts": [],
                "create_only_absences": [_absence()],
                "referenced_inputs": [],
            }
        )


def test_lock_rejects_duplicate_referenced_inputs() -> None:
    referenced_input = {
        "standard_id": "demo",
        "extension_id": "options",
        "path": ".standards/extensions/demo/options.toml",
        "digest": _DIGEST_A,
    }
    with pytest.raises(ValidationError):
        CentralLock.model_validate(
            {
                "project_standards": _lock_header(),
                "standards": {},
                "accepted_tracks": {},
                "artifacts": [],
                "referenced_inputs": [referenced_input, referenced_input],
            }
        )


def test_diagnostics_sort_stably_and_never_emit_internal_content() -> None:
    actions = [
        ControlAction(
            kind=ActionKind.UPDATE,
            target="z.toml",
            adapter="toml",
            scope="key:/z",
            standard_id="zeta",
            summary="update z",
            before_digest=_DIGEST_A,
            after_digest=_DIGEST_B,
            content=b"private-content",
        ),
        ControlAction(
            kind=ActionKind.CREATE,
            target="a.toml",
            adapter="toml",
            scope="key:/a",
            standard_id="alpha",
            summary="create a",
            after_digest=_DIGEST_A,
            content=b"other-private-content",
        ),
    ]
    findings = [
        ControlFinding(
            code="CP-Z",
            severity="error",
            standard_id="zeta",
            version="2.0",
            path="z.toml",
            identity="key:/z",
            message="z failed",
            hint="repair z",
        ),
        ControlFinding(
            code="CP-A",
            severity="warning",
            standard_id="alpha",
            version="1.0",
            path="a.toml",
            identity="key:/a",
            message="a differs",
            hint="review a",
        ),
    ]

    action_json = actions_to_jsonable(reversed(actions))
    finding_json = findings_to_jsonable(reversed(findings))

    assert [item["standard_id"] for item in action_json] == ["alpha", "zeta"]
    assert [item["standard_id"] for item in finding_json] == ["alpha", "zeta"]
    assert all("content" not in item for item in action_json)
    assert "private-content" not in repr(action_json)


def test_public_models_accept_the_exact_documented_shapes() -> None:
    assert CatalogMajor("5").value == "5"
    assert (
        ControlHeader.model_validate({"schema_version": "1.0", "catalog": "5"}).catalog.major == 5
    )
    assert (
        CatalogHeader.model_validate(
            {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "digest": _DIGEST_A,
            }
        ).digest.value
        == _DIGEST_A
    )
    assert DesiredPackage(enabled=False, version="latest", config={}).version == "latest"
    assert SelectionKind.CANDIDATE.value == "breaking-candidate"
    assert UnitProvenance.PROVIDER.value == "provider"
    assert (
        AcceptedTrack.model_validate(
            {"major": 2, "authorized_catalog": "5"}
        ).authorized_catalog.major
        == 5
    )
    assert LockedInput.model_validate(
        {
            "standard_id": "demo",
            "extension_id": "options",
            "path": ".standards/extensions/demo/options.toml",
            "digest": _DIGEST_A,
        }
    ).path.original.endswith("options.toml")
    assert LockedUnit.model_validate(_unit()).mode == "0644"
    assert LockHeader.model_validate(_lock_header()).release == "5.0.0"
    assert (
        CatalogVersion.model_validate(
            {
                "channel": "stable",
                "availability": "consumer",
                "payload_digest": _DIGEST_A,
            }
        ).channel.value
        == "stable"
    )
