from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from project_standards.agent_handoff.integrations.codex import (
    CODEX_COMMAND,
    CODEX_MATCHER,
    merge_codex_config,
)
from project_standards.agent_handoff.integrations.markers import IntegrationConflictError


def test_codex_block_preserves_unrelated_toml() -> None:
    before = (
        'model = "gpt-5.6"\n\n[features]\nhooks = true\n\n[mcp_servers.local]\ncommand = "server"\n'
    )

    after = merge_codex_config(before)

    assert after.startswith(before)
    assert "# BEGIN agent-handoff managed codex hook\n" in after
    assert ".agents/hooks/agent-handoff/session_start.py" in after
    parsed = tomllib.loads(after)
    assert parsed["model"] == "gpt-5.6"
    assert parsed["features"] == {"hooks": True}
    assert parsed["mcp_servers"] == {"local": {"command": "server"}}


def test_codex_merge_creates_missing_config() -> None:
    after = merge_codex_config("")
    parsed = tomllib.loads(after)
    group = parsed["hooks"]["SessionStart"][0]
    handler = group["hooks"][0]

    assert group["matcher"] == CODEX_MATCHER
    assert handler == {
        "type": "command",
        "command": CODEX_COMMAND,
        "timeout": 10,
        "statusMessage": "Loading agent handoff state...",
    }
    assert "python" not in CODEX_COMMAND


def test_codex_merge_is_idempotent_and_preserves_outside_bytes() -> None:
    first = merge_codex_config('model = "gpt-5.6"\n')
    before, block = first.split("# BEGIN agent-handoff managed codex hook\n", maxsplit=1)

    second = merge_codex_config(first)

    assert second == first
    assert second.startswith(before)
    assert second.endswith(block)


@pytest.mark.parametrize(
    "text",
    [
        "# BEGIN agent-handoff managed codex hook\n",
        "# END agent-handoff managed codex hook\n",
        "# END agent-handoff managed codex hook\n# BEGIN agent-handoff managed codex hook\n",
        "# BEGIN agent-handoff managed codex hook\n"
        "# END agent-handoff managed codex hook\n"
        "# BEGIN agent-handoff managed codex hook\n"
        "# END agent-handoff managed codex hook\n",
    ],
)
def test_codex_merge_rejects_malformed_markers(text: str) -> None:
    with pytest.raises(IntegrationConflictError):
        merge_codex_config(text)


def test_codex_merge_rejects_invalid_toml() -> None:
    with pytest.raises(IntegrationConflictError):
        merge_codex_config("model = [")


def test_codex_merge_rejects_hooks_json_coexistence() -> None:
    with pytest.raises(IntegrationConflictError):
        merge_codex_config("", hooks_json_exists=True)


@pytest.mark.parametrize(
    "command",
    [
        CODEX_COMMAND,
        'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/session_start.py"',
        "python3 /opt/handoff-system-v3/session_start.py",
    ],
)
def test_codex_merge_rejects_unmarked_equivalent_or_legacy_handler(command: str) -> None:
    text = (
        '[[hooks.SessionStart]]\nmatcher = "startup"\n'
        "[[hooks.SessionStart.hooks]]\n"
        'type = "command"\n'
        f"command = {command!r}\n"
    )

    with pytest.raises(IntegrationConflictError):
        merge_codex_config(text)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('type = "command"', 'type = "prompt"'),
        ("timeout = 10", "timeout = 30"),
        (CODEX_COMMAND, "./wrong/session_start.py"),
        (CODEX_MATCHER, "startup"),
    ],
)
def test_codex_merge_rejects_drifted_managed_handler(old: str, new: str) -> None:
    text = merge_codex_config("").replace(old, new)

    with pytest.raises(IntegrationConflictError):
        merge_codex_config(text)


def test_codex_merge_preserves_unrelated_session_start_handler() -> None:
    unrelated = (
        '[[hooks.SessionStart]]\nmatcher = "startup"\n'
        "[[hooks.SessionStart.hooks]]\n"
        'type = "command"\ncommand = "echo existing"\n'
    )

    merged = merge_codex_config(unrelated)

    assert merged.startswith(unrelated)
    assert tomllib.loads(merged)["hooks"]["SessionStart"][0]["hooks"][0]["command"] == (
        "echo existing"
    )


def test_shipped_codex_fragment_matches_managed_output() -> None:
    root = Path(__file__).parents[2]
    canonical = root / "standards/agent-handoff/resources/integration/codex-session-start.toml"
    bundled = (
        root
        / "src/project_standards/bundles/agent-handoff/resources/integration/codex-session-start.toml"
    )

    assert canonical.read_bytes() == bundled.read_bytes()
    assert canonical.read_text(encoding="utf-8") == merge_codex_config("")
