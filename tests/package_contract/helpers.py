from __future__ import annotations

import hashlib
import json
import re
import shutil
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    ContributionDeclaration,
    JsonObject,
    PayloadManifest,
    load_payload_manifest,
)

_MINIMAL = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"

# Renders one contribution scope to its TOML fragment. Each test module owns its
# own provider invocation (payload root, standard id, snapshot shape), so the
# shared Ruff helpers below take the renderer rather than rebuilding it.
ScopeRenderer = Callable[[str], str]


def copy_minimal_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    shutil.copytree(_MINIMAL, repository)
    return repository


def clone_demo_family(repository: Path, standard_id: str) -> Path:
    source = repository / "standards/demo"
    destination = repository / f"standards/{standard_id}"
    shutil.copytree(source, destination)
    family_path = destination / "standard.toml"
    family_path.write_text(
        family_path.read_text(encoding="utf-8").replace('id = "demo"', f'id = "{standard_id}"'),
        encoding="utf-8",
    )
    payload_path = destination / "versions/1.2/payload.toml"
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8").replace(
            'standard = "demo"', f'standard = "{standard_id}"'
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    aggregate = validate_payload_integrity(payload_path.parent, manifest).aggregate_digest.value
    family_path.write_text(
        re.sub(
            r'digest = "sha256:[0-9a-f]{64}"',
            f'digest = "{aggregate}"',
            family_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    return destination


def refresh_declared_file_digest(family: Path, relative_path: str) -> None:
    payload_path = family / "versions/1.2/payload.toml"
    target_digest = hashlib.sha256((payload_path.parent / relative_path).read_bytes()).hexdigest()
    payload_text = payload_path.read_text(encoding="utf-8")
    pattern = rf'(path = "{re.escape(relative_path)}"\nmedia_type = "[^"]+"\ndigest = ")sha256:[0-9a-f]{{64}}(")'
    payload_path.write_text(
        re.sub(pattern, rf"\g<1>sha256:{target_digest}\2", payload_text),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    aggregate = validate_payload_integrity(payload_path.parent, manifest).aggregate_digest.value
    family_path = family / "standard.toml"
    family_path.write_text(
        re.sub(
            r'digest = "sha256:[0-9a-f]{64}"',
            f'digest = "{aggregate}"',
            family_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )


def selects_ruff(scope: str) -> bool:
    """Report whether a contribution scope addresses `[tool.ruff]` or a leaf inside it."""
    pointer = scope.split(":", 1)[1]
    return pointer == "/tool/ruff" or pointer.startswith("/tool/ruff/")


def ruff_declarations(
    manifest: PayloadManifest, config: JsonObject
) -> list[ContributionDeclaration]:
    """Select the Ruff contributions a payload materializes under `config`.

    Version-agnostic by construction: through python-tooling 1.11 this returns the
    single whole-table declaration, and from 1.12 on the eleven leaf units the
    monolith was decomposed into (issue #99). Callers that need the resolved table
    must go through `ruff_value` rather than naming `table:/tool/ruff`, which no
    longer exists.
    """
    return [
        declaration
        for declaration in manifest.contributions
        if declaration.target.original == "pyproject.toml"
        and declaration.adapter is AdapterKind.TOML
        and selects_ruff(declaration.scope)
        and declaration.materializes(config)
    ]


def compose_toml(fragments: Sequence[str]) -> str:
    """Fold rendered fragments into one document, merging repeated table headers.

    Each key-scope fragment carries its own `[tool.ruff]` header, so plain
    concatenation would redefine the table and fail the parser. Grouping by
    header is also what makes the two payloads comparable at all: the 1.11
    monolith and the 1.12 unit set reduce to the same document shape.
    """
    grouped: dict[str, list[str]] = {}
    for fragment in fragments:
        header = ""
        for line in fragment.splitlines():
            if not line.strip():
                continue
            if line.startswith("["):
                header = line
                grouped.setdefault(header, [])
                continue
            grouped.setdefault(header, []).append(line)
    sections: list[str] = []
    for header, lines in grouped.items():
        body = "".join(f"{line}\n" for line in lines)
        sections.append(f"{header}\n{body}\n" if header else body)
    return "".join(sections)


def ruff_source(render: ScopeRenderer, manifest: PayloadManifest, config: JsonObject) -> str:
    """Render every materialized Ruff contribution into one composed TOML document."""
    return compose_toml(
        [render(declaration.scope) for declaration in ruff_declarations(manifest, config)]
    )


def _walk_property_scopes(
    node: object, pointer: str, found: list[tuple[str, dict[str, object]]]
) -> None:
    """Collect every `properties` map in a schema document, with its JSON pointer.

    A payload reference is a JSON Schema subschema, so it can sit at any depth: the
    render envelopes pin identity at the document root, the migration report pins it
    inside a nested `package` object, and the configuration-transform input pins
    migration edges inside `$defs` and again inside each `oneOf` branch. Keying on
    the enclosing `properties` map rather than on fixed paths is what makes those
    shapes one rule.
    """
    if isinstance(node, list):
        for index, item in enumerate(cast("list[object]", node)):
            _walk_property_scopes(item, f"{pointer}/{index}", found)
        return
    if not isinstance(node, dict):
        return
    mapping = cast("dict[str, object]", node)
    properties = mapping.get("properties")
    if isinstance(properties, dict):
        found.append((f"{pointer}/properties", cast("dict[str, object]", properties)))
    for key, value in mapping.items():
        _walk_property_scopes(value, f"{pointer}/{key}", found)


def _literal_values(node: object) -> list[str]:
    """Return every string literal a subschema admits, across `const`, `enum`, and branches.

    A payload reference is pinned three different ways in the shipped schemas — a bare
    `const`, a closed `enum`, and an `anyOf` branch set (the migration report's selector)
    — and a guard that reads only one of them is a guard that misses the other two.
    Nested `properties` are deliberately not followed: those literals belong to a
    different property and the caller's own walk visits them under their own key.
    Non-string literals (`declared_pointers` pins a list) are not payload references
    and are dropped rather than compared.
    """
    if not isinstance(node, dict):
        return []
    mapping = cast("dict[str, object]", node)
    values: list[object] = []
    if "const" in mapping:
        values.append(mapping["const"])
    enum = mapping.get("enum")
    if isinstance(enum, list):
        values.extend(cast("list[object]", enum))
    for keyword in ("anyOf", "oneOf", "allOf"):
        branches = mapping.get(keyword)
        if isinstance(branches, list):
            for branch in cast("list[object]", branches):
                values.extend(_literal_values(branch))
    return [value for value in values if isinstance(value, str)]


def _endpoint_reference(value: str) -> bool:
    """Report whether a literal names a migration endpoint rather than ordinary content.

    `source` and `target` are overloaded across the payload's schemas: in the mutation
    plan `target` is a repository path, and only the `package:`/`legacy:` grammar marks
    a literal as an edge of the migration graph. Filtering here keeps the endpoint rule
    from firing on schemas that merely reuse the property name.
    """
    return value.startswith(("package:", "legacy:"))


def assert_schema_payload_references(payload_root: Path, manifest: PayloadManifest) -> list[str]:
    """Assert every payload reference a declared JSON schema pins matches this payload.

    A successor is cut by copying the predecessor's payload forward, so any literal the
    copy carries over is unreachable rather than merely mislabelled: `_validate_json_schema`
    fails closed the first time the payload is selected. Three release-prep failures came
    from exactly that, each on a different literal — a stale `version` const in a provider
    input schema, a stale `version` const nested in a migration report, and a stale
    `migration_id`/`source` enum pair in a configuration-transform input. A guard scoped to
    one literal kind is therefore too narrow by construction; this one sweeps every
    identity, migration id, endpoint, and selector literal in every JSON resource the
    manifest declares, so a schema added to a later cut is covered without anyone
    remembering to extend it.

    Every expectation is derived from the manifest, never from the schema being checked:

    - `standard_id`/`version` consts must name this payload.
    - Every `migration_id` literal must be a migration the manifest declares.
    - Every `package:`/`legacy:` `source` or `target` literal must be an endpoint some
      declared migration actually references.
    - Every `selector` literal must be `latest` or this payload's own version.
    - Where a subschema also pins `provider_id`, its `migration_id`, `source`, and
      `target` literals must be *exactly* the declared migrations for that provider —
      the completeness half, which membership alone cannot catch when a successor drops
      or gains an edge.

    Returns the locations checked so a caller can assert the guard had a corpus.
    """
    declared_ids = {migration.id for migration in manifest.migrations}
    declared_endpoints = {
        endpoint.value
        for migration in manifest.migrations
        for endpoint in (migration.from_endpoint, migration.to_endpoint)
    }
    own_selectors = {"latest", manifest.payload.version.value}
    checked: list[str] = []
    for resource in manifest.resources:
        relative = resource.path.normalized.as_posix()
        if not relative.endswith(".json"):
            continue
        document = cast(
            "object",
            json.loads((payload_root / relative).read_text(encoding="utf-8")),
        )
        scopes: list[tuple[str, dict[str, object]]] = []
        _walk_property_scopes(document, "", scopes)
        for pointer, properties in scopes:
            location = f"{relative}#{pointer}"
            checked.extend(_check_identity_pin(location, properties, manifest))
            checked.extend(
                _check_migration_references(
                    location,
                    properties,
                    declared_ids=declared_ids,
                    declared_endpoints=declared_endpoints,
                    own_selectors=own_selectors,
                )
            )
            checked.extend(_check_provider_closure(location, properties, manifest))
    return checked


def _check_identity_pin(
    location: str, properties: dict[str, object], manifest: PayloadManifest
) -> list[str]:
    """Assert a scope that pins `standard_id` also pins this payload's own version.

    `schema_version` is a different axis — the envelope's own format version — and is
    never a sibling of a `standard_id` const, so it is exempt by construction rather
    than by exclusion.
    """
    standard_id = properties.get("standard_id")
    if not isinstance(standard_id, dict) or "const" not in cast("dict[str, object]", standard_id):
        return []
    assert cast("dict[str, object]", standard_id)["const"] == manifest.payload.standard, location
    version = properties.get("version")
    assert isinstance(version, dict), f"{location} pins standard_id without a version"
    assert cast("dict[str, object]", version).get("const") == manifest.payload.version.value, (
        location
    )
    return [location]


def _check_migration_references(
    location: str,
    properties: dict[str, object],
    *,
    declared_ids: set[str],
    declared_endpoints: set[str],
    own_selectors: set[str],
) -> list[str]:
    """Assert every migration id, endpoint, and selector literal in one scope is reachable."""
    checked: list[str] = []
    ids = _literal_values(properties.get("migration_id"))
    if ids:
        unknown = sorted(set(ids) - declared_ids)
        assert not unknown, f"{location}/migration_id names undeclared migrations {unknown}"
        checked.append(f"{location}/migration_id")
    for key in ("source", "target"):
        endpoints = [
            value for value in _literal_values(properties.get(key)) if _endpoint_reference(value)
        ]
        if not endpoints:
            continue
        unknown = sorted(set(endpoints) - declared_endpoints)
        assert not unknown, f"{location}/{key} names unreferenced endpoints {unknown}"
        checked.append(f"{location}/{key}")
    selectors = _literal_values(properties.get("selector"))
    if selectors:
        unknown = sorted(set(selectors) - own_selectors)
        assert not unknown, f"{location}/selector names foreign selectors {unknown}"
        checked.append(f"{location}/selector")
    return checked


def _check_provider_closure(
    location: str, properties: dict[str, object], manifest: PayloadManifest
) -> list[str]:
    """Assert a provider-pinned scope enumerates exactly that provider's declared edges.

    Membership alone accepts a schema that silently omits a declared migration, which is
    the same unreachable-payload failure seen from the other side. The `provider_id` const
    is what makes the expected set derivable: the configuration-transform input pins
    `migrate-config`, so its enums must be that provider's migrations and no others —
    the legacy edge belongs to a different provider and is correctly absent.
    """
    provider = properties.get("provider_id")
    if not isinstance(provider, dict):
        return []
    provider_id = cast("dict[str, object]", provider).get("const")
    if not isinstance(provider_id, str):
        return []
    edges = [migration for migration in manifest.migrations if migration.provider == provider_id]
    if not edges:
        return []
    expected: dict[str, set[str]] = {
        "migration_id": {migration.id for migration in edges},
        "source": {migration.from_endpoint.value for migration in edges},
        "target": {migration.to_endpoint.value for migration in edges},
    }
    checked: list[str] = []
    for key, wanted in expected.items():
        if key not in properties:
            continue
        actual = set(_literal_values(properties[key]))
        assert actual == wanted, (
            f"{location}/{key} does not enumerate provider {provider_id!r}: "
            f"missing {sorted(wanted - actual)}, unexpected {sorted(actual - wanted)}"
        )
        checked.append(f"{location}/{key}@{provider_id}")
    return checked


def ruff_value(render: ScopeRenderer, manifest: PayloadManifest, config: JsonObject) -> JsonObject:
    """Return the resolved `[tool.ruff]` table the payload contributes under `config`."""
    document = tomllib.loads(ruff_source(render, manifest, config))
    return cast("JsonObject", cast("JsonObject", document["tool"])["ruff"])
