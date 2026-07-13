from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tomllib
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from project_standards.control_plane.adapters import MarkdownBlockAdapter
from project_standards.control_plane.codec import parse_config, parse_lock
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.migration import (
    plan_legacy_migration,
    render_migration_report,
)
from project_standards.control_plane.models import LockedUnit
from project_standards.package_contract.payload import ArtifactPolicy
from project_standards.package_contract.repository import build_package_repository
from tests.package_compatibility import release_candidate as release_candidate_helpers
from tests.package_compatibility.release_candidate import (
    build_installed_release,
    classify_legacy_dependencies,
    copy_tracked_checkout,
    declare_release_cut_intent,
    initialize_release_baseline,
    mirror_release_tree,
    release_patch,
    replay_release_patch,
    set_release_version,
)

pytestmark = pytest.mark.release_replay

_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_RELEASE_FIXTURE = _ROOT / "tests/fixtures/package_compatibility/legacy/release-root"

_EXPECTED_DIRECT_WRITER_MODULES = (
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
)


@dataclass(frozen=True, slots=True)
class _ReconstructedPredecessor:
    root: Path = field(compare=False, repr=False)
    tree: release_candidate_helpers.GitKnownFileTree
    overlay: release_candidate_helpers.LegacyReleaseOverlay
    preserved_create_only: dict[Path, bytes]


@dataclass(frozen=True, slots=True)
class _ControlPlaneDigests:
    config: str
    catalog: str
    lock: str


@dataclass(frozen=True, slots=True)
class _MigrationProofResult:
    completed_authority: Path = field(compare=False, repr=False)
    completed_tree: release_candidate_helpers.GitKnownFileTree
    dev_group_alignment: release_candidate_helpers.DevGroupAlignment
    check_task_alignment: release_candidate_helpers.CheckTaskAlignment
    dev_group_lock: LockedUnit
    check_task_lock: LockedUnit
    migration_patch: release_candidate_helpers.ReleaseContentPatch
    digests: _ControlPlaneDigests


def _file_tree(root: Path) -> dict[str, tuple[str, int, bytes | str]]:
    result: dict[str, tuple[str, int, bytes | str]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            result[relative.as_posix()] = ("symlink", mode, path.readlink().as_posix())
        elif stat.S_ISREG(metadata.st_mode):
            result[relative.as_posix()] = ("regular", mode, path.read_bytes())
    return result


def _instruction_residual_without_legacy_handoff_block(content: bytes) -> bytes:
    begin_line = b"<!-- BEGIN agent-handoff managed instructions -->\n"
    end_line = b"<!-- END agent-handoff managed instructions -->\n"
    assert content.count(begin_line) == 1
    assert content.count(end_line) == 1
    start = content.index(begin_line)
    end = content.index(end_line, start) + len(end_line)
    return content[:start] + content[end:]


def _release_subprocess_environment(*, pythonpath: Path | None = None) -> dict[str, str]:
    """Pass only tool/runtime settings, never unrelated credentials, into release probes."""
    allowed = (
        "HOME",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "NO_PROXY",
        "PATH",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TMPDIR",
        "TZ",
        "UV_CACHE_DIR",
        "XDG_CACHE_HOME",
        "https_proxy",
        "http_proxy",
        "no_proxy",
    )
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    if pythonpath is not None:
        environment["PYTHONPATH"] = str(pythonpath)
    return environment


def _expected_legacy_overlay_path_sets(
    source_root: Path,
) -> tuple[frozenset[Path], frozenset[Path]]:
    repository = build_package_repository(source_root, catalog_major=5)
    assert repository.findings == ()
    assert repository.catalog is not None
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
    assert not any(path.parts[0] == ".standards" for path in legacy_targets | pinned)
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
    return required, preserved_create_only


def _versioned_legacy_predecessor(
    tmp_path: Path,
) -> tuple[Path, release_candidate_helpers.LegacyReleaseOverlay]:
    predecessor = release_candidate_helpers.prepare_legacy_release_checkout(
        _ROOT,
        tmp_path / "predecessor",
    )
    set_release_version(predecessor)
    overlay = release_candidate_helpers.load_legacy_overlay(
        _LEGACY_RELEASE_FIXTURE,
        required_paths=_expected_legacy_overlay_path_sets(_ROOT)[0],
    )
    assert f"sha256:{sha256((predecessor / 'pyproject.toml').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.pyproject_sha256_after_version
    )
    assert f"sha256:{sha256((predecessor / 'uv.lock').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.uv_lock_sha256_after_version
    )
    return predecessor, overlay


def _expected_release_python_tooling_config() -> dict[str, object]:
    return {
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


def test_legacy_release_overlay_matches_exact_catalog_target_union() -> None:
    required_paths, preserved_create_only = _expected_legacy_overlay_path_sets(_ROOT)
    production_path_sets = release_candidate_helpers.derive_legacy_overlay_path_sets(_ROOT)

    overlay = release_candidate_helpers.load_legacy_overlay(
        _LEGACY_RELEASE_FIXTURE,
        required_paths=required_paths,
    )
    preserved_snapshot = release_candidate_helpers.snapshot_regular_files(
        _ROOT,
        preserved_create_only,
    )

    assert production_path_sets.required == required_paths
    assert production_path_sets.preserved_create_only == preserved_create_only
    assert frozenset(entry.path for entry in overlay.entries) == required_paths
    assert frozenset(preserved_snapshot) == preserved_create_only
    assert Path("docs/usage.md") in required_paths
    assert Path("docs/STATUS.md") in preserved_create_only
    assert overlay.guarded_predecessor.pyproject_sha256_after_version == (
        "sha256:e52339824c6f106adf4fef1f59068710ecb395bc57d66826bfd2a9a0e7335cf9"
    )
    assert overlay.guarded_predecessor.uv_lock_sha256_after_version == (
        "sha256:7dab9066b9fcbe304978e21fed042cfaa6eff9524d71a0703b3e1084af1fe10f"
    )
    assert overlay.guarded_predecessor.vscode_tasks_sha256 == (
        "sha256:8dcb4880139bb708bf20819479bcb7898bb5d1dabd8d79e43b7d64bb3e4b3b08"
    )
    assert overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment == (
        "sha256:cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7"
    )
    assert overlay.guarded_predecessor.vscode_check_task == {
        "command": (
            "uv run ruff format --check . && uv run ruff check . && "
            "uv run basedpyright && uv run coverage run -m pytest && "
            "uv run coverage report && uv run pip-audit"
        ),
        "group": "test",
        "label": "check",
        "problemMatcher": [],
        "type": "shell",
    }
    assert overlay.guarded_predecessor.dev_group == (
        "pytest>=9.0",
        "ruff>=0.14",
        "basedpyright",
        "types-PyYAML",
        "coverage[toml]",
        "pip-audit",
        "pytest-xdist>=3.8",
        "pyright==1.1.411",
    )


def test_legacy_release_overlay_rejects_extra_entry(tmp_path: Path) -> None:
    fixture = Path(shutil.copytree(_LEGACY_RELEASE_FIXTURE, tmp_path / "fixture"))
    manifest = fixture / "manifest.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + '\n[[entries]]\npath = "zz-unexpected.txt"\nstate = "absent"\n',
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="overlay path set changed"):
        release_candidate_helpers.load_legacy_overlay(
            fixture,
            required_paths=_expected_legacy_overlay_path_sets(_ROOT)[0],
        )


def test_legacy_release_overlay_requires_frozen_predecessor_input(
    tmp_path: Path,
) -> None:
    fixture = Path(shutil.copytree(_LEGACY_RELEASE_FIXTURE, tmp_path / "fixture"))
    (fixture / "files/pyproject.toml").unlink()

    with pytest.raises(AssertionError, match="declared overlay file is unavailable"):
        release_candidate_helpers.load_legacy_overlay(
            fixture,
            required_paths=_expected_legacy_overlay_path_sets(_ROOT)[0],
        )


def test_legacy_release_overlay_ignores_only_ruff_runtime_cache(tmp_path: Path) -> None:
    fixture = Path(shutil.copytree(_LEGACY_RELEASE_FIXTURE, tmp_path / "fixture"))
    cache_file = fixture / "files/.ruff_cache/0.15.15/cache-entry"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("runtime residue\n", encoding="utf-8")
    required_paths = _expected_legacy_overlay_path_sets(_ROOT)[0]

    release_candidate_helpers.load_legacy_overlay(
        fixture,
        required_paths=required_paths,
    )

    (fixture / "files/unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="file inventory has extra bytes"):
        release_candidate_helpers.load_legacy_overlay(
            fixture,
            required_paths=required_paths,
        )


def test_legacy_release_overlay_rejects_standards_state_entry(tmp_path: Path) -> None:
    fixture = Path(shutil.copytree(_LEGACY_RELEASE_FIXTURE, tmp_path / "fixture"))
    manifest = fixture / "manifest.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + '\n[[entries]]\npath = ".standards/config.toml"\nstate = "absent"\n',
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match=r"must not target \.standards"):
        release_candidate_helpers.load_legacy_overlay(
            fixture,
            required_paths=_expected_legacy_overlay_path_sets(_ROOT)[0],
        )


def test_prepare_legacy_predecessor_requires_live_create_only_target(tmp_path: Path) -> None:
    source = copy_tracked_checkout(tmp_path / "source")
    initialize_release_baseline(source)
    (source / "docs/STATUS.md").unlink()

    with pytest.raises(AssertionError, match="live-preserved target must be a regular file"):
        release_candidate_helpers.prepare_legacy_release_checkout(
            source,
            tmp_path / "predecessor",
        )


def test_prepare_legacy_predecessor_restores_frozen_post_checker_inputs(
    tmp_path: Path,
) -> None:
    post_atomic = copy_tracked_checkout(tmp_path / "post-atomic")
    set_release_version(post_atomic)
    pyproject_path = post_atomic / "pyproject.toml"
    pyproject = pyproject_path.read_text(encoding="utf-8")
    predecessor_group = """dev = [
    "pytest>=9.0",
    "ruff>=0.14",
    "basedpyright",
    "types-PyYAML",
    "coverage[toml]",
    "pip-audit",
    "pytest-xdist>=3.8",
    "pyright==1.1.411",
]
"""
    aligned_group = """dev = [
    "basedpyright",
    "coverage[toml]>=7.10.0",
    "pip-audit",
    "pytest>=9.0",
    "ruff>=0.14.11",
    "types-PyYAML",
    "pytest-xdist>=3.8",
    "pyright==1.1.411",
]
"""
    assert pyproject.count(predecessor_group) == 1
    pyproject_path.write_text(
        pyproject.replace(predecessor_group, aligned_group),
        encoding="utf-8",
    )
    (post_atomic / ".project-standards.yml").unlink()
    standards_state = post_atomic / ".standards/config.toml"
    standards_state.parent.mkdir()
    standards_state.write_text('schema_version = "1.0"\n', encoding="utf-8")
    changed_managed_files = (
        Path(".agents/hooks/agent-handoff/session_start.py"),
        Path(".agents/skills/agent-handoff/SKILL.md"),
        Path(".agents/skills/agent-handoff/agents/openai.yaml"),
        Path(".claude/settings.json"),
    )
    created_managed_files = (
        Path(".agents/skills/markdown-frontmatter/agents/openai.yaml"),
        Path(".github/workflows/validate-standards.yml"),
    )
    for relative in (*changed_managed_files, *created_managed_files):
        path = post_atomic / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("migrated output\n", encoding="utf-8")
    initialize_release_baseline(post_atomic)
    live_pyproject = (post_atomic / "pyproject.toml").read_bytes()
    live_lock = (post_atomic / "uv.lock").read_bytes()
    _, preserved_create_only = _expected_legacy_overlay_path_sets(post_atomic)
    preserved_before = release_candidate_helpers.snapshot_regular_files(
        post_atomic,
        preserved_create_only,
    )

    predecessor = release_candidate_helpers.prepare_legacy_release_checkout(
        post_atomic,
        tmp_path / "predecessor",
    )
    overlay = release_candidate_helpers.load_legacy_overlay(
        post_atomic / "tests/fixtures/package_compatibility/legacy/release-root",
        required_paths=_expected_legacy_overlay_path_sets(post_atomic)[0],
    )

    assert (predecessor / "pyproject.toml").read_bytes() != live_pyproject
    assert (predecessor / "uv.lock").read_bytes() != live_lock
    assert (predecessor / "pyproject.toml").read_bytes() == (
        _LEGACY_RELEASE_FIXTURE / "files/pyproject.toml"
    ).read_bytes()
    assert (predecessor / "uv.lock").read_bytes() == (
        _LEGACY_RELEASE_FIXTURE / "files/uv.lock"
    ).read_bytes()
    assert (predecessor / ".project-standards.yml").is_file()
    assert not (predecessor / ".standards").exists()
    assert standards_state.is_file()
    for relative in changed_managed_files:
        assert (predecessor / relative).read_bytes() == (
            _LEGACY_RELEASE_FIXTURE / "files" / relative
        ).read_bytes()
    for relative in created_managed_files:
        assert not (predecessor / relative).exists()
    assert (
        release_candidate_helpers.snapshot_regular_files(
            predecessor,
            preserved_create_only,
        )
        == preserved_before
    )

    set_release_version(predecessor)
    assert f"sha256:{sha256((predecessor / 'pyproject.toml').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.pyproject_sha256_after_version
    )
    assert f"sha256:{sha256((predecessor / 'uv.lock').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.uv_lock_sha256_after_version
    )


def test_prealign_release_intent_changes_only_legacy_config(tmp_path: Path) -> None:
    predecessor, _overlay = _versioned_legacy_predecessor(tmp_path)
    before = _file_tree(predecessor)

    declare_release_cut_intent(predecessor)

    after = _file_tree(predecessor)
    changed = {
        relative
        for relative in set(before) | set(after)
        if before.get(relative) != after.get(relative)
    }
    assert changed == {".project-standards.yml"}
    expected = _expected_release_python_tooling_config()
    assert expected == release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG
    legacy_config = yaml.safe_load(
        (predecessor / ".project-standards.yml").read_text(encoding="utf-8")
    )
    expected_legacy = {**expected, "version": expected["contract_version"]}
    expected_legacy.pop("contract_version")
    assert legacy_config["python_tooling"] == expected_legacy
    assert legacy_config["markdown"]["frontmatter"]["workflow_mode"] == "local"


def test_prealign_release_dev_group_uses_installed_provider_and_single_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    installed = build_installed_release(predecessor, tmp_path / "build")
    distribution = InstalledDistribution(
        installed / "project_standards",
        tool_release="5.0.0",
    )
    declare_release_cut_intent(predecessor)
    path = predecessor / "pyproject.toml"
    lock_before = (predecessor / "uv.lock").read_bytes()
    writes: list[bytes] = []
    original_write_bytes = Path.write_bytes

    def record_pyproject_write(candidate: Path, content: bytes) -> int:
        if candidate == path:
            writes.append(content)
        return original_write_bytes(candidate, content)

    monkeypatch.setattr(Path, "write_bytes", record_pyproject_write)

    alignment = release_candidate_helpers.prealign_release_dev_group(
        predecessor,
        distribution,
        release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
        expected_source_sha256=(overlay.guarded_predecessor.pyproject_sha256_after_version),
        expected_dev_group=overlay.guarded_predecessor.dev_group,
    )

    assert alignment.mutated is True
    assert alignment.source_sha256 == (overlay.guarded_predecessor.pyproject_sha256_after_version)
    assert alignment.before_semantic_digest != alignment.after_semantic_digest
    assert alignment.rendered_content_digest.startswith("sha256:")
    assert len(writes) == 1
    assert writes[0] == path.read_bytes()
    assert (predecessor / "uv.lock").read_bytes() == lock_before
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["dependency-groups"]["dev"] == [
        "basedpyright",
        "coverage[toml]>=7.10.0",
        "pip-audit",
        "pytest>=9.0",
        "ruff>=0.14.11",
        "types-PyYAML",
        "pytest-xdist>=3.8",
        "pyright==1.1.411",
    ]

    aligned_source = path.read_bytes()
    aligned_digest = f"sha256:{sha256(aligned_source).hexdigest()}"
    with pytest.raises(AssertionError, match="already aligned"):
        release_candidate_helpers.prealign_release_dev_group(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=aligned_digest,
            expected_dev_group=tuple(parsed["dependency-groups"]["dev"]),
        )
    assert path.read_bytes() == aligned_source
    assert len(writes) == 1


def test_prealign_release_dev_group_rejects_semantic_drift_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    declare_release_cut_intent(predecessor)
    path = predecessor / "pyproject.toml"
    source = path.read_text(encoding="utf-8")
    anchor = '    "pyright==1.1.411",\n'
    assert source.count(anchor) == 1
    path.write_text(
        source.replace(anchor, f'{anchor}    "unexpected-package",\n'),
        encoding="utf-8",
    )
    drifted_source = path.read_bytes()
    lock_before = (predecessor / "uv.lock").read_bytes()

    def reject_catalog_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("provider must not load before semantic preconditions pass")

    monkeypatch.setattr(InstalledDistribution, "load_catalog", reject_catalog_load)
    distribution = InstalledDistribution(
        predecessor / "src/project_standards",
        tool_release="5.0.0",
    )

    with pytest.raises(AssertionError, match="dev group changed"):
        release_candidate_helpers.prealign_release_dev_group(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=f"sha256:{sha256(drifted_source).hexdigest()}",
            expected_dev_group=overlay.guarded_predecessor.dev_group,
        )
    assert path.read_bytes() == drifted_source
    assert (predecessor / "uv.lock").read_bytes() == lock_before


def test_prealign_release_dev_group_rejects_digest_drift_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    declare_release_cut_intent(predecessor)
    path = predecessor / "pyproject.toml"
    source = path.read_bytes()
    lock_before = (predecessor / "uv.lock").read_bytes()

    def reject_catalog_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("provider must not load before digest preconditions pass")

    monkeypatch.setattr(InstalledDistribution, "load_catalog", reject_catalog_load)
    distribution = InstalledDistribution(
        predecessor / "src/project_standards",
        tool_release="5.0.0",
    )

    with pytest.raises(AssertionError, match="pyproject digest changed"):
        release_candidate_helpers.prealign_release_dev_group(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=f"sha256:{'0' * 64}",
            expected_dev_group=overlay.guarded_predecessor.dev_group,
        )
    assert path.read_bytes() == source
    assert (predecessor / "uv.lock").read_bytes() == lock_before


def test_prealign_release_check_task_uses_installed_provider_and_single_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    installed = build_installed_release(predecessor, tmp_path / "build")
    distribution = InstalledDistribution(
        installed / "project_standards",
        tool_release="5.0.0",
    )
    declare_release_cut_intent(predecessor)
    path = predecessor / ".vscode/tasks.json"
    before_document = json.loads(path.read_bytes())
    writes: list[bytes] = []
    original_write_bytes = Path.write_bytes

    def record_tasks_write(candidate: Path, content: bytes) -> int:
        if candidate == path:
            writes.append(content)
        return original_write_bytes(candidate, content)

    monkeypatch.setattr(Path, "write_bytes", record_tasks_write)

    alignment = release_candidate_helpers.prealign_release_check_task(
        predecessor,
        distribution,
        release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
        expected_source_sha256=overlay.guarded_predecessor.vscode_tasks_sha256,
        expected_check_task=overlay.guarded_predecessor.vscode_check_task,
        expected_post_alignment_sha256=(
            overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
        ),
    )

    assert alignment.mutated is True
    assert alignment.source_sha256 == overlay.guarded_predecessor.vscode_tasks_sha256
    assert alignment.post_alignment_sha256 == (
        overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
    )
    assert alignment.before_semantic_digest != alignment.after_semantic_digest
    assert alignment.after_semantic_digest == (
        "sha256:119597ceaea2647bae17e3261ad820bf1a7ffec997a33b431c9396797e03ff6d"
    )
    assert alignment.rendered_content_digest.startswith("sha256:")
    assert len(writes) == 1
    assert writes[0] == path.read_bytes()
    after_document = json.loads(path.read_bytes())
    before_check = next(task for task in before_document["tasks"] if task.get("label") == "check")
    after_check = next(task for task in after_document["tasks"] if task.get("label") == "check")
    assert before_check == overlay.guarded_predecessor.vscode_check_task
    assert after_check == {
        "command": (
            "uv run ruff format --check . && uv run ruff check . && "
            "uv run basedpyright && uv run coverage erase && "
            "uv run coverage run --parallel-mode -m pytest && "
            "uv run coverage combine && uv run coverage report && uv run pip-audit"
        ),
        "group": "test",
        "label": "check",
        "problemMatcher": [],
        "type": "shell",
    }
    assert before_document["version"] == after_document["version"]
    assert [task for task in before_document["tasks"] if task.get("label") != "check"] == [
        task for task in after_document["tasks"] if task.get("label") != "check"
    ]

    aligned_source = path.read_bytes()
    with pytest.raises(AssertionError, match="already aligned"):
        release_candidate_helpers.prealign_release_check_task(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=(
                overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
            ),
            expected_check_task=after_check,
            expected_post_alignment_sha256=(
                overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
            ),
        )
    assert path.read_bytes() == aligned_source
    assert len(writes) == 1


def test_prealign_release_check_task_rejects_semantic_drift_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    declare_release_cut_intent(predecessor)
    path = predecessor / ".vscode/tasks.json"
    source = path.read_text(encoding="utf-8")
    anchor = "uv run coverage run -m pytest"
    assert source.count(anchor) == 1
    path.write_text(source.replace(anchor, "uv run pytest -n auto"), encoding="utf-8")
    drifted_source = path.read_bytes()

    def reject_catalog_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("provider must not load before semantic preconditions pass")

    monkeypatch.setattr(InstalledDistribution, "load_catalog", reject_catalog_load)
    distribution = InstalledDistribution(
        predecessor / "src/project_standards",
        tool_release="5.0.0",
    )

    with pytest.raises(AssertionError, match="check task changed"):
        release_candidate_helpers.prealign_release_check_task(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=f"sha256:{sha256(drifted_source).hexdigest()}",
            expected_check_task=overlay.guarded_predecessor.vscode_check_task,
            expected_post_alignment_sha256=(
                overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
            ),
        )
    assert path.read_bytes() == drifted_source


def test_prealign_release_check_task_rejects_digest_drift_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predecessor, overlay = _versioned_legacy_predecessor(tmp_path)
    declare_release_cut_intent(predecessor)
    path = predecessor / ".vscode/tasks.json"
    source = path.read_bytes()

    def reject_catalog_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("provider must not load before digest preconditions pass")

    monkeypatch.setattr(InstalledDistribution, "load_catalog", reject_catalog_load)
    distribution = InstalledDistribution(
        predecessor / "src/project_standards",
        tool_release="5.0.0",
    )

    with pytest.raises(AssertionError, match="tasks digest changed"):
        release_candidate_helpers.prealign_release_check_task(
            predecessor,
            distribution,
            release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
            expected_source_sha256=f"sha256:{'0' * 64}",
            expected_check_task=overlay.guarded_predecessor.vscode_check_task,
            expected_post_alignment_sha256=(
                overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
            ),
        )
    assert path.read_bytes() == source


def test_legacy_dependency_scan_rejects_unapproved_runtime_writers(tmp_path: Path) -> None:
    approved = tmp_path / "project_standards/cli.py"
    approved.parent.mkdir(parents=True)
    approved.write_text(
        "from project_standards.adopt.engine import execute_plan\n",
        encoding="utf-8",
    )
    unexpected = tmp_path / "project_standards/surprise.py"
    unexpected.write_text(
        "from project_standards.agent_handoff.planning import apply_adoption\napply_adoption()\n",
        encoding="utf-8",
    )
    provider = tmp_path / "project_standards/agent_handoff/providers.py"
    provider.parent.mkdir()
    provider.write_text(
        "from project_standards.agent_handoff.planning import apply_adoption\napply_adoption()\n",
        encoding="utf-8",
    )

    classified = classify_legacy_dependencies(tmp_path)

    assert classified["direct-writer-runtime"] == (
        "project_standards/agent_handoff/providers.py",
        "project_standards/cli.py",
    )
    assert classified["unclassified"] == ("project_standards/surprise.py",)


def test_copy_tracked_checkout_uses_current_working_tree_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    tracked = source / "tracked.txt"
    deleted = source / "deleted.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    deleted.write_text("deleted\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    deleted.unlink()
    added = source / "added.txt"
    added.write_text("added\n", encoding="utf-8")

    checkout = copy_tracked_checkout(tmp_path / "checkout", source_root=source)

    assert (checkout / "tracked.txt").read_text(encoding="utf-8") == "tracked\n"
    assert (checkout / "added.txt").read_text(encoding="utf-8") == "added\n"
    assert not (checkout / "deleted.txt").exists()


def test_git_known_tree_and_mirror_exclude_repository_and_runtime_artifacts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    (source / ".gitignore").write_text(
        ".venv/\n.coverage*\n.pytest_cache/\n.ruff_cache/\n__pycache__/\n",
        encoding="utf-8",
    )
    executable = source / "script.py"
    executable.write_text("print('tracked')\n", encoding="utf-8")
    executable.chmod(0o755)
    (source / "linked.py").symlink_to("script.py")
    deleted = source / "deleted.txt"
    deleted.write_text("deleted\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    deleted.unlink()
    (source / "added.txt").write_text("added\n", encoding="utf-8")
    for relative in (
        ".venv/ignored.txt",
        ".coverage.worker",
        ".pytest_cache/ignored.txt",
        ".ruff_cache/ignored.txt",
        "pkg/__pycache__/ignored.pyc",
    ):
        ignored = source / relative
        ignored.parent.mkdir(parents=True, exist_ok=True)
        ignored.write_text("runtime residue\n", encoding="utf-8")

    expected = release_candidate_helpers.git_known_file_tree(source)

    assert set(expected) == {".gitignore", "added.txt", "linked.py", "script.py"}
    assert expected["script.py"][:2] == ("regular", 0o755)
    assert expected["linked.py"] == ("symlink", 0o777, "script.py")

    baseline = tmp_path / "baseline"
    baseline.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=baseline, check=True)
    (baseline / "stale.txt").write_text("stale\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=baseline, check=True)

    mirror_release_tree(source, baseline)

    assert (baseline / ".git").is_dir()
    assert not (baseline / "stale.txt").exists()
    assert not (baseline / ".venv").exists()
    assert release_candidate_helpers.git_known_file_tree(baseline) == expected


def test_release_patch_disables_rename_detection(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "old.txt").write_text("same bytes\n", encoding="utf-8")
    initialize_release_baseline(checkout)
    subprocess.run(["git", "config", "diff.renames", "true"], cwd=checkout, check=True)
    (checkout / "old.txt").unlink()
    (checkout / "new.txt").write_text("same bytes\n", encoding="utf-8")

    result = release_patch(checkout)

    assert result.ledger == ("A\tnew.txt", "D\told.txt")
    assert b"similarity index" not in result.patch
    assert b"deleted file mode" in result.patch
    assert b"new file mode" in result.patch


def test_migration_patch_replay_initializes_git_known_baseline(tmp_path: Path) -> None:
    source_snapshot = tmp_path / "source-snapshot"
    source_snapshot.mkdir()
    (source_snapshot / "old.txt").write_text("old\n", encoding="utf-8")

    completed = Path(shutil.copytree(source_snapshot, tmp_path / "completed"))
    initialize_release_baseline(completed)
    (completed / "old.txt").write_text("new\n", encoding="utf-8")
    (completed / "added.txt").write_text("added\n", encoding="utf-8")
    migration_patch = release_patch(completed)

    replay = _replay_migration_patch(
        source_snapshot,
        tmp_path / "replay",
        migration_patch.patch,
    )

    assert (replay / ".git").is_dir()
    assert release_candidate_helpers.git_known_file_tree(replay) == (
        release_candidate_helpers.git_known_file_tree(completed)
    )


def test_materialize_git_object_tree_commits_exact_modes_and_symlinks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    executable = source / "scripts/check"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    (source / "check-link").symlink_to("scripts/check")
    (source / "plain.txt").write_text("plain\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected_tree = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    target = tmp_path / "materialized"
    target.mkdir()

    release_candidate_helpers.materialize_git_object_tree(source, commit, target)

    actual_tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert actual_tree == expected_tree
    assert release_candidate_helpers.git_known_file_tree(target) == (
        release_candidate_helpers.git_known_file_tree(source)
    )
    assert (
        subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=target,
            check=True,
            capture_output=True,
        ).stdout
        == b""
    )


def test_release_replay_source_override_accepts_exact_independent_tree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("authority\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    override = tmp_path / "override"
    release_candidate_helpers.materialize_git_object_tree(source, commit, override)

    resolved = release_candidate_helpers.resolve_release_replay_source_root(
        source,
        environment={
            "RELEASE_REPLAY_SOURCE_ROOT": str(override),
            "PRE_ATOMIC_HEAD": commit,
        },
    )

    assert resolved == override


def test_release_replay_source_override_rejects_non_git_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("authority\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    override = tmp_path / "override"
    override.mkdir()

    with pytest.raises(AssertionError, match="independent Git repository"):
        release_candidate_helpers.resolve_release_replay_source_root(
            source,
            environment={
                "RELEASE_REPLAY_SOURCE_ROOT": str(override),
                "PRE_ATOMIC_HEAD": commit,
            },
        )


def test_release_replay_source_override_rejects_dirty_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("authority\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    override = tmp_path / "override"
    release_candidate_helpers.materialize_git_object_tree(source, commit, override)
    (override / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="must be clean"):
        release_candidate_helpers.resolve_release_replay_source_root(
            source,
            environment={
                "RELEASE_REPLAY_SOURCE_ROOT": str(override),
                "PRE_ATOMIC_HEAD": commit,
            },
        )


def test_release_replay_source_override_rejects_wrong_tree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("authority\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    other = tmp_path / "other"
    other.mkdir()
    (other / "tracked.txt").write_text("different\n", encoding="utf-8")
    initialize_release_baseline(other)

    with pytest.raises(AssertionError, match="tree differs"):
        release_candidate_helpers.resolve_release_replay_source_root(
            source,
            environment={
                "RELEASE_REPLAY_SOURCE_ROOT": str(other),
                "PRE_ATOMIC_HEAD": commit,
            },
        )


def test_release_replay_source_override_rejects_ambient_object_borrowing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "tracked.txt").write_text("authority\n", encoding="utf-8")
    initialize_release_baseline(source)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    override = tmp_path / "override"
    override.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=override, check=True)
    (override / ".git/HEAD").write_text("ref: refs/heads/replay\n", encoding="utf-8")
    replay_ref = override / ".git/refs/heads/replay"
    replay_ref.parent.mkdir(parents=True, exist_ok=True)
    replay_ref.write_text(f"{commit}\n", encoding="ascii")
    source_commit = source / ".git/objects" / commit[:2] / commit[2:]
    override_commit = override / ".git/objects" / commit[:2] / commit[2:]
    override_commit.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_commit, override_commit)

    monkeypatch.setenv(
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        str(source / ".git/objects"),
    )
    subprocess.run(["git", "read-tree", "HEAD"], cwd=override, check=True)
    (override / "tracked.txt").write_text("authority\n", encoding="utf-8")
    borrowed_tree = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{tree}"],
        cwd=override,
        check=True,
        capture_output=True,
    ).stdout
    assert borrowed_tree

    with pytest.raises(AssertionError, match="self-contained"):
        release_candidate_helpers.resolve_release_replay_source_root(
            source,
            environment={
                "RELEASE_REPLAY_SOURCE_ROOT": str(override),
                "PRE_ATOMIC_HEAD": commit,
            },
        )


def test_complete_release_patch_includes_additions_and_matches_committed_diff(
    tmp_path: Path,
) -> None:
    predecessor = tmp_path / "predecessor"
    predecessor.mkdir()
    (predecessor / "kept.txt").write_text("before\n", encoding="utf-8")
    removed = predecessor / "removed.txt"
    removed.write_text("remove me\n", encoding="utf-8")
    evidence = (
        predecessor
        / "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
    )
    evidence.parent.mkdir(parents=True)
    evidence.write_text("old evidence\n", encoding="utf-8")
    initialize_release_baseline(predecessor)
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=predecessor,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    final_root = Path(shutil.copytree(predecessor, tmp_path / "final", symlinks=True))
    (final_root / "kept.txt").write_text("after\n", encoding="utf-8")
    (final_root / "removed.txt").unlink()
    added = final_root / ".standards/config.toml"
    added.parent.mkdir()
    added.write_text('schema_version = "1.0"\n', encoding="utf-8")
    linked = final_root / "config-link"
    linked.symlink_to(".standards/config.toml")
    final_evidence = final_root / evidence.relative_to(predecessor)
    final_evidence.write_text("validated evidence\n", encoding="utf-8")

    complete = release_candidate_helpers.complete_release_content_patch(
        predecessor,
        final_root,
    )

    assert "A\t.standards/config.toml" in complete.ledger
    assert "A\tconfig-link" in complete.ledger
    assert "D\tremoved.txt" in complete.ledger
    assert "M\tkept.txt" in complete.ledger
    assert not any(evidence.relative_to(predecessor).as_posix() in row for row in complete.ledger)
    assert evidence.relative_to(predecessor).as_posix().encode() not in complete.patch
    assert complete.patch_sha256 == sha256(complete.patch).hexdigest()

    subprocess.run(["git", "add", "--all"], cwd=final_root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Release Evidence",
            "-c",
            "user.email=168346341+chrisdpurcell@users.noreply.github.com",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--quiet",
            "-m",
            "final release",
        ],
        cwd=final_root,
        check=True,
    )
    committed = release_candidate_helpers.canonical_release_diff(
        final_root,
        before,
        "HEAD",
    )
    assert committed == complete


def test_complete_release_patch_has_no_second_excluded_path(tmp_path: Path) -> None:
    predecessor = tmp_path / "predecessor"
    predecessor.mkdir()
    (predecessor / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    initialize_release_baseline(predecessor)
    final_root = Path(shutil.copytree(predecessor, tmp_path / "final", symlinks=True))
    first = release_candidate_helpers.complete_release_content_patch(
        predecessor,
        final_root,
    )
    assert first.ledger == ()
    (final_root / "unexpected.txt").write_text("must be recorded\n", encoding="utf-8")

    changed = release_candidate_helpers.complete_release_content_patch(
        predecessor,
        final_root,
    )

    assert changed.ledger == ("A\tunexpected.txt",)
    assert changed.patch


def test_canonical_release_diff_ignores_ambient_and_local_diff_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "target.txt"
    target.write_text("one\ntwo\nthree\nfour\nfive\nsix\n", encoding="utf-8")
    initialize_release_baseline(repo)
    target.write_text("one\nTWO\nthree\nfour\nFIVE\nsix\n", encoding="utf-8")
    expected = release_candidate_helpers.canonical_release_diff(repo, "HEAD")

    subprocess.run(
        ["git", "config", "diff.algorithm", "patience"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "diff.noprefix", "true"],
        cwd=repo,
        check=True,
    )
    monkeypatch.setenv("GIT_DIFF_OPTS", "-u0")
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "foreign-index"))

    assert release_candidate_helpers.canonical_release_diff(repo, "HEAD") == expected


def test_release_input_digest_excludes_only_its_evidence_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    tracked = source / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    evidence = (
        source / "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
    )
    evidence.parent.mkdir(parents=True)
    evidence.write_text("evidence one\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source, check=True)

    release_input_digest = release_candidate_helpers.release_input_digest
    baseline = release_input_digest(source)
    evidence.write_text("evidence two\n", encoding="utf-8")

    assert release_input_digest(source) == baseline

    tracked.write_text("changed\n", encoding="utf-8")

    assert release_input_digest(source) != baseline


def test_release_input_digest_frames_binary_file_records(tmp_path: Path) -> None:
    two_files = tmp_path / "two-files"
    two_files.mkdir()
    (two_files / "a").write_bytes(b"X")
    (two_files / "b").write_bytes(b"Y")
    initialize_release_baseline(two_files)

    one_file = tmp_path / "one-file"
    one_file.mkdir()
    (one_file / "a").write_bytes(b"X\0b\0" + b"100644\0regular\0Y")
    initialize_release_baseline(one_file)

    assert release_candidate_helpers.release_input_digest(two_files) != (
        release_candidate_helpers.release_input_digest(one_file)
    )


def test_release_evidence_preflight_rejects_stale_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
    tracked = source / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    evidence = (
        source / "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
    )
    evidence.parent.mkdir(parents=True)
    evidence.write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    digest = release_candidate_helpers.release_input_digest(source)
    proof_digest = "0" * 64
    semantic_digest = f"sha256:{proof_digest}"
    record = {
        "schema_version": 1,
        "release_input_sha256": digest,
        "migration_patch_sha256": proof_digest,
        "migration_ledger": ["M\ttracked.txt"],
        "control_plane_sha256": {
            "catalog.toml": proof_digest,
            "config.toml": proof_digest,
            "lock.toml": proof_digest,
        },
        "dev_group_alignment": {
            "source_sha256": semantic_digest,
            "before_semantic_digest": semantic_digest,
            "after_semantic_digest": semantic_digest,
            "rendered_content_digest": semantic_digest,
            "mutated": True,
        },
        "check_task_alignment": {
            "source_sha256": semantic_digest,
            "post_alignment_sha256": semantic_digest,
            "before_semantic_digest": semantic_digest,
            "after_semantic_digest": semantic_digest,
            "rendered_content_digest": semantic_digest,
            "mutated": True,
        },
    }
    evidence.write_text(
        f"Release-input SHA-256: `{digest}`\n\n"
        "<!-- release-migration-record:begin -->\n"
        "```json\n"
        f"{json.dumps(record, sort_keys=True)}\n"
        "```\n"
        "<!-- release-migration-record:end -->\n",
        encoding="utf-8",
    )
    preflight = release_candidate_helpers.assert_release_evidence_current

    preflight(source, expected_record=record)
    mismatched = {**record, "migration_patch_sha256": "1" * 64}
    with pytest.raises(AssertionError, match="differs from the executed proof"):
        preflight(source, expected_record=mismatched)
    tracked.write_text("stale\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="release evidence is stale"):
        preflight(source)


def test_retained_release_evidence_is_current() -> None:
    release_candidate_helpers.assert_release_evidence_current(_ROOT)


def test_disposable_checkout_builds_release_without_mutating_source(tmp_path: Path) -> None:
    source_versions = {path: (_ROOT / path).read_bytes() for path in ("pyproject.toml", "uv.lock")}
    checkout = copy_tracked_checkout(tmp_path / "checkout")
    set_release_version(checkout)
    installed = build_installed_release(checkout, tmp_path / "build")
    environment = _release_subprocess_environment(pythonpath=installed)

    result = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; raise SystemExit(main(['--version']))",
        ],
        cwd=checkout,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "project-standards 5.0.0"
    assert {path: (_ROOT / path).read_bytes() for path in source_versions} == source_versions
    assert (_ROOT / ".project-standards.yml").is_file()
    assert not (_ROOT / ".standards").exists()


def _reconstruct_predecessor(
    source_root: Path,
    target: Path,
) -> _ReconstructedPredecessor:
    path_sets = release_candidate_helpers.derive_legacy_overlay_path_sets(source_root)
    preserved_create_only = release_candidate_helpers.snapshot_regular_files(
        source_root,
        path_sets.preserved_create_only,
    )
    predecessor = release_candidate_helpers.prepare_legacy_release_checkout(
        source_root,
        target,
    )
    initialize_release_baseline(predecessor)
    overlay = release_candidate_helpers.load_legacy_overlay(
        source_root / "tests/fixtures/package_compatibility/legacy/release-root",
        required_paths=path_sets.required,
    )
    return _ReconstructedPredecessor(
        root=predecessor,
        tree=release_candidate_helpers.git_known_file_tree(predecessor),
        overlay=overlay,
        preserved_create_only=preserved_create_only,
    )


def _replay_migration_patch(
    source_snapshot: Path,
    target: Path,
    patch: bytes,
) -> Path:
    """Replay against the same committed predecessor used to derive the patch."""
    replay = Path(shutil.copytree(source_snapshot, target, symlinks=True))
    initialize_release_baseline(replay)
    replay_release_patch(replay, patch)
    return replay


def _execute_migration_proof(
    reconstructed: _ReconstructedPredecessor,
    tmp_path: Path,
) -> _MigrationProofResult:
    predecessor = reconstructed.root
    overlay = reconstructed.overlay
    source_snapshot = copy_tracked_checkout(
        tmp_path / "source-snapshot",
        source_root=predecessor,
    )
    checkout = copy_tracked_checkout(
        tmp_path / "checkout",
        source_root=predecessor,
    )
    set_release_version(checkout)
    assert f"sha256:{sha256((checkout / 'pyproject.toml').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.pyproject_sha256_after_version
    )
    assert f"sha256:{sha256((checkout / 'uv.lock').read_bytes()).hexdigest()}" == (
        overlay.guarded_predecessor.uv_lock_sha256_after_version
    )
    installed = build_installed_release(checkout, tmp_path / "build")
    distribution = InstalledDistribution(
        installed / "project_standards",
        tool_release="5.0.0",
    )
    declare_release_cut_intent(checkout)
    alignment = release_candidate_helpers.prealign_release_dev_group(
        checkout,
        distribution,
        release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
        expected_source_sha256=(overlay.guarded_predecessor.pyproject_sha256_after_version),
        expected_dev_group=overlay.guarded_predecessor.dev_group,
    )
    assert alignment.mutated is True
    assert alignment.before_semantic_digest != alignment.after_semantic_digest
    task_alignment = release_candidate_helpers.prealign_release_check_task(
        checkout,
        distribution,
        release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG,
        expected_source_sha256=overlay.guarded_predecessor.vscode_tasks_sha256,
        expected_check_task=overlay.guarded_predecessor.vscode_check_task,
        expected_post_alignment_sha256=(
            overlay.guarded_predecessor.vscode_tasks_sha256_after_alignment
        ),
    )
    assert task_alignment.mutated is True
    assert task_alignment.after_semantic_digest == (
        "sha256:119597ceaea2647bae17e3261ad820bf1a7ffec997a33b431c9396797e03ff6d"
    )
    tasks_after_alignment = (checkout / ".vscode/tasks.json").read_bytes()
    handoff_before = {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in (checkout / "docs/handoff").rglob("*")
        if path.is_file()
    }
    workflows_before = {
        path: (checkout / path).read_bytes()
        for path in (
            ".github/workflows/check.yml",
            ".github/workflows/format.yml",
            ".github/workflows/lint-markdown.yml",
            ".github/workflows/validate-specs.yml",
        )
    }
    instructions_before = {
        path: (checkout / path).read_bytes() for path in ("AGENTS.md", "CLAUDE.md")
    }

    environment = _release_subprocess_environment(pythonpath=installed)
    preview_outputs: list[str] = []
    for machine_readable in (False, True):
        arguments = ["init", "--catalog", "5", "--migrate", "--repo", "."]
        if machine_readable:
            arguments.append("--json")
        preview_cli = subprocess.run(
            [
                "python",
                "-c",
                f"from project_standards.cli import main; raise SystemExit(main({arguments!r}))",
            ],
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert preview_cli.returncode == 1, preview_cli.stderr
        assert preview_cli.stdout
        preview_outputs.append(preview_cli.stdout)
    json_preview = json.loads(preview_outputs[1])
    assert json_preview["applicable"] is True, json.dumps(json_preview, indent=2)

    preview = plan_legacy_migration(checkout, distribution, "5")
    assert preview.applicable, "\n".join(
        f"{finding.code} {finding.standard_id} {finding.path} {finding.identity}"
        for finding in preview.findings
    )
    reports = {report.package.standard_id: report for report in preview.reports}
    python_report = reports["python-tooling"]
    (workflow_claim,) = [
        claim
        for claim in python_report.claims
        if claim.target.original == ".github/workflows/check.yml"
    ]
    assert workflow_claim.observed_digest.value == (
        f"sha256:{sha256(workflows_before['.github/workflows/check.yml']).hexdigest()}"
    )
    assert workflow_claim.ownership == "consumer-owned"
    assert workflow_claim.disposition.value == "preserve"
    assert workflow_claim.intent_pointer == "/python_tooling/workflow_ownership"
    assert "not semantically validated by the package" in render_migration_report(python_report)

    protected_python_containers = {
        "AGENTS.md",
        "CLAUDE.md",
        ".vscode/settings.json",
        ".vscode/tasks.json",
    }
    assert protected_python_containers.isdisjoint(
        path.original for path in preview.planner.retired_targets
    )
    assert protected_python_containers.isdisjoint(
        action.target for action in preview.legacy_removals
    )
    assert all(
        claim.disposition.value != "remove"
        for claim in python_report.claims
        if claim.target.original in protected_python_containers
    )
    retired_instruction_content: dict[str, list[bytes]] = {path: [] for path in instructions_before}
    for path, content in preview.planner.retired_content:
        if path.original in retired_instruction_content:
            retired_instruction_content[path.original].append(content)
    assert all(len(chunks) == 1 for chunks in retired_instruction_content.values())

    lock_by_unit = {
        (unit.path.original, unit.scope): unit
        for unit in preview.reconciliation.next_lock.artifacts
    }
    for path, scope, semantic_digest in (
        (
            "pyproject.toml",
            "key:/dependency-groups/dev",
            alignment.after_semantic_digest,
        ),
        (
            ".vscode/tasks.json",
            "keyed-set:/tasks#label=check",
            task_alignment.after_semantic_digest,
        ),
    ):
        unit = lock_by_unit[(path, scope)]
        assert unit.owners == ("python-tooling",)
        assert unit.provenance.value == "provider"
        assert unit.semantic_digest.value == semantic_digest
    assert not any(
        unit.path.original == ".github/workflows/check.yml"
        for unit in preview.reconciliation.next_lock.artifacts
    )
    expected_actions = {action.target for action in preview.actions}
    assert {action["target"] for action in json_preview["plan"]["actions"]} == expected_actions
    assert all(target in preview_outputs[0] for target in expected_actions)
    mutating_actions = {
        (action.target, action.kind.value)
        for action in preview.actions
        if action.kind not in {ActionKind.NOOP, ActionKind.PRESERVE, ActionKind.ADOPT}
    }
    assert not any(target == ".github/workflows/check.yml" for target, _kind in mutating_actions)
    assert not any(
        target == ".github/workflows/validate-markdown-frontmatter.yml"
        for target, _kind in mutating_actions
    )
    assert (".github/workflows/validate-standards.yml", "create") in mutating_actions
    assert (".github/workflows/validate-specs.yml", "update") in mutating_actions
    assert not any(
        target
        in {
            ".github/workflows/format.yml",
            ".github/workflows/lint-markdown.yml",
        }
        for target, _kind in mutating_actions
    )
    assert (checkout / ".project-standards.yml").is_file()
    apply_cli = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; "
            "raise SystemExit(main(['init', '--catalog', '5', '--migrate', '--apply', '--repo', '.']))",
        ],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert apply_cli.returncode == 0, apply_cli.stdout + apply_cli.stderr

    assert not (checkout / ".project-standards.yml").exists()
    assert not (checkout / ".agents/agent-handoff/manifest.json").exists()
    assert (checkout / ".github/workflows/check.yml").read_bytes() == (
        workflows_before[".github/workflows/check.yml"]
    )
    assert (checkout / ".vscode/tasks.json").read_bytes() == tasks_after_alignment
    assert {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in (checkout / "docs/handoff").rglob("*")
        if path.is_file()
    } == handoff_before
    lock = parse_lock((checkout / ".standards/lock.toml").read_bytes())
    assert lock == preview.reconciliation.next_lock
    config = parse_config((checkout / ".standards/config.toml").read_bytes())
    assert config.standards["markdown-frontmatter"].config["workflow_mode"] == "local"
    assert config.standards["markdown-tooling"].config["workflow_mode"] == "self-hosted"
    assert config.standards["project-spec"].config["workflow_mode"] == "self-hosted"
    python_config = config.standards["python-tooling"].config
    for option in (
        "additional_dev_dependencies",
        "ruff",
        "pytest",
        "coverage",
        "workflow_ownership",
    ):
        assert (
            python_config[option]
            == (release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG[option])
        )
    pyproject = tomllib.loads((checkout / "pyproject.toml").read_text(encoding="utf-8"))
    dev_group = pyproject["dependency-groups"]["dev"]
    assert "coverage[toml]>=7.10.0" in dev_group
    assert "pytest-xdist>=3.8" in dev_group
    assert "pyright==1.1.411" in dev_group
    assert pyproject["tool"]["coverage"]["run"]["parallel"] is True
    assert pyproject["tool"]["coverage"]["run"]["patch"] == ["subprocess"]
    expected_pytest_config = release_candidate_helpers.RELEASE_PYTHON_TOOLING_CONFIG["pytest"]
    assert isinstance(expected_pytest_config, dict)
    assert (
        pyproject["tool"]["pytest"]["ini_options"]["markers"] == (expected_pytest_config["markers"])
    )
    check_script_bytes = (checkout / "scripts/check.py").read_bytes()
    assert check_script_bytes == preview.reconciliation.proposed_content("scripts/check.py")
    check_script = check_script_bytes.decode("utf-8")
    assert '"coverage", "erase"' in check_script
    assert '"coverage", "run", "--parallel-mode"' in check_script
    assert '"coverage", "combine"' in check_script
    # The root gate becomes meaningful only after Task 11 atomically rewrites the
    # repository's pre-control-plane tests; Task 9 executes both scratch gates instead.
    frontmatter_endpoint = checkout / ".github/workflows/validate-markdown-frontmatter.yml"
    assert frontmatter_endpoint.read_bytes() == workflows_before[
        ".github/workflows/validate-markdown-frontmatter.yml"
    ]
    assert b"workflow_call:" in frontmatter_endpoint.read_bytes()
    standards_workflow = checkout / ".github/workflows/validate-standards.yml"
    assert standards_workflow.is_file()
    assert b"uses: ./.github/workflows/validate-markdown-frontmatter.yml" in (
        standards_workflow.read_bytes()
    )
    assert b"validate-markdown-frontmatter.yml@v5" not in standards_workflow.read_bytes()
    for path in (
        ".github/workflows/format.yml",
        ".github/workflows/lint-markdown.yml",
    ):
        assert (checkout / path).read_bytes() == workflows_before[path]
    expected_spec_workflow = (
        installed
        / "project_standards/payloads/project-spec/1.1/resources/self-host-validate-specs.yml"
    ).read_bytes()
    assert (
        checkout / ".github/workflows/validate-specs.yml"
    ).read_bytes() == expected_spec_workflow
    assert b".project-standards.yml" not in expected_spec_workflow
    markdown_adapter = MarkdownBlockAdapter()
    instruction_scopes = (
        "block:agent-handoff",
        "block:markdown-tooling",
        "block:python-tooling",
    )
    for path, frozen_content in instructions_before.items():
        migrated_content = (checkout / path).read_bytes()
        assert migrated_content == preview.reconciliation.proposed_content(path)
        state = markdown_adapter.inspect(migrated_content, instruction_scopes)
        assert tuple(unit.scope for unit in state.units) == instruction_scopes
        assert all(
            migrated_content.count(
                f"<!-- BEGIN project-standards:{scope.removeprefix('block:')} -->".encode()
            )
            == 1
            for scope in instruction_scopes
        )
        for unit in state.units:
            locked = lock_by_unit[(path, unit.scope)]
            assert locked.provenance.value == "provider"
            assert locked.content_digest.value == f"sha256:{sha256(unit.raw).hexdigest()}"
            assert locked.semantic_digest == unit.semantic_digest
        (retired_residual,) = retired_instruction_content[path]
        assert frozen_content.count(b"<!-- BEGIN agent-handoff managed instructions -->") == 1
        assert frozen_content.count(b"<!-- END agent-handoff managed instructions -->") == 1
        assert b"<!-- BEGIN agent-handoff managed instructions -->" not in retired_residual
        assert b"<!-- END agent-handoff managed instructions -->" not in retired_residual
        assert len(retired_residual) < len(frozen_content)
        assert retired_residual == _instruction_residual_without_legacy_handoff_block(
            frozen_content
        )
        assert migrated_content.startswith(retired_residual)
        managed_suffix = migrated_content[len(retired_residual) :]
        for unit in state.units:
            block_id = unit.scope.removeprefix("block:")
            envelope = (
                b"<!-- prettier-ignore-start -->\n\n"
                + f"<!-- BEGIN project-standards:{block_id} -->\n".encode()
                + unit.raw
                + f"<!-- END project-standards:{block_id} -->\n\n".encode()
                + b"<!-- prettier-ignore-end -->\n"
            )
            assert managed_suffix.count(envelope) == 1
            managed_suffix = managed_suffix.replace(envelope, b"", 1)
        assert managed_suffix.replace(b"\n", b"") == b""
    active_workflow_bytes = b"\n".join(
        path.read_bytes() for path in sorted((checkout / ".github/workflows").glob("*.yml"))
    )
    assert b".project-standards.yml" not in active_workflow_bytes
    assert b".agents/agent-handoff/manifest.json" not in active_workflow_bytes
    tracked_dependencies = classify_legacy_dependencies(checkout)
    installed_dependencies = classify_legacy_dependencies(installed)
    assert tracked_dependencies["unclassified"] == ()
    assert installed_dependencies["unclassified"] == ()
    assert tracked_dependencies["migration-runtime"]
    assert installed_dependencies["migration-runtime"]
    assert tracked_dependencies["direct-writer-runtime"] == tuple(
        f"src/{path}" for path in _EXPECTED_DIRECT_WRITER_MODULES
    )
    assert installed_dependencies["direct-writer-runtime"] == _EXPECTED_DIRECT_WRITER_MODULES

    sync_environment = _release_subprocess_environment()
    for arguments in (
        ["uv", "lock", "--offline"],
        ["uv", "lock", "--check", "--offline"],
        ["uv", "sync", "--locked", "--all-groups", "--offline"],
    ):
        lock_command = subprocess.run(
            arguments,
            cwd=checkout,
            env=sync_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert lock_command.returncode == 0, lock_command.stdout + lock_command.stderr
    refreshed_lock = tomllib.loads((checkout / "uv.lock").read_text(encoding="utf-8"))
    locked_pyright = [
        package for package in refreshed_lock["package"] if package["name"] == "pyright"
    ]
    assert len(locked_pyright) == 1
    assert locked_pyright[0]["version"] == "1.1.411"

    initialize_release_baseline(checkout)
    before = release_candidate_helpers.git_known_file_tree(checkout)
    fixed_point = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; "
            "raise SystemExit(main(['reconcile', '--apply', '--repo', '.', '--json']))",
        ],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert fixed_point.returncode == 0, fixed_point.stderr
    fixed_point_result = json.loads(fixed_point.stdout)
    assert fixed_point_result["applied_action_ids"] == []
    assert not any(
        action["kind"] not in {"no-op", "preserve"}
        for action in fixed_point_result["plan"]["actions"]
    )
    assert release_candidate_helpers.git_known_file_tree(checkout) == before

    catalog_check = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; raise SystemExit(main(['standards', 'render-consumer-catalog', '--root', '.', '--catalog-major', '5', '--output', '.standards/catalog.toml', '--tool-release', '5.0.0', '--check']))",
        ],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert catalog_check.returncode == 0, catalog_check.stderr

    for arguments in (
        ["validate"],
        ["spec", "validate"],
        ["spec", "lint", "--strict"],
        ["agent-handoff", "validate", "--repo", "."],
        ["agent-handoff", "drift-check", "--repo", "."],
    ):
        validation = subprocess.run(
            [
                "python",
                "-c",
                f"from project_standards.cli import main; raise SystemExit(main({arguments!r}))",
            ],
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert validation.returncode == 0, validation.stdout + validation.stderr

    command_tree = _file_tree(checkout)
    package_commands = (
        ["fix", "--quiet", "CHANGELOG.md"],
        ["spec", "extract", "standards/project-spec/examples/spec.example.md", "§7", "--json"],
        ["spec", "next", "standards/project-spec/examples/spec.example.md", "FR", "--json"],
        ["agent-handoff", "size-report", "--repo", ".", "--json"],
        ["agent-handoff", "shape-check", "--repo", ".", "--json"],
        ["agent-handoff", "legacy-report", "--repo", ".", "--json"],
        ["agent-handoff", "upgrade", "--repo", ".", "--json"],
        ["render", "cli-documentation", "render-workflow", "--repo", "."],
    )
    for arguments in package_commands:
        command = subprocess.run(
            [
                "python",
                "-c",
                f"from project_standards.cli import main; raise SystemExit(main({arguments!r}))",
            ],
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert command.returncode == 0, command.stdout + command.stderr

    new_spec = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; "
            "raise SystemExit(main(['spec', 'new', '--profile', 'light', '--id', "
            "'SPEC-TMP1', '--title', 'Temporary release proof', '--stdout']))",
        ],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert new_spec.returncode == 0, new_spec.stderr
    temporary_spec = checkout / "release-proof-spec.md"
    temporary_spec.write_text(new_spec.stdout, encoding="utf-8")
    upgrade_spec = subprocess.run(
        [
            "python",
            "-c",
            "from project_standards.cli import main; "
            "raise SystemExit(main(['spec', 'upgrade', 'release-proof-spec.md', "
            "'--to', 'standard', '--stdout']))",
        ],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
    )
    temporary_spec.unlink()
    assert upgrade_spec.returncode == 0, upgrade_spec.stderr
    assert _file_tree(checkout) == command_tree

    patch_checkout = Path(
        shutil.copytree(source_snapshot, tmp_path / "patch-checkout", symlinks=True)
    )
    initialize_release_baseline(patch_checkout)
    mirror_release_tree(checkout, patch_checkout)
    migration_patch = release_patch(patch_checkout)
    assert migration_patch.patch
    assert len(migration_patch.patch_sha256) == 64
    changed_paths = {path for row in migration_patch.ledger for path in row.split("\t")[1:]}
    assert ".standards/config.toml" in changed_paths
    assert ".standards/catalog.toml" in changed_paths
    assert ".standards/lock.toml" in changed_paths
    assert ".project-standards.yml" in changed_paths
    replay = _replay_migration_patch(
        source_snapshot,
        tmp_path / "replay",
        migration_patch.patch,
    )
    assert release_candidate_helpers.git_known_file_tree(replay) == (
        release_candidate_helpers.git_known_file_tree(checkout)
    )
    assert (
        release_candidate_helpers.snapshot_regular_files(
            checkout,
            frozenset(reconstructed.preserved_create_only),
        )
        == reconstructed.preserved_create_only
    )
    return _MigrationProofResult(
        completed_authority=checkout,
        completed_tree=release_candidate_helpers.git_known_file_tree(checkout),
        dev_group_alignment=alignment,
        check_task_alignment=task_alignment,
        dev_group_lock=lock_by_unit[("pyproject.toml", "key:/dependency-groups/dev")],
        check_task_lock=lock_by_unit[(".vscode/tasks.json", "keyed-set:/tasks#label=check")],
        migration_patch=migration_patch,
        digests=_ControlPlaneDigests(
            config=sha256((checkout / ".standards/config.toml").read_bytes()).hexdigest(),
            catalog=sha256((checkout / ".standards/catalog.toml").read_bytes()).hexdigest(),
            lock=sha256((checkout / ".standards/lock.toml").read_bytes()).hexdigest(),
        ),
    )


def test_disposable_release_checkout_migrates_and_reaches_fixed_point(
    tmp_path: Path,
) -> None:
    source_root = release_candidate_helpers.resolve_release_replay_source_root()
    predecessor_a = _reconstruct_predecessor(source_root, tmp_path / "predecessor-a")
    result_a = _execute_migration_proof(predecessor_a, tmp_path / "run-a")

    predecessor_b = _reconstruct_predecessor(
        result_a.completed_authority,
        tmp_path / "predecessor-b",
    )
    assert predecessor_b.tree == predecessor_a.tree
    assert predecessor_b.overlay == predecessor_a.overlay
    assert predecessor_b.preserved_create_only == predecessor_a.preserved_create_only

    result_b = _execute_migration_proof(predecessor_b, tmp_path / "run-b")

    assert result_b.dev_group_alignment == result_a.dev_group_alignment
    assert result_b.check_task_alignment == result_a.check_task_alignment
    assert result_b.dev_group_lock == result_a.dev_group_lock
    assert result_b.check_task_lock == result_a.check_task_lock
    assert result_b.migration_patch == result_a.migration_patch
    assert result_b.digests == result_a.digests
    assert result_b.completed_tree == result_a.completed_tree

    evidence_record = {
        "schema_version": 1,
        "check_task_alignment": {
            "before_semantic_digest": result_a.check_task_alignment.before_semantic_digest,
            "after_semantic_digest": result_a.check_task_alignment.after_semantic_digest,
            "mutated": result_a.check_task_alignment.mutated,
            "post_alignment_sha256": result_a.check_task_alignment.post_alignment_sha256,
            "rendered_content_digest": result_a.check_task_alignment.rendered_content_digest,
            "source_sha256": result_a.check_task_alignment.source_sha256,
        },
        "control_plane_sha256": {
            "catalog.toml": result_a.digests.catalog,
            "config.toml": result_a.digests.config,
            "lock.toml": result_a.digests.lock,
        },
        "dev_group_alignment": {
            "before_semantic_digest": result_a.dev_group_alignment.before_semantic_digest,
            "after_semantic_digest": result_a.dev_group_alignment.after_semantic_digest,
            "mutated": result_a.dev_group_alignment.mutated,
            "rendered_content_digest": result_a.dev_group_alignment.rendered_content_digest,
            "source_sha256": result_a.dev_group_alignment.source_sha256,
        },
        "migration_ledger": list(result_a.migration_patch.ledger),
        "migration_patch_sha256": result_a.migration_patch.patch_sha256,
        "release_input_sha256": release_candidate_helpers.release_input_digest(source_root),
    }
    print(
        "RELEASE_EVIDENCE_JSON="
        + json.dumps(evidence_record, separators=(",", ":"), sort_keys=True)
    )
    if os.environ.get("PROJECT_STANDARDS_REFRESH_RELEASE_EVIDENCE") != "1":
        release_candidate_helpers.assert_release_evidence_current(
            source_root,
            expected_record=evidence_record,
        )
