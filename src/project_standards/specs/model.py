"""Frozen data shapes shared across the spec tooling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Registry:
    """Canonical rules parsed once from the bundled project-spec templates."""

    canonical_sections: frozenset[str]
    section_titles: dict[str, str]
    appendices: dict[str, frozenset[str]]
    full_only_appendices: frozenset[str]
    prefix_defined_in: dict[str, str]
    frontmatter_keys: tuple[str, ...]
    tier_sections: dict[str, frozenset[str]]
    tier_prefixes: dict[str, frozenset[str]]
    sentinel: str
    spec_id_pattern: str


@dataclass(frozen=True)
class Finding:
    """One validate/lint finding, also the stable JSON record shape."""

    code: str
    severity: str
    message: str
    line: int | None = None
    locus: str | None = None


@dataclass
class SpecDocument:
    """Parsed consumer spec, ready for validate/lint/extract/next commands."""

    path: str
    profile: str | None
    frontmatter_keys: list[str]
    frontmatter: dict[str, str]
    body: str
    sections: list[tuple[str, int]]
    slugs: frozenset[str]
    used_ids: dict[str, list[tuple[str, int]]]
    declared_prefixes: dict[str, str]
