from __future__ import annotations

from project_standards.specs.registry import load_registry


def test_canonical_sections_include_full_ladder() -> None:
    reg = load_registry()
    for n in ("1", "2", "7", "7.1", "17", "21"):
        assert n in reg.canonical_sections
    assert reg.tier_sections["light"] <= reg.tier_sections["standard"]
    assert reg.tier_sections["standard"] <= reg.tier_sections["full"]


def test_prefix_defined_in_and_tier_availability() -> None:
    reg = load_registry()
    assert "7.1" in reg.prefix_defined_in["FR"]
    assert "R" in reg.tier_prefixes["full"]
    assert "R" not in reg.tier_prefixes["standard"]
    assert "R" not in reg.tier_prefixes["light"]


def test_appendix_c_is_full_only() -> None:
    reg = load_registry()
    assert "C" in reg.full_only_appendices
    assert reg.frontmatter_keys[0] == "spec_id"
    assert reg.sentinel == "SPEC-____"
