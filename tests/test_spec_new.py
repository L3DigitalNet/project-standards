"""Unit tests for the pure `spec new` core (no I/O, injected nondeterminism)."""

from __future__ import annotations

import pytest
import yaml

from project_standards.specs.commands.new import (
    FieldValueError,
    check_field,
    emit_scalar,
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
