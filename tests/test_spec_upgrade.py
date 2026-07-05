from __future__ import annotations

from project_standards.specs.commands.upgrade import (  # pyright: ignore[reportPrivateUsage]
    _merge_top,  # pyright: ignore[reportPrivateUsage]
    _present_top_keys,  # pyright: ignore[reportPrivateUsage]
    _reconcile_shared,  # pyright: ignore[reportPrivateUsage]
    _rewrite_h1_suffix,  # pyright: ignore[reportPrivateUsage]
    _set_profile,  # pyright: ignore[reportPrivateUsage]
    _top_blocks,  # pyright: ignore[reportPrivateUsage]
)


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
