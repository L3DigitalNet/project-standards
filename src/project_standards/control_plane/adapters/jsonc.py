"""Compose JSON-family semantic units without reserializing consumer files.

``json.loads`` validates a copy whose JSONC comments and trailing commas are
replaced by spaces. The replacement keeps character offsets aligned with a
small lexical tree, allowing mutations to splice only the selected value and
the minimum required separator while retaining all other source bytes.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, cast
from urllib.parse import unquote

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
    apply_edits,
    decode_json_pointer,
    decode_utf8,
)
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import (
    AdapterKind,
    JsonValue,
    normalize_scope,
)

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_MISSING = object()
_PRETTIER_PRINT_WIDTH = 88

type TokenKind = Literal[
    "string",
    "number",
    "true",
    "false",
    "null",
    "open-object",
    "close-object",
    "open-array",
    "close-array",
    "colon",
    "comma",
    "whitespace",
    "comment",
]
type NodeKind = Literal["object", "array", "scalar"]
type ScopeKind = Literal["key", "set", "keyed-set"]


@dataclass(frozen=True, slots=True)
class JsonToken:
    """One lexical token with absolute character offsets."""

    kind: TokenKind
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class JsonMember:
    """One object member and the comma that follows it, when present."""

    key: str
    key_token: JsonToken
    value: JsonNode
    comma: JsonToken | None


@dataclass(frozen=True, slots=True)
class JsonNode:
    """One semantic JSON value with exact lexical boundaries."""

    kind: NodeKind
    start: int
    end: int
    value: JsonValue
    opening: JsonToken | None = None
    closing: JsonToken | None = None
    members: tuple[JsonMember, ...] = ()
    elements: tuple[JsonNode, ...] = ()
    commas: tuple[JsonToken | None, ...] = ()


@dataclass(frozen=True, slots=True)
class JsonDocument:
    """Parsed semantics plus source-preserving lexical structure."""

    text: str
    root: JsonNode


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """One normalized JSON-family selector decomposed for lookup."""

    normalized: str
    kind: ScopeKind
    path: tuple[str, ...]
    identity_key: str | None = None
    identity: str | None = None


@dataclass(frozen=True, slots=True)
class LocatedUnit:
    """A selected node plus enough parent context for bounded removal."""

    node: JsonNode
    container: JsonNode
    index: int
    member: JsonMember | None = None


class _DuplicateObjectKey(ValueError):
    pass


def _flat_json(value: JsonValue) -> str:
    if isinstance(value, dict):
        if not value:
            return "{}"
        members = (
            f"{json.dumps(key, ensure_ascii=True)}: {_flat_json(item)}"
            for key, item in value.items()
        )
        return f"{{ {', '.join(members)} }}"
    if isinstance(value, list):
        return f"[{', '.join(_flat_json(item) for item in value)}]"
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def _forces_prettier_break(value: JsonValue) -> bool:
    if isinstance(value, list):
        homogeneous_table = len(value) > 1 and all(
            isinstance(item, dict) and len(item) > 1 for item in value
        )
        homogeneous_matrix = len(value) > 1 and all(
            isinstance(item, list) and len(item) > 1 for item in value
        )
        return (
            homogeneous_table
            or homogeneous_matrix
            or any(_forces_prettier_break(item) for item in value)
        )
    if isinstance(value, dict):
        return any(_forces_prettier_break(item) for item in value.values())
    return False


def _prettier_json(
    value: JsonValue,
    indent: str = "",
    *,
    force_break: bool = False,
    prefix_width: int = 0,
) -> str:
    flat = _flat_json(value)
    if (
        not force_break
        and not _forces_prettier_break(value)
        and len(indent.expandtabs(2)) + prefix_width + len(flat) <= _PRETTIER_PRINT_WIDTH
    ):
        return flat
    child_indent = f"{indent}\t"
    if isinstance(value, dict):
        members: list[str] = []
        for index, (key, item) in enumerate(value.items()):
            rendered_key = json.dumps(key, ensure_ascii=True)
            rendered_value = _prettier_json(
                item,
                child_indent,
                force_break=_forces_prettier_break(item),
                prefix_width=(len(rendered_key) + 2 + (1 if index < len(value) - 1 else 0)),
            )
            members.append(f"{child_indent}{rendered_key}: {rendered_value}")
        return "{\n" + ",\n".join(members) + f"\n{indent}}}"
    if isinstance(value, list):
        items = [
            f"{child_indent}{_prettier_json(item, child_indent, prefix_width=(1 if index < len(value) - 1 else 0))}"
            for index, item in enumerate(value)
        ]
        return "[\n" + ",\n".join(items) + f"\n{indent}]"
    return flat


def format_fresh_json_container(content: bytes, kind: AdapterKind) -> bytes:
    """Format a newly materialized JSON-family container to repository style."""
    if kind not in {AdapterKind.JSON, AdapterKind.JSONC}:
        raise ControlPlaneError("fresh JSON formatting requires a JSON-family adapter")
    value = _parse(content, kind).root.value
    return f"{_prettier_json(value)}\n".encode()


def _scan_string(text: str, start: int) -> int:
    index = start + 1
    while index < len(text):
        character = text[index]
        if character == '"':
            return index + 1
        if character == "\\":
            index += 2
            continue
        if ord(character) < 0x20:
            raise ValueError("JSON string contains an unescaped control character")
        index += 1
    raise ValueError("JSON string is not terminated")


def _lex(text: str, *, allow_comments: bool) -> tuple[JsonToken, ...]:
    tokens: list[JsonToken] = []
    punctuation: dict[str, TokenKind] = {
        "{": "open-object",
        "}": "close-object",
        "[": "open-array",
        "]": "close-array",
        ":": "colon",
        ",": "comma",
    }
    literals: dict[str, TokenKind] = {
        "true": "true",
        "false": "false",
        "null": "null",
    }
    index = 0
    while index < len(text):
        character = text[index]
        if character in " \t\r\n":
            end = index + 1
            while end < len(text) and text[end] in " \t\r\n":
                end += 1
            tokens.append(JsonToken("whitespace", index, end))
            index = end
            continue
        if character == '"':
            end = _scan_string(text, index)
            json.loads(text[index:end])
            tokens.append(JsonToken("string", index, end))
            index = end
            continue
        if character in punctuation:
            tokens.append(JsonToken(punctuation[character], index, index + 1))
            index += 1
            continue
        if text.startswith("//", index) or text.startswith("/*", index):
            if not allow_comments:
                raise ValueError("comments are not valid JSON")
            if text.startswith("//", index):
                newline = text.find("\n", index + 2)
                end = len(text) if newline == -1 else newline
            else:
                closing = text.find("*/", index + 2)
                if closing == -1:
                    raise ValueError("block comment is not terminated")
                end = closing + 2
            tokens.append(JsonToken("comment", index, end))
            index = end
            continue
        literal = next((value for value in literals if text.startswith(value, index)), None)
        if literal is not None:
            end = index + len(literal)
            tokens.append(JsonToken(literals[literal], index, end))
            index = end
            continue
        match = _NUMBER.match(text, index)
        if match is not None:
            tokens.append(JsonToken("number", index, match.end()))
            index = match.end()
            continue
        raise ValueError("JSON content contains an unexpected token")
    return tuple(tokens)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKey("duplicate object key")
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise ValueError("JSON number is not finite")


def _semantic_view(
    text: str,
    tokens: tuple[JsonToken, ...],
    *,
    allow_extensions: bool,
) -> JsonValue:
    cleaned = list(text)
    significant = [token for token in tokens if token.kind not in {"whitespace", "comment"}]
    for token in tokens:
        if token.kind != "comment":
            continue
        for index in range(token.start, token.end):
            if cleaned[index] not in "\r\n":
                cleaned[index] = " "
    if allow_extensions:
        for index, token in enumerate(significant[:-1]):
            if token.kind == "comma" and significant[index + 1].kind in {
                "close-array",
                "close-object",
            }:
                cleaned[token.start] = " "
    try:
        parsed = json.loads(
            "".join(cleaned),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateObjectKey:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("semantic JSON parsing failed") from exc
    return _json_value(parsed)


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON number is not finite")
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in cast("list[object]", value)]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in cast("dict[str, object]", value).items()}
    raise ValueError("value is not JSON-compatible")


class _StructureParser:
    """Derive source spans from tokens after json.loads validates semantics."""

    def __init__(self, text: str, tokens: tuple[JsonToken, ...]) -> None:
        self._text = text
        self._tokens = tuple(
            token for token in tokens if token.kind not in {"whitespace", "comment"}
        )
        self._index = 0

    def parse(self) -> JsonNode:
        node = self._value()
        if self._index != len(self._tokens):
            raise ValueError("JSON document contains more than one value")
        return node

    def _peek(self) -> JsonToken | None:
        return self._tokens[self._index] if self._index < len(self._tokens) else None

    def _take(self, kind: TokenKind | None = None) -> JsonToken:
        token = self._peek()
        if token is None or (kind is not None and token.kind != kind):
            raise ValueError("JSON token sequence is malformed")
        self._index += 1
        return token

    def _value(self) -> JsonNode:
        token = self._peek()
        if token is None:
            raise ValueError("JSON value is missing")
        if token.kind == "open-object":
            return self._object()
        if token.kind == "open-array":
            return self._array()
        if token.kind not in {"string", "number", "true", "false", "null"}:
            raise ValueError("JSON value token is invalid")
        self._take()
        return JsonNode(
            "scalar",
            token.start,
            token.end,
            _json_value(json.loads(self._text[token.start : token.end])),
        )

    def _object(self) -> JsonNode:
        opening = self._take("open-object")
        members: list[JsonMember] = []
        value: dict[str, JsonValue] = {}
        while (token := self._peek()) is not None and token.kind != "close-object":
            key_token = self._take("string")
            key = cast("str", json.loads(self._text[key_token.start : key_token.end]))
            self._take("colon")
            child = self._value()
            comma = self._take("comma") if self._peek_kind() == "comma" else None
            members.append(JsonMember(key, key_token, child, comma))
            value[key] = child.value
            if comma is None and self._peek_kind() != "close-object":
                raise ValueError("JSON object members require a comma")
        closing = self._take("close-object")
        return JsonNode(
            "object",
            opening.start,
            closing.end,
            value,
            opening,
            closing,
            tuple(members),
        )

    def _array(self) -> JsonNode:
        opening = self._take("open-array")
        elements: list[JsonNode] = []
        commas: list[JsonToken | None] = []
        while (token := self._peek()) is not None and token.kind != "close-array":
            elements.append(self._value())
            comma = self._take("comma") if self._peek_kind() == "comma" else None
            commas.append(comma)
            if comma is None and self._peek_kind() != "close-array":
                raise ValueError("JSON array elements require a comma")
        closing = self._take("close-array")
        return JsonNode(
            "array",
            opening.start,
            closing.end,
            [element.value for element in elements],
            opening,
            closing,
            elements=tuple(elements),
            commas=tuple(commas),
        )

    def _peek_kind(self) -> TokenKind | None:
        token = self._peek()
        return token.kind if token is not None else None


def _parse(content: bytes, kind: AdapterKind, *, fragment: bool = False) -> JsonDocument:
    label = "JSONC" if kind is AdapterKind.JSONC else "JSON"
    text = decode_utf8(content, label)
    try:
        tokens = _lex(text, allow_comments=kind is AdapterKind.JSONC)
        semantic = _semantic_view(
            text,
            tokens,
            allow_extensions=kind is AdapterKind.JSONC,
        )
        root = _StructureParser(text, tokens).parse()
        if root.value != semantic:
            raise ValueError("lexical and semantic JSON views disagree")
    except _DuplicateObjectKey as exc:
        raise ControlPlaneError(f"{label} content contains a duplicate object key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        noun = "fragment" if fragment else "content"
        detail = "a single JSON value" if fragment else f"valid {label}"
        raise ControlPlaneError(f"{noun} must contain {detail}") from exc
    return JsonDocument(text, root)


def container_value_without_comments(content: bytes, kind: AdapterKind) -> JsonValue | None:
    """Return container semantics only when deleting it cannot discard JSONC comments."""
    if kind not in {AdapterKind.JSON, AdapterKind.JSONC}:
        raise ControlPlaneError("JSON container inspection requires a JSON-family adapter")
    text = decode_utf8(content, kind.value.upper())
    try:
        tokens = _lex(text, allow_comments=kind is AdapterKind.JSONC)
    except ValueError as exc:
        raise ControlPlaneError("content is not valid JSON-family syntax") from exc
    if any(token.kind == "comment" for token in tokens):
        return None
    return _parse(content, kind).root.value


def _scope(kind: AdapterKind, value: str) -> ScopeSpec:
    try:
        normalized = normalize_scope(kind, value)
    except ValueError as exc:
        raise ControlPlaneError(f"{kind.value.upper()} scope is not canonical") from exc
    if normalized.startswith("key:"):
        return ScopeSpec(
            normalized,
            "key",
            decode_json_pointer(normalized.removeprefix("key:")),
        )
    if normalized.startswith("set:"):
        pointer, identity = normalized.removeprefix("set:").rsplit("#value=", 1)
        return ScopeSpec(
            normalized,
            "set",
            decode_json_pointer(pointer),
            identity=unquote(identity),
        )
    pointer, binding = normalized.removeprefix("keyed-set:").rsplit("#", 1)
    identity_key, identity = binding.split("=", 1)
    return ScopeSpec(
        normalized,
        "keyed-set",
        decode_json_pointer(pointer),
        identity_key=unquote(identity_key),
        identity=unquote(identity),
    )


def _object_member(node: JsonNode, key: str) -> tuple[int, JsonMember] | None:
    if node.kind != "object":
        return None
    matches = [(index, member) for index, member in enumerate(node.members) if member.key == key]
    if len(matches) > 1:
        raise ControlPlaneError("JSON content contains a duplicate object key")
    return matches[0] if matches else None


def _node_at(root: JsonNode, path: tuple[str, ...]) -> JsonNode | None:
    current = root
    for component in path:
        if current.kind == "object":
            found = _object_member(current, component)
            if found is None:
                return None
            current = found[1].value
            continue
        if current.kind == "array" and component.isdecimal():
            index = int(component)
            if index >= len(current.elements):
                return None
            current = current.elements[index]
            continue
        return None
    return current


def _scalar_identity(value: JsonValue, *, casefold: bool) -> str | None:
    if isinstance(value, (list, dict)):
        return None
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        return normalized.casefold() if casefold else normalized
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _key_location(root: JsonNode, path: tuple[str, ...]) -> LocatedUnit | None:
    if not path:
        raise ControlPlaneError("JSON key scope must identify an object member")
    parent = _node_at(root, path[:-1])
    if parent is None:
        return None
    if parent.kind != "object":
        raise ControlPlaneError("JSON key scope parent is not an object")
    found = _object_member(parent, path[-1])
    if found is None:
        return None
    index, member = found
    return LocatedUnit(member.value, parent, index, member)


def _array_location(root: JsonNode, spec: ScopeSpec) -> LocatedUnit | None:
    container = _node_at(root, spec.path)
    if container is None:
        return None
    if container.kind != "array":
        raise ControlPlaneError("JSON set scope does not identify an array")
    matches: list[tuple[int, JsonNode]] = []
    seen: set[str] = set()
    for index, element in enumerate(container.elements):
        if spec.kind == "set":
            identity = _scalar_identity(element.value, casefold=True)
        else:
            identity = None
            if element.kind == "object" and spec.identity_key is not None:
                member = _object_member(element, spec.identity_key)
                if member is not None:
                    identity = _scalar_identity(member[1].value.value, casefold=False)
        if identity is None:
            continue
        if identity in seen:
            label = "set identity" if spec.kind == "set" else "keyed-set identity"
            raise ControlPlaneError(f"JSON content contains a duplicate {label}")
        seen.add(identity)
        wanted = spec.identity.casefold() if spec.kind == "set" and spec.identity else spec.identity
        if identity == wanted:
            matches.append((index, element))
    if not matches:
        return None
    index, node = matches[0]
    return LocatedUnit(node, container, index)


def _locate(root: JsonNode, spec: ScopeSpec) -> LocatedUnit | None:
    return _key_location(root, spec.path) if spec.kind == "key" else _array_location(root, spec)


def _unit(document: JsonDocument, spec: ScopeSpec) -> AdapterUnit | None:
    located = _locate(document.root, spec)
    if located is None:
        return None
    raw = document.text[located.node.start : located.node.end].encode()
    return AdapterUnit(
        spec.normalized,
        located.node.value,
        raw,
        semantic_digest(located.node.value),
    )


def _check_fragment_identity(spec: ScopeSpec, value: JsonValue) -> None:
    if spec.kind == "key":
        return
    if spec.kind == "set":
        identity = _scalar_identity(value, casefold=True)
        wanted = spec.identity.casefold() if spec.identity else spec.identity
    else:
        if not isinstance(value, dict) or spec.identity_key not in value:
            raise ControlPlaneError("JSON keyed-set fragment is missing its identity key")
        identity = _scalar_identity(value[spec.identity_key], casefold=False)
        wanted = spec.identity
    if identity != wanted:
        raise ControlPlaneError("JSON fragment does not match its declared identity")


def _check_declared_value(actual: JsonValue, declared: JsonValue | bytes | None) -> None:
    if declared is not None and (
        isinstance(declared, bytes) or semantic_digest(declared) != semantic_digest(actual)
    ):
        raise ControlPlaneError("JSON fragment does not match its declared semantic value")


def _semantically_equal(left: JsonValue, right: JsonValue) -> bool:
    return semantic_digest(left) == semantic_digest(right)


def _deletion_edits(
    located: LocatedUnit,
    text: str | None = None,
    *,
    prune_whitespace: bool = False,
) -> list[tuple[int, int, str]]:
    # Delete the semantic code and its separator as disjoint spans. Comments
    # and whitespace between them are consumer bytes and must survive removal.
    if located.member is not None:
        start = located.member.key_token.start
        end = located.member.value.end
        comma = located.member.comma
        previous_comma = (
            located.container.members[located.index - 1].comma if located.index > 0 else None
        )
    else:
        start = located.node.start
        end = located.node.end
        comma = located.container.commas[located.index]
        previous_comma = located.container.commas[located.index - 1] if located.index > 0 else None
    if prune_whitespace and text is not None:
        count = (
            len(located.container.members)
            if located.container.kind == "object"
            else len(located.container.elements)
        )
        if comma is not None and located.index + 1 < count:
            next_start = (
                located.container.members[located.index + 1].key_token.start
                if located.container.kind == "object"
                else located.container.elements[located.index + 1].start
            )
            separator = text[end:next_start]
            if separator.replace(",", "", 1).strip() == "":
                return [(start, next_start, "")]
        if previous_comma is not None:
            separator = text[previous_comma.start : start]
            if separator.replace(",", "", 1).strip() == "":
                return [(previous_comma.start, end, "")]
    edits = [(start, end, "")]
    selected_comma = comma if comma is not None else previous_comma
    if selected_comma is not None:
        edits.append((selected_comma.start, selected_comma.end, ""))
    return edits


def _prune_empty_object_ancestors(
    content: bytes,
    kind: AdapterKind,
    path: tuple[str, ...],
) -> bytes:
    """Remove empty parent objects known to originate in a platform-created file."""
    parent = path[:-1]
    while parent:
        document = _parse(content, kind)
        node = _node_at(document.root, parent)
        if node is None or node.kind != "object" or node.value != {}:
            break
        raw = document.text[node.start : node.end].encode()
        if container_value_without_comments(raw, kind) != {}:
            break
        located = _key_location(document.root, parent)
        if located is None:
            break
        content = apply_edits(
            document.text,
            _deletion_edits(located, document.text, prune_whitespace=True),
        ).encode()
        parent = parent[:-1]
    return content


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def _line_start(text: str, index: int) -> int:
    return text.rfind("\n", 0, index) + 1


def _item_start(container: JsonNode, index: int) -> int:
    if container.kind == "object":
        return container.members[index].key_token.start
    return container.elements[index].start


def _item_end(container: JsonNode, index: int) -> int:
    if container.kind == "object":
        return container.members[index].value.end
    return container.elements[index].end


def _item_comma(container: JsonNode, index: int) -> JsonToken | None:
    if container.kind == "object":
        return container.members[index].comma
    return container.commas[index]


def _append(container: JsonNode, text: str, fragment: str) -> str:
    if container.opening is None or container.closing is None:
        raise ControlPlaneError("JSON insertion target has no bounded container")
    count = len(container.members) if container.kind == "object" else len(container.elements)
    newline = _newline(text)
    fragment = fragment.replace("\r\n", "\n").replace("\n", newline)
    body = text[container.opening.end : container.closing.start]
    if "\n" not in body:
        if count == 0:
            return apply_edits(text, [(container.opening.end, container.opening.end, fragment)])
        last_comma = _item_comma(container, count - 1)
        if last_comma is not None:
            insertion = f" {fragment},"
            return apply_edits(text, [(last_comma.end, last_comma.end, insertion)])
        end = _item_end(container, count - 1)
        return apply_edits(text, [(end, end, f", {fragment}")])

    closing_line = _line_start(text, container.closing.start)
    closing_indent = text[closing_line : container.closing.start]
    if closing_indent.strip():
        raise ControlPlaneError("JSON closing delimiter is not independently addressable")
    if count:
        first_start = _item_start(container, 0)
        first_line = _line_start(text, first_start)
        child_indent = text[first_line:first_start]
        if child_indent.strip():
            child_indent = f"{closing_indent}  "
    else:
        child_indent = f"{closing_indent}  "
    indented = fragment.replace(newline, f"{newline}{child_indent}")
    edits: list[tuple[int, int, str]] = [
        (closing_line, closing_line, f"{child_indent}{indented}"),
    ]
    # Match the existing container's trailing-comma style; changing that style
    # would rewrite consumer formatting outside the newly inserted unit.
    trailing = count > 0 and _item_comma(container, count - 1) is not None
    if trailing:
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented},{newline}")
    elif count:
        end = _item_end(container, count - 1)
        edits.append((end, end, ","))
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented}{newline}")
    else:
        edits[0] = (closing_line, closing_line, f"{child_indent}{indented}{newline}")
    return apply_edits(text, edits)


class _JsonFamilyAdapter:
    """Compose selected JSON-family units through exact lexical splices."""

    kind: AdapterKind

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        document = _parse(content, self.kind)
        specs = [_scope(self.kind, scope) for scope in scopes]
        normalized = [spec.normalized for spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("JSON inspection contains a duplicate scope")
        units = [
            unit
            for spec in sorted(specs, key=lambda item: item.normalized.encode("utf-8"))
            if (unit := _unit(document, spec)) is not None
        ]
        return AdapterState(content, tuple(units))

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        specs = [(change, _scope(self.kind, change.scope)) for change in changes]
        normalized = [spec.normalized for _, spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("JSON rendering contains a duplicate change scope")
        content = state.content
        for change, spec in sorted(specs, key=lambda item: item[1].normalized.encode("utf-8")):
            document = _parse(content, self.kind)
            located = _locate(document.root, spec)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating JSON change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("JSON removal cannot carry content")
                if located is None:
                    raise ControlPlaneError("JSON removal scope is not present")
                content = apply_edits(
                    document.text,
                    _deletion_edits(
                        located,
                        document.text,
                        prune_whitespace=change.prune_empty_ancestors,
                    ),
                ).encode()
                if change.prune_empty_ancestors and spec.kind == "key":
                    content = _prune_empty_object_ancestors(content, self.kind, spec.path)
                _parse(content, self.kind)
                continue
            if change.content is None:
                raise ControlPlaneError("mutating JSON change requires a bounded fragment")
            fragment_document = _parse(change.content, self.kind, fragment=True)
            desired = fragment_document.root.value
            _check_declared_value(desired, change.value)
            _check_fragment_identity(spec, desired)
            if change.kind is ActionKind.ADOPT:
                if located is None or not _semantically_equal(located.node.value, desired):
                    raise ControlPlaneError("JSON adoption requires an equal existing value")
                continue
            if change.kind is ActionKind.CREATE:
                if located is not None:
                    raise ControlPlaneError("JSON creation scope already exists")
                content = self._create(document, spec, fragment_document.text).encode()
                _parse(content, self.kind)
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("JSON adapter received an unsupported action")
            if located is None:
                raise ControlPlaneError("JSON update scope is not present")
            if _semantically_equal(located.node.value, desired):
                continue
            content = apply_edits(
                document.text,
                [(located.node.start, located.node.end, fragment_document.text)],
            ).encode()
            _parse(content, self.kind)
        return content

    def _create(self, document: JsonDocument, spec: ScopeSpec, fragment: str) -> str:
        if spec.kind == "key":
            if not spec.path:
                raise ControlPlaneError("JSON key scope must identify an object member")
            parent = _node_at(document.root, spec.path[:-1])
            if parent is None:
                grandparent = _node_at(document.root, spec.path[:-2])
                if grandparent is None:
                    raise ControlPlaneError("JSON creation parent scope is not present")
                if grandparent.kind != "object":
                    raise ControlPlaneError("JSON creation parent is not an object")
                parent_key = json.dumps(spec.path[-2], ensure_ascii=False)
                member_key = json.dumps(spec.path[-1], ensure_ascii=False)
                return _append(
                    grandparent,
                    document.text,
                    f"{parent_key}: {{{member_key}: {fragment}}}",
                )
            if parent.kind != "object":
                raise ControlPlaneError("JSON creation parent is not an object")
            member = f"{json.dumps(spec.path[-1], ensure_ascii=False)}: {fragment}"
            return _append(parent, document.text, member)
        container = _node_at(document.root, spec.path)
        if container is None:
            if not spec.path:
                raise ControlPlaneError("JSON set container is not present")
            parent = _node_at(document.root, spec.path[:-1])
            if parent is None:
                if spec.kind != "keyed-set":
                    raise ControlPlaneError("JSON set container parent is not present")
                grandparent = _node_at(document.root, spec.path[:-2])
                if grandparent is None:
                    raise ControlPlaneError("JSON set container parent is not present")
                if grandparent.kind != "object":
                    raise ControlPlaneError("JSON set container grandparent is not an object")
                parent_key = json.dumps(spec.path[-2], ensure_ascii=False)
                member_key = json.dumps(spec.path[-1], ensure_ascii=False)
                return _append(
                    grandparent,
                    document.text,
                    f"{parent_key}: {{{member_key}: [{fragment}]}}",
                )
            if parent.kind != "object":
                raise ControlPlaneError("JSON set container parent is not an object")
            member = f"{json.dumps(spec.path[-1], ensure_ascii=False)}: [{fragment}]"
            return _append(parent, document.text, member)
        if container.kind != "array":
            raise ControlPlaneError("JSON set scope does not identify an array")
        return _append(container, document.text, fragment)


class JsonAdapter(_JsonFamilyAdapter):
    """Compose strict JSON semantic units without reserializing the document."""

    kind = AdapterKind.JSON


class JsoncAdapter(_JsonFamilyAdapter):
    """Compose comment- and trailing-comma-tolerant JSONC semantic units."""

    kind = AdapterKind.JSONC
