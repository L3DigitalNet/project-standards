from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.catalog_refresh import CATALOG_REFRESH_BACKUP
from project_standards.control_plane.codec import (
    parse_lock,
    render_catalog,
    render_empty_config,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.models import CentralLock
from project_standards.control_plane.recovery import (
    RecoveryKind,
    RecoveryRequest,
    apply_recovery,
    plan_recovery,
)
from project_standards.control_plane.resolution import MajorAuthorization
from project_standards.package_contract.payload import JsonValue
from tests.control_plane.helpers import installed_distribution


def _empty_lock(distribution: InstalledDistribution, config: bytes) -> CentralLock:
    catalog = distribution.consumer_catalog("5")
    from project_standards.control_plane.codec import parse_config

    desired = parse_config(config)
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": semantic_digest(
                    cast(JsonValue, desired.model_dump(mode="json"))
                ).value,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": [],
        }
    )


def _control(repo: Path) -> Path:
    control = repo / ".standards"
    control.mkdir(parents=True)
    return control


def test_plan_recovery__lock_busy__returns_cp_busy_finding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)

    with control_plane_lock(repo, LockMode.WRITE):
        plan = plan_recovery(RecoveryRequest(repo, distribution))

    assert not plan.applicable
    assert plan.kind is RecoveryKind.UNRECOVERABLE
    assert plan.findings[0].code == "CP-BUSY"


@pytest.mark.parametrize(
    "recovery_case",
    ["missing-catalog", "catalog-refresh"],
)
def test_apply_recovery__lock_busy__returns_cp_busy_result(
    tmp_path: Path,
    recovery_case: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    if recovery_case == "missing-catalog":
        (control / "catalog.toml").unlink()
    else:
        (control / CATALOG_REFRESH_BACKUP).write_bytes((control / "catalog.toml").read_bytes())
    request = RecoveryRequest(repo, distribution)
    plan = plan_recovery(request)
    assert plan.applicable

    with control_plane_lock(repo, LockMode.READ):
        result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert not result.success
    assert result.error_code == "CP-BUSY"


def test_missing_user_config_refuses_inference_or_apply(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    catalog = distribution.consumer_catalog("5")
    (control / "catalog.toml").write_bytes(render_catalog(catalog))
    (control / "lock.toml").write_bytes(
        render_lock(_empty_lock(distribution, render_empty_config("5")))
    )
    request = RecoveryRequest(repo, distribution)

    plan = plan_recovery(request)
    result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert plan.kind is RecoveryKind.MISSING_CONFIG
    assert not plan.applicable
    assert plan.findings[0].code == "CP-MISSING-CONFIG"
    assert not result.success
    assert not (control / "config.toml").exists()


def test_missing_catalog_regenerates_only_matching_installed_snapshot(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = render_empty_config("5")
    (control / "config.toml").write_bytes(config)
    (control / "lock.toml").write_bytes(render_lock(_empty_lock(distribution, config)))
    request = RecoveryRequest(repo, distribution)

    plan = plan_recovery(request)

    assert plan.kind is RecoveryKind.MISSING_CATALOG
    assert plan.applicable
    assert plan.target == ".standards/catalog.toml"
    assert plan.proposed_content == render_catalog(distribution.consumer_catalog("5"))
    assert not (control / "catalog.toml").exists()

    denied = apply_recovery(request, plan, apply=True, repair_state=False)
    assert not denied.success and denied.error_code == "CP-REPAIR-AUTH"

    applied = apply_recovery(request, plan, apply=True, repair_state=True)
    assert applied.success
    assert (control / "catalog.toml").read_bytes() == plan.proposed_content


def test_missing_catalog_staging_failure_cleans_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = render_empty_config("5")
    (control / "config.toml").write_bytes(config)
    (control / "lock.toml").write_bytes(render_lock(_empty_lock(distribution, config)))
    request = RecoveryRequest(repo, distribution)
    plan = plan_recovery(request)

    def zero_write(_descriptor: int, _content: memoryview) -> int:
        return 0

    monkeypatch.setattr(os, "write", zero_write)

    result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert not result.success
    assert result.error_code == "CP-RECOVERY-APPLY"
    assert not (control / "catalog.toml").exists()
    assert not list(control.glob(".project-standards-*.tmp"))


@pytest.mark.parametrize(
    ("failure_call", "expected_applied"),
    [
        pytest.param(1, (), id="before-replacement"),
        pytest.param(2, (".standards/catalog.toml",), id="after-replacement"),
    ],
)
def test_missing_catalog_failure_reports_the_applied_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
    expected_applied: tuple[str, ...],
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = render_empty_config("5")
    (control / "config.toml").write_bytes(config)
    (control / "lock.toml").write_bytes(render_lock(_empty_lock(distribution, config)))
    request = RecoveryRequest(repo, distribution)
    plan = plan_recovery(request)
    original_fsync = os.fsync
    calls = 0

    def fail_at_boundary(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected recovery fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_at_boundary)

    result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert not result.success
    assert result.error_code == "CP-RECOVERY-APPLY"
    assert result.applied_action_ids == expected_applied
    assert (control / "catalog.toml").exists() is bool(expected_applied)


def test_catalog_refresh_cleanup_removes_only_reserved_regular_temporaries(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    backup = control / CATALOG_REFRESH_BACKUP
    backup.write_bytes((control / "catalog.toml").read_bytes())
    reserved_regular = control / ".project-standards-0123456789abcdef.tmp"
    reserved_regular.write_bytes(b"stale")
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    reserved_symlink = control / ".project-standards-fedcba9876543210.tmp"
    reserved_symlink.symlink_to(outside)
    reserved_directory = control / ".project-standards-1111111111111111.tmp"
    reserved_directory.mkdir()
    user_named = control / ".config.toml.2222222222222222.tmp"
    user_named.write_bytes(b"keep")
    request = RecoveryRequest(repo, distribution)

    plan = plan_recovery(request)

    assert plan.applicable
    assert plan.cleanup_targets == (reserved_regular.name, CATALOG_REFRESH_BACKUP)

    result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert result.success
    assert not reserved_regular.exists()
    assert not backup.exists()
    assert reserved_symlink.is_symlink()
    assert reserved_directory.is_dir()
    assert user_named.read_bytes() == b"keep"
    assert outside.read_bytes() == b"keep"


@pytest.mark.parametrize(
    ("failure_call", "expected_applied"),
    [
        pytest.param(1, (), id="before-replacement"),
        pytest.param(2, (".standards/catalog.toml",), id="after-replacement"),
    ],
)
def test_catalog_refresh_failure_reports_the_applied_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_call: int,
    expected_applied: tuple[str, ...],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    previous = (control / "catalog.toml").read_bytes()
    (control / CATALOG_REFRESH_BACKUP).write_bytes(previous)
    newer = InstalledDistribution(distribution.package_root, tool_release="5.0.1")
    (control / "catalog.toml").write_bytes(render_catalog(newer.consumer_catalog("5")))
    request = RecoveryRequest(repo, newer)
    plan = plan_recovery(request)
    assert plan.applicable and plan.proposed_content == previous
    original_fsync = os.fsync
    calls = 0

    def fail_at_boundary(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError("injected recovery fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_at_boundary)

    result = apply_recovery(request, plan, apply=True, repair_state=True)

    assert not result.success
    assert result.error_code == "CP-RECOVERY-APPLY"
    assert result.applied_action_ids == expected_applied
    if expected_applied:
        assert (control / "catalog.toml").read_bytes() == previous


def test_missing_lock_builds_evidence_backed_plan_without_accepted_tracks(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = render_empty_config("5")
    (control / "config.toml").write_bytes(config)
    (control / "catalog.toml").write_bytes(render_catalog(distribution.consumer_catalog("5")))
    request = RecoveryRequest(repo, distribution)

    plan = plan_recovery(request)

    assert plan.kind is RecoveryKind.MISSING_LOCK
    assert plan.applicable
    assert plan.reconciliation is not None
    assert plan.reconciliation.next_lock.accepted_tracks == {}
    assert plan.reconciliation.next_lock.standards == {}
    assert plan.reconciliation.next_lock.project_standards.schema_version == "1.1"
    assert plan.proposed_content is not None
    assert plan.proposed_content.startswith(b'[project_standards]\nschema_version = "1.1"\n')
    assert not (control / "lock.toml").exists()

    denied = apply_recovery(request, plan, apply=False, repair_state=True)
    assert not denied.success and denied.error_code == "CP-REPAIR-AUTH"

    applied = apply_recovery(request, plan, apply=True, repair_state=True)
    assert applied.success
    assert parse_lock((control / "lock.toml").read_bytes()) == (plan.reconciliation.next_lock)


def test_missing_lock_candidate_requires_fresh_matching_authorization(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = b"""[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n[standards.alpha]\nenabled = true\nversion = "3.0"\n"""
    (control / "config.toml").write_bytes(config)
    (control / "catalog.toml").write_bytes(render_catalog(distribution.consumer_catalog("5")))

    denied = plan_recovery(RecoveryRequest(repo, distribution))

    assert not denied.applicable
    assert denied.findings[0].code == "CP-RECOVERY-AUTH"

    allowed = plan_recovery(
        RecoveryRequest(
            repo,
            distribution,
            allowed_majors=frozenset({MajorAuthorization("alpha", 3)}),
        )
    )
    assert allowed.applicable
    assert allowed.reconciliation is not None
    assert allowed.reconciliation.next_lock.standards["alpha"].resolved.value == "3.0"
    assert allowed.reconciliation.next_lock.accepted_tracks["alpha"].major == 3


@pytest.mark.parametrize(
    ("missing", "expected"),
    [
        (("catalog.toml", "lock.toml"), RecoveryKind.UNRECOVERABLE),
        (
            ("config.toml", "catalog.toml", "lock.toml"),
            RecoveryKind.MISSING_CONFIG,
        ),
    ],
)
def test_several_missing_authorities_fail_closed(
    tmp_path: Path,
    missing: tuple[str, ...],
    expected: RecoveryKind,
) -> None:
    repo = tmp_path / "repo"
    control = _control(repo)
    distribution = installed_distribution(tmp_path)
    config = render_empty_config("5")
    files = {
        "config.toml": config,
        "catalog.toml": render_catalog(distribution.consumer_catalog("5")),
        "lock.toml": render_lock(_empty_lock(distribution, config)),
    }
    for name, content in files.items():
        if name not in missing:
            (control / name).write_bytes(content)

    plan = plan_recovery(RecoveryRequest(repo, distribution))

    assert not plan.applicable
    assert plan.kind is expected
