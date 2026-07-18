"""Contained referenced inputs and the version-selected provider runner."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import stat
from collections.abc import Iterator, Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from pydantic import ValidationError

from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlFinding,
    ControlPlaneError,
)
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.migration import MigrationReport
from project_standards.control_plane.models import LockedInput
from project_standards.control_plane.schemas import MutationPlanSchema, ProviderInputSchema
from project_standards.control_plane.snapshot import RepositorySnapshot
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
    ProviderEffect,
    ProviderKind,
    ProviderOperation,
    ResourceDeclaration,
)


def _sha256(content: bytes) -> Sha256Digest:
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


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
    if _sha256(content) != locked.digest:
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
                digest=_sha256(content),
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
    if _sha256(content) != resource.digest:
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


def _assert_declared_paths_unchanged(before: RepositorySnapshot) -> None:
    try:
        after = RepositorySnapshot.capture(before.root, before.targets)
    except ControlPlaneError as exc:
        raise ControlPlaneError(
            "CP-PROVIDER-INTEGRITY: provider made a declared live path unsafe"
        ) from exc
    for expected, observed in zip(before.entries, after.entries, strict=True):
        if expected.precondition_digest != observed.precondition_digest:
            raise ControlPlaneError(
                f"CP-PROVIDER-INTEGRITY: provider changed live path {expected.path.original}"
            )


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
        resources={name: _sha256(content) for name, content in resource_bytes.items()},
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
                findings.append(
                    ControlFinding(
                        code=cast(str, table["code"]),
                        severity=cast("Literal['error', 'warning']", table["severity"]),
                        standard_id=invocation.standard_id,
                        version=invocation.version.value,
                        path=cast(str, table["path"]),
                        identity=cast(str, table["identity"]),
                        message=cast(str, table["message"]),
                        hint=cast(str, table["hint"]),
                        line=cast(int | None, table.get("line")),
                        locus=cast(str | None, table.get("locus")),
                    )
                )
            except KeyError as exc:
                raise ControlPlaneError("findings provider omitted a required field") from exc
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


def invoke_provider(invocation: ProviderInvocation) -> ProviderResult:
    """Invoke one declared Python provider and reject changes to declared live targets."""
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
    if provider.kind is not ProviderKind.PYTHON or provider.entrypoint is None:
        raise ControlPlaneError("provider kind is not executable by the bounded runner")

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
    input_schema = _json_document(
        loaded[cast(str, provider.input_schema)],
        kind="input schema",
    )
    output_schema = _json_document(
        loaded[cast(str, provider.output_schema)],
        kind="output schema",
    )
    provider_resource_bytes = {
        resource_id: loaded[resource_id] for resource_id in provider.resources
    }
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
    provider_input = _provider_input(effective_invocation, provider_resource_bytes)
    input_value = cast(JsonValue, provider_input.model_dump(mode="json"))
    _validate_json_schema(input_schema, input_value, kind="input")
    frozen_input = _deep_freeze(input_value)
    frozen_resources = MappingProxyType(provider_resource_bytes)

    code_resource = resources[cast(str, provider.entrypoint_resource)]
    code_path = payload.root / code_resource.path.normalized
    symbol = provider.entrypoint.rsplit("#", 1)[1]
    before = RepositorySnapshot.capture(
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
                loaded[cast(str, provider.entrypoint_resource)],
                str(code_path),
                "exec",
            )
            namespace: dict[str, object] = {
                "__file__": str(code_path),
                "__name__": "__project_standards_provider__",
            }
            exec(code, namespace)
            callable_provider = namespace.get(symbol)
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
        raise ControlPlaneError(f"provider failed with {type(failure).__name__}") from failure

    output = _json_result(result)
    _validate_json_schema(output_schema, cast(JsonValue, output), kind="output")
    return _typed_result(
        invocation,
        provider.effect,
        output,
        _output_notice(stdout, stderr),
    )
