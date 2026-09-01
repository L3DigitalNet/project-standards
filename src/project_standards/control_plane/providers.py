"""Contained referenced inputs and the version-selected provider runner."""

from __future__ import annotations

import base64
import io
import json
import os
import platform
import stat
import sys
import tempfile
import threading
from collections.abc import Generator, Iterator, Mapping, Sequence
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from pydantic import ValidationError

from project_standards.control_plane.codec import content_digest
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlFinding,
    ControlPlaneError,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.migration import MigrationReport
from project_standards.control_plane.models import LockedInput
from project_standards.control_plane.provider_subprocess import (
    PROVIDER_TIMEOUT_SECONDS as _DEFAULT_PROVIDER_TIMEOUT_SECONDS,
)
from project_standards.control_plane.provider_subprocess import (
    ProviderSubprocessError,
    ProviderSubprocessOutcome,
    compose_provider_diagnostics,
    encode_provider_request,
    python_worker_argv,
    python_worker_environment,
    run_provider_subprocess,
    safe_failure_detail,
)
from project_standards.control_plane.schemas import MutationPlanSchema, ProviderInputSchema
from project_standards.control_plane.snapshot import (
    RepositorySnapshot,
    canonical_targets,
)
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ExtensionDeclaration,
    JsonObject,
    JsonValue,
    PayloadAvailability,
    ProviderDeclaration,
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ResourceDeclaration,
)

PROVIDER_TIMEOUT_SECONDS: float = _DEFAULT_PROVIDER_TIMEOUT_SECONDS

# Child data may select only constructors fixed here. Resolving a reported name
# through builtins, imports, or module globals would let provider bytes execute a
# second attacker-selected constructor in the trusted parent.
_SAFE_PROVIDER_CAUSE_TYPES: dict[str, type[Exception]] = {"ValueError": ValueError}
_UNKNOWN_PROVIDER_CAUSE = "provider raised an unrecognized exception"


def _safe_repo(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ControlPlaneError("repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ControlPlaneError("repository root could not be inspected") from exc


def _safe_reference(root: Path, value: str) -> tuple[SafeRelativePath, Path]:
    try:
        relative = SafeRelativePath.parse(value)
    except ValueError as exc:
        raise ControlPlaneError("referenced input must be repository-relative") from exc
    if relative.original.startswith(".standards/packages/"):
        raise ControlPlaneError("referenced input cannot use the package namespace")
    candidate = root / relative.normalized
    current = root
    try:
        for part in relative.normalized.parts:
            current /= part
            if current.is_symlink():
                raise ControlPlaneError("referenced input path cannot contain a symlink")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ControlPlaneError("referenced input escapes the repository")
        if not resolved.is_file():
            raise ControlPlaneError("referenced input is not a regular file")
    except FileNotFoundError as exc:
        raise ControlPlaneError("referenced input does not exist") from exc
    except OSError as exc:
        raise ControlPlaneError("referenced input could not be inspected") from exc
    return relative, resolved


def read_locked_input_bytes(repo: Path, locked: LockedInput) -> bytes:
    """Read one lock-authorized input without following any path component."""
    root = _safe_repo(repo)
    root_descriptor = os.open(
        root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    descriptor = root_descriptor
    try:
        for part in locked.path.normalized.parts[:-1]:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise ControlPlaneError(
                    "locked referenced input path contains a symlink or missing ancestor"
                ) from exc
            if descriptor != root_descriptor:
                os.close(descriptor)
            descriptor = child
        try:
            leaf = os.open(
                locked.path.normalized.name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
        except OSError as exc:
            raise ControlPlaneError("locked referenced input is missing or is a symlink") from exc
        try:
            if not stat.S_ISREG(os.fstat(leaf).st_mode):
                raise ControlPlaneError("locked referenced input is not a regular file")
            chunks: list[bytes] = []
            while chunk := os.read(leaf, 1024 * 1024):
                chunks.append(chunk)
            content = b"".join(chunks)
        finally:
            os.close(leaf)
    finally:
        if descriptor != root_descriptor:
            os.close(descriptor)
        os.close(root_descriptor)
    if content_digest(content) != locked.digest:
        raise ControlPlaneError("locked referenced input digest changed")
    return content


def materialize_referenced_input_snapshots(
    repo: Path,
    snapshots: JsonObject,
    *,
    standard_id: str | None = None,
    config: Mapping[str, JsonValue] | None = None,
    extensions: Sequence[ExtensionDeclaration] | None = None,
) -> JsonObject:
    """Attach immutable bytes for every lock-declared referenced input."""
    raw_inputs = snapshots.get("referenced_inputs")
    if raw_inputs is None:
        return dict(snapshots)
    if not isinstance(raw_inputs, list):
        raise ControlPlaneError("provider referenced-input snapshot must be an array")
    locked_inputs: list[LockedInput] = []
    try:
        for raw in raw_inputs:
            locked_inputs.append(LockedInput.model_validate(raw))
    except ValidationError as exc:
        raise ControlPlaneError("provider referenced-input snapshot is invalid") from exc
    keys = [item.natural_key for item in locked_inputs]
    if len(keys) != len(set(keys)):
        raise ControlPlaneError("provider referenced-input snapshot contains a duplicate")
    if standard_id is not None and config is not None and extensions is not None:
        declared = {extension.id: extension for extension in extensions}
        for locked in locked_inputs:
            if locked.standard_id != standard_id:
                raise ControlPlaneError(
                    "provider referenced input does not match the selected package"
                )
            extension = declared.get(locked.extension_id)
            if extension is None:
                raise ControlPlaneError("provider referenced input uses an undeclared extension")
            configured = config.get(extension.option)
            if not isinstance(configured, str):
                raise ControlPlaneError("provider referenced input has no configured path")
            try:
                configured_path = SafeRelativePath.parse(configured)
            except ValueError as exc:
                raise ControlPlaneError(
                    "provider referenced input configured path is not canonical"
                ) from exc
            if configured_path != locked.path:
                raise ControlPlaneError(
                    "provider referenced input does not match its configured path"
                )
    materialized: list[JsonValue] = []
    for locked in sorted(locked_inputs, key=lambda item: item.natural_key):
        content = read_locked_input_bytes(repo, locked)
        materialized.append(
            {
                "standard_id": locked.standard_id,
                "extension_id": locked.extension_id,
                "path": locked.path.original,
                "digest": locked.digest.value,
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    return {
        **snapshots,
        "referenced_input_content": materialized,
    }


def _canonical_target(root: Path, target: SafeRelativePath) -> Path:
    try:
        resolved = (root / target.normalized).resolve(strict=False)
    except OSError as exc:
        raise ControlPlaneError("managed output path could not be resolved") from exc
    if not resolved.is_relative_to(root):
        raise ControlPlaneError("managed output path escapes the repository")
    return resolved


def resolve_referenced_inputs(
    repo: Path,
    *,
    standard_id: str,
    version: PackageVersion,
    config: Mapping[str, JsonValue],
    extensions: tuple[ExtensionDeclaration, ...],
    managed_targets: tuple[SafeRelativePath, ...],
    enabled: bool,
) -> tuple[LockedInput, ...]:
    """Hash declared consumer-owned inputs without claiming or changing them."""
    if not enabled or not extensions:
        return ()
    root = _safe_repo(repo)
    managed = {_canonical_target(root, target) for target in managed_targets}
    inputs: list[LockedInput] = []
    for extension in sorted(extensions, key=lambda item: item.id):
        if extension.option not in config:
            raise ControlPlaneError(
                f"referenced input option is missing or not a path: {extension.option}"
            )
        configured = config[extension.option]
        if configured is None:
            continue
        if not isinstance(configured, str):
            raise ControlPlaneError(
                f"referenced input option is missing or not a path: {extension.option}"
            )
        relative, resolved = _safe_reference(root, configured)
        if resolved in managed:
            raise ControlPlaneError("referenced input aliases a managed output")
        try:
            content = resolved.read_bytes()
        except OSError as exc:
            raise ControlPlaneError("referenced input could not be read") from exc
        inputs.append(
            LockedInput(
                standard_id=standard_id,
                extension_id=extension.id,
                path=relative,
                digest=content_digest(content),
            )
        )
    return tuple(sorted(inputs, key=lambda item: item.natural_key))


@dataclass(frozen=True, slots=True)
class ProviderInvocation:
    """All selected, immutable semantic inputs for one provider call."""

    repo: Path
    payload: InstalledPayload
    standard_id: str
    version: PackageVersion
    provider_id: str
    operation: ProviderOperation
    effective_config: JsonObject
    snapshots: JsonObject


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """One typed provider effect with captured output reduced to a notice."""

    effect: ProviderEffect
    findings: tuple[ControlFinding, ...] = ()
    content: bytes | None = None
    mutation_plan: MutationPlanSchema | None = None
    migration_report: MigrationReport | None = None
    output_notice: str | None = None
    structured_output: JsonObject | None = None


@dataclass(frozen=True, slots=True)
class _PreparedPythonProvider:
    """Hold the exact integrity-checked bytes needed by one Python call."""

    code: bytes
    code_path: Path
    symbol: str
    input_schema: JsonObject
    output_schema: JsonObject
    resources: dict[str, bytes]


@dataclass(frozen=True, slots=True)
class _PreparedCommandProvider:
    """Hold the verified command bytes, schemas, and declared resource closure."""

    executable: bytes
    executable_digest: Sha256Digest
    input_schema: JsonObject
    output_schema: JsonObject
    resources: dict[str, bytes]


class _OutputSink(io.TextIOBase):
    """Discard provider output while remembering only which streams were used."""

    def __init__(self) -> None:
        super().__init__()
        self.used = False

    def write(self, value: str) -> int:
        self.used = self.used or bool(value)
        return len(value)


class _SchemaValidator(Protocol):
    def iter_errors(self, instance: JsonValue) -> Iterator[object]: ...


def _deep_freeze(value: JsonValue) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(child) for child in value)
    return value


def _json_document(content: bytes, *, kind: str) -> JsonObject:
    try:
        parsed = cast(object, json.loads(content.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControlPlaneError(f"provider {kind} is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ControlPlaneError(f"provider {kind} must be a JSON object")
    return cast(JsonObject, parsed)


def _validate_schema_bounds(value: JsonValue) -> None:
    if isinstance(value, list):
        for child in value:
            _validate_schema_bounds(child)
        return
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if key in {"$ref", "$dynamicRef"} and (
            not isinstance(child, str) or not child.startswith("#")
        ):
            raise ControlPlaneError("provider schema reference must remain local")
        _validate_schema_bounds(child)


def _validate_json_schema(schema: JsonObject, value: JsonValue, *, kind: str) -> None:
    _validate_schema_bounds(schema)
    try:
        Draft202012Validator.check_schema(schema)
        validator = cast("_SchemaValidator", Draft202012Validator(schema))
        error = next(validator.iter_errors(value), None)
    except JsonSchemaError as exc:
        raise ControlPlaneError(f"provider {kind} schema is invalid") from exc
    if error is not None:
        raise ControlPlaneError(f"provider {kind} violates its declared schema")


def _resource_map(payload: InstalledPayload) -> dict[str, ResourceDeclaration]:
    return {resource.id: resource for resource in payload.manifest.resources}


def _read_payload_resource(
    payload: InstalledPayload,
    resource: ResourceDeclaration,
) -> bytes:
    inventory = {item.path.original: item.digest for item in payload.integrity.inventory}
    if inventory.get(resource.path.original) != resource.digest:
        raise ControlPlaneError("provider resource is outside verified payload integrity")
    candidate = payload.root / resource.path.normalized
    try:
        if candidate.is_symlink():
            raise ControlPlaneError("provider resource cannot be a symlink")
        resolved = candidate.resolve(strict=True)
        root = payload.root.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ControlPlaneError("provider resource escapes its selected payload")
        content = resolved.read_bytes()
    except OSError as exc:
        raise ControlPlaneError("provider resource could not be read") from exc
    if content_digest(content) != resource.digest:
        raise ControlPlaneError("provider resource changed after integrity validation")
    return content


def _declared_snapshot_paths(snapshots: JsonObject) -> tuple[SafeRelativePath, ...]:
    raw_paths: set[str] = set()
    container_keys = {
        "authoring",
        "documents",
        "legacy_config",
        "legacy_evidence",
        "legacy_signatures",
        "managed_markdown_units",
        "managed_units",
        "planned_contribution",
        "preview",
        "referenced_input_content",
        "referenced_inputs",
    }

    for key, value in snapshots.items():
        if key in container_keys:
            continue
        if not isinstance(value, dict) or "kind" not in value:
            continue
        declared_path = value.get("path")
        if isinstance(declared_path, str):
            raw_paths.add(declared_path)
        else:
            raw_paths.add(key)

    for collection in (
        "documents",
        "referenced_inputs",
        "referenced_input_content",
        "managed_units",
        "managed_markdown_units",
    ):
        raw_items = snapshots.get(collection)
        if not isinstance(raw_items, list):
            continue
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            value = raw_item.get("path", raw_item.get("target"))
            if isinstance(value, str):
                raw_paths.add(value)

    for key in ("authoring", "planned_contribution", "preview"):
        raw_item = snapshots.get(key)
        if isinstance(raw_item, dict):
            value = raw_item.get("target")
            if isinstance(value, str):
                raw_paths.add(value)

    if "legacy_config" in snapshots:
        raw_paths.add(".project-standards.yml")
    raw_signatures = snapshots.get("legacy_signatures")
    if isinstance(raw_signatures, dict):
        for raw_targets in raw_signatures.values():
            if isinstance(raw_targets, dict):
                raw_paths.update(raw_targets)
    legacy_evidence = snapshots.get("legacy_evidence")
    if isinstance(legacy_evidence, dict):
        findings = legacy_evidence.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict):
                    path = finding.get("path")
                    if isinstance(path, str):
                        raw_paths.add(path)

    try:
        return tuple(SafeRelativePath.parse(path) for path in sorted(raw_paths))
    except ValueError as exc:
        raise ControlPlaneError("provider snapshot declares an invalid repository path") from exc


@dataclass(frozen=True, slots=True)
class _ChainedSnapshot:
    """The AFTER snapshot of the most recent provider, offered to the next one."""

    root: Path
    targets: tuple[SafeRelativePath, ...]
    snapshot: RepositorySnapshot


# Chaining state is per thread: two threads planning against one repository see
# each other's writes, and a slot armed by one of them describes a tree the
# other never observed.
_chain_state = threading.local()


def _chain_slot() -> _ChainedSnapshot | None:
    return cast("_ChainedSnapshot | None", getattr(_chain_state, "slot", None))


@contextmanager
def provider_snapshot_chain() -> Generator[None]:
    """Allow consecutive provider invocations to share one integrity snapshot.

    Inside this window, the AFTER snapshot the CP-PROVIDER-INTEGRITY guard takes
    for one provider becomes the BEFORE snapshot of the next provider that
    declares the identical target set, so N invocations cost N+1 captures rather
    than 2N. Every declared path is still read in full once per invocation and
    every AFTER capture is still a fresh read, so a provider that changes a
    declared live path is caught exactly as before.

    The window carries one obligation, and it is the reason chaining is opt-in
    rather than always on: the caller promises that nothing but the providers
    themselves touches a declared path between two invocations. Publication,
    recovery, a spec fix that rewrites the file it just linted, or an operator
    editing the tree between two plans in a long-lived process would otherwise
    be attributed to the next provider as a CP-PROVIDER-INTEGRITY violation.
    Open the window around one planning pass — never around a pass that writes,
    and never across a repository mutation the process performed itself.

    Nested windows are permitted and share the single slot; leaving any window
    discards it, so a chained snapshot never outlives the pass that vouched
    for it — including the outer pass, which resumes with no slot rather than
    with the reading it held before the inner pass ran.
    """
    previous_active = getattr(_chain_state, "active", False)
    _chain_state.active = True
    _chain_state.slot = None
    try:
        yield
    finally:
        _chain_state.active = previous_active
        _chain_state.slot = None


def _arm_snapshot_chain(after: RepositorySnapshot) -> None:
    if getattr(_chain_state, "active", False):
        _chain_state.slot = _ChainedSnapshot(after.root, after.targets, after)


def _capture_declared_paths(
    root: Path,
    targets: tuple[SafeRelativePath, ...],
) -> RepositorySnapshot:
    """Take this invocation's BEFORE snapshot, reusing a chained one when offered."""
    ordered = canonical_targets(targets)
    slot = _chain_slot()
    # Consumed at most once: the reference for the next invocation is whatever
    # this invocation's own AFTER capture observes, never an older reading.
    _chain_state.slot = None
    if slot is not None and slot.root == root and slot.targets == ordered:
        return slot.snapshot
    return RepositorySnapshot.capture(root, ordered, retain_content=False)


def _assert_declared_paths_unchanged(before: RepositorySnapshot) -> None:
    try:
        after = RepositorySnapshot.capture(before.root, before.targets, retain_content=False)
    except ControlPlaneError as exc:
        raise ControlPlaneError(
            "CP-PROVIDER-INTEGRITY: provider made a declared live path unsafe"
        ) from exc
    for expected, observed in zip(before.entries, after.entries, strict=True):
        if expected.precondition_digest != observed.precondition_digest:
            raise ControlPlaneError(
                f"CP-PROVIDER-INTEGRITY: provider changed live path {expected.path.original}"
            )
    # Armed only after the comparison succeeded: a snapshot that already failed
    # the guard must never become the next invocation's reference.
    _arm_snapshot_chain(after)


def _output_notice(stdout: _OutputSink, stderr: _OutputSink) -> str | None:
    streams = [name for name, sink in (("stdout", stdout), ("stderr", stderr)) if sink.used]
    if not streams:
        return None
    return f"provider output suppressed ({', '.join(streams)})"


def _provider_input(
    invocation: ProviderInvocation,
    resource_bytes: Mapping[str, bytes],
) -> ProviderInputSchema:
    return ProviderInputSchema(
        schema_version="1.0",
        standard_id=invocation.standard_id,
        version=invocation.version,
        operation=invocation.operation,
        config=invocation.effective_config,
        resources={name: content_digest(content) for name, content in resource_bytes.items()},
        snapshots=invocation.snapshots,
    )


def _json_result(value: object) -> JsonObject:
    try:
        serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
        parsed = cast(object, json.loads(serialized))
    except (TypeError, ValueError) as exc:
        raise ControlPlaneError("provider returned a non-JSON result") from exc
    if not isinstance(parsed, dict):
        raise ControlPlaneError("provider result must be a JSON object")
    return cast(JsonObject, parsed)


def _typed_result(
    invocation: ProviderInvocation,
    effect: ProviderEffect,
    output: JsonObject,
    notice: str | None,
) -> ProviderResult:
    if effect is ProviderEffect.CONTENT:
        content = output.get("content")
        if not isinstance(content, str):
            raise ControlPlaneError("content provider returned an invalid result")
        return ProviderResult(
            effect,
            content=content.encode(),
            output_notice=notice,
            structured_output=output,
        )
    if effect is ProviderEffect.FINDINGS:
        raw_findings = output.get("findings")
        if not isinstance(raw_findings, list):
            raise ControlPlaneError("findings provider returned an invalid result")
        findings: list[ControlFinding] = []
        for raw in raw_findings:
            if not isinstance(raw, dict):
                raise ControlPlaneError("findings provider returned an invalid finding")
            table = cast(dict[str, JsonValue], raw)
            try:
                code = table["code"]
                severity = table["severity"]
                path = table["path"]
                identity = table["identity"]
                message = table["message"]
                hint = table["hint"]
            except KeyError as exc:
                raise ControlPlaneError("findings provider omitted a required field") from exc
            if not isinstance(code, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            if severity == "error":
                typed_severity: Literal["error", "warning"] = "error"
            elif severity == "warning":
                typed_severity = "warning"
            else:
                raise ControlPlaneError("findings provider returned an invalid finding")
            if not isinstance(path, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            if not isinstance(identity, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            if not isinstance(message, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            if not isinstance(hint, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            measures: dict[str, int | None] = {}
            for field, minimum in (
                ("line", 1),
                ("column", 1),
                ("observed", 0),
                ("limit", 1),
            ):
                raw_value = table.get(field)
                if raw_value is None:
                    measures[field] = None
                elif (
                    isinstance(raw_value, int)
                    and not isinstance(raw_value, bool)
                    and raw_value >= minimum
                ):
                    measures[field] = raw_value
                else:
                    raise ControlPlaneError("findings provider returned an invalid finding")
            locus = table.get("locus")
            if locus is not None and not isinstance(locus, str):
                raise ControlPlaneError("findings provider returned an invalid finding")
            findings.append(
                ControlFinding(
                    code=code,
                    severity=typed_severity,
                    standard_id=invocation.standard_id,
                    version=invocation.version.value,
                    path=path,
                    identity=identity,
                    message=message,
                    hint=hint,
                    line=measures["line"],
                    column=measures["column"],
                    locus=locus,
                    observed=measures["observed"],
                    limit=measures["limit"],
                )
            )
        return ProviderResult(
            effect,
            findings=tuple(findings),
            output_notice=notice,
            structured_output=output,
        )
    if effect is ProviderEffect.MUTATION_PLAN:
        try:
            plan = MutationPlanSchema.model_validate(output)
        except ValidationError as exc:
            raise ControlPlaneError("mutation provider returned an invalid plan") from exc
        if plan.standard_id != invocation.standard_id or plan.version != invocation.version:
            raise ControlPlaneError("mutation plan identity does not match selected payload")
        if invocation.operation is ProviderOperation.FIX:
            _bind_fix_actions_to_snapshots(invocation, plan)
        elif invocation.operation in {ProviderOperation.SCAFFOLD, ProviderOperation.UPGRADE}:
            _bind_authoring_actions_to_snapshot(invocation, plan)
        return ProviderResult(
            effect,
            mutation_plan=plan,
            output_notice=notice,
            structured_output=output,
        )
    if effect is ProviderEffect.MIGRATION_REPORT:
        try:
            report = MigrationReport.model_validate(output)
        except ValidationError as exc:
            raise ControlPlaneError("migration provider returned an invalid report") from exc
        if (
            report.package.standard_id != invocation.standard_id
            or report.package.version != invocation.version
        ):
            raise ControlPlaneError("migration report identity does not match selected payload")
        declared_signatures = {
            signature
            for migration in invocation.payload.manifest.migrations
            if migration.provider == invocation.provider_id
            for signature in migration.signatures
        }
        if any(claim.signature_id not in declared_signatures for claim in report.claims):
            raise ControlPlaneError("migration provider claimed an undeclared legacy signature")
        return ProviderResult(
            effect,
            migration_report=report,
            output_notice=notice,
            structured_output=output,
        )
    raise ControlPlaneError("provider declared an unsupported effect")


def _bind_fix_actions_to_snapshots(
    invocation: ProviderInvocation,
    plan: MutationPlanSchema,
) -> None:
    """Reject FIX actions that are not exact whole-file transitions over snapshots."""
    raw_documents = invocation.snapshots.get("documents")
    if not isinstance(raw_documents, list):
        if plan.actions:
            raise ControlPlaneError("FIX mutation plan requires immutable document snapshots")
        return
    documents: dict[str, tuple[str, Sha256Digest]] = {}
    for raw in raw_documents:
        if not isinstance(raw, dict):
            raise ControlPlaneError("FIX document snapshot is invalid")
        document = cast(dict[str, JsonValue], raw)
        path = document.get("path")
        kind = document.get("kind")
        digest = document.get("precondition_digest")
        if not isinstance(path, str) or not isinstance(kind, str) or not isinstance(digest, str):
            raise ControlPlaneError("FIX document snapshot is invalid")
        try:
            normalized = SafeRelativePath.parse(path).original
            precondition = Sha256Digest(digest)
        except ValueError as exc:
            raise ControlPlaneError("FIX document snapshot is invalid") from exc
        if normalized in documents:
            raise ControlPlaneError("FIX document snapshots contain a duplicate target")
        documents[normalized] = (kind, precondition)

    targets: set[str] = set()
    for action in plan.actions:
        target = action.target.original
        if target in targets:
            raise ControlPlaneError("FIX mutation plan contains a duplicate target")
        targets.add(target)
        snapshot = documents.get(target)
        if snapshot is None:
            raise ControlPlaneError("FIX mutation plan contains an undeclared target")
        if action.adapter is not AdapterKind.WHOLE_FILE or action.scope != "$file":
            raise ControlPlaneError("FIX mutation actions must use whole-file scope and adapter")
        if action.kind is ActionKind.REMOVE:
            raise ControlPlaneError("FIX mutation plan cannot request document removal")
        kind, precondition = snapshot
        if action.precondition_digest != precondition:
            raise ControlPlaneError("FIX mutation action precondition does not match its snapshot")
        expected = (
            ActionKind.UPDATE
            if kind == "regular"
            else ActionKind.CREATE
            if kind == "missing"
            else None
        )
        if expected is None or action.kind is not expected:
            raise ControlPlaneError("FIX mutation action kind does not match its document snapshot")


def _bind_authoring_actions_to_snapshot(
    invocation: ProviderInvocation,
    plan: MutationPlanSchema,
) -> None:
    """Bind scaffold/upgrade output to one caller-authorized target snapshot."""
    raw_authoring = invocation.snapshots.get("authoring")
    if not isinstance(raw_authoring, dict):
        raise ControlPlaneError("authoring provider requires one immutable target snapshot")
    authoring = cast(dict[str, JsonValue], raw_authoring)
    target = authoring.get("target")
    kind = authoring.get("kind")
    digest = authoring.get("precondition_digest")
    mode = authoring.get("mode")
    overwrite = authoring.get("overwrite")
    if (
        not isinstance(target, str)
        or not isinstance(kind, str)
        or not isinstance(digest, str)
        or not (isinstance(mode, str) or mode is None)
        or not isinstance(overwrite, bool)
    ):
        raise ControlPlaneError("authoring target snapshot is invalid")
    try:
        normalized_target = SafeRelativePath.parse(target)
        precondition = Sha256Digest(digest)
    except ValueError as exc:
        raise ControlPlaneError("authoring target snapshot is invalid") from exc
    if len(plan.actions) != 1:
        raise ControlPlaneError("authoring provider must return exactly one target action")
    action = plan.actions[0]
    if (
        action.target != normalized_target
        or action.adapter is not AdapterKind.WHOLE_FILE
        or action.scope != "$file"
        or action.precondition_digest != precondition
    ):
        raise ControlPlaneError("authoring mutation does not match its target snapshot")
    if action.mode != mode:
        raise ControlPlaneError("authoring mutation mode exceeds its target authorization")
    expected = (
        ActionKind.CREATE if kind == "missing" else ActionKind.UPDATE if kind == "regular" else None
    )
    if expected is None or action.kind is not expected:
        raise ControlPlaneError("authoring mutation kind does not match its target snapshot")
    if expected is ActionKind.UPDATE and not overwrite:
        raise ControlPlaneError("authoring mutation exceeds its overwrite authorization")


def _qualified_provider(
    invocation: ProviderInvocation,
) -> tuple[Path, InstalledPayload, ProviderDeclaration]:
    """Qualify one direct invocation before it is allowed to spawn a child."""
    root = _safe_repo(invocation.repo)
    payload = invocation.payload
    identity = payload.manifest.payload
    if (
        identity.standard != invocation.standard_id
        or identity.version != invocation.version
        or identity.availability is not PayloadAvailability.CONSUMER
    ):
        raise ControlPlaneError("provider payload does not match the selected package")
    matches = [item for item in payload.manifest.providers if item.id == invocation.provider_id]
    if len(matches) != 1:
        raise ControlPlaneError("selected payload does not declare exactly one provider")
    provider = matches[0]
    if provider.operation is not invocation.operation:
        raise ControlPlaneError("provider operation does not match the requested operation")
    if provider.kind not in {ProviderKind.PYTHON, ProviderKind.COMMAND}:
        raise ControlPlaneError("provider kind is not executable by the bounded runner")
    return root, payload, provider


def _qualified_python_provider(
    invocation: ProviderInvocation,
) -> tuple[Path, InstalledPayload, ProviderDeclaration]:
    """Qualify the Python-only in-child execution path."""
    root, payload, provider = _qualified_provider(invocation)
    if provider.kind is not ProviderKind.PYTHON:
        raise ControlPlaneError("provider kind is not executable in the Python worker")
    return root, payload, provider


def _prepare_python_provider(
    payload: InstalledPayload,
    provider: ProviderDeclaration,
) -> _PreparedPythonProvider:
    """Load the provider's complete integrity-checked execution closure."""
    resources = _resource_map(payload)
    required_ids = {
        provider.entrypoint_resource,
        provider.input_schema,
        provider.output_schema,
        *provider.resources,
    }
    if None in required_ids or not cast(set[str], required_ids).issubset(resources):
        raise ControlPlaneError("provider references an undeclared payload resource")
    selected_resources = cast(set[str], required_ids)
    loaded = {
        resource_id: _read_payload_resource(payload, resources[resource_id])
        for resource_id in sorted(selected_resources)
    }
    entrypoint_id = cast(str, provider.entrypoint_resource)
    input_schema_id = cast(str, provider.input_schema)
    output_schema_id = cast(str, provider.output_schema)
    code_resource = resources[entrypoint_id]
    return _PreparedPythonProvider(
        code=loaded[entrypoint_id],
        code_path=payload.root / code_resource.path.normalized,
        symbol=cast(str, provider.entrypoint).rsplit("#", 1)[1],
        input_schema=_json_document(loaded[input_schema_id], kind="input schema"),
        output_schema=_json_document(loaded[output_schema_id], kind="output schema"),
        resources={resource_id: loaded[resource_id] for resource_id in provider.resources},
    )


def _prepare_command_provider(
    payload: InstalledPayload,
    provider: ProviderDeclaration,
) -> _PreparedCommandProvider:
    """Load a command's complete integrity-checked execution closure."""
    resources = _resource_map(payload)
    required_ids = {
        provider.entrypoint_resource,
        provider.input_schema,
        provider.output_schema,
        *provider.resources,
    }
    if None in required_ids or not cast(set[str], required_ids).issubset(resources):
        raise ControlPlaneError("provider references an undeclared payload resource")
    selected_resources = cast(set[str], required_ids)
    loaded = {
        resource_id: _read_payload_resource(payload, resources[resource_id])
        for resource_id in sorted(selected_resources)
    }
    entrypoint_id = cast(str, provider.entrypoint_resource)
    input_schema_id = cast(str, provider.input_schema)
    output_schema_id = cast(str, provider.output_schema)
    return _PreparedCommandProvider(
        executable=loaded[entrypoint_id],
        executable_digest=resources[entrypoint_id].digest,
        input_schema=_json_document(loaded[input_schema_id], kind="input schema"),
        output_schema=_json_document(loaded[output_schema_id], kind="output schema"),
        resources={resource_id: loaded[resource_id] for resource_id in provider.resources},
    )


def _host_command_platform() -> str:
    """Return the closed command ABI platform identifier for this host."""
    machine = platform.machine().lower()
    if sys.platform == "linux" and machine in {"amd64", "x86_64"}:
        return "linux/amd64"
    return "unsupported"


def _run_bounded_provider(
    argv: Sequence[str],
    request: bytes,
    *,
    environment: Mapping[str, str],
    validate_status: bool = True,
) -> ProviderSubprocessOutcome:
    """Keep every direct provider kind on the sole shared transport call site."""
    return run_provider_subprocess(
        argv,
        request,
        timeout=float(PROVIDER_TIMEOUT_SECONDS),
        environment=environment,
        validate_status=validate_status,
    )


def _invoke_command_provider(
    root: Path,
    payload: InstalledPayload,
    provider: ProviderDeclaration,
    invocation: ProviderInvocation,
) -> ProviderResult:
    """Materialize and invoke one integrity-addressed native command."""
    if _host_command_platform() != "linux/amd64":
        raise ControlPlaneError("unsupported command provider platform")
    prepared = _prepare_command_provider(payload, provider)
    effective_invocation = replace(
        invocation,
        repo=root,
        snapshots=materialize_referenced_input_snapshots(
            root,
            invocation.snapshots,
            standard_id=invocation.standard_id,
            config=invocation.effective_config,
            extensions=payload.manifest.extensions,
        ),
    )
    before = _capture_declared_paths(
        root,
        _declared_snapshot_paths(effective_invocation.snapshots),
    )
    provider_input = _provider_input(effective_invocation, prepared.resources)
    input_value = cast(JsonValue, provider_input.model_dump(mode="json"))
    _validate_json_schema(prepared.input_schema, input_value, kind="input")
    request = encode_provider_request(
        cast(
            JsonObject,
            {
                "schema_version": "1.0",
                "input": input_value,
                "resources": {
                    resource_id: base64.b64encode(content).decode("ascii")
                    for resource_id, content in sorted(prepared.resources.items())
                },
            },
        )
    )
    outcome = None
    failure: ControlPlaneError | None = None
    cause: BaseException | None = None
    with tempfile.TemporaryDirectory(prefix="project-standards-provider-") as private:
        executable = Path(private) / "provider"
        try:
            executable.write_bytes(prepared.executable)
            executable.chmod(0o755)
            metadata = executable.stat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != 0o755
                or content_digest(executable.read_bytes()) != prepared.executable_digest
            ):
                raise ControlPlaneError("materialized command provider failed verification")
            outcome = _run_bounded_provider(
                (str(executable),),
                request,
                environment={},
                validate_status=False,
            )
        except OSError as exc:
            failure = ControlPlaneError("command provider could not be materialized")
            cause = exc
        except ProviderSubprocessError as exc:
            failure = ControlPlaneError(exc.message)
            cause = exc
    try:
        _assert_declared_paths_unchanged(before)
    except ControlPlaneError as exc:
        raise exc from (cause or failure)
    if failure is not None:
        raise failure from cause
    assert outcome is not None
    output = _json_result(outcome.frame)
    _validate_json_schema(prepared.output_schema, cast(JsonValue, output), kind="output")
    diagnostics = compose_provider_diagnostics(None, outcome.stdout, outcome.stderr)
    notice = (
        safe_failure_detail(
            diagnostics,
            (str(root), str(payload.root)),
        )
        if diagnostics
        else None
    )
    return _typed_result(
        effective_invocation,
        provider.effect,
        output,
        notice,
    )


def invoke_provider_in_child(invocation: ProviderInvocation) -> ProviderResult:
    """Execute Python bytes in this process; only the child worker may call this."""
    root, payload, provider = _qualified_python_provider(invocation)
    prepared = _prepare_python_provider(payload, provider)
    effective_invocation = replace(
        invocation,
        snapshots=materialize_referenced_input_snapshots(
            root,
            invocation.snapshots,
            standard_id=invocation.standard_id,
            config=invocation.effective_config,
            extensions=payload.manifest.extensions,
        ),
    )
    provider_input = _provider_input(effective_invocation, prepared.resources)
    input_value = cast(JsonValue, provider_input.model_dump(mode="json"))
    _validate_json_schema(prepared.input_schema, input_value, kind="input")
    frozen_input = _deep_freeze(input_value)
    frozen_resources = MappingProxyType(prepared.resources)
    before = _capture_declared_paths(
        root,
        _declared_snapshot_paths(effective_invocation.snapshots),
    )
    stdout = _OutputSink()
    stderr = _OutputSink()
    result: object | None = None
    failure: BaseException | None = None
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Execute the bytes already checked against the payload inventory;
            # reopening the path through an importer would create a verification-to-use race.
            code = compile(
                prepared.code,
                str(prepared.code_path),
                "exec",
            )
            namespace: dict[str, object] = {
                "__file__": str(prepared.code_path),
                "__name__": "__project_standards_provider__",
            }
            exec(code, namespace)
            callable_provider = namespace.get(prepared.symbol)
            if not callable(callable_provider):
                raise TypeError("entrypoint symbol is not callable")
            result = callable_provider(frozen_input, frozen_resources)
    except BaseException as exc:
        failure = exc
    try:
        _assert_declared_paths_unchanged(before)
    except ControlPlaneError as exc:
        raise exc from failure
    if failure is not None:
        coordinate = f"{invocation.standard_id}@{invocation.version.value}/{invocation.provider_id}"
        raise ControlPlaneError(
            f"provider failed with {type(failure).__name__} ({coordinate})"
        ) from failure

    output = _json_result(result)
    _validate_json_schema(prepared.output_schema, cast(JsonValue, output), kind="output")
    return _typed_result(
        invocation,
        provider.effect,
        output,
        _output_notice(stdout, stderr),
    )


def invoke_provider(invocation: ProviderInvocation) -> ProviderResult:
    """Invoke one V2 executable provider through the shared bounded process."""
    root, payload, provider = _qualified_provider(invocation)
    if provider.kind is ProviderKind.COMMAND:
        return _invoke_command_provider(root, payload, provider, invocation)
    prepared = _prepare_python_provider(payload, provider)
    effective_invocation = replace(
        invocation,
        repo=root,
        snapshots=materialize_referenced_input_snapshots(
            root,
            invocation.snapshots,
            standard_id=invocation.standard_id,
            config=invocation.effective_config,
            extensions=payload.manifest.extensions,
        ),
    )
    before = _capture_declared_paths(
        root,
        _declared_snapshot_paths(effective_invocation.snapshots),
    )
    provider_input = _provider_input(effective_invocation, prepared.resources)
    input_value = cast(JsonValue, provider_input.model_dump(mode="json"))
    _validate_json_schema(prepared.input_schema, input_value, kind="input")
    request = encode_provider_request(
        cast(
            JsonObject,
            {
                "dispatch_mode": "direct",
                "repo_root": str(root),
                "payload_root": str(payload.root),
                # The child receives bytes already coupled to the qualified
                # InstalledPayload. Reloading payload.toml here would discard
                # legitimate in-memory qualification seams and reopen a second
                # manifest authority after the parent has checked every byte.
                "capsule": {
                    "standard_id": invocation.standard_id,
                    "version": invocation.version.value,
                    "provider_id": invocation.provider_id,
                    "operation": invocation.operation.value,
                    "effect": provider.effect.value,
                    "symbol": prepared.symbol,
                    "source_path": str(prepared.code_path),
                    "code_base64": base64.b64encode(prepared.code).decode("ascii"),
                    "input": input_value,
                    "resources": {
                        resource_id: base64.b64encode(content).decode("ascii")
                        for resource_id, content in sorted(prepared.resources.items())
                    },
                },
            },
        )
    )
    outcome = None
    failure: ControlPlaneError | None = None
    cause: BaseException | None = None
    try:
        outcome = _run_bounded_provider(
            python_worker_argv(),
            request,
            environment=python_worker_environment(),
        )
    except ProviderSubprocessError as exc:
        failure = ControlPlaneError(exc.message)
        cause = exc
    if outcome is not None and outcome.frame.get("status") != "ok":
        if outcome.frame.get("code") == "provider-result-too-large":
            failure = ControlPlaneError(
                "the bounded provider worker returned a result above the transport limit"
            )
            cause = RuntimeError("provider result exceeded the transport limit")
        else:
            raw_kind = outcome.frame.get("kind")
            raw_detail = outcome.frame.get("detail")
            kind = raw_kind if isinstance(raw_kind, str) else ""
            detail = safe_failure_detail(
                raw_detail if isinstance(raw_detail, str) else "",
                (str(root), str(payload.root)),
            )
            exception_type = _SAFE_PROVIDER_CAUSE_TYPES.get(kind)
            if exception_type is None:
                label = "an unrecognized exception"
                cause = RuntimeError(_UNKNOWN_PROVIDER_CAUSE)
            else:
                label = kind
                cause = exception_type(detail)
            coordinate = (
                f"{invocation.standard_id}@{invocation.version.value}/{invocation.provider_id}"
            )
            failure = ControlPlaneError(f"provider failed with {label} ({coordinate})")
    try:
        _assert_declared_paths_unchanged(before)
    except ControlPlaneError as exc:
        raise exc from (cause or failure)
    if failure is not None:
        raise failure from cause
    assert outcome is not None

    response_effect = outcome.frame.get("effect")
    if response_effect != provider.effect.value:
        raise ControlPlaneError("provider worker returned an invalid effect")
    output = _json_result(outcome.frame.get("output"))
    _validate_json_schema(prepared.output_schema, cast(JsonValue, output), kind="output")
    raw_notice = outcome.frame.get("output_notice")
    if raw_notice is not None and not isinstance(raw_notice, str):
        raise ControlPlaneError("provider worker returned an invalid output notice")
    return _typed_result(
        effective_invocation,
        provider.effect,
        output,
        raw_notice,
    )
