"""Stable, content-safe diagnostics and planned-action representations."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import ValidationError

from project_standards.package_contract.paths import PackageVersion


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
    )


def sort_findings(findings: Iterable[ControlFinding]) -> list[ControlFinding]:
    """Return findings in deterministic semantic order."""
    return sorted(findings, key=finding_sort_key)


def sort_actions(actions: Iterable[ControlAction]) -> list[ControlAction]:
    """Return actions in deterministic semantic order."""
    return sorted(actions, key=action_sort_key)


def findings_to_jsonable(findings: Iterable[ControlFinding]) -> list[dict[str, object]]:
    """Return deterministically ordered JSON-compatible finding objects."""
    return [asdict(finding) for finding in sort_findings(findings)]


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
            }
        )
    return result


def validation_summary(exc: ValidationError) -> str:
    """Summarize structural failures without echoing untrusted input values."""
    summaries: list[str] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = ".".join(str(part) for part in error["loc"])
        summaries.append(f"{location or '<root>'}: {error['msg']}")
    return "; ".join(summaries)
