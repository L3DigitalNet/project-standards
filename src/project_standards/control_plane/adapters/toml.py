"""Lexically index valid TOML statements without reserializing their source text."""

from __future__ import annotations

import json
import math
import re
import tomllib
from dataclasses import dataclass
from typing import Literal, cast
from urllib.parse import unquote

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
)
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonValue,
    normalize_scope,
)

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$", re.ASCII)
_MISSING = object()


@dataclass(frozen=True, slots=True)
class TomlStatement:
    """One table header or assignment with absolute source spans."""

    kind: Literal["table", "assignment"]
    table: tuple[str, ...]
    key: tuple[str, ...] | None
    start: int
    end: int
    source_end: int
    value_start: int
    value_end: int
    array_table: bool = False


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """One normalized TOML selector decomposed for bounded source lookup."""

    normalized: str
    kind: Literal["key", "table", "keyed-set"]
    path: tuple[str, ...]
    identity_key: str | None = None
    identity: str | None = None


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
            array_table = code.startswith("[[")
            table = _table_path(code)
            statements.append(
                TomlStatement(
                    kind="table",
                    table=table,
                    key=None,
                    start=absolute_start,
                    end=absolute_start + len(code),
                    source_end=end,
                    value_start=-1,
                    value_end=-1,
                    array_table=array_table,
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
                source_end=end,
                value_start=absolute_start + value_offset,
                value_end=absolute_start + value_end,
            )
        )
    return tuple(statements)


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("TOML content is not valid UTF-8") from exc


def _parse(text: str) -> dict[str, object]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ControlPlaneError("content is not valid TOML") from exc


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ControlPlaneError("selected TOML value is not canonical JSON")
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        table = cast("dict[str, object]", value)
        return {key: _json_value(child) for key, child in table.items()}
    raise ControlPlaneError("selected TOML value is not JSON-compatible")


def _pointer(value: str) -> tuple[str, ...]:
    return tuple(segment.replace("~1", "/").replace("~0", "~") for segment in value.split("/")[1:])


def _scope(scope: str) -> ScopeSpec:
    try:
        normalized = normalize_scope(AdapterKind.TOML, scope)
    except ValueError as exc:
        raise ControlPlaneError("TOML scope is not canonical") from exc
    if normalized.startswith(("key:", "table:")):
        prefix, pointer = normalized.split(":", 1)
        return ScopeSpec(
            normalized,
            cast("Literal['key', 'table']", prefix),
            _pointer(pointer),
        )
    pointer, binding = normalized.removeprefix("keyed-set:").rsplit("#", 1)
    identity_key, identity = binding.split("=", 1)
    return ScopeSpec(
        normalized,
        "keyed-set",
        _pointer(pointer),
        unquote(identity_key),
        unquote(identity),
    )


def _value_at(root: object, path: tuple[str, ...]) -> object:
    current = root
    for component in path:
        if not isinstance(current, dict) or component not in current:
            return _MISSING
        current = cast("dict[str, object]", current)[component]
    return current


def _full_key(statement: TomlStatement) -> tuple[str, ...] | None:
    if statement.kind != "assignment" or statement.key is None:
        return None
    return (*statement.table, *statement.key)


def _is_prefix(prefix: tuple[str, ...], value: tuple[str, ...]) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def _reject_array_ambiguity(
    statements: tuple[TomlStatement, ...],
    kind: Literal["key", "table"],
    path: tuple[str, ...],
) -> None:
    for statement in statements:
        if not statement.array_table:
            continue
        if _is_prefix(statement.table, path) or (
            kind == "table" and _is_prefix(path, statement.table)
        ):
            raise ControlPlaneError("selected TOML scope crosses an array-of-tables")


def _keyed_values(root: object, spec: ScopeSpec) -> tuple[list[object], int | None]:
    value = _value_at(root, spec.path)
    if value is _MISSING:
        return [], None
    if not isinstance(value, list):
        raise ControlPlaneError("TOML keyed-set scope does not identify an array")
    items = cast("list[object]", value)
    matches: list[int] = []
    identity_key = spec.identity_key
    if identity_key is None:
        raise ControlPlaneError("TOML keyed-set scope is missing its identity key")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ControlPlaneError("TOML keyed-set array must contain tables")
        table = cast("dict[str, object]", item)
        if identity_key not in table:
            raise ControlPlaneError("TOML keyed-set entry is missing its identity key")
        if table[identity_key] == spec.identity:
            matches.append(index)
    if len(matches) > 1:
        raise ControlPlaneError("TOML content contains a duplicate keyed-set identity")
    return items, matches[0] if matches else None


def _keyed_entry_statements(
    statements: tuple[TomlStatement, ...],
    path: tuple[str, ...],
    entry_index: int,
) -> tuple[TomlStatement, ...]:
    roots = [
        index
        for index, statement in enumerate(statements)
        if statement.kind == "table" and statement.array_table and statement.table == path
    ]
    if entry_index >= len(roots):
        raise ControlPlaneError("TOML keyed-set entry has no bounded source statements")
    start = roots[entry_index]
    end = roots[entry_index + 1] if entry_index + 1 < len(roots) else len(statements)
    selected: list[TomlStatement] = []
    for statement in statements[start:end]:
        if statement.kind == "table" and not _is_prefix(path, statement.table):
            break
        if statement.kind == "assignment":
            full_key = _full_key(statement)
            if full_key is None or not _is_prefix(path, full_key):
                break
        selected.append(statement)
    if not selected:
        raise ControlPlaneError("TOML keyed-set entry has no bounded source statements")
    return tuple(selected)


def _keyed_fragment_value(content: bytes, spec: ScopeSpec) -> tuple[JsonValue, str]:
    text = _decode(content)
    parsed = _parse(text)
    items, match = _keyed_values(parsed, spec)
    if match is None or len(items) != 1:
        raise ControlPlaneError("TOML keyed-set fragment must define exactly one selected entry")
    normalized = _json_value(items[match])
    if parsed != _nested_value(spec.path, [normalized]):
        raise ControlPlaneError("TOML keyed-set fragment exceeds its declared scope")
    return normalized, text


def _assignment(
    statements: tuple[TomlStatement, ...],
    path: tuple[str, ...],
) -> TomlStatement | None:
    matches = [statement for statement in statements if _full_key(statement) == path]
    if len(matches) > 1:
        raise ControlPlaneError("selected TOML key has duplicate semantic identity")
    return matches[0] if matches else None


def _table_statements(
    statements: tuple[TomlStatement, ...],
    path: tuple[str, ...],
) -> tuple[TomlStatement, ...]:
    return tuple(
        statement
        for statement in statements
        if (statement.kind == "table" and _is_prefix(path, statement.table))
        or (
            statement.kind == "assignment"
            and (full_key := _full_key(statement)) is not None
            and _is_prefix(path, full_key)
        )
    )


def _table_fragment(
    text: str,
    statements: tuple[TomlStatement, ...],
    path: tuple[str, ...],
    expected: JsonValue,
) -> bytes:
    selected = _table_statements(statements, path)
    if not selected:
        raise ControlPlaneError("selected TOML table has no bounded source statements")
    fragment = "\n".join(text[item.start : item.end] for item in selected) + "\n"
    parsed = _parse(fragment)
    value = _value_at(parsed, path)
    if value is _MISSING or _json_value(value) != expected:
        raise ControlPlaneError("selected TOML table cannot be isolated safely")
    return fragment.encode()


def _unit_for_scope(
    text: str,
    parsed: dict[str, object],
    statements: tuple[TomlStatement, ...],
    scope: str,
) -> AdapterUnit | None:
    spec = _scope(scope)
    if spec.kind == "keyed-set":
        items, match = _keyed_values(parsed, spec)
        if match is None:
            return None
        normalized = _json_value(items[match])
        selected = _keyed_entry_statements(statements, spec.path, match)
        fragment = "\n".join(text[item.start : item.end] for item in selected) + "\n"
        isolated = _parse(fragment)
        isolated_items, isolated_match = _keyed_values(isolated, spec)
        if (
            isolated_match is None
            or len(isolated_items) != 1
            or _json_value(isolated_items[isolated_match]) != normalized
        ):
            raise ControlPlaneError("selected TOML keyed-set entry cannot be isolated safely")
        return AdapterUnit(
            spec.normalized, normalized, fragment.encode(), semantic_digest(normalized)
        )
    _reject_array_ambiguity(statements, spec.kind, spec.path)
    value = _value_at(parsed, spec.path)
    if value is _MISSING:
        return None
    normalized = _json_value(value)
    if spec.kind == "key":
        statement = _assignment(statements, spec.path)
        if statement is None:
            raise ControlPlaneError("selected TOML key is not independently addressable")
        raw = text[statement.value_start : statement.value_end].encode()
    else:
        if not isinstance(value, dict):
            raise ControlPlaneError("selected TOML table scope does not name a table")
        raw = _table_fragment(text, statements, spec.path, normalized)
    return AdapterUnit(spec.normalized, normalized, raw, semantic_digest(normalized))


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def _canonical_key(value: str) -> str:
    return value if _BARE_KEY.fullmatch(value) else json.dumps(value, ensure_ascii=False)


def _canonical_path(path: tuple[str, ...]) -> str:
    return ".".join(_canonical_key(component) for component in path)


def _fragment_value(content: bytes) -> JsonValue:
    value_text = _decode(content)
    parsed = _parse(f"__project_standards_value__ = {value_text}\n")
    if set(parsed) != {"__project_standards_value__"}:
        raise ControlPlaneError("TOML key fragment exceeds its declared scope")
    return _json_value(parsed["__project_standards_value__"])


def _nested_value(path: tuple[str, ...], value: JsonValue) -> dict[str, object]:
    nested: object = value
    for component in reversed(path):
        nested = {component: nested}
    return cast("dict[str, object]", nested)


def _table_fragment_value(
    content: bytes,
    path: tuple[str, ...],
) -> tuple[JsonValue, str]:
    text = _decode(content)
    parsed = _parse(text)
    statements = scan_toml_statements(text)
    _reject_array_ambiguity(statements, "table", path)
    value = _value_at(parsed, path)
    if value is _MISSING or not isinstance(value, dict):
        raise ControlPlaneError("TOML table fragment does not define its declared scope")
    normalized = _json_value(cast("dict[str, object]", value))
    if parsed != _nested_value(path, normalized):
        raise ControlPlaneError("TOML table fragment exceeds its declared scope")
    return normalized, text


def _check_declared_value(actual: JsonValue, declared: JsonValue | bytes | None) -> None:
    if declared is not None and declared != actual:
        raise ControlPlaneError("TOML fragment does not match its declared semantic value")


def _preserve_comments_and_whitespace(source: str) -> str:
    preserved: list[str] = []
    delimiter: str | None = None
    comment = False
    index = 0
    line_start = 0
    while index < len(source):
        if comment:
            preserved.append(source[index])
            if source[index] == "\n":
                comment = False
                line_start = index + 1
            index += 1
            continue
        if delimiter is not None:
            if source.startswith(delimiter, index):
                index += len(delimiter)
                delimiter = None
                continue
            if delimiter in {'"', '"""'} and source[index] == "\\":
                index += 2
                continue
            if source[index] == "\n":
                line_start = index + 1
            index += 1
            continue
        if source.startswith('"""', index) or source.startswith("'''", index):
            delimiter = source[index : index + 3]
            index += 3
            continue
        character = source[index]
        if character in {'"', "'"}:
            delimiter = character
        elif character == "#":
            prefix = source[line_start:index]
            if not prefix.strip():
                preserved.append(prefix)
            comment = True
            preserved.append(character)
        elif character == "\n":
            line_start = index + 1
        index += 1
    return "".join(preserved)


def _apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    updated = text
    for start, end, replacement in sorted(edits, reverse=True):
        updated = f"{updated[:start]}{replacement}{updated[end:]}"
    return updated


def _removal_bounds(
    text: str,
    statement: TomlStatement,
    *,
    consume_separator: bool,
) -> tuple[int, int]:
    start = statement.start
    end = statement.end
    if text.startswith("\r\n", end):
        end += 2
    elif end < len(text) and text[end] in "\r\n":
        end += 1
    if not consume_separator:
        return start, end

    whitespace_start = start
    while whitespace_start > 0 and text[whitespace_start - 1].isspace():
        whitespace_start -= 1
    if whitespace_start == 0:
        return 0, end
    if text.startswith("\r\n", whitespace_start):
        return whitespace_start + 2, end
    if text[whitespace_start] in "\r\n":
        return whitespace_start + 1, end
    return start, end


def _insertion_position(
    text: str,
    statements: tuple[TomlStatement, ...],
    parent: tuple[str, ...],
) -> int | None:
    if not parent:
        root_assignments = [
            statement
            for statement in statements
            if statement.kind == "assignment" and statement.table == ()
        ]
        if root_assignments:
            return root_assignments[-1].source_end
        first_table = next(
            (statement for statement in statements if statement.kind == "table"),
            None,
        )
        return first_table.start if first_table is not None else len(text)
    headers = [
        statement
        for statement in statements
        if statement.kind == "table" and not statement.array_table and statement.table == parent
    ]
    if not headers:
        return None
    header = headers[0]
    direct = [
        statement
        for statement in statements
        if statement.kind == "assignment"
        and statement.table == parent
        and statement.start > header.start
    ]
    return direct[-1].source_end if direct else header.source_end


def _insert_keys(
    text: str,
    keys: list[tuple[tuple[str, ...], str]],
    newline: str,
) -> str:
    grouped: dict[tuple[str, ...], list[tuple[str, str]]] = {}
    for path, value in keys:
        grouped.setdefault(path[:-1], []).append((path[-1], value))
    updated = text
    for parent in sorted(grouped, key=lambda item: tuple(part.encode() for part in item)):
        statements = scan_toml_statements(updated)
        position = _insertion_position(updated, statements, parent)
        assignments = "".join(
            f"{_canonical_key(key)} = {value}{newline}"
            for key, value in sorted(
                grouped[parent],
                key=lambda item: item[0].encode("utf-8"),
            )
        )
        if position is None:
            if not updated or updated.endswith(newline * 2):
                prefix = ""
            elif updated.endswith(newline):
                prefix = newline
            else:
                prefix = newline * 2
            block = f"{prefix}[{_canonical_path(parent)}]{newline}{assignments}"
            updated += block
            continue
        if position > 0 and updated[position - 1] not in "\r\n":
            assignments = f"{newline}{assignments}"
        updated = f"{updated[:position]}{assignments}{updated[position:]}"
    return updated


def _append_tables(text: str, tables: list[tuple[str, str]], newline: str) -> str:
    updated = text
    for _, fragment in sorted(tables, key=lambda item: item[0].encode("utf-8")):
        normalized = fragment.replace("\r\n", "\n").replace("\n", newline)
        prefix = "" if not updated or updated.endswith(("\n", "\r")) else newline
        if updated and not updated.endswith(newline * 2):
            prefix += newline
        updated = f"{updated}{prefix}{normalized}"
        if not updated.endswith(newline):
            updated += newline
    return updated


class TomlAdapter:
    """Compose selected TOML keys and tables through bounded source splices."""

    kind = AdapterKind.TOML

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        text = _decode(content)
        parsed = _parse(text)
        try:
            statements = scan_toml_statements(text)
        except (tomllib.TOMLDecodeError, ValueError) as exc:
            raise ControlPlaneError("content is not valid TOML") from exc
        normalized_scopes: list[str] = []
        for scope in scopes:
            normalized_scopes.append(_scope(scope).normalized)
        if len(normalized_scopes) != len(set(normalized_scopes)):
            raise ControlPlaneError("TOML inspection contains a duplicate scope")
        units = [
            unit
            for scope in sorted(normalized_scopes, key=lambda item: item.encode("utf-8"))
            if (unit := _unit_for_scope(text, parsed, statements, scope)) is not None
        ]
        return AdapterState(content, tuple(units))

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        text = _decode(state.content)
        parsed = _parse(text)
        try:
            statements = scan_toml_statements(text)
        except (tomllib.TOMLDecodeError, ValueError) as exc:
            raise ControlPlaneError("content is not valid TOML") from exc
        scopes = [change.scope for change in changes]
        if len(scopes) != len(set(scopes)):
            raise ControlPlaneError("TOML rendering contains a duplicate change scope")

        edits: list[tuple[int, int, str]] = []
        new_keys: list[tuple[tuple[str, ...], str]] = []
        new_tables: list[tuple[str, str]] = []
        for change in sorted(changes, key=lambda item: item.scope.encode("utf-8")):
            spec = _scope(change.scope)
            match: int | None = None
            if spec.kind == "keyed-set":
                items, match = _keyed_values(parsed, spec)
                current = items[match] if match is not None else _MISSING
            else:
                _reject_array_ambiguity(statements, spec.kind, spec.path)
                current = _value_at(parsed, spec.path)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating TOML change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("TOML removal cannot carry content")
                if current is _MISSING:
                    raise ControlPlaneError("TOML removal scope is not present")
                if spec.kind == "keyed-set":
                    assert match is not None
                    selected = _keyed_entry_statements(statements, spec.path, match)
                elif spec.kind == "key":
                    selected = (_assignment(statements, spec.path),)
                else:
                    selected = _table_statements(statements, spec.path)
                if not selected or selected[0] is None:
                    raise ControlPlaneError("TOML removal scope is not independently addressable")
                for index, statement in enumerate(cast("tuple[TomlStatement, ...]", selected)):
                    start, end = _removal_bounds(
                        text,
                        statement,
                        consume_separator=spec.kind != "key" and index == 0,
                    )
                    source = text[start:end]
                    edits.append(
                        (
                            start,
                            end,
                            _preserve_comments_and_whitespace(source),
                        )
                    )
                continue
            if change.content is None:
                raise ControlPlaneError("mutating TOML change requires a bounded fragment")
            if spec.kind == "key":
                desired = _fragment_value(change.content)
                fragment = _decode(change.content)
            elif spec.kind == "keyed-set":
                desired, fragment = _keyed_fragment_value(change.content, spec)
            else:
                desired, fragment = _table_fragment_value(change.content, spec.path)
            _check_declared_value(desired, change.value)
            if change.kind is ActionKind.ADOPT:
                if current is _MISSING or _json_value(current) != desired:
                    raise ControlPlaneError("TOML adoption requires an equal existing value")
                continue
            if change.kind is ActionKind.CREATE:
                if current is not _MISSING:
                    raise ControlPlaneError("TOML creation scope already exists")
                if spec.kind == "key":
                    new_keys.append((spec.path, fragment))
                else:
                    new_tables.append((change.scope, fragment))
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("TOML adapter received an unsupported action")
            if current is _MISSING:
                raise ControlPlaneError("TOML update scope is not present")
            if _json_value(current) == desired:
                continue
            if spec.kind == "key":
                statement = _assignment(statements, spec.path)
                if statement is None:
                    raise ControlPlaneError("TOML update scope is not independently addressable")
                edits.append((statement.value_start, statement.value_end, fragment))
            elif spec.kind == "keyed-set":
                assert match is not None
                selected = _keyed_entry_statements(statements, spec.path, match)
                for index, statement in enumerate(selected):
                    source = text[statement.start : statement.end]
                    preserved = _preserve_comments_and_whitespace(source)
                    replacement = f"{fragment}{preserved}" if index == 0 else preserved
                    edits.append((statement.start, statement.end, replacement))
            else:
                selected = _table_statements(statements, spec.path)
                if not selected:
                    raise ControlPlaneError("TOML update scope is not independently addressable")
                for index, statement in enumerate(selected):
                    source = text[statement.start : statement.end]
                    preserved = _preserve_comments_and_whitespace(source)
                    replacement = f"{fragment}{preserved}" if index == 0 else preserved
                    edits.append((statement.start, statement.end, replacement))

        updated = _apply_edits(text, edits)
        newline = _newline(updated)
        new_keys = [
            (path, value.replace("\r\n", "\n").replace("\n", newline)) for path, value in new_keys
        ]
        updated = _insert_keys(updated, new_keys, newline)
        updated = _append_tables(updated, new_tables, newline)
        _parse(updated)
        return updated.encode()
