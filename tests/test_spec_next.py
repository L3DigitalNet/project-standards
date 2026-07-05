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
