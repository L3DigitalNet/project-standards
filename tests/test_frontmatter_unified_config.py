from __future__ import annotations

from pathlib import Path

import pytest

from project_standards import (
    format_frontmatter,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards.validate_frontmatter import ConfigError, load_cli_config


def _write_unified_config(root: Path) -> None:
    control = root / ".standards"
    control.mkdir()
    (control / "config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-frontmatter]
enabled = true
version = "1.2"

[standards.markdown-frontmatter.config]
contract_version = "1.1"
schema = "custom"
schema_path = ".standards/extensions/markdown-frontmatter/schema.json"
required = false
include = ["handbook/**/*.md"]
exclude = ["handbook/generated/**"]

[standards.markdown-frontmatter.config.references]
enabled = true
""",
        encoding="utf-8",
    )


def test_cli_config_loads_frontmatter_options_from_repository_root(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)

    config, legacy = load_cli_config(tmp_path, explicit_legacy=None)

    assert legacy is False
    assert config.frontmatter_version == "1.1"
    assert config.schema == ".standards/extensions/markdown-frontmatter/schema.json"
    assert config.required is False
    assert config.include == ["handbook/**/*.md"]
    assert config.exclude == ["handbook/generated/**"]
    assert config.references_enabled is True


def test_cli_config_rejects_dual_authority(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)
    (tmp_path / ".project-standards.yml").write_text("markdown: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="dual authority"):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_cli_config_retains_explicit_legacy_debug_path(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.yml"
    legacy_path.write_text(
        "markdown:\n  frontmatter:\n    version: '1.1'\n    include: ['docs/**']\n",
        encoding="utf-8",
    )

    config, legacy = load_cli_config(tmp_path, explicit_legacy=legacy_path)

    assert legacy is True
    assert config.frontmatter_version == "1.1"
    assert config.include == ["docs/**"]


def test_frontmatter_cli_suite_uses_unified_config_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = tmp_path / ".standards"
    control.mkdir()
    (control / "config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-frontmatter]
enabled = true
version = "1.2"

[standards.markdown-frontmatter.config]
contract_version = "1.1"
schema = "markdown-frontmatter"
required = false
include = ["plain.md"]
exclude = []

[standards.markdown-frontmatter.config.references]
enabled = false
""",
        encoding="utf-8",
    )
    (tmp_path / "plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--quiet"]) == 0
    assert validate_id.main(["--quiet"]) == 0
    assert validate_references.main(["--quiet"]) == 0
    assert format_frontmatter.main(["--quiet"]) == 0
