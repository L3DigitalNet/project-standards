"""Shared semantic-unit contract for syntax-preserving document adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from project_standards.control_plane.diagnostics import ActionKind
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import AdapterKind, JsonValue


@dataclass(frozen=True, slots=True)
class AdapterUnit:
    """One normalized owned scope inspected from a physical document."""

    scope: str
    value: JsonValue | bytes
    raw: bytes
    semantic_digest: Sha256Digest


@dataclass(frozen=True, slots=True)
class AdapterState:
    """Exact source bytes plus the semantic units addressed by a caller."""

    content: bytes
    units: tuple[AdapterUnit, ...]


@dataclass(frozen=True, slots=True)
class UnitChange:
    """One requested semantic-unit transition supplied to an adapter."""

    kind: ActionKind
    scope: str
    content: bytes | None = None
    value: JsonValue | bytes | None = None
    prune_empty_ancestors: bool = False


class DocumentAdapter(Protocol):
    """Inspect and render one document without touching the live repository."""

    kind: AdapterKind

    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState: ...

    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes: ...
