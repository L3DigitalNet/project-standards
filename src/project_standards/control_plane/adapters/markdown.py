"""Compose formatter-stable Markdown blocks inside exact managed envelopes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    UnitChange,
)
from project_standards.control_plane.codec import content_digest
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import AdapterKind, normalize_scope

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_BEGIN = re.compile(r"^<!-- BEGIN project-standards:([^ ]+) -->$")
_END = re.compile(r"^<!-- END project-standards:([^ ]+) -->$")
_PRETTIER_START = "<!-- prettier-ignore-start -->"
_PRETTIER_END = "<!-- prettier-ignore-end -->"
_MANAGED_MARKER_TEXT = "project-standards:"


@dataclass(frozen=True, slots=True)
class MarkdownLine:
    """One physical line with absolute bounds and top-level status."""

    text: str
    start: int
    end: int
    top_level: bool


@dataclass(frozen=True, slots=True)
class MarkdownBlock:
    """One validated managed block and its complete Prettier envelope."""

    block_id: str
    content_start: int
    content_end: int
    envelope_start: int
    envelope_end: int


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    """Original Markdown text plus all validated managed envelopes."""

    text: str
    blocks: tuple[MarkdownBlock, ...]


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("Markdown content is not valid UTF-8") from exc


def _line_end_without_newline(line: str) -> int:
    if line.endswith("\r\n"):
        return len(line) - 2
    if line.endswith("\n"):
        return len(line) - 1
    return len(line)


def _lines(text: str) -> tuple[MarkdownLine, ...]:
    result: list[MarkdownLine] = []
    offset = 0
    fence: str | None = None
    segments = text.split("\n")
    for index, segment in enumerate(segments):
        if index == len(segments) - 1:
            if not segment:
                break
            physical = segment
        else:
            physical = f"{segment}\n"
        code = physical[: _line_end_without_newline(physical)]
        match = _FENCE.match(code)
        top_level = fence is None
        if match is not None:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
                top_level = False
            elif marker[0] == fence:
                top_level = False
                fence = None
        result.append(MarkdownLine(code, offset, offset + len(physical), top_level))
        offset += len(physical)
    return tuple(result)


def _blank(line: MarkdownLine) -> bool:
    return not line.text.strip()


def _marker_id(pattern: re.Pattern[str], line: MarkdownLine) -> str | None:
    if not line.top_level:
        return None
    match = pattern.fullmatch(line.text)
    return match.group(1) if match is not None else None


def _contains_marker_syntax(line: MarkdownLine) -> bool:
    return (
        ("<!--" in line.text and _MANAGED_MARKER_TEXT in line.text)
        or _PRETTIER_START in line.text
        or _PRETTIER_END in line.text
    )


def _validated_id(value: str) -> str:
    try:
        normalized = normalize_scope(AdapterKind.MARKDOWN_BLOCK, f"block:{value}")
    except ValueError as exc:
        raise ControlPlaneError("Markdown block marker contains a non-canonical ID") from exc
    marker_id = normalized.removeprefix("block:")
    if marker_id != value:
        raise ControlPlaneError("Markdown block marker contains a non-canonical ID")
    return marker_id


def _parse(content: bytes) -> MarkdownDocument:
    text = _decode(content)
    lines = _lines(text)
    blocks: list[MarkdownBlock] = []
    consumed: set[int] = set()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.top_level:
            index += 1
            continue
        if (
            _contains_marker_syntax(line)
            and line.text
            not in {
                _PRETTIER_START,
                _PRETTIER_END,
            }
            and _marker_id(_BEGIN, line) is None
            and _marker_id(_END, line) is None
        ):
            raise ControlPlaneError("Markdown managed marker must occupy an exact top-level line")
        if line.text != _PRETTIER_START:
            index += 1
            continue
        if index > 0 and not _blank(lines[index - 1]):
            raise ControlPlaneError(
                "Markdown Prettier range marker requires a preceding blank line"
            )
        if index + 2 >= len(lines) or not _blank(lines[index + 1]):
            raise ControlPlaneError("Markdown managed block has an invalid Prettier range envelope")
        block_id = _marker_id(_BEGIN, lines[index + 2])
        if block_id is None:
            raise ControlPlaneError("Markdown Prettier range start is orphaned")
        block_id = _validated_id(block_id)
        end_index = index + 3
        while end_index < len(lines):
            if _marker_id(_BEGIN, lines[end_index]) is not None:
                raise ControlPlaneError("Markdown managed blocks cannot be nested")
            ending_id = _marker_id(_END, lines[end_index])
            if ending_id is not None:
                if ending_id != block_id:
                    raise ControlPlaneError("Markdown managed end marker is orphaned")
                break
            if lines[end_index].top_level and lines[end_index].text in {
                _PRETTIER_START,
                _PRETTIER_END,
            }:
                raise ControlPlaneError("Markdown managed block has an orphaned range marker")
            end_index += 1
        if end_index >= len(lines):
            raise ControlPlaneError("Markdown managed begin marker is orphaned")
        if end_index + 2 >= len(lines) or not _blank(lines[end_index + 1]):
            raise ControlPlaneError("Markdown managed block has an invalid Prettier range envelope")
        if lines[end_index + 2].text != _PRETTIER_END:
            raise ControlPlaneError("Markdown managed block has an orphaned range marker")
        consumed.update({index, index + 2, end_index, end_index + 2})
        blocks.append(
            MarkdownBlock(
                block_id,
                lines[index + 2].end,
                lines[end_index].start,
                line.start,
                lines[end_index + 2].end,
            )
        )
        index = end_index + 3
    for line_index, line in enumerate(lines):
        if not line.top_level or line_index in consumed:
            continue
        if (
            line.text in {_PRETTIER_START, _PRETTIER_END}
            or _marker_id(_BEGIN, line) is not None
            or _marker_id(_END, line) is not None
        ):
            raise ControlPlaneError("Markdown managed marker is orphaned")
    ids = [block.block_id for block in blocks]
    if len(ids) != len(set(ids)):
        raise ControlPlaneError("Markdown content contains a duplicate managed block ID")
    return MarkdownDocument(text, tuple(blocks))


def _scope(value: str) -> tuple[str, str]:
    try:
        normalized = normalize_scope(AdapterKind.MARKDOWN_BLOCK, value)
    except ValueError as exc:
        raise ControlPlaneError("Markdown block scope is not canonical") from exc
    encoded = normalized.removeprefix("block:")
    return normalized, encoded


def _block(document: MarkdownDocument, marker_id: str) -> MarkdownBlock | None:
    matches = [block for block in document.blocks if block.block_id == marker_id]
    if len(matches) > 1:
        raise ControlPlaneError("Markdown content contains a duplicate managed block ID")
    return matches[0] if matches else None


def _normalized(content: bytes | str) -> bytes:
    raw = content.encode() if isinstance(content, str) else content
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("Markdown block content is not valid UTF-8") from exc
    return text.replace("\r\n", "\n").encode()


def _unit(document: MarkdownDocument, scope: str, marker_id: str) -> AdapterUnit | None:
    block = _block(document, marker_id)
    if block is None:
        return None
    raw = document.text[block.content_start : block.content_end].encode()
    value = _normalized(raw)
    return AdapterUnit(scope, value, raw, content_digest(value))


def _desired(content: bytes) -> tuple[str, bytes]:
    text = _decode(content)
    lines = _lines(text)
    for line in lines:
        if line.top_level and _contains_marker_syntax(line):
            raise ControlPlaneError("Markdown block fragment cannot contain a managed marker")
    normalized = _normalized(text)
    if not normalized.endswith(b"\n"):
        normalized += b"\n"
    return normalized.decode(), normalized


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def _physical(value: str, newline: str) -> str:
    return value.replace("\r\n", "\n").replace("\n", newline)


def _envelope(marker_id: str, content: str, newline: str) -> str:
    physical = _physical(content, newline)
    return (
        f"{_PRETTIER_START}{newline}{newline}"
        f"<!-- BEGIN project-standards:{marker_id} -->{newline}"
        f"{physical}"
        f"<!-- END project-standards:{marker_id} -->{newline}{newline}"
        f"{_PRETTIER_END}{newline}"
    )


def _apply(text: str, start: int, end: int, replacement: str) -> str:
    return f"{text[:start]}{replacement}{text[end:]}"


def _remove_span(document: MarkdownDocument, block: MarkdownBlock) -> tuple[int, int]:
    newline = _newline(document.text)
    start = block.envelope_start
    end = block.envelope_end
    consumed_preceding_separator = False
    if start >= len(newline) and document.text[:start].endswith(newline * 2):
        start -= len(newline)
        consumed_preceding_separator = True
    if not consumed_preceding_separator and document.text[end:].startswith(newline):
        end += len(newline)
    return start, end


def _insert(document: MarkdownDocument, envelope: str) -> str:
    newline = _newline(document.text)
    position = document.blocks[-1].envelope_end if document.blocks else len(document.text)
    before = document.text[:position]
    after = document.text[position:]
    prefix = "" if not before or before.endswith(newline * 2) else newline
    if before and not before.endswith(("\n", "\r")):
        prefix = newline * 2
    suffix = "" if not after or after.startswith(newline) else newline
    return f"{before}{prefix}{envelope}{suffix}{after}"


class MarkdownBlockAdapter:
    """Compose exact managed Markdown blocks protected from Prettier."""

    kind = AdapterKind.MARKDOWN_BLOCK

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState:
        document = _parse(content)
        specs = [_scope(scope) for scope in scopes]
        normalized = [scope for scope, _ in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("Markdown inspection contains a duplicate scope")
        units = [
            unit
            for scope, marker_id in sorted(specs, key=lambda item: item[0].encode("utf-8"))
            if (unit := _unit(document, scope, marker_id)) is not None
        ]
        return AdapterState(content, tuple(units))

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes:
        specs = [(change, *_scope(change.scope)) for change in changes]
        normalized = [scope for _, scope, _ in specs]
        if len(normalized) != len(set(normalized)):
            raise ControlPlaneError("Markdown rendering contains a duplicate change scope")
        content = state.content
        for change, scope, marker_id in sorted(specs, key=lambda item: item[1].encode("utf-8")):
            document = _parse(content)
            current = _block(document, marker_id)
            if change.kind in {ActionKind.NOOP, ActionKind.PRESERVE}:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("non-mutating Markdown change cannot carry content")
                continue
            if change.kind is ActionKind.REMOVE:
                if change.content is not None or change.value is not None:
                    raise ControlPlaneError("Markdown removal cannot carry content")
                if current is None:
                    raise ControlPlaneError("Markdown removal scope is not present")
                start, end = _remove_span(document, current)
                content = _apply(document.text, start, end, "").encode()
                continue
            if change.content is None:
                raise ControlPlaneError("mutating Markdown change requires block content")
            desired_text, desired = _desired(change.content)
            if change.value is not None and (
                not isinstance(change.value, bytes) or _normalized(change.value) != desired
            ):
                raise ControlPlaneError(
                    "Markdown fragment does not match its declared semantic value"
                )
            if change.kind is ActionKind.ADOPT:
                if current is None:
                    raise ControlPlaneError("Markdown adoption requires equal existing content")
                raw = document.text[current.content_start : current.content_end]
                if _normalized(raw) != desired:
                    raise ControlPlaneError("Markdown adoption requires equal existing content")
                continue
            if change.kind is ActionKind.CREATE:
                if current is not None:
                    raise ControlPlaneError("Markdown creation scope already exists")
                newline = _newline(document.text)
                content = _insert(
                    document,
                    _envelope(scope.removeprefix("block:"), desired_text, newline),
                ).encode()
                continue
            if change.kind is not ActionKind.UPDATE:
                raise ControlPlaneError("Markdown adapter received an unsupported action")
            if current is None:
                raise ControlPlaneError("Markdown update scope is not present")
            raw = document.text[current.content_start : current.content_end]
            if _normalized(raw) == desired:
                continue
            physical = _physical(desired_text, _newline(document.text))
            content = _apply(
                document.text,
                current.content_start,
                current.content_end,
                physical,
            ).encode()
        _parse(content)
        return content
