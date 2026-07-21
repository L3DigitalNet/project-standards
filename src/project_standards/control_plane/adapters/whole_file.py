"""Exclusive whole-file inspection, rendering, and lifecycle classification."""

from __future__ import annotations

from dataclasses import dataclass

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
)
from project_standards.control_plane.codec import content_digest
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    ControlPlaneError,
)
from project_standards.control_plane.models import LockedUnit
from project_standards.control_plane.snapshot import EntryKind, SnapshotEntry
from project_standards.package_contract.paths import PackageVersion, SafeRelativePath
from project_standards.package_contract.payload import AdapterKind, ArtifactPolicy


class WholeFileAdapter:
    """Treat arbitrary bytes as the single exclusive `$file` semantic unit."""

    kind = AdapterKind.WHOLE_FILE

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        if scopes != ("$file",):
            raise ControlPlaneError("whole-file inspection requires one $file scope")
        digest = content_digest(content)
        return AdapterState(
            content=content,
            units=(AdapterUnit("$file", content, content, digest),),
        )

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        if len(changes) != 1 or changes[0].scope != "$file":
            raise ControlPlaneError("whole-file rendering requires one $file change")
        change = changes[0]
        if change.kind in {ActionKind.CREATE, ActionKind.ADOPT, ActionKind.UPDATE}:
            if change.content is None:
                raise ControlPlaneError("whole-file mutation requires complete content")
            return change.content
        if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
            if change.content is not None:
                raise ControlPlaneError("non-mutating whole-file change cannot replace content")
            return state.content
        if change.kind is ActionKind.REMOVE:
            if change.content is not None:
                raise ControlPlaneError("whole-file removal cannot carry content")
            return b""
        raise ControlPlaneError("whole-file adapter received an unsupported action")


@dataclass(frozen=True, slots=True)
class WholeFileIntent:
    """One selected package's desired exclusive file bytes and lifecycle policy."""

    standard_id: str
    version: PackageVersion
    content: bytes
    policy: ArtifactPolicy
    mode: str | None


@dataclass(frozen=True, slots=True)
class WholeFilePlan:
    """One target-level classification with either an action or a finding."""

    action: ControlAction | None
    finding: ControlFinding | None
    mode: str | None
    created_container: bool


def _finding(
    code: str,
    path: SafeRelativePath,
    standard_id: str,
    version: str,
    message: str,
) -> WholeFilePlan:
    return WholeFilePlan(
        action=None,
        finding=ControlFinding(
            code=code,
            severity="error",
            standard_id=standard_id,
            version=version,
            path=path.original,
            identity="$file",
            message=message,
            hint="preserve the file and resolve ownership or local modifications explicitly",
        ),
        mode=None,
        created_container=False,
    )


def _action(
    kind: ActionKind,
    path: SafeRelativePath,
    standard_id: str,
    entry: SnapshotEntry,
    *,
    content: bytes | None,
    mode: str | None,
    created_container: bool,
) -> WholeFilePlan:
    after = content_digest(content).value if content is not None else None
    return WholeFilePlan(
        action=ControlAction(
            kind=kind,
            target=path.original,
            adapter=AdapterKind.WHOLE_FILE.value,
            scope="$file",
            standard_id=standard_id,
            summary=f"{kind.value} exclusive whole-file artifact",
            before_digest=entry.precondition_digest.value,
            after_digest=after,
            content=content,
        ),
        finding=None,
        mode=mode,
        created_container=created_container,
    )


def _modified(entry: SnapshotEntry, previous: LockedUnit) -> bool:
    return (
        entry.kind is not EntryKind.REGULAR
        or entry.content_digest != previous.content_digest
        or (previous.mode is not None and entry.mode != previous.mode)
    )


def _managed_guard(
    path: SafeRelativePath,
    entry: SnapshotEntry,
    standard_id: str,
    version: str,
    previous: LockedUnit,
) -> WholeFilePlan | None:
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        return _action(
            ActionKind.PRESERVE,
            path,
            standard_id,
            entry,
            content=None,
            mode=entry.mode,
            created_container=previous.created_container,
        )
    if _modified(entry, previous):
        return _finding(
            "CP-MODIFIED-MANAGED",
            path,
            standard_id,
            version,
            "managed whole-file content or mode differs from the lock",
        )
    return None


def _intent_conflict(
    path: SafeRelativePath,
    intents: tuple[WholeFileIntent, ...],
) -> WholeFilePlan | None:
    if len(intents) < 2:
        return None
    ids = [intent.standard_id for intent in intents]
    code = "CP-DUPLICATE-IDENTITY" if len(ids) != len(set(ids)) else "CP-PACKAGE-OVERLAP"
    return _finding(
        code,
        path,
        min(ids),
        min(intent.version.value for intent in intents),
        "whole-file target has duplicate or overlapping package ownership",
    )


def plan_whole_file(
    path: SafeRelativePath,
    entry: SnapshotEntry,
    intents: tuple[WholeFileIntent, ...],
    *,
    previous: LockedUnit | None,
) -> WholeFilePlan:
    """Classify one exclusive target without mutating the snapshot or repository."""
    conflict = _intent_conflict(path, intents)
    if conflict is not None:
        return conflict
    intent = intents[0] if intents else None
    standard_id = (
        intent.standard_id
        if intent is not None
        else (previous.owners[0] if previous is not None else "project-standards")
    )
    version = (
        intent.version.value
        if intent is not None
        else (previous.versions[previous.owners[0]].value if previous is not None else "")
    )

    if previous is not None and (
        previous.path != path
        or previous.adapter is not AdapterKind.WHOLE_FILE
        or previous.scope != "$file"
        or len(previous.owners) != 1
    ):
        return _finding(
            "CP-LOCK-INCONSISTENT",
            path,
            standard_id,
            version,
            "whole-file lock record does not describe one exclusive target",
        )

    if intent is None:
        if previous is None:
            return WholeFilePlan(None, None, None, False)
        guarded = _managed_guard(path, entry, standard_id, version, previous)
        if guarded is not None:
            return guarded
        if not previous.created_container:
            return _action(
                ActionKind.PRESERVE,
                path,
                standard_id,
                entry,
                content=None,
                mode=entry.mode,
                created_container=False,
            )
        return _action(
            ActionKind.REMOVE,
            path,
            standard_id,
            entry,
            content=None,
            mode=None,
            created_container=True,
        )

    desired_digest = content_digest(intent.content)
    if previous is None:
        if entry.kind is EntryKind.MISSING:
            return _action(
                ActionKind.CREATE,
                path,
                standard_id,
                entry,
                content=intent.content,
                mode=intent.mode,
                created_container=True,
            )
        if entry.kind is EntryKind.REGULAR and entry.content_digest == desired_digest:
            return _action(
                ActionKind.ADOPT,
                path,
                standard_id,
                entry,
                content=intent.content,
                mode=intent.mode,
                created_container=False,
            )
        if intent.policy is ArtifactPolicy.CREATE_ONLY and entry.kind is EntryKind.REGULAR:
            return _action(
                ActionKind.PRESERVE,
                path,
                standard_id,
                entry,
                content=None,
                mode=entry.mode,
                created_container=False,
            )
        return _finding(
            "CP-CONSUMER-CONFLICT",
            path,
            standard_id,
            version,
            "pre-existing whole-file content cannot be overwritten implicitly",
        )

    if previous.owners != (intent.standard_id,):
        return _finding(
            "CP-PACKAGE-OVERLAP",
            path,
            standard_id,
            version,
            "selected package does not match exclusive lock ownership",
        )
    guarded = _managed_guard(path, entry, standard_id, version, previous)
    if guarded is not None:
        return guarded
    if entry.content_digest == desired_digest and (
        intent.mode is None or entry.mode == intent.mode
    ):
        return _action(
            ActionKind.NOOP,
            path,
            standard_id,
            entry,
            content=None,
            mode=intent.mode,
            created_container=previous.created_container,
        )
    return _action(
        ActionKind.UPDATE,
        path,
        standard_id,
        entry,
        content=intent.content,
        mode=intent.mode,
        created_container=previous.created_container,
    )
