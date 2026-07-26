from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION_PROMISE = "every setting the migration provider recognizes is accepted there"


def test_issue_21_package_option_migration_guidance_is_semantically_complete() -> None:
    upgrading = (_ROOT / "UPGRADING.md").read_text(encoding="utf-8")
    assert (
        "Every setting a selected package's migration provider recognizes may be set "
        "under that package's namespace in `.project-standards.yml`"
    ) in upgrading
    assert "ownership escape or ordinary option" in upgrading

    for version in ("1.6", "1.7", "1.8"):
        source = (_ROOT / f"standards/python-tooling/versions/{version}/adopt.md").read_text(
            encoding="utf-8"
        )
        installed = (
            _ROOT / f"src/project_standards/payloads/python-tooling/{version}/adopt.md"
        ).read_text(encoding="utf-8")
        assert _MIGRATION_PROMISE in source
        assert _MIGRATION_PROMISE in installed

    assert "additional_source_roots" in (
        _ROOT / "standards/python-tooling/versions/1.6/adopt.md"
    ).read_text(encoding="utf-8")
    assert "coverage = false" in (
        _ROOT / "standards/python-tooling/versions/1.7/adopt.md"
    ).read_text(encoding="utf-8")
    assert "pytest.test_paths" in (
        _ROOT / "standards/python-tooling/versions/1.8/adopt.md"
    ).read_text(encoding="utf-8")
