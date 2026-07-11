"""Syntax-preserving adapters for consumer-owned repository files."""

from project_standards.control_plane.adapters.base import (
    AdapterState,
    AdapterUnit,
    DocumentAdapter,
    UnitChange,
)
from project_standards.control_plane.adapters.editorconfig import EditorConfigAdapter
from project_standards.control_plane.adapters.jsonc import JsonAdapter, JsoncAdapter
from project_standards.control_plane.adapters.markdown import MarkdownBlockAdapter
from project_standards.control_plane.adapters.registry import AdapterRegistry
from project_standards.control_plane.adapters.toml import TomlAdapter
from project_standards.control_plane.adapters.whole_file import WholeFileAdapter
from project_standards.control_plane.adapters.yaml import YamlAdapter

__all__ = [
    "AdapterRegistry",
    "AdapterState",
    "AdapterUnit",
    "DocumentAdapter",
    "EditorConfigAdapter",
    "JsonAdapter",
    "JsoncAdapter",
    "MarkdownBlockAdapter",
    "TomlAdapter",
    "UnitChange",
    "WholeFileAdapter",
    "YamlAdapter",
]
