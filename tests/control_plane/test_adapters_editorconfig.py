from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.control_plane.adapters.base import UnitChange
from project_standards.control_plane.adapters.editorconfig import EditorConfigAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError

_FIXTURES = Path(__file__).parent / "fixtures/editorconfig"


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def test_editorconfig_inspects_normalized_global_and_section_properties() -> None:
    adapter = EditorConfigAdapter()
    content = _fixture("consumer.editorconfig")

    state = adapter.inspect(
        content,
        (
            "property:$global#root",
            "property:*.{py,pyi}#indent_size",
            "property:*.md#trim_trailing_whitespace",
        ),
    )

    units = {unit.scope: unit for unit in state.units}
    assert units["property:$global#root"].value == "true"
    assert units["property:$global#root"].raw == b"true"
    assert units["property:*.{py,pyi}#indent_size"].value == "4"
    assert units["property:*.md#trim_trailing_whitespace"].value == "false"


def test_editorconfig_update_splices_only_value_and_is_idempotent() -> None:
    before = _fixture("consumer.editorconfig")
    adapter = EditorConfigAdapter()
    scope = "property:*.{py,pyi}#indent_size"
    change = UnitChange(ActionKind.UPDATE, scope, content=b"2", value="2")

    after = adapter.render(adapter.inspect(before, (scope,)), (change,))

    assert after == before.replace(b"indent_size: 4", b"indent_size: 2", 1)
    assert adapter.render(adapter.inspect(after, (scope,)), (change,)) == after


def test_editorconfig_adopts_equal_value_without_rewriting_case_or_spacing() -> None:
    content = b"ROOT : TRUE\n"
    adapter = EditorConfigAdapter()
    scope = "property:$global#root"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.ADOPT, scope, content=b"true", value="true"),),
    )

    assert after == content


def test_editorconfig_shared_property_preserves_until_last_reference_removal() -> None:
    content = _fixture("consumer.editorconfig")
    adapter = EditorConfigAdapter()
    scope = "property:*.{py,pyi}#indent_style"

    preserved = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.PRESERVE, scope),),
    )
    removed = adapter.render(
        adapter.inspect(preserved, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert preserved == content
    assert b"indent_style" not in removed
    assert b"# Keep this local rule." in removed
    assert b"max_line_length = 100" in removed


def test_editorconfig_appends_properties_and_missing_sections_canonically() -> None:
    before = _fixture("consumer.editorconfig")
    adapter = EditorConfigAdapter()
    changes = (
        UnitChange(
            ActionKind.CREATE,
            "property:*.py#zeta",
            content=b"z",
            value="z",
        ),
        UnitChange(
            ActionKind.CREATE,
            "property:*.md#insert_final_newline",
            content=b"true",
            value="true",
        ),
        UnitChange(
            ActionKind.CREATE,
            "property:*.py#alpha",
            content=b"a",
            value="a",
        ),
        UnitChange(
            ActionKind.CREATE,
            "property:$global#charset",
            content=b"utf-8",
            value="utf-8",
        ),
    )

    after = adapter.render(adapter.inspect(before, tuple(item.scope for item in changes)), changes)

    assert after.startswith(b"# Consumer-wide settings.\nroot = true\ncharset = utf-8\n")
    assert b"[*.md]\ntrim_trailing_whitespace = false\ninsert_final_newline = true\n" in after
    assert after.endswith(b"[*.py]\nalpha = a\nzeta = z\n")


def test_editorconfig_preserves_crlf_when_inserting() -> None:
    content = b"root = true\r\n\r\n[*.py]\r\nindent_size = 4\r\n"
    adapter = EditorConfigAdapter()
    scope = "property:*.py#indent_style"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"space", value="space"),),
    )

    assert after == content + b"indent_style = space\r\n"


def test_editorconfig_rejects_duplicate_properties_sections_and_conflicts() -> None:
    adapter = EditorConfigAdapter()
    duplicate = _fixture("duplicate.editorconfig")

    with pytest.raises(ControlPlaneError, match="duplicate property"):
        adapter.inspect(duplicate, ("property:$global#root",))
    with pytest.raises(ControlPlaneError, match="duplicate section"):
        adapter.inspect(duplicate, ("property:*.py#indent_style",))

    content = b"root = false\n"
    state = adapter.inspect(content, ("property:$global#root",))
    with pytest.raises(ControlPlaneError, match="equal existing value"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.ADOPT,
                    "property:$global#root",
                    content=b"true",
                    value="true",
                ),
            ),
        )


def test_editorconfig_rejects_invalid_fragments_and_lifecycle_transitions() -> None:
    adapter = EditorConfigAdapter()
    content = b"root = true\n"
    scope = "property:$global#root"
    state = adapter.inspect(content, (scope,))

    with pytest.raises(ControlPlaneError, match="duplicate"):
        adapter.render(
            state,
            (
                UnitChange(ActionKind.UPDATE, scope, content=b"false", value="false"),
                UnitChange(ActionKind.UPDATE, scope, content=b"false", value="false"),
            ),
        )
    with pytest.raises(ControlPlaneError, match="single property value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"false\nother = x", value="false"),),
        )
    with pytest.raises(ControlPlaneError, match="semantic value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"false", value="true"),),
        )
    with pytest.raises(ControlPlaneError, match="already exists"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, scope, content=b"false", value="false"),),
        )


def test_editorconfig_noop_is_byte_identical() -> None:
    content = _fixture("consumer.editorconfig")
    adapter = EditorConfigAdapter()
    scope = "property:*.md#trim_trailing_whitespace"

    assert (
        adapter.render(
            adapter.inspect(content, (scope,)),
            (UnitChange(ActionKind.NOOP, scope),),
        )
        == content
    )
