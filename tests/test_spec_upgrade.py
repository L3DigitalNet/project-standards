from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.commands.upgrade import (  # pyright: ignore[reportPrivateUsage]
    _merge_top,  # pyright: ignore[reportPrivateUsage]
    _present_top_keys,  # pyright: ignore[reportPrivateUsage]
    _reconcile_shared,  # pyright: ignore[reportPrivateUsage]
    _rewrite_h1_suffix,  # pyright: ignore[reportPrivateUsage]
    _set_profile,  # pyright: ignore[reportPrivateUsage]
    _sub_blocks,  # pyright: ignore[reportPrivateUsage]
    _top_blocks,  # pyright: ignore[reportPrivateUsage]
    upgrade_text,
)
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import TEMPLATES_DIR, TIER_FILES, load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _tmpl(tier: str) -> str:
    return (TEMPLATES_DIR / TIER_FILES[tier]).read_text(encoding="utf-8")


def test_set_profile_rewrites_only_the_profile_line() -> None:
    text = "---\nspec_id: SPEC-UP01\nprofile: light\nowner: 'me'\n---\n\nbody\n"
    out = _set_profile(text, "standard")
    assert "profile: standard\n" in out
    assert "spec_id: SPEC-UP01\n" in out  # other frontmatter untouched
    assert "owner: 'me'\n" in out
    assert out.endswith("body\n")


def test_rewrite_h1_suffix_changes_tier_word_only() -> None:
    text = "# `My Project` — Specification (Light)\n\n## 1. Purpose\n"
    out = _rewrite_h1_suffix(text, "standard")
    assert out.startswith("# `My Project` — Specification (Standard)\n")


def test_rewrite_h1_suffix_supports_full_tier() -> None:
    text = "# `My Project` — Specification (Standard)\n\n## 1. Purpose\n"
    out = _rewrite_h1_suffix(text, "full")
    assert out.startswith("# `My Project` — Specification (Full)\n")


def test_rewrite_h1_suffix_ignores_h1_shaped_line_mid_body() -> None:
    # A mid-line H1-shaped mention in the body must NOT be rewritten (line-anchored).
    text = (
        "# `My Project` — Specification (Light)\n\n"
        "## 1. Purpose\n\n"
        "Inline mention: # `X` — Specification (Light) stays verbatim.\n"
    )
    out = _rewrite_h1_suffix(text, "standard")
    assert out.startswith("# `My Project` — Specification (Standard)\n")
    assert "Inline mention: # `X` — Specification (Light) stays verbatim." in out


def test_rewrite_h1_suffix_ignores_fenced_h1_example() -> None:
    text = "```markdown\n# `Example` — Specification (Light)\n```\n"

    assert _rewrite_h1_suffix(text, "standard") == text


def test_check_upgradeable_does_not_accept_a_fenced_h1_example() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    template = (
        "---\nprofile: light\n---\n"
        "# `Demo` — Specification (Light)\n\n"
        "## 1. Purpose\n\n"
        "Authored.\n\n"
        "```markdown\n# `Example` — Specification (Light)\n```\n"
    )
    source = template.replace("# `Demo` — Specification (Light)", "# Broken", 1)

    assert check_upgradeable(source, template) is not None


def test_upgrade_preserves_fenced_appendix_anchor_example() -> None:
    source = (
        "---\nprofile: light\n---\n"
        "# `Demo` — Specification (Light)\n\n"
        "[Live Appendix D](#appendix-d-upgrading-this-spec)\n\n"
        "## 1. Purpose\n\n"
        "```markdown\n"
        "[Example Appendix D](#appendix-d-upgrading-this-spec)\n"
        "```\n"
    )
    target = (
        "---\nprofile: standard\n---\n"
        "# `Demo` — Specification (Standard)\n\n"
        "## 1. Purpose\n\n"
        "Stub.\n\n"
        "## Appendix D: Tailoring\n\n"
        "Donor.\n"
    )

    out = upgrade_text(source, target, target_tier="standard")

    assert "[Live Appendix D](#appendix-d-tailoring)" in out
    assert "[Example Appendix D](#appendix-d-upgrading-this-spec)" in out


def test_top_blocks_splits_on_h2_and_keys_by_canonical_identity() -> None:
    body = (
        "# `T` — Specification (Light)\n\npreamble\n\n"
        "## 1. Purpose\n\np\n\n"
        "## References\n\nr\n\n"
        "## Appendix A: ID Conventions\n\na\n"
    )
    blocks = _top_blocks(body)
    keys = [k for k, _ in blocks]
    assert keys == ["", "1", "references", "appendix-A"]
    assert blocks[1][1].startswith("## 1. Purpose")
    assert blocks[0][1].startswith("# `T`")  # preamble preserved under key ""


def test_present_top_keys_lists_numbered_sections() -> None:
    body = "## 1. Purpose\n\n## 2. Scope\n\n## 7. Requirements\n"
    assert _present_top_keys(body) == ["1", "2", "7"]


def test_top_blocks_ignores_headings_inside_code_fences() -> None:
    # A spec section body may contain a Markdown/code example with heading-looking
    # lines; those must NOT be treated as section boundaries (Codex CR-003).
    body = "## 1. Purpose\n\n```markdown\n## Not A Heading\n### Also Not\n```\n\n## 2. Scope\n\nx\n"
    assert [k for k, _ in _top_blocks(body)] == ["1", "2"]


def test_top_blocks_handles_nested_and_mixed_fences() -> None:
    # CommonMark: a fence closes only on a same-character run at least as long as the
    # opener. A 4-backtick fence is not closed by an inner ```; a ``` fence is not
    # closed by ~~~ (Codex CR-003, mirroring validate_frontmatter's fence model).
    body = (
        "## 1. Purpose\n\n"
        "````markdown\n```\n## Inner Backtick\n```\n````\n\n"  # inner ``` does NOT close ````
        "## 2. Scope\n\n"
        "```\n~~~\n### Inner Tilde\n~~~\n```\n\n"  # ~~~ does NOT close ```
        "## 7. Requirements\n"
    )
    assert [k for k, _ in _top_blocks(body)] == ["1", "2", "7"]


def test_top_blocks_fence_indent_and_info_string_rules() -> None:
    # CommonMark: a 4-space-indented ``` is indented code, not a fence opener; and a
    # closing-looking ```lang line carries an info string, so it does NOT close a
    # backtick fence (Codex CR-003, mirroring validate_frontmatter's close rule).
    body = (
        "## 1. Purpose\n\n"
        "    ```\n"  # 4-space indent → not a fence
        "## 2. Scope\n\n"
        "```\n## Inside\n```lang\n## Still Inside\n```\n\n"  # ```lang has info → not a closer
        "## 7. Requirements\n"
    )
    assert [k for k, _ in _top_blocks(body)] == ["1", "2", "7"]


def test_merge_top_inserts_missing_section_and_keeps_author_block() -> None:
    source = "# `T` — Specification (Light)\n\n## 1. Purpose\n\nAUTHORED\n\n## 7. Requirements\n\nFR stuff\n"
    target = (
        "# `X` — Specification (Standard)\n\n## 1. Purpose\n\nstub\n\n"
        "## 3. Context\n\ncontext stub\n\n## 7. Requirements\n\nreq stub\n"
    )
    out = _merge_top(source, target)
    assert "AUTHORED" in out  # source's §1 kept verbatim
    assert "FR stuff" in out  # source's §7 kept verbatim
    assert "## 3. Context" in out  # target's §3 inserted
    assert "context stub" in out
    assert out.index("## 1. Purpose") < out.index("## 3. Context") < out.index("## 7. Requirements")


def test_reconcile_drops_stale_omission_note_tail() -> None:
    source = (
        "## 2. Scope\n\nAUTHORED scope\n\n---\n\n"
        "> **Sections §3–§6 are Standard/Full-tier** and are intentionally omitted "  # noqa: RUF001
        "at the Light profile.\n\n"
    )
    target = "## 2. Scope\n\nscope stub\n\n---\n\n"
    out = _reconcile_shared(source, target)
    assert "AUTHORED scope" in out  # author body kept
    assert "intentionally omitted" not in out  # stale tail dropped (target tail used)


def test_reconcile_inserts_missing_subsections_and_drops_reduction_note() -> None:
    source = (
        "## 7. Requirements\n\n"
        "> At the Light profile, Requirements is functional-only (§7.1). "
        "§7.2–§7.4 are Standard-tier.\n\n"  # noqa: RUF001
        "### 7.1 Functional Requirements\n\nAUTHORED FR TABLE\n\n"
    )
    target = (
        "## 7. Requirements\n\n"
        "> **Quality rule:** one testable statement.\n\n"
        "### 7.1 Functional Requirements\n\nstub\n\n"
        "### 7.2 Non-Functional Requirements\n\nnfr stub\n\n"
    )
    out = _reconcile_shared(source, target)
    assert "AUTHORED FR TABLE" in out  # source §7.1 kept
    assert "### 7.2 Non-Functional" in out  # target §7.2 inserted
    assert "functional-only" not in out  # reduction note dropped
    assert "Quality rule" in out  # target intro used


def test_reconcile_takes_tier_variant_subsection_17_1_from_target() -> None:
    source = (
        "## 17. Testing and Acceptance\n\n"
        "> At the Light profile, this is the Definition of Done only (§17.1).\n\n"
        "### 17.1 Definition of Done\n\n- [ ] LIGHT dod item\n\n---\n\n"
    )
    target = (
        "## 17. Testing and Acceptance\n\n"
        "### 17.1 Definition of Done\n\n- [ ] STANDARD dod item\n\n"
        "### 17.2 Test Strategy\n\nstub\n\n"
        "### 17.3 Traceability\n\nstub\n\n---\n\n"
    )
    out = _reconcile_shared(source, target)
    assert "STANDARD dod item" in out  # §17.1 taken from TARGET (tier-variant boilerplate)
    assert "LIGHT dod item" not in out  # light's DoD dropped
    assert "### 17.2 Test Strategy" in out  # missing subsection inserted
    assert "At the Light profile" not in out  # reduction-note intro dropped (target intro used)


def test_reconcile_drops_trailing_omission_note_on_last_source_subsection() -> None:
    source = (
        "## 7. Requirements\n\n"
        "### 7.1 Functional Requirements\n\nAUTHORED FR TABLE\n\n---\n\n"
        "> **Sections §8–§16 are Standard/Full-tier** and are intentionally omitted at the Light profile.\n\n"  # noqa: RUF001
    )
    target = (
        "## 7. Requirements\n\n"
        "### 7.1 Functional Requirements\n\nstub\n\n"
        "### 7.2 Non-Functional Requirements\n\nnfr stub\n\n"
    )
    out = _reconcile_shared(source, target)
    assert "AUTHORED FR TABLE" in out  # author body kept
    assert "### 7.2 Non-Functional" in out  # inserted subsection present
    assert "intentionally omitted" not in out  # stale trailing note dropped (target tail used)
    assert "§8–§16" not in out  # noqa: RUF001


@pytest.mark.parametrize(
    ("src", "tier", "want"),
    [
        ("upgrade_light.md", "standard", "upgrade_standard.md"),
        ("upgrade_light.md", "full", "upgrade_full.md"),
        ("upgrade_standard.md", "full", "upgrade_full.md"),
    ],
)
def test_upgrade_round_trip_is_byte_identical_to_target_fixture(
    src: str, tier: str, want: str
) -> None:
    out = upgrade_text((_FIX / src).read_text(encoding="utf-8"), _tmpl(tier), target_tier=tier)
    assert out == (_FIX / want).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("src", "tier"),
    [
        ("upgrade_light.md", "standard"),
        ("upgrade_light.md", "full"),
        ("upgrade_standard.md", "full"),
    ],
)
def test_upgrade_output_validates(src: str, tier: str) -> None:
    out = upgrade_text((_FIX / src).read_text(encoding="utf-8"), _tmpl(tier), target_tier=tier)
    assert validate_document(parse_document("<out>", out), load_registry()) == []


def test_check_upgradeable_accepts_a_canonical_source() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    assert check_upgradeable(light, _tmpl("light")) is None


def test_check_upgradeable_rejects_gap_prose() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace(
        "## 7. Requirements", "Author prose in a gap.\n\n## 7. Requirements", 1
    )
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_rejects_non_canonical_subsection() -> None:
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace("## 17. ", "### 7.3 Interface Requirements\n\nx\n\n## 17. ", 1)
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_rejects_edited_appendix_b() -> None:
    # Appendix B is template-owned (SA-NEW-001); an author edit makes the reshape differ.
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace(
        "### B.1 Implementation Rules", "### B.1 Implementation Rules\n\nAuthor-added rule.", 1
    )
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_rejects_wrong_h1_tier_suffix() -> None:
    # A validate-clean Light spec whose H1 wrongly says (Standard) must be refused —
    # the reshape takes the H1 from the source, so only the explicit H1 check catches it
    # (Codex CR-001). validate never inspects the H1.
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace("— Specification (Light)", "— Specification (Standard)", 1)
    assert check_upgradeable(tampered, _tmpl("light")) is not None


def test_check_upgradeable_accepts_fenced_heading_in_a_section_body() -> None:
    # A code fence containing heading-looking lines inside an authored section body is
    # legitimate and must NOT make the source non-upgradeable (fence-aware segmentation).
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    tampered = light.replace(
        "### 7.1 Functional Requirements",
        "### 7.1 Functional Requirements\n\n```markdown\n## Example\n```",
        1,
    )
    assert check_upgradeable(tampered, _tmpl("light")) is None


def test_check_upgradeable_rejects_noncanonical_trailing_blockquote_in_kept_subsection() -> None:
    # A validate-clean source whose kept §7.1 ends in an author blockquote that _is_filler
    # would trim must be refused (reshape differs) — proving no silent author-content loss.
    #
    # The note must land in §7.1's TRAILING FILLER RUN — contiguous with the existing
    # blank/"---"/omission-note lines right before "## 17." — not merely somewhere inside
    # the subsection body. `_swap_tail` only rewrites a block's trailing filler run (the
    # maximal suffix `_is_filler` matches), so a filler-shaped blockquote placed mid-body
    # (e.g. immediately after the "### 7.1" heading, before the FR table) survives
    # untouched and the reshape stays identical. Placed in the trailing run, it gets
    # swept up in the same backward scan as the genuine filler and silently dropped by
    # the real splice — which is exactly what this precheck must catch first.
    from project_standards.specs.commands.upgrade import check_upgradeable

    light = (_FIX / "upgrade_light.md").read_text(encoding="utf-8")
    anchor = "at the Light profile.\n\n## 17. Testing and Acceptance"
    assert anchor in light  # guard: fixture text the tampering depends on still exists
    tampered = light.replace(
        anchor,
        "at the Light profile.\n\n"
        "> Note: nothing is Standard-tier here, none omitted.\n\n"
        "## 17. Testing and Acceptance",
        1,
    )
    assert check_upgradeable(tampered, _tmpl("light")) is not None


@pytest.mark.parametrize(
    ("lo", "hi"),
    [("light", "standard"), ("light", "full"), ("standard", "full")],
)
def test_no_section_gains_first_subsection_across_a_tier_boundary(lo: str, hi: str) -> None:
    """Pin an unenforced template-structure invariant the upgrade precheck's U2
    soundness silently depends on: no top-level numbered section may be
    un-subsectioned (zero ``### `` subsections) at a lower tier but subsectioned
    (>=1) at a higher tier.

    A section may gain MORE subsections across tiers (light §7 has only §7.1;
    standard adds §7.2-§7.4) — that's fine, the source already has >=1. The
    forbidden transition is 0 -> N: if a future template edit ever gave a
    section its FIRST subsection across a tier boundary, `_reconcile_shared`'s
    ``key == ""`` branch would take the higher tier's (target's) short intro
    unconditionally, silently dropping the lower tier's entire un-subsectioned
    section body — the reshape-identity precheck (`check_upgradeable`) would no
    longer be a true superset of the splice's mutations for that section, and
    real author content could be lost with no refusal. This test fails loudly
    the moment the invariant is violated, instead of the splice losing bytes
    quietly.
    """
    lo_body = _tmpl(lo)
    hi_body = _tmpl(hi)
    lo_blocks = dict(_top_blocks(lo_body))
    hi_blocks = dict(_top_blocks(hi_body))
    shared_keys = set(_present_top_keys(lo_body)) & set(_present_top_keys(hi_body))
    for key in sorted(shared_keys):
        lo_has_subs = any(k for k, _ in _sub_blocks(lo_blocks[key]) if k)
        hi_has_subs = any(k for k, _ in _sub_blocks(hi_blocks[key]) if k)
        if not lo_has_subs:
            assert not hi_has_subs, (
                f"section {key}: un-subsectioned at {lo} but subsectioned at {hi} — "
                "would silently drop author body in _reconcile_shared (U2 risk); "
                "update _reconcile_shared's key=='' path before adding such a section"
            )
