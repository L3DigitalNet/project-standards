"""Unit tests for the pure `spec new` core (no I/O, injected nondeterminism)."""

from __future__ import annotations

import random
import re
from datetime import date

import pytest
import yaml

from project_standards.specs.commands.new import (
    FieldValueError,
    NewOptions,
    SpecIdExhausted,
    check_field,
    emit_scalar,
    mint_spec_id,
    scaffold,
)
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import (
    SPEC_ID_PATTERN,
    TEMPLATES_DIR,
    TIER_FILES,
    load_registry,
)


@pytest.mark.parametrize(
    "value", ["O'Brien", "Ratio 1:2", "weight #1", "café", "a `b`", "  spaced  "]
)
def test_emit_scalar_round_trips(value: str) -> None:
    rendered = emit_scalar(value)
    assert yaml.safe_load(f"x: {rendered}") == {"x": value}


@pytest.mark.parametrize("value", ["", "line\none", "tab\there", "cr\rhere"])
def test_check_field_rejects_bad_values(value: str) -> None:
    with pytest.raises(FieldValueError):
        check_field("owner", value, is_title=False)


def test_check_field_title_rejects_backtick_but_owner_allows_it() -> None:
    with pytest.raises(FieldValueError):
        check_field("title", "Use `uv`", is_title=True)
    check_field("owner", "team `core`", is_title=False)  # no raise


def test_check_field_accepts_ordinary_values() -> None:
    check_field("title", "Checkout Service", is_title=True)
    check_field("implementer", "coding agent", is_title=False)


def test_mint_matches_pattern_and_is_deterministic_per_seed() -> None:
    first = mint_spec_id(random.Random(0), set[str]())
    again = mint_spec_id(random.Random(0), set[str]())
    assert re.match(SPEC_ID_PATTERN, first)
    assert first == again  # same seed, same id -> injected RNG is the only nondeterminism


def test_mint_retries_past_a_collision() -> None:
    taken = mint_spec_id(random.Random(0), set[str]())
    other = mint_spec_id(random.Random(0), {taken})
    assert other != taken
    assert re.match(SPEC_ID_PATTERN, other)


def test_mint_exhaustion_raises() -> None:
    # Reproduce the seed-0 first candidate, then demand a fresh id in exactly 1 attempt
    # while that id is already taken -> the single attempt collides -> exhausted.
    taken = mint_spec_id(random.Random(0), set[str]())
    with pytest.raises(SpecIdExhausted):
        mint_spec_id(random.Random(0), {taken}, attempts=1)


_TODAY = date(2026, 7, 4)


def _template(tier: str) -> str:
    return (TEMPLATES_DIR / TIER_FILES[tier]).read_text(encoding="utf-8")


def _opts(
    tier: str,
    *,
    spec_id: str = "SPEC-7F3Q",
    title: str | None = None,
    owner: str | None = None,
    implementer: str | None = None,
) -> NewOptions:
    return NewOptions(
        profile=tier, spec_id=spec_id, title=title, owner=owner, implementer=implementer
    )


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_fills_machine_fields_and_drops_sentinel_comment(tier: str) -> None:
    out = scaffold(_template(tier), _opts(tier), today=_TODAY)
    assert "spec_id: SPEC-7F3Q\n" in out
    assert "SPEC-____" not in out
    assert "created: '2026-07-04'\n" in out
    assert "last_reviewed: '2026-07-04'\n" in out


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_keeps_placeholders_when_flags_omitted(tier: str) -> None:
    out = scaffold(_template(tier), _opts(tier), today=_TODAY)
    assert "title: '<Project / Feature Name>'\n" in out
    assert "owner: '<person or team>'\n" in out


def test_scaffold_fills_provided_fields_and_rewrites_h1() -> None:
    out = scaffold(
        _template("standard"),
        _opts("standard", title="Checkout Service", owner="Payments team"),
        today=_TODAY,
    )
    assert "title: 'Checkout Service'\n" in out
    assert "owner: 'Payments team'\n" in out
    assert "# `Checkout Service` — Specification (Standard)\n" in out


def test_scaffold_only_rewrites_h1_with_title() -> None:
    out = scaffold(_template("standard"), _opts("standard"), today=_TODAY)
    assert "# `<Project / Feature Name>` — Specification (Standard)\n" in out


@pytest.mark.parametrize("tier", list(TIER_FILES))
@pytest.mark.parametrize("filled", [False, True])
def test_scaffold_output_validates_clean(tier: str, filled: bool) -> None:
    opts = _opts(tier, title="T", owner="O", implementer="I") if filled else _opts(tier)
    out = scaffold(_template(tier), opts, today=_TODAY)
    findings = validate_document(parse_document("new.md", out), load_registry())
    assert findings == []  # spec invariant I1


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_leaves_body_below_frontmatter_untouched(tier: str) -> None:
    template = _template(tier)
    out = scaffold(template, _opts(tier), today=_TODAY)
    # No --title -> even the H1 is unchanged, so from the first '## ' heading onward the
    # output is byte-identical to the template (I4).
    marker = "\n## "
    assert template[template.index(marker) :] == out[out.index(marker) :]


@pytest.mark.parametrize("tier", list(TIER_FILES))
def test_scaffold_with_title_leaves_body_untouched(tier: str) -> None:
    # I4 holds even when --title rewrites the H1: the H1 sits ABOVE the first "## "
    # marker, so from that marker onward the output must stay byte-identical to the template.
    template = _template(tier)
    out = scaffold(_template(tier), _opts(tier, title="Checkout Service"), today=_TODAY)
    marker = "\n## "
    assert template[template.index(marker) :] == out[out.index(marker) :]
