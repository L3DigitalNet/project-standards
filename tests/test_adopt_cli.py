from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.cli import main


def test_list_plain_lists_four_standards(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list"])
    out = capsys.readouterr().out
    assert rc == 0
    for sid in ("markdown-frontmatter", "adr", "markdown-tooling", "python-tooling"):
        assert sid in out


def test_list_json_schema(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["list", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    ids = {s["id"] for s in data}
    assert "python-tooling" in ids
    for s in data:  # stable schema: every standard carries a contract_version key
        assert "contract_version" in s
    py = next(s for s in data if s["id"] == "python-tooling")
    assert any(a["kind"] == "fragment" and a["target"] == "pyproject.toml" for a in py["artifacts"])


def test_list_on_broken_manifest_exits_clean(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A malformed/absent bundle manifest must yield a documented exit code, not a traceback.
    import project_standards.cli as cli
    from project_standards.adopt.errors import ManifestError

    def boom(_sid: str) -> object:
        raise ManifestError("manifest missing")

    monkeypatch.setattr(cli, "load_manifest", boom)
    rc = main(["list"])
    assert rc == 3
    assert "manifest missing" in capsys.readouterr().err


def test_bundle_ids_align_with_registry_contract_versions() -> None:
    # Drift guard (both directions): every adoptable bundle maps to a non-None registry
    # contract version, and the registry's version-tracked standards are exactly the bundles.
    from project_standards.adopt.manifest import available_standards
    from project_standards.cli import _contract_version  # pyright: ignore[reportPrivateUsage]
    from project_standards.registry import load_registry

    reg = load_registry()
    bundle_ids = set(available_standards())
    registry_ids = {
        "markdown-frontmatter": reg.frontmatter_default,
        "adr": reg.adr_default,
        "python-tooling": reg.python_tooling_default,
        "markdown-tooling": reg.markdown_tooling_default,
    }
    assert bundle_ids == set(registry_ids)
    for sid in bundle_ids:
        assert _contract_version(reg, sid) is not None, sid


def test_adopt_unknown_standard_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["adopt", "nope"])
    assert rc == 2
    assert "unknown standard" in capsys.readouterr().err


def test_validate_subcommand_delegates_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    # `project-standards validate --config X --quiet` must forward ALL flags to the validator
    # (regression guard for the argparse REMAINDER trap — must not exit 2 before delegating).
    import project_standards.cli as cli

    captured: list[list[str]] = []

    def fake_validate(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    monkeypatch.setattr(cli.validate_frontmatter, "main", fake_validate)
    rc = main(["validate", "--config", ".project-standards.yml", "--quiet"])
    assert rc == 0
    assert captured == [["--config", ".project-standards.yml", "--quiet"]]


def test_adopt_dest_not_a_directory_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    rc = main(["adopt", "markdown-tooling", "--dest", str(missing)])
    assert rc == 2


def test_adopt_markdown_tooling_creates_files(tmp_path: Path) -> None:
    rc = main(["adopt", "markdown-tooling", "--dest", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".markdownlint.json").is_file()
    assert (tmp_path / ".editorconfig").is_file()
    caller = (tmp_path / ".github/workflows/lint-markdown.yml").read_text()
    assert "{{ref}}" not in caller and "@v" in caller
