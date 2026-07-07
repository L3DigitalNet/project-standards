"""cli_documentation contract-version registration (spec §7/§9)."""

from __future__ import annotations

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


def _run_with_config(tmp_path: Path, version_yaml: str) -> int:
    cfg = tmp_path / ".project-standards.yml"
    cfg.write_text(version_yaml, encoding="utf-8")
    return validate_frontmatter.main(["--config", str(cfg)])


def test_known_version_accepted_silently(tmp_path: Path) -> None:
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="1.0")) == 0


def test_unknown_version_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run_with_config(tmp_path, _CONFIG_KNOWN.format(version="9.9")) == 2
    assert "unknown cli_documentation.version" in capsys.readouterr().err


def test_non_string_version_exits_2(tmp_path: Path) -> None:
    bad = _CONFIG_KNOWN.replace('version: "{version}"', "version: 1.0")  # bare float
    assert _run_with_config(tmp_path, bad) == 2


def test_dogfood_config_selects_1_0() -> None:
    cfg = validate_frontmatter.load_config(Path(".project-standards.yml"))
    assert cfg.cli_documentation_version == "1.0"
