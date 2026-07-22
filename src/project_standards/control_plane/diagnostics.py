"""Stable, content-safe diagnostics and planned-action representations."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Literal, cast

from project_standards.package_contract.diagnostics import validation_summary as validation_summary
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import JsonValue


class ControlPlaneError(ValueError):
    """Report an invalid control-plane boundary without leaking input content."""


class ControlPlaneConfigurationError(ControlPlaneError):
    """Report invalid desired configuration at a control-plane boundary."""


class _MajorAuthorizationError(  # pyright: ignore[reportUnusedClass]  # cross-module classifier
    ControlPlaneError
):
    """Report a package-major transition missing its exact authorization."""


class ActionKind(StrEnum):
    """Repository mutation or preservation decisions emitted by planning."""

    CREATE = "create"
    ADOPT = "adopt"
    UPDATE = "update"
    REMOVE = "remove"
    PRESERVE = "preserve"
    NOOP = "no-op"


@dataclass(frozen=True, slots=True)
class ControlFinding:
    """Describe one control-plane result in the stable public report shape."""

    code: str
    severity: Literal["error", "warning"]
    standard_id: str
    version: str
    path: str
    identity: str
    message: str
    hint: str
    line: int | None = None
    locus: str | None = None
    # Conflict enrichment (schema 1.1): values are set only for JSON-representable
    # semantic units; byte-valued and whole-file conflicts carry digests alone.
    # governing_options mirrors the owning contribution's declaration: None means
    # the payload declares nothing, an empty tuple means "no option governs".
    expected: JsonValue | None = None
    actual: JsonValue | None = None
    expected_digest: str | None = None
    actual_digest: str | None = None
    governing_options: tuple[str, ...] | None = None
    # Names among {"expected", "actual"} whose semantic value is a genuine JSON
    # null. Serialization emits those as explicit nulls; a plain None field stays
    # omitted as unset. Without this, null-valued units would vanish from output.
    null_values: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ControlAction:
    """Describe one planned repository action without publishing staged bytes."""

    kind: ActionKind
    target: str
    adapter: str
    scope: str
    standard_id: str
    summary: str
    before_digest: str | None = None
    after_digest: str | None = None
    before_mode: str | None = None
    after_mode: str | None = None
    content: bytes | None = field(default=None, repr=False, compare=False)


def _normalized(value: str) -> tuple[str, str]:
    normalized = unicodedata.normalize("NFC", value)
    return (normalized.casefold(), normalized)


def _version_sort_key(value: str) -> tuple[int, int, int, str, str]:
    try:
        version = PackageVersion(value)
    except ValueError:
        normalized = _normalized(value)
        return (1, 0, 0, *normalized)
    return (0, version.major, version.minor, "", "")


def finding_sort_key(finding: ControlFinding) -> tuple[object, ...]:
    """Return a total semantic ordering key that tolerates invalid facts."""
    return (
        *_normalized(finding.standard_id),
        *_version_sort_key(finding.version),
        finding.identity,
        finding.path,
        finding.code,
        finding.severity,
        finding.message,
        finding.hint,
        finding.line if finding.line is not None else -1,
        finding.locus or "",
        finding.expected_digest or "",
        finding.actual_digest or "",
    )


def action_sort_key(action: ControlAction) -> tuple[str, ...]:
    """Return a deterministic ordering key for repository actions."""
    return (
        *_normalized(action.standard_id),
        action.target,
        action.adapter,
        action.scope,
        action.kind.value,
        action.summary,
        action.before_digest or "",
        action.after_digest or "",
        action.before_mode or "",
        action.after_mode or "",
    )


def sort_findings(findings: Iterable[ControlFinding]) -> list[ControlFinding]:
    """Return findings in deterministic semantic order."""
    return sorted(findings, key=finding_sort_key)


def sort_actions(actions: Iterable[ControlAction]) -> list[ControlAction]:
    """Return actions in deterministic semantic order."""
    return sorted(actions, key=action_sort_key)


def findings_to_jsonable(findings: Iterable[ControlFinding]) -> list[dict[str, object]]:
    """Return deterministically ordered JSON-compatible finding objects."""
    result: list[dict[str, object]] = []
    for finding in sort_findings(findings):
        item = {key: value for key, value in asdict(finding).items() if value is not None}
        item.pop("null_values", None)
        for name in finding.null_values:
            item[name] = None
        options = item.get("governing_options")
        if isinstance(options, tuple):
            item["governing_options"] = list(cast("tuple[str, ...]", options))
        result.append(item)
    return result


def actions_to_jsonable(actions: Iterable[ControlAction]) -> list[dict[str, object]]:
    """Return ordered public action fields while withholding staged content bytes."""
    result: list[dict[str, object]] = []
    for action in sort_actions(actions):
        result.append(
            {
                "kind": action.kind.value,
                "target": action.target,
                "adapter": action.adapter,
                "scope": action.scope,
                "standard_id": action.standard_id,
                "summary": action.summary,
                "before_digest": action.before_digest,
                "after_digest": action.after_digest,
                "before_mode": action.before_mode,
                "after_mode": action.after_mode,
            }
        )
    return result
