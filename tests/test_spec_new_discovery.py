"""collect_existing_spec_ids: tolerant of an empty corpus, strict on broken config."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.specs import cli as spec_cli
from project_standards.specs import config as cfgmod
from project_standards.specs.config import (
    ConfigError,
    SpecConfig,
    collect_existing_spec_ids,
    load_spec_config,
)


def _cfg(tmp: Path, body: str) -> SpecConfig:
    p = tmp / ".project-standards.yml"
    p.write_text(body, encoding="utf-8")
    return load_spec_config(p)


def test_no_spec_block_yields_empty_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert collect_existing_spec_ids(_cfg(tmp_path, "markdown:\n  frontmatter: {}\n")) == set()


def test_zero_match_include_yields_empty_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = _cfg(tmp_path, "spec:\n  include:\n    - docs/specs/**/*.md\n")
    assert collect_existing_spec_ids(cfg) == set()


def test_collects_ids_and_skips_malformed_neighbor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "good.md").write_text(
        "---\nspec_id: SPEC-7F3Q\n---\n# t\n", encoding="utf-8"
    )
    # Unterminated frontmatter fence -> SpecParseError -> skipped, not fatal.
    (tmp_path / "docs" / "bad.md").write_text(
        "---\nspec_id: SPEC-9Z9Z\n# no close\n", encoding="utf-8"
    )
    cfg = _cfg(tmp_path, "spec:\n  include:\n    - docs/*.md\n")
    assert collect_existing_spec_ids(cfg) == {"SPEC-7F3Q"}


def test_existing_id_resolution__legacy_and_selected__matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "one.md").write_text("---\nspec_id: SPEC-7F3Q\n---\n# One\n", encoding="utf-8")
    config = _cfg(tmp_path, "spec:\n  include: docs/*.md\n")
    runtime = spec_cli._SpecRuntime(  # pyright: ignore[reportPrivateUsage]
        repo=tmp_path,
        effective_config={"include_patterns": ["docs/*.md"]},
    )

    assert spec_cli._selected_existing_ids(  # pyright: ignore[reportPrivateUsage]
        runtime
    ) == collect_existing_spec_ids(config)


def test_non_discovery_configerror_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only DiscoveryError becomes an empty set; every OTHER ConfigError still propagates.
    def _boom(explicit: list[Path], cfg: SpecConfig) -> list[Path]:
        raise ConfigError("boom")

    monkeypatch.setattr(cfgmod, "collect_spec_paths", _boom)
    with pytest.raises(ConfigError):
        collect_existing_spec_ids(SpecConfig(include=["x"], exclude=[], present=True))
