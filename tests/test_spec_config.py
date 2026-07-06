from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs.config import DiscoveryError, collect_spec_paths, load_spec_config


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


def test_reference_prefixes_parsed_from_config(tmp_path: Path) -> None:
    cfg = load_spec_config(
        _write(
            tmp_path,
            "spec:\n  include:\n    - '**/*.md'\n  reference_prefixes:\n    - ADR\n    - RQ\n",
        )
    )
    assert cfg.reference_prefixes == ["ADR", "RQ"]


def test_reference_prefixes_defaults_to_empty(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "spec:\n  include:\n    - '**/*.md'\n"))
    assert cfg.reference_prefixes == []


def test_reference_prefixes_absent_when_no_spec_block(tmp_path: Path) -> None:
    cfg = load_spec_config(_write(tmp_path, "markdown:\n  frontmatter:\n    include: []\n"))
    assert cfg.reference_prefixes == []
