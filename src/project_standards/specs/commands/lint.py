"""Advisory authoring-quality warnings for specs that already pass validate."""

from __future__ import annotations

import re

from project_standards.specs.document import section_slice
from project_standards.specs.model import Finding, Registry, SpecDocument

_ANGLE = re.compile(r"<[^>\n]+>")
_GUIDANCE = "> **Template instructions"


def _w(code: str, message: str, line: int | None = None, locus: str | None = None) -> Finding:
    return Finding(code=code, severity="warning", message=message, line=line, locus=locus)


def lint_document(doc: SpecDocument, reg: Registry) -> list[Finding]:
    """Return advisory findings; callers decide whether warnings are strict."""
    out: list[Finding] = []
    for i, line in enumerate(doc.body.splitlines(), start=1):
        if _ANGLE.search(line):
            out.append(_w("SL-PLACEHOLDER", "unfilled <angle-bracket> placeholder", line=i))
        if line.lstrip().startswith(_GUIDANCE):
            out.append(_w("SL-GUIDANCE", "template guidance not deleted", line=i))
    if doc.frontmatter.get("status") == "approved":
        out += _traceability(doc, reg)
    return out


def _must_frs(doc: SpecDocument) -> list[str]:
    """Return FR IDs whose §7.1 Priority column is exactly Must."""
    rows = [
        ln for ln in (section_slice(doc, "7.1") or "").splitlines() if ln.lstrip().startswith("|")
    ]
    if not rows:
        return []
    header = [c.strip().lower() for c in rows[0].strip().strip("|").split("|")]
    if "priority" not in header:
        return []
    pcol = header.index("priority")
    out: list[str] = []
    for line in rows[1:]:
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) > pcol and re.match(r"^FR-\d+$", cells[0]) and cells[pcol] == "Must":
            out.append(cells[0])
    return out


def _traceability(doc: SpecDocument, reg: Registry) -> list[Finding]:
    has_matrix = "17.3" in reg.tier_sections.get(doc.profile or "", frozenset())
    if has_matrix:
        matrix = section_slice(doc, "17.3") or ""
        missing = [fid for fid in _must_frs(doc) if fid not in matrix]
        return [
            _w("SL-TRACE", f"Must requirement {fid} not mapped in §17.3", locus=fid)
            for fid in dict.fromkeys(missing)
        ]
    dod = section_slice(doc, "17.1") or ""
    return [_w("SL-DOD", "unchecked Definition-of-Done item in §17.1")] if "- [ ]" in dod else []
