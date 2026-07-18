from __future__ import annotations

import os
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.base import UnitChange
from project_standards.control_plane.adapters.registry import AdapterRegistry
from project_standards.control_plane.adapters.whole_file import (
    WholeFileAdapter,
    WholeFileIntent,
    plan_whole_file,
)
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.models import LockedUnit
from project_standards.control_plane.snapshot import (
    EntryKind,
    RepositorySnapshot,
    SnapshotEntry,
)
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import AdapterKind, ArtifactPolicy

_DIGEST_A = f"sha256:{'a' * 64}"


def _path(value: str = "tool.py") -> SafeRelativePath:
    return SafeRelativePath.parse(value)


def _intent(
    content: bytes = b"new\n",
    *,
    standard_id: str = "demo",
    policy: ArtifactPolicy = ArtifactPolicy.MANAGED,
    mode: str | None = "0644",
) -> WholeFileIntent:
    return WholeFileIntent(
        standard_id=standard_id,
        version=PackageVersion("1.2"),
        content=content,
        policy=policy,
        mode=mode,
    )


def _locked(
    content_digest: str,
    *,
    policy: ArtifactPolicy = ArtifactPolicy.MANAGED,
    mode: str | None = "0644",
    created_container: bool = True,
) -> LockedUnit:
    return LockedUnit.model_validate(
        {
            "path": "tool.py",
            "adapter": "whole-file",
            "scope": "$file",
            "owners": ["demo"],
            "versions": {"demo": "1.1"},
            "provenance": "source",
            "policy": policy.value,
            "semantic_digest": content_digest,
            "content_digest": content_digest,
            "mode": mode,
            "created_container": created_container,
        }
    )


def _snapshot(
    tmp_path: Path,
    content: bytes | None,
) -> tuple[RepositorySnapshot, SnapshotEntry]:
    if content is not None:
        (tmp_path / "tool.py").write_bytes(content)
        (tmp_path / "tool.py").chmod(0o644)
    snapshot = RepositorySnapshot.capture(tmp_path, (_path(),))
    return snapshot, snapshot.entry(_path())


def test_snapshot_records_regular_missing_and_symlink_state(tmp_path: Path) -> None:
    regular = tmp_path / "regular.txt"
    regular.write_bytes(b"exact\r\nbytes")
    regular.chmod(0o640)
    link = tmp_path / "link.txt"
    link.symlink_to("regular.txt")

    snapshot = RepositorySnapshot.capture(
        tmp_path,
        (_path("regular.txt"), _path("missing.txt"), _path("link.txt")),
    )

    regular_entry = snapshot.entry(_path("regular.txt"))
    assert regular_entry.kind is EntryKind.REGULAR
    assert regular_entry.content == b"exact\r\nbytes"
    assert regular_entry.mode == "0640"
    assert regular_entry.content_digest is not None
    assert snapshot.entry(_path("missing.txt")).kind is EntryKind.MISSING
    link_entry = snapshot.entry(_path("link.txt"))
    assert link_entry.kind is EntryKind.SYMLINK
    assert link_entry.link_target == "regular.txt"
    assert link_entry.content is None


def test_snapshot_rejects_duplicate_targets_before_reading(tmp_path: Path) -> None:
    (tmp_path / "tool.py").write_text("content", encoding="utf-8")

    with pytest.raises(ControlPlaneError, match="collision"):
        RepositorySnapshot.capture(tmp_path, (_path(), _path()))


def test_snapshot_rejects_ancestor_symlink_escape_before_content_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe = tmp_path / "safe.txt"
    safe.write_text("must-not-be-read", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    reads = 0
    original_read = os.read

    def counted_read(descriptor: int, size: int) -> bytes:
        nonlocal reads
        reads += 1
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", counted_read)

    with pytest.raises(ControlPlaneError, match="ancestor"):
        RepositorySnapshot.capture(
            tmp_path,
            (_path("safe.txt"), _path("escape/secret.txt")),
        )

    assert reads == 0


def test_snapshot_precondition_detects_concurrent_content_or_mode_change(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tool.py"
    path.write_bytes(b"before")
    path.chmod(0o644)
    snapshot = RepositorySnapshot.capture(tmp_path, (_path(),))
    path.write_bytes(b"after")

    with pytest.raises(ControlPlaneError, match="precondition changed"):
        snapshot.assert_current()

    path.write_bytes(b"before")
    path.chmod(0o600)
    with pytest.raises(ControlPlaneError, match="precondition changed"):
        snapshot.assert_current()


@pytest.mark.parametrize("mutation", ["add", "remove", "replace-type", "chmod"])
def test_directory_snapshot_precondition_detects_inventory_or_mode_change(
    tmp_path: Path,
    mutation: str,
) -> None:
    directory = tmp_path / "declared"
    directory.mkdir()
    directory.chmod(0o755)
    child = directory / "child"
    child.write_text("before", encoding="utf-8")
    snapshot = RepositorySnapshot.capture(tmp_path, (_path("declared"),))
    entry = snapshot.entry(_path("declared"))
    assert entry.kind is EntryKind.DIRECTORY
    assert entry.mode == "0755"

    if mutation == "add":
        (directory / "added").write_text("new", encoding="utf-8")
    elif mutation == "remove":
        child.unlink()
    elif mutation == "replace-type":
        child.unlink()
        child.mkdir()
    else:
        directory.chmod(0o700)

    with pytest.raises(ControlPlaneError, match="precondition changed"):
        snapshot.assert_current()


@pytest.mark.parametrize("special_mode", [0o1755, 0o2755])
def test_directory_snapshot_accepts_and_binds_special_mode_bits(
    tmp_path: Path,
    special_mode: int,
) -> None:
    directory = tmp_path / "declared"
    directory.mkdir()
    directory.chmod(special_mode)

    snapshot = RepositorySnapshot.capture(tmp_path, (_path("declared"),))

    assert snapshot.entry(_path("declared")).mode == "0755"
    directory.chmod(0o755)
    with pytest.raises(ControlPlaneError, match="precondition changed"):
        snapshot.assert_current()


def test_whole_file_adapter_inspects_and_renders_the_only_valid_scope() -> None:
    adapter = WholeFileAdapter()
    state = adapter.inspect(b"old\n", ("$file",))

    assert state.content == b"old\n"
    assert state.units[0].scope == "$file"
    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, "$file", b"new\n"),),
        )
        == b"new\n"
    )
    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.NOOP, "$file"),),
        )
        == b"old\n"
    )
    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.PRESERVE, "$file"),),
        )
        == b"old\n"
    )
    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.REMOVE, "$file"),),
        )
        == b""
    )


@pytest.mark.parametrize("scopes", [(), ("bad",), ("$file", "$file")])
def test_whole_file_adapter_rejects_malformed_or_duplicate_scope(
    scopes: tuple[str, ...],
) -> None:
    with pytest.raises(ControlPlaneError):
        WholeFileAdapter().inspect(b"content", scopes)


def test_adapter_registry_rejects_duplicate_kind() -> None:
    registry = AdapterRegistry()
    registry.register(AdapterKind.WHOLE_FILE, WholeFileAdapter())

    with pytest.raises(ControlPlaneError, match="already registered"):
        registry.register(AdapterKind.WHOLE_FILE, WholeFileAdapter())

    assert registry.get(AdapterKind.WHOLE_FILE).kind is AdapterKind.WHOLE_FILE


def test_whole_file_plan_creates_missing_managed_artifact(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, None)

    plan = plan_whole_file(_path(), entry, (_intent(),), previous=None)

    assert plan.finding is None
    assert plan.action is not None and plan.action.kind is ActionKind.CREATE
    assert plan.action.content == b"new\n"
    assert plan.mode == "0644"
    assert plan.created_container


def test_whole_file_plan_adopts_equal_consumer_file_without_rewrite(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, b"new\n")

    plan = plan_whole_file(_path(), entry, (_intent(),), previous=None)

    assert plan.finding is None
    assert plan.action is not None and plan.action.kind is ActionKind.ADOPT
    assert not plan.created_container


def test_whole_file_plan_rejects_different_consumer_file(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, b"consumer\n")

    plan = plan_whole_file(_path(), entry, (_intent(),), previous=None)

    assert plan.action is None
    assert plan.finding is not None
    assert plan.finding.code == "CP-CONSUMER-CONFLICT"


def test_whole_file_plan_updates_and_then_reaches_noop(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, b"old\n")
    previous = _locked(cast_digest(entry.content_digest))

    update = plan_whole_file(_path(), entry, (_intent(),), previous=previous)

    assert update.action is not None and update.action.kind is ActionKind.UPDATE

    _, updated_entry = _snapshot(tmp_path, b"new\n")
    updated_lock = _locked(cast_digest(updated_entry.content_digest))
    noop = plan_whole_file(_path(), updated_entry, (_intent(),), previous=updated_lock)
    assert noop.action is not None and noop.action.kind is ActionKind.NOOP


def test_whole_file_ignores_mode_drift_when_mode_is_not_declared(
    tmp_path: Path,
) -> None:
    _, entry = _snapshot(tmp_path, b"new\n")
    previous = _locked(cast_digest(entry.content_digest), mode=None)
    (tmp_path / "tool.py").chmod(0o600)
    snapshot = RepositorySnapshot.capture(tmp_path, (_path(),))

    plan = plan_whole_file(
        _path(),
        snapshot.entry(_path()),
        (_intent(mode=None),),
        previous=previous,
    )

    assert plan.finding is None
    assert plan.action is not None and plan.action.kind is ActionKind.NOOP
    assert plan.mode is None


def cast_digest(value: Sha256Digest | None) -> str:
    assert value is not None
    return value.value


@pytest.mark.parametrize("enabled", [True, False])
def test_create_only_content_is_preserved_after_creation(
    tmp_path: Path,
    enabled: bool,
) -> None:
    _, entry = _snapshot(tmp_path, b"consumer-edited\n")
    previous = _locked(
        _DIGEST_A,
        policy=ArtifactPolicy.CREATE_ONLY,
        created_container=True,
    )
    intents = (
        (_intent(content=b"package-new\n", policy=ArtifactPolicy.CREATE_ONLY),) if enabled else ()
    )

    plan = plan_whole_file(_path(), entry, intents, previous=previous)

    assert plan.finding is None
    assert plan.action is not None and plan.action.kind is ActionKind.PRESERVE


def test_create_only_preserves_different_preexisting_consumer_file(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, b"consumer\n")

    plan = plan_whole_file(
        _path(),
        entry,
        (_intent(policy=ArtifactPolicy.CREATE_ONLY),),
        previous=None,
    )

    assert plan.finding is None
    assert plan.action is not None and plan.action.kind is ActionKind.PRESERVE
    assert not plan.created_container


def test_whole_file_removes_only_unchanged_platform_created_managed_file(
    tmp_path: Path,
) -> None:
    _, entry = _snapshot(tmp_path, b"old\n")
    digest = cast_digest(entry.content_digest)

    removable = plan_whole_file(
        _path(),
        entry,
        (),
        previous=_locked(digest, created_container=True),
    )
    adopted = plan_whole_file(
        _path(),
        entry,
        (),
        previous=_locked(digest, created_container=False),
    )

    assert removable.action is not None and removable.action.kind is ActionKind.REMOVE
    assert adopted.action is not None and adopted.action.kind is ActionKind.PRESERVE


def test_whole_file_rejects_modified_managed_content_or_mode(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, b"live\n")
    previous = _locked(_DIGEST_A)

    content_drift = plan_whole_file(_path(), entry, (_intent(),), previous=previous)
    assert content_drift.finding is not None
    assert content_drift.finding.code == "CP-MODIFIED-MANAGED"

    digest = cast_digest(entry.content_digest)
    mode_drift = plan_whole_file(
        _path(),
        entry,
        (_intent(),),
        previous=_locked(digest, mode="0600"),
    )
    assert mode_drift.finding is not None
    assert mode_drift.finding.code == "CP-MODIFIED-MANAGED"


def test_whole_file_rejects_duplicate_identity_and_package_overlap(tmp_path: Path) -> None:
    _, entry = _snapshot(tmp_path, None)

    duplicate = plan_whole_file(
        _path(),
        entry,
        (_intent(), _intent()),
        previous=None,
    )
    overlap = plan_whole_file(
        _path(),
        entry,
        (_intent(), _intent(standard_id="other")),
        previous=None,
    )

    assert duplicate.finding is not None
    assert duplicate.finding.code == "CP-DUPLICATE-IDENTITY"
    assert overlap.finding is not None
    assert overlap.finding.code == "CP-PACKAGE-OVERLAP"


def test_whole_file_rejects_symlink_target_as_consumer_conflict(tmp_path: Path) -> None:
    (tmp_path / "target.py").write_text("target", encoding="utf-8")
    (tmp_path / "tool.py").symlink_to("target.py")
    snapshot = RepositorySnapshot.capture(tmp_path, (_path(),))

    plan = plan_whole_file(
        _path(),
        snapshot.entry(_path()),
        (_intent(),),
        previous=None,
    )

    assert plan.finding is not None
    assert plan.finding.code == "CP-CONSUMER-CONFLICT"
