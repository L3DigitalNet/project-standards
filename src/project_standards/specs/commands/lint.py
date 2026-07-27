"""Advisory authoring-quality warnings for specs that already pass validate."""

from __future__ import annotations

import re

from project_standards.specs.document import section_slice
from project_standards.specs.model import (
    Finding,
    Registry,
    SpecDocument,
    absolute_finding_lines,
)
from project_standards.specs.registry import (
    _masked_structural_view,  # pyright: ignore[reportPrivateUsage]
)

_ANGLE = re.compile(r"<[^>\n]+>")
_BACKTICK_RUN = re.compile(r"`+")
# A code span that is nothing but one angle group is how the shipped templates write
# their own fields (`<capability>`, `<owner>`), so it stays visible to the scan;
# blanket-masking inline code would silence this rule on an entirely unfilled template.
# Anything else in the span makes the angle group domain notation instead — a
# metavariable (`test_<unit>_<scenario>`) or generic call shape (`_Probe(<base>)`).
_CODE_FIELD = re.compile(r"`+\s*<[^<>\n]+>\s*`+")
# GFM autolinks are valid Markdown, and are the fix markdownlint's MD034 prescribes for
# a bare URL; flagging them would put the two managed linters in direct conflict. The
# email alternative follows GFM's own grammar rather than "anything with an @": a
# permissive form let `<owner@>` and `<user@@example.com>` — which GFM renders as
# literal text, so they are unfilled placeholders — pass as links (issue #65 follow-up).
_URI_AUTOLINK = r"[A-Za-z][A-Za-z0-9+.-]{1,31}:[^<>\s]*"
_EMAIL_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_EMAIL_AUTOLINK = rf"[A-Za-z0-9.!#$%&'*+/=?^_`{{|}}~-]+@{_EMAIL_LABEL}(?:\.{_EMAIL_LABEL})*"
_AUTOLINK = re.compile(rf"<(?:{_URI_AUTOLINK}|{_EMAIL_AUTOLINK})>")
_GUIDANCE = "> **Template instructions"


def _mask_code_spans(line: str) -> str:
    """Mask inline code spans with CommonMark backtick-run pairing.

    A span opens with a run of N backticks and closes with the next run of
    exactly N; a run with no such closer is literal text. Greedy `` `+[^`]*`+ ``
    matching instead split a span that nests a shorter run (```` ``x` <t> `y`` ````
    read as two spans) and fused unbalanced runs into one (```` ``x <t>` y` ````),
    flipping this rule's verdict either way. Masking to spaces rather than
    deleting keeps offsets, so a removed span cannot join the text on either side
    of it into an angle pair that was never written. Spans are line-scoped, since
    the whole rule is: a span wrapped across a newline is out of scope.
    """
    runs = [(match.start(), match.end()) for match in _BACKTICK_RUN.finditer(line)]
    parts: list[str] = []
    cursor = 0
    index = 0
    while index < len(runs):
        start, end = runs[index]
        closer = next(
            (
                candidate
                for candidate in range(index + 1, len(runs))
                if runs[candidate][1] - runs[candidate][0] == end - start
            ),
            None,
        )
        if closer is None:
            index += 1
            continue
        span = line[start : runs[closer][1]]
        parts.append(line[cursor:start])
        parts.append(span if _CODE_FIELD.fullmatch(span) else " " * len(span))
        cursor = runs[closer][1]
        index = closer + 1
    parts.append(line[cursor:])
    return "".join(parts)


def _placeholder_angles(line: str) -> bool:
    """Report whether a line holds an angle pair that is neither notation nor a link."""
    visible = _mask_code_spans(line)
    return any(not _AUTOLINK.fullmatch(m.group(0)) for m in _ANGLE.finditer(visible))


def _w(code: str, message: str, line: int | None = None, locus: str | None = None) -> Finding:
    return Finding(code=code, severity="warning", message=message, line=line, locus=locus)


def lint_document(doc: SpecDocument, reg: Registry) -> list[Finding]:
    """Return advisory findings; callers decide whether warnings are strict."""
    out: list[Finding] = []
    structural_body = _masked_structural_view(doc.body)
    for i, line in enumerate(structural_body.splitlines(), start=1):
        if _placeholder_angles(line):
            out.append(_w("SL-PLACEHOLDER", "unfilled <angle-bracket> placeholder", line=i))
        if line.lstrip().startswith(_GUIDANCE):
            out.append(_w("SL-GUIDANCE", "template guidance not deleted", line=i))
    if doc.frontmatter.get("status") == "approved":
        out += _traceability(doc, reg)
    return absolute_finding_lines(out, body_line_offset=doc.body_line_offset)


def _must_frs(doc: SpecDocument) -> list[str]:
    """Return FR IDs whose §7.1 Priority column is exactly Must."""
    structural_section = _masked_structural_view(section_slice(doc, "7.1") or "")
    rows = [ln for ln in structural_section.splitlines() if ln.lstrip().startswith("|")]
    if not rows:
        return []
    header = [c.strip().lower() for c in rows[0].strip().strip("|").split("|")]
    if "priority" not in header:
        return []
    pcol = header.index("priority")
    out: list[str] = []
    for line in rows[1:]:
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) > pcol and re.match(r"^FR-\d+$", cells[0]) and cells[pcol].lower() == "must":
            out.append(cells[0])
    return out


def _traceability(doc: SpecDocument, reg: Registry) -> list[Finding]:
    has_matrix = "17.3" in reg.tier_sections.get(doc.profile or "", frozenset())
    if has_matrix:
        matrix = _masked_structural_view(section_slice(doc, "17.3") or "")
        missing = [fid for fid in _must_frs(doc) if fid not in matrix]
        return [
            _w("SL-TRACE", f"Must requirement {fid} not mapped in §17.3", locus=fid)
            for fid in dict.fromkeys(missing)
        ]
    dod = _masked_structural_view(section_slice(doc, "17.1") or "")
    return [_w("SL-DOD", "unchecked Definition-of-Done item in §17.1")] if "- [ ]" in dod else []
