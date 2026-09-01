"""Author a successor payload version as an edited copy of its predecessor.

Released payload bytes are immutable at every release level: `packages
check-release` classifies any change under an already-advertised
`standards/<family>/versions/<v>/` as forbidden. A fix or a feature is therefore
always cut as a *new* version directory copied from the predecessor, with four
declaration sites moved in lockstep — the copied `payload.toml`, the family
index, the catalog major, and the generated projection and catalog. This module
performs exactly the mechanical half of that procedure; the content edits and
the family landing pages stay with the author.

Two deliberate non-goals, both because a wrong automatic answer here is worse
than no answer:

Stale embedded version references are REPORTED, never rewritten. A successor
copy inherits every string naming the predecessor — provider-input constants,
migration ids and `from` endpoints, schema enums, documentation permalinks — and
only some of them must move. A permalink into the predecessor's own published
documentation, or a migration whose `from` endpoint names the version a consumer
is leaving, is correct history that a blanket substitution would silently
corrupt. The single exception is a migration's `to` endpoint, which the payload
contract requires to name the containing version and which
`_rewrite_payload_manifest` therefore re-points; it is reported as an applied
edit, not left for the author.

Family landing pages (`standards/<family>/README.md`, `agent-summary.md`,
`adopt.md`) are untouched. They are prose mirrors whose "what changed" sections
cannot be generated, and a half-written mirror reads as finished work.

The digest chain runs in one direction and the order below is load-bearing: the
per-resource digests are written into `payload.toml` first, because the
aggregate hashes `payload.toml`'s own bytes along with every declared file. The
aggregate is then computed by `validate_payload_integrity`, the same function
the repository validators use, so a manifest this module writes and a manifest a
human writes are verified by one implementation.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from project_standards.package_contract._write import atomic_write
from project_standards.package_contract.catalog import (
    CatalogRole,
    load_catalog_source,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import load_payload_manifest

_SCALAR = re.compile(
    r'^(?P<indent>[ \t]*)(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"(?P<value>[^"]*)"'
)
_TABLE_HEADER = re.compile(r"^\s*\[")
_DIGEST_TABLES = {"[[resources]]": "path", "[[artifacts]]": "source"}
_TEST_FUNCTION = re.compile(r"^def (test_[A-Za-z0-9_]+)\(", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class VersionOccurrence:
    """One line inside the new payload tree that still names the predecessor."""

    path: str
    line: int
    text: str


@dataclass(frozen=True, slots=True)
class CutPlan:
    """Every path and role decision the cut will apply, resolved before any write."""

    root: Path
    standard_id: str
    predecessor: PackageVersion
    successor: PackageVersion
    source_dir: Path
    target_dir: Path
    family_index: Path
    catalog_path: Path
    successor_role: CatalogRole
    predecessor_role: CatalogRole
    predecessor_role_after: CatalogRole
    predecessor_test: Path | None
    scaffold_target: Path | None


@dataclass(frozen=True, slots=True)
class CutResult:
    """What the applied cut wrote, plus the review work it hands back to the author."""

    plan: CutPlan
    aggregate_digest: Sha256Digest
    file_count: int
    occurrences: tuple[VersionOccurrence, ...]
    undecodable: tuple[str, ...]
    repointed_migrations: tuple[str, ...]
    scaffold_written: Path | None


def _family_dir(root: Path, standard_id: str) -> Path:
    directory = root / "standards" / standard_id
    if directory.is_symlink() or not directory.is_dir():
        raise PackageContractError(f"standard family is not a directory: standards/{standard_id}")
    return directory


def _catalog_for(root: Path, standard_id: str, predecessor: PackageVersion) -> Path:
    """Return the one catalog major that advertises the predecessor.

    A family is expected to live in exactly one catalog major. Two majors
    advertising it is a state this writer refuses rather than guesses at: the
    successor would have to be added to both, and which of them takes the new
    default is a release decision, not a mechanical one.
    """
    catalogs = root / "catalogs"
    matches = [
        path
        for path in sorted(catalogs.glob("*.toml"))
        if any(
            entry.id == standard_id and entry.version.value == predecessor.value
            for entry in load_catalog_source(path).packages
        )
    ]
    if not matches:
        raise PackageContractError(f"no catalog major advertises {standard_id}@{predecessor.value}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise PackageContractError(
            f"{standard_id}@{predecessor.value} is advertised by several catalog majors: {names}"
        )
    return matches[0]


def _catalog_role(catalog_path: Path, standard_id: str, version: PackageVersion) -> CatalogRole:
    for entry in load_catalog_source(catalog_path).packages:
        if entry.id == standard_id and entry.version.value == version.value:
            return entry.role
    raise PackageContractError(
        f"{standard_id}@{version.value} is not advertised by {catalog_path.name}"
    )


def _test_module_name(standard_id: str, version: PackageVersion) -> str:
    return f"test_{standard_id.replace('-', '_')}_{version.value.replace('.', '_')}.py"


def plan_cut(
    root: Path,
    standard_id: str,
    successor: str,
    *,
    predecessor: str | None = None,
    scaffold_test: bool = False,
) -> CutPlan:
    """Resolve and validate every decision a cut makes, without writing anything.

    Refuses a successor whose version directory already exists, which is the one
    guard that keeps this command from overwriting work in progress or, worse,
    mutating already-released bytes.
    """
    try:
        successor_version = PackageVersion(successor)
    except ValueError as exc:
        raise PackageContractError(
            f"successor version is not canonical MAJOR.MINOR: {successor}"
        ) from exc

    family_dir = _family_dir(root, standard_id)
    manifest = load_family_manifest(family_dir / "standard.toml")
    declared = {entry.version.value: entry.version for entry in manifest.versions}

    if successor_version.value in declared:
        raise PackageContractError(
            f"{standard_id}@{successor_version.value} is already declared in the family index"
        )

    if predecessor is None:
        predecessor_version = max(declared.values(), key=lambda version: version.sort_key)
    elif predecessor in declared:
        predecessor_version = declared[predecessor]
    else:
        raise PackageContractError(
            f"{standard_id}@{predecessor} is not declared in the family index"
        )

    if successor_version.sort_key <= predecessor_version.sort_key:
        raise PackageContractError(
            f"successor {successor_version.value} does not follow "
            f"predecessor {predecessor_version.value}"
        )

    source_dir = family_dir / "versions" / predecessor_version.value
    target_dir = family_dir / "versions" / successor_version.value
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise PackageContractError(f"predecessor payload directory is missing: {source_dir}")
    if target_dir.exists() or target_dir.is_symlink():
        raise PackageContractError(f"successor payload directory already exists: {target_dir}")

    catalog_path = _catalog_for(root, standard_id, predecessor_version)
    if any(
        entry.id == standard_id and entry.version.value == successor_version.value
        for entry in load_catalog_source(catalog_path).packages
    ):
        raise PackageContractError(
            f"{standard_id}@{successor_version.value} is already advertised by {catalog_path.name}"
        )
    predecessor_role = _catalog_role(catalog_path, standard_id, predecessor_version)
    # The successor inherits the predecessor's role, and only a `default`
    # predecessor is demoted. That keeps reference-only and internal families —
    # which have no default at all — from acquiring one as a side effect of a cut.
    successor_role = predecessor_role
    predecessor_role_after = (
        CatalogRole.RETAINED if predecessor_role is CatalogRole.DEFAULT else predecessor_role
    )

    tests_dir = root / "tests" / "package_contract"
    predecessor_test = tests_dir / _test_module_name(standard_id, predecessor_version)
    scaffold_target = tests_dir / _test_module_name(standard_id, successor_version)
    if scaffold_test and scaffold_target.exists():
        raise PackageContractError(f"scaffold target already exists: {scaffold_target}")

    return CutPlan(
        root=root,
        standard_id=standard_id,
        predecessor=predecessor_version,
        successor=successor_version,
        source_dir=source_dir,
        target_dir=target_dir,
        family_index=family_dir / "standard.toml",
        catalog_path=catalog_path,
        successor_role=successor_role,
        predecessor_role=predecessor_role,
        predecessor_role_after=predecessor_role_after,
        predecessor_test=predecessor_test if predecessor_test.is_file() else None,
        scaffold_target=scaffold_target if scaffold_test else None,
    )


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _rewrite_payload_manifest(plan: CutPlan) -> tuple[str, ...]:
    """Stamp the successor version, re-digest every declared file, re-point migrations.

    Returns the migration ids whose `to` endpoint was moved onto the successor.

    Edits the manifest as text rather than re-serializing the parsed model: the
    checked-in manifests carry comments and a hand-chosen layout that a
    round-trip through the strict model would erase, and a cut whose diff is the
    whole file hides the content edits a reviewer is looking for.

    Migration `to` endpoints are the one embedded version reference this module
    does rewrite, because the payload contract admits exactly one value: every
    migration must connect to its containing payload version, so a copied
    `to = "package:<predecessor>"` produces a manifest that does not load at all.
    `from` endpoints are left alone — they name the versions a consumer is
    migrating away from, which the cut does not change — and so are migration
    ids, which routinely spell a version but are opaque to the contract; both
    surface in the predecessor-reference report instead.
    """
    manifest_path = plan.target_dir / "payload.toml"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    header = ""
    file_key: str | None = None
    migration_id: str | None = None
    pending_digest: int | None = None
    replacements: dict[int, str] = {}
    repointed: list[str] = []

    def resolve(block_end: int) -> None:
        if pending_digest is None:
            return
        if file_key is None:
            raise PackageContractError(
                f"payload manifest declares a digest with no source path near line {block_end}"
            )
        target = plan.target_dir / file_key
        if not target.is_file():
            raise PackageContractError(f"declared payload file is missing: {file_key}")
        declaration = _SCALAR.match(lines[pending_digest])
        if declaration is None:  # pragma: no cover - the index came from this same match
            raise PackageContractError("payload manifest digest line could not be re-read")
        replacements[pending_digest] = (
            f'{declaration.group("indent")}digest = "{_sha256_of(target)}"'
        )

    for index, line in enumerate(lines):
        if _TABLE_HEADER.match(line):
            resolve(index)
            header, file_key, pending_digest = line.strip(), None, None
            migration_id = None
            continue
        match = _SCALAR.match(line)
        if match is None:
            continue
        key, value = match.group("key"), match.group("value")
        if header == "[payload]" and key == "version":
            replacements[index] = f'{match.group("indent")}version = "{plan.successor.value}"'
        elif header == "[[migrations]]":
            if key == "id":
                migration_id = value
            elif key == "to" and value == f"package:{plan.predecessor.value}":
                replacements[index] = (
                    f'{match.group("indent")}to = "package:{plan.successor.value}"'
                )
                repointed.append(migration_id or f"line {index + 1}")
        elif header in _DIGEST_TABLES:
            if key == _DIGEST_TABLES[header]:
                file_key = value
            elif key == "digest":
                pending_digest = index
    resolve(len(lines))

    for index, text in replacements.items():
        lines[index] = text
    atomic_write(manifest_path, ("\n".join(lines) + "\n").encode("utf-8"))

    written = load_payload_manifest(manifest_path)
    if written.payload.version.value != plan.successor.value:
        raise PackageContractError(
            "payload manifest did not take the successor version; "
            "its [payload] table may declare version unconventionally"
        )
    return tuple(repointed)


def _append_version_entry(plan: CutPlan, digest: Sha256Digest) -> None:
    text = plan.family_index.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    entry = (
        "\n[[versions]]\n"
        f'version = "{plan.successor.value}"\n'
        f'payload = "versions/{plan.successor.value}/payload.toml"\n'
        f'digest = "{digest.value}"\n'
    )
    atomic_write(plan.family_index, (text + entry).encode("utf-8"))


def _insert_catalog_entry(plan: CutPlan, digest: Sha256Digest) -> None:
    """Add the successor entry directly after the family's last entry.

    Locality is the point: several families can be cut in one release train, and
    an entry appended to the end of the catalog would put every one of those cuts
    in the same diff hunk.
    """
    lines = plan.catalog_path.read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == "[[packages]]"]
    blocks: list[tuple[int, int]] = [
        (start, starts[position + 1] if position + 1 < len(starts) else len(lines))
        for position, start in enumerate(starts)
    ]

    def field(block: tuple[int, int], key: str) -> str | None:
        for index in range(block[0], block[1]):
            match = _SCALAR.match(lines[index])
            if match is not None and match.group("key") == key:
                return match.group("value")
        return None

    family_blocks = [block for block in blocks if field(block, "id") == plan.standard_id]
    if not family_blocks:
        raise PackageContractError(f"{plan.catalog_path.name} declares no {plan.standard_id} entry")

    if plan.predecessor_role_after is not plan.predecessor_role:
        for block in family_blocks:
            if field(block, "version") != plan.predecessor.value:
                continue
            for index in range(block[0], block[1]):
                match = _SCALAR.match(lines[index])
                if match is not None and match.group("key") == "role":
                    lines[index] = f'role = "{plan.predecessor_role_after.value}"'

    insertion = family_blocks[-1][1]
    entry = [
        "[[packages]]",
        f'id = "{plan.standard_id}"',
        f'version = "{plan.successor.value}"',
        f'digest = "{digest.value}"',
        f'role = "{plan.successor_role.value}"',
        "",
    ]
    if insertion >= len(lines):
        entry = ["", *entry[:-1]]
    lines[insertion:insertion] = entry
    atomic_write(plan.catalog_path, ("\n".join(lines) + "\n").encode("utf-8"))


def _predecessor_occurrences(
    plan: CutPlan,
) -> tuple[tuple[VersionOccurrence, ...], tuple[str, ...]]:
    """Report, never rewrite, every line in the new tree naming the predecessor.

    The lookarounds keep `1.8` from matching inside `1.80` or `v1.8.1` while
    still matching the path segments (`versions/1.8/`) and bare mentions that
    carry most of the real staleness.
    """
    pattern = re.compile(rf"(?<![\w.]){re.escape(plan.predecessor.value)}(?![\w.])")
    occurrences: list[VersionOccurrence] = []
    undecodable: list[str] = []
    for path in sorted(plan.target_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(plan.target_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            undecodable.append(relative)
            continue
        for number, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                occurrences.append(
                    VersionOccurrence(path=relative, line=number, text=line.strip()[:160])
                )
    return tuple(occurrences), tuple(undecodable)


def _scaffold_source(plan: CutPlan) -> str:
    behaviors = (
        _TEST_FUNCTION.findall(plan.predecessor_test.read_text(encoding="utf-8"))
        if plan.predecessor_test is not None
        else []
    )
    predecessor_name = (
        plan.predecessor_test.name if plan.predecessor_test is not None else "(none found)"
    )
    todo = "\n".join(f"#   - {name}" for name in behaviors) or "#   (none found)"
    module = plan.standard_id.replace("-", "_")
    return f'''"""Contract tests for {plan.standard_id}@{plan.successor.value}.

Scaffolded by `project-standards standards cut-successor` from
{predecessor_name}. The assertions below are the mechanical half of a cut — the
registration, role, and digest facts that hold for every successor. The behavior
assertions that make the cut worth shipping are still to be written; see the
TODO block at the end of this module.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_STANDARD = "{plan.standard_id}"
_VERSION = "{plan.successor.value}"
_PREDECESSOR = "{plan.predecessor.value}"
_CATALOG = _ROOT / "catalogs" / "{plan.catalog_path.name}"


def _family_versions() -> dict[str, dict[str, object]]:
    raw = tomllib.loads(
        (_ROOT / "standards" / _STANDARD / "standard.toml").read_text(encoding="utf-8")
    )
    return {{entry["version"]: entry for entry in raw["versions"]}}


def _payload_dir() -> Path:
    return _ROOT / "standards" / _STANDARD / "versions" / _VERSION


def _catalog_entries() -> dict[str, dict[str, object]]:
    raw = tomllib.loads(_CATALOG.read_text(encoding="utf-8"))
    return {{entry["version"]: entry for entry in raw["packages"] if entry["id"] == _STANDARD}}


def test_{module}_{plan.successor.value.replace(".", "_")}_is_indexed_by_its_family() -> None:
    entry = _family_versions()[_VERSION]

    assert entry["payload"] == f"versions/{{_VERSION}}/payload.toml"
    assert _payload_dir().joinpath("payload.toml").is_file()


def test_{module}_{plan.successor.value.replace(".", "_")}_payload_declares_its_own_version() -> None:
    manifest = tomllib.loads(_payload_dir().joinpath("payload.toml").read_text(encoding="utf-8"))

    assert manifest["payload"]["standard"] == _STANDARD
    assert manifest["payload"]["version"] == _VERSION


def test_{module}_{plan.successor.value.replace(".", "_")}_catalog_roles_moved_with_the_cut() -> None:
    entries = _catalog_entries()

    assert entries[_VERSION]["role"] == "{plan.successor_role.value}"
    assert entries[_PREDECESSOR]["role"] == "{plan.predecessor_role_after.value}"


def test_{module}_{plan.successor.value.replace(".", "_")}_catalog_and_family_agree_on_the_digest() -> None:
    # The catalog digest and the family index digest are two independent
    # declarations of one payload aggregate; a cut that moves only one of them
    # is exactly the drift PC-CATALOG-DIGEST-REPLACED reports at release time.
    assert _catalog_entries()[_VERSION]["digest"] == _family_versions()[_VERSION]["digest"]


# TODO(before this cut is admitted): port the behavior assertions from
# {predecessor_name}, which pins these cases:
{todo}
'''


def apply_cut(plan: CutPlan) -> CutResult:
    """Execute the planned cut and return the aggregate digest plus the review list.

    A refused cut leaves nothing behind. The copied tree is removed and the
    family index is restored on any failure, because a half-written successor
    directory would be advertised by nothing and yet block the retry — `plan_cut`
    refuses when the target already exists, which is the guard that makes the
    command safe to rerun.
    """
    index_before = plan.family_index.read_bytes()
    try:
        shutil.copytree(plan.source_dir, plan.target_dir, symlinks=True)
        repointed = _rewrite_payload_manifest(plan)
        manifest = load_payload_manifest(plan.target_dir / "payload.toml")
        integrity = validate_payload_integrity(plan.target_dir, manifest)
        _append_version_entry(plan, integrity.aggregate_digest)
        _insert_catalog_entry(plan, integrity.aggregate_digest)
    except BaseException:
        shutil.rmtree(plan.target_dir, ignore_errors=True)
        atomic_write(plan.family_index, index_before)
        raise
    occurrences, undecodable = _predecessor_occurrences(plan)

    scaffold_written: Path | None = None
    if plan.scaffold_target is not None:
        atomic_write(plan.scaffold_target, _scaffold_source(plan).encode("utf-8"))
        scaffold_written = plan.scaffold_target

    return CutResult(
        plan=plan,
        aggregate_digest=integrity.aggregate_digest,
        file_count=len(integrity.inventory),
        occurrences=occurrences,
        undecodable=undecodable,
        repointed_migrations=repointed,
        scaffold_written=scaffold_written,
    )
