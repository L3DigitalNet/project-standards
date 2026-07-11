from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest

from project_standards.control_plane import catalog_refresh
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.catalog_refresh import plan_catalog_refresh
from project_standards.control_plane.cli import build_planner_request, run
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_catalog,
    parse_lock,
)
from project_standards.control_plane.config_edit import (
    set_standard_enabled,
    set_standard_selection,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import InstalledCatalog, InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.models import CentralLock, ConsumerCatalog, DesiredConfig
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.state import StateKind, detect_control_plane_state
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.helpers import installed_distribution

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"


def _payload_digest(version: str) -> str:
    return f"sha256:{hashlib.sha256(version.encode()).hexdigest()}"


def _catalog(
    release: str,
    *,
    major: str = "5",
    default: str = "1.1",
    retained: tuple[str, ...] = (),
    candidates: tuple[str, ...] = (),
) -> ConsumerCatalog:
    versions: dict[str, object] = {
        version: {
            "channel": "retained",
            "availability": "consumer",
            "payload_digest": _payload_digest(version),
        }
        for version in retained
    }
    versions[default] = {
        "channel": "stable",
        "availability": "consumer",
        "payload_digest": _payload_digest(default),
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
                    "default": default,
                    "candidates": list(candidates),
                    "versions": versions,
                }
            },
        }
    )
    return bind_catalog_digest(catalog)


def _desired(selector: str = "latest", *, enabled: bool = True) -> DesiredConfig:
    return DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": "5"},
            "standards": {"demo": {"enabled": enabled, "version": selector, "config": {}}},
        }
    )


def _lock(
    catalog: ConsumerCatalog,
    *,
    resolved: str | None = "1.1",
    accepted_major: int | None = None,
) -> CentralLock:
    standards: dict[str, object] = {}
    if resolved is not None:
        standards["demo"] = {
            "requested": "latest",
            "resolved": resolved,
            "selection": "retained" if accepted_major is not None else "stable",
            "payload_digest": catalog.standards["demo"].versions[resolved].payload_digest.value,
            "effective_config_digest": _DIGEST_A,
        }
    accepted_tracks = (
        {"demo": {"major": accepted_major, "authorized_catalog": "5"}}
        if accepted_major is not None
        else {}
    )
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": catalog.project_standards.release,
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": _DIGEST_B,
            },
            "standards": standards,
            "accepted_tracks": accepted_tracks,
            "artifacts": [],
            "referenced_inputs": [],
        }
    )


def _distribution_with_alpha_2_1(tmp_path: Path) -> InstalledDistribution:
    repository = tmp_path / "repository"
    source = repository / "standards/alpha/versions/2.0"
    target = repository / "standards/alpha/versions/2.1"
    shutil.copytree(source, target)
    payload_path = target / "payload.toml"
    payload_text = payload_path.read_text(encoding="utf-8").replace(
        'version = "2.0"',
        'version = "2.1"',
        1,
    )
    zeta = b"alpha 2.1 staged artifact\n"
    (target / "zeta.txt").write_bytes(zeta)
    zeta_digest = f"sha256:{hashlib.sha256(zeta).hexdigest()}"
    payload_path.write_text(
        payload_text.replace('to = "package:2.0"', 'to = "package:2.1"')
        + (
            '\n[[artifacts]]\nid = "zeta"\ntarget = "zeta.txt"\n'
            f'source = "zeta.txt"\ndigest = "{zeta_digest}"\n'
            'policy = "managed"\nmode = "0644"\n'
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    digest = validate_payload_integrity(target, manifest).aggregate_digest.value
    family_path = repository / "standards/alpha/standard.toml"
    family_path.write_text(
        family_path.read_text(encoding="utf-8")
        + (
            '\n[[versions]]\nversion = "2.1"\n'
            'payload = "versions/2.1/payload.toml"\n'
            f'digest = "{digest}"\n'
        ),
        encoding="utf-8",
    )
    catalog_path = repository / "catalogs/5.toml"
    catalog_text = catalog_path.read_text(encoding="utf-8").replace(
        'version = "2.0"\n'
        'digest = "sha256:c1666aee5b8d0bbf35bf771c4539012a1c5c7fbd3f5aeb5d99bc7f0ba18b69e9"\n'
        'role = "default"',
        'version = "2.0"\n'
        'digest = "sha256:c1666aee5b8d0bbf35bf771c4539012a1c5c7fbd3f5aeb5d99bc7f0ba18b69e9"\n'
        'role = "retained"',
        1,
    )
    catalog_path.write_text(
        catalog_text
        + (
            '\n[[packages]]\nid = "alpha"\nversion = "2.1"\n'
            f'digest = "{digest}"\nrole = "default"\n'
        ),
        encoding="utf-8",
    )
    assert sync_payload_projection(repository, check=False) == ()
    installed = tmp_path / "installed-refresh/project_standards"
    shutil.copytree(repository / "src/project_standards", installed)
    return InstalledDistribution(installed, tool_release="5.1.0")


def test_catalog_refresh_boundary_module_exists() -> None:
    assert find_spec("project_standards.control_plane.catalog_refresh") is not None


def test_catalog_refresh_boundary_is_public() -> None:
    assert callable(getattr(catalog_refresh, "plan_catalog_refresh", None))


def test_newer_same_major_release_plans_catalog_lineage_refresh() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.0.1")

    result = plan_catalog_refresh(committed, installed, _desired(), _lock(committed))

    assert result.changed
    assert result.before.release == "5.0.0"
    assert result.after.release == "5.0.1"
    assert result.classification == "patch"
    assert result.affected_selections == ()


def test_byte_identical_catalog_is_a_clean_noop() -> None:
    committed = _catalog("5.0.0")

    result = plan_catalog_refresh(committed, committed, _desired(), _lock(committed))

    assert not result.changed
    assert result.before == result.after
    assert result.affected_selections == ()


def test_compatible_default_advancement_is_reported() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.1.0", default="1.2", retained=("1.1",))

    result = plan_catalog_refresh(committed, installed, _desired(), _lock(committed))

    assert result.classification == "minor"
    (change,) = result.affected_selections
    assert change.previous is not None
    assert (change.standard_id, change.previous.value, change.current.value) == (
        "demo",
        "1.1",
        "1.2",
    )


def test_exact_pin_remains_exact_across_refresh() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.1.0", default="1.2", retained=("1.1",))

    result = plan_catalog_refresh(
        committed,
        installed,
        _desired("1.1"),
        _lock(committed),
    )

    assert result.affected_selections == ()


def test_accepted_track_advances_without_normalizing_authorization() -> None:
    committed = _catalog("5.0.0", candidates=("2.0",))
    installed = _catalog("5.1.0", candidates=("2.0", "2.1"))

    result = plan_catalog_refresh(
        committed,
        installed,
        _desired(),
        _lock(committed, resolved="2.0", accepted_major=2),
    )

    (change,) = result.affected_selections
    assert change.previous is not None
    assert (change.standard_id, change.previous.value, change.current.value) == (
        "demo",
        "2.0",
        "2.1",
    )


def test_disabled_package_does_not_gain_an_applied_selection() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.1.0", default="1.2", retained=("1.1",))

    result = plan_catalog_refresh(
        committed,
        installed,
        _desired(enabled=False),
        _lock(committed, resolved=None),
    )

    assert result.changed
    assert result.affected_selections == ()


def test_unavailable_pin_blocks_refresh() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.0.1")

    with pytest.raises(ControlPlaneError, match="exact package"):
        plan_catalog_refresh(
            committed,
            installed,
            _desired("9.9"),
            _lock(committed, resolved=None),
        )


def test_unavailable_retained_track_blocks_refresh_while_disabled() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.0.1")

    with pytest.raises(ControlPlaneError, match="accepted major 3"):
        plan_catalog_refresh(
            committed,
            installed,
            _desired(enabled=False),
            _lock(committed, resolved=None, accepted_major=3),
        )


def test_older_installed_release_cannot_downgrade_catalog() -> None:
    committed = _catalog("5.0.1")

    with pytest.raises(ControlPlaneError, match="older"):
        plan_catalog_refresh(
            committed,
            _catalog("5.0.0"),
            _desired(),
            _lock(committed),
        )


def test_changed_catalog_major_requires_explicit_promotion() -> None:
    committed = _catalog("5.0.0")

    with pytest.raises(ControlPlaneError, match="catalog major"):
        plan_catalog_refresh(
            committed,
            _catalog("6.0.0", major="6"),
            _desired(),
            _lock(committed),
        )


def test_tool_major_mismatch_allows_read_only_inspection_but_refuses_apply(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    catalog = (repo / ".standards/catalog.toml").read_bytes()
    lock = (repo / ".standards/lock.toml").read_bytes()
    next_major = InstalledDistribution(base.package_root, tool_release="6.0.0")

    assert run(["--repo", str(repo), "--check", "--json"], distribution=next_major) == 1
    inspection = json.loads(capsys.readouterr().out)
    assert inspection == {
        "ok": False,
        "mode": "inspection",
        "state": "tool-mismatch",
        "mutable": False,
        "catalog": {"major": "5", "release": "5.0.0"},
        "error": "installed tool major does not match configured catalog major",
    }

    assert run(["--repo", str(repo), "--apply", "--json"], distribution=next_major) == 2
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["code"] == "CP-CATALOG-MAJOR-MISMATCH"
    assert (repo / ".standards/catalog.toml").read_bytes() == catalog
    assert (repo / ".standards/lock.toml").read_bytes() == lock


def test_equal_release_with_different_catalog_is_rejected_as_tampering() -> None:
    committed = _catalog("5.0.0")
    changed = _catalog("5.0.0", candidates=("2.0",))

    with pytest.raises(ControlPlaneError, match="release did not advance"):
        plan_catalog_refresh(committed, changed, _desired(), _lock(committed))


def test_material_catalog_change_requires_a_minor_release() -> None:
    committed = _catalog("5.0.0")
    changed = _catalog("5.0.1", candidates=("2.0",))

    with pytest.raises(ControlPlaneError, match="PC-RELEASE-LEVEL"):
        plan_catalog_refresh(committed, changed, _desired(), _lock(committed))


def test_payload_removal_and_breaking_default_promotion_are_rejected() -> None:
    committed = _catalog("5.0.0", candidates=("2.0",))
    removed = _catalog("5.1.0")
    promoted = _catalog("5.1.0", default="2.0", retained=("1.1",))

    with pytest.raises(ControlPlaneError, match="PC-RELEASE-PAYLOAD-DELETED"):
        plan_catalog_refresh(committed, removed, _desired(), _lock(committed))
    with pytest.raises(ControlPlaneError, match="release policy"):
        plan_catalog_refresh(committed, promoted, _desired(), _lock(committed))


def test_digest_or_committed_lineage_tampering_is_rejected() -> None:
    committed = _catalog("5.0.0")
    installed = _catalog("5.0.1")
    bad_header = installed.project_standards.model_copy(update={"digest": _DIGEST_A})
    tampered = installed.model_copy(update={"project_standards": bad_header})

    with pytest.raises(ControlPlaneError, match="digest"):
        plan_catalog_refresh(committed, tampered, _desired(), _lock(committed))

    stale_lock = _lock(committed).model_copy(
        update={
            "project_standards": _lock(committed).project_standards.model_copy(
                update={"catalog_digest": _DIGEST_A}
            )
        }
    )
    with pytest.raises(ControlPlaneError, match=r"lock.*catalog"):
        plan_catalog_refresh(committed, installed, _desired(), stale_lock)


def test_cli_previews_applies_and_converges_catalog_refresh(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")

    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1
    preview = json.loads(capsys.readouterr().out)
    catalog_actions = [
        action
        for action in preview["plan"]["actions"]
        if action["target"] == ".standards/catalog.toml"
    ]
    assert preview["drift"]
    assert len(catalog_actions) == 1
    assert catalog_actions[0]["kind"] == "update"
    assert "content" not in catalog_actions[0]

    assert run(["--repo", str(repo), "--apply", "--json"], distribution=newer) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["success"]
    assert applied["applied_action_ids"] == [".standards/catalog.toml"]
    assert parse_catalog(
        (repo / ".standards/catalog.toml").read_bytes()
    ).project_standards.release == ("5.0.1")
    assert parse_lock((repo / ".standards/lock.toml").read_bytes()).project_standards.release == (
        "5.0.1"
    )

    assert run(["--repo", str(repo), "--check", "--json"], distribution=newer) == 0
    converged = json.loads(capsys.readouterr().out)
    assert not converged["drift"]


def test_cli_derives_refresh_catalog_from_one_validated_installed_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    original = InstalledDistribution.load_catalog
    calls = 0

    def tracked_load(
        distribution: InstalledDistribution,
        catalog: CatalogMajor | str,
        *,
        recorded_release: str | None = None,
    ) -> InstalledCatalog:
        nonlocal calls
        calls += 1
        return original(distribution, catalog, recorded_release=recorded_release)

    monkeypatch.setattr(InstalledDistribution, "load_catalog", tracked_load)

    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1
    capsys.readouterr()
    assert calls == 1


def test_unavailable_selection_blocks_catalog_and_lock_writes(tmp_path: Path) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    set_standard_selection(repo, "alpha", enabled=True, version="9.9")
    old_catalog = (repo / ".standards/catalog.toml").read_bytes()
    old_lock = (repo / ".standards/lock.toml").read_bytes()
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")

    assert run(["--repo", str(repo), "--apply", "--json"], distribution=newer) == 2
    assert (repo / ".standards/catalog.toml").read_bytes() == old_catalog
    assert (repo / ".standards/lock.toml").read_bytes() == old_lock
    assert not (repo / ".standards/.catalog-refresh.previous.toml").exists()


def test_real_installed_default_advancement_updates_selection_compatibly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("enabled = true\n", encoding="utf-8")
    set_standard_enabled(repo, "alpha", True)
    assert run(["--repo", str(repo), "--apply", "--json"], distribution=base) == 0
    capsys.readouterr()
    initial = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert initial.standards["alpha"].resolved.value == "2.0"
    newer = _distribution_with_alpha_2_1(tmp_path)

    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1
    preview = json.loads(capsys.readouterr().out)
    assert preview["plan"]["catalog_refresh"]["affected_selections"] == [
        {"standard_id": "alpha", "previous": "2.0", "current": "2.1"}
    ]

    assert run(["--repo", str(repo), "--apply", "--json"], distribution=newer) == 0
    capsys.readouterr()
    refreshed = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert refreshed.standards["alpha"].resolved.value == "2.1"
    assert refreshed.accepted_tracks == {}


@pytest.mark.parametrize(
    ("failure_phase", "failure_identity"),
    [
        ("published", ".standards/.catalog-refresh.previous.toml"),
        ("publish", ".standards/catalog.toml"),
        ("published", ".standards/catalog.toml"),
        ("lock", ".standards/lock.toml"),
    ],
)
def test_pre_lock_failure_restores_committed_catalog_for_recovery(
    tmp_path: Path,
    failure_phase: str,
    failure_identity: str,
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    old_catalog = (repo / ".standards/catalog.toml").read_bytes()
    old_lock = (repo / ".standards/lock.toml").read_bytes()
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    planner = build_planner_request(repo, newer, frozenset())
    plan = plan_reconciliation(planner)

    def fail(phase: str, identity: str) -> None:
        if phase == failure_phase and identity == failure_identity:
            raise RuntimeError("injected catalog refresh failure")

    result = apply_reconciliation(
        ApplyRequest(planner=planner, expected_plan=plan, fault_hook=fail)
    )

    assert not result.success
    assert ".standards/catalog.toml" not in result.applied_action_ids
    assert (repo / ".standards/catalog.toml").read_bytes() == old_catalog
    assert (repo / ".standards/lock.toml").read_bytes() == old_lock
    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1


def test_post_lock_fault_reports_committed_refresh_truthfully(tmp_path: Path) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    planner = build_planner_request(repo, newer, frozenset())
    plan = plan_reconciliation(planner)

    def fail(phase: str, identity: str) -> None:
        if (phase, identity) == ("published", ".standards/lock.toml"):
            raise RuntimeError("injected post-commit reporting failure")

    result = apply_reconciliation(
        ApplyRequest(planner=planner, expected_plan=plan, fault_hook=fail)
    )

    assert not result.success
    assert result.lock_written
    assert not (repo / ".standards/.catalog-refresh.previous.toml").exists()
    assert detect_control_plane_state(repo, tool_release="5.0.1").kind is StateKind.INITIALIZED
    assert run(["--repo", str(repo), "--check", "--json"], distribution=newer) == 0


def test_process_interruption_with_durable_backup_has_sanctioned_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    catalog_path = repo / ".standards/catalog.toml"
    backup_path = repo / ".standards/.catalog-refresh.previous.toml"
    committed = catalog_path.read_bytes()
    backup_path.write_bytes(committed)
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    catalog_path.write_bytes(catalog_refresh.render_catalog(newer.consumer_catalog("5")))

    state = detect_control_plane_state(repo, tool_release="5.0.1")
    assert state.kind is StateKind.INTERRUPTED_REFRESH
    assert run(["--repo", str(repo), "--repair-state", "--json"], distribution=newer) == 1
    preview = json.loads(capsys.readouterr().out)
    assert preview["recovery_kind"] == "catalog-refresh"

    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply", "--json"],
            distribution=newer,
        )
        == 0
    )
    recovered = json.loads(capsys.readouterr().out)
    assert recovered["success"]
    assert catalog_path.read_bytes() == committed
    assert not backup_path.exists()
    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1


def test_recovery_cleans_stale_backup_after_committed_refresh(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    catalog_path = repo / ".standards/catalog.toml"
    committed = catalog_path.read_bytes()
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    assert run(["--repo", str(repo), "--apply", "--json"], distribution=newer) == 0
    capsys.readouterr()
    refreshed = catalog_path.read_bytes()
    backup_path = repo / ".standards/.catalog-refresh.previous.toml"
    backup_path.write_bytes(committed)

    assert (
        detect_control_plane_state(repo, tool_release="5.0.1").kind is StateKind.INTERRUPTED_REFRESH
    )
    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply", "--json"],
            distribution=newer,
        )
        == 0
    )
    recovered = json.loads(capsys.readouterr().out)
    assert recovered["applied_action_ids"] == ["remove:.standards/.catalog-refresh.previous.toml"]
    assert catalog_path.read_bytes() == refreshed
    assert not backup_path.exists()


def test_process_death_after_catalog_publication_recovers_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    newer = InstalledDistribution(base.package_root, tool_release="5.0.1")
    script = r"""
import os
import sys
from pathlib import Path

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation

repo = Path(sys.argv[1])
distribution = InstalledDistribution(Path(sys.argv[2]), tool_release="5.0.1")
planner = build_planner_request(repo, distribution, frozenset())
plan = plan_reconciliation(planner)

def terminate(phase, identity):
    if (phase, identity) == ("published", ".standards/catalog.toml"):
        os._exit(73)

apply_reconciliation(ApplyRequest(planner, plan, fault_hook=terminate))
raise AssertionError("termination fault did not run")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(repo), str(base.package_root)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 73, completed.stderr
    assert (
        detect_control_plane_state(repo, tool_release="5.0.1").kind is StateKind.INTERRUPTED_REFRESH
    )
    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply", "--json"],
            distribution=newer,
        )
        == 0
    )
    capsys.readouterr()
    assert not (repo / ".standards/.catalog-refresh.previous.toml").exists()
    assert not list((repo / ".standards").glob(".project-standards-*.tmp"))
    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1


def test_process_death_during_artifact_publication_leaves_no_orphaned_staging(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=base)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("enabled = true\n", encoding="utf-8")
    set_standard_enabled(repo, "alpha", True)
    assert run(["--repo", str(repo), "--apply", "--json"], distribution=base) == 0
    capsys.readouterr()
    newer = _distribution_with_alpha_2_1(tmp_path)
    script = r"""
import os
import sys
from pathlib import Path

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation

repo = Path(sys.argv[1])
distribution = InstalledDistribution(Path(sys.argv[2]), tool_release="5.1.0")
planner = build_planner_request(repo, distribution, frozenset())
plan = plan_reconciliation(planner)

def terminate(phase, identity):
    if (phase, identity) == ("published", ".standards/catalog.toml"):
        os._exit(74)

apply_reconciliation(ApplyRequest(planner, plan, fault_hook=terminate))
raise AssertionError("termination fault did not run")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, str(repo), str(newer.package_root)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 74, completed.stderr
    assert list(repo.rglob(".project-standards-*.tmp"))
    assert (
        detect_control_plane_state(repo, tool_release="5.1.0").kind is StateKind.INTERRUPTED_REFRESH
    )
    assert (
        run(
            ["--repo", str(repo), "--repair-state", "--apply", "--json"],
            distribution=newer,
        )
        == 0
    )
    capsys.readouterr()
    assert not list(repo.rglob(".project-standards-*.tmp"))
    assert run(["--repo", str(repo), "--json"], distribution=newer) == 1
