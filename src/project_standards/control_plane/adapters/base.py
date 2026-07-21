"""Shared semantic-unit contract for syntax-preserving document adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import AdapterKind, JsonValue


def line_end_without_newline(line: str) -> int:
    if line.endswith("\r\n"):
        return len(line) - 2
    if line.endswith("\n"):
        return len(line) - 1
    return len(line)


def decode_utf8(content: bytes, label: str) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError(f"{label} content is not valid UTF-8") from exc


def decode_json_pointer(value: str) -> tuple[str, ...]:
    """Decode the tokens of one RFC 6901 pointer (leading "/" required by callers)."""
    return tuple(
        component.replace("~1", "/").replace("~0", "~") for component in value.split("/")[1:]
    )


def apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    updated = text
    for start, end, replacement in sorted(edits, reverse=True):
        updated = f"{updated[:start]}{replacement}{updated[end:]}"
    return updated


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
