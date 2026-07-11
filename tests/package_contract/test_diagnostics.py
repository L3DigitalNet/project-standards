from __future__ import annotations

import dataclasses
from typing import Literal

from project_standards.package_contract import (
    PackageContractError,
    PackageFinding,
    finding_sort_key,
    findings_to_jsonable,
    sort_findings,
)


def _finding(*, code: str, severity: Literal["error", "warning"] = "error") -> PackageFinding:
    return PackageFinding(
        code=code,
        severity=severity,
        standard_id="markdown-tooling",
        version="5.0",
        path="standards/markdown-tooling/standard.toml",
        identity="standard:markdown-tooling",
        message=f"message for {code}",
        hint=f"hint for {code}",
    )


def test_package_finding_has_the_stable_public_field_contract() -> None:
    finding = _finding(code="PKG002", severity="warning")

    assert dataclasses.is_dataclass(finding)
    assert [field.name for field in dataclasses.fields(finding)] == [
        "code",
        "severity",
        "standard_id",
        "version",
        "path",
        "identity",
        "message",
        "hint",
    ]
    assert finding.severity == "warning"


def test_package_finding_is_frozen_and_slotted() -> None:
    finding = _finding(code="PKG001")

    assert not hasattr(finding, "__dict__")
    try:
        finding.code = "PKG999"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("PackageFinding must be immutable")


def test_finding_sort_is_independent_of_input_order() -> None:
    first = _finding(code="PKG001")
    second = _finding(code="PKG002", severity="warning")

    assert sort_findings([second, first]) == sort_findings([first, second]) == [first, second]


def test_finding_sort_key_preserves_v1_leading_order_with_total_tie_breakers() -> None:
    finding = _finding(code="PKG001", severity="warning")

    assert finding_sort_key(finding) == (
        finding.code,
        finding.standard_id,
        finding.version,
        finding.path,
        finding.identity,
        finding.message,
        finding.severity,
        finding.hint,
    )


def test_findings_to_jsonable_is_sorted_and_uses_exact_fields() -> None:
    first = _finding(code="PKG001")
    second = _finding(code="PKG002", severity="warning")

    expected = [
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
        for finding in (first, second)
    ]
    assert findings_to_jsonable([second, first]) == expected
    assert findings_to_jsonable([first, second]) == expected


def test_package_contract_error_is_a_value_error() -> None:
    assert issubclass(PackageContractError, ValueError)
