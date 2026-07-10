from __future__ import annotations

import pytest

from project_standards.agent_handoff.integrations.instructions import (
    instruction_targets,
    merge_instruction_block,
)
from project_standards.agent_handoff.integrations.markers import (
    INSTRUCTION_MARKERS,
    IntegrationConflictError,
    parse_marked_block,
    replace_marked_block,
)
from project_standards.agent_handoff.model import Harness, StartupMode


def test_replace_block_preserves_unowned_bytes() -> None:
    before = (
        "# Custom\n\nkeep exactly\n\n<!-- BEGIN agent-handoff managed instructions -->\n"
        "old\n<!-- END agent-handoff managed instructions -->\n\ntail\n"
    )

    after = replace_marked_block(before, INSTRUCTION_MARKERS, "new\n")

    assert after.startswith("# Custom\n\nkeep exactly\n\n")
    assert after.endswith("\n\ntail\n")
    assert "\nnew\n" in after


def test_replace_block_appends_with_deterministic_separation() -> None:
    after = replace_marked_block("# Existing\n", INSTRUCTION_MARKERS, "new\n")

    assert after == (
        "# Existing\n\n<!-- BEGIN agent-handoff managed instructions -->\n"
        "new\n<!-- END agent-handoff managed instructions -->\n"
    )


def test_replace_block_creates_fresh_file_and_final_newline() -> None:
    after = replace_marked_block("", INSTRUCTION_MARKERS, "new")

    assert after.startswith("<!-- BEGIN agent-handoff managed instructions -->\n")
    assert after.endswith("<!-- END agent-handoff managed instructions -->\n")


def test_replace_block_preserves_crlf_policy() -> None:
    before = (
        "# Existing\r\n\r\n<!-- BEGIN agent-handoff managed instructions -->\r\n"
        "old\r\n<!-- END agent-handoff managed instructions -->\r\n"
    )

    after = replace_marked_block(before, INSTRUCTION_MARKERS, "new\n")

    assert "\n" not in after.replace("\r\n", "")
    assert "\r\nnew\r\n" in after


@pytest.mark.parametrize(
    "text",
    [
        "<!-- BEGIN agent-handoff managed instructions -->\na\n"
        "<!-- BEGIN agent-handoff managed instructions -->\nb\n"
        "<!-- END agent-handoff managed instructions -->\n",
        "<!-- BEGIN agent-handoff managed instructions -->\na\n"
        "<!-- END agent-handoff managed instructions -->\n"
        "<!-- END agent-handoff managed instructions -->\n",
        "<!-- END agent-handoff managed instructions -->\n"
        "<!-- BEGIN agent-handoff managed instructions -->\n",
        "<!-- BEGIN agent-handoff managed instructions -->\nmissing end\n",
        "<!-- END agent-handoff managed instructions -->\nmissing start\n",
    ],
)
def test_parse_marked_block_rejects_ambiguous_markers(text: str) -> None:
    with pytest.raises(IntegrationConflictError):
        parse_marked_block(text, INSTRUCTION_MARKERS)


def test_marker_text_inside_prose_is_not_a_control_line() -> None:
    text = "Discuss <!-- BEGIN agent-handoff managed instructions --> inline.\n"

    assert parse_marked_block(text, INSTRUCTION_MARKERS) is None


@pytest.mark.parametrize(
    ("startup", "harnesses", "expected"),
    [
        (StartupMode.MANUAL, (), ("AGENTS.md",)),
        (StartupMode.AUTOMATIC, (Harness.CLAUDE_CODE,), ("CLAUDE.md",)),
        (StartupMode.AUTOMATIC, (Harness.CODEX,), ("AGENTS.md",)),
        (
            StartupMode.AUTOMATIC,
            (Harness.CODEX, Harness.CLAUDE_CODE),
            ("AGENTS.md", "CLAUDE.md"),
        ),
    ],
)
def test_instruction_targets_follow_startup_profile(
    startup: StartupMode, harnesses: tuple[Harness, ...], expected: tuple[str, ...]
) -> None:
    assert instruction_targets(startup, harnesses) == expected


def test_instruction_block_names_v1_operating_contract() -> None:
    text = merge_instruction_block("# Existing\n")

    assert "$agent-handoff" in text
    assert "docs/STATUS.md" in text
    assert "docs/TODO.md" in text
    assert "docs/handoff/state.md" in text
    assert "closeout" in text.lower()
    assert "handoff-system-v3" not in text
