from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _codes(name: str) -> set[str]:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    return {f.code for f in validate_document(doc, load_registry())}


@pytest.mark.parametrize("name", ["valid_light.md", "valid_standard.md"])
def test_valid_specs_pass(name: str) -> None:
    assert _codes(name) == set()


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("bad_sentinel.md", "SV-SENTINEL"),
        ("bad_spec_id.md", "SV-SPEC-ID"),
        ("bad_dup_id.md", "SV-ID-DUP"),
        ("bad_dup_dev.md", "SV-ID-DUP"),
        ("bad_undeclared.md", "SV-ID-UNDECLARED"),
        ("bad_tier_prefix.md", "SV-ID-TIER"),
        ("bad_gap.md", "SV-GAP"),
        ("bad_anchor.md", "SV-ANCHOR"),
        ("bad_table.md", "SV-TABLE"),
    ],
)
def test_bad_fixture_reports_code(name: str, code: str) -> None:
    assert code in _codes(name)
