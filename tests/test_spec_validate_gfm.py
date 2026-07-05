"""Regression tests: validate must not false-reject well-formed GFM/Unicode specs.

Each test encodes a valid Markdown construct that the validator previously
flagged as an error, so `spec validate` (and, downstream, the fail-closed
`spec upgrade`) refused a correct spec. See the 2026-07-05 code review.
"""

from __future__ import annotations

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.model import Finding
from project_standards.specs.registry import load_registry


def _findings(body: str) -> list[Finding]:
    return validate_document(parse_document("t.md", body), load_registry())


def _codes(body: str) -> set[str]:
    return {f.code for f in _findings(body)}


def test_escaped_and_inline_pipe_in_table_cell_is_not_sv_table() -> None:
    # A GFM table cell may hold a pipe inside inline code or an escaped `\|`.
    # Neither is a column delimiter, so it must not inflate the column count.
    body = (
        "---\nprofile: standard\n---\n\n"
        "## 7. Requirements\n\n"
        "| Name | Meaning |\n"
        "| --- | --- |\n"
        "| Foo | matches `a \\| b` |\n"
    )
    assert "SV-TABLE" not in _codes(body)


def test_disambiguated_anchor_for_repeated_heading_is_not_dead() -> None:
    # GitHub gives a second identically-titled heading the anchor `#slug-1`.
    body = (
        "---\nprofile: standard\n---\n\n"
        "## Notes\n\nfirst\n\n"
        "## Notes\n\n"
        "[see the second](#notes-1)\n"
    )
    assert "SV-ANCHOR" not in _codes(body)


def test_em_dash_omission_range_covers_interior_sections() -> None:
    # An omission note may use an em-dash range (§14—§16); the interior §15
    # must count as annotated, not be reported as an un-annotated gap.
    body = (
        "---\nprofile: standard\n---\n\n"
        "## 1. Purpose\n\nx\n\n"
        "## 2. Scope\n\ny\n\n"
        "> **Sections §14—§16 are Full-tier** and are intentionally omitted at the Standard profile.\n\n"
        "## 7. Requirements\n\nz\n"
    )
    gaps = {f.locus for f in _findings(body) if f.code == "SV-GAP"}
    assert "§15" not in gaps
