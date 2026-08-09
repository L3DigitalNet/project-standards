#!/usr/bin/env python3
"""Report which hand-maintained declaration sites already mention a family id.

Adopting a family into this repository means editing nine hand-maintained
collections beyond the family's own payload tree. Each is enforced by its own
fail-closed gate, and historically each was discovered only by running the
previous layer's gate and reading the failure -- eight serial worker dispatches
for one family, the dominant time sink measured in the issue #133 findings (R1,
`docs/research/2026-08-07-plan-execution-efficiency.md`).

This check predicts those gates so the edits can be authored in one pass. It
never replaces them. Every site keeps its independent enforcement, and a
`declared` verdict means only that the family id appears in the right place --
never that the value there is correct. A green preflight is a checklist, not a
proof, and it is deliberately reported as such.

Stdlib-only and free of any `project_standards` import on purpose: the tool has
to run in a bare checkout at task-claim time, before an environment or a
candidate wheel exists. It reads TOML through `tomllib` and Python through
`ast` rather than importing either, so no site can execute code to satisfy it.

Exit codes: 0 every applicable site declared, 1 at least one site missing,
2 usage error or a stale site inventory.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tomllib
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Named once because they are read twice: as probed sites below, and as fact
# sources in `collect_facts`.
_CATALOG_PATH = "catalogs/5.toml"
_CENSUS_PATH = "tests/mcp_services/test_providers.py"
_CENSUS_BINDING = "AUTHORITATIVE_INPUT_OWNER"


class PreflightError(Exception):
    """A usage error, or a site inventory that no longer matches the tree."""


class Status(StrEnum):
    """The three verdicts a site can carry for one family."""

    DECLARED = "declared"
    MISSING = "missing"
    NOT_APPLICABLE = "not applicable"


class Match(StrEnum):
    """How a probe recognises the family id inside a string constant.

    EXACT finds a collection keyed by the bare id. PATH_SEGMENT finds a
    delivered-artifact path such as `.agents/skills/<id>/bin/<id>`. The two are
    disjoint in practice, which is what lets one module carry two independent
    probes -- a dispatch branch and an artifact list -- without either
    verdict standing in for the other.
    """

    EXACT = "exact"
    PATH_SEGMENT = "path-segment"


# --------------------------------------------------------------------------
# Family facts
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyFacts:
    """What the family's own payload says, used to decide site applicability.

    Every field is derived from `standards/<id>/`, never hand-declared here, so
    a family that gains a seam provider or an executable becomes subject to the
    matching sites without an edit to this file.
    """

    family_id: str
    version: str
    consumer_selectable: bool
    is_catalog_default: bool
    has_findings_provider: bool
    has_markdown_block: bool
    has_executables: bool
    has_legacy_bundle: bool
    has_required_option_without_default: bool
    # Authorities recorded for this family in the provider-input census, empty
    # when the census has no row for it yet. See `_seam` for why this, and not
    # anything in the payload, decides whether the seam sites apply.
    census_authorities: frozenset[str]


def _load_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PreflightError(f"expected file is absent: {_display(path)}")
    with path.open("rb") as handle:
        return cast("dict[str, object]", tomllib.load(handle))


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def _tables(document: dict[str, object], key: str) -> list[dict[str, object]]:
    """Return an array-of-tables, tolerating its absence."""
    raw = document.get(key)
    if not isinstance(raw, list):
        return []
    return [
        cast("dict[str, object]", item)
        for item in cast("list[object]", raw)
        if isinstance(item, dict)
    ]


def _version_sort_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError as exc:
        raise PreflightError(f"unparsable version in the family index: {version}") from exc


def _latest_version(index: dict[str, object]) -> str:
    versions: list[str] = []
    for entry in _tables(index, "versions"):
        value = entry.get("version")
        if isinstance(value, str):
            versions.append(value)
    if not versions:
        raise PreflightError("the family index declares no versions")
    return max(versions, key=_version_sort_key)


def _config_schema_path(payload_dir: Path, payload: dict[str, object]) -> Path | None:
    """Resolve `[config].schema_resource` to a file through `[[resources]]`."""
    config = payload.get("config")
    if not isinstance(config, dict):
        return None
    resource_id: object = cast("dict[str, object]", config).get("schema_resource")
    if not isinstance(resource_id, str):
        return None
    for resource in _tables(payload, "resources"):
        path: object = resource.get("path")
        if resource.get("id") == resource_id and isinstance(path, str):
            return payload_dir / path
    return None


def _requires_option_without_default(schema_path: Path | None) -> bool:
    """True when the config schema requires an option that has no default.

    This is precisely the condition that forces a row into the compatibility
    matrix's `_MINIMAL_PACKAGE_CONFIG`: planning rejects such a package under
    the empty configuration every other default resolves under.
    """
    if schema_path is None or not schema_path.is_file():
        return False
    try:
        schema: object = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"unreadable config schema: {_display(schema_path)}: {exc}") from exc
    if not isinstance(schema, dict):
        return False
    document = cast("dict[str, object]", schema)
    required: object = document.get("required")
    properties: object = document.get("properties")
    if not isinstance(required, list) or not isinstance(properties, dict):
        return False
    known = cast("dict[str, object]", properties)
    for name in cast("list[object]", required):
        definition = known.get(name) if isinstance(name, str) else None
        if not isinstance(definition, dict) or "default" not in cast(
            "dict[str, object]", definition
        ):
            return True
    return False


def _catalog_roles(root: Path, family_id: str) -> set[str]:
    """Return every `role` the catalog advertises for this family."""
    document = _load_toml(root / _CATALOG_PATH)
    roles: set[str] = set()
    for entry in _tables(document, "packages"):
        role: object = entry.get("role")
        if entry.get("id") == family_id and isinstance(role, str):
            roles.add(role)
    return roles


def _census_authorities(root: Path, family_id: str) -> frozenset[str]:
    """Read the provider-input authorities recorded for one family.

    The census is site 6, and it is the only place in the repository that
    states whether a family's operations are served by the seam (`family`) or
    by the executor/planner. Nothing in `payload.toml` distinguishes the two:
    `python-tooling` declares the same provider shape as `adr` and is
    deliberately not a seam family. So the seam sites read their applicability
    from here rather than guessing from the payload.
    """
    path = root / _CENSUS_PATH
    if not path.is_file():
        raise PreflightError(f"expected file is absent: {_CENSUS_PATH}")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    node = _scope_node(tree, _CENSUS_BINDING)
    if node is None:
        raise PreflightError(
            f"stale site inventory: {_CENSUS_PATH} no longer defines {_CENSUS_BINDING!r}."
        )
    authorities: set[str] = set()
    for mapping in (child for child in ast.walk(node) if isinstance(child, ast.Dict)):
        for key, value in zip(mapping.keys, mapping.values, strict=True):
            if not isinstance(key, ast.Tuple) or not isinstance(value, ast.Constant):
                continue
            owners = [
                element.value
                for element in key.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if owners and owners[0] == family_id and isinstance(value.value, str):
                authorities.add(value.value)
    return frozenset(authorities)


def collect_facts(root: Path, family_id: str) -> FamilyFacts:
    """Derive the applicability facts for one family from its own payload."""
    family_dir = root / "standards" / family_id
    index_path = family_dir / "standard.toml"
    if not index_path.is_file():
        raise PreflightError(
            f"unknown family: {family_id} (no {_display(index_path)}). "
            "Author the family's own payload tree before running this preflight."
        )
    index = _load_toml(index_path)
    version = _latest_version(index)
    payload_dir = family_dir / "versions" / version
    payload = _load_toml(payload_dir / "payload.toml")

    payload_table = payload.get("payload")
    availability = ""
    if isinstance(payload_table, dict):
        declared: object = cast("dict[str, object]", payload_table).get("availability")
        if isinstance(declared, str):
            availability = declared

    providers = _tables(payload, "providers")
    contributions = _tables(payload, "contributions")

    return FamilyFacts(
        family_id=family_id,
        version=version,
        consumer_selectable=availability == "consumer",
        is_catalog_default="default" in _catalog_roles(root, family_id),
        # A `documentation-only` provider is advisory prose, never dispatched,
        # so it does not put the family into the provider-input census.
        has_findings_provider=any(
            entry.get("effect") == "findings" and entry.get("kind") != "documentation-only"
            for entry in providers
        ),
        census_authorities=_census_authorities(root, family_id),
        has_markdown_block=any(entry.get("adapter") == "markdown-block" for entry in contributions),
        has_executables=any(
            item.is_file() and item.stat().st_mode & 0o100 for item in payload_dir.rglob("*")
        ),
        has_legacy_bundle=(root / "src/project_standards/bundles" / family_id).is_dir(),
        has_required_option_without_default=_requires_option_without_default(
            _config_schema_path(payload_dir, payload)
        ),
    )


# --------------------------------------------------------------------------
# Probes
# --------------------------------------------------------------------------


class Probe(Protocol):
    """One question asked of one file.

    The members are declared read-only because every implementation is a frozen
    dataclass; a plain attribute here would demand a writable field and reject
    all of them.
    """

    @property
    def path(self) -> str: ...

    @property
    def role(self) -> str: ...

    @property
    def applies(self) -> Callable[[FamilyFacts], bool]: ...

    def declared(self, root: Path, family_id: str) -> bool: ...


def _matches(value: str, family_id: str, mode: Match) -> bool:
    if mode is Match.EXACT:
        return value == family_id
    return family_id in value.split("/")


@dataclass(frozen=True)
class TomlArrayProbe:
    """Look for an array-of-tables entry whose `key` is the family id."""

    path: str
    role: str
    array: str
    key: str
    applies: Callable[[FamilyFacts], bool]

    def declared(self, root: Path, family_id: str) -> bool:
        document = _load_toml(root / self.path)
        return any(entry.get(self.key) == family_id for entry in _tables(document, self.array))


@dataclass(frozen=True)
class TomlTableProbe:
    """Look for a table at `<prefix>.<family id>`."""

    path: str
    role: str
    prefix: str
    applies: Callable[[FamilyFacts], bool]

    def declared(self, root: Path, family_id: str) -> bool:
        document = _load_toml(root / self.path)
        section = document.get(self.prefix)
        return isinstance(section, dict) and family_id in section


@dataclass(frozen=True)
class PythonProbe:
    """Look for the family id as a string constant in a Python module.

    `scope` names a module-level binding, function, or class to search inside.
    `None` searches the whole module, which is the correct scope for a site
    whose declaration is a NEW binding named after the family itself -- there
    the binding name cannot be known in advance.

    A `scope` that no longer resolves is a stale inventory, not a missing
    declaration, and is raised rather than reported: a silently renamed binding
    would turn this check into false comfort for every future family.
    """

    path: str
    role: str
    scope: str | None
    match: Match
    applies: Callable[[FamilyFacts], bool]

    def declared(self, root: Path, family_id: str) -> bool:
        source_path = root / self.path
        if not source_path.is_file():
            raise PreflightError(f"expected file is absent: {self.path}")
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        except SyntaxError as exc:
            raise PreflightError(f"unparsable module: {self.path}: {exc}") from exc
        node: ast.AST = tree
        if self.scope is not None:
            found = _scope_node(tree, self.scope)
            if found is None:
                raise PreflightError(
                    f"stale site inventory: {self.path} no longer defines {self.scope!r}. "
                    "Update the site table in this script to the current name."
                )
            node = found
        return any(_matches(value, family_id, self.match) for value in _string_constants(node))


def _scope_node(tree: ast.Module, scope: str) -> ast.AST | None:
    """Find the module-level binding, function, or class named `scope`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == scope for target in node.targets):
                return node
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == scope:
                return node
        elif (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name == scope
        ):
            return node
    return None


def _string_constants(node: ast.AST) -> Iterator[str]:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            yield child.value


# --------------------------------------------------------------------------
# Site inventory -- the single edit point for a tenth site
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Site:
    """One numbered declaration site, made of one or more probes."""

    number: int
    label: str
    probes: tuple[Probe, ...]


def _always(_: FamilyFacts) -> bool:
    return True


def _consumer_selectable(facts: FamilyFacts) -> bool:
    return facts.consumer_selectable


def _in_census(facts: FamilyFacts) -> bool:
    return facts.has_findings_provider


def _seam(facts: FamilyFacts) -> bool:
    """Whether the family needs family-authored provider input.

    An empty census means the authority has not been decided yet, which is the
    normal state for the family this tool exists to help adopt. Report the
    sites rather than hide them: a spurious line costs seconds, and a silent
    omission is the multi-hour cascade measured in the #133 findings.
    """
    if not facts.has_findings_provider:
        return False
    if not facts.census_authorities:
        return True
    return "family" in facts.census_authorities


def _catalog_native_candidate(facts: FamilyFacts) -> bool:
    """Only a catalog DEFAULT is classified; retained and internal ids are not."""
    return facts.is_catalog_default and not facts.has_legacy_bundle


def _needs_minimal_config(facts: FamilyFacts) -> bool:
    return facts.has_required_option_without_default


def _ships_executables(facts: FamilyFacts) -> bool:
    return facts.has_executables


def _contributes_markdown_block(facts: FamilyFacts) -> bool:
    return facts.has_markdown_block


SITES: tuple[Site, ...] = (
    Site(
        number=1,
        label="catalog entry",
        probes=(
            TomlArrayProbe(
                path=_CATALOG_PATH,
                role="packages entry",
                array="packages",
                key="id",
                applies=_always,
            ),
        ),
    ),
    Site(
        number=2,
        label="self-hosting selection (seam canary)",
        probes=(
            TomlTableProbe(
                path=".standards/config.toml",
                role="[standards.<id>] table",
                prefix="standards",
                applies=_consumer_selectable,
            ),
        ),
    ),
    Site(
        number=3,
        label="compatibility matrix minimal config",
        probes=(
            PythonProbe(
                path="tests/package_compatibility/matrix.py",
                role="_MINIMAL_PACKAGE_CONFIG",
                scope="_MINIMAL_PACKAGE_CONFIG",
                match=Match.EXACT,
                applies=_needs_minimal_config,
            ),
        ),
    ),
    Site(
        number=4,
        label="catalog-native classification",
        probes=(
            PythonProbe(
                path="tests/test_standards_composition.py",
                role="_CATALOG_NATIVE_FAMILIES",
                scope="_CATALOG_NATIVE_FAMILIES",
                match=Match.EXACT,
                applies=_catalog_native_candidate,
            ),
        ),
    ),
    Site(
        number=5,
        label="command resolution seam oracle",
        probes=(
            PythonProbe(
                path="tests/control_plane/test_command_resolution.py",
                role="_SEAM_FAMILIES",
                scope="_SEAM_FAMILIES",
                match=Match.EXACT,
                applies=_seam,
            ),
            # The test-owned copy of the declared read set is a NEW binding
            # named after the family, so it is found by module scope.
            PythonProbe(
                path="tests/control_plane/test_command_resolution.py",
                role="declared read-set copy",
                scope=None,
                match=Match.PATH_SEGMENT,
                applies=_seam,
            ),
        ),
    ),
    Site(
        number=6,
        label="authoritative provider-input census",
        probes=(
            PythonProbe(
                path=_CENSUS_PATH,
                role=_CENSUS_BINDING,
                scope=_CENSUS_BINDING,
                match=Match.EXACT,
                applies=_in_census,
            ),
        ),
    ),
    Site(
        number=7,
        label="provider input dispatch and read set",
        probes=(
            # Both probes are module-scoped because both declarations are new
            # per-family names. The match modes keep them independent: an
            # artifact path never equals the bare id, and the dispatch branch
            # never contains a slash.
            PythonProbe(
                path="src/project_standards/control_plane/provider_inputs.py",
                role="dispatch branch",
                scope=None,
                match=Match.EXACT,
                applies=_seam,
            ),
            PythonProbe(
                path="src/project_standards/control_plane/provider_inputs.py",
                role="declared read set",
                scope=None,
                match=Match.PATH_SEGMENT,
                applies=_seam,
            ),
        ),
    ),
    Site(
        number=8,
        label="executable projection allowlist",
        probes=(
            PythonProbe(
                path="tests/test_repository_hygiene.py",
                role="_POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES",
                scope="_POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES",
                match=Match.PATH_SEGMENT,
                applies=_ships_executables,
            ),
        ),
    ),
    Site(
        number=9,
        label="shallow corpus and managed-markdown owners",
        probes=(
            PythonProbe(
                path="tests/package_contract/test_release_consistency.py",
                role="_LIVE_SHALLOW_FAMILY_CORPUS",
                scope="_LIVE_SHALLOW_FAMILY_CORPUS",
                match=Match.PATH_SEGMENT,
                applies=_always,
            ),
            PythonProbe(
                path="tests/agent_handoff/test_selected_routing.py",
                role="managed-markdown owner set",
                scope=(
                    "test_managed_markdown_snapshot_spans_all_packages_while_local_units_stay_local"
                ),
                match=Match.EXACT,
                applies=_contributes_markdown_block,
            ),
        ),
    ),
)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeResult:
    role: str
    path: str
    status: Status


@dataclass(frozen=True)
class SiteResult:
    number: int
    label: str
    probes: tuple[ProbeResult, ...]

    @property
    def status(self) -> Status:
        applicable = [item for item in self.probes if item.status is not Status.NOT_APPLICABLE]
        if not applicable:
            return Status.NOT_APPLICABLE
        if any(item.status is Status.MISSING for item in applicable):
            return Status.MISSING
        return Status.DECLARED


def inspect_family(root: Path, family_id: str) -> tuple[FamilyFacts, tuple[SiteResult, ...]]:
    """Run every probe for one family and return the per-site verdicts."""
    facts = collect_facts(root, family_id)
    results: list[SiteResult] = []
    for site in SITES:
        probe_results: list[ProbeResult] = []
        for probe in site.probes:
            if not probe.applies(facts):
                status = Status.NOT_APPLICABLE
            elif probe.declared(root, family_id):
                status = Status.DECLARED
            else:
                status = Status.MISSING
            probe_results.append(ProbeResult(role=probe.role, path=probe.path, status=status))
        results.append(
            SiteResult(number=site.number, label=site.label, probes=tuple(probe_results))
        )
    return facts, tuple(results)


def _render_human(facts: FamilyFacts, results: Sequence[SiteResult]) -> str:
    lines = [
        f"family: {facts.family_id}@{facts.version}",
        "",
    ]
    for result in results:
        lines.append(f"{result.number}. {result.label}  [{result.status}]")
        for probe in result.probes:
            lines.append(f"     {probe.status:<14} {probe.path}  ({probe.role})")
    missing = [result for result in results if result.status is Status.MISSING]
    lines.append("")
    if missing:
        numbers = ", ".join(str(result.number) for result in missing)
        lines.append(f"{len(missing)} site(s) missing: {numbers}")
    else:
        lines.append("every applicable site is declared")
    # Stated on every run, including the green one: the gates remain the
    # authority, and this check never inspects whether a value is correct.
    lines.append("This predicts the gates; it does not replace them. Run the gate.")
    return "\n".join(lines)


def _render_json(facts: FamilyFacts, results: Sequence[SiteResult]) -> str:
    payload = {
        "ok": all(result.status is not Status.MISSING for result in results),
        "family": facts.family_id,
        "version": facts.version,
        "sites": [
            {
                "number": result.number,
                "label": result.label,
                "status": str(result.status),
                "probes": [
                    {"role": probe.role, "path": probe.path, "status": str(probe.status)}
                    for probe in result.probes
                ],
            }
            for result in results
        ],
    }
    return json.dumps(payload, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="family-preflight",
        description=(
            "Report which hand-maintained declaration sites already mention a family id. "
            "Predicts the integration gates so a new family lands in one authored pass."
        ),
    )
    parser.add_argument("family_id", help="catalog family id, e.g. github-workflow")
    parser.add_argument("--root", type=Path, default=_REPO_ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    try:
        facts, results = inspect_family(Path(args.root).resolve(), str(args.family_id))
    except PreflightError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    render = _render_json if bool(args.json) else _render_human
    print(render(facts, results))
    return 1 if any(result.status is Status.MISSING for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
