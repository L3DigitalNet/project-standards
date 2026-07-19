from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff.integrations.claude import (
    CLAUDE_COMMAND,
    CLAUDE_MATCHER,
    managed_claude_handler_count,
    merge_claude_settings,
    merge_claude_settings_json,
)
from project_standards.agent_handoff.integrations.markers import IntegrationConflictError


def _managed_group(**handler_overrides: object) -> dict[str, object]:
    handler: dict[str, object] = {
        "type": "command",
        "command": CLAUDE_COMMAND,
        "args": [],
        "timeout": 10,
        "statusMessage": "Loading agent handoff state...",
    }
    handler.update(handler_overrides)
    return {"matcher": CLAUDE_MATCHER, "hooks": [handler]}


def test_merge_claude_preserves_unrelated_semantics() -> None:
    existing: dict[str, object] = {
        "permissions": {"allow": ["Bash(git status)"]},
        "hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "echo done"}]}]},
    }

    merged = merge_claude_settings(existing)

    assert merged["permissions"] == existing["permissions"]
    assert merged["hooks"]["PostToolUse"] == existing["hooks"]["PostToolUse"]  # type: ignore[index]
    assert managed_claude_handler_count(merged) == 1


def test_merge_claude_creates_missing_settings() -> None:
    merged = merge_claude_settings({})

    assert managed_claude_handler_count(merged) == 1
    hooks = cast(dict[str, object], merged["hooks"])
    groups = cast(list[object], hooks["SessionStart"])
    group = cast(dict[str, object], groups[0])
    handlers = cast(list[object], group["hooks"])
    handler = cast(dict[str, object], handlers[0])
    assert group["matcher"] == "startup|resume|clear|compact"
    assert handler["command"] == CLAUDE_COMMAND
    assert handler["args"] == []
    assert "python" not in cast(str, handler["command"])


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param({"hooks": None}, id="null-hooks"),
        pytest.param({"hooks": {"SessionStart": None}}, id="null-session-start"),
    ],
)
def test_merge_claude_accepts_null_hook_containers(
    existing: dict[str, object],
) -> None:
    merged = merge_claude_settings(existing)

    assert merged == {"hooks": {"SessionStart": [_managed_group()]}}


def test_merge_claude_is_idempotent_for_exact_managed_handler() -> None:
    existing: dict[str, object] = {"hooks": {"SessionStart": [_managed_group()]}}

    assert merge_claude_settings(existing) == existing


def test_merge_claude_preserves_unrelated_session_start_handler() -> None:
    unrelated = {"matcher": "startup", "hooks": [{"type": "command", "command": "echo hi"}]}
    existing: dict[str, object] = {"hooks": {"SessionStart": [unrelated]}}

    merged = merge_claude_settings(existing)

    assert merged["hooks"]["SessionStart"][0] == unrelated  # type: ignore[index]
    assert managed_claude_handler_count(merged) == 1


@pytest.mark.parametrize(
    "groups",
    [
        [_managed_group(), _managed_group()],
        [_managed_group(type="prompt")],
        [_managed_group(args=["--unexpected"])],
        [{**_managed_group(), "matcher": "startup"}],
        [
            {
                "matcher": CLAUDE_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session_start.py",
                    }
                ],
            }
        ],
        [
            {
                "matcher": CLAUDE_MATCHER,
                "hooks": [
                    {"type": "command", "command": "python handoff-system-v3/session_start.py"}
                ],
            }
        ],
    ],
)
def test_merge_claude_rejects_ambiguous_or_legacy_handler(
    groups: list[dict[str, object]],
) -> None:
    existing: dict[str, object] = {"hooks": {"SessionStart": groups}}

    with pytest.raises(IntegrationConflictError):
        merge_claude_settings(existing)


_WRONG_CONTAINER_SHAPES: list[dict[str, object]] = [
    {"hooks": []},
    {"hooks": {"SessionStart": {}}},
    {"hooks": {"SessionStart": ["bad"]}},
    {"hooks": {"SessionStart": [{"matcher": "startup", "hooks": {}}]}},
]


@pytest.mark.parametrize("existing", _WRONG_CONTAINER_SHAPES)
def test_merge_claude_rejects_wrong_container_shapes(existing: dict[str, object]) -> None:
    with pytest.raises(IntegrationConflictError):
        merge_claude_settings(existing)


@pytest.mark.parametrize("text", ["[", "[]", '"scalar"'])
def test_merge_claude_json_rejects_invalid_or_non_object_root(text: str) -> None:
    with pytest.raises(IntegrationConflictError):
        merge_claude_settings_json(text)


def test_merge_claude_json_round_trips_valid_output() -> None:
    rendered = merge_claude_settings_json('{"permissions":{"deny":["Bash(rm *)"]}}')
    parsed = json.loads(rendered)

    assert parsed["permissions"] == {"deny": ["Bash(rm *)"]}
    assert managed_claude_handler_count(parsed) == 1
    assert rendered.endswith("\n")


def test_shipped_claude_fragment_matches_the_managed_group() -> None:
    root = Path(__file__).parents[2]
    canonical = root / "standards/agent-handoff/resources/integration/claude-session-start.json"
    bundled = (
        root
        / "src/project_standards/bundles/agent-handoff/resources/integration/claude-session-start.json"
    )

    assert canonical.read_bytes() == bundled.read_bytes()
    assert json.loads(canonical.read_text(encoding="utf-8")) == _managed_group()
