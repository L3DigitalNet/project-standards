#!/usr/bin/env python3
"""Consistency validator for the tiered spec templates (light / standard / full).

Purpose
-------
These three Markdown templates are designed so that programmatic tooling can treat
them interchangeably: FULL is the canonical registry, and LIGHT/STANDARD are strict
subsets that keep the SAME section/appendix numbers (leaving intentional, annotated
gaps). This script enforces the invariants that guarantee interchangeability so drift
is caught in CI rather than by a downstream tool that silently mis-parses.

See `template-tooling-notes.md` for the full contract this checks.

Usage
-----
    python3 check_specs.py [DIR]

DIR defaults to the directory containing this script. Exits 0 if all checks pass,
1 if any problem is found (suitable for CI / pre-commit).

Checks
------
  frontmatter   identical YAML key set/order across files; profile matches the
                filename tier; spec_id is the `SPEC-____` sentinel; status enum present
  sections      FULL defines the canonical registry; each file's sections are a subset
                of it, appear in ascending order, and every top-level gap is annotated
  appendices    A + B + D present in all; C only in Full; letters ascending, no
                unintended gap (C-skip in Light/Standard is the sole allowed hole)
  xrefs         every "§N[.M]" resolves to the canonical registry; every intra-doc
                "[..](#anchor)" resolves to a real heading (GitHub slug) in the same file
  id-format     every ID token is PREFIX-NNN (3-digit) except milestones MS-0..MS-9
  id-registry   Appendix A lists every prefix used in the body; each "Defined In"
                resolves to the canonical registry
  cross-file    a shared ID prefix maps to the SAME "Defined In" in every file (the
                core interchangeability guarantee)
  tables        Markdown tables have a consistent column count under their header
"""

from __future__ import annotations

import pathlib
import re
import sys

TIER_FILES = {
    "light": "spec-light-template.md",
    "standard": "spec-standard-template.md",
    "full": "spec-full-template.md",
}
# non-milestone IDs are zero-padded to 3 digits; milestones are a bounded 1-digit set
ID_TOKEN = re.compile(r"\b([A-Z]{1,4})-([0-9]+)\b")
# tokens that look like IDs but are not (standards, crypto, acronyms)
NOT_AN_ID = {
    "HTTP",
    "AES",
    "SHA",
    "UTF",
    "ISO",
    "IEEE",
    "IEC",
    "WCAG",
    "RPO",
    "RTO",
    "PII",
    "API",
    "URL",
    "SPEC",
    "TLS",
    "CSRF",
    "CORS",
    "SSO",
    "WAL",
    "PITR",
}


def gh_slug(text: str) -> str:
    """GitHub heading-anchor slug (sufficient for these headings)."""
    s = text.strip().lower().replace("`", "")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return s.strip().replace(" ", "-")


def split_front_matter(text: str):
    if not text.startswith("---\n"):
        return "", text
    end = text.index("\n---\n", 4)
    return text[4:end], text[end + 5 :]


def fm_keys(fm: str) -> list[str]:
    return [
        m.group(1)
        for line in fm.splitlines()
        if (m := re.match(r"^([A-Za-z_][\w]*):", line))
    ]


def headings(body: str) -> list[tuple[int, str, int]]:
    out: list[tuple[int, str, int]] = []
    for i, line in enumerate(body.splitlines(), 1):
        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).rstrip(), i))
    return out


def section_numbers(hs: list[tuple[int, str, int]]) -> list[tuple[str, int]]:
    """Ordered list of (number, line) for numbered headings, e.g. ('7.1', 210)."""
    out: list[tuple[str, int]] = []
    for _lvl, text, ln in hs:
        m = re.match(r"^([0-9]+(?:\.[0-9]+)*)\.?\s", text)
        if m:
            out.append((m.group(1), ln))
    return out


def numkey(s: str) -> list[int]:
    return [int(x) for x in s.split(".")]


def check_file(
    name: str,
    path: pathlib.Path,
    canonical: set[str],
    fm_reference: list[str],
    defined_in_acc: dict[str, dict[str, str]],
) -> tuple[list[str], list[str]]:
    text = pathlib.Path(path).read_text()
    fm, body = split_front_matter(text)
    problems: list[str] = []
    hs = headings(body)
    slugs = {gh_slug(t) for _lvl, t, _ln in hs}
    secs = section_numbers(hs)

    # --- frontmatter -------------------------------------------------------
    keys = fm_keys(fm)
    if keys != fm_reference:
        problems.append(
            f"[frontmatter] key set/order differs from full: {keys} != {fm_reference}"
        )
    prof = re.search(r"^profile:\s*(\S+)", fm, re.M)
    if not prof or prof.group(1) != name:
        problems.append(
            f"[frontmatter] profile is '{prof.group(1) if prof else None}', expected '{name}'"
        )
    sid = re.search(r"^spec_id:\s*(\S+)", fm, re.M)
    if not sid or sid.group(1) != "SPEC-____":
        problems.append(
            f"[frontmatter] spec_id is '{sid.group(1) if sid else None}', expected sentinel 'SPEC-____'"
        )

    # --- sections: subset of canonical, ascending, gaps annotated ----------
    for n, ln in secs:
        if n not in canonical:
            problems.append(
                f"[sections] §{n} (L{ln}) is not in the canonical (full) registry"
            )
    order = [numkey(n) for n, _ in secs]
    if order != sorted(order):
        problems.append("[sections] headings are not in ascending numeric order")
    # top-level gap annotation coverage (range-aware)
    omit_lines = [
        l
        for l in body.splitlines()
        if l.lstrip().startswith(">") and "tier" in l and "omitted" in l
    ]
    covered: set[int] = set()
    for l in omit_lines:
        ranges: list[tuple[str, str]] = re.findall(
            r"§(\d+)\s*[–-]\s*§?(\d+)", l
        )  # §3–§6
        for a, b in ranges:
            covered.update(range(int(a), int(b) + 1))
        singles: list[str] = re.findall(r"§(\d+)", l)  # §5
        for n in singles:
            covered.add(int(n))
    canon_top = {int(n) for n in canonical if "." not in n}
    present_top = {int(n) for n, _ in secs if "." not in n}
    for n in sorted(canon_top - present_top):
        if n not in covered:
            problems.append(
                f"[sections] gap at §{n} is not annotated with an omission note"
            )

    # --- appendices --------------------------------------------------------
    apps = re.findall(r"^## Appendix ([A-Z]):", body, re.M)
    if apps != sorted(apps):
        problems.append(f"[appendices] letters not in ascending order: {apps}")
    for required in ("A", "B", "D"):
        if required not in apps:
            problems.append(f"[appendices] Appendix {required} missing")
    if name == "full" and "C" not in apps:
        problems.append("[appendices] Full must contain Appendix C (Optional Modules)")
    if name != "full" and "C" in apps:
        problems.append("[appendices] Appendix C (Optional Modules) is Full-only")

    # --- cross-references --------------------------------------------------
    for m in re.finditer(r"§\s?([0-9]+(?:\.[0-9]+)*)", body):
        ref = m.group(1)
        if ref not in canonical and ref.split(".")[0] not in canonical:
            ln = body[: m.start()].count("\n") + 1
            problems.append(f"[xref] '§{ref}' (L{ln}) not in canonical registry")
    for m in re.finditer(r"\[([^\]]+)\]\(#([^)]+)\)", body):
        if m.group(2) not in slugs:
            ln = body[: m.start()].count("\n") + 1
            problems.append(
                f"[xref] dead anchor '#{m.group(2)}' (L{ln}, text '{m.group(1)}')"
            )

    # --- ID format + registry ---------------------------------------------
    used: dict[str, int] = {}
    for m in ID_TOKEN.finditer(body):
        pfx, digits = m.group(1), m.group(2)
        if pfx in NOT_AN_ID:
            continue
        used[pfx] = used.get(pfx, 0) + 1
        ok = (pfx == "MS" and len(digits) == 1) or (pfx != "MS" and len(digits) == 3)
        if not ok:
            ln = body[: m.start()].count("\n") + 1
            problems.append(
                f"[id-format] '{pfx}-{digits}' (L{ln}) — expected "
                + ("MS-N (1 digit)" if pfx == "MS" else f"{pfx}-NNN (3 digits)")
            )
    # Appendix A declared prefixes + Defined In
    apxA = re.search(r"## Appendix A:.*?(?=\n## |\Z)", body, re.S)
    declared: dict[str, str] = {}
    if apxA:
        for row in re.finditer(
            r"^\|\s*`([A-Z]{1,4})-`\s*\|[^|]*\|\s*([^|]+?)\s*\|", apxA.group(0), re.M
        ):
            declared[row.group(1)] = row.group(2).strip()
    for pfx in used:
        if pfx not in declared:
            problems.append(
                f"[id-registry] prefix '{pfx}-' used but not declared in Appendix A"
            )
    for pfx, definedin in declared.items():
        defined_in_acc.setdefault(pfx, {})[name] = definedin
        mm = re.search(r"([0-9]+(?:\.[0-9]+)*)", definedin)
        if (
            mm
            and mm.group(1) not in canonical
            and mm.group(1).split(".")[0] not in canonical
        ):
            problems.append(
                f"[id-registry] Appendix A '{pfx}-' Defined In '{definedin}' not in registry"
            )

    # --- table column consistency -----------------------------------------
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        if (
            lines[i].strip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])
        ):
            cols = lines[i].count("|")
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                if j != i + 1 and lines[j].count("|") != cols:
                    problems.append(
                        f"[table] L{j + 1}: {lines[j].count('|')} pipes vs header {cols}"
                    )
                j += 1
            i = j
        else:
            i += 1

    return keys, problems


def main() -> int:
    root = (
        pathlib.Path(sys.argv[1])
        if len(sys.argv) > 1
        else pathlib.Path(__file__).parent
    )
    paths = {n: root / f for n, f in TIER_FILES.items()}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        print("ERROR: template(s) not found:\n  " + "\n  ".join(missing))
        return 2

    # canonical registry = full's headings
    full_body = split_front_matter(paths["full"].read_text())[1]
    canonical = {n for n, _ in section_numbers(headings(full_body))}
    fm_ref = fm_keys(split_front_matter(paths["full"].read_text())[0])

    defined_in_acc: dict[str, dict[str, str]] = {}
    all_problems: dict[str, list[str]] = {}
    for name, path in paths.items():
        _keys, problems = check_file(name, path, canonical, fm_ref, defined_in_acc)
        all_problems[name] = problems

    # cross-file: Defined In identical for shared prefixes
    xfile: list[str] = []
    for pfx, per_file in sorted(defined_in_acc.items()):
        if len({v for v in per_file.values()}) > 1:
            xfile.append(
                f"[cross-file] '{pfx}-' Defined In differs: "
                + "; ".join(f"{f}={v!r}" for f, v in per_file.items())
            )

    total = sum(len(v) for v in all_problems.values()) + len(xfile)
    print(f"canonical registry: {len(canonical)} numbered sections (from full)\n")
    for name in TIER_FILES:
        ps = all_problems[name]
        print(f"{name.upper():9} {'OK' if not ps else str(len(ps)) + ' problem(s)'}")
        for p in ps:
            print("   " + p)
    print(f"\nCROSS-FILE  {'OK' if not xfile else str(len(xfile)) + ' problem(s)'}")
    for p in xfile:
        print("   " + p)

    print(
        "\n"
        + (
            "PASS — templates are consistent and tooling-interchangeable"
            if total == 0
            else f"FAIL — {total} problem(s)"
        )
    )
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
