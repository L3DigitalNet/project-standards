"""Internal Markdown link normalization for mutable Agent Handoff callers."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import unquote

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]*)\)")


@dataclass(frozen=True, slots=True)
class LinkOccurrence:
    """One normalized Markdown destination and its structural source location."""

    target: str
    line: int
    column: int


def _normalized_target(raw_target: str) -> str:
    cleaned = raw_target.strip()
    angle_end = cleaned.find(">", 1) if cleaned.startswith("<") else -1
    if angle_end >= 0:
        target = cleaned[1:angle_end]
    else:
        parts = cleaned.split(maxsplit=1)
        target = parts[0] if parts else ""
    if target.startswith("#"):
        return target
    return unquote(target.split("#", maxsplit=1)[0])


def _normalized_link_occurrences(text: str) -> Iterator[LinkOccurrence]:
    """Yield destinations with one-based coordinates without retaining source content."""
    for match in _LINK_RE.finditer(text):
        start = match.start()
        previous_newline = text.rfind("\n", 0, start)
        yield LinkOccurrence(
            target=_normalized_target(match.group(1)),
            line=text.count("\n", 0, start) + 1,
            column=start - previous_newline,
        )


def _normalized_link_targets(  # pyright: ignore[reportUnusedFunction]
    text: str,
) -> Iterator[str]:
    """Yield normalized destinations without applying caller-specific filtering."""
    # Fragment-only links remain distinct from malformed empty destinations so
    # callers can preserve their existing skip-versus-finding policy.
    yield from (occurrence.target for occurrence in _normalized_link_occurrences(text))
