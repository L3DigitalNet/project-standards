"""Build disposable release-cut checkouts without mutating the source tree."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Literal, cast

import yaml

from project_standards.control_plane.adapters import JsoncAdapter, TomlAdapter, UnitChange
from project_standards.control_plane.adapters.jsonc import container_value_without_comments
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonObject,
    ProviderEffect,
    ProviderOperation,
    load_option_schema,
)
from project_standards.package_contract.repository import build_package_repository
from tests.wheel_helpers import extract_pure_python_wheel

_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_EVIDENCE = Path(
    "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
)
_RELEASE_EVIDENCE_RECORD_BEGIN = "<!-- release-migration-record:begin -->\n"
_RELEASE_EVIDENCE_RECORD_END = "<!-- release-migration-record:end -->"
_LEGACY_RELEASE_FIXTURE = Path("tests/fixtures/package_compatibility/legacy/release-root")

RELEASE_PYTHON_TOOLING_CONFIG: JsonObject = {
    "contract_version": "1.0",
    "additional_dev_dependencies": [
        "types-PyYAML",
        "pytest-xdist>=3.8",
        "pyright==1.1.411",
    ],
    "ruff": {
        "line_length": 100,
        "extend_exclude": [".claude/hooks", ".codex/hooks", "docs/handoff"],
    },
    "pytest": {
        "fail_under": 85,
        "markers": [
            "compatibility: catalog-derived source and wheel lifecycle rows run in the parallel phase",
            "performance: deterministic scale gates run explicitly in CI",
            "release_replay: disposable release-cut checks run in their own serial phase",
        ],
        "coverage_exclude_also": ["if __name__ == .__main__.:"],
    },
    "coverage": {"parallel": True, "patch": ["subprocess"]},
    "workflow_ownership": "consumer-owned",
}

_DIRECT_WRITER_RUNTIME_PATHS = frozenset(
    {
        "project_standards/adopt/engine.py",
        "project_standards/adopt/manifest.py",
        "project_standards/agent_handoff/cli.py",
        "project_standards/agent_handoff/planning.py",
        "project_standards/agent_handoff/providers.py",
        "project_standards/agent_handoff/validation.py",
        "project_standards/cli.py",
        "project_standards/provider_runner.py",
        "project_standards/standards_graph/catalog.py",
        "project_standards/standards_graph/cli.py",
        "project_standards/standards_graph/discovery.py",
        "project_standards/standards_graph/model.py",
        "project_standards/standards_graph/validators.py",
    }
)

_V5_FALLBACK_RUNTIME_PATHS = frozenset(
    {
        "project_standards/agent_handoff/legacy.py",
        "project_standards/specs/cli.py",
        "project_standards/sync_standards_include.py",
        "project_standards/sync_vscode_colors.py",
        "project_standards/validate_frontmatter.py",
    }
)

GitKnownEntry = tuple[Literal["regular", "symlink"], int, bytes | str]
GitKnownFileTree = dict[str, GitKnownEntry]


@dataclass(frozen=True, slots=True)
class LegacyOverlayPathSets:
    """Separate frozen root authority from live-preserved create-only files."""

    required: frozenset[Path]
    preserved_create_only: frozenset[Path]


@dataclass(frozen=True, slots=True)
class LegacyOverlayEntry:
    """Restore or remove one path while reconstructing the frozen predecessor."""

    path: Path
    state: Literal["file", "absent"]


@dataclass(frozen=True, slots=True)
class GuardedPredecessor:
    """Bind the reviewed dependency state after the release-only version change."""

    pyproject_sha256_after_version: str
    uv_lock_sha256_after_version: str
    vscode_tasks_sha256: str
    vscode_tasks_sha256_after_alignment: str
    vscode_check_task: JsonObject
    dev_group: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LegacyReleaseOverlay:
    """Carry the complete path overlay and its guarded predecessor facts."""

    entries: tuple[LegacyOverlayEntry, ...]
    guarded_predecessor: GuardedPredecessor


@dataclass(frozen=True, slots=True)
class DevGroupAlignment:
    """Record one provider-derived, guarded predecessor-unit transition."""

    source_sha256: str
    before_semantic_digest: str
    after_semantic_digest: str
    rendered_content_digest: str
    mutated: bool


@dataclass(frozen=True, slots=True)
class CheckTaskAlignment:
    """Record one provider-derived, guarded VS Code task transition."""

    source_sha256: str
    post_alignment_sha256: str
    before_semantic_digest: str
    after_semantic_digest: str
    rendered_content_digest: str
    mutated: bool


@dataclass(frozen=True, slots=True)
class ReleaseContentPatch:
    """Bind a canonical binary patch to its ordered name-status ledger."""

    patch: bytes
    ledger: tuple[str, ...]
    patch_sha256: str


def _sha256_value(value: object, *, field: str) -> str:
    assert isinstance(value, str), f"{field} must be a string"
    assert value.startswith("sha256:"), f"{field} must use sha256"
    hexadecimal = value.removeprefix("sha256:")
    assert len(hexadecimal) == 64 and all(
        character in "0123456789abcdef" for character in hexadecimal
    ), f"{field} must be a canonical SHA-256 digest"
    return value


def _overlay_path(value: object) -> Path:
    assert isinstance(value, str), "overlay path must be a string"
    pure = PurePosixPath(value)
    assert value == pure.as_posix(), "overlay path must be canonical POSIX"
    assert value not in {"", "."} and not pure.is_absolute(), (
        "overlay path must be repository-relative"
    )
    assert ".." not in pure.parts and "\\" not in value, "overlay path must be contained"
    assert pure.parts[0] != ".standards", "overlay path must not target .standards state"
    return Path(*pure.parts)


def load_legacy_overlay(
    fixture_root: Path,
    *,
    required_paths: frozenset[Path],
) -> LegacyReleaseOverlay:
    """Load a complete, byte-backed legacy overlay and fail closed on drift."""
    document = cast(
        "dict[str, object]",
        tomllib.loads((fixture_root / "manifest.toml").read_text(encoding="utf-8")),
    )
    assert set(document) == {"schema_version", "guarded_predecessor", "entries"}, (
        "legacy overlay manifest keys changed"
    )
    assert document["schema_version"] == "1.0", "legacy overlay schema changed"

    raw_guard = document["guarded_predecessor"]
    assert isinstance(raw_guard, dict), "guarded predecessor must be a table"
    guard = cast("dict[str, object]", raw_guard)
    assert set(guard) == {
        "pyproject_sha256_after_version",
        "uv_lock_sha256_after_version",
        "vscode_tasks_sha256",
        "vscode_tasks_sha256_after_alignment",
        "vscode_check_task_json",
        "dev_group",
    }, "guarded predecessor keys changed"
    raw_dev_group = guard["dev_group"]
    assert isinstance(raw_dev_group, list), "guarded predecessor dev group must be a string array"
    dev_group_items = cast("list[object]", raw_dev_group)
    assert all(isinstance(item, str) for item in dev_group_items), (
        "guarded predecessor dev group must be a string array"
    )
    raw_check_task = guard["vscode_check_task_json"]
    assert isinstance(raw_check_task, str), (
        "guarded predecessor VS Code check task must be canonical JSON"
    )
    parsed_check_task = json.loads(raw_check_task)
    assert isinstance(parsed_check_task, dict), (
        "guarded predecessor VS Code check task must be an object"
    )
    assert (
        json.dumps(
            parsed_check_task,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        == raw_check_task
    ), "guarded predecessor VS Code check task must be canonical JSON"
    guarded_predecessor = GuardedPredecessor(
        pyproject_sha256_after_version=_sha256_value(
            guard["pyproject_sha256_after_version"],
            field="guarded_predecessor.pyproject_sha256_after_version",
        ),
        uv_lock_sha256_after_version=_sha256_value(
            guard["uv_lock_sha256_after_version"],
            field="guarded_predecessor.uv_lock_sha256_after_version",
        ),
        vscode_tasks_sha256=_sha256_value(
            guard["vscode_tasks_sha256"],
            field="guarded_predecessor.vscode_tasks_sha256",
        ),
        vscode_tasks_sha256_after_alignment=_sha256_value(
            guard["vscode_tasks_sha256_after_alignment"],
            field="guarded_predecessor.vscode_tasks_sha256_after_alignment",
        ),
        vscode_check_task=cast("JsonObject", parsed_check_task),
        dev_group=tuple(cast("list[str]", dev_group_items)),
    )

    raw_entries = document["entries"]
    assert isinstance(raw_entries, list), "legacy overlay entries must be an array"
    entries: list[LegacyOverlayEntry] = []
    for raw_entry in cast("list[object]", raw_entries):
        assert isinstance(raw_entry, dict), "legacy overlay entry must be a table"
        entry = cast("dict[str, object]", raw_entry)
        assert set(entry) == {"path", "state"}, "legacy overlay entry keys changed"
        path = _overlay_path(entry["path"])
        state = entry["state"]
        assert state in {"file", "absent"}, "legacy overlay state changed"
        entries.append(
            LegacyOverlayEntry(
                path=path,
                state=cast("Literal['file', 'absent']", state),
            )
        )

    paths = tuple(entry.path for entry in entries)
    assert len(paths) == len(set(paths)), "legacy overlay contains duplicate paths"
    assert paths == tuple(sorted(paths, key=lambda path: path.as_posix().encode("utf-8"))), (
        "legacy overlay paths must be bytewise sorted"
    )
    observed_paths = frozenset(paths)
    assert observed_paths == required_paths, (
        "legacy overlay path set changed: "
        f"missing={sorted(path.as_posix() for path in required_paths - observed_paths)!r} "
        f"extra={sorted(path.as_posix() for path in observed_paths - required_paths)!r}"
    )

    files_root = fixture_root / "files"
    assert files_root.is_dir() and not files_root.is_symlink(), (
        "legacy overlay files root is unavailable"
    )
    expected_files = frozenset(entry.path for entry in entries if entry.state == "file")
    actual_files: set[Path] = set()
    for source in files_root.rglob("*"):
        relative = source.relative_to(files_root)
        # A root Ruff gate treats the frozen pyproject as a nested project and may
        # emit this ignored cache inside the fixture before release tests execute.
        if ".ruff_cache" in relative.parts:
            continue
        assert not source.is_symlink(), "legacy overlay file payload must not be a symlink"
        if source.is_dir():
            continue
        assert source.is_file(), "legacy overlay file payload must be regular"
        actual_files.add(relative)
    assert actual_files == expected_files, (
        "declared overlay file is unavailable or the file inventory has extra bytes: "
        f"missing={sorted(path.as_posix() for path in expected_files - actual_files)!r} "
        f"extra={sorted(path.as_posix() for path in actual_files - expected_files)!r}"
    )
    return LegacyReleaseOverlay(
        entries=tuple(entries),
        guarded_predecessor=guarded_predecessor,
    )


def _git_environment() -> dict[str, str]:
    """Keep release Git operations independent of ambient repository state."""
    environment = {
        key: os.environ[key]
        for key in ("HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH", "TMPDIR", "TZ")
        if key in os.environ
    }
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _git(checkout: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=checkout,
        env=_git_environment(),
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


def resolve_release_replay_source_root(
    default_root: Path = _ROOT,
    *,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve and authenticate Task 11's immutable pre-atomic source tree."""
    values = os.environ if environment is None else environment
    raw_override = values.get("RELEASE_REPLAY_SOURCE_ROOT")
    if raw_override is None:
        return default_root
    override = Path(raw_override)
    if (
        not override.is_absolute()
        or not override.is_dir()
        or override.is_symlink()
        or override.resolve() != override
        or override.resolve() == default_root.resolve()
    ):
        raise AssertionError("release replay override must be a distinct absolute directory")
    git_directory = override / ".git"
    if not git_directory.is_dir() or git_directory.is_symlink():
        raise AssertionError("release replay override must be an independent Git repository")
    try:
        top_level = Path(_git(override, "rev-parse", "--show-toplevel").decode().strip())
        common_directory = Path(_git(override, "rev-parse", "--git-common-dir").decode().strip())
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            "release replay override must be a self-contained Git repository"
        ) from exc
    if not common_directory.is_absolute():
        common_directory = override / common_directory
    if top_level.resolve() != override or common_directory.resolve() != git_directory:
        raise AssertionError("release replay override must own its repository metadata")
    alternates = git_directory / "objects/info/alternates"
    if alternates.is_symlink() or (alternates.exists() and alternates.read_bytes().strip()):
        raise AssertionError("release replay override must not borrow mutable Git objects")
    try:
        _git(override, "fsck", "--full", "--no-dangling")
        if _git(override, "status", "--porcelain=v1", "--untracked-files=all"):
            raise AssertionError("release replay override must be clean")
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            "release replay override must be a self-contained Git repository"
        ) from exc
    pre_atomic_head = values.get("PRE_ATOMIC_HEAD")
    if (
        pre_atomic_head is None
        or len(pre_atomic_head) not in {40, 64}
        or pre_atomic_head != pre_atomic_head.lower()
        or any(character not in "0123456789abcdef" for character in pre_atomic_head)
    ):
        raise AssertionError("PRE_ATOMIC_HEAD must be one full canonical object ID")
    expected_tree = _git(
        default_root,
        "rev-parse",
        "--verify",
        f"{pre_atomic_head}^{{tree}}",
    ).strip()
    actual_tree = _git(override, "rev-parse", "--verify", "HEAD^{tree}").strip()
    if actual_tree != expected_tree:
        raise AssertionError("release replay override tree differs from PRE_ATOMIC_HEAD")
    return override


def _git_known_worktree_paths(source_root: Path) -> tuple[Path, ...]:
    output = _git(
        source_root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    return tuple(
        sorted(
            (Path(raw.decode("utf-8")) for raw in output.split(b"\0") if raw),
            key=lambda path: path.as_posix().encode("utf-8"),
        )
    )


def git_known_file_tree(
    root: Path,
    *,
    excluded_paths: frozenset[Path] = frozenset(),
) -> GitKnownFileTree:
    """Snapshot Git-known current files with modes and symlink identities."""
    tree: dict[str, tuple[Literal["regular", "symlink"], int, bytes | str]] = {}
    for relative in _git_known_worktree_paths(root):
        if relative in excluded_paths:
            continue
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            tree[relative.as_posix()] = ("symlink", mode, path.readlink().as_posix())
        elif stat.S_ISREG(metadata.st_mode):
            tree[relative.as_posix()] = ("regular", mode, path.read_bytes())
        else:
            raise AssertionError(f"Git-known path is not a regular file or symlink: {relative}")
    return tree


def release_input_digest(source_root: Path = _ROOT) -> str:
    """Hash every copied release input except the self-referential evidence file."""
    digest = sha256()
    digest.update(b"project-standards-release-input-v2\0")
    for relative in _git_known_worktree_paths(source_root):
        if relative == _RELEASE_EVIDENCE:
            continue
        source = source_root / relative
        if not source.exists() and not source.is_symlink():
            continue
        metadata = source.lstat()
        if source.is_symlink():
            kind = b"symlink"
            content = source.readlink().as_posix().encode("utf-8")
        else:
            kind = b"regular"
            content = source.read_bytes()
        for field in (
            relative.as_posix().encode("utf-8"),
            f"{metadata.st_mode:o}".encode("ascii"),
            kind,
            content,
        ):
            digest.update(len(field).to_bytes(8, "big"))
            digest.update(field)
    return digest.hexdigest()


def _is_sha256(value: object, *, prefixed: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.removeprefix("sha256:") if prefixed else value
    if prefixed and raw == value:
        return False
    return (
        len(raw) == 64
        and raw == raw.lower()
        and all(character in "0123456789abcdef" for character in raw)
    )


def load_release_evidence_record(source_root: Path = _ROOT) -> JsonObject:
    """Load the single machine-readable migration record from retained evidence."""
    evidence = (source_root / _RELEASE_EVIDENCE).read_text(encoding="utf-8")
    if (
        evidence.count(_RELEASE_EVIDENCE_RECORD_BEGIN) != 1
        or evidence.count(_RELEASE_EVIDENCE_RECORD_END) != 1
    ):
        raise AssertionError("release evidence must contain one migration record")
    section = evidence.split(_RELEASE_EVIDENCE_RECORD_BEGIN, 1)[1].split(
        _RELEASE_EVIDENCE_RECORD_END,
        1,
    )[0]
    if not section.startswith("```json\n") or not section.endswith("```\n"):
        raise AssertionError("release evidence migration record must be one JSON fence")
    try:
        raw_record: object = json.loads(section.removeprefix("```json\n").removesuffix("```\n"))
    except json.JSONDecodeError as exc:
        raise AssertionError("release evidence migration record is invalid JSON") from exc
    if not isinstance(raw_record, dict):
        raise AssertionError("release evidence migration record must be a JSON object")
    untyped_record = cast(dict[object, object], raw_record)
    if not all(isinstance(key, str) for key in untyped_record):
        raise AssertionError("release evidence migration record keys must be strings")
    record = cast(JsonObject, untyped_record)
    if (
        set(record)
        != {
            "schema_version",
            "release_input_sha256",
            "migration_patch_sha256",
            "migration_ledger",
            "control_plane_sha256",
            "dev_group_alignment",
            "check_task_alignment",
        }
        or record["schema_version"] != 1
    ):
        raise AssertionError("release evidence migration record has unexpected fields")
    if not _is_sha256(record["release_input_sha256"]) or not _is_sha256(
        record["migration_patch_sha256"]
    ):
        raise AssertionError("release evidence migration record has an invalid digest")
    ledger = record["migration_ledger"]
    if (
        not isinstance(ledger, list)
        or not ledger
        or not all(
            isinstance(row, str)
            and len(parts := row.split("\t")) == 2
            and parts[0] in {"A", "D", "M", "T"}
            and bool(parts[1])
            for row in ledger
        )
    ):
        raise AssertionError("release evidence migration ledger is invalid")
    control = record["control_plane_sha256"]
    if (
        not isinstance(control, dict)
        or set(control) != {"catalog.toml", "config.toml", "lock.toml"}
        or not all(_is_sha256(value) for value in control.values())
    ):
        raise AssertionError("release evidence control-plane digests are invalid")
    expected_alignment_fields = {
        "source_sha256",
        "before_semantic_digest",
        "after_semantic_digest",
        "rendered_content_digest",
        "mutated",
    }
    for field in ("dev_group_alignment", "check_task_alignment"):
        alignment = record[field]
        expected_fields = set(expected_alignment_fields)
        if field == "check_task_alignment":
            expected_fields.add("post_alignment_sha256")
        if (
            not isinstance(alignment, dict)
            or set(alignment) != expected_fields
            or alignment["mutated"] is not True
            or not all(
                _is_sha256(value, prefixed=True)
                for key, value in alignment.items()
                if key != "mutated"
            )
        ):
            raise AssertionError(f"release evidence {field} is invalid")
    return record


def assert_release_evidence_current(
    source_root: Path = _ROOT,
    *,
    expected_record: Mapping[str, object] | None = None,
) -> None:
    """Bind retained prose and its record to current inputs and executed proof."""
    digest = release_input_digest(source_root)
    expected = f"Release-input SHA-256: `{digest}`"
    evidence = (source_root / _RELEASE_EVIDENCE).read_text(encoding="utf-8")
    assert expected in evidence, (
        f"release evidence is stale; refresh the disposable proof for release-input digest {digest}"
    )
    record = load_release_evidence_record(source_root)
    assert record["release_input_sha256"] == digest, (
        "release evidence migration record has a stale release-input digest"
    )
    if expected_record is not None:
        assert record == expected_record, (
            "release evidence migration record differs from the executed proof"
        )


def copy_tracked_checkout(target: Path, *, source_root: Path = _ROOT) -> Path:
    """Copy Git-known working-tree paths, preserving symlink identities.

    Include non-ignored additions and omit tracked deletions so pre-commit release
    verification exercises the tree that would be committed, not the stale index.
    """
    for relative in _git_known_worktree_paths(source_root):
        source = source_root / relative
        if not source.exists() and not source.is_symlink():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(source.readlink())
        else:
            shutil.copy2(source, destination)
    return target


def derive_legacy_overlay_path_sets(source_root: Path) -> LegacyOverlayPathSets:
    """Derive the frozen and live-preserved root sets from catalog-5 declarations."""
    repository = build_package_repository(source_root, catalog_major=5)
    assert repository.findings == (), "catalog-5 package source is invalid"
    assert repository.catalog is not None, "catalog 5 is unavailable"
    selected = {(entry.id, entry.version.value) for entry in repository.catalog.packages}
    legacy_targets: set[Path] = set()
    policies_by_target: dict[Path, set[ArtifactPolicy]] = {}
    for loaded in repository.payloads:
        manifest = loaded.manifest
        if (
            loaded.manifest.payload.standard,
            loaded.manifest.payload.version.value,
        ) not in selected:
            continue
        for signature in manifest.legacy_signatures:
            legacy_targets.update(Path(*target.normalized.parts) for target in signature.targets)
        for declaration in (*manifest.artifacts, *manifest.contributions):
            target = Path(*declaration.target.normalized.parts)
            if target.parts[0] == ".standards":
                continue
            policies_by_target.setdefault(target, set()).add(declaration.policy)

    pinned = {
        Path(".project-standards.yml"),
        Path("pyproject.toml"),
        Path("uv.lock"),
    }
    assert not any(path.parts[0] == ".standards" for path in legacy_targets | pinned), (
        "legacy overlay contract cannot target .standards state"
    )
    non_create_only = {
        target
        for target, policies in policies_by_target.items()
        if any(policy is not ArtifactPolicy.CREATE_ONLY for policy in policies)
    }
    required = frozenset(legacy_targets | non_create_only | pinned)
    preserved_create_only = frozenset(
        target
        for target, policies in policies_by_target.items()
        if policies == {ArtifactPolicy.CREATE_ONLY} and target not in required
    )
    return LegacyOverlayPathSets(
        required=required,
        preserved_create_only=preserved_create_only,
    )


def snapshot_regular_files(root: Path, paths: frozenset[Path]) -> dict[Path, bytes]:
    """Snapshot required regular files without following symlinks."""
    snapshot: dict[Path, bytes] = {}
    for relative in sorted(paths, key=lambda path: path.as_posix().encode("utf-8")):
        assert not relative.is_absolute() and ".." not in relative.parts, (
            "live-preserved path must be repository-relative"
        )
        path = root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError as exc:
            raise AssertionError(
                f"live-preserved target must be a regular file: {relative}"
            ) from exc
        assert stat.S_ISREG(metadata.st_mode), (
            f"live-preserved target must be a regular file: {relative}"
        )
        snapshot[relative] = path.read_bytes()
    return snapshot


def prepare_legacy_release_checkout(source_root: Path, target: Path) -> Path:
    """Reconstruct the frozen pre-intent release authority in a disposable tree."""
    path_sets = derive_legacy_overlay_path_sets(source_root)
    snapshot_regular_files(source_root, path_sets.preserved_create_only)
    checkout = copy_tracked_checkout(target, source_root=source_root)
    standards_state = checkout / ".standards"
    if standards_state.is_symlink() or standards_state.is_file():
        standards_state.unlink()
    else:
        shutil.rmtree(standards_state, ignore_errors=True)

    fixture_root = source_root / _LEGACY_RELEASE_FIXTURE
    overlay = load_legacy_overlay(
        fixture_root,
        required_paths=path_sets.required,
    )
    for entry in overlay.entries:
        destination = checkout / entry.path
        if destination.is_dir() and not destination.is_symlink():
            raise AssertionError(f"legacy overlay target became a directory: {entry.path}")
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        if entry.state == "file":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fixture_root / "files" / entry.path, destination)
    return checkout


def initialize_release_baseline(checkout: Path) -> None:
    """Create a local baseline so the exact release patch can be hashed and replayed."""
    _git(checkout, "init", "--quiet")
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=Release Evidence",
        "-c",
        "user.email=168346341+chrisdpurcell@users.noreply.github.com",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--quiet",
        "-m",
        "tracked baseline",
    )


def mirror_release_tree(source: Path, baseline: Path) -> None:
    """Overlay only one completed tree's Git-known authority onto a baseline."""
    source_files = {
        relative
        for relative in _git_known_worktree_paths(source)
        if (source / relative).exists() or (source / relative).is_symlink()
    }
    baseline_files = {
        relative
        for relative in _git_known_worktree_paths(baseline)
        if (baseline / relative).exists() or (baseline / relative).is_symlink()
    }
    for relative in sorted(
        baseline_files - source_files,
        key=lambda item: item.as_posix().encode("utf-8"),
    ):
        path = baseline / relative
        if path.is_dir() and not path.is_symlink():
            raise AssertionError(f"baseline Git-known path became a directory: {relative}")
        path.unlink()
    for relative in sorted(source_files, key=lambda item: item.as_posix().encode("utf-8")):
        source_path = source / relative
        target = baseline / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir() and not target.is_symlink():
            raise AssertionError(f"baseline target became a directory: {relative}")
        if target.exists() or target.is_symlink():
            target.unlink()
        if source_path.is_symlink():
            target.symlink_to(source_path.readlink())
        else:
            shutil.copy2(source_path, target)


def set_release_version(checkout: Path, version: str = "5.0.0") -> None:
    """Set only the disposable checkout's package and root lock version."""
    replacements = (
        (checkout / "pyproject.toml", 'version = "4.3.0"', f'version = "{version}"'),
        (checkout / "uv.lock", 'version = "4.3.0"', f'version = "{version}"'),
    )
    for path, before, after in replacements:
        content = path.read_text(encoding="utf-8")
        if before in content:
            assert content.count(before) == 1 and after not in content, path
            path.write_text(content.replace(before, after), encoding="utf-8")
        else:
            assert content.count(after) == 1, path


def declare_release_cut_intent(checkout: Path) -> None:
    """Inject sparse V5 owner intent without changing the guarded TOML input."""
    legacy = checkout / ".project-standards.yml"
    content = legacy.read_text(encoding="utf-8")
    anchor = 'python_tooling:\n  version: "1.0"\n'
    assert content.count(anchor) == 1, "legacy Python Tooling intent anchor changed"
    legacy_options = {
        ("version" if key == "contract_version" else key): value
        for key, value in RELEASE_PYTHON_TOOLING_CONFIG.items()
    }
    replacement = yaml.safe_dump(
        {"python_tooling": legacy_options},
        sort_keys=False,
        width=1000,
    )
    legacy.write_text(content.replace(anchor, replacement), encoding="utf-8")


def prealign_release_dev_group(
    checkout: Path,
    distribution: InstalledDistribution,
    sparse_config: JsonObject,
    *,
    expected_source_sha256: str,
    expected_dev_group: tuple[str, ...],
) -> DevGroupAlignment:
    """Render and apply one installed-provider dev-group update after strict guards."""
    path = checkout / "pyproject.toml"
    source = path.read_bytes()
    source_sha256 = f"sha256:{sha256(source).hexdigest()}"
    if source_sha256 != expected_source_sha256:
        raise AssertionError("guarded predecessor pyproject digest changed")

    adapter = TomlAdapter()
    scope = "key:/dependency-groups/dev"
    state = adapter.inspect(source, (scope,))
    if len(state.units) != 1:
        raise AssertionError("guarded predecessor dev group is absent")
    existing = state.units[0]
    if not isinstance(existing.value, list) or tuple(existing.value) != expected_dev_group:
        raise AssertionError("guarded predecessor dev group changed")

    catalog = distribution.load_catalog("5")
    payload = catalog.payload_map[("python-tooling", "1.1")]
    if not payload.root.is_relative_to(distribution.package_root):
        raise AssertionError("release rendering did not use the installed distribution")
    effective_config = load_option_schema(payload.root, payload.manifest).resolve_options(
        sparse_config
    )
    contributions = [
        contribution
        for contribution in payload.manifest.contributions
        if contribution.target.original == "pyproject.toml" and contribution.scope == scope
    ]
    if len(contributions) != 1:
        raise AssertionError("installed payload does not declare exactly one dev-group unit")
    contribution = contributions[0]
    if contribution.provider != "render-semantic":
        raise AssertionError("installed dev-group unit changed its rendering provider")
    result = invoke_provider(
        ProviderInvocation(
            repo=checkout,
            payload=payload,
            standard_id=payload.manifest.payload.standard,
            version=payload.manifest.payload.version,
            provider_id=contribution.provider,
            operation=ProviderOperation.RENDER,
            effective_config=effective_config,
            snapshots={
                "planned_contribution": {
                    "id": contribution.id,
                    "target": contribution.target.original,
                    "adapter": contribution.adapter.value,
                    "scope": contribution.scope,
                }
            },
        )
    )
    if result.effect is not ProviderEffect.CONTENT or result.content is None:
        raise AssertionError("installed provider did not render the dev group")
    rendered = adapter.inspect(result.content, (scope,))
    if len(rendered.units) != 1:
        raise AssertionError("installed provider rendered an invalid dev-group fragment")
    desired = rendered.units[0]
    updated = adapter.render(
        state,
        (
            UnitChange(
                kind=ActionKind.UPDATE,
                scope=scope,
                content=desired.raw,
                value=desired.value,
            ),
        ),
    )

    before_document = cast("dict[str, object]", tomllib.loads(source.decode("utf-8")))
    after_document = cast("dict[str, object]", tomllib.loads(updated.decode("utf-8")))
    before_groups = before_document.get("dependency-groups")
    after_groups = after_document.get("dependency-groups")
    if not isinstance(before_groups, dict) or not isinstance(after_groups, dict):
        raise AssertionError("guarded rewrite lost the dependency-groups table")
    cast("dict[str, object]", before_groups).pop("dev", None)
    cast("dict[str, object]", after_groups).pop("dev", None)
    if before_document != after_document:
        raise AssertionError("guarded rewrite changed content outside the dev group")
    if updated == source:
        raise AssertionError("guarded predecessor was already aligned")

    final_state = adapter.inspect(updated, (scope,))
    if len(final_state.units) != 1:
        raise AssertionError("guarded rewrite lost the dev group")
    path.write_bytes(updated)
    return DevGroupAlignment(
        source_sha256=source_sha256,
        before_semantic_digest=existing.semantic_digest.value,
        after_semantic_digest=final_state.units[0].semantic_digest.value,
        rendered_content_digest=f"sha256:{sha256(result.content).hexdigest()}",
        mutated=True,
    )


def _without_check_task(content: bytes) -> JsonObject:
    document = container_value_without_comments(content, AdapterKind.JSONC)
    if not isinstance(document, dict):
        raise AssertionError("guarded tasks container must be comment-free JSONC object")
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or not all(isinstance(task, dict) for task in tasks):
        raise AssertionError("guarded tasks container must contain task objects")
    task_objects = cast("list[JsonObject]", tasks)
    check_tasks = [task for task in task_objects if task.get("label") == "check"]
    if len(check_tasks) != 1:
        raise AssertionError("guarded tasks container must contain exactly one check task")
    return {
        **document,
        "tasks": [task for task in task_objects if task.get("label") != "check"],
    }


def prealign_release_check_task(
    checkout: Path,
    distribution: InstalledDistribution,
    sparse_config: JsonObject,
    *,
    expected_source_sha256: str,
    expected_check_task: JsonObject,
    expected_post_alignment_sha256: str,
) -> CheckTaskAlignment:
    """Render and apply one installed-provider task update after strict guards."""
    path = checkout / ".vscode/tasks.json"
    source = path.read_bytes()
    source_sha256 = f"sha256:{sha256(source).hexdigest()}"
    if source_sha256 != expected_source_sha256:
        raise AssertionError("guarded predecessor tasks digest changed")

    adapter = JsoncAdapter()
    scope = "keyed-set:/tasks#label=check"
    state = adapter.inspect(source, (scope,))
    if len(state.units) != 1:
        raise AssertionError("guarded predecessor check task is absent")
    existing = state.units[0]
    if existing.value != expected_check_task:
        raise AssertionError("guarded predecessor check task changed")

    catalog = distribution.load_catalog("5")
    payload = catalog.payload_map[("python-tooling", "1.1")]
    if not payload.root.is_relative_to(distribution.package_root):
        raise AssertionError("release rendering did not use the installed distribution")
    effective_config = load_option_schema(payload.root, payload.manifest).resolve_options(
        sparse_config
    )
    contributions = [
        contribution
        for contribution in payload.manifest.contributions
        if contribution.id == "vscode-task-check"
        and contribution.target.original == ".vscode/tasks.json"
        and contribution.scope == scope
    ]
    if len(contributions) != 1:
        raise AssertionError("installed payload does not declare exactly one check task unit")
    contribution = contributions[0]
    if contribution.provider != "render-semantic":
        raise AssertionError("installed check task unit changed its rendering provider")
    result = invoke_provider(
        ProviderInvocation(
            repo=checkout,
            payload=payload,
            standard_id=payload.manifest.payload.standard,
            version=payload.manifest.payload.version,
            provider_id=contribution.provider,
            operation=ProviderOperation.RENDER,
            effective_config=effective_config,
            snapshots={
                "planned_contribution": {
                    "id": contribution.id,
                    "target": contribution.target.original,
                    "adapter": contribution.adapter.value,
                    "scope": contribution.scope,
                }
            },
        )
    )
    if result.effect is not ProviderEffect.CONTENT or result.content is None:
        raise AssertionError("installed provider did not render the check task")
    rendered = adapter.inspect(result.content, (scope,))
    if len(rendered.units) != 1:
        raise AssertionError("installed provider rendered an invalid check task fragment")
    desired = rendered.units[0]
    updated = adapter.render(
        state,
        (
            UnitChange(
                kind=ActionKind.UPDATE,
                scope=scope,
                content=desired.raw,
                value=desired.value,
            ),
        ),
    )

    if _without_check_task(source) != _without_check_task(updated):
        raise AssertionError("guarded rewrite changed content outside the check task")
    if updated == source:
        raise AssertionError("guarded predecessor check task was already aligned")
    post_alignment_sha256 = f"sha256:{sha256(updated).hexdigest()}"
    if post_alignment_sha256 != expected_post_alignment_sha256:
        raise AssertionError("guarded check task post-alignment digest changed")
    final_state = adapter.inspect(updated, (scope,))
    if len(final_state.units) != 1:
        raise AssertionError("guarded rewrite lost the check task")
    if final_state.units[0].semantic_digest != desired.semantic_digest:
        raise AssertionError("guarded rewrite changed the provider-rendered check task")

    path.write_bytes(updated)
    return CheckTaskAlignment(
        source_sha256=source_sha256,
        post_alignment_sha256=post_alignment_sha256,
        before_semantic_digest=existing.semantic_digest.value,
        after_semantic_digest=desired.semantic_digest.value,
        rendered_content_digest=f"sha256:{sha256(result.content).hexdigest()}",
        mutated=True,
    )


def build_installed_release(checkout: Path, target: Path) -> Path:
    """Build one offline wheel and extract its importable installed tree."""
    output = target / "dist"
    subprocess.run(
        ["uv", "build", "--offline", "--wheel", "--out-dir", str(output)],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    (wheel,) = output.glob("*.whl")
    installed = target / "installed"
    extract_pure_python_wheel(wheel, installed)
    return installed


def release_patch(checkout: Path) -> ReleaseContentPatch:
    """Return the migration patch with binary bytes and exact path identities."""
    _git(checkout, "add", "--intent-to-add", ".")
    patch = _git(
        checkout,
        "diff",
        "--binary",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "HEAD",
        "--",
        ".",
    )
    ledger = tuple(
        line.decode("utf-8")
        for line in _git(
            checkout,
            "diff",
            "--name-status",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "HEAD",
            "--",
            ".",
        ).splitlines()
    )
    return ReleaseContentPatch(
        patch=patch,
        ledger=ledger,
        patch_sha256=sha256(patch).hexdigest(),
    )


def materialize_git_object_tree(repo: Path, commit: str, target: Path) -> None:
    """Create an independent committed repository with one exact Git tree."""
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise AssertionError("Git object-tree target must be empty")
    listing = _git(repo, "ls-tree", "-rz", "--full-tree", commit)
    _git(target, "init", "--quiet")
    for raw_entry in listing.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        mode, object_type, raw_object_id = metadata.split(b" ", 2)
        if object_type != b"blob" or mode not in {b"100644", b"100755", b"120000"}:
            raise AssertionError("release predecessor contains an unsupported Git entry")
        relative_text = raw_path.decode("utf-8")
        relative_pure = PurePosixPath(relative_text)
        if (
            relative_text != relative_pure.as_posix()
            or relative_pure.is_absolute()
            or ".." in relative_pure.parts
            or not relative_pure.parts
            or relative_pure.parts[0] == ".git"
        ):
            raise AssertionError("release predecessor contains an unsafe Git path")
        relative = Path(*relative_pure.parts)
        content = _git(repo, "cat-file", "blob", raw_object_id.decode("ascii"))
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if mode == b"120000":
            destination.symlink_to(content.decode("utf-8"))
        else:
            destination.write_bytes(content)
            destination.chmod(0o755 if mode == b"100755" else 0o644)
        materialized_object_id = _git(
            target,
            "hash-object",
            "-w",
            "--stdin",
            input_bytes=content,
        ).strip()
        if materialized_object_id != raw_object_id:
            raise AssertionError("materialized Git blob differs from predecessor authority")
        _git(
            target,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{mode.decode('ascii')},{raw_object_id.decode('ascii')},{relative_text}",
        )
    _git(
        target,
        "-c",
        "user.name=Release Evidence",
        "-c",
        "user.email=168346341+chrisdpurcell@users.noreply.github.com",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "materialized predecessor authority",
    )
    source_tree = _git(repo, "rev-parse", f"{commit}^{{tree}}").strip()
    target_tree = _git(target, "rev-parse", "HEAD^{tree}").strip()
    if target_tree != source_tree:
        raise AssertionError("materialized predecessor tree object changed")
    if _git(target, "ls-tree", "-rz", "--full-tree", "HEAD") != listing:
        raise AssertionError("materialized predecessor tree entries changed")
    _git(target, "fsck", "--full", "--no-dangling")
    if _git(target, "status", "--porcelain=v1"):
        raise AssertionError("materialized predecessor repository is dirty")


def canonical_release_diff(
    repo: Path,
    before: str,
    after: str | None = None,
) -> ReleaseContentPatch:
    """Derive release content with fixed diff behavior and one evidence exclusion."""
    references = (before,) if after is None else (before, after)
    pathspec = (".", f":(exclude){_RELEASE_EVIDENCE.as_posix()}")
    common = (
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "--no-color",
        "--no-relative",
        "--full-index",
        "--unified=3",
        "--inter-hunk-context=0",
        "--diff-algorithm=myers",
        "--no-indent-heuristic",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "--line-prefix=",
        "--output-indicator-new=+",
        "--output-indicator-old=-",
        "--output-indicator-context= ",
        "--ita-visible-in-index",
        "--ignore-submodules=none",
        "-O/dev/null",
        *references,
        "--",
        *pathspec,
    )
    patch = _git(repo, "-c", "core.quotePath=true", "diff", "--binary", *common)
    ledger = tuple(
        line.decode("utf-8")
        for line in _git(
            repo,
            "-c",
            "core.quotePath=true",
            "diff",
            "--name-status",
            *common,
        ).splitlines()
    )
    return ReleaseContentPatch(
        patch=patch,
        ledger=ledger,
        patch_sha256=sha256(patch).hexdigest(),
    )


def complete_release_content_patch(
    predecessor: Path,
    final_root: Path,
) -> ReleaseContentPatch:
    """Prove the final Git-known tree by canonical patch and fresh replay."""
    if _git(predecessor, "status", "--porcelain=v1"):
        raise AssertionError("release predecessor authority must be clean")
    with tempfile.TemporaryDirectory(prefix="project-standards-release-") as temporary:
        temporary_root = Path(temporary)
        scratch = Path(shutil.copytree(predecessor, temporary_root / "scratch", symlinks=True))
        if _git(scratch, "diff", "--quiet", "HEAD", "--"):
            raise AssertionError("release scratch index differs from predecessor HEAD")
        mirror_release_tree(final_root, scratch)
        _git(scratch, "add", "--intent-to-add", "--", ".")
        result = canonical_release_diff(scratch, "HEAD")

        replay = Path(shutil.copytree(predecessor, temporary_root / "replay", symlinks=True))
        replay_release_patch(replay, result.patch)
        excluded = frozenset({_RELEASE_EVIDENCE})
        if git_known_file_tree(replay, excluded_paths=excluded) != git_known_file_tree(
            final_root,
            excluded_paths=excluded,
        ):
            raise AssertionError("complete release patch does not replay to the final tree")
        return result


def replay_release_patch(baseline: Path, patch: bytes) -> None:
    """Apply the reviewed patch to a fresh tracked baseline."""
    if not patch:
        return
    _git(baseline, "apply", "--binary", "-", input_bytes=patch)


def classify_legacy_dependencies(root: Path) -> dict[str, tuple[str, ...]]:
    """Classify every retained legacy-authority reference in a tracked or installed tree."""
    tokens = (
        b".project-standards.yml",
        b"adopt.toml",
        b".agents/agent-handoff/manifest.json",
        b"project_standards/bundles",
        b"project_standards.adopt",
        b"apply_adoption(",
        b"execute_plan(",
    )
    classified: dict[str, list[str]] = {
        "migration-runtime": [],
        "direct-writer-runtime": [],
        "v5-fallback-runtime": [],
        "historical-or-test": [],
        "unclassified": [],
    }
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if (
            not path.is_file()
            or path.is_symlink()
            or ".git" in relative_path.parts
            or "__pycache__" in relative_path.parts
        ):
            continue
        try:
            content = path.read_bytes()
        except OSError:
            continue
        relative = relative_path.as_posix()
        normalized = relative.removeprefix("src/")
        is_v1_family_index = normalized.startswith(
            "project_standards/bundles/"
        ) and normalized.endswith("/standard.toml")
        if not is_v1_family_index and not any(token in content for token in tokens):
            continue
        module_relative = normalized.removeprefix("project_standards/")
        if module_relative.startswith("control_plane/"):
            category = "migration-runtime"
        elif normalized in _DIRECT_WRITER_RUNTIME_PATHS:
            category = "direct-writer-runtime"
        elif (
            normalized in _V5_FALLBACK_RUNTIME_PATHS
            or normalized.startswith("project_standards/bundles/")
            or relative.startswith("scripts/")
        ):
            category = "v5-fallback-runtime"
        elif (
            relative.startswith(("tests/", "docs/", "standards/", "meta/"))
            or normalized.startswith(("project_standards/families/", "project_standards/payloads/"))
            or normalized == "project_standards/README.md"
            or ("/" not in relative and relative.endswith((".md", ".jsonc")))
            or ".dist-info/" in relative
        ):
            category = "historical-or-test"
        else:
            category = "unclassified"
        classified[category].append(relative)
    return {key: tuple(sorted(values, key=str.encode)) for key, values in classified.items()}
