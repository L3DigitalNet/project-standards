"""Protocol-neutral DTO and error types exposed by the MCP service facade.

These are the frozen §5.5 DTO shapes (ADR 0025): mapped views over validated V2
package and control-plane facts, never a second durable schema. Nothing in
``mcp_services`` may import the MCP SDK or the ``mcp_server`` adapter package,
and no SDK type may appear in a public signature, return value, or exception.
Stable fields compare verbatim (DR-009): collections carry a declared ordering,
paths are root-relative, and timestamps/durations are absent.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _ServiceModel(BaseModel):
    """Immutable strict base for every protocol-neutral DTO.

    ``strict=True`` matters here: stable facts must arrive as their exact types,
    so a mapper bug (stringly typed major, str-for-bytes content) fails loudly
    instead of being silently coerced.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RelationshipSet(_ServiceModel):
    """Exact V2 family relations; independence is the empty default (DR-006)."""

    companions: tuple[str, ...] = ()
    extends: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


class ResourceDescriptor(_ServiceModel):
    """One declared payload resource behind its canonical four-segment URI.

    The URI grammar is frozen by ADR 0026:
    ``standards://{standard_id}/{version}/resources/{resource_id}``.
    """

    uri: str
    resource_id: str
    role: str
    media_type: str
    digest: str
    standard_id: str
    package_version: str


class ResourceContent(_ServiceModel):
    """One resource descriptor plus its digest-verified immutable bytes."""

    descriptor: ResourceDescriptor
    data: bytes


class ProviderDescriptor(_ServiceModel):
    """Declared provider identity and execution contract facts (DR-001)."""

    provider_id: str
    operation: str
    kind: str
    phase: str
    effect: str


class StandardDescriptor(_ServiceModel):
    """One exact standard package version derived from validated V2 facts.

    ``resources`` and ``providers`` are ordered by their declared IDs — the
    explicit documented key required by DR-009 for collections whose authored
    manifest order is not semantically meaningful.
    """

    standard_id: str
    title: str
    status: str
    package_version: str
    exposure: str
    capabilities: tuple[str, ...]
    relationships: RelationshipSet
    resources: tuple[ResourceDescriptor, ...]
    providers: tuple[ProviderDescriptor, ...]


class CatalogDescriptor(_ServiceModel):
    """One catalog generation with its ordered exact standard descriptors."""

    catalog_major: int
    standards: tuple[StandardDescriptor, ...]


class ServiceError(Exception):
    """Structured service failure with a stable code and remediation.

    Stable codes are part of the service contract: ``catalog-invalid`` for
    construction failures, ``standard-not-found`` / ``resource-not-found`` for
    exact-lookup misses, and ``resource-integrity`` for per-read declaration,
    containment, or digest violations. The message never carries raw file or
    secret content.
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        remediation: str,
        standard_id: str | None = None,
        version: str | None = None,
        path: str | None = None,
        severity: str = "error",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation
        self.standard_id = standard_id
        self.version = version
        self.path = path
        self.severity = severity
