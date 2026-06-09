import re
from project_standards.id_format import slugify, random_token


def test_slugify_basic():
    assert slugify("Tailscale ACL tag ordering gotcha") == "tailscale-acl-tag-ordering-gotcha"


def test_slugify_strips_accents_and_punctuation():
    assert slugify("Standards Adoption & Compliance Procedure") == "standards-adoption-compliance-procedure"
    assert slugify("café déjà") == "cafe-deja"


def test_slugify_empty_for_symbol_only():
    assert slugify("!!!") == ""


def test_random_token_is_six_base36_chars():
    tok = random_token()
    assert re.fullmatch(r"[0-9a-z]{6}", tok)


def test_random_token_varies():
    assert len({random_token() for _ in range(50)}) > 1
