"""Parse a consumer spec into a SpecDocument.

Frontmatter scalar values come from PyYAML so inline comments on values like
`profile: full # ...` are stripped exactly as consumers expect. Key order still
comes from a small regex because YAML mappings do not preserve the syntactic
surface the frontmatter validator checks.
"""

from __future__ import annotations

import bisect
import re
from typing import Any, cast

import yaml

from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import (
    BUILTIN_REFERENCE_PREFIXES,
    ID_TOKEN,
    NOT_AN_ID,
    _masked_structural_view,  # pyright: ignore[reportPrivateUsage]
    anchor_headings,
    declared_prefixes,
    gh_slug,
    headings,
    numkey,
    section_numbers,
    split_front_matter,
)

_DEFINED_NUM = re.compile(r"([0-9]+(?:\.[0-9]+)*)")


class SpecParseError(ValueError):
    """Malformed or undecodable spec input; CLI converts this to a clean exit."""


def _scalar_frontmatter(fm: str) -> dict[str, str]:
    try:
        loaded: Any = yaml.safe_load(fm) if fm.strip() else {}
    except yaml.YAMLError as exc:
        raise SpecParseError(f"unparseable frontmatter: {exc}") from exc
    if not isinstance(loaded, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in cast("dict[str, Any]", loaded).items():
        if isinstance(v, str):
            out[str(k)] = v
        elif isinstance(v, int | float | bool):
            out[str(k)] = str(v)
    return out


def _fm_key_order(fm: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*):", fm, re.M)]


def _anchor_slugs(hs: list[tuple[int, str, int]]) -> frozenset[str]:
    """Valid in-document anchors, following GitHub's repeated-heading rule.

    GitHub disambiguates identically-titled headings by suffixing the 2nd, 3rd,
    ... occurrence with -1, -2, ... A plain deduped set would flag `#slug-1` as a
    dead anchor (SV-ANCHOR) on a spec whose link is actually correct.
    """
    counts: dict[str, int] = {}
    out: set[str] = set()
    for _lvl, text, _ln in hs:
        base = gh_slug(text)
        seen = counts.get(base, 0)
        out.add(base if seen == 0 else f"{base}-{seen}")
        counts[base] = seen + 1
    return frozenset(out)


def parse_document(
    path: str, text: str, reference_prefixes: frozenset[str] = frozenset()
) -> SpecDocument:
    """Parse a consumer spec into a SpecDocument.

    reference_prefixes are external namespaces the spec cites but does not own; like
    NOT_AN_ID and the built-in reference prefixes they are skipped in the ID scan.
    """
    try:
        fm, body = split_front_matter(text)
    except ValueError as exc:
        raise SpecParseError(f"{path}: malformed frontmatter fence: {exc}") from exc
    structural_body = _masked_structural_view(body)
    hs = headings(structural_body)
    anchors = anchor_headings(structural_body)
    scalars = _scalar_frontmatter(fm)
    nl_offsets = [i for i, ch in enumerate(body) if ch == "\n"]
    used: dict[str, list[tuple[str, int]]] = {}
    for m in ID_TOKEN.finditer(structural_body):
        pfx = m.group(1)
        if pfx in NOT_AN_ID or pfx in BUILTIN_REFERENCE_PREFIXES or pfx in reference_prefixes:
            continue
        # Version/SPDX shape: digits immediately followed by ".<digit>" (MPL-2.0, FR-1.2).
        # A real id at a sentence end (FR-007.) is "."+space, never "."+digit, so it survives.
        tail = structural_body[m.end() : m.end() + 2]
        if len(tail) == 2 and tail[0] == "." and tail[1].isdigit():
            continue
        line = bisect.bisect_left(nl_offsets, m.start()) + 1
        used.setdefault(pfx, []).append((f"{pfx}-{m.group(2)}", line))
    declared = declared_prefixes(structural_body)
    return SpecDocument(
        path=path,
        profile=scalars.get("profile"),
        frontmatter_keys=_fm_key_order(fm),
        frontmatter=scalars,
        body=body,
        sections=section_numbers(hs),
        slugs=_anchor_slugs(anchors),
        used_ids=used,
        declared_prefixes=declared,
    )


def section_slice(doc: SpecDocument, number: str) -> str | None:
    """Return a numbered section, including child subsections only."""
    lines = doc.body.splitlines(keepends=True)
    start = next((ln for n, ln in doc.sections if n == number), None)
    if start is None:
        return None
    depth = len(numkey(number))
    later = [ln for n, ln in doc.sections if ln > start and len(numkey(n)) <= depth]
    end = min(later) if later else len(lines) + 1
    return "".join(lines[start - 1 : end - 1]).rstrip()


def _defined_in_slice(doc: SpecDocument, definedin: str) -> tuple[str, int] | None:
    """Resolve Appendix-A Defined In text to (slice, start line)."""
    if m := _DEFINED_NUM.search(definedin):
        num = m.group(1)
        start = next((ln for n, ln in doc.sections if n == num), None)
        sec = section_slice(doc, num)
        return (
            (_masked_structural_view(sec), start) if sec is not None and start is not None else None
        )
    name = definedin.strip().lower()
    lines = _masked_structural_view(doc.body).splitlines(keepends=True)
    for i, line in enumerate(lines):
        if (hm := re.match(r"^(#+)\s+(.*)$", line)) and name in hm.group(2).strip().lower():
            level = len(hm.group(1))
            end = len(lines) + 1
            for j in range(i + 1, len(lines)):
                if (nm := re.match(r"^(#+)\s", lines[j])) and len(nm.group(1)) <= level:
                    end = j + 1
                    break
            return "".join(lines[i : end - 1]).rstrip(), i + 1
    return None


def definition_sites(doc: SpecDocument) -> dict[str, list[tuple[str, int]]]:
    """Return ID definitions only, excluding traceability/prose references."""
    defs: dict[str, list[tuple[str, int]]] = {}
    for pfx, definedin in doc.declared_prefixes.items():
        resolved = _defined_in_slice(doc, definedin)
        if resolved is None:
            continue
        sec, start = resolved
        row = re.compile(rf"^\|\s*`?({re.escape(pfx)}-\d+)`?\b")
        for i, line in enumerate(sec.splitlines()):
            if rm := row.match(line):
                defs.setdefault(pfx, []).append((rm.group(1), start + i))
    return defs
