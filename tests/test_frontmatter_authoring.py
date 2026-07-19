from __future__ import annotations

from pathlib import Path

import pytest

import project_standards.format_frontmatter as format_frontmatter
from project_standards.control_plane.executor import apply_authoring_plan
from project_standards.frontmatter_authoring import plan_frontmatter_fix
from project_standards.package_contract.paths import PackageVersion
from project_standards.validate_frontmatter import ConfigError


def _clear_schema_enum_cache() -> None:
    loader = getattr(format_frontmatter, "_valid_doc_types", None)
    if loader is not None:
        loader.cache_clear()


def test_frontmatter_fix_plans_combined_format_and_id_repair_before_apply(
    tmp_path: Path,
) -> None:
    source = (
        b"---\n"
        b"schema_version: '1.1'\n"
        b"id: wrong\n"
        b"title: Hello World\n"
        b"description: d\n"
        b"type: note\n"
        b"status: draft\n"
        b"created: '2026-01-01'\n"
        b"updated: '2026-01-02'\n"
        b"tags: []\n"
        b"aliases: []\n"
        b"related: []\n"
        b"---\n"
        b"# Body\n"
    )
    path = tmp_path / "doc.md"
    path.write_bytes(source)

    planned = plan_frontmatter_fix(
        tmp_path,
        (Path("doc.md"),),
        version=PackageVersion("1.2"),
        token_factory=lambda: "aaaaaa",
    )

    assert path.read_bytes() == source
    assert planned.plan.standard_id == "markdown-frontmatter"
    assert len(planned.plan.actions) == 1
    replacement = planned.plan.actions[0].content_bytes
    assert replacement is not None
    assert b"doc_type: 'note'" in replacement
    assert b"id: 'note-aaaaaa-hello-world'" in replacement
    assert planned.fixed_ids == (("doc.md", "note-aaaaaa-hello-world"),)

    result = apply_authoring_plan(tmp_path, planned.plan)

    assert result.success
    assert path.read_bytes() == replacement


def test_frontmatter_fix__missing_schema__raises_config_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "doc.md"
    path.write_text("# Body\n", encoding="utf-8")
    _clear_schema_enum_cache()
    monkeypatch.setattr(
        format_frontmatter,
        "_SCHEMA_PATH",
        tmp_path / "missing.schema.json",
    )

    try:
        with pytest.raises(ConfigError, match="cannot load doc_type enum"):
            plan_frontmatter_fix(
                tmp_path,
                (Path("doc.md"),),
                version=PackageVersion("1.2"),
            )
    finally:
        _clear_schema_enum_cache()
