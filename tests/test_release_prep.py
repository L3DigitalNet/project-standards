"""Regression tests for the release-preparation operator handoff."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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
