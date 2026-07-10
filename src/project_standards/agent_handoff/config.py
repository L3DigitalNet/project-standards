"""Load only the strict agent_handoff namespace from project configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, overload

import yaml
from pydantic import ValidationError

from project_standards.agent_handoff.model import AgentHandoffConfig


class AgentHandoffConfigError(ValueError):
    """The owned agent_handoff configuration is missing or invalid."""


def _validation_message(exc: ValidationError) -> str:
    details: list[str] = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        locus = ".".join(str(part) for part in error["loc"])
        details.append(f"{locus}: {error['msg']}" if locus else str(error["msg"]))
    return "; ".join(details)


@overload
def load_agent_handoff_config(
    path: Path, *, required: Literal[True] = True
) -> AgentHandoffConfig: ...


@overload
def load_agent_handoff_config(
    path: Path, *, required: Literal[False]
) -> AgentHandoffConfig | None: ...


def load_agent_handoff_config(path: Path, *, required: bool = True) -> AgentHandoffConfig | None:
    """Load the owned namespace while ignoring unrelated top-level configuration."""
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AgentHandoffConfigError(f"cannot read agent-handoff config {path}") from exc

    if not isinstance(raw, dict):
        raise AgentHandoffConfigError(f"project config {path} must contain a mapping")
    if "agent_handoff" not in raw:
        if required:
            raise AgentHandoffConfigError(f"project config {path} is missing agent_handoff")
        return None

    try:
        return AgentHandoffConfig.model_validate(raw["agent_handoff"])
    except ValidationError as exc:
        raise AgentHandoffConfigError(
            f"invalid agent_handoff config in {path}: {_validation_message(exc)}"
        ) from exc
