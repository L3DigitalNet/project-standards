"""Validate release-current prose against one exact candidate catalog."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    render_consumer_catalog,
)
from project_standards.package_contract.diagnostics import PackageFinding, sort_findings
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import PayloadAvailability
from project_standards.package_contract.repository import PackageRepository

_PACKAGE_VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
_TOOL_VERSION = rf"{_PACKAGE_VERSION}\.(?:0|[1-9][0-9]*)"
_EXACT_SELECTOR = re.compile(
    rf"(?<![A-Za-z0-9_-])(?P<family>[a-z][a-z0-9-]*)@"
    rf"(?P<version>{_PACKAGE_VERSION})(?![0-9]|\.[0-9])"
)
_FULL_VERSION_PATH = re.compile(
    rf"(?<![A-Za-z0-9_./-])standards/(?P<family>[a-z][a-z0-9-]*)/"
    rf"versions/(?P<version>{_PACKAGE_VERSION})(?=/)"
)
_SHALLOW_VERSION_PATH = re.compile(
    rf"(?<![A-Za-z0-9_./-])versions/(?P<version>{_PACKAGE_VERSION})(?=/)"
)
_ENABLE_COMMAND = re.compile(
    rf"project-standards\s+standards\s+enable\s+"
    rf"(?P<family>[a-z][a-z0-9-]*)\s+--version(?:=|\s+)"
    rf"(?P<version>{_PACKAGE_VERSION})(?![0-9]|\.[0-9])"
)
_FAMILY_VERSION = re.compile(
    rf"(?<![A-Za-z0-9_-])(?P<family>[a-z][a-z0-9-]*)\s+version\s+"
    rf"`?(?P<version>{_PACKAGE_VERSION})`?(?![0-9]|\.[0-9])",
    re.IGNORECASE,
)
_BARE_PACKAGE_VERSION = re.compile(
    rf"\bPackage(?:\s+version)?\s+`?"
    rf"(?P<version>{_PACKAGE_VERSION})`?(?![0-9]|\.[0-9])",
    re.IGNORECASE,
)
_INTERNAL_PACKAGE_VERSION = re.compile(
    rf"\bInternal package\s+`?"
    rf"(?P<version>{_PACKAGE_VERSION})`?(?![0-9]|\.[0-9])",
    re.IGNORECASE,
)
_MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((?P<target>[^)\s]+)\)")
_PROJECT_RELEASE_PATTERNS = (
    re.compile(rf"\bProject Standards (?P<version>{_TOOL_VERSION})\b"),
    re.compile(rf"project-standards@v(?P<version>{_TOOL_VERSION})\b"),
    re.compile(rf"\bproject-standards (?P<version>{_TOOL_VERSION})\b"),
    re.compile(rf"\brev:\s+v(?P<version>{_TOOL_VERSION})\b"),
)
_MARKER = re.compile(
    r"<!-- release-consistency: "
    r"(?P<kind>historical|historical-characterization|catalog-range|inventory) "
    r"(?P<family>[a-z][a-z0-9-]*)"
    r"(?: (?P<source>catalog|family))? -->"
)

_ROOT_CURRENT = ("README.md", "UPGRADING.md", "AGENTS.md", "standards/README.md")
_OPTIONAL_CURRENT = ("docs/STATUS.md", "docs/handoff/conventions.md")
_STRUCTURAL_FILES = frozenset(
    {
        "CHANGELOG.md",
        "docs/handoff/deployed.md",
        "docs/handoff/specs-plans.md",
        "docs/usage.md",
    }
)
_STRUCTURAL_PREFIXES = (
    ".project-pipeline/",
    "docs/plans/",
    "docs/specs/",
    "docs/adr/",
    "docs/handoff/bugs/",
    "docs/handoff/sessions/",
    "docs/research/",
    "docs/reviews/",
    "docs/specs/archive/",
    "scripts/",
    "src/project_standards/families/",
    "src/project_standards/payloads/",
    "standards/",
    "tests/",
)
_HISTORICAL_SECTIONS = frozenset(
    {
        "deviations",
        "legacy boundary",
        "migration",
        "released-version errata",
        "revision history",
    }
)
_NATURAL_HISTORY_PHRASES = (
    "correction from",
    "historical #",
    "historical limitations",
    "immutable ",
    "released history",
    "remain advertised as released history",
    "migration evidence only",
    "previous behavior",
    "prior internal",
    "superseded package",
)
# These exact documents were characterized at T14.0. Any byte change removes the
# exemption so newly edited body prose must pass the ordinary fail-closed scan.
_CHARACTERIZED_SPEC_PLAN_DIGESTS = {
    "docs/plans/2026-07-19-project-standards-5.1-review-remediation.md": (
        "40bfd4fa0261c384d50bba2c92556b6d5c56136022814955b40c3ba7feb68a4a"
    ),
    "docs/plans/2026-07-24-project-standards-mcp-documentation-reconciliation-plan.md": (
        "a9d677cb3895790a0aca43bfeccbd025accd17049d6b310a17bb3c692a99088a"
    ),
    "docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md": (
        "3b52aae630a2605cd931196d481c7815c43b7c5380eaf7da30a1ee78fafbf229"
    ),
    "docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md": (
        "b36e2e68130f3b4ac61f87d073aba703b47b0b3940493b8bb1c7c8f264d54413"
    ),
    "docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md": (
        "9fe629b29f2d86078798ab8e9f01feec9cba324dd53f6a7759be10e6ceb4f64d"
    ),
}


@dataclass(frozen=True, slots=True)
class FamilyReleaseFacts:
    """Catalog-derived current and inventory versions for one governed family."""

    standard_id: str
    display_name: str
    current: PackageVersion
    role: CatalogRole
    catalog_versions: tuple[PackageVersion, ...]
    family_versions: tuple[PackageVersion, ...]


@dataclass(frozen=True, slots=True)
class _Reference:
    family: str
    version: str
    kind: str


def _finding(
    code: str,
    path: str,
    identity: str,
    *,
    standard_id: str = "project-standards",
    version: str = "",
) -> PackageFinding:
    messages = {
        "PC-RELEASE-CORPUS": "a required release-consistency surface is unavailable",
        "PC-RELEASE-DISTRIBUTION-VERSION": (
            "candidate distribution metadata does not match the validated tool version"
        ),
        "PC-RELEASE-INTERNAL-CURRENT-MISSING": (
            "an internal package has no canonical internal catalog row"
        ),
        "PC-RELEASE-INVENTORY": "a classified package inventory disagrees with its authority",
        "PC-RELEASE-LINK": "a current package reference does not resolve to a safe regular file",
        "PC-RELEASE-PACKAGE-CURRENT": (
            "a release-current package reference disagrees with the candidate catalog"
        ),
        "PC-RELEASE-PATH-UNCLASSIFIED": (
            "a package-version reference appears in an unclassified mutable path"
        ),
        "PC-RELEASE-PROJECT-VERSION": (
            "a release-current project version disagrees with candidate metadata"
        ),
        "PC-RELEASE-PROJECTION": "a generated catalog projection is stale",
    }
    hints = {
        "PC-RELEASE-CORPUS": "restore the required regular UTF-8 file and rerun the release gate",
        "PC-RELEASE-INTERNAL-CURRENT-MISSING": (
            "add the intended internal row to the candidate catalog before updating prose"
        ),
        "PC-RELEASE-INVENTORY": "regenerate the inventory from its declared package authority",
        "PC-RELEASE-LINK": "repair the contained repository-relative current-package link",
        "PC-RELEASE-PROJECTION": "regenerate the catalog projection from the candidate catalog",
    }
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path=path,
        identity=identity,
        message=messages[code],
        hint=hints.get(
            code,
            "update the release-current reference from candidate catalog metadata",
        ),
    )


def _family_facts(
    repository: PackageRepository,
) -> tuple[dict[str, FamilyReleaseFacts], list[PackageFinding]]:
    catalog = repository.catalog
    if catalog is None:
        return (
            {},
            [
                _finding(
                    "PC-RELEASE-CORPUS",
                    "catalogs",
                    "candidate-catalog",
                )
            ],
        )

    entries_by_family: dict[str, list[CatalogPackageEntry]] = {}
    for entry in catalog.packages:
        entries_by_family.setdefault(entry.id, []).append(entry)

    availability_by_family: dict[str, set[PayloadAvailability]] = {}
    for payload in repository.payloads:
        availability_by_family.setdefault(
            payload.manifest.payload.standard,
            set(),
        ).add(payload.manifest.payload.availability)

    facts: dict[str, FamilyReleaseFacts] = {}
    findings: list[PackageFinding] = []
    for family in repository.families:
        standard_id = family.manifest.standard.id
        entries = entries_by_family.get(standard_id, [])
        defaults = [entry for entry in entries if entry.role is CatalogRole.DEFAULT]
        internal = [entry for entry in entries if entry.role is CatalogRole.INTERNAL]
        role: CatalogRole
        current: PackageVersion
        if defaults:
            selected = defaults[0]
            role = CatalogRole.DEFAULT
            current = selected.version
        elif PayloadAvailability.INTERNAL in availability_by_family.get(standard_id, set()):
            if not internal:
                findings.append(
                    _finding(
                        "PC-RELEASE-INTERNAL-CURRENT-MISSING",
                        f"catalogs/{catalog.catalog_major}.toml",
                        f"internal:{standard_id}",
                        standard_id=standard_id,
                    )
                )
                continue
            selected = max(internal, key=lambda entry: entry.version.sort_key)
            role = CatalogRole.INTERNAL
            current = selected.version
        else:
            continue

        display_name = family.manifest.standard.name
        if display_name.endswith(" Standard"):
            display_name = display_name.removesuffix(" Standard")
        facts[standard_id] = FamilyReleaseFacts(
            standard_id=standard_id,
            display_name=display_name,
            current=current,
            role=role,
            catalog_versions=tuple(
                sorted(
                    (entry.version for entry in entries),
                    key=lambda version: version.sort_key,
                )
            ),
            family_versions=tuple(
                sorted(
                    (entry.version for entry in family.manifest.versions),
                    key=lambda version: version.sort_key,
                )
            ),
        )
    return facts, findings


def _tracked_markdown(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ()
    try:
        paths = completed.stdout.decode("utf-8").split("\0")
    except UnicodeDecodeError:
        return ()
    return tuple(sorted(path for path in paths if path))


def _read_regular_utf8_bytes(
    root: Path,
    relative: str,
    findings: list[PackageFinding],
) -> tuple[str, bytes] | None:
    try:
        relative_path = PurePosixPath(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise OSError
        path = root.joinpath(*relative_path.parts)
        cursor = root
        for part in relative_path.parts:
            cursor /= part
            if cursor.is_symlink():
                raise OSError
        if not path.resolve(strict=False).is_relative_to(root) or not path.is_file():
            raise OSError
        raw = path.read_bytes()
        return raw.decode("utf-8"), raw
    except OSError, UnicodeDecodeError, ValueError:
        findings.append(
            _finding(
                "PC-RELEASE-CORPUS",
                relative,
                "required-surface",
            )
        )
        return None


def _read_regular_utf8(
    root: Path,
    relative: str,
    findings: list[PackageFinding],
) -> str | None:
    result = _read_regular_utf8_bytes(root, relative, findings)
    return None if result is None else result[0]


def _shallow_family(path: str, facts: dict[str, FamilyReleaseFacts]) -> str | None:
    parts = PurePosixPath(path).parts
    if len(parts) == 3 and parts[0] == "standards" and parts[2].endswith(".md"):
        return parts[1] if parts[1] in facts else None
    return None


def _marker_before(lines: list[str], index: int) -> re.Match[str] | None:
    previous = index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    if previous < 0:
        return None
    return _MARKER.fullmatch(lines[previous].strip())


def _section_history(lines: list[str], index: int) -> bool:
    for line in reversed(lines[: index + 1]):
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading is None:
            continue
        return heading.group(2).strip().casefold() in _HISTORICAL_SECTIONS
    return False


def _references(
    line: str,
    *,
    shallow_family: str | None,
    facts: dict[str, FamilyReleaseFacts],
) -> tuple[_Reference, ...]:
    references: list[_Reference] = []
    for expression, kind in (
        (_EXACT_SELECTOR, "exact-selector"),
        (_FULL_VERSION_PATH, "versioned-link"),
        (_ENABLE_COMMAND, "enable-command"),
        (_FAMILY_VERSION, "family-prose"),
    ):
        for match in expression.finditer(line):
            family = match.group("family").casefold()
            if family in facts:
                references.append(_Reference(family, match.group("version"), kind))

    if shallow_family is not None:
        for match in _SHALLOW_VERSION_PATH.finditer(line):
            references.append(_Reference(shallow_family, match.group("version"), "versioned-link"))
        for match in _BARE_PACKAGE_VERSION.finditer(line):
            references.append(_Reference(shallow_family, match.group("version"), "family-prose"))

    line_folded = line.casefold()
    for family, release in facts.items():
        name = release.display_name.casefold()
        for match in re.finditer(
            rf"(?<![a-z0-9_-]){re.escape(name)}\s+`?"
            rf"(?P<version>{_PACKAGE_VERSION})`?(?![0-9]|\.[0-9])",
            line_folded,
        ):
            references.append(_Reference(family, match.group("version"), "named-prose"))

    unique: dict[tuple[str, str, str], _Reference] = {}
    for reference in references:
        unique[(reference.family, reference.version, reference.kind)] = reference
    return tuple(unique.values())


def _historical_line(
    path: str,
    lines: list[str],
    index: int,
    family: str,
) -> bool:
    marker = _marker_before(lines, index)
    if marker is not None and marker.group("family") == family:
        return marker.group("kind") in {
            "historical",
            "historical-characterization",
            "catalog-range",
            "inventory",
        }
    if _section_history(lines, index):
        return True
    line = lines[index].casefold()
    if any(phrase in line for phrase in _NATURAL_HISTORY_PHRASES):
        return True
    return path == "standards/python-tooling/build-backend.md"


def _validate_inventory_line(
    path: str,
    lines: list[str],
    index: int,
    facts: dict[str, FamilyReleaseFacts],
    findings: list[PackageFinding],
) -> bool:
    marker = _marker_before(lines, index)
    if marker is None or marker.group("kind") != "inventory":
        return False
    family = marker.group("family")
    release = facts.get(family)
    if release is None:
        findings.append(
            _finding(
                "PC-RELEASE-INVENTORY",
                path,
                f"line:{index + 1}:inventory",
                standard_id=family,
            )
        )
        return True
    source = marker.group("source") or "family"
    expected = release.catalog_versions if source == "catalog" else release.family_versions
    observed = {
        reference.version
        for reference in _references(lines[index], shallow_family=None, facts=facts)
        if reference.family == family
    }
    if observed != {version.value for version in expected}:
        findings.append(
            _finding(
                "PC-RELEASE-INVENTORY",
                path,
                f"line:{index + 1}:inventory",
                standard_id=family,
            )
        )
    return True


def _safe_link(root: Path, document: str, target: str) -> bool:
    if target.startswith(("#", "http://", "https://", "mailto:")):
        return True
    target_path = PurePosixPath(target.split("#", 1)[0])
    if target_path.is_absolute():
        return False
    lexical = Path(os.path.normpath(str(Path(document).parent / Path(target_path))))
    if lexical == Path("..") or ".." in lexical.parts:
        return False
    candidate = root / lexical
    try:
        if not candidate.resolve(strict=False).is_relative_to(root.resolve()):
            return False
        relative = candidate.relative_to(root)
        cursor = root
        for part in relative.parts:
            cursor /= part
            if cursor.is_symlink():
                return False
        return candidate.is_file() or candidate.is_dir()
    except OSError, ValueError:
        return False


def _validate_links(
    root: Path,
    path: str,
    lines: list[str],
    index: int,
    *,
    shallow_family: str | None,
    facts: dict[str, FamilyReleaseFacts],
    findings: list[PackageFinding],
) -> None:
    line = lines[index]
    for link in _MARKDOWN_LINK.finditer(line):
        target = link.group("target")
        target_references = _references(
            target,
            shallow_family=shallow_family,
            facts=facts,
        )
        current_context = any(
            reference.version == facts[reference.family].current.value
            for reference in target_references
        ) or any(
            phrase in line.casefold()
            for phrase in ("current adoption guide", "current authority", "current link")
        )
        if current_context and not _safe_link(root, path, target):
            family = (
                target_references[0].family
                if target_references
                else shallow_family or "project-standards"
            )
            findings.append(
                _finding(
                    "PC-RELEASE-LINK",
                    path,
                    f"line:{index + 1}:link",
                    standard_id=family,
                )
            )


def _scan_current_document(
    root: Path,
    path: str,
    text: str,
    facts: dict[str, FamilyReleaseFacts],
    findings: list[PackageFinding],
) -> None:
    lines = text.splitlines()
    shallow = _shallow_family(path, facts)
    root_internal_reported: set[str] = set()
    internal_families = tuple(
        family for family, release in facts.items() if release.role is CatalogRole.INTERNAL
    )
    for index, line in enumerate(lines):
        _validate_inventory_line(path, lines, index, facts, findings)
        references = list(
            () if path == "UPGRADING.md" else _references(line, shallow_family=shallow, facts=facts)
        )
        if path == "README.md" and len(internal_families) == 1:
            references.extend(
                _Reference(
                    family=internal_families[0],
                    version=match.group("version"),
                    kind="internal-package-prose",
                )
                for match in _INTERNAL_PACKAGE_VERSION.finditer(line)
            )
        reported_on_line: set[str] = set()
        for reference in references:
            release = facts[reference.family]
            if path in _OPTIONAL_CURRENT and release.role is not CatalogRole.INTERNAL:
                continue
            if reference.version == release.current.value:
                continue
            if _historical_line(path, lines, index, reference.family):
                continue
            if (
                path in _ROOT_CURRENT
                and release.role is CatalogRole.INTERNAL
                and reference.family in root_internal_reported
            ):
                continue
            if reference.family in reported_on_line:
                continue
            findings.append(
                _finding(
                    "PC-RELEASE-PACKAGE-CURRENT",
                    path,
                    f"line:{index + 1}:{reference.kind}",
                    standard_id=reference.family,
                    version=reference.version,
                )
            )
            reported_on_line.add(reference.family)
            if path in _ROOT_CURRENT and release.role is CatalogRole.INTERNAL:
                root_internal_reported.add(reference.family)
        if path not in _OPTIONAL_CURRENT and path != "UPGRADING.md":
            _validate_links(
                root,
                path,
                lines,
                index,
                shallow_family=shallow,
                facts=facts,
                findings=findings,
            )


def _scan_project_versions(
    path: str,
    text: str,
    expected: str,
    findings: list[PackageFinding],
) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "replaces the legacy" in line.casefold():
            continue
        observed: set[str] = set()
        for expression in _PROJECT_RELEASE_PATTERNS:
            observed.update(match.group("version") for match in expression.finditer(line))
        for version in sorted(observed):
            if version != expected:
                findings.append(
                    _finding(
                        "PC-RELEASE-PROJECT-VERSION",
                        path,
                        f"line:{line_number}:project-release",
                        version=version,
                    )
                )


def _validate_distribution_version(
    root: Path,
    distribution_version: str,
    findings: list[PackageFinding],
) -> None:
    text = _read_regular_utf8(root, "pyproject.toml", findings)
    if text is None:
        return
    try:
        raw = tomllib.loads(text)
        project = raw["project"]
        version = project["version"]
    except KeyError, TypeError, tomllib.TOMLDecodeError:
        version = None
    if version != distribution_version:
        findings.append(
            _finding(
                "PC-RELEASE-DISTRIBUTION-VERSION",
                "pyproject.toml",
                "project.version",
                version=version if isinstance(version, str) else "",
            )
        )


def _validate_projections(
    root: Path,
    repository: PackageRepository,
    distribution_version: str,
    findings: list[PackageFinding],
) -> None:
    if repository.catalog is None:
        return
    from project_standards.standards_graph.catalog import render_catalog
    from project_standards.standards_graph.model import StandardsGraph

    graph = StandardsGraph(
        root=root,
        standards=(),
        missing_manifest_dirs=(),
        package_repository=repository,
    )
    expected_human = render_catalog(graph)
    human_path = root / "standards/catalog.md"
    try:
        human_matches = (
            not human_path.is_symlink()
            and human_path.is_file()
            and human_path.read_text(encoding="utf-8") == expected_human
        )
    except OSError, UnicodeDecodeError:
        human_matches = False
    if not human_matches:
        findings.append(
            _finding(
                "PC-RELEASE-PROJECTION",
                "standards/catalog.md",
                "human-catalog",
            )
        )

    consumer_path = root / ".standards/catalog.toml"
    if consumer_path.exists() or consumer_path.is_symlink():
        expected_consumer = render_consumer_catalog(
            repository.catalog,
            repository.family_map,
            repository.payload_map,
            tool_release=distribution_version,
        )
        try:
            consumer_matches = (
                not consumer_path.is_symlink()
                and consumer_path.is_file()
                and consumer_path.read_bytes() == expected_consumer
            )
        except OSError:
            consumer_matches = False
        if not consumer_matches:
            findings.append(
                _finding(
                    "PC-RELEASE-PROJECTION",
                    ".standards/catalog.toml",
                    "consumer-catalog",
                )
            )


def _is_structural_path(path: str) -> bool:
    if path in _STRUCTURAL_FILES:
        return True
    if "/versions/" in path and path.startswith("standards/"):
        return True
    return any(path.startswith(prefix) for prefix in _STRUCTURAL_PREFIXES)


def _scan_unclassified_paths(
    root: Path,
    tracked: tuple[str, ...],
    current_paths: set[str],
    facts: dict[str, FamilyReleaseFacts],
    findings: list[PackageFinding],
) -> None:
    internal_families = {
        family for family, release in facts.items() if release.role is CatalogRole.INTERNAL
    }
    for path in tracked:
        if path in current_paths or path == "standards/catalog.md":
            continue
        if _is_structural_path(path) and (
            not path.startswith(("docs/specs/", "docs/plans/"))
            or path.startswith("docs/specs/archive/")
        ):
            continue
        document = _read_regular_utf8_bytes(root, path, findings)
        if document is None:
            continue
        text, raw = document
        characterized_digest = _CHARACTERIZED_SPEC_PLAN_DIGESTS.get(path)
        if characterized_digest is not None and (
            hashlib.sha256(raw).hexdigest() == characterized_digest
        ):
            continue
        lines = text.splitlines()
        for index, line in enumerate(lines):
            _validate_inventory_line(path, lines, index, facts, findings)
            references = tuple(
                reference
                for reference in _references(line, shallow_family=None, facts=facts)
                if reference.family in internal_families
            )
            if not references:
                continue
            stale = [
                reference
                for reference in references
                if reference.version != facts[reference.family].current.value
            ]
            if not stale:
                continue
            stale = [
                reference
                for reference in stale
                if not _historical_line(path, lines, index, reference.family)
            ]
            if not stale:
                continue
            findings.append(
                _finding(
                    "PC-RELEASE-PATH-UNCLASSIFIED",
                    path,
                    f"line:{index + 1}:package-reference",
                    standard_id=stale[0].family,
                    version=stale[0].version,
                )
            )
            break


def validate_release_consistency(
    root: Path,
    repository: PackageRepository,
    *,
    distribution_version: str,
) -> tuple[PackageFinding, ...]:
    """Return stable findings for release-current candidate/catalog drift."""
    resolved_root = root.resolve()
    findings: list[PackageFinding] = []
    facts, fact_findings = _family_facts(repository)
    findings.extend(fact_findings)
    _validate_distribution_version(resolved_root, distribution_version, findings)

    tracked = _tracked_markdown(resolved_root)
    if not tracked:
        findings.append(
            _finding(
                "PC-RELEASE-CORPUS",
                ".git",
                "tracked-markdown",
            )
        )
        return tuple(sort_findings(findings))

    shallow_paths = {path for path in tracked if _shallow_family(path, facts) is not None}
    current_paths = set(_ROOT_CURRENT) | shallow_paths
    current_paths.update(path for path in _OPTIONAL_CURRENT if path in tracked)
    documents: dict[str, str] = {}
    for path in sorted(current_paths):
        text = _read_regular_utf8(resolved_root, path, findings)
        if text is not None:
            documents[path] = text

    for path, text in documents.items():
        _scan_current_document(resolved_root, path, text, facts, findings)
    for path in ("README.md", "UPGRADING.md"):
        text = documents.get(path)
        if text is not None:
            _scan_project_versions(path, text, distribution_version, findings)

    _scan_unclassified_paths(
        resolved_root,
        tracked,
        current_paths,
        facts,
        findings,
    )
    _validate_projections(
        resolved_root,
        repository,
        distribution_version,
        findings,
    )
    return tuple(sort_findings(findings))
