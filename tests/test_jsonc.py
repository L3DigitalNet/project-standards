"""Tests for the private mutable-runtime JSONC sanitizer."""

from __future__ import annotations

import json

import pytest


def _sanitize(source: str) -> str:
    from project_standards.jsonc import (
        _sanitize_jsonc,  # pyright: ignore[reportPrivateUsage]
    )

    return _sanitize_jsonc(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            '{\n  // whole line\n  "enabled": true\n}',
            {"enabled": True},
            id="whole-line-comment",
        ),
        pytest.param(
            '{"enabled": true, // inline comment\n "count": 2}',
            {"enabled": True, "count": 2},
            id="inline-comment",
        ),
        pytest.param(
            '{"enabled": true, // inline comment\r "count": 2}',
            {"enabled": True, "count": 2},
            id="cr-only-line-comment",
        ),
        pytest.param(
            '{"enabled": true, // inline comment\r\n "count": 2}',
            {"enabled": True, "count": 2},
            id="crlf-line-comment",
        ),
        pytest.param(
            '{"enabled": /* inline block */ true}',
            {"enabled": True},
            id="inline-block-comment",
        ),
        pytest.param(
            '{"enabled": true, /* multiline\n block */ "count": 2}',
            {"enabled": True, "count": 2},
            id="multiline-block-comment",
        ),
        pytest.param(
            '{"enabled": true,}',
            {"enabled": True},
            id="object-trailing-comma",
        ),
        pytest.param(
            "[1, 2,]",
            [1, 2],
            id="array-trailing-comma",
        ),
        pytest.param(
            '{"items": [1, 2,], "nested": {"enabled": true,},}',
            {"items": [1, 2], "nested": {"enabled": True}},
            id="nested-trailing-commas",
        ),
        pytest.param(
            '{"enabled": true, /* after comma */ }',
            {"enabled": True},
            id="comment-after-trailing-comma",
        ),
        pytest.param(
            '{"url": "https://example.test/a//b", "note": "/* literal */", "closers": ",} and ,]"}',
            {
                "url": "https://example.test/a//b",
                "note": "/* literal */",
                "closers": ",} and ,]",
            },
            id="comment-and-comma-tokens-inside-strings",
        ),
        pytest.param(
            r'{"quote": "escaped \" // literal", "slash": "\\\\/* literal */"}',
            {"quote": 'escaped " // literal', "slash": r"\\/* literal */"},
            id="escaped-quote-and-backslash",
        ),
    ],
)
def test_sanitize_jsonc__valid_extensions__loads_expected(source: str, expected: object) -> None:
    assert json.loads(_sanitize(source)) == expected


def test_sanitize_jsonc__strict_json__preserves_source_text() -> None:
    source = '{"url":"https://example.test","text":",} // literal"}\n'

    assert _sanitize(source) == source


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('{"enabled": true} /* unterminated', id="unterminated-block-comment"),
        pytest.param('{"enabled": "unterminated}', id="unterminated-string"),
        pytest.param('{"enabled": true,,}', id="repeated-comma"),
        pytest.param("{,}", id="object-leading-comma"),
        pytest.param("[,]", id="array-leading-comma"),
        pytest.param('{"enabled" true}', id="missing-colon"),
    ],
)
def test_sanitize_jsonc__malformed_input__remains_invalid(source: str) -> None:
    with pytest.raises(json.JSONDecodeError):
        json.loads(_sanitize(source))
