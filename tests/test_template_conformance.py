"""Maintainer dogfood: bundled templates are structurally sound."""

from __future__ import annotations

import pytest

from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, load_registry

_ALLOWED = {"SV-SENTINEL"}


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_template_has_no_structural_findings(tier: str) -> None:
    path = TEMPLATES_DIR / TIER_FILES[tier]
    doc = parse_document(str(path), path.read_text(encoding="utf-8"))
    codes = {f.code for f in validate_document(doc, load_registry())}
    assert codes <= _ALLOWED, f"unexpected structural findings: {codes - _ALLOWED}"
