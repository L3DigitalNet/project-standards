"""Strict delimiter-bounded text integration without ownership outside the block."""

from __future__ import annotations

from dataclasses import dataclass


class IntegrationConflictError(ValueError):
    """Consumer integration is malformed or ambiguous and must not be changed."""


@dataclass(frozen=True)
class MarkerPair:
    start: str
    end: str


@dataclass(frozen=True)
class BlockSpan:
    start: int
    end: int
    newline: str


INSTRUCTION_MARKERS = MarkerPair(
    "<!-- BEGIN agent-handoff managed instructions -->",
    "<!-- END agent-handoff managed instructions -->",
)
PROJECT_CONFIG_MARKERS = MarkerPair(
    "# BEGIN agent-handoff managed config",
    "# END agent-handoff managed config",
)
CODEX_HOOK_MARKERS = MarkerPair(
    "# BEGIN agent-handoff managed codex hook",
    "# END agent-handoff managed codex hook",
)


def _ending(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n"


def parse_marked_block(text: str, markers: MarkerPair) -> BlockSpan | None:
    """Return the single exact marker span, or reject every ambiguous marker shape."""
    starts: list[tuple[int, int, str]] = []
    ends: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        control = line.rstrip("\r\n")
        record = (offset, offset + len(line), _ending(line))
        if control == markers.start:
            starts.append(record)
        elif control == markers.end:
            ends.append(record)
        offset += len(line)

    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1:
        raise IntegrationConflictError("managed integration markers must appear exactly once")
    start, end = starts[0], ends[0]
    if start[0] >= end[0]:
        raise IntegrationConflictError("managed integration markers are reordered or nested")
    return BlockSpan(start=start[0], end=end[1], newline=start[2])


def _default_newline(text: str) -> str:
    without_crlf = text.replace("\r\n", "")
    return "\r\n" if "\r\n" in text and "\n" not in without_crlf else "\n"


def _render_block(markers: MarkerPair, body: str, newline: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    middle = f"{normalized}{newline}" if normalized else ""
    return f"{markers.start}{newline}{middle}{markers.end}{newline}"


def replace_marked_block(text: str, markers: MarkerPair, body: str) -> str:
    """Replace only the owned span, or append one with deterministic separation."""
    span = parse_marked_block(text, markers)
    newline = span.newline if span is not None else _default_newline(text)
    block = _render_block(markers, body, newline)
    if span is not None:
        return f"{text[: span.start]}{block}{text[span.end :]}"
    if not text:
        return block
    if text.endswith(newline * 2):
        separator = ""
    elif text.endswith(newline):
        separator = newline
    else:
        separator = newline * 2
    return f"{text}{separator}{block}"
