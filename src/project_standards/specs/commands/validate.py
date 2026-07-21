"""Validate a SpecDocument against the canonical Registry."""

from __future__ import annotations

import re

from project_standards.specs.document import definition_sites
from project_standards.specs.model import Finding, Registry, SpecDocument
from project_standards.specs.registry import (
    _masked_structural_view,  # pyright: ignore[reportPrivateUsage]
    appendix_letters,
    numkey,
)

# Range dashes: en-dash (\u2013), em-dash (\u2014), and hyphen. Em-dash is
# common via editor autocorrect; without it a "14 to 16 omitted" range note
# leaves the interior sections looking like un-annotated gaps (SV-GAP).
_OMIT = re.compile(r"§(\d+)\s*[\u2013\u2014-]\s*§?(\d+)")
_OMIT_SINGLE = re.compile(r"§(\d+)")
# A blockquote covers a section gap only when it both names the section and
# carries one of these markers. Tier notes say "intentionally omitted"; the
# exceptions process (case-1 tailoring) also lets an author delete a conditional
# section outright with a one-line reason, whose natural wordings are the other
# markers. A marker is required — template preambles name section numbers in
# blockquotes ("§5, §8.4 … are absent by design"), so accepting any §-bearing
# blockquote would let retained boilerplate cover every real gap.
_OMIT_MARKERS = ("omitted", "omission", "does not apply", "not applicable")
_SECTION_REF = re.compile(r"§\s?([0-9]+(?:\.[0-9]+)*)")
_ANCHOR = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")
# Inline code spans hide their contents from GFM table parsing, so pipes
# inside them (and backslash-escaped pipes) are not column delimiters. Count
# only real delimiters, or a cell like a code-span pipe inflates the count.
_INLINE_CODE = re.compile(r"`+[^`]*`+")


def _delim_pipes(line: str) -> int:
    """Count GFM column-delimiter pipes, ignoring inline code and escaped pipes."""
    return _INLINE_CODE.sub("", line).replace("\\|", "").count("|")


def _f(code: str, message: str, line: int | None = None, locus: str | None = None) -> Finding:
    return Finding(code=code, severity="error", message=message, line=line, locus=locus)


def validate_document(doc: SpecDocument, reg: Registry) -> list[Finding]:
    """Return integrity findings; an empty list means the spec passes."""
    structural_body = _masked_structural_view(doc.body)
    out: list[Finding] = []
    out += _check_frontmatter(doc, reg)
    out += _check_sections(doc, reg, structural_body)
    out += _check_appendices(doc, reg, structural_body)
    out += _check_references(doc, reg, structural_body)
    out += _check_ids(doc, reg)
    out += _check_tables(structural_body)
    return out


def _check_frontmatter(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    if tuple(doc.frontmatter_keys) != reg.frontmatter_keys:
        out.append(
            _f(
                "SV-FM-KEYS",
                f"frontmatter keys {doc.frontmatter_keys} != {list(reg.frontmatter_keys)}",
            )
        )
    spec_id = doc.frontmatter.get("spec_id", "")
    if spec_id == reg.sentinel:
        out.append(_f("SV-SENTINEL", "spec_id is the unfilled sentinel SPEC-____", locus="spec_id"))
    elif not re.match(reg.spec_id_pattern, spec_id):
        out.append(
            _f(
                "SV-SPEC-ID",
                f"spec_id {spec_id!r} does not match {reg.spec_id_pattern}",
                locus="spec_id",
            )
        )
    status = doc.frontmatter.get("status")
    if status not in {"draft", "review", "approved", "superseded"}:
        out.append(
            _f(
                "SV-STATUS",
                f"status {status!r} not in draft|review|approved|superseded",
                locus="status",
            )
        )
    if doc.profile not in reg.tier_sections:
        out.append(
            _f("SV-PROFILE", f"profile {doc.profile!r} not in light|standard|full", locus="profile")
        )
    return out


def _check_sections(doc: SpecDocument, reg: Registry, structural_body: str) -> list[Finding]:
    out: list[Finding] = []
    for n, ln in doc.sections:
        if n not in reg.canonical_sections:
            out.append(
                _f("SV-SECTION", f"§{n} is not in the canonical registry", line=ln, locus=f"§{n}")
            )
    order = [numkey(n) for n, _ in doc.sections]
    if order != sorted(order):
        out.append(_f("SV-ORDER", "section headings are not in ascending numeric order"))
    covered: set[int] = set()
    for line in structural_body.splitlines():
        lowered = line.lower()
        if line.lstrip().startswith(">") and any(m in lowered for m in _OMIT_MARKERS):
            for a, b in _OMIT.findall(line):
                covered.update(range(int(a), int(b) + 1))
            covered.update(int(x) for x in _OMIT_SINGLE.findall(line))
    canon_top = {int(n) for n in reg.canonical_sections if "." not in n}
    present_top = {int(n) for n, _ in doc.sections if "." not in n}
    for n in sorted(canon_top - present_top):
        if n not in covered:
            out.append(
                _f(
                    "SV-GAP",
                    f"gap at §{n} is not annotated with an omission note "
                    f"(a blockquote naming §{n} that says omitted, omission, "
                    f"does not apply, or not applicable)",
                    locus=f"§{n}",
                )
            )
    return out


def _check_appendices(doc: SpecDocument, reg: Registry, structural_body: str) -> list[Finding]:
    out: list[Finding] = []
    apps = appendix_letters(structural_body)
    if apps != sorted(apps):
        out.append(_f("SV-APX-ORDER", f"appendix letters not ascending: {apps}"))
    for required in ("A", "B", "D"):
        if required not in apps:
            out.append(_f("SV-APX-MISSING", f"Appendix {required} missing"))
    if doc.profile == "full":
        for letter in reg.full_only_appendices:
            if letter not in apps:
                out.append(_f("SV-APX-FULL", f"Full must contain Appendix {letter}"))
    else:
        for letter in reg.full_only_appendices:
            if letter in apps:
                out.append(_f("SV-APX-FULLONLY", f"Appendix {letter} is Full-only", locus=letter))
    return out


def _check_references(doc: SpecDocument, reg: Registry, structural_body: str) -> list[Finding]:
    out: list[Finding] = []
    for m in _SECTION_REF.finditer(structural_body):
        ref = m.group(1)
        if ref not in reg.canonical_sections and ref.split(".")[0] not in reg.canonical_sections:
            ln = structural_body[: m.start()].count("\n") + 1
            out.append(_f("SV-XREF", f"§{ref} not in canonical registry", line=ln, locus=f"§{ref}"))
    for m in _ANCHOR.finditer(structural_body):
        if m.group(2) not in doc.slugs:
            ln = structural_body[: m.start()].count("\n") + 1
            out.append(_f("SV-ANCHOR", f"dead anchor #{m.group(2)}", line=ln, locus=m.group(2)))
    return out


def _check_ids(doc: SpecDocument, reg: Registry) -> list[Finding]:
    out: list[Finding] = []
    tier_ok = reg.tier_prefixes.get(doc.profile or "", frozenset())
    for pfx, occurrences in doc.used_ids.items():
        for full_id, ln in occurrences:
            digits = full_id.split("-", 1)[1]
            ok = (pfx == "MS" and len(digits) == 1) or (pfx != "MS" and len(digits) == 3)
            if not ok:
                out.append(_f("SV-ID-FMT", f"{full_id} bad width", line=ln, locus=full_id))
        if pfx not in doc.declared_prefixes:
            out.append(
                _f(
                    "SV-ID-UNDECLARED",
                    f"prefix {pfx}- is not declared in this spec's Appendix A. If it names "
                    "an external namespace (backlog, tickets, another spec), add it to "
                    "spec.reference_prefixes; otherwise declare it in Appendix A.",
                    locus=f"{pfx}-",
                )
            )
        elif pfx not in tier_ok:
            out.append(
                _f("SV-ID-TIER", f"prefix {pfx}- not valid at {doc.profile} tier", locus=f"{pfx}-")
            )
    seen: set[str] = set()
    for sites in definition_sites(doc).values():
        for full_id, ln in sites:
            if full_id in seen:
                out.append(
                    _f("SV-ID-DUP", f"duplicate definition of {full_id}", line=ln, locus=full_id)
                )
            seen.add(full_id)
    for pfx, definedin in doc.declared_prefixes.items():
        canon = reg.prefix_defined_in.get(pfx)
        if canon is not None and definedin != canon:
            out.append(
                _f(
                    "SV-ID-DEFINED",
                    f"{pfx}- Defined In {definedin!r} != canonical {canon!r}",
                    locus=f"{pfx}-",
                )
            )
    return out


def _check_tables(structural_body: str) -> list[Finding]:
    out: list[Finding] = []
    lines = structural_body.splitlines()
    i = 0
    while i < len(lines):
        if (
            lines[i].strip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])
        ):
            cols = _delim_pipes(lines[i])
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                if j != i + 1 and _delim_pipes(lines[j]) != cols:
                    out.append(
                        _f(
                            "SV-TABLE",
                            f"L{j + 1}: {_delim_pipes(lines[j])} pipes vs header {cols}",
                            line=j + 1,
                        )
                    )
                j += 1
            i = j
        else:
            i += 1
    return out
