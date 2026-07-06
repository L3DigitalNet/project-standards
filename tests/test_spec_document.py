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


def test_skip_set_zero_config():
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


def test_reference_prefixes_param_skips_configured():
    doc = parse_document("t.md", _body("Backlog RQ-123 and GAP-56."), frozenset({"RQ", "GAP"}))
    assert "RQ" not in doc.used_ids
    assert "GAP" not in doc.used_ids
