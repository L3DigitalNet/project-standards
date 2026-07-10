"""Bounded inline-TOML integration for Codex ``SessionStart`` hooks."""

from __future__ import annotations

import tomllib
from typing import cast

from project_standards.agent_handoff.integrations.markers import (
    CODEX_HOOK_MARKERS,
    IntegrationConflictError,
    parse_marked_block,
    replace_marked_block,
)

CODEX_MATCHER = "startup|resume|clear|compact"
CODEX_COMMAND = '"$(git rev-parse --show-toplevel)/.agents/hooks/agent-handoff/session_start.py"'


def _render_managed_hook() -> str:
    return (
        "[[hooks.SessionStart]]\n"
        f'matcher = "{CODEX_MATCHER}"\n\n'
        "[[hooks.SessionStart.hooks]]\n"
        'type = "command"\n'
        f"command = '{CODEX_COMMAND}'\n"
        "timeout = 10\n"
        'statusMessage = "Loading agent handoff state..."\n'
    )


def _load_toml(text: str, *, locus: str) -> dict[str, object]:
    try:
        return cast(dict[str, object], tomllib.loads(text))
    except tomllib.TOMLDecodeError as exc:
        raise IntegrationConflictError(f"{locus} is not valid TOML") from exc


def _session_start_groups(parsed: dict[str, object]) -> list[object]:
    hooks_value = parsed.get("hooks")
    if hooks_value is None:
        return []
    if not isinstance(hooks_value, dict):
        raise IntegrationConflictError("Codex hooks must be a TOML table")
    hooks = cast(dict[str, object], hooks_value)
    groups_value = hooks.get("SessionStart")
    if groups_value is None:
        return []
    if not isinstance(groups_value, list):
        raise IntegrationConflictError("Codex SessionStart hooks must be an array of tables")
    return cast(list[object], groups_value)


def _is_legacy_command(command: str) -> bool:
    normalized = command.lower().replace("\\", "/")
    if "handoff-system-v3" in normalized:
        return True
    if "session_start.py" not in normalized:
        return False
    return "agent-handoff" in normalized or "/.codex/hooks/" in normalized


def _inspect_session_start(parsed: dict[str, object]) -> int:
    canonical_count = 0
    for group_value in _session_start_groups(parsed):
        if not isinstance(group_value, dict):
            raise IntegrationConflictError("Codex SessionStart groups must be TOML tables")
        group = cast(dict[str, object], group_value)
        handlers_value = group.get("hooks")
        if not isinstance(handlers_value, list):
            raise IntegrationConflictError(
                "Codex SessionStart group handlers must be an array of tables"
            )
        for handler_value in cast(list[object], handlers_value):
            if not isinstance(handler_value, dict):
                raise IntegrationConflictError("Codex SessionStart handlers must be TOML tables")
            handler = cast(dict[str, object], handler_value)
            command = handler.get("command")
            if command is None:
                continue
            if not isinstance(command, str):
                raise IntegrationConflictError("Codex hook commands must be strings")
            if command == CODEX_COMMAND:
                canonical_count += 1
            elif _is_legacy_command(command):
                raise IntegrationConflictError(
                    "a legacy agent-handoff Codex hook requires manual migration"
                )
    if canonical_count > 1:
        raise IntegrationConflictError("the agent-handoff Codex hook is configured more than once")
    return canonical_count


def merge_codex_config(text: str, *, hooks_json_exists: bool = False) -> str:
    """Install one managed hook block while preserving every outside byte."""
    if hooks_json_exists:
        raise IntegrationConflictError(
            ".codex/hooks.json coexists with inline hooks; consolidate it manually first"
        )

    parsed = _load_toml(text, locus="Codex config")
    span = parse_marked_block(text, CODEX_HOOK_MARKERS)
    canonical_count = _inspect_session_start(parsed)
    if span is None:
        if canonical_count:
            raise IntegrationConflictError(
                "an unmarked agent-handoff Codex hook requires manual reconciliation"
            )
    else:
        managed_text = text[span.start : span.end]
        managed = _load_toml(managed_text, locus="managed Codex hook block")
        expected = _load_toml(_render_managed_hook(), locus="packaged Codex hook")
        if managed != expected or canonical_count != 1:
            raise IntegrationConflictError(
                "the managed agent-handoff Codex hook differs from its packaged definition"
            )

    rendered = replace_marked_block(text, CODEX_HOOK_MARKERS, _render_managed_hook())
    result = _load_toml(rendered, locus="rendered Codex config")
    if _inspect_session_start(result) != 1:
        raise IntegrationConflictError("rendered Codex config lacks one managed hook")
    return rendered
