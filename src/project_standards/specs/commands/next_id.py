"""Compute the next free project-spec ID for a prefix."""

from __future__ import annotations

from project_standards.specs.model import Registry, SpecDocument


def next_free_id(doc: SpecDocument, reg: Registry, prefix: str) -> str:
    """Return the next available ID, honoring tier and width rules."""
    prefix = prefix.rstrip("-").upper()
    tier_ok = reg.tier_prefixes.get(doc.profile or "full", frozenset())
    if prefix not in reg.prefix_defined_in:
        raise ValueError(f"unknown prefix {prefix!r}")
    if prefix not in tier_ok:
        raise ValueError(f"prefix {prefix!r} not valid at {doc.profile} tier")
    used = doc.used_ids.get(prefix, [])
    highest = max((int(fid.split("-", 1)[1]) for fid, _ in used), default=0)
    nxt = highest + 1
    return f"{prefix}-{nxt}" if prefix == "MS" else f"{prefix}-{nxt:03d}"
