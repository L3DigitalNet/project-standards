from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.control_plane.adapters import editorconfig as editorconfig_adapter
from project_standards.control_plane.adapters.base import UnitChange
from project_standards.control_plane.adapters.editorconfig import EditorConfigAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError

_FIXTURES = Path(__file__).parent / "fixtures/editorconfig"

_NON_NEWLINE_SPLITLINES_BOUNDARIES = (
    pytest.param("\r", id="carriage-return"),
    pytest.param("\v", id="vertical-tab"),
    pytest.param("\f", id="form-feed"),
    pytest.param("\x1c", id="file-separator"),
    pytest.param("\x1d", id="group-separator"),
    pytest.param("\x1e", id="record-separator"),
    pytest.param("\x85", id="next-line"),
    pytest.param("\u2028", id="line-separator"),
    pytest.param("\u2029", id="paragraph-separator"),
)
_REAL_NEWLINES = (
    pytest.param("\n", id="lf"),
    pytest.param("\r\n", id="crlf"),
)
_CR_SUFFIX_CASES = (
    pytest.param("root = value\r", "root = value\r", id="bare-cr-at-eof"),
    pytest.param("root = value\r\r\n", "root = value\r", id="content-cr-before-crlf"),
)


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


@pytest.mark.parametrize("separator", _NON_NEWLINE_SPLITLINES_BOUNDARIES)
def test_editorconfig_inspect__non_newline_splitlines_boundary__preserves_value_span(
    separator: str,
) -> None:
    scope = "property:$global#root"
    value = f"left{separator}right"
    content = f"root = {value}\nnext = untouched\n".encode()
    adapter = EditorConfigAdapter()

    state = adapter.inspect(content, (scope,))

    assert state.units[0].raw == value.encode()
    assert adapter.render(state, (UnitChange(ActionKind.NOOP, scope),)) == content
    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"changed", value="changed"),),
        )
        == b"root = changed\nnext = untouched\n"
    )


@pytest.mark.parametrize("newline", _REAL_NEWLINES)
def test_editorconfig_inspect__lf_or_crlf__preserves_value_spans_and_round_trip(
    newline: str,
) -> None:
    scopes = ("property:$global#root", "property:$global#next")
    content = f"root = left{newline}next = right{newline}".encode()
    adapter = EditorConfigAdapter()

    state = adapter.inspect(content, scopes)

    units = {unit.scope: unit for unit in state.units}
    assert units["property:$global#root"].raw == b"left"
    assert units["property:$global#next"].raw == b"right"
    assert (
        adapter.render(
            state,
            tuple(UnitChange(ActionKind.NOOP, scope) for scope in scopes),
        )
        == content
    )


@pytest.mark.parametrize(("physical", "expected_code"), _CR_SUFFIX_CASES)
def test_editorconfig_parse__cr_suffix__preserves_content_span_and_round_trip(
    physical: str,
    expected_code: str,
) -> None:
    code_end = editorconfig_adapter._line_end_without_newline(  # pyright: ignore[reportPrivateUsage]  # parser span regression
        physical
    )
    document = editorconfig_adapter._parse(  # pyright: ignore[reportPrivateUsage]  # parser span regression
        physical.encode()
    )

    assert physical[:code_end] == expected_code
    assert len(document.properties) == 1
    assert (document.properties[0].line_start, document.properties[0].source_end) == (
        0,
        len(physical),
    )
    content = physical.encode()
    adapter = EditorConfigAdapter()
    state = adapter.inspect(content, ("property:$global#root",))
    assert adapter.render(state, (UnitChange(ActionKind.NOOP, "property:$global#root"),)) == content


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


def test_editorconfig_global_property_round_trip_restores_created_bytes() -> None:
    content = b"root = true\n\n[*]\ncharset = utf-8\n"
    adapter = EditorConfigAdapter()
    scope = "property:$global#root"

    removed = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )
    restored = adapter.render(
        adapter.inspect(removed, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"true", value="true"),),
    )

    assert restored == content


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
