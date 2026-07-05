"""Unit tests for the pure `spec new` core (no I/O, injected nondeterminism)."""

from __future__ import annotations

import random
import re

import pytest
import yaml

from project_standards.specs.commands.new import (
    FieldValueError,
    SpecIdExhausted,
    check_field,
    emit_scalar,
    mint_spec_id,
)
from project_standards.specs.registry import SPEC_ID_PATTERN


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
