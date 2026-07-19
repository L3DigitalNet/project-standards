"""Semantic integration for Claude Code ``SessionStart`` command hooks."""

from __future__ import annotations

import copy
import json
from typing import cast

from project_standards.agent_handoff.integrations.markers import (
    IntegrationConflictError,
)

CLAUDE_MATCHER = "startup|resume|clear|compact"
CLAUDE_COMMAND = "${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py"

_MANAGED_HANDLER: dict[str, object] = {
    "type": "command",
    "command": CLAUDE_COMMAND,
    "args": [],
    "timeout": 10,
    "statusMessage": "Loading agent handoff state...",
}
_MANAGED_GROUP: dict[str, object] = {
    "matcher": CLAUDE_MATCHER,
    "hooks": [_MANAGED_HANDLER],
}


def _is_legacy_command(command: str) -> bool:
    normalized = command.lower().replace("\\", "/")
    if "handoff-system-v3" in normalized:
        return True
    if "session_start.py" not in normalized:
        return False
    return "/.claude/hooks/" in normalized or "agent-handoff" in normalized


def _session_start_groups(settings: dict[str, object]) -> list[object]:
    hooks = settings.get("hooks")
    if hooks is None:
        return []
    if not isinstance(hooks, dict):
        raise IntegrationConflictError("Claude settings hooks must be an object")
    typed_hooks = cast(dict[str, object], hooks)
    session_start = typed_hooks.get("SessionStart")
    if session_start is None:
        return []
    if not isinstance(session_start, list):
        raise IntegrationConflictError("Claude SessionStart hooks must be an array")
    return cast(list[object], session_start)


def _inspect_groups(groups: list[object]) -> int:
    managed_count = 0
    for group in groups:
        if not isinstance(group, dict):
            raise IntegrationConflictError("Claude SessionStart groups must be objects")
        typed_group = cast(dict[str, object], group)
        handlers = typed_group.get("hooks")
        if not isinstance(handlers, list):
            raise IntegrationConflictError("Claude SessionStart group hooks must be an array")
        for handler in cast(list[object], handlers):
            if not isinstance(handler, dict):
                raise IntegrationConflictError("Claude SessionStart handlers must be objects")
            typed_handler = cast(dict[str, object], handler)
            command = typed_handler.get("command")
            if not isinstance(command, str):
                continue
            if command == CLAUDE_COMMAND:
                managed_count += 1
                if (
                    typed_group.get("matcher") != CLAUDE_MATCHER
                    or typed_handler != _MANAGED_HANDLER
                ):
                    raise IntegrationConflictError(
                        "the agent-handoff Claude handler differs from the managed definition"
                    )
            elif _is_legacy_command(command):
                raise IntegrationConflictError(
                    "a legacy agent-handoff Claude handler requires manual migration"
                )
    if managed_count > 1:
        raise IntegrationConflictError(
            "the agent-handoff Claude handler is configured more than once"
        )
    return managed_count


def managed_claude_handler_count(settings: dict[str, object]) -> int:
    """Return the canonical handler count after validating the hook structure."""
    return _inspect_groups(_session_start_groups(settings))


def merge_claude_settings(settings: dict[str, object]) -> dict[str, object]:
    """Add the managed hook while preserving unrelated settings semantically."""
    merged = copy.deepcopy(settings)
    groups = _session_start_groups(merged)
    if _inspect_groups(groups) == 1:
        return merged

    if merged.get("hooks") is None:
        merged["hooks"] = {}
    hooks = cast(dict[str, object], merged["hooks"])
    if hooks.get("SessionStart") is None:
        hooks["SessionStart"] = []
    session_start = cast(list[object], hooks["SessionStart"])
    session_start.append(copy.deepcopy(_MANAGED_GROUP))
    return merged


def merge_claude_settings_json(text: str) -> str:
    """Parse, merge, and render a Claude settings JSON object."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IntegrationConflictError("Claude settings are not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise IntegrationConflictError("Claude settings must contain a JSON object")
    merged = merge_claude_settings(cast(dict[str, object], parsed))
    return f"{json.dumps(merged, indent=2, ensure_ascii=False)}\n"
