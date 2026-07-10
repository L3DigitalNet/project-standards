"""Merge the strict agent_handoff YAML namespace without owning surrounding config."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any, cast

import yaml

from project_standards.agent_handoff.integrations.markers import (
    PROJECT_CONFIG_MARKERS,
    IntegrationConflictError,
    parse_marked_block,
    replace_marked_block,
)
from project_standards.agent_handoff.model import AgentHandoffConfig, Harness, StartupMode

_MERGE_KEY_RE = re.compile(r"(?m)^\s*<<\s*:")


def _load_mapping(text: str, *, locus: str) -> dict[object, object]:
    try:
        loaded: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise IntegrationConflictError(f"{locus} is not valid YAML") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise IntegrationConflictError(f"{locus} must contain a YAML mapping")
    return cast("dict[object, object]", loaded)


def _reject_owned_yaml_indirection(block: str) -> None:
    try:
        scan = cast("Callable[[str], Iterable[yaml.tokens.Token]]", yaml.scan)
        tokens = tuple(scan(block))
    except yaml.YAMLError as exc:
        raise IntegrationConflictError("managed config block is not valid YAML") from exc
    if any(
        isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for token in tokens
    ):
        raise IntegrationConflictError("managed config block cannot contain an alias or anchor")
    if _MERGE_KEY_RE.search(block):
        raise IntegrationConflictError("managed config block cannot contain a merge key")


def _render_owned_config(config: AgentHandoffConfig) -> str:
    lines = [
        "agent_handoff:",
        "  version: '1.0'",
        f"  startup: {config.startup.value}",
    ]
    if config.harnesses:
        lines.append("  harnesses:")
        lines.extend(f"    - {harness.value}" for harness in config.harnesses)
    else:
        lines.append("  harnesses: []")
    return "\n".join(lines) + "\n"


def merge_project_config(text: str, *, startup: StartupMode, harnesses: tuple[Harness, ...]) -> str:
    """Return config with one validated owned block and all outside bytes preserved."""
    _load_mapping(text, locus="project config")
    config = AgentHandoffConfig(version="1.0", startup=startup, harnesses=harnesses)
    span = parse_marked_block(text, PROJECT_CONFIG_MARKERS)
    if span is None:
        outside = text
        if "agent_handoff" in _load_mapping(outside, locus="project config"):
            raise IntegrationConflictError("unmarked agent_handoff namespace already exists")
    else:
        managed = text[span.start : span.end]
        _reject_owned_yaml_indirection(managed)
        outside = f"{text[: span.start]}{text[span.end :]}"
        if "agent_handoff" in _load_mapping(outside, locus="unmanaged project config"):
            raise IntegrationConflictError("unmarked agent_handoff namespace already exists")

    rendered = replace_marked_block(text, PROJECT_CONFIG_MARKERS, _render_owned_config(config))
    result = _load_mapping(rendered, locus="rendered project config")
    try:
        AgentHandoffConfig.model_validate(result["agent_handoff"])
    except (KeyError, ValueError) as exc:
        raise IntegrationConflictError("rendered agent_handoff namespace is invalid") from exc
    return rendered
