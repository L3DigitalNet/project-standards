"""cli_documentation contract-version registration (spec §7/§9)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from project_standards import validate_frontmatter
from project_standards.registry import load_registry

# The include pattern deliberately matches nothing: an EMPTY include list is falsy and
# falls back to _default_corpus() (validate_frontmatter.py:423-427 `elif include_patterns:`),
# which would validate the whole repo (codex CR-001). The version gate runs BEFORE path
# collection, so a no-match run still exercises it; zero files exits 0 with
# "no files matched" on stderr (validate_frontmatter.py:832-835).
_CONFIG_KNOWN = """\
markdown:
  frontmatter:
    version: "1.1"
    schema: "markdown-frontmatter"
    include:
      - "no-such-path/**/*.md"
cli_documentation:
  version: "{version}"
"""


def test_registry_bundles_cli_documentation_default() -> None:
    reg = load_registry()
    assert reg.cli_documentation_default == "1.0"
    assert reg.is_known_cli_documentation("1.0")
    assert not reg.is_known_cli_documentation("9.9")


def test_registry_bundles_agent_handoff_default() -> None:
    reg = load_registry()
    assert reg.agent_handoff_default == "1.0"
    assert reg.agent_handoff_versions == ["1.0"]
    assert reg.is_known_agent_handoff("1.0")
    assert not reg.is_known_agent_handoff("9.9")


def _run_with_config(tmp_path: Path, version_yaml: str) -> int:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(version_yaml, encoding="utf-8")
    return validate_frontmatter.main(["--config", str(cfg)])


def test_known_version_accepted_silently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="1.0")) == 0


def test_unknown_version_exits_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="9.9")) == 2
    assert "unknown cli_documentation.version" in capsys.readouterr().err


def test_non_string_version_exits_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    bad = _CONFIG_KNOWN.replace('version: "{version}"', "version: 1.0")  # bare float
    assert _run_with_config(tmp_path, bad) == 2


def test_dogfood_config_selects_cli_documentation_v1_3() -> None:
    config = tomllib.loads(Path(".standards/config.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads(Path(".standards/lock.toml").read_text(encoding="utf-8"))

    assert config["standards"]["cli-documentation"]["config"]["contract_version"] == "1.0"
    assert lock["standards"]["cli-documentation"]["resolved"] == "1.3"
