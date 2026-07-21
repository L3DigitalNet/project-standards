from __future__ import annotations

import dataclasses
import itertools
from typing import Literal, get_type_hints

import pytest
from pydantic import BaseModel, RootModel, ValidationError

import project_standards.package_contract as package_contract
from project_standards.package_contract import (
    PackageContractError,
    PackageFinding,
    finding_sort_key,
    findings_to_jsonable,
    sort_findings,
)
from project_standards.package_contract.diagnostics import validation_summary


class _SummaryModel(BaseModel):
    name: str
    count: int


class _RootSummaryModel(RootModel[int]):
    pass


def _finding(
    *,
    code: str,
    severity: Literal["error", "warning"] = "error",
    standard_id: str = "markdown-tooling",
    version: str = "5.0",
    identity: str = "standard:markdown-tooling",
    path: str = "standards/markdown-tooling/standard.toml",
) -> PackageFinding:
    return PackageFinding(
        code=code,
        severity=severity,
        standard_id=standard_id,
        version=version,
        path=path,
        identity=identity,
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
    assert get_type_hints(PackageFinding)["severity"] == Literal["error", "warning"]


def test_package_root_does_not_export_internal_severity_alias() -> None:
    assert not hasattr(package_contract, "Severity")


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


def test_finding_sort_uses_numeric_versions_for_every_input_permutation() -> None:
    findings = tuple(
        _finding(code=f"PKG{index:03d}", version=version)
        for index, version in enumerate(("10.0", "2.10", "2.2"), start=1)
    )

    for permutation in itertools.permutations(findings):
        assert [finding.version for finding in sort_findings(permutation)] == [
            "2.2",
            "2.10",
            "10.0",
        ]


def test_finding_sort_handles_malformed_versions_with_deterministic_fallback() -> None:
    versions = ("bad", "", "BAD", "1.02")
    findings = tuple(
        _finding(code="PKG001", version=version, identity="same") for version in versions
    )

    expected = ["", "1.02", "BAD", "bad"]
    for permutation in itertools.permutations(findings):
        assert [finding.version for finding in sort_findings(permutation)] == expected


def test_finding_sort_uses_normalized_standard_id_and_original_spelling_fallback() -> None:
    lowercase = _finding(code="PKG001", standard_id="alpha", identity="same")
    uppercase = _finding(code="PKG001", standard_id="ALPHA", identity="same")
    later = _finding(code="PKG001", standard_id="beta", identity="same")

    assert sort_findings([later, lowercase, uppercase]) == [uppercase, lowercase, later]


def test_finding_sort_key_never_parses_invalid_version_eagerly() -> None:
    finding = _finding(code="PKG001", version="not-a-version")

    assert finding_sort_key(finding)[1] == 1


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
    reverse_result = findings_to_jsonable([second, first])
    forward_result = findings_to_jsonable([first, second])

    assert reverse_result == expected
    assert forward_result == expected
    expected_keys = [
        "code",
        "severity",
        "standard_id",
        "version",
        "path",
        "identity",
        "message",
        "hint",
    ]
    assert [list(item) for item in reverse_result] == [expected_keys, expected_keys]
    assert [list(item) for item in forward_result] == [expected_keys, expected_keys]


def test_package_contract_error_is_a_value_error() -> None:
    assert issubclass(PackageContractError, ValueError)


def test_validation_summary__invalid_model__omits_input_values() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _SummaryModel.model_validate({"name": {"never": "print-this"}, "count": "also-secret"})

    summary = validation_summary(exc_info.value)

    assert summary.startswith("name: ")
    assert "; count: " in summary
    assert "never" not in summary
    assert "print-this" not in summary
    assert "also-secret" not in summary


def test_validation_summary__root_error__uses_root_location() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _RootSummaryModel.model_validate("secret-root-input")

    summary = validation_summary(exc_info.value)

    assert summary.startswith("<root>: ")
    assert "secret-root-input" not in summary
