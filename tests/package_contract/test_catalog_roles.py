"""Family-wide, catalog-derived invariants that no per-version test should re-pin.

Every historical package-contract test (`test_<family>_<version>.py` for a version
that is no longer current) used to hardcode which sibling version currently holds
the catalog's `default` role, and where the family root's mutable navigation
(`README.md`, `agent-summary.md`) currently points. Both of those facts move on
every later cut in the family, so a historical test that pinned them broke on its
successor's release rather than on a regression of its own — the defect found
during the github-workflow 1.5 cut (#TBD-contract-tests).

This module is the one place that invariant belongs: derived from `catalogs/5.toml`
itself rather than from a hardcoded version literal, so it never needs editing when
a new cut becomes current. Per-version contract tests keep only what they can
prove about their own bytes, digest, declared artifacts, and their own (permanent,
once set) `retained`/`internal`/`reference-only` role.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

_ROOT = Path(__file__).resolve().parents[2]
_CATALOG = _ROOT / "catalogs/5.toml"
_STANDARDS = _ROOT / "standards"

# Roles a family may use instead of ever having a `default` row: both are
# permanent classifications, not a stage a package passes through toward
# `default`, so a family entirely in one of these roles is not missing a default —
# it is not default-eligible at all.
_NO_DEFAULT_ROLES = {"reference-only", "internal"}

# No known gaps remain: every default version now has its own
# test_<family>_<ver>.py (project-toolbox 1.0 closed in
# test_project_toolbox_1_0.py). Keep this frozenset as the documented escape
# hatch: a new gap gets a scoped ("family", "version") entry plus a comment
# naming the follow-up issue, rather than letting this invariant go red for an
# untracked reason.
_KNOWN_MISSING_CONTRACT_TESTS: frozenset[tuple[str, str]] = frozenset()


def _family_id_to_test_stub(family_id: str) -> str:
    """`agent-handoff` -> `agent_handoff`, matching the `test_<family>_<ver>.py` convention."""
    return family_id.replace("-", "_")


def _version_to_test_stub(version: str) -> str:
    """`1.15` -> `1_15`, matching the `test_<family>_<ver>.py` convention."""
    return version.replace(".", "_")


def _catalog_entries() -> list[dict[str, str]]:
    catalog = tomllib.loads(_CATALOG.read_text(encoding="utf-8"))
    return cast("list[dict[str, str]]", catalog["packages"])


def _roles_by_family() -> dict[str, list[tuple[str, str]]]:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for entry in _catalog_entries():
        grouped.setdefault(entry["id"], []).append((entry["version"], entry["role"]))
    return grouped


def test_catalog_roles__every_default_eligible_family__has_exactly_one_default() -> None:
    """A family either has one `default` row, or is entirely reference-only/internal.

    Two defaults would make `version = "latest"` ambiguous; zero defaults on an
    otherwise consumer-shaped family would leave that resolution with nothing to
    select. Reference-only (Python Coding) and internal (Standard Bundle
    Authoring) families are the sanctioned exception: they are never selected by
    `latest` at all.
    """
    for family_id, rows in _roles_by_family().items():
        defaults = [version for version, role in rows if role == "default"]
        non_default_only_roles = {role for _, role in rows} <= _NO_DEFAULT_ROLES

        if non_default_only_roles:
            assert defaults == [], f"{family_id} is reference-only/internal but has a default row"
        else:
            assert len(defaults) == 1, (
                f"{family_id} must have exactly one default row, found {defaults}"
            )


def test_catalog_roles__every_default_version__has_its_own_contract_test() -> None:
    """The version a consumer actually receives on `latest` must be the one this
    repository's own package-contract suite proves against — not just a
    predecessor's file that happened to keep passing.
    """
    for family_id, rows in _roles_by_family().items():
        for version, role in rows:
            if role != "default" or (family_id, version) in _KNOWN_MISSING_CONTRACT_TESTS:
                continue
            expected = (
                Path(__file__).parent
                / f"test_{_family_id_to_test_stub(family_id)}_{_version_to_test_stub(version)}.py"
            )
            assert expected.is_file(), (
                f"{family_id}@{version} is the catalog default but {expected.name} is missing"
            )


def test_catalog_roles__family_root_navigation__points_at_the_current_default() -> None:
    """`README.md`, `adopt.md`, and `agent-summary.md` at each family root are mutable
    navigation that repoints on every activation. Checking that dynamically here
    (derived from the catalog, not a hardcoded version literal) is what lets
    per-version contract tests stop pinning it — the assertion that used to break
    every historical github-workflow, markdown-frontmatter, and python-tooling test
    on each new cut.

    `adopt.md` joined the set when the last per-version navigation pins were deleted
    at the 5.27.0 activation. It had been covered only by those historical tests, so
    dropping them without widening this one would have left the family-root adoption
    guide unpinned for every future cut.
    """
    for family_id, rows in _roles_by_family().items():
        defaults = [version for version, role in rows if role == "default"]
        if not defaults:
            continue
        (current_version,) = defaults
        family_root = _STANDARDS / family_id

        for document in ("README.md", "adopt.md", "agent-summary.md"):
            path = family_root / document
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            assert f"versions/{current_version}/" in content, (
                f"{family_id}/{document} does not reference its current default {current_version}"
            )
