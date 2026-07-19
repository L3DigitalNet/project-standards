import re

from project_standards.id_format import random_token, slugify


def test_slugify_basic() -> None:
    assert slugify("Tailscale ACL tag ordering gotcha") == "tailscale-acl-tag-ordering-gotcha"


def test_slugify_strips_accents_and_punctuation() -> None:
    assert (
        slugify("Standards Adoption & Compliance Procedure")
        == "standards-adoption-compliance-procedure"
    )
    assert slugify("café déjà") == "cafe-deja"


def test_slugify_empty_for_symbol_only() -> None:
    assert slugify("!!!") == ""


def test_random_token_is_six_base36_chars() -> None:
    tok = random_token()
    assert re.fullmatch(r"[0-9a-z]{6}", tok)


def test_random_token_varies() -> None:
    assert len({random_token() for _ in range(50)}) > 1


def test_slugify_caps_long_titles_at_word_boundary() -> None:
    # Generated slugs are bounded so --fix on a long title cannot mint an
    # unwieldy id (F26); the cut must land between words, never mid-word.
    long_title = "word " * 30  # 150-char slug if uncapped
    slug = slugify(long_title.strip())
    assert len(slug) <= 60
    assert not slug.endswith("-")
    assert set(slug.split("-")) == {"word"}  # only whole words survive


def test_slugify_single_long_token_hard_truncates() -> None:
    # No word boundary exists inside one unbroken token — hard truncation is the
    # only option and must still respect the cap.
    slug = slugify("x" * 100)
    assert slug == "x" * 60


def test_slugify_short_titles_unchanged() -> None:
    assert slugify("Tailscale ACL Tag") == "tailscale-acl-tag"
