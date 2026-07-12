"""Index EditorConfig properties so values can be spliced without reformatting."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
)
from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import AdapterKind, normalize_scope


@dataclass(frozen=True, slots=True)
class EditorConfigSection:
    """One normalized section occurrence and its physical source bounds."""

    name: str
    start: int
    header_end: int
    end: int


@dataclass(frozen=True, slots=True)
class EditorConfigProperty:
    """One property assignment with exact line and value spans."""

    section: str
    key: str
    value: str
    line_start: int
    source_end: int
    value_start: int
    value_end: int


@dataclass(frozen=True, slots=True)
class EditorConfigDocument:
    """Parsed EditorConfig structure over the original source text."""

    text: str
    sections: tuple[EditorConfigSection, ...]
    properties: tuple[EditorConfigProperty, ...]


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    """One normalized section/property selector."""

    normalized: str
    section: str
    key: str


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("EditorConfig content is not valid UTF-8") from exc


def _line_end_without_newline(line: str) -> int:
    return len(line.rstrip("\r\n"))


def _parse(content: bytes) -> EditorConfigDocument:
    text = _decode(content)
    raw_sections: list[tuple[str, int, int]] = []
    properties: list[EditorConfigProperty] = []
    section = "$global"
    offset = 0
    for line in text.splitlines(keepends=True):
        code_end = _line_end_without_newline(line)
        code = line[:code_end]
        stripped = code.strip()
        source_end = offset + len(line)
        if not stripped or stripped.startswith(("#", ";")):
            offset = source_end
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1].strip()
            if not name:
                raise ControlPlaneError("EditorConfig section name is empty")
            section = name
            raw_sections.append((name, offset, source_end))
            offset = source_end
            continue
        separators = [index for index in (code.find("="), code.find(":")) if index >= 0]
        if not separators:
            raise ControlPlaneError("EditorConfig content contains an invalid property line")
        separator = min(separators)
        key = code[:separator].strip().casefold()
        if not key:
            raise ControlPlaneError("EditorConfig property key is empty")
        raw_value = code[separator + 1 :]
        leading = len(raw_value) - len(raw_value.lstrip())
        trailing = len(raw_value.rstrip())
        value = raw_value.strip()
        properties.append(
            EditorConfigProperty(
                section,
                key,
                value,
                offset,
                source_end,
                offset + separator + 1 + leading,
                offset + separator + 1 + trailing,
            )
        )
        offset = source_end
    sections = tuple(
        EditorConfigSection(
            name,
            start,
            header_end,
            raw_sections[index + 1][1] if index + 1 < len(raw_sections) else len(text),
        )
        for index, (name, start, header_end) in enumerate(raw_sections)
    )
    return EditorConfigDocument(text, sections, tuple(properties))


def _scope(value: str) -> ScopeSpec:
    try:
        normalized = normalize_scope(AdapterKind.EDITORCONFIG, value)
    except ValueError as exc:
        raise ControlPlaneError("EditorConfig scope is not canonical") from exc
    section, key = normalized.removeprefix("property:").rsplit("#", 1)
    return ScopeSpec(normalized, unquote(section).strip(), unquote(key).strip().casefold())


def _section(document: EditorConfigDocument, name: str) -> EditorConfigSection | None:
    matches = [section for section in document.sections if section.name == name]
    if len(matches) > 1:
        raise ControlPlaneError("EditorConfig content contains a duplicate section")
    return matches[0] if matches else None


def _property(
    document: EditorConfigDocument,
    spec: ScopeSpec,
) -> EditorConfigProperty | None:
    if spec.section != "$global":
        _section(document, spec.section)
    matches = [
        prop
        for prop in document.properties
        if prop.section == spec.section and prop.key == spec.key
    ]
    if len(matches) > 1:
        raise ControlPlaneError("EditorConfig content contains a duplicate property")
    return matches[0] if matches else None


def _normalized_value(value: str) -> str:
    return value.strip().casefold()


def _unit(document: EditorConfigDocument, spec: ScopeSpec) -> AdapterUnit | None:
    prop = _property(document, spec)
    if prop is None:
        return None
    raw = document.text[prop.value_start : prop.value_end].encode()
    value = _normalized_value(prop.value)
    return AdapterUnit(spec.normalized, value, raw, semantic_digest(value))


def _fragment(content: bytes) -> tuple[str, str]:
    text = _decode(content)
    if "\n" in text or "\r" in text or not text.strip():
        raise ControlPlaneError("EditorConfig fragment must contain a single property value")
    physical = text.strip()
    return physical, _normalized_value(physical)


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def _apply(text: str, start: int, end: int, replacement: str) -> str:
    return f"{text[:start]}{replacement}{text[end:]}"


def _insertion_position(document: EditorConfigDocument, section: str) -> int | None:
    properties = [prop for prop in document.properties if prop.section == section]
    if properties:
        return properties[-1].source_end
    if section == "$global":
        if not document.sections:
            return len(document.text)
        first_section = document.sections[0].start
        return 0 if not document.text[:first_section].strip() else first_section
    found = _section(document, section)
    return found.header_end if found is not None else None


def _insert_property(
    document: EditorConfigDocument,
    spec: ScopeSpec,
    value: str,
) -> str:
    newline = _newline(document.text)
    position = _insertion_position(document, spec.section)
    assignment = f"{spec.key} = {value}{newline}"
    if position is not None:
        prefix = "" if position == 0 or document.text[position - 1] in "\r\n" else newline
        return _apply(document.text, position, position, f"{prefix}{assignment}")
    prefix = "" if not document.text or document.text.endswith(newline * 2) else newline
    if document.text and not document.text.endswith(("\n", "\r")):
        prefix = newline * 2
    return f"{document.text}{prefix}[{spec.section}]{newline}{assignment}"


class EditorConfigAdapter:
    """Compose normalized EditorConfig section/property units."""

    kind = AdapterKind.EDITORCONFIG

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        document = _parse(content)
        specs = [_scope(scope) for scope in scopes]
        normalized = [spec.normalized for spec in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("EditorConfig inspection contains a duplicate scope")
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
            raise ControlPlaneError("EditorConfig rendering contains a duplicate change scope")
        content = state.content
        for change, spec in sorted(specs, key=lambda item: item[1].normalized.encode("utf-8")):
            document = _parse(content)
            current = _property(document, spec)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating EditorConfig change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("EditorConfig removal cannot carry content")
                if current is None:
                    raise ControlPlaneError("EditorConfig removal scope is not present")
                content = _apply(document.text, current.line_start, current.source_end, "").encode()
                continue
            if change.content is None:
                raise ControlPlaneError("mutating EditorConfig change requires a property value")
            physical, desired = _fragment(change.content)
            if change.value is not None and change.value != desired:
                raise ControlPlaneError(
                    "EditorConfig fragment does not match its declared semantic value"
                )
            if change.kind is ActionKind.ADOPT:
                if current is None or _normalized_value(current.value) != desired:
                    raise ControlPlaneError(
                        "EditorConfig adoption requires an equal existing value"
                    )
                continue
            if change.kind is ActionKind.CREATE:
                if current is not None:
                    raise ControlPlaneError("EditorConfig creation scope already exists")
                content = _insert_property(document, spec, physical).encode()
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("EditorConfig adapter received an unsupported action")
            if current is None:
                raise ControlPlaneError("EditorConfig update scope is not present")
            if _normalized_value(current.value) == desired:
                continue
            content = _apply(
                document.text,
                current.value_start,
                current.value_end,
                physical,
            ).encode()
        _parse(content)
        return content
