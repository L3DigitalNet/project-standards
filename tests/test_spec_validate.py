from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.lint import lint_document
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"
_REPO_ROOT = Path(__file__).resolve().parent.parent


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


def _make_light_with_body_addition(extra_lines: str) -> str:
    """Return valid_light.md content with extra_lines injected into §1 body."""
    src = (_FIX / "valid_light.md").read_text(encoding="utf-8")
    # Inject after "## 1. Purpose & Background"
    marker = "## 1. Purpose & Background\n"
    idx = src.index(marker) + len(marker)
    return src[:idx] + "\n" + extra_lines + "\n" + src[idx:]


# ---------------------------------------------------------------------------
# F1/F2/F3 — reference_prefixes exemption
# ---------------------------------------------------------------------------


def test_adr_reference_without_refpfx_raises_undeclared() -> None:
    """ADR-0001 in spec body → SV-ID-UNDECLARED without reference_prefixes."""
    text = _make_light_with_body_addition("See ADR-0001 for context.")
    doc = parse_document("t.md", text)
    codes = {f.code for f in validate_document(doc, load_registry())}
    assert "SV-ID-UNDECLARED" in codes


def test_adr_reference_with_refpfx_passes() -> None:
    """ADR-0001 in spec body → clean when ADR is in reference_prefixes."""
    text = _make_light_with_body_addition("See ADR-0001 for context.")
    doc = parse_document("t.md", text)
    codes = {
        f.code
        for f in validate_document(doc, load_registry(), reference_prefixes=frozenset({"ADR"}))
    }
    assert "SV-ID-UNDECLARED" not in codes
    assert "SV-ID-TIER" not in codes
    assert "SV-ID-FMT" not in codes


def test_external_prefix_with_refpfx_passes() -> None:
    """RQ-123 (external namespace) → clean when RQ is in reference_prefixes."""
    text = _make_light_with_body_addition("Resolves RQ-123 and RQ-124.")
    doc = parse_document("t.md", text)
    codes = {
        f.code
        for f in validate_document(doc, load_registry(), reference_prefixes=frozenset({"RQ"}))
    }
    assert "SV-ID-UNDECLARED" not in codes
    assert "SV-ID-TIER" not in codes
    assert "SV-ID-FMT" not in codes


def test_adr_four_digit_width_exempt_via_refpfx() -> None:
    """ADR-0001 (4-digit) → SV-ID-FMT without reference_prefixes; exempt with it."""
    text = _make_light_with_body_addition("See ADR-0001.")
    doc = parse_document("t.md", text)
    # Without reference_prefixes: 4-digit width triggers SV-ID-FMT after SV-ID-UNDECLARED
    codes_bare = {f.code for f in validate_document(doc, load_registry())}
    assert "SV-ID-FMT" in codes_bare
    # With reference_prefixes: all ID checks are skipped for ADR
    codes_ref = {
        f.code
        for f in validate_document(doc, load_registry(), reference_prefixes=frozenset({"ADR"}))
    }
    assert "SV-ID-FMT" not in codes_ref


def test_shipped_dogfood_example_validates_and_lints_clean() -> None:
    """standards/project-spec/examples/spec.example.md is this standard's shipped worked
    example (see standards/project-spec/README.md §2 Scope) — it is excluded from the
    canonical-frontmatter dogfood sweep (test_validate_frontmatter.EXAMPLE_FILES) because it
    uses project-spec's own schema, so it must stay covered here instead."""
    path = _REPO_ROOT / "standards" / "project-spec" / "examples" / "spec.example.md"
    doc = parse_document(str(path), path.read_text(encoding="utf-8"))
    reg = load_registry()
    assert validate_document(doc, reg) == []
    assert lint_document(doc, reg) == []
