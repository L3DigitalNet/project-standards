"""Syntax-preserving adapters for consumer-owned repository files."""

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    DocumentAdapter,
    UnitChange,
)
from project_standards.control_plane.adapters.registry import AdapterRegistry
from project_standards.control_plane.adapters.toml import TomlAdapter
from project_standards.control_plane.adapters.whole_file import WholeFileAdapter

__all__ = [
    "AdapterRegistry",
    "AdapterState",
    "AdapterUnit",
    "DocumentAdapter",
    "TomlAdapter",
    "UnitChange",
    "WholeFileAdapter",
]
