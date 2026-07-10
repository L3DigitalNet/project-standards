"""Select agent instruction files and maintain one bounded handoff block."""

from __future__ import annotations

from project_standards.agent_handoff.integrations.markers import (
    INSTRUCTION_MARKERS,
    replace_marked_block,
)
from project_standards.agent_handoff.model import AgentHandoffConfig, Harness, StartupMode

_INSTRUCTION_BODY = """Use the repo-local `$agent-handoff` skill at startup and closeout.
Do not reread `docs/handoff/state.md` when SessionStart already injected it.
Keep current status and tasks in `docs/STATUS.md` and `docs/TODO.md`; route durable facts through `docs/handoff/`.
At closeout, update only changed facts, preserve user-authored work, store credential references only, and run relevant validation.
"""


def instruction_targets(startup: StartupMode, harnesses: tuple[Harness, ...]) -> tuple[str, ...]:
    """Return deterministic instruction targets for one validated startup profile."""
    config = AgentHandoffConfig(version="1.0", startup=startup, harnesses=harnesses)
    targets: set[str] = set()
    if config.startup is StartupMode.MANUAL or Harness.CODEX in config.harnesses:
        targets.add("AGENTS.md")
    if Harness.CLAUDE_CODE in config.harnesses:
        targets.add("CLAUDE.md")
    return tuple(sorted(targets))


def merge_instruction_block(text: str) -> str:
    """Return instructions with exactly one current agent-handoff owned block."""
    return replace_marked_block(text, INSTRUCTION_MARKERS, _INSTRUCTION_BODY)
