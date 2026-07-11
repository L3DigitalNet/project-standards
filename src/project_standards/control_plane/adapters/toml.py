"""Lexically index valid TOML statements without reserializing their source text."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import Literal, cast


@dataclass(frozen=True, slots=True)
class TomlStatement:
    """One table header or assignment with absolute source spans."""

    kind: Literal["table", "assignment"]
    table: tuple[str, ...]
    key: tuple[str, ...] | None
    start: int
    end: int
    value_start: int
    value_end: int


def _logical_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    index = 0
    depth = 0
    delimiter: str | None = None
    comment = False
    while index < len(text):
        if comment:
            if text[index] == "\n":
                comment = False
                if depth == 0 and delimiter is None:
                    spans.append((start, index + 1))
                    start = index + 1
            index += 1
            continue
        if delimiter is not None:
            if text.startswith(delimiter, index):
                index += len(delimiter)
                delimiter = None
                continue
            if delimiter in {'"', '"""'} and text[index] == "\\":
                index += 2
                continue
            index += 1
            continue
        if text.startswith('"""', index) or text.startswith("'''", index):
            delimiter = text[index : index + 3]
            index += 3
            continue
        character = text[index]
        if character in {'"', "'"}:
            delimiter = character
        elif character == "#":
            comment = True
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth = max(0, depth - 1)
        elif character == "\n" and depth == 0:
            spans.append((start, index + 1))
            start = index + 1
        index += 1
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _comment_start(text: str) -> int:
    delimiter: str | None = None
    depth = 0
    index = 0
    while index < len(text):
        if delimiter is not None:
            if text.startswith(delimiter, index):
                index += len(delimiter)
                delimiter = None
                continue
            if delimiter in {'"', '"""'} and text[index] == "\\":
                index += 2
                continue
            index += 1
            continue
        if text.startswith('"""', index) or text.startswith("'''", index):
            delimiter = text[index : index + 3]
            index += 3
            continue
        character = text[index]
        if character in {'"', "'"}:
            delimiter = character
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth = max(0, depth - 1)
        elif character == "#" and depth == 0:
            return index
        index += 1
    return len(text)


def _assignment_separator(text: str) -> int:
    delimiter: str | None = None
    index = 0
    while index < len(text):
        if delimiter is not None:
            if text[index] == delimiter:
                delimiter = None
            elif delimiter == '"' and text[index] == "\\":
                index += 1
            index += 1
            continue
        if text[index] in {'"', "'"}:
            delimiter = text[index]
        elif text[index] == "=":
            return index
        index += 1
    raise ValueError("TOML assignment has no separator")


def _marker_path(value: object, path: tuple[str, ...] = ()) -> tuple[str, ...] | None:
    if not isinstance(value, dict):
        return None
    for key, nested in cast(dict[str, object], value).items():
        if key == "__project_standards_marker__":
            return path
        found = _marker_path(nested, (*path, key))
        if found is not None:
            return found
    return None


def _table_path(header: str) -> tuple[str, ...]:
    array_table = header.startswith("[[")
    closing = 2 if array_table else 1
    body = header[closing:-closing].strip()
    marker = "__project_standards_marker__ = true"
    parsed = tomllib.loads(f"[{body}]\n{marker}\n")
    path = _marker_path(parsed)
    if path is None:
        raise ValueError("TOML table path could not be resolved")
    return path


def _key_path(key: str) -> tuple[str, ...]:
    parsed = tomllib.loads(f"{key} = {{ __project_standards_marker__ = true }}\n")

    def find(value: object, path: tuple[str, ...] = ()) -> tuple[str, ...] | None:
        if not isinstance(value, dict):
            return None
        table = cast(dict[str, object], value)
        if table.get("__project_standards_marker__") is True:
            return path
        for name, nested in table.items():
            found = find(nested, (*path, name))
            if found is not None:
                return found
        return None

    path = find(parsed)
    if path is None:
        raise ValueError("TOML assignment key could not be resolved")
    return path


def scan_toml_statements(text: str) -> tuple[TomlStatement, ...]:
    """Return table and assignment spans from syntactically valid TOML.

    TOML parsing remains authoritative for semantics. This scanner records only
    lexical boundaries so callers can splice an owned value without normalizing
    comments, quoting, ordering, or unrelated whitespace.
    """
    tomllib.loads(text)
    statements: list[TomlStatement] = []
    table: tuple[str, ...] = ()
    for start, end in _logical_spans(text):
        raw = text[start:end]
        leading = len(raw) - len(raw.lstrip())
        source = raw[leading:]
        if not source or source.startswith("#"):
            continue
        comment_at = _comment_start(source)
        code = source[:comment_at].rstrip()
        if not code:
            continue
        absolute_start = start + leading
        if code.startswith("["):
            table = _table_path(code)
            statements.append(
                TomlStatement(
                    kind="table",
                    table=table,
                    key=None,
                    start=absolute_start,
                    end=absolute_start + len(code),
                    value_start=-1,
                    value_end=-1,
                )
            )
            continue
        separator = _assignment_separator(code)
        key_text = code[:separator].strip()
        value_offset = separator + 1
        while value_offset < len(code) and code[value_offset].isspace():
            value_offset += 1
        value_end = len(code.rstrip())
        statements.append(
            TomlStatement(
                kind="assignment",
                table=table,
                key=_key_path(key_text),
                start=absolute_start,
                end=absolute_start + len(code),
                value_start=absolute_start + value_offset,
                value_end=absolute_start + value_end,
            )
        )
    return tuple(statements)
