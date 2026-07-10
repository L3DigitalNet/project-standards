from pathlib import Path

import pytest

from project_standards.agent_handoff.config import (
    AgentHandoffConfigError,
    load_agent_handoff_config,
)
from project_standards.agent_handoff.model import Harness, StartupMode


def _write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / ".project-standards.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_agent_handoff_namespace_rejects_unknown_keys(tmp_path: Path) -> None:
    config = _write_config(
        tmp_path,
        "other_standard:\n  keep: true\nagent_handoff:\n  version: '1.0'\n"
        "  startup: manual\n  harnesses: []\n  typo: true\n",
    )

    with pytest.raises(AgentHandoffConfigError, match="typo"):
        load_agent_handoff_config(config)


def test_agent_handoff_loader_ignores_unrelated_top_level_namespaces(tmp_path: Path) -> None:
    config = _write_config(
        tmp_path,
        "other_standard:\n  keep: true\nagent_handoff:\n  version: '1.0'\n"
        "  startup: automatic\n  harnesses: [claude-code, codex]\n",
    )

    loaded = load_agent_handoff_config(config)

    assert loaded.version == "1.0"
    assert loaded.startup is StartupMode.AUTOMATIC
    assert loaded.harnesses == (Harness.CLAUDE_CODE, Harness.CODEX)


def test_agent_handoff_loader_requires_owned_namespace_by_default(tmp_path: Path) -> None:
    config = _write_config(tmp_path, "other_standard:\n  keep: true\n")

    with pytest.raises(AgentHandoffConfigError, match="agent_handoff"):
        load_agent_handoff_config(config)


def test_agent_handoff_loader_can_probe_absent_namespace(tmp_path: Path) -> None:
    config = _write_config(tmp_path, "other_standard:\n  keep: true\n")

    assert load_agent_handoff_config(config, required=False) is None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "agent_handoff:\n  version: 1.0\n  startup: manual\n  harnesses: []\n",
            "version",
        ),
        (
            "agent_handoff:\n  version: '1.0'\n  startup: automatic\n  harnesses: []\n",
            "automatic",
        ),
        (
            "agent_handoff:\n  version: '1.0'\n  startup: manual\n  harnesses: [codex]\n",
            "manual",
        ),
        (
            "agent_handoff:\n  version: '1.0'\n  startup: automatic\n  harnesses: [codex, codex]\n",
            "unique",
        ),
    ],
)
def test_agent_handoff_loader_rejects_invalid_profile(
    tmp_path: Path, body: str, message: str
) -> None:
    config = _write_config(tmp_path, body)

    with pytest.raises(AgentHandoffConfigError, match=message):
        load_agent_handoff_config(config)


@pytest.mark.parametrize("body", ["- not-a-mapping\n", "agent_handoff: [\n"])
def test_agent_handoff_loader_wraps_yaml_boundary(tmp_path: Path, body: str) -> None:
    config = _write_config(tmp_path, body)

    with pytest.raises(AgentHandoffConfigError):
        load_agent_handoff_config(config)


def test_agent_handoff_loader_wraps_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AgentHandoffConfigError, match="cannot read"):
        load_agent_handoff_config(tmp_path / "missing.yml")
