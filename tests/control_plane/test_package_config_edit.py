from __future__ import annotations

import tomllib
from collections.abc import Callable
from typing import cast

import pytest

from project_standards.control_plane import config_edit
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.package_contract.payload import JsonObject

type ConfigTransformRenderer = Callable[
    [bytes, str, JsonObject, tuple[str, ...]],
    bytes,
]

_TRANSFORMED_CONFIG: JsonObject = {
    "ci": {"enabled": True, "performance": True},
    "keep": "consumer",
}

_TABLE_EXISTING = b"""# owner preamble
[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "1.8"

[standards.python-tooling.config]
keep = "consumer" # unrelated

[standards.python-tooling.config.ci]
enabled = true
performance = false # owned

[standards.zeta]
enabled = false
version = "latest"
"""

_DOTTED_EXISTING = b"""# compact owner layout
project_standards.schema_version = "1.0"
project_standards.catalog = "5"
standards.python-tooling.enabled = true
standards.python-tooling.version = "1.8"
standards.python-tooling.config.keep = "consumer" # unrelated
standards.python-tooling.config.ci.enabled = true
standards.python-tooling.config.ci.performance = false # owned
standards.zeta.enabled = false
standards.zeta.version = "latest"
"""

_INLINE_EXISTING = b"""# inline owner layout
project_standards = { schema_version = "1.0", catalog = "5" }
standards.python-tooling = { enabled = true, version = "1.8", config = { keep = "consumer", ci = { enabled = true, performance = false } } } # retained
standards.zeta = { enabled = false, version = "latest" }
"""

_TABLE_MISSING = _TABLE_EXISTING.replace(b"performance = false # owned\n", b"")
_DOTTED_MISSING = _DOTTED_EXISTING.replace(
    b"standards.python-tooling.config.ci.performance = false # owned\n",
    b"",
)
_INLINE_MISSING = _INLINE_EXISTING.replace(b", performance = false", b"")
_TABLE_MISSING_CONTAINER = _TABLE_EXISTING.replace(
    b"\n[standards.python-tooling.config.ci]\nenabled = true\nperformance = false # owned\n",
    b"",
)
_DOTTED_MISSING_CONTAINER = _DOTTED_EXISTING.replace(
    b"standards.python-tooling.config.ci.enabled = true\n"
    b"standards.python-tooling.config.ci.performance = false # owned\n",
    b"",
)
_INLINE_MISSING_CONTAINER = _INLINE_EXISTING.replace(
    b", ci = { enabled = true, performance = false }",
    b"",
)
_CONTAINER_TRANSFORMED_CONFIG: JsonObject = {
    "ci": {"performance": True},
    "keep": "consumer",
}
_MULTI_LEAF_TRANSFORMED_CONFIG: JsonObject = {
    "ci": {"performance": True, "smoke": False},
    "keep": "consumer",
}
_INLINE_EMPTY_CONTAINER = _INLINE_MISSING_CONTAINER.replace(
    b'config = { keep = "consumer"',
    b'config = { keep = "consumer", ci = {}',
)
_INLINE_DOTTED_CONTAINER = _INLINE_MISSING_CONTAINER.replace(
    b'config = { keep = "consumer"',
    b'config = { keep = "consumer", ci.enabled = true',
)
_ESCAPED_KEY_CONFIG = b"""[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "1.8"

[standards.python-tooling.config]
keep = "consumer"
"a/b" = false
"""
_ESCAPED_KEY_CREATE_CONFIG = _ESCAPED_KEY_CONFIG.replace(b'"a/b" = false\n', b"")


def _render(
    original: bytes,
    transformed_config: JsonObject = _TRANSFORMED_CONFIG,
    declared_pointers: tuple[str, ...] = ("/ci/performance",),
) -> bytes:
    renderer = cast(
        ConfigTransformRenderer,
        config_edit.__dict__["render_package_config_transform"],
    )
    return renderer(
        original,
        "python-tooling",
        transformed_config,
        declared_pointers,
    )


def _package_config(content: bytes) -> dict[str, object]:
    parsed = tomllib.loads(content.decode("utf-8"))
    standards = cast("dict[str, object]", parsed["standards"])
    package = cast("dict[str, object]", standards["python-tooling"])
    return cast("dict[str, object]", package["config"])


@pytest.mark.parametrize(
    "original",
    [_TABLE_EXISTING, _DOTTED_EXISTING, _INLINE_EXISTING],
    ids=["table", "dotted", "nested-inline"],
)
def test_existing_performance_leaf_is_the_only_lexical_change(original: bytes) -> None:
    expected = original.replace(b"performance = false", b"performance = true")

    updated = _render(original)

    assert updated == expected
    assert _package_config(updated) == _TRANSFORMED_CONFIG
    assert _render(updated) == updated


@pytest.mark.parametrize(
    ("original", "inserted"),
    [
        (_TABLE_MISSING, b"performance = true\n"),
        (
            _DOTTED_MISSING,
            b"standards.python-tooling.config.ci.performance = true\n",
        ),
        (_INLINE_MISSING, b", performance = true"),
    ],
    ids=["table", "dotted", "nested-inline"],
)
def test_missing_performance_leaf_is_one_bounded_lexical_insertion(
    original: bytes,
    inserted: bytes,
) -> None:
    updated = _render(original)

    assert updated.count(inserted) == 1
    assert updated.replace(inserted, b"", 1) == original
    assert _package_config(updated) == _TRANSFORMED_CONFIG
    assert _render(updated) == updated
    assert updated.index(inserted) < updated.index(b"standards.zeta")


@pytest.mark.parametrize(
    "original",
    [_TABLE_MISSING_CONTAINER, _DOTTED_MISSING_CONTAINER, _INLINE_MISSING_CONTAINER],
    ids=["table", "dotted", "nested-inline"],
)
def test_missing_intermediate_container_counts_as_only_the_declared_leaf(
    original: bytes,
) -> None:
    updated = _render(original, _CONTAINER_TRANSFORMED_CONFIG)

    assert _package_config(updated) == _CONTAINER_TRANSFORMED_CONFIG
    assert _render(updated, _CONTAINER_TRANSFORMED_CONFIG) == updated


@pytest.mark.parametrize(
    "original",
    [_INLINE_EMPTY_CONTAINER, _INLINE_MISSING_CONTAINER],
    ids=["empty-inline-container", "missing-inline-container"],
)
def test_multiple_missing_sibling_leaves_are_inserted_atomically(
    original: bytes,
) -> None:
    pointers = ("/ci/performance", "/ci/smoke")

    updated = _render(original, _MULTI_LEAF_TRANSFORMED_CONFIG, pointers)

    assert _package_config(updated) == _MULTI_LEAF_TRANSFORMED_CONFIG
    assert updated.count(b"performance = true") == 1
    assert updated.count(b"smoke = false") == 1
    assert _render(updated, _MULTI_LEAF_TRANSFORMED_CONFIG, pointers) == updated
    reversed_provider_order: JsonObject = {
        "keep": "consumer",
        "ci": {"smoke": False, "performance": True},
    }
    assert _render(original, reversed_provider_order, pointers) == updated


_INLINE_TIGHT_CONTAINER = _INLINE_MISSING_CONTAINER.replace(
    b'config = { keep = "consumer" }',
    b'config = {keep = "consumer"}',
)
_INLINE_BARE_EMPTY_CONTAINER = _INLINE_MISSING_CONTAINER.replace(
    b'config = { keep = "consumer" }',
    b"config = {}",
)
_INLINE_SPACED_EMPTY_CONTAINER = _INLINE_MISSING_CONTAINER.replace(
    b'config = { keep = "consumer" }',
    b"config = { }",
)
_EMPTY_TRANSFORMED_CONFIG: JsonObject = {"ci": {"performance": True}}


@pytest.mark.parametrize(
    ("original", "transformed", "before", "after"),
    [
        pytest.param(
            _INLINE_MISSING_CONTAINER,
            _CONTAINER_TRANSFORMED_CONFIG,
            b'config = { keep = "consumer" }',
            b'config = { keep = "consumer", ci = { performance = true } }',
            id="spaced-populated",
        ),
        pytest.param(
            _INLINE_TIGHT_CONTAINER,
            _CONTAINER_TRANSFORMED_CONFIG,
            b'config = {keep = "consumer"}',
            b'config = {keep = "consumer", ci = { performance = true }}',
            id="tight-populated",
        ),
        pytest.param(
            _INLINE_BARE_EMPTY_CONTAINER,
            _EMPTY_TRANSFORMED_CONFIG,
            b"config = {}",
            b"config = { ci = { performance = true } }",
            id="bare-empty",
        ),
        pytest.param(
            _INLINE_SPACED_EMPTY_CONTAINER,
            _EMPTY_TRANSFORMED_CONFIG,
            b"config = { }",
            b"config = { ci = { performance = true } }",
            id="spaced-empty",
        ),
    ],
)
def test_inline_insertion_keeps_reviewable_punctuation_and_is_idempotent(
    original: bytes,
    transformed: JsonObject,
    before: bytes,
    after: bytes,
) -> None:
    """Issue #79: no space before the comma and no crowded closing brace."""
    updated = _render(original, transformed)

    assert updated == original.replace(before, after)
    assert b" ," not in updated
    assert _package_config(updated) == transformed
    assert _render(updated, transformed) == updated


def test_missing_leaf_uses_existing_dotted_inline_container() -> None:
    transformed: JsonObject = {
        "ci": {"enabled": True, "performance": True},
        "keep": "consumer",
    }

    updated = _render(
        _INLINE_DOTTED_CONTAINER,
        transformed,
        ("/ci/performance",),
    )

    assert _package_config(updated) == transformed
    assert _render(updated, transformed, ("/ci/performance",)) == updated


def test_escaped_slash_key_is_updated_through_its_canonical_pointer() -> None:
    transformed: JsonObject = {"a/b": True, "keep": "consumer"}

    updated = _render(_ESCAPED_KEY_CONFIG, transformed, ("/a~1b",))

    assert _package_config(updated) == transformed
    assert _render(updated, transformed, ("/a~1b",)) == updated


def test_escaped_tilde_key_is_created_through_its_canonical_pointer() -> None:
    transformed: JsonObject = {"a~b": True, "keep": "consumer"}

    updated = _render(_ESCAPED_KEY_CREATE_CONFIG, transformed, ("/a~0b",))

    assert _package_config(updated) == transformed
    assert _render(updated, transformed, ("/a~0b",)) == updated


def test_transform_rejects_removing_a_declared_leaf() -> None:
    transformed: JsonObject = {
        "ci": {"enabled": True},
        "keep": "consumer",
    }

    with pytest.raises(ControlPlaneError, match="remove"):
        _render(_TABLE_EXISTING, transformed)


def test_transform_rejects_a_change_outside_the_declared_pointer() -> None:
    transformed: JsonObject = {
        "ci": {"enabled": False, "performance": True},
        "keep": "consumer",
    }

    with pytest.raises(ControlPlaneError, match="declared"):
        _render(_TABLE_EXISTING, transformed)


def test_changed_pointers_distinguish_json_booleans_from_numbers() -> None:
    changed = config_edit.changed_package_config_pointers(
        {"nested": {"value": 1}},
        {"nested": {"value": True}},
    )

    assert changed == ("/nested/value",)
