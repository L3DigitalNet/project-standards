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


def test_license_tokens_excluded_from_used_ids() -> None:
    """SPDX license identifiers must not be parsed as spec-local IDs (F4)."""
    # Single-digit forms covered by NOT_AN_ID; dotted forms (MPL-2.0) covered by lookahead
    doc = parse_document(
        "x.md",
        "---\n\n---\n# t\nDependency licensed under MPL-2, GPL-3, LGPL-2, AGPL-3, BSD-3.\n",
    )
    for pfx in ("MPL", "GPL", "LGPL", "AGPL", "BSD"):
        assert pfx not in doc.used_ids, f"{pfx} should be in NOT_AN_ID"
    # Dotted versions — also excluded by NOT_AN_ID and the lookahead
    doc2 = parse_document(
        "x.md",
        "---\n\n---\n# t\nMPL-2.0 or GPL-3.0 or LGPL-2.1 licensed. FR-001 is still matched.\n",
    )
    for pfx in ("MPL", "GPL", "LGPL"):
        assert pfx not in doc2.used_ids, f"dotted {pfx}-N.M should not produce an ID token"
    assert "FR" in doc2.used_ids


def test_spdx_version_string_excluded_by_lookahead() -> None:
    """MPL-2.0 / GPL-3.0 style tokens are excluded by the regex lookahead (F4)."""
    # MPL/GPL/LGPL are in NOT_AN_ID, so use a synthetic prefix to isolate the lookahead.
    doc = parse_document(
        "x.md",
        "---\n\n---\n# t\nLicense ZZ-2.0 (version string). ZZ-001 is a real ID.\n",
    )
    zz_ids = [fid for fid, _ in doc.used_ids.get("ZZ", [])]
    assert "ZZ-2" not in zz_ids, (
        "ZZ-2 from ZZ-2.0 should be excluded by the version-string lookahead"
    )
    assert "ZZ-001" in zz_ids, "ZZ-001 must still be matched"


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
