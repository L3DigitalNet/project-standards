from __future__ import annotations

from pathlib import Path

from project_standards.specs.commands.lint import lint_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _codes(name: str) -> set[str]:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    return {f.code for f in lint_document(doc, load_registry())}


def test_draft_placeholders_warn() -> None:
    assert "SL-PLACEHOLDER" in _codes("draft_placeholders.md")


def test_approved_light_flags_dod_not_matrix() -> None:
    codes = _codes("approved_light.md")
    assert "SL-DOD" in codes
    assert "SL-TRACE" not in codes


def test_valid_light_is_clean() -> None:
    assert _codes("valid_light.md") == set()


def test_approved_standard_should_requirement_not_flagged() -> None:
    doc = parse_document(
        "approved_standard_traceability.md",
        (_FIX / "approved_standard_traceability.md").read_text(encoding="utf-8"),
    )
    traces = [f.locus for f in lint_document(doc, load_registry()) if f.code == "SL-TRACE"]
    assert "FR-002" not in traces
    assert "FR-001" not in traces


def test_uppercase_must_priority_is_still_traced() -> None:
    """`Priority` values are authored freehand; `MUST`/`must` must count like `Must`."""
    doc = parse_document(
        "approved_standard_uppercase_must.md",
        (_FIX / "approved_standard_uppercase_must.md").read_text(encoding="utf-8"),
    )
    traces = [f.locus for f in lint_document(doc, load_registry()) if f.code == "SL-TRACE"]
    assert "FR-002" in traces
