"""The catalog-wide schema-payload-reference invariant, asserted exactly once.

`PC-SCHEMA-PAYLOAD-REFERENCE` is a property of the whole package repository: every
`const`/`enum` in every declared JSON schema must name a version or migration that the
payload it belongs to actually declares. Eighteen per-version contract modules each ran
this identical whole-repository check, so a single stale reference failed eighteen tests
while eighteen `build_package_repository(_ROOT)` walks (~2.4 s each) bought no coverage
beyond the first. The check lives here now; the per-version modules keep only the
sweeps that inspect their own payload bytes.

Synthetic-repository cases that prove the *detection* logic (what the finding says when
a reference really is stale) stay in `test_graph.py` — this module only asserts that the
real catalog is clean.
"""

from __future__ import annotations

from pathlib import Path

from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references

_ROOT = Path(__file__).resolve().parents[2]


def test_repository_schemas__reference_only_declared_payload_versions() -> None:
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []
