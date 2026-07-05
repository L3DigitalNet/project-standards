"""Shared project-spec ID prefixes resolve to identical sections in every tier."""

from __future__ import annotations

from project_standards.specs.registry import (
    TEMPLATES_DIR,
    TIER_FILES,
    declared_prefixes,
    split_front_matter,
)


def test_defined_in_identical_across_tiers() -> None:
    per_tier: dict[str, dict[str, str]] = {}
    for tier, fname in TIER_FILES.items():
        _fm, body = split_front_matter((TEMPLATES_DIR / fname).read_text(encoding="utf-8"))
        per_tier[tier] = declared_prefixes(body)
    shared = set(per_tier["light"]) & set(per_tier["standard"]) & set(per_tier["full"])
    for pfx in shared:
        values = {per_tier[t][pfx] for t in TIER_FILES}
        assert len(values) == 1, f"{pfx}- Defined In differs across tiers: {values}"
