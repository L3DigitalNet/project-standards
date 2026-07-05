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
