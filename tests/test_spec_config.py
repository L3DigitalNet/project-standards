from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.config import DiscoveryError, collect_spec_paths, load_spec_config
from project_standards.validate_frontmatter import ConfigError


def _write(tmp: Path, body: str) -> Path:
    cfg = tmp / ".project-standards.yml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_missing_spec_block_no_paths_raises(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "markdown:\n  frontmatter:\n    include: []\n"))
    assert cfg.present is False
    with pytest.raises(DiscoveryError):
        collect_spec_paths([], cfg)


def test_zero_match_include_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include:\n    - docs/specs/**/*.md\n"))
    assert cfg.present is True
    with pytest.raises(DiscoveryError):
        collect_spec_paths([], cfg)


def test_empty_include_list_does_not_fall_back_to_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "stray.md").write_text("x", encoding="utf-8")
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include: []\n"))
    assert cfg.present is True
    with pytest.raises(DiscoveryError):
        collect_spec_paths([], cfg)


def test_explicit_path_bypasses_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "a.md"
    spec.write_text("x", encoding="utf-8")
    cfg = load_spec_config(_write(tmp_path, "markdown:\n  frontmatter: {}\n"))
    assert collect_spec_paths([spec], cfg) == [spec]


def test_explicit_path_survives_config_exclude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    spec = tmp_path / "docs" / "s.md"
    spec.write_text("x", encoding="utf-8")
    cfg = load_spec_config(
        _write(
            tmp_path,
            "spec:\n  include:\n    - '**/*.md'\n  exclude:\n    - 'docs/**'\n",
        )
    )
    assert collect_spec_paths([spec], cfg) == [spec]


def test_reference_prefixes_parsed(tmp_path: Path) -> None:
    cfg = load_spec_config(
        _write(tmp_path, "spec:\n  include: ['x/**']\n  reference_prefixes: ['RQ', 'GAP']\n")
    )
    assert cfg.reference_prefixes == ["RQ", "GAP"]


def test_reference_prefixes_default_empty(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include: ['x/**']\n"))
    assert cfg.reference_prefixes == []


def test_spec_version_parsed(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "spec:\n  version: '1.0'\n  include: ['x/**']\n"))
    assert cfg.version == "1.0"


def test_unknown_spec_version_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"unknown spec\.version"):
        load_spec_config(_write(tmp_path, "spec:\n  version: '9.9'\n"))


def test_spec_version_must_be_quoted_string(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="must be a quoted string"):
        load_spec_config(_write(tmp_path, "spec:\n  version: 1.0\n"))


def test_reference_prefixes_bad_shape_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="1-4 uppercase"):
        load_spec_config(_write(tmp_path, "spec:\n  reference_prefixes: ['rq']\n"))


def test_reference_prefixes_canonical_collision_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="canonical spec-local prefix"):
        load_spec_config(_write(tmp_path, "spec:\n  reference_prefixes: ['FR']\n"))
