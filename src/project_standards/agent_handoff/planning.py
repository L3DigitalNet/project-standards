"""Two-phase, repository-confined adoption and upgrade planning."""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from project_standards.adopt.engine import Action, build_plan, execute_plan, render_action
from project_standards.adopt.errors import AdoptError, WriteError
from project_standards.adopt.manifest import BUNDLES_DIR, InstallPolicy
from project_standards.agent_handoff.integrations.claude import (
    CLAUDE_COMMAND,
    merge_claude_settings,
    merge_claude_settings_json,
)
from project_standards.agent_handoff.integrations.codex import merge_codex_config
from project_standards.agent_handoff.integrations.instructions import (
    instruction_targets,
    merge_instruction_block,
)
from project_standards.agent_handoff.integrations.markers import (
    CODEX_HOOK_MARKERS,
    INSTRUCTION_MARKERS,
    PROJECT_CONFIG_MARKERS,
    IntegrationConflictError,
    MarkerPair,
    parse_marked_block,
)
from project_standards.agent_handoff.integrations.project_config import merge_project_config
from project_standards.agent_handoff.model import (
    ChangeKind,
    Finding,
    Harness,
    OperationReport,
    PlannedChange,
    ProvenanceLock,
    StartupMode,
)
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot

_STANDARD_VERSION = "1.0"
_LOCK_PATH = ".agents/agent-handoff/manifest.json"
_HOOK_PATH = ".agents/hooks/agent-handoff/session_start.py"
_OWNED_SUFFIX = "#agent-handoff"


@dataclass(frozen=True)
class _DynamicWrite:
    path: str
    data: bytes
    precondition_sha256: str | None
    require_absent: bool


@dataclass(frozen=True)
class AdoptionPlan:
    """A complete non-mutating plan whose writes are safe only while preconditions hold."""

    repository: RepositoryRoot
    standard_ids: tuple[str, ...]
    startup: StartupMode
    harnesses: tuple[Harness, ...]
    changes: tuple[PlannedChange, ...]
    findings: tuple[Finding, ...]
    static_actions: tuple[Action, ...]
    dynamic_writes: tuple[_DynamicWrite, ...]

    @property
    def blocked(self) -> bool:
        return any(finding.severity == "error" for finding in self.findings) or any(
            change.kind is ChangeKind.BLOCKED for change in self.changes
        )


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(code: str, path: str, message: str, guidance: str) -> Finding:
    return Finding(
        code=code,
        severity="error",
        path=path,
        locus="preflight",
        message=message,
        guidance=guidance,
    )


def _read_optional(repository: RepositoryRoot, relative: str) -> bytes | None:
    target = repository.consumer_path(relative)
    if not target.exists():
        return None
    return repository.read_bytes(relative)


def _normalized_mapping(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _marked_owned_bytes(text: str, markers: MarkerPair, *, syntax: str) -> bytes:
    span = parse_marked_block(text, markers)
    if span is None:
        raise IntegrationConflictError("managed integration block is missing")
    block = text[span.start : span.end]
    body = "\n".join(block.splitlines()[1:-1]) + "\n"
    if syntax == "toml":
        try:
            return _normalized_mapping(tomllib.loads(body))
        except tomllib.TOMLDecodeError as exc:
            raise IntegrationConflictError("managed integration block is invalid TOML") from exc
    if syntax == "yaml":
        try:
            return _normalized_mapping(yaml.safe_load(body))
        except yaml.YAMLError as exc:
            raise IntegrationConflictError("managed integration block is invalid YAML") from exc
    return body.replace("\r\n", "\n").encode()


def _claude_owned_bytes(text: str) -> bytes:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntegrationConflictError("Claude settings are invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise IntegrationConflictError("Claude settings must contain an object")
    settings = cast(dict[str, object], parsed)
    if merge_claude_settings(settings) != settings:
        raise IntegrationConflictError("managed Claude handler is missing")
    hooks_value = settings.get("hooks")
    hooks = cast(dict[str, object], hooks_value)
    groups_value = hooks.get("SessionStart")
    for group_value in cast(list[object], groups_value):
        group = cast(dict[str, object], group_value)
        handlers_value = group.get("hooks")
        for handler_value in cast(list[object], handlers_value):
            handler = cast(dict[str, object], handler_value)
            if handler.get("command") == CLAUDE_COMMAND:
                return _normalized_mapping(group)
    raise IntegrationConflictError("managed Claude handler is missing")


def _owned_bytes(key: str, data: bytes) -> bytes:
    if not key.endswith(_OWNED_SUFFIX):
        return data
    path = key.removesuffix(_OWNED_SUFFIX)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IntegrationConflictError("managed integration is not UTF-8") from exc
    if path == ".claude/settings.json":
        return _claude_owned_bytes(text)
    if path == ".codex/config.toml":
        return _marked_owned_bytes(text, CODEX_HOOK_MARKERS, syntax="toml")
    if path == ".project-standards.yml":
        return _marked_owned_bytes(text, PROJECT_CONFIG_MARKERS, syntax="yaml")
    if path in {"AGENTS.md", "CLAUDE.md"}:
        return _marked_owned_bytes(text, INSTRUCTION_MARKERS, syntax="text")
    raise IntegrationConflictError(f"unknown managed integration key {key!r}")


def _load_lock(
    repository: RepositoryRoot,
    findings: list[Finding],
    changes: list[PlannedChange],
    *,
    required: bool,
) -> tuple[ProvenanceLock | None, bytes | None]:
    try:
        raw = _read_optional(repository, _LOCK_PATH)
    except RepositoryBoundaryError as exc:
        findings.append(
            _finding("AH-PATH-BOUNDARY", _LOCK_PATH, str(exc), "Replace the unsafe path.")
        )
        changes.append(PlannedChange(ChangeKind.BLOCKED, _LOCK_PATH))
        return None, None
    if raw is None:
        if required:
            findings.append(
                _finding(
                    "AH-LOCK-MISSING",
                    _LOCK_PATH,
                    "the provenance lock is required for upgrade",
                    "Adopt agent-handoff before running upgrade.",
                )
            )
            changes.append(PlannedChange(ChangeKind.BLOCKED, _LOCK_PATH))
        return None, None
    try:
        return ProvenanceLock.model_validate_json(raw), raw
    except ValidationError:
        findings.append(
            _finding(
                "AH-LOCK-INVALID",
                _LOCK_PATH,
                "the provenance lock is invalid",
                "Restore a valid lock or reconcile the installation manually.",
            )
        )
        changes.append(PlannedChange(ChangeKind.BLOCKED, _LOCK_PATH))
        return None, raw


def _verify_lock(
    repository: RepositoryRoot,
    lock: ProvenanceLock,
    findings: list[Finding],
    changes: list[PlannedChange],
) -> set[str]:
    verified: set[str] = set()
    for key, expected in sorted(lock.managed.items()):
        path = key.removesuffix(_OWNED_SUFFIX)
        try:
            current = _read_optional(repository, path)
            if current is None or _digest(_owned_bytes(key, current)) != expected:
                raise IntegrationConflictError("managed content differs from its lock")
        except IntegrationConflictError, RepositoryBoundaryError:
            findings.append(
                _finding(
                    "AH-LOCK-DRIFT",
                    path,
                    "managed content is missing or differs from the provenance lock",
                    "Restore the locked content or reconcile the local change manually.",
                )
            )
            changes.append(PlannedChange(ChangeKind.BLOCKED, path))
            continue
        verified.add(key)
    return verified


def _preflight_static(
    repository: RepositoryRoot,
    standard_ids: tuple[str, ...],
    *,
    startup: StartupMode,
    verified_lock_keys: set[str],
    findings: list[Finding],
    changes: list[PlannedChange],
    managed_hashes: dict[str, str],
) -> list[Action]:
    try:
        generic = build_plan(list(standard_ids), bundles_dir=BUNDLES_DIR)
    except AdoptError as exc:
        findings.append(_finding("AH-STATIC-PLAN", ".", str(exc), "Fix the package request."))
        changes.append(PlannedChange(ChangeKind.BLOCKED, "."))
        return []

    executable: list[Action] = []
    for action in generic:
        is_agent_handoff = "agent-handoff" in action.standards
        relative = action.target if action.kind == "fragment" else action.dest
        assert relative is not None
        if is_agent_handoff and action.kind == "fragment":
            continue
        if is_agent_handoff and relative == _LOCK_PATH:
            continue
        if is_agent_handoff and relative == _HOOK_PATH and startup is StartupMode.MANUAL:
            continue
        try:
            repository.consumer_path(relative)
            if action.kind == "fragment":
                action.source_path.read_bytes()
                executable.append(action)
                continue
            desired = render_action(action)
            current = _read_optional(repository, relative)
        except (AdoptError, OSError, RepositoryBoundaryError) as exc:
            findings.append(
                _finding("AH-PATH-BOUNDARY", relative, str(exc), "Repair the unsafe path.")
            )
            changes.append(PlannedChange(ChangeKind.BLOCKED, relative))
            continue

        if is_agent_handoff and action.install_policy is InstallPolicy.MANAGED:
            managed_hashes[relative] = _digest(desired)
        if current is None:
            kind = ChangeKind.CREATE
            planned = replace(action, require_absent=True)
            executable.append(planned)
        elif action.install_policy is InstallPolicy.CREATE_ONLY or current == desired:
            kind = ChangeKind.SKIP
        elif is_agent_handoff and relative in verified_lock_keys:
            kind = ChangeKind.UPDATE
            executable.append(replace(action, precondition_sha256=_digest(current)))
        elif is_agent_handoff:
            kind = ChangeKind.BLOCKED
            findings.append(
                _finding(
                    "AH-MANAGED-UNOWNED",
                    relative,
                    "an existing managed destination has no verified provenance",
                    "Remove it, restore its lock, or reconcile it manually.",
                )
            )
        else:
            kind = ChangeKind.SKIP
        changes.append(
            PlannedChange(
                kind,
                relative,
                source=str(action.source_path),
                precondition_sha256=(
                    _digest(cast(bytes, current)) if kind is ChangeKind.UPDATE else None
                ),
            )
        )

    try:
        execute_plan(executable, repository.path, force=True, dry_run=True)
    except AdoptError as exc:
        findings.append(
            _finding("AH-STATIC-PREFLIGHT", ".", str(exc), "Repair the static artifact error.")
        )
        changes.append(PlannedChange(ChangeKind.BLOCKED, "."))
    return executable


def _plan_dynamic(
    repository: RepositoryRoot,
    path: str,
    renderer: Callable[[str], str],
    *,
    findings: list[Finding],
    changes: list[PlannedChange],
    managed_hashes: dict[str, str],
    writes: list[_DynamicWrite],
) -> None:
    try:
        current = _read_optional(repository, path)
        current_text = "" if current is None else current.decode("utf-8")
        desired = renderer(current_text).encode()
        key = f"{path}{_OWNED_SUFFIX}"
        managed_hashes[key] = _digest(_owned_bytes(key, desired))
    except (IntegrationConflictError, RepositoryBoundaryError, UnicodeError) as exc:
        findings.append(
            _finding(
                "AH-INTEGRATION-CONFLICT",
                path,
                str(exc),
                "Reconcile the existing integration before adoption.",
            )
        )
        changes.append(PlannedChange(ChangeKind.BLOCKED, path))
        return

    if current is None:
        kind = ChangeKind.CREATE
        precondition = None
        writes.append(_DynamicWrite(path, desired, None, True))
    elif current == desired:
        kind = ChangeKind.SKIP
        precondition = None
    else:
        kind = ChangeKind.UPDATE
        precondition = _digest(current)
        writes.append(_DynamicWrite(path, desired, precondition, False))
    changes.append(
        PlannedChange(
            kind,
            path,
            source="agent-handoff integration",
            precondition_sha256=precondition,
        )
    )


def _build_plan(
    *,
    repository: Path,
    standard_ids: tuple[str, ...],
    startup: StartupMode,
    harnesses: tuple[Harness, ...],
    upgrade: bool,
) -> AdoptionPlan:
    findings: list[Finding] = []
    changes: list[PlannedChange] = []
    try:
        root = RepositoryRoot.from_input(repository)
        # Validate the profile before inspecting any consumer files.
        ProvenanceLock(
            standard_version=_STANDARD_VERSION,
            startup=startup,
            harnesses=harnesses,
            managed={},
        )
    except (RepositoryBoundaryError, ValidationError, ValueError) as exc:
        root = RepositoryRoot(repository)
        findings.append(_finding("AH-USAGE", ".", str(exc), "Correct the adoption arguments."))
        changes.append(PlannedChange(ChangeKind.BLOCKED, "."))
        return AdoptionPlan(
            root, standard_ids, startup, harnesses, tuple(changes), tuple(findings), (), ()
        )

    lock, lock_bytes = _load_lock(root, findings, changes, required=upgrade)
    verified: set[str] = _verify_lock(root, lock, findings, changes) if lock is not None else set()

    managed_hashes: dict[str, str] = {}
    static_actions = _preflight_static(
        root,
        standard_ids,
        startup=startup,
        verified_lock_keys=verified,
        findings=findings,
        changes=changes,
        managed_hashes=managed_hashes,
    )
    writes: list[_DynamicWrite] = []
    _plan_dynamic(
        root,
        ".project-standards.yml",
        lambda text: merge_project_config(text, startup=startup, harnesses=harnesses),
        findings=findings,
        changes=changes,
        managed_hashes=managed_hashes,
        writes=writes,
    )
    for target in instruction_targets(startup, harnesses):
        _plan_dynamic(
            root,
            target,
            merge_instruction_block,
            findings=findings,
            changes=changes,
            managed_hashes=managed_hashes,
            writes=writes,
        )
    if Harness.CLAUDE_CODE in harnesses:
        _plan_dynamic(
            root,
            ".claude/settings.json",
            lambda text: merge_claude_settings_json(text or "{}"),
            findings=findings,
            changes=changes,
            managed_hashes=managed_hashes,
            writes=writes,
        )
    if Harness.CODEX in harnesses:
        try:
            hooks_json_exists = _read_optional(root, ".codex/hooks.json") is not None
        except RepositoryBoundaryError as exc:
            findings.append(
                _finding("AH-PATH-BOUNDARY", ".codex/hooks.json", str(exc), "Repair the path.")
            )
            changes.append(PlannedChange(ChangeKind.BLOCKED, ".codex/hooks.json"))
            hooks_json_exists = True
        _plan_dynamic(
            root,
            ".codex/config.toml",
            lambda text: merge_codex_config(text, hooks_json_exists=hooks_json_exists),
            findings=findings,
            changes=changes,
            managed_hashes=managed_hashes,
            writes=writes,
        )

    if not any(finding.severity == "error" for finding in findings):
        desired_lock = (
            ProvenanceLock(
                standard_version=_STANDARD_VERSION,
                startup=startup,
                harnesses=harnesses,
                managed=managed_hashes,
            )
            .to_json()
            .encode()
        )
        if lock_bytes is None:
            lock_kind = ChangeKind.CREATE
            lock_precondition = None
            writes.append(_DynamicWrite(_LOCK_PATH, desired_lock, None, True))
        elif lock_bytes == desired_lock:
            lock_kind = ChangeKind.SKIP
            lock_precondition = None
        else:
            lock_kind = ChangeKind.UPDATE
            lock_precondition = _digest(lock_bytes)
            writes.append(_DynamicWrite(_LOCK_PATH, desired_lock, lock_precondition, False))
        changes.append(
            PlannedChange(
                lock_kind,
                _LOCK_PATH,
                source="agent-handoff provenance",
                precondition_sha256=lock_precondition,
            )
        )

    return AdoptionPlan(
        repository=root,
        standard_ids=standard_ids,
        startup=startup,
        harnesses=harnesses,
        changes=tuple(changes),
        findings=tuple(findings),
        static_actions=tuple(static_actions),
        dynamic_writes=tuple(writes),
    )


def plan_adoption(
    *,
    repository: Path,
    standard_ids: tuple[str, ...],
    startup: StartupMode,
    harnesses: tuple[Harness, ...],
) -> AdoptionPlan:
    """Return a fully preflighted, non-mutating aggregate adoption plan."""
    return _build_plan(
        repository=repository,
        standard_ids=standard_ids,
        startup=startup,
        harnesses=harnesses,
        upgrade=False,
    )


def plan_upgrade(*, repository: Path, standard_ids: tuple[str, ...]) -> AdoptionPlan:
    """Plan a refresh only when every prior managed lock entry still matches."""
    findings: list[Finding] = []
    changes: list[PlannedChange] = []
    try:
        root = RepositoryRoot.from_input(repository)
    except RepositoryBoundaryError:
        root = RepositoryRoot(repository)
    lock, _raw = _load_lock(root, findings, changes, required=True)
    if lock is None:
        return AdoptionPlan(
            root,
            standard_ids,
            StartupMode.MANUAL,
            (),
            tuple(changes),
            tuple(findings),
            (),
            (),
        )
    return _build_plan(
        repository=root.path,
        standard_ids=standard_ids,
        startup=lock.startup,
        harnesses=lock.harnesses,
        upgrade=True,
    )


def check_provenance_lock(
    repository: RepositoryRoot, *, required: bool = True
) -> tuple[ProvenanceLock | None, tuple[Finding, ...]]:
    """Read and verify the installed lock using the planner's normalized hashes."""
    findings: list[Finding] = []
    changes: list[PlannedChange] = []
    lock, _raw = _load_lock(repository, findings, changes, required=required)
    if lock is not None:
        _verify_lock(repository, lock, findings, changes)
    return lock, tuple(findings)


def _recheck_dynamic(repository: RepositoryRoot, write: _DynamicWrite) -> None:
    current = _read_optional(repository, write.path)
    if write.require_absent:
        if current is not None:
            raise WriteError(f"destination changed after preflight: {write.path}")
        return
    if current is None or write.precondition_sha256 is None:
        raise WriteError(f"destination changed after preflight: {write.path}")
    if _digest(current) != write.precondition_sha256:
        raise WriteError(f"destination changed after preflight: {write.path}")


def apply_adoption(plan: AdoptionPlan, *, dry_run: bool) -> OperationReport:
    """Apply a clean plan, rechecking every write and publishing the lock last."""
    if plan.blocked or dry_run:
        return OperationReport(
            repository=str(plan.repository.path),
            standard_version=_STANDARD_VERSION,
            changes=plan.changes,
            findings=plan.findings,
        )

    applied: list[PlannedChange] = []
    skipped = [change for change in plan.changes if change.kind is ChangeKind.SKIP]
    active_path = "."
    try:
        for action in sorted(plan.static_actions, key=lambda item: item.dest or item.target or ""):
            active_path = action.dest or action.target or "."
            execute_plan([action], plan.repository.path, force=True, dry_run=False)
            if action.kind != "fragment":
                applied.extend(
                    change
                    for change in plan.changes
                    if change.path == active_path
                    and change.kind in {ChangeKind.CREATE, ChangeKind.UPDATE}
                )
        writes = sorted(
            (write for write in plan.dynamic_writes if write.path != _LOCK_PATH),
            key=lambda write: write.path,
        )
        lock_writes = [write for write in plan.dynamic_writes if write.path == _LOCK_PATH]
        for write in [*writes, *lock_writes]:
            active_path = write.path
            _recheck_dynamic(plan.repository, write)
            plan.repository.write_bytes(write.path, write.data)
            applied.extend(
                change
                for change in plan.changes
                if change.path == active_path
                and change.kind in {ChangeKind.CREATE, ChangeKind.UPDATE}
            )
    except (AdoptError, RepositoryBoundaryError) as exc:
        finding = _finding(
            "AH-APPLY-FAILED",
            active_path,
            str(exc),
            "Resolve the I/O or precondition failure, then re-plan before retrying.",
        )
        return OperationReport(
            repository=str(plan.repository.path),
            standard_version=_STANDARD_VERSION,
            changes=(*applied, *skipped, PlannedChange(ChangeKind.BLOCKED, active_path)),
            findings=(*plan.findings, finding),
        )
    return OperationReport(
        repository=str(plan.repository.path),
        standard_version=_STANDARD_VERSION,
        changes=plan.changes,
        findings=plan.findings,
    )
