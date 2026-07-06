from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent
_BIN = _REPO / "node_modules" / ".bin"
_CORPUS = Path(__file__).resolve().parent / "corpus"
# CR-001: the corpus lives in tmp_path (outside the repo), so Prettier's upward
# config discovery would miss the repo's .prettierrc.json and use defaults —
# proving nothing. Pass the shipped configs explicitly to both tools.
_PRETTIER_CFG = str(_REPO / ".prettierrc.json")
_MDLINT_CFG = str(_REPO / ".markdownlint.json")

pytestmark = pytest.mark.skipif(
    not (_BIN / "prettier").exists() or not (_BIN / "markdownlint-cli2").exists(),
    reason="Node dev deps not installed (run `npm ci`); behavioral coherence is a CI-only gate",
)


def _prettier_write(target: Path) -> None:
    subprocess.run(
        [_BIN / "prettier", "--config", _PRETTIER_CFG, "--write", str(target)],
        cwd=_REPO,
        check=True,
    )


def _markdownlint(target: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [_BIN / "markdownlint-cli2", "--config", _MDLINT_CFG, str(target)],
        cwd=_REPO,
        capture_output=True,
    )


def test_corpus_co_satisfies(tmp_path: Path) -> None:
    work = tmp_path / "adversarial.md"
    work.write_text((_CORPUS / "adversarial.md").read_text(encoding="utf-8"), encoding="utf-8")
    _prettier_write(work)  # Prettier owns formatting
    result = _markdownlint(work)  # markdownlint must accept Prettier's output
    assert result.returncode == 0, result.stderr.decode()


def test_prettier_is_idempotent(tmp_path: Path) -> None:
    work = tmp_path / "adversarial.md"
    work.write_text((_CORPUS / "adversarial.md").read_text(encoding="utf-8"), encoding="utf-8")
    _prettier_write(work)
    once = work.read_text(encoding="utf-8")
    _prettier_write(work)
    assert work.read_text(encoding="utf-8") == once
