# tests/test_spec_upgrade_fixtures.py
from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


@pytest.mark.parametrize(
    ("name", "profile"),
    [
        ("upgrade_light.md", "light"),
        ("upgrade_standard.md", "standard"),
        ("upgrade_full.md", "full"),
    ],
)
def test_upgrade_fixture_is_valid_at_its_tier(name: str, profile: str) -> None:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    assert doc.profile == profile
    assert validate_document(doc, load_registry()) == []
