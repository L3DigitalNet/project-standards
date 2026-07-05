from __future__ import annotations

from project_standards.specs.commands.upgrade import (  # pyright: ignore[reportPrivateUsage]
    _rewrite_h1_suffix,  # pyright: ignore[reportPrivateUsage]
    _set_profile,  # pyright: ignore[reportPrivateUsage]
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
