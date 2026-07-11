"""Stable diagnostics shared by package loaders and validators."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from project_standards.package_contract.paths import PackageVersion


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


def _version_sort_key(value: str) -> tuple[int, int, int, str, str]:
    try:
        version = PackageVersion(value)
    except ValueError:
        return (1, 0, 0, unicodedata.normalize("NFC", value).casefold(), value)
    return (0, version.major, version.minor, "", "")


def finding_sort_key(
    finding: PackageFinding,
) -> tuple[str, int, int, int, str, str, str, str, str, str, str, str, str]:
    """Return a total semantic ordering key that remains safe for invalid findings."""
    version_key = _version_sort_key(finding.version)
    return (
        unicodedata.normalize("NFC", finding.standard_id).casefold(),
        *version_key,
        finding.identity,
        finding.path,
        finding.code,
        finding.severity,
        finding.message,
        finding.hint,
        finding.standard_id,
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
