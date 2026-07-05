from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.next_id import next_free_id
from project_standards.specs.document import parse_document
from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _doc(name: str = "valid_standard.md") -> SpecDocument:
    return parse_document(name, (_FIX / name).read_text(encoding="utf-8"))


def test_next_fr_is_zero_padded() -> None:
    nid = next_free_id(_doc(), load_registry(), "FR")
    assert nid.startswith("FR-") and len(nid.split("-")[1]) == 3


def test_unknown_prefix_raises() -> None:
    with pytest.raises(ValueError, match="unknown prefix"):
        next_free_id(_doc(), load_registry(), "ZZ")


def test_ms_is_single_digit() -> None:
    nid = next_free_id(_doc(), load_registry(), "MS")
    assert nid.startswith("MS-") and len(nid.split("-")[1]) == 1


def test_exhausted_three_digit_prefix_raises_instead_of_widening() -> None:
    doc = parse_document("x.md", "---\nprofile: full\n---\n# t\nFR-999 already exists.\n")
    with pytest.raises(ValueError, match="exhausted"):
        next_free_id(doc, load_registry(), "FR")


def test_exhausted_ms_raises_instead_of_widening() -> None:
    doc = parse_document("x.md", "---\nprofile: full\n---\n# t\nMS-9 already exists.\n")
    with pytest.raises(ValueError, match="exhausted"):
        next_free_id(doc, load_registry(), "MS")


def test_profile_less_doc_agrees_with_validate_tier_default() -> None:
    """`next` and `validate` must apply the same tier default for a profile-less doc.

    `R-` is declared only in the Full template's Appendix A, so a profile-less
    doc (``doc.profile is None``) must never be allowed to mint one — that
    would contradict `validate`'s own `SV-ID-TIER` rule, which uses the same
    empty-string tier default.
    """
    doc = parse_document("x.md", "---\n\n---\n# t\n")
    with pytest.raises(ValueError, match="not valid at None tier"):
        next_free_id(doc, load_registry(), "R")
