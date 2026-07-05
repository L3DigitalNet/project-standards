"""Project-spec registry and document parsing helpers."""

from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

__all__ = ["load_registry", "parse_document"]
