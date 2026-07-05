"""Bundled spec templates stay byte-identical to the canonical copies."""

from __future__ import annotations

from pathlib import Path

import pytest

_TIERS = ("light", "standard", "full")
_ROOT = Path(__file__).resolve().parent.parent
_PKG = _ROOT / "src" / "project_standards" / "specs" / "templates"
_CANON = _ROOT / "standards" / "project-spec" / "templates"


@pytest.mark.parametrize("tier", _TIERS)
def test_bundled_template_is_byte_identical(tier: str) -> None:
    name = f"spec-{tier}-template.md"
    assert (_PKG / name).read_bytes() == (_CANON / name).read_bytes()


def test_templates_resolve_from_package_root() -> None:
    from project_standards import specs

    tdir = Path(specs.__file__).resolve().parent / "templates"
    assert sorted(p.name for p in tdir.glob("*.md")) == [
        "spec-full-template.md",
        "spec-light-template.md",
        "spec-standard-template.md",
    ]
