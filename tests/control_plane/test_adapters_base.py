from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from project_standards.control_plane.adapters import (
    EditorConfigAdapter,
    JsonAdapter,
    JsoncAdapter,
    MarkdownBlockAdapter,
    TomlAdapter,
    YamlAdapter,
)
from project_standards.control_plane.adapters import markdown as markdown_adapter
from project_standards.control_plane.adapters.base import (
    DocumentAdapter,
    apply_edits,
    decode_json_pointer,
    decode_utf8,
    line_end_without_newline,
)
from project_standards.control_plane.diagnostics import ControlPlaneError


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param("value\r\n", 5, id="crlf"),
        pytest.param("value\n", 5, id="lf"),
        pytest.param("value\r", 6, id="bare-cr"),
        pytest.param("value", 5, id="no-newline"),
    ],
)
def test_line_end_without_newline_preserves_only_real_line_endings(
    line: str, expected: int
) -> None:
    assert line_end_without_newline(line) == expected


def test_decode_json_pointer_unescapes_rfc_6901_tokens() -> None:
    assert decode_json_pointer("/a~1b/m~0n") == ("a/b", "m~n")


def test_apply_edits_splices_from_the_highest_offset() -> None:
    assert apply_edits("abcdef", [(1, 3, "X"), (4, 6, "Y")]) == "aXdY"


def test_decode_utf8_preserves_the_caller_label() -> None:
    assert decode_utf8(b"valid", "Example") == "valid"
    with pytest.raises(ControlPlaneError, match=r"^Example content is not valid UTF-8$"):
        decode_utf8(b"\xff", "Example")


@pytest.mark.parametrize(
    ("adapter", "label"),
    [
        pytest.param(EditorConfigAdapter(), "EditorConfig", id="editorconfig"),
        pytest.param(MarkdownBlockAdapter(), "Markdown", id="markdown"),
        pytest.param(YamlAdapter(), "YAML", id="yaml"),
        pytest.param(TomlAdapter(), "TOML", id="toml"),
        pytest.param(JsonAdapter(), "JSON", id="json"),
        pytest.param(JsoncAdapter(), "JSONC", id="jsonc"),
    ],
)
def test_adapter_invalid_utf8_diagnostics_keep_their_format_label(
    adapter: DocumentAdapter,
    label: str,
) -> None:
    with pytest.raises(ControlPlaneError, match=f"^{label} content is not valid UTF-8$"):
        adapter.inspect(b"\xff", ())


def test_markdown_block_normalization_keeps_its_distinct_utf8_label() -> None:
    normalize = cast(
        "Callable[[bytes | str], bytes]",
        vars(markdown_adapter)["_normalized"],
    )

    with pytest.raises(
        ControlPlaneError,
        match=r"^Markdown block content is not valid UTF-8$",
    ):
        normalize(b"\xff")
