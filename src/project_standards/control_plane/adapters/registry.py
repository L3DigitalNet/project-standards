"""Closed adapter dispatch keyed by manifest-declared semantic format."""

from __future__ import annotations

from project_standards.control_plane.adapters.base import DocumentAdapter
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.package_contract.payload import AdapterKind


class AdapterRegistry:
    """Register exactly one implementation for each supported adapter kind."""

    def __init__(self) -> None:
        self._adapters: dict[AdapterKind, DocumentAdapter] = {}

    def register(self, kind: AdapterKind, adapter: DocumentAdapter) -> None:
        if kind in self._adapters:
            raise ControlPlaneError(f"adapter kind is already registered: {kind.value}")
        if adapter.kind is not kind:
            raise ControlPlaneError("adapter implementation declares a different kind")
        self._adapters[kind] = adapter

    def get(self, kind: AdapterKind) -> DocumentAdapter:
        try:
            return self._adapters[kind]
        except KeyError as exc:
            raise ControlPlaneError(f"adapter kind is not registered: {kind.value}") from exc
