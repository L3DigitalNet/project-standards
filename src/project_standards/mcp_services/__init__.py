"""SDK-free, protocol-neutral service layer for the MCP server (ADR 0025).

This package is the only surface the ``mcp_server`` adapter may call, and it
must never import ``mcp`` or ``mcp_server`` back: the dependency points one way.
Exports are limited to the frozen §5.5 facade and its DTO/error types.
"""

from project_standards.mcp_services.catalog import McpServiceFacade
from project_standards.mcp_services.models import (
    CatalogDescriptor,
    ProviderDescriptor,
    RelationshipSet,
    ResourceContent,
    ResourceDescriptor,
    ServiceError,
    StandardDescriptor,
)

__all__ = [
    "CatalogDescriptor",
    "McpServiceFacade",
    "ProviderDescriptor",
    "RelationshipSet",
    "ResourceContent",
    "ResourceDescriptor",
    "ServiceError",
    "StandardDescriptor",
]
