from __future__ import annotations

import pytest

from project_standards.specs.registry import load_registry, split_front_matter


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


def test_frontmatter_closing_fence_at_eof_is_complete() -> None:
    frontmatter, body = split_front_matter("---\nspec_id: SPEC-0001\n---")

    assert frontmatter == "spec_id: SPEC-0001"
    assert body == ""

    with pytest.raises(ValueError, match="unterminated frontmatter fence"):
        split_front_matter("---\nspec_id: SPEC-0001\n# body")


def test_fence_mask_preserves_offsets_lines_and_outside_text() -> None:
    from project_standards.specs.registry import (
        _masked_structural_view,  # pyright: ignore[reportPrivateUsage]
    )

    text = "before\n```markdown\n## 99. Example\nRQ-123 and <placeholder>\n```\nafter\n"

    masked = _masked_structural_view(text)

    assert len(masked) == len(text)
    assert [i for i, char in enumerate(masked) if char == "\n"] == [
        i for i, char in enumerate(text) if char == "\n"
    ]
    assert masked.startswith("before\n")
    assert masked.endswith("after\n")
    assert all(not line.strip() for line in masked.splitlines()[1:5])


def test_fence_mask_crlf_and_cr_closers_restore_later_structure() -> None:
    from project_standards.specs.registry import (
        _masked_structural_view,  # pyright: ignore[reportPrivateUsage]
    )

    for newline in ("\r\n", "\r"):
        text = newline.join(("```markdown", "## 99. Example", "```", "## 1. Visible", ""))

        masked = _masked_structural_view(text)

        assert len(masked) == len(text)
        assert [(i, char) for i, char in enumerate(masked) if char in "\r\n"] == [
            (i, char) for i, char in enumerate(text) if char in "\r\n"
        ]
        assert "## 99. Example" not in masked
        assert f"## 1. Visible{newline}" in masked
