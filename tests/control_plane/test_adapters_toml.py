from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.base import UnitChange
from project_standards.control_plane.adapters.toml import TomlAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError

_FIXTURES = Path(__file__).parent / "fixtures/toml"


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _unit(adapter: TomlAdapter, content: bytes, scope: str):
    state = adapter.inspect(content, (scope,))
    assert len(state.units) == 1
    return state.units[0]


def test_toml_inspect_normalizes_key_and_table_scopes_without_losing_raw_bytes() -> None:
    content = _fixture("complex.toml")
    adapter = TomlAdapter()

    state = adapter.inspect(
        content,
        (
            "key:/tool/ruff/line-length",
            "key:/tool/coverage.py/branch",
            "table:/tool/ruff",
        ),
    )

    units = {unit.scope: unit for unit in state.units}
    assert units["key:/tool/ruff/line-length"].value == 88
    assert units["key:/tool/ruff/line-length"].raw == b"88"
    assert units["key:/tool/coverage.py/branch"].value is True
    table = units["table:/tool/ruff"]
    assert table.value == {
        "line-length": 88,
        "select": ["E", "F"],
        "message": "hash # and brackets [stay] inside the string\n",
        "inline": {"z": 1, "note": "x#y"},
        "lint": {"ignore": ["E501"]},
    }
    assert b'["tool".ruff]' in table.raw
    assert b"[tool.ruff.lint]" in table.raw


def test_toml_key_update_splices_only_the_value_and_is_idempotent() -> None:
    before = _fixture("complex.toml")
    adapter = TomlAdapter()
    state = adapter.inspect(before, ("key:/tool/ruff/line-length",))
    change = UnitChange(
        ActionKind.UPDATE,
        "key:/tool/ruff/line-length",
        content=b"100",
        value=100,
    )

    after = adapter.render(state, (change,))

    assert after == before.replace(b"88  # keep", b"100  # keep", 1)
    assert adapter.render(adapter.inspect(after, (change.scope,)), (change,)) == after


def test_toml_adopts_semantically_equal_value_without_rewriting_spelling() -> None:
    content = b"count = 1_000 # consumer spelling\n"
    adapter = TomlAdapter()
    scope = "key:/count"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.ADOPT, scope, content=b"1000", value=1000),),
    )

    assert after == content


def test_toml_render_preserves_crlf_and_comments() -> None:
    before = b"[tool.ruff]\r\nline-length = 88 # local\r\n\r\n[project]\r\nname='demo'\r\n"
    adapter = TomlAdapter()
    scope = "key:/tool/ruff/line-length"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.UPDATE, scope, content=b"99", value=99),),
    )

    assert after == before.replace(b"88 # local", b"99 # local")
    assert b"\r\n" in after
    assert b"\n" not in after.replace(b"\r\n", b"")


def test_toml_key_removal_preserves_comments_and_consumer_table_header() -> None:
    before = (
        b"[tool.demo]\n"
        b"# consumer explanation\n"
        b"owned = true  # retain inline note\n"
        b"\n[other]\nvalue = 1\n"
    )
    adapter = TomlAdapter()
    scope = "key:/tool/demo/owned"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert b"[tool.demo]" in after
    assert b"# consumer explanation" in after
    assert b"# retain inline note" in after
    assert b"owned" not in after
    assert tomllib.loads(after.decode())["tool"]["demo"] == {}
    assert after.endswith(b"\n[other]\nvalue = 1\n")


def test_toml_inserts_missing_root_parent_keys_and_tables_canonically() -> None:
    before = b"# root\n[tool]\nexisting = true\n\n[tail]\nvalue = 1\n"
    adapter = TomlAdapter()
    scopes = (
        "key:/tool/zeta",
        "table:/build-system",
        "key:/requires-python",
        "key:/tool/alpha",
    )
    state = adapter.inspect(before, scopes)
    changes = (
        UnitChange(ActionKind.CREATE, "key:/tool/zeta", content=b'"z"', value="z"),
        UnitChange(
            ActionKind.CREATE,
            "table:/build-system",
            content=b'[build-system]\nrequires = ["hatchling"]\n',
            value={"requires": ["hatchling"]},
        ),
        UnitChange(
            ActionKind.CREATE,
            "key:/requires-python",
            content=b'">=3.14"',
            value=">=3.14",
        ),
        UnitChange(ActionKind.CREATE, "key:/tool/alpha", content=b"1", value=1),
    )

    after = adapter.render(state, changes)

    assert after.startswith(b'# root\nrequires-python = ">=3.14"\n[tool]')
    assert b'existing = true\nalpha = 1\nzeta = "z"\n\n[tail]' in after
    assert after.endswith(b'[build-system]\nrequires = ["hatchling"]\n')
    parsed = tomllib.loads(after.decode())
    assert parsed["tool"] == {"existing": True, "alpha": 1, "zeta": "z"}
    assert parsed["build-system"] == {"requires": ["hatchling"]}


def test_toml_creates_a_nested_key_in_an_empty_document_without_leading_noise() -> None:
    adapter = TomlAdapter()
    scope = "key:/tool/ruff/line-length"

    after = adapter.render(
        adapter.inspect(b"", (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"88", value=88),),
    )

    assert after == b"[tool.ruff]\nline-length = 88\n"


def test_toml_table_update_preserves_unowned_bytes_and_reaches_fixed_point() -> None:
    before = _fixture("complex.toml")
    desired = _fixture("desired-ruff.toml")
    adapter = TomlAdapter()
    scope = "table:/tool/ruff"
    desired_unit = _unit(adapter, desired, scope)
    change = UnitChange(
        ActionKind.UPDATE,
        scope,
        content=desired_unit.raw,
        value=desired_unit.value,
    )

    after = adapter.render(adapter.inspect(before, (scope,)), (change,))

    assert after.startswith(b'# consumer preamble\ntitle = "Consumer"')
    assert after.endswith(b"[project]\nname = 'demo'\n# consumer trailer\n")
    assert b"# keep this inline comment" in after
    assert b"# nested comment" in after
    assert tomllib.loads(after.decode())["tool"]["ruff"] == desired_unit.value
    assert adapter.render(adapter.inspect(after, (scope,)), (change,)) == after


def test_toml_table_removal_removes_owned_code_but_preserves_comments() -> None:
    before = _fixture("complex.toml")
    adapter = TomlAdapter()
    scope = "table:/tool/ruff"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert b'["tool".ruff]' not in after
    assert b"[tool.ruff.lint]" not in after
    assert b"# keep this inline comment" in after
    assert b"# nested comment" in after
    assert after.endswith(b"[project]\nname = 'demo'\n# consumer trailer\n")
    parsed = tomllib.loads(after.decode())
    assert parsed["tool"] == {"coverage.py": {"branch": True}}


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"not = [valid", "valid TOML"),
        (_fixture("duplicate.toml"), "valid TOML"),
        (b"[tool.items]\n[[tool.items.entry]]\nname='x'\n", "array-of-tables"),
    ],
)
def test_toml_rejects_malformed_duplicate_or_ambiguous_selected_input(
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(ControlPlaneError, match=message):
        TomlAdapter().inspect(content, ("table:/tool/items",))


def test_toml_rejects_duplicate_or_mismatched_changes() -> None:
    content = b"[tool]\nvalue = 1\n"
    adapter = TomlAdapter()
    scope = "key:/tool/value"
    state = adapter.inspect(content, (scope,))
    change = UnitChange(ActionKind.UPDATE, scope, content=b"2", value=2)

    with pytest.raises(ControlPlaneError, match="duplicate"):
        adapter.render(state, (change, change))
    with pytest.raises(ControlPlaneError, match="semantic value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"3", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="exceeds"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"2\nother = 3", value=2),),
        )


def test_toml_noop_and_preserve_are_byte_identical() -> None:
    content = _fixture("complex.toml")
    adapter = TomlAdapter()
    scopes = ("key:/tool/ruff/line-length", "key:/project/name")
    state = adapter.inspect(content, scopes)

    rendered = adapter.render(
        state,
        (
            UnitChange(ActionKind.NOOP, scopes[0]),
            UnitChange(ActionKind.PRESERVE, scopes[1]),
        ),
    )

    assert rendered == content
