"""Internal Markdown link normalization for mutable Agent Handoff callers."""

from __future__ import annotations

import re
from collections.abc import Iterator
from urllib.parse import unquote

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]*)\)")


def _normalized_link_targets(  # pyright: ignore[reportUnusedFunction]
    text: str,
) -> Iterator[str]:
    """Yield normalized destinations without applying caller-specific filtering."""
    for raw_target in _LINK_RE.findall(text):
        cleaned = raw_target.strip()
        angle_end = cleaned.find(">", 1) if cleaned.startswith("<") else -1
        if angle_end >= 0:
            target = cleaned[1:angle_end]
        else:
            parts = cleaned.split(maxsplit=1)
            target = parts[0] if parts else ""

        # Fragment-only links remain distinct from malformed empty destinations
        # so callers can preserve their existing skip-versus-finding policy.
        if target.startswith("#"):
            yield target
        else:
            yield unquote(target.split("#", maxsplit=1)[0])
