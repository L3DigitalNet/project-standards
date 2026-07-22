from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.document import (
    SpecParseError,
    definition_sites,
    parse_document,
    section_slice,
)
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_parse_valid_light() -> None:
    doc = parse_document("valid_light.md", (_FIX / "valid_light.md").read_text(encoding="utf-8"))
    assert doc.profile == "light"
    assert doc.frontmatter["spec_id"] == "SPEC-7F3Q"
    assert "FR" in doc.used_ids
    assert doc.frontmatter_keys[0] == "spec_id"


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_raw_template_frontmatter_ignores_inline_comments(tier: str) -> None:
    path = TEMPLATES_DIR / TIER_FILES[tier]
    doc = parse_document(str(path), path.read_text(encoding="utf-8"))
    assert doc.profile == tier
    assert doc.frontmatter["spec_id"] == "SPEC-____"


def test_used_ids_line_numbers_are_one_indexed() -> None:
    doc = parse_document("x.md", "---\n\n---\n# t\nline2\nFR-001 here\nline4\nFR-002 and FR-003\n")
    assert [ln for _fid, ln in doc.used_ids["FR"]] == [3, 5, 5]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("# Body\n", 0, id="no-frontmatter"),
        pytest.param("---\nspec_id: SPEC-0001\n---\n# Body\n", 3, id="frontmatter"),
        pytest.param("---\nspec_id: SPEC-0001\n---", 2, id="empty-body"),
        pytest.param("---\r\nspec_id: SPEC-0001\r\n---\r\n# Body\r\n", 0, id="crlf-unrecognized"),
    ],
)
def test_body_line_offset_tracks_split_frontmatter(source: str, expected: int) -> None:
    doc = parse_document("x.md", source)

    assert doc.body_line_offset == expected


def test_denylist_excludes_non_ids() -> None:
    doc = parse_document("x.md", "---\n\n---\n# t\nText about WCAG-2 and PITR-1 and FR-005.\n")
    assert "WCAG" not in doc.used_ids and "PITR" not in doc.used_ids
    assert "FR" in doc.used_ids


def test_definition_sites_ignore_traceability_references() -> None:
    doc = parse_document(
        "valid_standard.md", (_FIX / "valid_standard.md").read_text(encoding="utf-8")
    )
    fr_defs = [fid for fid, _ in definition_sites(doc).get("FR", [])]
    assert fr_defs.count("FR-001") == 1


def test_section_slice_includes_subsections() -> None:
    doc = parse_document(
        "valid_standard.md", (_FIX / "valid_standard.md").read_text(encoding="utf-8")
    )
    sl = section_slice(doc, "7")
    assert sl is not None and "FR-001" in sl


def test_malformed_frontmatter_raises_specparseerror() -> None:
    with pytest.raises(SpecParseError):
        parse_document("bad.md", "---\nspec_id: SPEC-7F3Q\n# no closing fence, no body\n")


def _body(text: str) -> str:
    # parse_document needs frontmatter to split; a minimal fence is enough here.
    return "---\nspec_id: SPEC-0001\n---\n" + text


def test_fenced_ids_headings_and_declarations_do_not_become_structure() -> None:
    doc = parse_document(
        "t.md",
        _body(
            "## 1. Purpose\n\n"
            "Real FR-001.\n\n"
            "```markdown\n"
            "## 99. Example\n\n"
            "RQ-123\n\n"
            "## Appendix A: Example ID Conventions\n\n"
            "| Prefix | Meaning | Defined In |\n"
            "| --- | --- | --- |\n"
            "| `RQ-` | Example | §99 |\n"
            "```\n\n"
            "## Appendix A: ID Conventions\n\n"
            "| Prefix | Meaning | Defined In |\n"
            "| --- | --- | --- |\n"
            "| `FR-` | Functional | §1 |\n"
        ),
    )

    assert doc.sections == [("1", 1)]
    assert "99-example" not in doc.slugs
    assert "RQ" not in doc.used_ids
    assert doc.declared_prefixes == {"FR": "§1"}


def test_anchor_slugs_include_h1_h5_h6_without_promoting_sections() -> None:
    doc = parse_document(
        "t.md",
        _body(
            "# Project Title\n\n"
            "## 1. Purpose\n\n"
            "##### 9. Deep Anchor\n\n"
            "###### 10. Deepest Anchor\n\n"
            "```markdown\n"
            "# Fenced Title\n"
            "##### 11. Fenced Deep Anchor\n"
            "```\n"
        ),
    )

    assert [number for number, _line in doc.sections] == ["1"]
    assert {"project-title", "1-purpose", "9-deep-anchor", "10-deepest-anchor"} <= doc.slugs
    assert {"fenced-title", "11-fenced-deep-anchor"}.isdisjoint(doc.slugs)


def test_fenced_definition_rows_do_not_create_definition_sites() -> None:
    doc = parse_document(
        "t.md",
        _body(
            "## 7. Requirements\n\n"
            "### 7.1 Functional Requirements\n\n"
            "| ID | Text |\n"
            "| --- | --- |\n"
            "| `FR-001` | Real requirement |\n\n"
            "```markdown\n"
            "| `FR-001` | Example row |\n"
            "```\n\n"
            "## Appendix A: ID Conventions\n\n"
            "| Prefix | Meaning | Defined In |\n"
            "| --- | --- | --- |\n"
            "| `FR-` | Functional | §7.1 |\n"
        ),
    )

    assert [full_id for full_id, _line in definition_sites(doc)["FR"]] == ["FR-001"]


def test_skip_set_zero_config() -> None:
    doc = parse_document(
        "t.md",
        _body(
            "Refs adr-0001-x and ADR-0001. Licenses MPL-2.0, CC-BY-4.0, and the current SPDX "
            "forms GPL-3.0-only and AGPL-3.0-or-later, plus the bare colloquial GPL-3. "
            "Own id FR-007 and a sentence end FR-008. Version-shaped FR-1.2 here."
        ),
    )
    prefixes = set(doc.used_ids)
    # ADR (built-in ref) and the license families are never recorded — including the
    # modern SPDX forms (GPL-3.0-only -> GPL-3 then ".0" => dot-rule) and the bare GPL-3
    # (via the NOT_AN_ID family denylist):
    assert "ADR" not in prefixes
    assert prefixes.isdisjoint({"MPL", "BY", "GPL", "AGPL"})
    # Real spec-local ids survive, including one at a sentence boundary:
    assert [fid for fid, _ in doc.used_ids["FR"]] == ["FR-007", "FR-008"]
    # The version-shaped token FR-1.2 is skipped (dot+digit), so FR-1 is absent:
    assert "FR-1" not in [fid for fid, _ in doc.used_ids["FR"]]


def test_reference_prefixes_param_skips_configured() -> None:
    doc = parse_document("t.md", _body("Backlog RQ-123 and GAP-56."), frozenset({"RQ", "GAP"}))
    assert "RQ" not in doc.used_ids
    assert "GAP" not in doc.used_ids
