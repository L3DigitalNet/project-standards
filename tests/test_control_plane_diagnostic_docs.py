"""Parity between the control-plane `CP-` vocabulary and its reference page.

The diagnostic codes are the stable part of control-plane output: consumers
grep them, runbooks quote them, and issue reports name them. They are declared
nowhere central — each one is a string literal at the site that raises or
reports it — so the only way to keep `docs/reference/control-plane-diagnostics.md`
honest is to re-derive the set from the source on every run (issue #189).

The check is bidirectional on purpose. A new code added to the control plane
fails here until it is documented, and a code deleted from the control plane
fails here until its row is removed, so the page can never describe a condition
the tool no longer produces.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _ROOT / "src" / "project_standards" / "control_plane"
_REFERENCE = _ROOT / "docs" / "reference" / "control-plane-diagnostics.md"

_CODE = re.compile(r"CP-[A-Z0-9]+(?:-[A-Z0-9]+)*")

# Only the first cell of a table row counts as documentation. Codes named in the
# page's prose (CP-DRIFT as the warning example, for instance) must not satisfy
# the parity check, or a code could be "documented" by a passing mention.
_TABLE_ROW = re.compile(r"^\|\s*`(CP-[A-Z0-9-]+)`\s*\|")


def _emitted_codes() -> set[str]:
    """Return every `CP-` code appearing in a control-plane string literal.

    Literals, not raw text: a comment that names a code is discussion, while a
    string literal is what actually reaches a finding, an exception message, or
    a `--json` payload. Docstrings are Constant nodes too and are deliberately
    included — a code named in a docstring is part of the module's described
    contract, and today no code appears only there.
    """
    codes: set[str] = set()
    for path in sorted(_SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                codes.update(_CODE.findall(node.value))
    return codes


def _documented_codes() -> list[str]:
    text = _REFERENCE.read_text(encoding="utf-8")
    return [match.group(1) for line in text.splitlines() if (match := _TABLE_ROW.match(line))]


def test_source_defines_diagnostic_codes() -> None:
    """Guard the extractor itself: an empty set would make parity vacuous."""
    assert len(_emitted_codes()) > 50


def test_every_emitted_code_is_documented() -> None:
    missing = sorted(_emitted_codes() - set(_documented_codes()))
    assert not missing, (
        f"control-plane codes missing from {_REFERENCE.relative_to(_ROOT)}: {missing}"
    )


def test_no_documented_code_is_obsolete() -> None:
    obsolete = sorted(set(_documented_codes()) - _emitted_codes())
    assert not obsolete, f"documented codes no longer emitted by the control plane: {obsolete}"


def test_reference_has_no_duplicate_rows() -> None:
    documented = _documented_codes()
    duplicates = sorted({code for code in documented if documented.count(code) > 1})
    assert not duplicates, f"duplicate rows in the reference table: {duplicates}"
