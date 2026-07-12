"""Typed, content-safe reports returned by legacy-migration providers."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import stat
import tomllib
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import yaml
from pydantic import ConfigDict, Field, ValidationError, field_validator, model_validator
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, AnchorToken

from project_standards.control_plane.codec import (
    parse_lock,
    render_catalog,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.diagnostics import (
    ActionKind,
    ControlAction,
    ControlFinding,
    ControlPlaneError,
    actions_to_jsonable,
    findings_to_jsonable,
    sort_actions,
    sort_findings,
    validation_summary,
)
from project_standards.control_plane.distribution import (
    InstalledCatalog,
    InstalledDistribution,
    InstalledPayload,
)
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    DesiredPackage,
    LockedUnit,
    UnitProvenance,
    VersionSelector,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.resolution import (
    DeclaredTransition,
    ResolutionPayload,
    ResolutionRequest,
)
from project_standards.control_plane.state import StateKind, detect_control_plane_state
from project_standards.package_contract.catalog import CatalogRole
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import KebabId, StrictModel
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    validate_json_pointer,
)
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonObject,
    JsonValue,
    LegacySignatureDeclaration,
    LegacySignatureFormat,
    LegacySignatureKind,
    MigrationMode,
    ProviderOperation,
    load_option_schema,
)

if TYPE_CHECKING:
    from project_standards.control_plane.executor import (
        ApplyResult,
        FaultHook,
        VerificationRunner,
    )
    from project_standards.control_plane.planner import PlannerRequest, ReconciliationPlan

type LegacyOwnership = Literal[
    "managed",
    "create-only",
    "shared",
    "consumer-owned",
    "package-lock",
]

_BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$", re.ASCII)
_MISSING = object()


class LegacyDisposition(StrEnum):
    """Proposed treatment of one exactly recognized legacy object."""

    ADOPT = "adopt"
    PRESERVE = "preserve"
    REMOVE = "remove"
    IMPORT_LOCK = "import-lock"


class MigratedPackage(StrictModel):
    """Validated desired-state contribution produced for one selected payload."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    standard_id: KebabId
    version: PackageVersion
    selector: VersionSelector
    config: dict[str, JsonValue] = Field(default_factory=dict)
    recognized_settings: tuple[str, ...] = ()

    @field_validator("config")
    @classmethod
    def _safe_config(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        try:
            validated = DesiredPackage(enabled=True, version="latest", config=value)
        except ValidationError as exc:
            raise ValueError(
                f"migrated package config is invalid: {validation_summary(exc)}"
            ) from exc
        return validated.config

    @field_validator("recognized_settings")
    @classmethod
    def _canonical_settings(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        validated = [validate_json_pointer(item) for item in value]
        if len(validated) != len(set(validated)):
            raise ValueError("recognized setting paths must be unique")
        return tuple(sorted(validated))

    @model_validator(mode="after")
    def _selector_matches_resolved_version(self) -> MigratedPackage:
        if isinstance(self.selector, PackageVersion) and self.selector != self.version:
            raise ValueError("exact migration selector must match the resolved payload version")
        return self


class LegacyClaim(StrictModel):
    """Identify one legacy signature match without retaining its source bytes."""

    signature_id: KebabId
    target: SafeRelativePath
    observed_digest: Sha256Digest
    ownership: LegacyOwnership
    disposition: LegacyDisposition
    intent_pointer: str | None = None

    @field_validator("intent_pointer")
    @classmethod
    def _canonical_intent_pointer(cls, value: str | None) -> str | None:
        return None if value is None else validate_json_pointer(value)

    @model_validator(mode="after")
    def _safe_disposition(self) -> LegacyClaim:
        allowed: dict[LegacyOwnership, frozenset[LegacyDisposition]] = {
            "managed": frozenset(
                {
                    LegacyDisposition.ADOPT,
                    LegacyDisposition.PRESERVE,
                    LegacyDisposition.REMOVE,
                }
            ),
            "create-only": frozenset({LegacyDisposition.PRESERVE}),
            "shared": frozenset({LegacyDisposition.ADOPT, LegacyDisposition.PRESERVE}),
            "consumer-owned": frozenset({LegacyDisposition.PRESERVE}),
            "package-lock": frozenset({LegacyDisposition.IMPORT_LOCK}),
        }
        if self.disposition not in allowed[self.ownership]:
            raise ValueError("legacy claim disposition is not valid for its ownership class")
        return self


class MigrationFinding(StrictModel):
    """Content-free warning or error about one recognized migration identity."""

    code: str = Field(pattern=r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
    severity: Literal["error", "warning"]
    path: SafeRelativePath
    identity: KebabId


def _claim_sort_key(claim: LegacyClaim) -> tuple[str, ...]:
    return (
        claim.signature_id,
        claim.target.original,
        claim.observed_digest.value,
        claim.ownership,
        claim.disposition.value,
        claim.intent_pointer or "",
    )


def _finding_sort_key(finding: MigrationFinding) -> tuple[str, ...]:
    return (
        finding.identity,
        finding.path.original,
        finding.code,
        finding.severity,
    )


class MigrationReport(StrictModel):
    """One deterministic, schema-valid result from a selected migrate provider."""

    schema_version: Literal["1.0"]
    package: MigratedPackage
    claims: tuple[LegacyClaim, ...] = ()
    findings: tuple[MigrationFinding, ...] = ()

    @model_validator(mode="after")
    def _normalize_entries(self) -> MigrationReport:
        identities = [(claim.signature_id, claim.target.original) for claim in self.claims]
        if len(identities) != len(set(identities)):
            raise ValueError("migration report contains a duplicate legacy claim")
        object.__setattr__(self, "claims", tuple(sorted(self.claims, key=_claim_sort_key)))
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=_finding_sort_key)),
        )
        return self


def _claim_to_jsonable(claim: LegacyClaim) -> dict[str, object]:
    result: dict[str, object] = {
        "signature_id": claim.signature_id,
        "target": claim.target.original,
        "observed_digest": claim.observed_digest.value,
        "ownership": claim.ownership,
        "disposition": claim.disposition.value,
    }
    if claim.intent_pointer is not None:
        result["intent_pointer"] = claim.intent_pointer
    return result


def migration_report_to_jsonable(report: MigrationReport) -> dict[str, object]:
    """Return stable public fields while withholding migrated option values."""
    selector = report.package.selector
    selector_value = selector.value if isinstance(selector, PackageVersion) else selector
    return {
        "schema_version": report.schema_version,
        "package": {
            "standard_id": report.package.standard_id,
            "version": report.package.version.value,
            "selector": selector_value,
            "recognized_settings": list(report.package.recognized_settings),
        },
        "claims": [_claim_to_jsonable(claim) for claim in report.claims],
        "findings": [
            {
                "code": finding.code,
                "severity": finding.severity,
                "path": finding.path.original,
                "identity": finding.identity,
            }
            for finding in report.findings
        ],
    }


def render_migration_report(report: MigrationReport) -> str:
    """Render deterministic human evidence without option or source values."""
    selector = report.package.selector
    selector_value = selector.value if isinstance(selector, PackageVersion) else selector
    lines = [
        f"package {report.package.standard_id}@{report.package.version.value} ({selector_value})",
    ]
    lines.extend(f"setting {path}" for path in report.package.recognized_settings)
    for claim in report.claims:
        line = (
            "claim "
            f"{claim.signature_id} {claim.target.original} {claim.observed_digest.value} "
            f"{claim.ownership} {claim.disposition.value}"
            + (f" {claim.intent_pointer}" if claim.intent_pointer is not None else "")
        )
        if (
            claim.ownership == "consumer-owned"
            and claim.disposition is LegacyDisposition.PRESERVE
            and claim.intent_pointer is not None
        ):
            line += "; consumer-owned preserved; not semantically validated by the package"
        lines.append(line)
    lines.extend(
        f"finding {finding.severity} {finding.code} {finding.path.original} {finding.identity}"
        for finding in report.findings
    )
    return "\n".join(lines) + "\n"


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = cast(
            object,
            loader.construct_object(key_node, deep=deep),  # pyright: ignore[reportUnknownMemberType]
        )
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "mapping key is not hashable",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "duplicate key",
                key_node.start_mark,
            )
        mapping[key] = cast(
            object,
            loader.construct_object(  # pyright: ignore[reportUnknownMemberType]
                value_node,
                deep=deep,
            ),
        )
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True, slots=True)
class _ObservedSignature:
    standard_id: str
    signature_id: str
    target: SafeRelativePath
    digest: Sha256Digest
    known: bool
    content: bytes = field(repr=False, compare=False)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.standard_id, self.signature_id, self.target.original)


@dataclass(frozen=True, slots=True)
class LegacyMigrationPlan:
    """Complete read-only proposal for replacing one legacy authority tree."""

    repo: Path
    applicable: bool
    reports: tuple[MigrationReport, ...]
    findings: tuple[ControlFinding, ...]
    desired_config: DesiredConfig
    catalog: ConsumerCatalog
    distribution: InstalledDistribution = field(repr=False, compare=False)
    planner: PlannerRequest = field(repr=False, compare=False)
    reconciliation: ReconciliationPlan
    reconciliation_fingerprint: str
    content_fingerprint: str
    legacy_removals: tuple[ControlAction, ...]
    legacy_preconditions: tuple[tuple[str, Sha256Digest], ...]
    config_content: bytes = field(repr=False)
    catalog_content: bytes = field(repr=False)
    lock_content: bytes = field(repr=False)

    @property
    def actions(self) -> tuple[ControlAction, ...]:
        """Return artifact and legacy-authority actions in stable public order."""
        return tuple(sort_actions((*self.reconciliation.actions, *self.legacy_removals)))

    def to_jsonable(self) -> dict[str, JsonValue]:
        """Return deterministic public evidence without legacy or proposed content bytes."""
        return {
            "applicable": self.applicable,
            "reports": cast(
                JsonValue,
                [migration_report_to_jsonable(report) for report in self.reports],
            ),
            "findings": cast(JsonValue, findings_to_jsonable(self.findings)),
            "actions": cast(JsonValue, actions_to_jsonable(self.actions)),
            "config_digest": _digest(self.config_content).value,
            "catalog_digest": self.catalog.project_standards.digest.value,
            "lock_digest": _digest(self.lock_content).value,
        }


def apply_legacy_migration(
    plan: LegacyMigrationPlan,
    *,
    fault_hook: FaultHook | None = None,
    verification_runner: VerificationRunner | None = None,
) -> ApplyResult:
    """Apply one reviewed legacy migration through the sole repository writer."""
    from project_standards.control_plane.executor import apply_legacy_migration as apply

    return apply(
        plan,
        fault_hook=fault_hook,
        verification_runner=verification_runner,
    )


def _digest(content: bytes) -> Sha256Digest:
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


def legacy_migration_content_fingerprint(
    repo: Path,
    reconciliation_fingerprint: str,
    legacy_preconditions: tuple[tuple[str, Sha256Digest], ...],
    config_content: bytes,
    catalog_content: bytes,
    lock_content: bytes,
) -> str:
    """Bind one preview's repository, lineage, preconditions, and private output bytes."""
    digest = hashlib.sha256()
    values = (
        str(repo).encode(),
        reconciliation_fingerprint.encode("ascii"),
        json.dumps(
            [(path, observed.value) for path, observed in legacy_preconditions],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode(),
        config_content,
        catalog_content,
        lock_content,
    )
    for value in values:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _safe_repo(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ControlPlaneError("migration repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ControlPlaneError("migration repository root could not be resolved") from exc


def _read_regular_file(path: Path, *, kind: str) -> bytes:
    if path.is_symlink():
        raise ControlPlaneError(f"{kind} cannot be a symlink")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ControlPlaneError(f"{kind} could not be opened safely") from exc
    chunks: list[bytes] = []
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ControlPlaneError(f"{kind} must be a regular file")
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise ControlPlaneError(f"{kind} could not be read safely") from exc
    finally:
        os.close(descriptor)
    stable = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
    if any(getattr(before, name) != getattr(after, name) for name in stable):
        raise ControlPlaneError(f"{kind} changed while it was being read")
    return b"".join(chunks)


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ControlPlaneError("legacy YAML contains a non-finite number")
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        result: JsonObject = {}
        for key, item in cast("dict[object, object]", value).items():
            if not isinstance(key, str):
                raise ControlPlaneError("legacy YAML contains a non-string mapping key")
            if not key or unicodedata.normalize("NFC", key) != key:
                raise ControlPlaneError("legacy YAML contains a noncanonical mapping key")
            result[key] = _json_value(item)
        return result
    raise ControlPlaneError("legacy YAML contains a non-JSON value")


def _load_legacy_yaml(content: bytes) -> JsonObject:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("legacy config is not valid UTF-8") from exc
    try:
        scanned = cast(
            "Iterable[object]",
            yaml.scan(  # pyright: ignore[reportUnknownMemberType]
                text,
                Loader=_UniqueKeyLoader,
            ),
        )
        tokens = tuple(scanned)
    except yaml.YAMLError as exc:
        raise ControlPlaneError("legacy config is not valid YAML") from exc
    if any(isinstance(token, AnchorToken | AliasToken) for token in tokens):
        raise ControlPlaneError("legacy config cannot contain YAML anchors or aliases")
    try:
        parsed = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.constructor.ConstructorError as exc:
        if "duplicate key" in str(exc):
            raise ControlPlaneError("legacy config contains a duplicate key") from exc
        raise ControlPlaneError("legacy config is not valid YAML") from exc
    except yaml.YAMLError as exc:
        raise ControlPlaneError("legacy config is not valid YAML") from exc
    value = _json_value(parsed)
    if not isinstance(value, dict):
        raise ControlPlaneError("legacy config root must be a mapping")
    return value


def _finding(
    code: str,
    *,
    path: str,
    identity: str,
    standard_id: str = "project-standards",
    version: str = "",
    message: str,
    hint: str,
) -> ControlFinding:
    return ControlFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=path,
        identity=identity,
        message=message,
        hint=hint,
    )


def _bounded_block(
    content: bytes,
    signature: LegacySignatureDeclaration,
) -> tuple[bytes | None, bool]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None, True
    lines = text.splitlines(keepends=True)
    normalized = [line.rstrip("\r\n") for line in lines]
    begins = [index for index, line in enumerate(normalized) if line == signature.begin]
    ends = [index for index, line in enumerate(normalized) if line == signature.end]
    if not begins and not ends:
        return None, False
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        return None, True
    body = "\n".join(normalized[begins[0] + 1 : ends[0]]) + "\n"
    if signature.format is LegacySignatureFormat.MARKDOWN:
        return body.encode(), False
    try:
        if signature.format is LegacySignatureFormat.TOML:
            value = _json_value(tomllib.loads(body))
        elif signature.format is LegacySignatureFormat.YAML:
            value = cast(JsonValue, _load_legacy_yaml(body.encode()))
        else:
            return None, True
        normalized_body = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    except ControlPlaneError, tomllib.TOMLDecodeError, TypeError, ValueError:
        return None, True
    return normalized_body, False


def _strip_bounded_block(content: bytes, signature: LegacySignatureDeclaration) -> bytes:
    """Remove one exactly recognized legacy block while preserving outside bytes."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("legacy bounded content is not UTF-8") from exc
    lines = text.splitlines(keepends=True)
    normalized = [line.rstrip("\r\n") for line in lines]
    assert signature.begin is not None and signature.end is not None
    begins = [index for index, line in enumerate(normalized) if line == signature.begin]
    ends = [index for index, line in enumerate(normalized) if line == signature.end]
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise ControlPlaneError("legacy bounded content changed after signature inspection")
    return "".join((*lines[: begins[0]], *lines[ends[0] + 1 :])).encode()


def _retirement_views(
    reports: tuple[MigrationReport, ...],
    payloads: Mapping[tuple[str, str], InstalledPayload],
    legacy_files: Mapping[str, bytes],
) -> tuple[frozenset[SafeRelativePath], tuple[tuple[SafeRelativePath, bytes], ...]]:
    """Separate whole-file retirement from bounded-block semantic replacement."""
    whole: set[SafeRelativePath] = set()
    bounded: dict[SafeRelativePath, bytes] = {}
    for report in reports:
        payload = payloads[(report.package.standard_id, report.package.version.value)]
        signatures = {item.id: item for item in payload.manifest.legacy_signatures}
        for claim in report.claims:
            if claim.disposition is not LegacyDisposition.REMOVE:
                continue
            signature = signatures[claim.signature_id]
            if signature.kind is LegacySignatureKind.WHOLE_FILE:
                whole.add(claim.target)
                continue
            current = bounded.get(claim.target, legacy_files[claim.target.original])
            bounded[claim.target] = _strip_bounded_block(current, signature)
    return frozenset(whole), tuple(
        sorted(bounded.items(), key=lambda item: item[0].original.encode("utf-8"))
    )


def _legacy_target(repo: Path, target: SafeRelativePath) -> Path:
    current = repo
    for part in target.normalized.parts:
        current /= part
        if current.is_symlink():
            raise ControlPlaneError("legacy signature path cannot contain a symlink")
    return current


def _inspect_signatures(
    repo: Path,
    payload: InstalledPayload,
    signature_ids: frozenset[str],
    file_cache: dict[str, bytes],
) -> tuple[dict[tuple[str, str, str], _ObservedSignature], list[ControlFinding]]:
    observed: dict[tuple[str, str, str], _ObservedSignature] = {}
    findings: list[ControlFinding] = []
    signatures = {
        signature.id: signature
        for signature in payload.manifest.legacy_signatures
        if signature.id in signature_ids
    }
    for signature_id in sorted(signature_ids):
        signature = signatures[signature_id]
        for target in signature.targets:
            path = _legacy_target(repo, target)
            if not path.exists():
                continue
            content = file_cache.get(target.original)
            if content is None:
                content = _read_regular_file(path, kind="legacy signature target")
                file_cache[target.original] = content
            candidate = content
            malformed = False
            if signature.kind is LegacySignatureKind.BOUNDED_BLOCK:
                candidate, malformed = _bounded_block(content, signature)
                if candidate is None and not malformed:
                    continue
            if malformed or candidate is None:
                findings.append(
                    _finding(
                        "CP-MIGRATION-LEGACY-BLOCK",
                        path=target.original,
                        identity=signature.id,
                        standard_id=payload.manifest.payload.standard,
                        version=payload.manifest.payload.version.value,
                        message="legacy bounded content is ambiguous",
                        hint="restore a known managed block or remove the partial markers",
                    )
                )
                continue
            digest = _digest(candidate)
            known = digest in signature.known_content_digests
            item = _ObservedSignature(
                payload.manifest.payload.standard,
                signature.id,
                target,
                digest,
                known,
                candidate,
            )
            observed[item.key] = item
            if not known and signature.kind is not LegacySignatureKind.WHOLE_FILE:
                findings.append(
                    _finding(
                        "CP-MIGRATION-LEGACY-DIGEST",
                        path=target.original,
                        identity=signature.id,
                        standard_id=payload.manifest.payload.standard,
                        version=payload.manifest.payload.version.value,
                        message="legacy content does not match a declared signature",
                        hint="restore known content or preserve the local version explicitly",
                    )
                )
    return observed, findings


def _signature_snapshot(
    observed: Mapping[tuple[str, str, str], _ObservedSignature],
) -> JsonObject:
    snapshot: JsonObject = {}
    for (_standard_id, _signature_id, _target), item in sorted(observed.items()):
        signature = cast(JsonObject, snapshot.setdefault(item.signature_id, {}))
        signature[item.target.original] = {
            "digest": item.digest.value,
            "known": item.known,
            "content_base64": base64.b64encode(item.content).decode("ascii"),
        }
    return snapshot


def _legacy_migrations(payload: InstalledPayload) -> tuple[tuple[str, frozenset[str]], ...]:
    providers: dict[str, set[str]] = {}
    for migration in payload.manifest.migrations:
        if (
            migration.mode is MigrationMode.AUTOMATIC
            and migration.provider is not None
            and migration.from_endpoint.legacy_state is not None
            and migration.to_endpoint.package_version == payload.manifest.payload.version
        ):
            providers.setdefault(migration.provider, set()).update(migration.signatures)
    return tuple(
        (provider, frozenset(signatures)) for provider, signatures in sorted(providers.items())
    )


def _merge_reports(reports: list[MigrationReport]) -> MigrationReport:
    if not reports:
        raise ControlPlaneError("selected package has no applicable legacy migration report")
    first = reports[0]
    if any(
        report.package.standard_id != first.package.standard_id
        or report.package.version != first.package.version
        or report.package.selector != first.package.selector
        or report.package.config != first.package.config
        for report in reports[1:]
    ):
        raise ControlPlaneError("legacy migration providers returned conflicting package state")
    try:
        return MigrationReport(
            schema_version="1.0",
            package=MigratedPackage(
                standard_id=first.package.standard_id,
                version=first.package.version,
                selector=first.package.selector,
                config=first.package.config,
                recognized_settings=tuple(
                    setting for report in reports for setting in report.package.recognized_settings
                ),
            ),
            claims=tuple(claim for report in reports for claim in report.claims),
            findings=tuple(finding for report in reports for finding in report.findings),
        )
    except ValidationError as exc:
        raise ControlPlaneError("legacy migration providers returned overlapping results") from exc


def _pointer_parts(pointer: str) -> tuple[str, ...]:
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/"))


def _pointer_exists(document: JsonObject, pointer: str) -> bool:
    current: JsonValue = document
    for part in _pointer_parts(pointer):
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        elif isinstance(current, list) and part.isascii() and part.isdigit():
            index = int(part)
            if index >= len(current):
                return False
            current = current[index]
        else:
            return False
    return True


def _pointer_value(document: JsonObject, pointer: str) -> object:
    current: object = document
    for part in _pointer_parts(pointer):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isascii() and part.isdigit():
            index = int(part)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _leaf_pointers(value: JsonValue, prefix: str = "") -> tuple[str, ...]:
    if isinstance(value, dict):
        if not value:
            return (prefix,)
        return tuple(
            pointer
            for key, child in sorted(value.items())
            for pointer in _leaf_pointers(child, f"{prefix}/{_escape_pointer(key)}")
        )
    if isinstance(value, list):
        if not value:
            return (prefix,)
        return tuple(
            pointer
            for index, child in enumerate(value)
            for pointer in _leaf_pointers(child, f"{prefix}/{index}")
        )
    return (prefix,)


def _pointers_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _pointer_covers(pointer: str, leaf: str) -> bool:
    return pointer == leaf or leaf.startswith(f"{pointer}/")


def _coverage_findings(
    legacy: JsonObject,
    reports: tuple[MigrationReport, ...],
) -> list[ControlFinding]:
    findings: list[ControlFinding] = []
    claims: list[tuple[str, str, str]] = []
    for report in reports:
        for pointer in report.package.recognized_settings:
            if not _pointer_exists(legacy, pointer):
                findings.append(
                    _finding(
                        "CP-MIGRATION-SETTING-MISSING",
                        path=".project-standards.yml",
                        identity=pointer,
                        standard_id=report.package.standard_id,
                        version=report.package.version.value,
                        message="migration provider claimed a setting that is not present",
                        hint="update the provider declaration or the legacy configuration",
                    )
                )
            claims.append((pointer, report.package.standard_id, report.package.version.value))
    for index, (pointer, standard_id, version) in enumerate(claims):
        for other, other_id, _other_version in claims[index + 1 :]:
            if _pointers_overlap(pointer, other):
                findings.append(
                    _finding(
                        "CP-MIGRATION-SETTING-OVERLAP",
                        path=".project-standards.yml",
                        identity=pointer,
                        standard_id=standard_id,
                        version=version,
                        message="migration providers claimed overlapping legacy settings",
                        hint=f"make the {standard_id} and {other_id} setting claims disjoint",
                    )
                )
    platform = legacy.get("standards_version")
    if platform != "v4":
        findings.append(
            _finding(
                "CP-MIGRATION-PLATFORM-VERSION",
                path=".project-standards.yml",
                identity="/standards_version",
                message="legacy platform version is not recognized",
                hint="use a supported v4 legacy configuration",
            )
        )
    recognized = [pointer for pointer, _standard_id, _version in claims]
    if platform == "v4":
        recognized.append("/standards_version")
    for leaf in _leaf_pointers(cast(JsonValue, legacy)):
        if not any(_pointer_covers(pointer, leaf) for pointer in recognized):
            findings.append(
                _finding(
                    "CP-MIGRATION-UNCLAIMED-SETTING",
                    path=".project-standards.yml",
                    identity=leaf,
                    message="legacy setting is not represented by any selected package",
                    hint="remove the unknown setting or add a declared package migration",
                )
            )
    return findings


def _claim_findings(
    reports: tuple[MigrationReport, ...],
    observed: Mapping[tuple[str, str, str], _ObservedSignature],
    legacy: JsonObject,
    payloads: Mapping[tuple[str, str], InstalledPayload],
    reconciliation: ReconciliationPlan,
) -> list[ControlFinding]:
    findings: list[ControlFinding] = []
    claimed: dict[tuple[str, str, str], str] = {}
    cleared_unknown: set[tuple[str, str, str]] = set()
    resolved_packages = {
        package.standard_id: package for package in reconciliation.resolution.packages
    }
    report_versions = {
        report.package.standard_id: report.package.version.value for report in reports
    }
    signature_declarations = {
        (report.package.standard_id, signature.id): signature
        for report in reports
        for signature in payloads[
            (report.package.standard_id, report.package.version.value)
        ].manifest.legacy_signatures
    }
    for report in reports:
        payload = payloads[(report.package.standard_id, report.package.version.value)]
        signatures = {signature.id: signature for signature in payload.manifest.legacy_signatures}
        resolved_package = resolved_packages.get(report.package.standard_id)
        for claim in report.claims:
            key = (report.package.standard_id, claim.signature_id, claim.target.original)
            item = observed.get(key)
            signature = signatures.get(claim.signature_id)
            prior = claimed.get(key)
            if prior is not None:
                findings.append(
                    _finding(
                        "CP-MIGRATION-CLAIM-OVERLAP",
                        path=claim.target.original,
                        identity=claim.signature_id,
                        standard_id=report.package.standard_id,
                        version=report.package.version.value,
                        message="several packages claimed the same legacy object",
                        hint=f"make the {prior} and {report.package.standard_id} claims disjoint",
                    )
                )
            claimed[key] = report.package.standard_id
            if item is not None and item.known:
                if item.digest != claim.observed_digest:
                    findings.append(
                        _finding(
                            "CP-MIGRATION-LEGACY-DIGEST",
                            path=claim.target.original,
                            identity=claim.signature_id,
                            standard_id=report.package.standard_id,
                            version=report.package.version.value,
                            message="legacy claim does not match the observed declared signature",
                            hint="rerun preview after restoring recognized legacy content",
                        )
                    )
                if claim.intent_pointer is not None:
                    findings.append(
                        _finding(
                            "CP-MIGRATION-OWNER-RESOLUTION",
                            path=claim.target.original,
                            identity=claim.signature_id,
                            standard_id=report.package.standard_id,
                            version=report.package.version.value,
                            message="known package history cannot use owner-resolution evidence",
                            hint="omit owner intent from claims for recognized package history",
                        )
                    )
                continue

            declaration_materializes = resolved_package is None or any(
                declaration.target == claim.target
                and declaration.materializes(resolved_package.effective_config)
                for declaration in (
                    *payload.manifest.artifacts,
                    *payload.manifest.contributions,
                )
            )
            valid_relinquishment = (
                signature is not None
                and signature.kind is LegacySignatureKind.WHOLE_FILE
                and len(signature.targets) == 1
                and signature.targets[0] == claim.target
                and signature.consumer_owned_intent_pointer is not None
                and claim.intent_pointer == signature.consumer_owned_intent_pointer
                and claim.intent_pointer in report.package.recognized_settings
                and _pointer_value(legacy, claim.intent_pointer) == "consumer-owned"
                and claim.ownership == "consumer-owned"
                and claim.disposition is LegacyDisposition.PRESERVE
                and item is not None
                and item.digest == claim.observed_digest
                and not declaration_materializes
                and not any(
                    target.target == claim.target.original for target in reconciliation.targets
                )
                and not any(
                    action.target == claim.target.original for action in reconciliation.actions
                )
                and not any(unit.target == claim.target.original for unit in reconciliation.units)
                and not any(
                    unit.path == claim.target for unit in reconciliation.next_lock.artifacts
                )
            )
            if valid_relinquishment:
                assert item is not None
                cleared_unknown.add(item.key)
            elif claim.intent_pointer is not None or (
                signature is not None and signature.consumer_owned_intent_pointer is not None
            ):
                findings.append(
                    _finding(
                        "CP-MIGRATION-OWNER-RESOLUTION",
                        path=claim.target.original,
                        identity=claim.signature_id,
                        standard_id=report.package.standard_id,
                        version=report.package.version.value,
                        message="legacy ownership relinquishment is not fully authorized",
                        hint="restore the target-bound consumer-owned preserve contract",
                    )
                )
    for key, item in sorted(observed.items()):
        signature = signature_declarations[(item.standard_id, item.signature_id)]
        if (
            not item.known
            and signature.kind is LegacySignatureKind.WHOLE_FILE
            and key not in cleared_unknown
        ):
            findings.append(
                _finding(
                    "CP-MIGRATION-LEGACY-DIGEST",
                    path=item.target.original,
                    identity=item.signature_id,
                    standard_id=item.standard_id,
                    version=report_versions[item.standard_id],
                    message="legacy content does not match a declared signature",
                    hint="restore known content or preserve the local version explicitly",
                )
            )
        elif item.known and key not in claimed:
            findings.append(
                _finding(
                    "CP-MIGRATION-UNCLAIMED-ARTIFACT",
                    path=item.target.original,
                    identity=item.signature_id,
                    message="recognized legacy content has no ownership disposition",
                    hint="make the selected migration provider claim or preserve it",
                )
            )
    return findings


def _toml_key(value: str) -> str:
    if _BARE_TOML_KEY.fullmatch(value) is not None:
        return value
    return json.dumps(value, ensure_ascii=False)


def _toml_value(value: JsonValue) -> str:
    if value is None:
        raise ControlPlaneError("migrated package config cannot contain TOML null values")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return (
        "{ "
        + ", ".join(
            f"{_toml_key(key)} = {_toml_value(child)}" for key, child in sorted(value.items())
        )
        + " }"
    )


def _render_config(config: DesiredConfig) -> bytes:
    lines = [
        "[project_standards]",
        'schema_version = "1.0"',
        f"catalog = {json.dumps(config.project_standards.catalog.value)}",
    ]
    for standard_id, package in config.standards.items():
        selector = package.version
        selector_value = selector.value if isinstance(selector, PackageVersion) else selector
        lines.extend(
            [
                "",
                f"[standards.{_toml_key(standard_id)}]",
                f"enabled = {'true' if package.enabled else 'false'}",
                f"version = {json.dumps(selector_value)}",
                f"config = {_toml_value(cast(JsonValue, package.config))}",
            ]
        )
    return ("\n".join(lines) + "\n").encode()


def _resolution_payloads(installed: InstalledCatalog) -> tuple[ResolutionPayload, ...]:
    result: list[ResolutionPayload] = []
    for payload in installed.payloads:
        if payload.manifest.payload.availability.value != "consumer":
            continue
        result.append(
            ResolutionPayload(
                standard_id=payload.manifest.payload.standard,
                version=payload.manifest.payload.version,
                payload_digest=payload.integrity.aggregate_digest,
                option_schema=load_option_schema(payload.root, payload.manifest),
            )
        )
    return tuple(result)


def _transitions(installed: InstalledCatalog) -> frozenset[DeclaredTransition]:
    transitions: set[DeclaredTransition] = set()
    for payload in installed.payloads:
        for migration in payload.manifest.migrations:
            source = migration.from_endpoint.package_version
            target = migration.to_endpoint.package_version
            if source is not None and target is not None:
                transitions.add(
                    DeclaredTransition(
                        payload.manifest.payload.standard,
                        source,
                        target,
                    )
                )
    return frozenset(transitions)


def _empty_lock(
    distribution: InstalledDistribution,
    catalog: ConsumerCatalog,
    desired: DesiredConfig,
) -> CentralLock:
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": catalog.project_standards.catalog.value,
                "release": distribution.tool_release.value,
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


def _adopted_legacy_units(
    reports: tuple[MigrationReport, ...],
    observed: Mapping[tuple[str, str, str], _ObservedSignature],
    payloads: Mapping[tuple[str, str], InstalledPayload],
) -> tuple[LockedUnit, ...]:
    """Authorize exact legacy whole files that the selected package will replace."""
    units: list[LockedUnit] = []
    for report in reports:
        package = report.package
        payload = payloads[(package.standard_id, package.version.value)]
        signatures = {item.id: item for item in payload.manifest.legacy_signatures}
        artifacts = {item.target: item for item in payload.manifest.artifacts}
        contributions = {
            item.target: item
            for item in payload.manifest.contributions
            if item.adapter is AdapterKind.WHOLE_FILE and item.scope == "$file"
        }
        for claim in report.claims:
            observed_item = observed.get(
                (package.standard_id, claim.signature_id, claim.target.original)
            )
            if (
                claim.disposition is LegacyDisposition.IMPORT_LOCK
                and claim.ownership == "package-lock"
                and observed_item is not None
                and observed_item.known
                and observed_item.digest == claim.observed_digest
            ):
                try:
                    lock_data = cast(object, json.loads(observed_item.content))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ControlPlaneError("recognized legacy package lock is invalid") from exc
                if not isinstance(lock_data, dict):
                    raise ControlPlaneError("recognized legacy package lock must be an object")
                managed = cast("dict[str, object]", lock_data).get("managed")
                if not isinstance(managed, dict):
                    raise ControlPlaneError("recognized legacy package lock has no managed map")
                for target, raw_digest in cast("dict[str, object]", managed).items():
                    if "#" in target:
                        continue
                    artifact = artifacts.get(SafeRelativePath.parse(target))
                    if artifact is None or not isinstance(raw_digest, str):
                        raise ControlPlaneError(
                            "legacy package lock contains an undeclared managed whole file"
                        )
                    digest = Sha256Digest(f"sha256:{raw_digest}")
                    units.append(
                        LockedUnit(
                            path=artifact.target,
                            adapter=AdapterKind.WHOLE_FILE,
                            scope="$file",
                            owners=(package.standard_id,),
                            versions={package.standard_id: package.version},
                            provenance=UnitProvenance.PACKAGE,
                            policy=ArtifactPolicy.MANAGED,
                            semantic_digest=digest,
                            content_digest=digest,
                            mode=artifact.mode,
                            created_container=True,
                        )
                    )
                continue
            if claim.disposition is not LegacyDisposition.ADOPT or claim.ownership != "managed":
                continue
            signature = signatures.get(claim.signature_id)
            artifact = artifacts.get(claim.target)
            contribution = contributions.get(claim.target)
            policy = (
                artifact.policy
                if artifact is not None
                else (contribution.policy if contribution is not None else None)
            )
            if (
                observed_item is None
                or not observed_item.known
                or observed_item.digest != claim.observed_digest
                or signature is None
                or signature.kind is not LegacySignatureKind.WHOLE_FILE
                or policy is not ArtifactPolicy.MANAGED
            ):
                continue
            provenance = (
                UnitProvenance.PACKAGE
                if artifact is not None
                else (
                    UnitProvenance.PROVIDER
                    if contribution is not None and contribution.provider is not None
                    else UnitProvenance.SOURCE
                )
            )
            units.append(
                LockedUnit(
                    path=claim.target,
                    adapter=AdapterKind.WHOLE_FILE,
                    scope="$file",
                    owners=(package.standard_id,),
                    versions={package.standard_id: package.version},
                    provenance=provenance,
                    policy=ArtifactPolicy.MANAGED,
                    semantic_digest=claim.observed_digest,
                    content_digest=claim.observed_digest,
                    mode=None,
                    created_container=False,
                )
            )
    return tuple(sorted(units, key=lambda item: item.natural_key))


def _dedupe_findings(findings: list[ControlFinding]) -> tuple[ControlFinding, ...]:
    unique = {
        (
            finding.code,
            finding.severity,
            finding.standard_id,
            finding.version,
            finding.path,
            finding.identity,
            finding.message,
            finding.hint,
        ): finding
        for finding in findings
    }
    return tuple(sort_findings(unique.values()))


def _removal_actions(
    reports: tuple[MigrationReport, ...],
    replacement_targets: frozenset[str] = frozenset(),
) -> tuple[ControlAction, ...]:
    actions = [
        ControlAction(
            kind=ActionKind.REMOVE,
            target=".project-standards.yml",
            adapter="whole-file",
            scope="$file",
            standard_id="project-standards",
            summary="remove legacy authority after unified verification",
        )
    ]
    for report in reports:
        for claim in report.claims:
            if claim.disposition not in {
                LegacyDisposition.REMOVE,
                LegacyDisposition.IMPORT_LOCK,
            }:
                continue
            if claim.target.original in replacement_targets:
                continue
            actions.append(
                ControlAction(
                    kind=ActionKind.REMOVE,
                    target=claim.target.original,
                    adapter="whole-file",
                    scope="$file",
                    standard_id=report.package.standard_id,
                    summary="remove imported legacy state after unified verification",
                    before_digest=claim.observed_digest.value,
                )
            )
    return tuple(sort_actions(actions))


def _plan_legacy_migration(
    repo: Path,
    distribution: InstalledDistribution,
    catalog_major: CatalogMajor | str,
    *,
    allowed_states: frozenset[StateKind],
) -> LegacyMigrationPlan:
    """Plan complete replacement of one legacy-only authority without writing."""
    from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
    from project_standards.control_plane.providers import ProviderInvocation, invoke_provider

    normalized = _safe_repo(repo)
    state = detect_control_plane_state(
        normalized,
        tool_release=distribution.tool_release.value,
    )
    if state.kind not in allowed_states:
        raise ControlPlaneError("repository state cannot produce this legacy migration plan")
    legacy_path = normalized / ".project-standards.yml"
    legacy_content = _read_regular_file(legacy_path, kind="legacy config")
    legacy = _load_legacy_yaml(legacy_content)
    major = (
        catalog_major if isinstance(catalog_major, CatalogMajor) else CatalogMajor(catalog_major)
    )
    try:
        installed = distribution.load_catalog(major)
        catalog = distribution.consumer_catalog(major)
    except (PackageContractError, ValueError) as exc:
        raise ControlPlaneError("installed distribution cannot supply migration inputs") from exc
    payloads = installed.payload_map
    reports: list[MigrationReport] = []
    observed: dict[tuple[str, str, str], _ObservedSignature] = {}
    legacy_files = {".project-standards.yml": legacy_content}
    findings: list[ControlFinding] = []
    defaults = sorted(
        (entry for entry in installed.source.packages if entry.role is CatalogRole.DEFAULT),
        key=lambda entry: (entry.id, entry.version.sort_key),
    )
    for entry in defaults:
        payload = payloads[(entry.id, entry.version.value)]
        migrations = _legacy_migrations(payload)
        if not migrations:
            continue
        signature_ids = frozenset(
            signature for _provider, signatures in migrations for signature in signatures
        )
        package_observed, package_findings = _inspect_signatures(
            normalized,
            payload,
            signature_ids,
            legacy_files,
        )
        observed.update(package_observed)
        findings.extend(package_findings)
        provider_reports: list[MigrationReport] = []
        snapshot: JsonObject = {
            "legacy_config": legacy,
            "legacy_signatures": _signature_snapshot(package_observed),
        }
        for provider_id, _signatures in migrations:
            result = invoke_provider(
                ProviderInvocation(
                    repo=normalized,
                    payload=payload,
                    standard_id=entry.id,
                    version=entry.version,
                    provider_id=provider_id,
                    operation=ProviderOperation.MIGRATE,
                    effective_config={},
                    snapshots=snapshot,
                )
            )
            if result.migration_report is None:
                raise ControlPlaneError("migrate provider did not return a migration report")
            provider_reports.append(result.migration_report)
        report = _merge_reports(provider_reports)
        try:
            load_option_schema(payload.root, payload.manifest).resolve_options(
                report.package.config
            )
        except PackageContractError:
            findings.append(
                _finding(
                    "CP-MIGRATION-CONFIG",
                    path=".project-standards.yml",
                    identity=entry.id,
                    standard_id=entry.id,
                    version=entry.version.value,
                    message="migrated package options violate the selected payload schema",
                    hint="correct the legacy values or the migration provider mapping",
                )
            )
        reports.append(report)
        findings.extend(
            ControlFinding(
                code=item.code,
                severity=item.severity,
                standard_id=report.package.standard_id,
                version=report.package.version.value,
                path=item.path.original,
                identity=item.identity,
                message="selected migration provider reported a legacy-state issue",
                hint="inspect the identified legacy path before applying migration",
            )
            for item in report.findings
        )
    ordered_reports = tuple(sorted(reports, key=lambda report: report.package.standard_id))
    if not ordered_reports:
        raise ControlPlaneError("installed catalog has no default legacy migration providers")
    findings.extend(_coverage_findings(legacy, ordered_reports))
    desired = DesiredConfig.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": major.value,
            },
            "standards": {
                report.package.standard_id: {
                    "enabled": True,
                    "version": (
                        report.package.selector.value
                        if isinstance(report.package.selector, PackageVersion)
                        else report.package.selector
                    ),
                    "config": report.package.config,
                }
                for report in ordered_reports
            },
        }
    )
    config_content = _render_config(desired)
    previous_lock = _empty_lock(distribution, catalog, desired).model_copy(
        update={"artifacts": list(_adopted_legacy_units(ordered_reports, observed, payloads))}
    )
    resolution = ResolutionRequest(
        desired=desired,
        catalog=catalog,
        previous_lock=previous_lock,
        allowed_majors=frozenset(),
        payloads=_resolution_payloads(installed),
        transition_paths=_transitions(installed),
    )
    retired_targets, retired_content = _retirement_views(
        ordered_reports,
        payloads,
        legacy_files,
    )
    planner = PlannerRequest(
        repo=normalized,
        resolution=resolution,
        payloads=installed.payloads,
        retired_targets=retired_targets,
        retired_content=retired_content,
    )
    reconciliation = plan_reconciliation(planner)
    if state.kind is StateKind.DUAL_AUTHORITY:
        control = normalized / ".standards"
        intent_path = control / ".migration-lock.toml"
        live_lock_path = control / "lock.toml"
        recovery_lock_path = intent_path if intent_path.exists() else live_lock_path
        if recovery_lock_path.exists() and not recovery_lock_path.is_symlink():
            live_lock = parse_lock(
                _read_regular_file(recovery_lock_path, kind="migration recovery lock")
            )
            normalized_live = live_lock.model_copy(
                update={
                    "artifacts": [
                        artifact.model_copy(update={"created_container": False})
                        for artifact in live_lock.artifacts
                    ]
                }
            )
            normalized_planned = reconciliation.next_lock.model_copy(
                update={
                    "artifacts": [
                        artifact.model_copy(update={"created_container": False})
                        for artifact in reconciliation.next_lock.artifacts
                    ]
                }
            )
            if normalized_live == normalized_planned:
                # A published migration lock retains whether the original apply
                # created each container. Recovery planning observes those paths as
                # preexisting, so it must restore that provenance before comparison.
                reconciliation = replace(reconciliation, next_lock=live_lock)
    from project_standards.control_plane.executor import reconciliation_fingerprint

    reconciliation_digest = reconciliation_fingerprint(reconciliation)
    findings.extend(
        _claim_findings(
            ordered_reports,
            observed,
            legacy,
            payloads,
            reconciliation,
        )
    )
    findings.extend(reconciliation.findings)
    ordered_findings = _dedupe_findings(findings)
    applicable = reconciliation.applicable and not any(
        finding.severity == "error" for finding in ordered_findings
    )
    replacement_targets = frozenset(target.target for target in reconciliation.targets)
    removals = _removal_actions(ordered_reports, replacement_targets) if applicable else ()
    legacy_preconditions = tuple(
        (path, _digest(content)) for path, content in sorted(legacy_files.items())
    )
    catalog_content = render_catalog(catalog)
    lock_content = render_lock(reconciliation.next_lock)
    return LegacyMigrationPlan(
        repo=normalized,
        applicable=applicable,
        reports=ordered_reports,
        findings=ordered_findings,
        desired_config=desired,
        catalog=catalog,
        distribution=distribution,
        planner=planner,
        reconciliation=reconciliation,
        reconciliation_fingerprint=reconciliation_digest,
        content_fingerprint=legacy_migration_content_fingerprint(
            normalized,
            reconciliation_digest,
            legacy_preconditions,
            config_content,
            catalog_content,
            lock_content,
        ),
        legacy_removals=removals,
        legacy_preconditions=legacy_preconditions,
        config_content=config_content,
        catalog_content=catalog_content,
        lock_content=lock_content,
    )


def plan_legacy_migration(
    repo: Path,
    distribution: InstalledDistribution,
    catalog_major: CatalogMajor | str,
) -> LegacyMigrationPlan:
    """Plan complete replacement of one legacy-only authority without writing."""
    return _plan_legacy_migration(
        repo,
        distribution,
        catalog_major,
        allowed_states=frozenset({StateKind.LEGACY_ONLY}),
    )


def plan_legacy_migration_recovery(
    repo: Path,
    distribution: InstalledDistribution,
    catalog_major: CatalogMajor | str,
) -> LegacyMigrationPlan:
    """Reconstruct a migration plan from an explicit dual-authority prefix."""
    return _plan_legacy_migration(
        repo,
        distribution,
        catalog_major,
        allowed_states=frozenset({StateKind.DUAL_AUTHORITY}),
    )
