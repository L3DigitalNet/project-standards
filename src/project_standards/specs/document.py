"""Parse a consumer spec into a SpecDocument.

Frontmatter scalar values come from PyYAML so inline comments on values like
`profile: full # ...` are stripped exactly as consumers expect. Key order still
comes from a small regex because YAML mappings do not preserve the syntactic
surface the frontmatter validator checks.
"""

from __future__ import annotations

import re
from typing import Any, cast

import yaml

from project_standards.specs.model import SpecDocument
from project_standards.specs.registry import (
    ID_TOKEN,
    NOT_AN_ID,
    gh_slug,
    headings,
    numkey,
    section_numbers,
    split_front_matter,
)

_DECLARE_ROW = re.compile(r"^\|\s*`([A-Z]{1,4})-`\s*\|[^|]*\|\s*([^|]+?)\s*\|", re.M)
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


def parse_document(path: str, text: str) -> SpecDocument:
    """Parse a project spec document into the command-facing model."""
    try:
        fm, body = split_front_matter(text)
    except ValueError as exc:
        raise SpecParseError(f"{path}: malformed frontmatter fence: {exc}") from exc
    hs = headings(body)
    scalars = _scalar_frontmatter(fm)
    used: dict[str, list[tuple[str, int]]] = {}
    for m in ID_TOKEN.finditer(body):
        pfx = m.group(1)
        if pfx in NOT_AN_ID:
            continue
        line = body[: m.start()].count("\n") + 1
        used.setdefault(pfx, []).append((f"{pfx}-{m.group(2)}", line))
    apx = re.search(r"## Appendix A:.*?(?=\n## |\Z)", body, re.S)
    declared = (
        {r.group(1): r.group(2).strip() for r in _DECLARE_ROW.finditer(apx.group(0))} if apx else {}
    )
    return SpecDocument(
        path=path,
        profile=scalars.get("profile"),
        frontmatter_keys=_fm_key_order(fm),
        frontmatter=scalars,
        body=body,
        sections=section_numbers(hs),
        slugs=_anchor_slugs(hs),
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
        return (sec, start) if sec is not None and start is not None else None
    name = definedin.strip().lower()
    lines = doc.body.splitlines(keepends=True)
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
