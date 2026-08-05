"""One overlap definition for the Claude and Codex ``SessionStart`` registrations.

Both harnesses register startup injection as a list of matcher-scoped groups, so
"the managed unit is present and correct" is a strictly weaker question than "the
repository injects startup context once". A legacy group that carries no matcher,
or one whose matcher merely intersects the managed matcher, occupies a different
keyed-set key: reconciliation appends the managed unit beside it, no consumer
conflict is raised, and every managed-unit check stays green while the harness
fires both handlers (issue #102).

Overlap is therefore decided on two axes at once — which startup events a group
selects, and whether its handlers inject handoff context at all. Neither axis
alone is sound: matching on events would claim every unrelated consumer
SessionStart handler, and matching on commands alone would claim a handoff hook
deliberately scoped to events the managed matcher never selects.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from typing import Literal, cast

from project_standards.jsonc import sanitize_jsonc

MANAGED_MATCHER = "startup|resume|clear|compact"
MANAGED_EVENTS = frozenset(MANAGED_MATCHER.split("|"))

# Commands that inject handoff startup context whatever launcher wraps them.
# Retired engine identities are matched by name because their hook paths moved
# between the v3 layouts; the current shared hook is matched by its own file
# name, so a second copy of the managed handler counts as injection too.
_INJECTION_NEEDLES = ("session_start.py", "handoff-system-v3", "agent-handoff-v3")

Syntax = Literal["jsonc", "toml"]


def _parse(text: str, *, syntax: Syntax) -> object | None:
    """Return the parsed document, or ``None`` when it cannot be read.

    Malformed containers are silently ignored here: reporting them is the
    selected package's authority, and this detector must never turn a parse
    failure into a duplicate-injection claim.
    """
    try:
        if syntax == "toml":
            return tomllib.loads(text)
        return json.loads(sanitize_jsonc(text.lstrip("﻿")))
    except tomllib.TOMLDecodeError, ValueError:
        return None


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return cast("Sequence[object]", value)


def _table(value: object) -> Mapping[str, object] | None:
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else None


def _groups(parsed: object) -> Sequence[object]:
    document = _table(parsed)
    hooks = _table(document.get("hooks")) if document is not None else None
    return _sequence(hooks.get("SessionStart")) if hooks is not None else ()


def _commands(group: Mapping[str, object]) -> Iterator[str]:
    for handler in _sequence(group.get("hooks")):
        entry = _table(handler)
        command = entry.get("command") if entry is not None else None
        if isinstance(command, str):
            yield command


def selected_managed_events(matcher: object) -> frozenset[str]:
    """Return the managed startup events a group's matcher selects.

    An absent, empty, or wildcard matcher selects every event, which is the
    shape issue #102 reproduces: it never collides with the managed key and so
    is invisible to keyed-set conflict detection.
    """
    if not isinstance(matcher, str) or not matcher.strip() or matcher.strip() == "*":
        return MANAGED_EVENTS
    return MANAGED_EVENTS & {part.strip() for part in matcher.split("|")}


def _injects_handoff_context(group: Mapping[str, object]) -> bool:
    return any(
        needle in command.replace("\\", "/").casefold()
        for command in _commands(group)
        for needle in _INJECTION_NEEDLES
    )


def overlapping_startup_groups(text: str, *, syntax: Syntax) -> int:
    """Count SessionStart groups that inject handoff context on a managed event."""
    return sum(
        1
        for raw in _groups(_parse(text, syntax=syntax))
        for group in (_table(raw),)
        if group is not None
        and selected_managed_events(group.get("matcher"))
        and _injects_handoff_context(group)
    )


def duplicate_startup_injection(text: str, *, syntax: Syntax) -> bool:
    """Report whether the container would inject handoff context more than once."""
    return overlapping_startup_groups(text, syntax=syntax) > 1
