"""URI canonicalization and the resource registration set (ADR 0026, plan T6).

Deliberately SDK-free: only :mod:`~project_standards.mcp_server.transport` may
import the MCP SDK, so everything here is protocol-*neutral* and the SDK
projection is one mapping step away. Equally deliberately repository-free: this
module reaches package facts only through ``mcp_services``, because NFR-006 keeps
package and provider semantics outside the MCP layer. Both boundaries are
enforced by ``tests/mcp_server/contract/test_import_boundary.py``.

**One parse, one place.** ``parse_resource_uri`` is the single implementation of
ADR 0026's grammar and canonicalization rules, and every read goes through it
before anything else happens. That ordering is the contract, not an
optimization: the record requires omitted generations, mutable aliases,
percent-encoding mismatches, traversal, and undeclared identifiers to be refused
*before service lookup*, so the registry answers from the index it built at
construction and only a fully canonical, fully declared resource URI ever reaches
``McpServiceFacade.resource``.

**Registration is eager, reads are lazy.** ``ResourceRegistry.build`` walks the
catalog once, at construction, and the resulting set is fixed for the process
lifetime — which is what makes ADR 0026's ``listChanged: false`` truthful. No
payload byte is read while building the registry or while answering any listing
or metadata request; bytes enter protocol context only when a specific payload
URI is read, and then they come from the facade, which rechecks the declaration,
containment, and current digest on every single read (FR-003, FR-006).

**Why the catalog resource is concrete and the other two are templates.** The
catalog generation is fixed by ``models.CATALOG_MAJOR``, so
``standards://catalog/5`` names exactly one resource; the package and payload
forms are parameterized over the installed catalog, which is what lets a new
installed package appear with no code change (FR-004).

**What ``resources/list`` contains, and why it is not everything.** The listing
carries the catalog resource plus one entry per installed package version, so a
client that cannot expand templates still sees which standards and versions exist
without reading anything large. Declared payload resources are addressable but
unlisted: the catalog resource already enumerates every one of them with its
version-qualified URI (FR-001 requires exactly that), and duplicating the
enumeration in the listing costs 587 KB of wire against the real installed
Catalog 5 versus 12 KB without it — a 587 KB answer to the cheapest discovery
call is what NFR-002 and NFR-012 exist to prevent. Both sets are derived from the
catalog, so they grow with the installed distribution rather than with the code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from project_standards.mcp_server.models import CATALOG_MAJOR
from project_standards.mcp_services import (
    CatalogDescriptor,
    McpServiceFacade,
    ResourceDescriptor,
    ServiceError,
    StandardDescriptor,
)

SCHEME = "standards://"
CATALOG_SEGMENT = "catalog"
RESOURCES_SEGMENT = "resources"

#: The two parameterized forms ADR 0026 freezes, spelled exactly as the record
#: spells them. The record's stop/backtrack rule is explicit: an SDK that cannot
#: express these without changing their identity sends T6 back to T1 rather than
#: licensing an alternate URI shape.
PACKAGE_TEMPLATE = f"{SCHEME}{{standard_id}}/{{version}}"
RESOURCE_TEMPLATE = f"{SCHEME}{{standard_id}}/{{version}}/{RESOURCES_SEGMENT}/{{resource_id}}"

#: Metadata resources serve the ``mcp_services`` DTO projection verbatim, as
#: JSON. The media type is part of that contract: a client must not have to guess
#: that a body is machine-readable.
METADATA_MEDIA_TYPE = "application/json"

# Characters that can never appear in a canonical `standards://` URI. Percent is
# in the list because no declared identifier requires percent-encoding, so any
# percent triple is by definition "beyond what RFC 3986 makes necessary"; query
# and fragment are excluded because the grammar has no place for them; and
# whitespace never survives canonicalization.
_FORBIDDEN_CHARACTERS = ("%", "?", "#", " ", "\t", "\n", "\r", "\x00")

# Non-canonical path segments. Kept separate from the character check so a
# traversal attempt is diagnosed as one.
_DOT_SEGMENTS = (".", "..")

# Stable failure codes. The two lookup classes reuse the spellings
# ``mcp_services`` already publishes for the same conditions, so a client sees one
# taxonomy rather than two for "you named something that does not exist". The URI
# and generation classes are this layer's own: they are refused before any service
# call, so no service code exists for them.
URI_INVALID = "resource-uri-invalid"
CATALOG_NOT_FOUND = "catalog-not-found"
STANDARD_NOT_FOUND = "standard-not-found"
RESOURCE_NOT_FOUND = "resource-not-found"
REGISTRATION_INVALID = "resource-registration-invalid"

_URI_REMEDIATION = (
    "address a resource with one of the exact forms "
    f"{SCHEME}{CATALOG_SEGMENT}/{{catalog_major}}, {PACKAGE_TEMPLATE}, or {RESOURCE_TEMPLATE}, "
    "using ids and versions exactly as the installed catalog declares them"
)
_LOOKUP_REMEDIATION = (
    "read the installed catalog resource and use a declared id, exact version, "
    "and declared resource id"
)

# Which declared media types the protocol carries as text. Checked against the
# *declaration* rather than by sniffing bytes, because the declared media type is
# the authority on what a resource is; the UTF-8 decode is only a guard so a
# mislabeled binary still travels losslessly as a blob instead of raising.
_TEXT_MEDIA_PREFIXES = ("text/",)
_TEXT_MEDIA_SUFFIXES = ("json", "xml", "yaml", "toml", "csv", "javascript", "html")


@dataclass(frozen=True, slots=True)
class ResourceAddress:
    """One parsed, canonical ``standards://`` URI.

    ``kind`` selects which fields carry meaning, so a caller cannot mistake a
    catalog address for a package one. Parsing is *positional*, exactly as ADR
    0026's disclosed-divergence paragraph describes: the first token after the
    scheme is the standard id and the second is the exact version. That is what
    makes the two-segment producer form ``standards://{id}/{resource_id}`` land
    its resource id in the version slot and fail as an unknown version rather
    than being silently served as something else.
    """

    kind: Literal["catalog", "package", "resource"]
    catalog_major: str = ""
    standard_id: str = ""
    version: str = ""
    resource_id: str = ""


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    """One concrete registered resource, protocol-neutral.

    Carries no size: computing one would mean reading payload bytes to answer a
    listing, which is exactly the eager whole-distribution read NFR-007 forbids.

    ``declared`` is the §5.5 ``ResourceDescriptor`` projection for a payload
    resource, and ``None`` for the two metadata resources, whose *bodies* already
    are their descriptors. DR-002 requires the exposed resource to include the
    declared resource id, role, media type, digest, standard id, and exact package
    version; the protocol's own ``Resource`` type has named slots for only the URI
    and the media type, so the rest travels as declaration metadata. Read from
    facts cached at registration, never from bytes.
    """

    uri: str
    name: str
    title: str
    description: str
    media_type: str
    declared: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ResourceTemplateEntry:
    """One registered parameterized form. Empty ``media_type`` means "varies"."""

    uri_template: str
    name: str
    title: str
    description: str
    media_type: str = ""


@dataclass(frozen=True, slots=True)
class ResourcePayload:
    """One read result: exact bytes plus how the protocol must carry them.

    ``as_text`` is decided here rather than in the transport so the SDK mapping
    stays a mechanical projection. When it is true the bytes are guaranteed to be
    valid UTF-8, because the decision required decoding them.
    """

    uri: str
    media_type: str
    data: bytes
    as_text: bool
    declared: dict[str, str] | None = None


def _invalid_uri(uri: str, reason: str) -> ServiceError:
    """Build the structured refusal for a non-canonical or unparseable URI.

    The message names the rule that was broken but never echoes more of the input
    than the URI itself, which the client already has.
    """
    return ServiceError(
        code=URI_INVALID,
        message=f"{uri!r} is not a canonical standards:// resource URI: {reason}",
        remediation=_URI_REMEDIATION,
    )


def parse_resource_uri(uri: str) -> ResourceAddress:
    """Parse one canonical ``standards://`` URI, or refuse it.

    The single implementation of ADR 0026's grammar and canonicalization rules
    (T6.5 keeps it that way). Every rule is enforced against the *literal* input:
    the server never normalizes, aliases, re-cases, or percent-decodes on the way
    in, because a URI that had to be repaired to match is by definition not the
    identity the catalog declared, and repairing it is the fuzzy matching the
    record forbids.

    Raises:
        ServiceError: with code ``resource-uri-invalid``. Nothing here consults
            the catalog, so a refusal at this stage cannot depend on installed
            state and never reaches the service layer.
    """
    if not uri.startswith(SCHEME):
        raise _invalid_uri(uri, f"it does not start with {SCHEME!r}")
    if uri != uri.lower():
        raise _invalid_uri(uri, "it carries uppercase characters")
    for character in _FORBIDDEN_CHARACTERS:
        if character in uri:
            raise _invalid_uri(uri, f"it carries the forbidden character {character!r}")

    remainder = uri[len(SCHEME) :]
    if remainder.endswith("/"):
        raise _invalid_uri(uri, "it carries a trailing slash")
    segments = remainder.split("/")
    if not all(segments):
        raise _invalid_uri(uri, "it carries an empty path segment")
    for segment in segments:
        if segment in _DOT_SEGMENTS:
            raise _invalid_uri(uri, f"it carries the non-canonical segment {segment!r}")

    if len(segments) == 2:
        if segments[0] == CATALOG_SEGMENT:
            return ResourceAddress(kind="catalog", catalog_major=segments[1])
        return ResourceAddress(kind="package", standard_id=segments[0], version=segments[1])
    if len(segments) == 4 and segments[2] == RESOURCES_SEGMENT:
        return ResourceAddress(
            kind="resource",
            standard_id=segments[0],
            version=segments[1],
            resource_id=segments[3],
        )
    raise _invalid_uri(
        uri,
        f"it has {len(segments)} path segments; only the two-segment package form and the "
        f"four-segment {RESOURCES_SEGMENT!r} form exist",
    )


def catalog_uri(catalog_major: str) -> str:
    return f"{SCHEME}{CATALOG_SEGMENT}/{catalog_major}"


def package_uri(standard_id: str, version: str) -> str:
    return PACKAGE_TEMPLATE.format(standard_id=standard_id, version=version)


def resource_uri(standard_id: str, version: str, resource_id: str) -> str:
    return RESOURCE_TEMPLATE.format(
        standard_id=standard_id, version=version, resource_id=resource_id
    )


#: The FR-001 field mask for the catalog resource, applied to
#: :class:`~project_standards.mcp_services.CatalogDescriptor` through pydantic's
#: nested ``include``.
#:
#: FR-001's acceptance criterion names exactly what the discovery resource owes:
#: "every installed family with ID, title, status, package version, exposure,
#: capabilities, relations, and version-qualified resource URIs". The full DTO
#: also carries every resource digest, role, and media type plus every provider
#: declaration, which measured 373,619 bytes against the real installed Catalog 5
#: — a discovery point that costs a third of a megabyte cannot satisfy the plan's
#: "compact metadata" or NFR-002 (T6.4 Codex GREEN review, F1).
#:
#: This is a *mask*, not a schema: every value still comes from the DTO's own
#: ``model_dump``, so a field-type or value change follows automatically and no
#: parallel serializer exists. Only the choice of which declared fields the
#: discovery resource carries lives here, and that choice is FR-001's sentence.
#: Package resources are unaffected — they serve the complete exact
#: ``StandardDescriptor``, which is where a client goes for digests and providers.
CATALOG_FIELD_MASK: dict[str, Any] = {
    "catalog_major": True,
    "standards": {
        "__all__": {
            "standard_id": True,
            "title": True,
            "status": True,
            "package_version": True,
            "exposure": True,
            "capabilities": True,
            "relationships": True,
            "resources": {"__all__": {"uri": True}},
        }
    },
}


def _metadata_payload(uri: str, projection: dict[str, object]) -> ResourcePayload:
    """Serialize one DTO projection as the body of a metadata resource.

    ``model_dump(mode="json")`` is the whole contract: the metadata resources
    publish the ``mcp_services`` DTOs and invent no second schema, so a field
    added to a DTO appears here without a code change and none can be quietly
    dropped. Key order follows the DTO's field order, which is stable across
    processes — a served frame has to be byte-identical between runs to satisfy
    NFR-005.
    """
    return ResourcePayload(
        uri=uri,
        media_type=METADATA_MEDIA_TYPE,
        data=json.dumps(projection, ensure_ascii=False).encode("utf-8"),
        as_text=True,
    )


def _declaration(descriptor: ResourceDescriptor) -> dict[str, str]:
    """The declared resource descriptor, projected for declaration metadata.

    Taken from the DTO rather than assembled field by field, so DR-002's field
    list cannot drift out of this projection: a field added to
    ``ResourceDescriptor`` is exposed automatically.
    """
    return {key: str(value) for key, value in descriptor.model_dump(mode="json").items()}


def _carries_text(media_type: str) -> bool:
    return media_type.startswith(_TEXT_MEDIA_PREFIXES) or media_type.endswith(_TEXT_MEDIA_SUFFIXES)


class ResourceRegistry:
    """The fixed resource registration set of one server process.

    Built once from a validated facade and immutable thereafter, which is what
    makes ADR 0026's static-registry claim (and therefore ``listChanged: false``)
    true rather than aspirational. It owns two responsibilities and no others:
    deciding what is addressable, and refusing everything else before the service
    layer is asked.
    """

    def __init__(
        self,
        *,
        facade: McpServiceFacade,
        catalog_major: str,
        catalog: CatalogDescriptor,
        entries: tuple[ResourceEntry, ...],
        packages: dict[tuple[str, str], StandardDescriptor],
        resources: dict[tuple[str, str, str], ResourceDescriptor],
    ) -> None:
        self._facade = facade
        self._catalog_major = catalog_major
        self._catalog = catalog
        self._entries = entries
        self._packages = packages
        self._resources = resources

    @classmethod
    def build(
        cls, facade: McpServiceFacade, *, catalog_major: str = CATALOG_MAJOR
    ) -> ResourceRegistry:
        """Derive the registration set from one already validated catalog.

        Called during server construction, after the facade has eagerly verified
        the complete installed distribution, so any failure here is a
        server-start failure and never a partially registered server. The
        canonicality self-check is the reason this can fail at all: a declared
        identifier that does not round-trip through ``parse_resource_uri`` would
        produce a URI the server advertises but would itself refuse, and shipping
        that is worse than refusing to start.
        """
        catalog = facade.catalog()
        if str(catalog.catalog_major) != catalog_major:
            raise ServiceError(
                code=REGISTRATION_INVALID,
                message=(
                    f"the facade serves catalog {catalog.catalog_major}, but the adapter "
                    f"advertises generation {catalog_major}"
                ),
                remediation="build the facade for the catalog generation the adapter exposes",
            )

        generation = catalog_uri(catalog_major)
        entries: list[ResourceEntry] = [
            ResourceEntry(
                uri=generation,
                name=f"standards-catalog-{catalog_major}",
                title=f"Installed Catalog {catalog_major}",
                description=(
                    f"Compact metadata for every standard package installed in Catalog "
                    f"{catalog_major}: ids, titles, statuses, exact versions, exposure, "
                    "capabilities, relationships, and version-qualified resource URIs."
                ),
                media_type=METADATA_MEDIA_TYPE,
            )
        ]
        packages: dict[tuple[str, str], StandardDescriptor] = {}
        resources: dict[tuple[str, str, str], ResourceDescriptor] = {}

        # Listing order follows the catalog's own declared order (DR-009's stable
        # ordering), so the served listing is a function of the installed catalog
        # and of nothing else - not of dict or directory iteration.
        #
        # Payload resources are addressable but deliberately *not* listed. They
        # are reached through the resource template and are already enumerated,
        # with their version-qualified URIs, inside the catalog resource that
        # FR-001 requires. Listing them as well is pure duplication, and it is not
        # free: measured against the real installed Catalog 5 (52 package
        # versions, 917 declared resources) the enumerated listing is 587 KB of
        # wire, against 12 KB for the catalog plus package entries alone. A
        # 587 KB reply to the cheapest discovery call is exactly what NFR-002 and
        # NFR-012 exist to prevent.
        for descriptor in catalog.standards:
            key = (descriptor.standard_id, descriptor.package_version)
            packages[key] = descriptor
            entries.append(
                ResourceEntry(
                    uri=package_uri(*key),
                    name=f"{descriptor.standard_id}@{descriptor.package_version}",
                    title=f"{descriptor.title} {descriptor.package_version}",
                    description=(
                        f"Exact metadata for {descriptor.standard_id} "
                        f"{descriptor.package_version} ({descriptor.status}, "
                        f"{descriptor.exposure})."
                    ),
                    media_type=METADATA_MEDIA_TYPE,
                )
            )
            for declared in descriptor.resources:
                resources[(*key, declared.resource_id)] = declared

        registry = cls(
            facade=facade,
            catalog_major=catalog_major,
            catalog=catalog,
            entries=tuple(entries),
            packages=packages,
            resources=resources,
        )
        registry._verify_registration()
        return registry

    def _verify_registration(self) -> None:
        """Refuse to start if any addressable URI is not one this server accepts.

        Every *addressable* identity is checked, not only the listed ones: a
        declared resource whose URI does not round-trip through
        ``parse_resource_uri`` would be advertised inside the catalog resource and
        then refused on read, which is a worse failure than not starting. Listed
        entries additionally have to be unique, because a duplicate registration
        is a client-visible defect in its own right.

        The payload URIs are also checked against this module's own template. That
        is not redundant: the *service* layer composes
        ``ResourceDescriptor.uri``, so the four-segment form has two producers, and
        ADR 0026's disclosed divergence is precisely what happens when producers of
        this grammar drift apart. Comparing them here collapses the pair into one
        checked producer — a disagreement aborts the launch instead of shipping a
        URI the adapter advertises and then refuses to read.
        """
        listed = [entry.uri for entry in self._entries]
        duplicates = sorted({uri for uri in listed if listed.count(uri) > 1})
        if duplicates:
            raise ServiceError(
                code=REGISTRATION_INVALID,
                message=f"these URIs are listed more than once: {duplicates}",
                remediation="repair the installed catalog projection and restart",
            )
        for (standard_id, version, declared_id), declared in self._resources.items():
            expected = resource_uri(standard_id, version, declared_id)
            if declared.uri != expected:
                raise ServiceError(
                    code=REGISTRATION_INVALID,
                    message=(
                        f"the service layer addresses {standard_id} {version} "
                        f"{declared_id!r} as {declared.uri}, but the frozen template "
                        f"produces {expected}"
                    ),
                    remediation=(
                        "align the package-resource URI producers on the four-segment "
                        "ADR 0026 form and restart"
                    ),
                )
        addressable = (*listed, *(declared.uri for declared in self._resources.values()))
        for uri in addressable:
            try:
                address = parse_resource_uri(uri)
            except ServiceError as error:
                raise ServiceError(
                    code=REGISTRATION_INVALID,
                    message=f"the registered URI {uri} is not canonical: {error.message}",
                    remediation="repair the installed catalog projection and restart",
                ) from error
            if self._resolve(address) is None:
                raise ServiceError(
                    code=REGISTRATION_INVALID,
                    message=f"the registered URI {uri} does not resolve to a declaration",
                    remediation="repair the installed catalog projection and restart",
                )

    def _resolve(self, address: ResourceAddress) -> ResourceAddress | None:
        """The address itself when it names something declared, otherwise ``None``."""
        if address.kind == "catalog":
            return address if address.catalog_major == self._catalog_major else None
        key = (address.standard_id, address.version)
        if key not in self._packages:
            return None
        if address.kind == "package":
            return address
        return address if (*key, address.resource_id) in self._resources else None

    def listings(self) -> tuple[ResourceEntry, ...]:
        """Every concrete registered resource, in deterministic order."""
        return self._entries

    def templates(self) -> tuple[ResourceTemplateEntry, ...]:
        """The two parameterized forms, and no others.

        The catalog form is absent on purpose: its only parameter is fixed by
        ``models.CATALOG_MAJOR``, so it is a concrete resource and appears in
        ``listings`` instead.
        """
        return (
            ResourceTemplateEntry(
                uri_template=PACKAGE_TEMPLATE,
                name="standard-package-version",
                title="Standard package version metadata",
                description=(
                    "Exact metadata for one installed standard package version: identity, "
                    "status, exposure, capabilities, declared relationships, declared "
                    "resources, and declared providers."
                ),
                media_type=METADATA_MEDIA_TYPE,
            ),
            ResourceTemplateEntry(
                uri_template=RESOURCE_TEMPLATE,
                name="standard-package-resource",
                title="Declared package resource",
                description=(
                    "The bytes of one declared resource inside an exact standard package "
                    "version, verified against its declaration and digest on every read."
                ),
            ),
        )

    def read(self, uri: str) -> ResourcePayload:
        """Return one addressed resource, or refuse before any service lookup.

        The order of the three steps is the contract: parse, resolve against the
        registration index, and only then call the facade. Nothing but a fully
        canonical URI naming a fully declared resource ever reaches
        ``McpServiceFacade.resource``, and that call is what rechecks the
        declaration, the contained path, and the current byte digest — so bytes
        that drifted after startup fail their own read.
        """
        address = parse_resource_uri(uri)
        if address.kind == "catalog":
            if address.catalog_major != self._catalog_major:
                raise ServiceError(
                    code=CATALOG_NOT_FOUND,
                    message=(
                        f"this server exposes catalog generation {self._catalog_major}, "
                        f"not {address.catalog_major!r}"
                    ),
                    remediation=f"read {catalog_uri(self._catalog_major)}",
                )
            # Masked to FR-001's field list; digests, roles, media types, and
            # provider declarations live on the package resource, one read away.
            return _metadata_payload(
                uri, self._catalog.model_dump(mode="json", include=CATALOG_FIELD_MASK)
            )

        key = (address.standard_id, address.version)
        descriptor = self._packages.get(key)
        if descriptor is None:
            raise ServiceError(
                code=STANDARD_NOT_FOUND,
                message=(
                    f"the installed catalog declares no {address.standard_id!r} at exact "
                    f"version {address.version!r}"
                ),
                remediation=_LOOKUP_REMEDIATION,
                standard_id=address.standard_id,
                version=address.version,
            )
        if address.kind == "package":
            return _metadata_payload(uri, descriptor.model_dump(mode="json"))

        declared = self._resources.get((*key, address.resource_id))
        if declared is None:
            raise ServiceError(
                code=RESOURCE_NOT_FOUND,
                message=(
                    f"{address.standard_id} {address.version} declares no resource "
                    f"{address.resource_id!r}"
                ),
                remediation=_LOOKUP_REMEDIATION,
                standard_id=address.standard_id,
                version=address.version,
            )
        content = self._facade.resource(address.standard_id, address.version, declared.resource_id)
        media_type = content.descriptor.media_type
        as_text = _carries_text(media_type)
        if as_text:
            try:
                content.data.decode("utf-8")
            except UnicodeDecodeError:
                # A declaration claiming a text media type for bytes that are not
                # text is still served exactly, as a blob, rather than raising or
                # replacing characters: FR-003 promises the declared bytes.
                as_text = False
        return ResourcePayload(
            uri=uri,
            media_type=media_type,
            data=content.data,
            as_text=as_text,
            # The descriptor the *read* verified, not the one cached at
            # registration: they are equal for an intact distribution, and using
            # the verified one means the published metadata can never describe
            # bytes this read did not actually check.
            declared=_declaration(content.descriptor),
        )


def build_resource_registry(facade: McpServiceFacade) -> ResourceRegistry:
    """Build the process's resource registration set from a validated facade."""
    return ResourceRegistry.build(facade)
