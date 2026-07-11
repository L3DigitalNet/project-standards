"""Compose YAML semantic units through PyYAML-proven source boundaries.

PyYAML's safe composer supplies the semantic tree and exact character marks;
``safe_load`` supplies normalized values. Rendering never dumps a consumer
document. It splices only a selected node, mapping entry, or keyed sequence
entry and rejects aliases, anchors, merges, or flow containers when their marks
cannot prove an independently editable region.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import cast
from urllib.parse import unquote

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, Token

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

_BARE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$", re.ASCII)
_YAML_IMPLICIT = frozenset(
    {
        "false",
        "n",
        "no",
        "null",
        "off",
        "on",
        "true",
        "y",
        "yes",
        "~",
    }
)


@dataclass(frozen=True, slots=True)
class YamlDocument:
    """One safe-composed YAML document and its exact source text."""

    text: str
    root: Node
    tokens: tuple[Token, ...]


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """One normalized YAML selector decomposed for tree lookup."""

    normalized: str
    path: tuple[str, ...]
    identity_key: str | None = None
    identity: str | None = None

    @property
    def keyed(self) -> bool:
        return self.identity_key is not None


@dataclass(frozen=True, slots=True)
class LocatedUnit:
    """One selected node with its independently removable parent entry."""

    node: Node
    container: MappingNode | SequenceNode
    index: int
    lower_bound: int
    key_node: ScalarNode | None = None


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("YAML content is not valid UTF-8") from exc


def _node_start(node: Node) -> int:
    return node.start_mark.index


def _node_end(node: Node) -> int:
    return node.end_mark.index


def _node_column(node: Node) -> int:
    return node.start_mark.column


def _content_end(node: Node) -> int:
    """Return the last semantic token, excluding block trailing layout."""
    if isinstance(node, (MappingNode, SequenceNode)) and not node.flow_style:
        children = _children(node)
        if children:
            return max(_content_end(child) for child in children)
    return _node_end(node)


def _children(node: Node) -> tuple[Node, ...]:
    if isinstance(node, MappingNode):
        return tuple(child for pair in node.value for child in pair)
    if isinstance(node, SequenceNode):
        return tuple(node.value)
    return ()


def _mapping_key(node: Node) -> str:
    if not isinstance(node, ScalarNode):
        raise ControlPlaneError("YAML mappings must use scalar keys")
    return node.value


def _validate_duplicate_keys(node: Node, visited: set[int] | None = None) -> None:
    seen_nodes: set[int] = visited if visited is not None else set()
    marker = id(node)
    if marker in seen_nodes:
        return
    seen_nodes.add(marker)
    if isinstance(node, MappingNode):
        keys: set[str] = set()
        for key_node, value_node in node.value:
            key = _mapping_key(key_node)
            if key in keys:
                raise ControlPlaneError("YAML content contains a duplicate mapping key")
            keys.add(key)
            _validate_duplicate_keys(value_node, seen_nodes)
        return
    if isinstance(node, SequenceNode):
        for child in node.value:
            _validate_duplicate_keys(child, seen_nodes)


def _parse(content: bytes, *, fragment: bool = False) -> YamlDocument:
    text = _decode(content)
    try:
        # types-PyYAML leaves the convenience functions untyped even though
        # their SafeLoader-backed return contracts are stable and concrete.
        compose = cast("Callable[..., Node | None]", yaml.compose)
        scan = cast("Callable[..., Iterable[Token]]", yaml.scan)
        root = compose(text, Loader=yaml.SafeLoader)
        tokens = tuple(scan(text, Loader=yaml.SafeLoader))
    except yaml.YAMLError as exc:
        noun = "fragment" if fragment else "content"
        raise ControlPlaneError(f"YAML {noun} is not valid YAML") from exc
    if root is None:
        noun = "fragment" if fragment else "content"
        raise ControlPlaneError(f"YAML {noun} must contain one document")
    _validate_duplicate_keys(root)
    return YamlDocument(text, root, tokens)


def _pointer(value: str) -> tuple[str, ...]:
    return tuple(
        component.replace("~1", "/").replace("~0", "~") for component in value.split("/")[1:]
    )


def _scope(value: str) -> ScopeSpec:
    try:
        normalized = normalize_scope(AdapterKind.YAML, value)
    except ValueError as exc:
        raise ControlPlaneError("YAML scope is not canonical") from exc
    if normalized.startswith("key:"):
        return ScopeSpec(normalized, _pointer(normalized.removeprefix("key:")))
    pointer, binding = normalized.removeprefix("keyed-set:").rsplit("#", 1)
    identity_key, identity = binding.split("=", 1)
    return ScopeSpec(
        normalized,
        _pointer(pointer),
        unquote(identity_key),
        unquote(identity),
    )


def _mapping_member(node: Node, key: str) -> tuple[int, ScalarNode, Node] | None:
    if not isinstance(node, MappingNode):
        return None
    matches: list[tuple[int, ScalarNode, Node]] = []
    for index, (key_node, value_node) in enumerate(node.value):
        if _mapping_key(key_node) == key:
            matches.append((index, cast("ScalarNode", key_node), value_node))
    if len(matches) > 1:
        raise ControlPlaneError("YAML content contains a duplicate mapping key")
    return matches[0] if matches else None


def _has_merge_key(node: Node) -> bool:
    visited: set[int] = set()

    def visit(current: Node) -> bool:
        marker = id(current)
        if marker in visited:
            return False
        visited.add(marker)
        if isinstance(current, MappingNode):
            for key_node, value_node in current.value:
                if _mapping_key(key_node) == "<<":
                    return True
                if visit(value_node):
                    return True
        elif isinstance(current, SequenceNode):
            return any(visit(child) for child in current.value)
        return False

    return visit(node)


def _node_at(root: Node, path: tuple[str, ...]) -> Node | None:
    current = root
    for component in path:
        if isinstance(current, MappingNode):
            if any(_mapping_key(key) == "<<" for key, _ in current.value):
                raise ControlPlaneError("YAML selected path crosses a merge key")
            found = _mapping_member(current, component)
            if found is None:
                return None
            current = found[2]
            continue
        if isinstance(current, SequenceNode) and component.isdecimal():
            index = int(component)
            if index >= len(current.value):
                return None
            current = current.value[index]
            continue
        return None
    return current


def _key_location(root: Node, path: tuple[str, ...]) -> LocatedUnit | None:
    if not path:
        raise ControlPlaneError("YAML key scope must identify a mapping entry")
    parent = _node_at(root, path[:-1])
    if parent is None:
        return None
    if not isinstance(parent, MappingNode):
        raise ControlPlaneError("YAML key scope parent is not a mapping")
    if any(_mapping_key(key) == "<<" for key, _ in parent.value):
        raise ControlPlaneError("YAML selected mapping contains a merge key")
    found = _mapping_member(parent, path[-1])
    if found is None:
        return None
    index, key_node, value_node = found
    return LocatedUnit(value_node, parent, index, _node_end(key_node), key_node)


def _standalone_fragment(text: str, node: Node) -> str:
    fragment = text[_node_start(node) : _node_end(node)]
    if not isinstance(node, (MappingNode, SequenceNode)) or node.flow_style:
        return fragment
    column = _node_column(node)
    if column == 0:
        return fragment
    lines = fragment.splitlines(keepends=True)
    prefix = " " * column
    for index in range(1, len(lines)):
        if lines[index].startswith(prefix):
            lines[index] = lines[index][column:]
    return "".join(lines)


def _json_value(value: object, active: set[int] | None = None) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ControlPlaneError("selected YAML value is not canonical JSON")
        return value
    stack: set[int] = active if active is not None else set()
    marker = id(value)
    if marker in stack:
        raise ControlPlaneError("selected YAML value contains a recursive alias")
    stack.add(marker)
    try:
        if isinstance(value, list):
            return [_json_value(child, stack) for child in cast("list[object]", value)]
        if isinstance(value, dict):
            mapping = cast("dict[object, object]", value)
            if not all(isinstance(key, str) for key in mapping):
                raise ControlPlaneError("selected YAML mapping has a non-string key")
            return {cast("str", key): _json_value(child, stack) for key, child in mapping.items()}
    finally:
        stack.remove(marker)
    raise ControlPlaneError("selected YAML value is not JSON-compatible")


def _semantic_fragment(fragment: str) -> JsonValue:
    try:
        return _json_value(yaml.safe_load(fragment))
    except yaml.YAMLError as exc:
        raise ControlPlaneError("selected YAML node is not independently loadable") from exc


def _assert_bounded(document: YamlDocument, located: LocatedUnit) -> None:
    if _has_merge_key(located.node):
        raise ControlPlaneError("selected YAML node contains a merge key")
    start = _node_start(located.node)
    end = _node_end(located.node)
    if start < located.lower_bound or end < start:
        raise ControlPlaneError("selected YAML node uses an unbounded anchor or alias")
    visited: set[int] = set()

    def visit(node: Node) -> None:
        marker = id(node)
        if marker in visited:
            return
        visited.add(marker)
        if _node_start(node) < start or _node_end(node) > end:
            raise ControlPlaneError("selected YAML node uses an unbounded anchor or alias")
        for child in _children(node):
            visit(child)

    visit(located.node)
    for token in document.tokens:
        if isinstance(token, (AnchorToken, AliasToken)) and (
            located.lower_bound <= token.start_mark.index < end
        ):
            raise ControlPlaneError("selected YAML node contains an anchor or alias")


def _scalar_identity(value: JsonValue) -> str | None:
    if isinstance(value, (list, dict)):
        return None
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _identity_from_item(document: YamlDocument, node: Node, key: str) -> str | None:
    found = _mapping_member(node, key)
    if found is None:
        return None
    value_node = found[2]
    if not isinstance(value_node, ScalarNode):
        return None
    value = _semantic_fragment(_standalone_fragment(document.text, value_node))
    return _scalar_identity(value)


def _keyed_location(document: YamlDocument, spec: ScopeSpec) -> LocatedUnit | None:
    container = _node_at(document.root, spec.path)
    if container is None:
        return None
    if not isinstance(container, SequenceNode):
        raise ControlPlaneError("YAML keyed-set scope does not identify a sequence")
    if container.flow_style:
        raise ControlPlaneError("YAML keyed-set flow sequences are not independently editable")
    if spec.identity_key is None:
        raise ControlPlaneError("YAML keyed-set scope is missing its identity key")
    seen: set[str] = set()
    match: tuple[int, Node] | None = None
    for index, item in enumerate(container.value):
        identity = _identity_from_item(document, item, spec.identity_key)
        if identity is None:
            continue
        if identity in seen:
            raise ControlPlaneError("YAML content contains a duplicate keyed-set identity")
        seen.add(identity)
        if identity == spec.identity:
            match = (index, item)
    if match is None:
        return None
    index, node = match
    line_start = document.text.rfind("\n", 0, _node_start(node)) + 1
    return LocatedUnit(node, container, index, line_start)


def _locate(document: YamlDocument, spec: ScopeSpec) -> LocatedUnit | None:
    return (
        _keyed_location(document, spec) if spec.keyed else _key_location(document.root, spec.path)
    )


def _unit(document: YamlDocument, spec: ScopeSpec) -> AdapterUnit | None:
    located = _locate(document, spec)
    if located is None:
        return None
    _assert_bounded(document, located)
    raw_text = _standalone_fragment(document.text, located.node)
    value = _semantic_fragment(raw_text)
    return AdapterUnit(
        spec.normalized,
        value,
        raw_text.encode(),
        semantic_digest(value),
    )


def _fragment(content: bytes) -> tuple[YamlDocument, JsonValue, str]:
    document = _parse(content, fragment=True)
    if _has_merge_key(document.root):
        raise ControlPlaneError("YAML fragment contains a merge key")
    for token in document.tokens:
        if isinstance(token, (AnchorToken, AliasToken)):
            raise ControlPlaneError("YAML fragment contains an anchor or alias")
    value = _json_value(yaml.safe_load(document.text))
    return document, value, document.text.rstrip("\r\n")


def _check_declared_value(actual: JsonValue, declared: JsonValue | bytes | None) -> None:
    if declared is not None and (
        isinstance(declared, bytes) or semantic_digest(declared) != semantic_digest(actual)
    ):
        raise ControlPlaneError("YAML fragment does not match its declared semantic value")


def _check_identity(spec: ScopeSpec, value: JsonValue) -> None:
    if not spec.keyed:
        return
    if not isinstance(value, dict) or spec.identity_key not in value:
        raise ControlPlaneError("YAML keyed-set fragment is missing its identity key")
    identity = _scalar_identity(value[spec.identity_key])
    if identity != spec.identity:
        raise ControlPlaneError("YAML fragment does not match its declared identity")


def _semantic_equal(left: JsonValue, right: JsonValue) -> bool:
    return semantic_digest(left) == semantic_digest(right)


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def _normalize_newlines(text: str, newline: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", newline)


def _line_start(text: str, index: int) -> int:
    return text.rfind("\n", 0, index) + 1


def _after_line(text: str, index: int) -> int:
    newline = text.find("\n", index)
    return len(text) if newline == -1 else newline + 1


def _indent_fragment(fragment: str, column: int, newline: str) -> str:
    normalized = _normalize_newlines(fragment, newline)
    return normalized.replace(newline, f"{newline}{' ' * column}")


def _fragment_is_block_collection(document: YamlDocument) -> bool:
    return isinstance(document.root, (MappingNode, SequenceNode)) and not document.root.flow_style


def _replacement(
    source: YamlDocument,
    located: LocatedUnit,
    fragment_document: YamlDocument,
    fragment: str,
) -> str:
    newline = _newline(source.text)
    if not _fragment_is_block_collection(fragment_document):
        return _normalize_newlines(fragment, newline)
    if (
        located.key_node is not None
        and located.key_node.start_mark.line == located.node.start_mark.line
    ):
        column = _node_column(located.key_node) + 2
        return f"{newline}{' ' * column}{_indent_fragment(fragment, column, newline)}"
    column = _node_column(located.node)
    return _indent_fragment(fragment, column, newline)


def _deletion_span(document: YamlDocument, located: LocatedUnit) -> tuple[int, int, str]:
    if located.key_node is not None:
        start = _line_start(document.text, _node_start(located.key_node))
    else:
        start = _line_start(document.text, _node_start(located.node))
    return (start, _content_end(located.node), "")


def _apply_edit(text: str, edit: tuple[int, int, str]) -> str:
    start, end, replacement = edit
    return f"{text[:start]}{replacement}{text[end:]}"


def _canonical_key(key: str) -> str:
    if _BARE_KEY.fullmatch(key) and key.casefold() not in _YAML_IMPLICIT:
        return key
    return json.dumps(key, ensure_ascii=False)


def _mapping_indent(node: MappingNode) -> int:
    if node.value:
        return _node_column(node.value[0][0])
    return _node_column(node)


def _append_mapping_entry(
    document: YamlDocument,
    parent: MappingNode,
    key: str,
    fragment_document: YamlDocument,
    fragment: str,
) -> str:
    if parent.flow_style:
        raise ControlPlaneError("YAML flow mappings are not independently editable")
    newline = _newline(document.text)
    indent = _mapping_indent(parent)
    key_text = _canonical_key(key)
    if _fragment_is_block_collection(fragment_document):
        child_indent = indent + 2
        value = _indent_fragment(fragment, child_indent, newline)
        entry = f"{' ' * indent}{key_text}:{newline}{' ' * child_indent}{value}{newline}"
    else:
        value = _normalize_newlines(fragment, newline)
        entry = f"{' ' * indent}{key_text}: {value}{newline}"
    position = _after_line(document.text, _content_end(parent))
    prefix = "" if position == 0 or document.text[position - 1] in "\r\n" else newline
    return _apply_edit(document.text, (position, position, f"{prefix}{entry}"))


def _append_sequence_entry(
    document: YamlDocument,
    parent: SequenceNode,
    fragment_document: YamlDocument,
    fragment: str,
) -> str:
    if parent.flow_style:
        raise ControlPlaneError("YAML flow sequences are not independently editable")
    newline = _newline(document.text)
    indent = _node_column(parent)
    value = _indent_fragment(fragment, indent + 2, newline)
    entry = f"{' ' * indent}- {value}{newline}"
    position = _after_line(document.text, _content_end(parent))
    prefix = "" if position == 0 or document.text[position - 1] in "\r\n" else newline
    return _apply_edit(document.text, (position, position, f"{prefix}{entry}"))


class YamlAdapter:
    """Compose YAML mapping entries and stable keyed sequence items."""

    kind = AdapterKind.YAML

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        document = _parse(content)
        specs = [_scope(scope) for scope in scopes]
        normalized = [spec.normalized for spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("YAML inspection contains a duplicate scope")
        units = [
            unit
            for spec in sorted(specs, key=lambda item: item.normalized.encode("utf-8"))
            if (unit := _unit(document, spec)) is not None
        ]
        return AdapterState(content, tuple(units))

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        specs = [(change, _scope(change.scope)) for change in changes]
        normalized = [spec.normalized for _, spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("YAML rendering contains a duplicate change scope")
        content = state.content
        for change, spec in sorted(specs, key=lambda item: item[1].normalized.encode("utf-8")):
            document = _parse(content)
            located = _locate(document, spec)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating YAML change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("YAML removal cannot carry content")
                if located is None:
                    raise ControlPlaneError("YAML removal scope is not present")
                _assert_bounded(document, located)
                content = _apply_edit(document.text, _deletion_span(document, located)).encode()
                _parse(content)
                continue
            if change.content is None:
                raise ControlPlaneError("mutating YAML change requires a bounded fragment")
            fragment_document, desired, fragment = _fragment(change.content)
            _check_declared_value(desired, change.value)
            _check_identity(spec, desired)
            if change.kind is ActionKind.ADOPT:
                if located is None:
                    raise ControlPlaneError("YAML adoption requires an equal existing value")
                _assert_bounded(document, located)
                current = _semantic_fragment(_standalone_fragment(document.text, located.node))
                if not _semantic_equal(current, desired):
                    raise ControlPlaneError("YAML adoption requires an equal existing value")
                continue
            if change.kind is ActionKind.CREATE:
                if located is not None:
                    raise ControlPlaneError("YAML creation scope already exists")
                content = self._create(document, spec, fragment_document, fragment).encode()
                _parse(content)
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("YAML adapter received an unsupported action")
            if located is None:
                raise ControlPlaneError("YAML update scope is not present")
            _assert_bounded(document, located)
            current = _semantic_fragment(_standalone_fragment(document.text, located.node))
            if _semantic_equal(current, desired):
                continue
            replacement = _replacement(document, located, fragment_document, fragment)
            content = _apply_edit(
                document.text,
                (_node_start(located.node), _content_end(located.node), replacement),
            ).encode()
            _parse(content)
        return content

    def _create(
        self,
        document: YamlDocument,
        spec: ScopeSpec,
        fragment_document: YamlDocument,
        fragment: str,
    ) -> str:
        if not spec.keyed:
            if not spec.path:
                raise ControlPlaneError("YAML key scope must identify a mapping entry")
            parent = _node_at(document.root, spec.path[:-1])
            if parent is None:
                raise ControlPlaneError("YAML creation parent scope is not present")
            if not isinstance(parent, MappingNode):
                raise ControlPlaneError("YAML creation parent is not a mapping")
            if any(_mapping_key(key) == "<<" for key, _ in parent.value):
                raise ControlPlaneError("YAML creation parent contains a merge key")
            return _append_mapping_entry(
                document,
                parent,
                spec.path[-1],
                fragment_document,
                fragment,
            )
        parent = _node_at(document.root, spec.path)
        if parent is None:
            raise ControlPlaneError("YAML keyed-set container is not present")
        if not isinstance(parent, SequenceNode):
            raise ControlPlaneError("YAML keyed-set scope does not identify a sequence")
        return _append_sequence_entry(document, parent, fragment_document, fragment)
