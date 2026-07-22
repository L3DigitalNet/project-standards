"""Cross-tool parity: the frontmatter formatter and the pinned Prettier must agree
on scalar quoting (issue #26). Before FR-008 the formatter single-quoted every
scalar and doubled apostrophes (`'Apple''s'`), which Prettier — under this repo's
`.prettierrc.json` `**/*.md` `singleQuote: true` override — rewrites to the
no-escape spelling `"Apple's"`; the two tools then fight forever. This runs the
real pinned Prettier binary over formatter-produced output and asserts Prettier
leaves it byte-identical. A missing Node toolchain is a task failure, not a skip."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from project_standards.format_frontmatter import format_text

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PRETTIER = _REPO_ROOT / "node_modules" / ".bin" / "prettier"

# A document whose only non-canonical concern is an apostrophe-bearing scalar. The
# formatter must emit it in the quote style Prettier already prefers.
_APOSTROPHE_DOC = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'note-a3f9zk-x'\n"
    'title: "Apple\'s"\n'
    "description: 'A doc.'\n"
    "doc_type: 'note'\n"
    "status: 'draft'\n"
    "created: '2026-06-08'\n"
    "updated: '2026-06-08'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n"
    "\n"  # Prettier keeps one blank line after the frontmatter fence; pre-canonical
    "# Body\n"  # body isolates the scalar-quoting parity as the only variable under test
)


def test_formatter_output_stable_under_pinned_prettier() -> None:
    # A missing Prettier binary is a hard failure: the cross-tool contract cannot be
    # demonstrated without the pinned toolchain (`npm ci`).
    if not _PRETTIER.exists():
        pytest.fail(
            f"pinned Prettier binary not found at {_PRETTIER}; run `npm ci` "
            "(the Node toolchain is required for this gate, never skipped)"
        )

    formatted, _changed, _warnings = format_text(_APOSTROPHE_DOC, path=None)

    # The probe file must live INSIDE the repo tree: Prettier resolves overrides by
    # matching the `**/*.md` glob against the file path relative to the config's
    # directory, so an out-of-tree temp path silently falls back to base
    # `singleQuote: false` and rewrites every scalar. mkdtemp under the repo root
    # keeps the probe transient and cleaned up regardless of assertion outcome.
    probe_dir = Path(tempfile.mkdtemp(dir=_REPO_ROOT, prefix="prettier_probe_"))
    try:
        probe = probe_dir / "frontmatter.md"
        probe.write_text(formatted, encoding="utf-8")
        result = subprocess.run(
            [str(_PRETTIER), str(probe.relative_to(_REPO_ROOT))],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    assert result.stdout == formatted, (
        "pinned Prettier rewrote the formatter output — the issue #26 quoting fight "
        "is live; the emitter must produce Prettier's minimal-escape spelling"
    )
