"""Stable diagnostics shared by package loaders and validators."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal


class PackageContractError(ValueError):
    """Report malformed package input without leaking boundary implementation errors."""


@dataclass(frozen=True, slots=True)
class PackageFinding:
    """Describe one package-contract violation in a stable report shape."""

    code: str
    severity: Literal["error", "warning"]
    standard_id: str
    version: str
    path: str
    identity: str
    message: str
    hint: str


def finding_sort_key(finding: PackageFinding) -> tuple[str, ...]:
    """Return the total ordering key used by package reports."""
    return (
        finding.code,
        finding.standard_id,
        finding.version,
        finding.path,
        finding.identity,
        finding.message,
        finding.severity,
        finding.hint,
    )


def sort_findings(findings: Iterable[PackageFinding]) -> list[PackageFinding]:
    """Return findings in deterministic field order."""
    return sorted(findings, key=finding_sort_key)


def findings_to_jsonable(findings: Iterable[PackageFinding]) -> list[dict[str, object]]:
    """Return findings as deterministically ordered JSON-compatible objects."""
    result: list[dict[str, object]] = []
    for finding in sort_findings(findings):
        result.append(
            {
                "code": finding.code,
                "severity": finding.severity,
                "standard_id": finding.standard_id,
                "version": finding.version,
                "path": finding.path,
                "identity": finding.identity,
                "message": finding.message,
                "hint": finding.hint,
            }
        )
    return result
