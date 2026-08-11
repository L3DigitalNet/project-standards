"""Regression tests for the release-preparation operator handoff."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import CaptureFixture


def _release_prep_module() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "scripts" / "release_prep.py"
    spec = importlib.util.spec_from_file_location("release_prep", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_catalog(root: Path, packages: list[tuple[str, str, str]]) -> None:
    catalog = ['schema_version = "1.0"', "catalog_major = 5", ""]
    for family, version, role in packages:
        catalog.extend(
            [
                "[[packages]]",
                f'id = "{family}"',
                f'version = "{version}"',
                'digest = "sha256:test"',
                f'role = "{role}"',
                "",
            ]
        )
    (root / "catalogs").mkdir(parents=True, exist_ok=True)
    (root / "catalogs" / "5.toml").write_text("\n".join(catalog), encoding="utf-8")


def _selection_tuples(review: Any) -> list[tuple[str, str, str]]:
    return [
        (selection.family, selection.version, selection.role) for selection in review.selections
    ]


def _stub_release_flow(
    release_prep: Any,
    monkeypatch: pytest.MonkeyPatch,
    current: Any,
) -> None:
    def check_preconditions(_target: object) -> tuple[Any, Any]:
        return (current, release_prep.StepResult("preconditions", "ok", "ready"))

    def plan_changelog(_target: object, *, today: str) -> Any:
        return release_prep.ChangelogPlan("", today, "planned")

    def previous_release_tag(_target: object) -> str:
        return "v5.18.0"

    def step(*_args: object, **_kwargs: object) -> Any:
        return release_prep.StepResult("step", "planned", "none")

    def verify(*_args: object, **_kwargs: object) -> list[Any]:
        return []

    monkeypatch.setattr(release_prep, "check_preconditions", check_preconditions)
    monkeypatch.setattr(release_prep, "plan_changelog", plan_changelog)
    monkeypatch.setattr(release_prep, "_previous_release_tag", previous_release_tag)
    monkeypatch.setattr(release_prep, "bump_version", step)
    monkeypatch.setattr(release_prep, "sweep_version_references", step)
    monkeypatch.setattr(release_prep, "apply_changelog", step)
    monkeypatch.setattr(release_prep, "verify_chain", verify)


def test_print_summary__prepared_release__prints_required_pre_tag_candidate_verification(
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    current = release_prep.Version.parse("5.13.0")
    target = release_prep.Version.parse("5.13.1")
    result = release_prep.StepResult("1. preconditions", "ok", "tree clean")

    release_prep.print_summary([result], target, current, "v5.13.0")

    summary = capsys.readouterr().out
    wheel = "build/release-wheel/project_standards-5.13.1-py3-none-any.whl"
    assert "uv sync --all-groups --locked" in summary
    assert "npm ci" in summary
    assert "standards sync-payload-projection --root . --check --json" in summary
    assert "uv build --clear --wheel --out-dir build/release-wheel" in summary
    assert "rm -rf -- build/wheel-runtime" in summary
    assert f"python -m zipfile -e {wheel} build/wheel-runtime" in summary
    assert 'export PYTHONPATH="$PWD/build/wheel-runtime"' in summary
    assert "scripts/verify.sh --full" in summary
    assert "uv run project-standards validate" in summary
    assert "standards validate-packages --root . --json" in summary
    assert "standards validate-graph --root . --require-all-manifests --json" in summary
    assert "standards generate-package-schemas --root . --check --json" in summary
    assert "packages check-release --root . --baseline v5.13.0 --json" in summary
    assert summary.index("uv sync --all-groups --locked") < summary.index(
        "uv build --clear --wheel --out-dir build/release-wheel"
    )
    assert summary.index(
        "standards sync-payload-projection --root . --check --json"
    ) < summary.index("uv build --clear --wheel --out-dir build/release-wheel")
    assert summary.index(
        "standards sync-payload-projection --root . --check --json"
    ) < summary.index("git tag -as v5.13.1")
    assert summary.index("npm ci") < summary.index("scripts/verify.sh --full")
    assert summary.index("scripts/verify.sh --full") < summary.index("git tag -as v5.13.1")


def test_check_preconditions__non_main_branch__refuses_release_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()

    def git(*args: str) -> str:
        if args == ("status", "--porcelain"):
            return ""
        assert args == ("rev-parse", "--abbrev-ref", "HEAD")
        return "testing\n"

    monkeypatch.setattr(release_prep, "_git", git)
    monkeypatch.setattr(release_prep, "_current_version", lambda: release_prep.Version(5, 13, 0))

    with pytest.raises(release_prep.ReleasePrepError, match="must run on 'main'"):
        release_prep.check_preconditions(release_prep.Version(5, 13, 1))


def test_main__stale_package_reference__reports_before_release_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    (tmp_path / "catalogs").mkdir()
    (tmp_path / "catalogs" / "5.toml").write_text(
        """\
schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "adr"
version = "1.4"
digest = "sha256:old"
role = "retained"

[[packages]]
id = "adr"
version = "1.5"
digest = "sha256:new"
role = "default"
""",
        encoding="utf-8",
    )
    family = tmp_path / "standards" / "adr"
    family.mkdir(parents=True)
    family.joinpath("README.md").write_text(
        "Current consumer package: `adr@1.4`.\n",
        encoding="utf-8",
    )

    current = release_prep.Version(5, 18, 0)
    target = release_prep.Version(5, 19, 0)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    _stub_release_flow(release_prep, monkeypatch, current)

    assert release_prep.main([str(target), "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "package-version references (review; nothing was rewritten)" in output
    assert (
        "standards/adr/README.md:1: family=adr observed=1.4 expected=1.5 "
        "reason=current exact-selector"
    ) in output


def test_plan_package_version_references__catalog_roles__selects_numeric_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()
    _write_catalog(
        tmp_path,
        [
            ("candidate-only", "3.0", "candidate"),
            ("consumer", "1.8", "retained"),
            ("consumer", "1.9", "default"),
            ("consumer", "2.0", "candidate"),
            ("internal", "2.9", "internal"),
            ("internal", "2.10", "internal"),
            ("reference", "0.9", "reference-only"),
            ("reference", "0.10", "reference-only"),
        ],
    )
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    review = release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))

    assert _selection_tuples(review) == [
        ("consumer", "1.9", "default"),
        ("internal", "2.10", "internal"),
        ("reference", "0.10", "reference-only"),
    ]
    assert review.mismatches == ()


def test_plan_package_version_references__root_forms__reports_only_current_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    _write_catalog(
        tmp_path,
        [
            ("adr", "1.4", "retained"),
            ("adr", "1.5", "default"),
            ("python-coding", "0.5", "reference-only"),
            ("python-coding", "0.6", "reference-only"),
            ("standard-bundle-authoring", "2.9", "internal"),
            ("standard-bundle-authoring", "2.10", "internal"),
        ],
    )
    adr = tmp_path / "standards" / "adr"
    adr.mkdir(parents=True)
    adr.joinpath("README.md").write_text(
        """\
Current selector `adr@1.4`.
Current [standard](versions/1.4/README.md).
project-standards standards enable adr --version 1.4
The adr version `1.4` is current.
Package version `1.4` is current.
ADR 1.4 standard is current.
Selected `adr@1.5` is already current.

## Migration

The superseded package `adr@1.4` remains historical.
""",
        encoding="utf-8",
    )
    adr.joinpath("agent-summary.md").write_text(
        """\
<!-- release-consistency: historical adr -->
The old selector `adr@1.4` is preserved for comparison.
""",
        encoding="utf-8",
    )
    python_coding = tmp_path / "standards" / "python-coding"
    python_coding.mkdir(parents=True)
    python_coding.joinpath("README.md").write_text(
        "Python Coding 0.6 is the current reference-only package.\n",
        encoding="utf-8",
    )
    internal = tmp_path / "standards" / "standard-bundle-authoring"
    internal.mkdir(parents=True)
    internal.joinpath("README.md").write_text(
        "Internal package `2.10` is current; 2.9 remains advertised as released history.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    before = {
        path: path.read_bytes()
        for path in (
            tmp_path / "catalogs" / "5.toml",
            adr / "README.md",
            adr / "agent-summary.md",
            python_coding / "README.md",
            internal / "README.md",
        )
    }

    review = release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))
    result = release_prep.report_package_version_references(review)

    assert len(review.mismatches) == 6
    assert [mismatch.kind for mismatch in review.mismatches] == [
        "exact-selector",
        "versioned-link",
        "enable-command",
        "family-prose",
        "family-prose",
        "named-prose",
    ]
    assert result.status == "ok"
    assert result.detail == "6 package-version mismatch occurrence(s) reported for review"
    assert "python-coding" not in capsys.readouterr().out
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("catalog", "message"),
    [
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.05"
role = "default"
""",
            "non-canonical package version",
        ),
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.5"
role = "default"
[[packages]]
id = "adr"
version = "1.5"
role = "retained"
""",
            "duplicates package/version adr@1.5",
        ),
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.5"
role = "default"
[[packages]]
id = "adr"
version = "2.0"
role = "internal"
""",
            "ambiguous selection for adr",
        ),
    ],
)
def test_plan_package_version_references__invalid_catalog__fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    catalog: str,
    message: str,
) -> None:
    release_prep = _release_prep_module()
    (tmp_path / "catalogs").mkdir()
    (tmp_path / "catalogs" / "5.toml").write_text(catalog, encoding="utf-8")
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    with pytest.raises(release_prep.ReleasePrepError, match=message):
        release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))


def test_main__missing_candidate_catalog__fails_before_bump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    current = release_prep.Version(5, 18, 0)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    _stub_release_flow(release_prep, monkeypatch, current)

    def unexpected_bump(*_args: object, **_kwargs: object) -> Any:
        pytest.fail("version bump ran before package-reference preflight")

    monkeypatch.setattr(release_prep, "bump_version", unexpected_bump)

    assert release_prep.main(["5.19.0", "--dry-run"]) == 1
    assert "cannot read candidate catalog catalogs/5.toml" in capsys.readouterr().err


def test_sweep_version_references__agent_summary_only__preserves_old_target_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    summary = tmp_path / "standards" / "adr" / "agent-summary.md"
    summary.parent.mkdir(parents=True)
    summary.write_text("Outgoing tool release 5.18.0.\n", encoding="utf-8")
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    result = release_prep.sweep_version_references(release_prep.Version(5, 18, 0))

    assert result.detail == "0 occurrence(s) of 5.18.0 reported for review"
    assert "  none" in capsys.readouterr().out
