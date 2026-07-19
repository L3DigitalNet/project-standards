from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from project_standards.specs.commands.extract import extract_slice
from project_standards.specs.document import parse_document
from project_standards.specs.model import SpecDocument

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _doc() -> SpecDocument:
    return parse_document(
        "valid_standard.md", (_FIX / "valid_standard.md").read_text(encoding="utf-8")
    )


def test_extract_section_includes_subsections() -> None:
    result = extract_slice(_doc(), "§7")
    assert result.found and result.kind == "section" and result.markdown
    assert result.markdown.lstrip().startswith("##")
    assert "FR-001" in result.markdown


def test_extract_appendix_found() -> None:
    assert extract_slice(_doc(), "Appendix B").found


def test_extract_letterless_appendix_selector_degrades_cleanly() -> None:
    # Regression: "Appendix " (trailing space only) satisfies the startswith("appendix ")
    # guard but split() strips it, so the old code raised IndexError instead of no-matching.
    # (Bare "Appendix" with no space skips this branch and matches a heading — not tested here.)
    for sel in ("Appendix ", "appendix   "):
        result = extract_slice(_doc(), sel)
        assert not result.found and result.markdown is None


def test_extract_missing_id_not_found() -> None:
    result = extract_slice(_doc(), "FR-999")
    assert not result.found and result.markdown is None


def test_heading_selector_starts_at_matching_heading() -> None:
    doc = replace(
        _doc(),
        body="# Earlier\nintro\n## Matching heading\nkept\n## Next\nafter\n",
    )

    result = extract_slice(doc, "Matching heading")

    assert result.kind == "heading"
    assert result.found
    assert result.markdown == "## Matching heading\nkept"


def test_heading_selector_does_not_match_prose() -> None:
    doc = replace(
        _doc(),
        body=("# Actual heading\nParagraph mentions Requested Selector.\n## Next\nafter\n"),
    )

    result = extract_slice(doc, "Requested Selector")

    assert result.kind == "heading"
    assert not result.found
    assert result.markdown is None


@pytest.mark.parametrize(
    "line_break",
    [pytest.param("\n", id="line-feed"), pytest.param("\r", id="carriage-return")],
)
def test_heading_selector_does_not_match_across_line_break(line_break: str) -> None:
    doc = replace(
        _doc(),
        body=f"# Actual heading{line_break}Paragraph text\n## Next\nafter\n",
    )

    result = extract_slice(doc, f"Actual heading{line_break}Paragraph")

    assert result.kind == "heading"
    assert not result.found
    assert result.markdown is None
