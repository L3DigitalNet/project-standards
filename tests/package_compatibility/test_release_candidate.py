from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from project_standards.control_plane.codec import parse_config, parse_lock
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.migration import plan_legacy_migration
from tests.package_compatibility import release_candidate as release_candidate_helpers
from tests.package_compatibility.release_candidate import (
    assert_release_evidence_current,
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
    evidence.write_text(f"Release-input SHA-256: `{digest}`\n", encoding="utf-8")
    preflight = release_candidate_helpers.assert_release_evidence_current

    preflight(source)
    tracked.write_text("stale\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="release evidence is stale"):
        preflight(source)


def test_disposable_checkout_builds_release_without_mutating_source(tmp_path: Path) -> None:
    source_versions = {path: (_ROOT / path).read_bytes() for path in ("pyproject.toml", "uv.lock")}
    checkout = copy_tracked_checkout(tmp_path / "checkout")
    set_release_version(checkout)
    installed = build_installed_release(checkout, tmp_path / "build")
    environment = {**os.environ, "PYTHONPATH": str(installed)}

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


def test_disposable_release_checkout_migrates_and_reaches_fixed_point(
    tmp_path: Path,
) -> None:
    assert_release_evidence_current()
    source_snapshot = copy_tracked_checkout(tmp_path / "source-snapshot")
    checkout = Path(shutil.copytree(source_snapshot, tmp_path / "checkout", symlinks=True))
    set_release_version(checkout)
    declare_release_cut_intent(checkout)
    installed = build_installed_release(checkout, tmp_path / "build")
    distribution = InstalledDistribution(
        installed / "project_standards",
        tool_release="5.0.0",
    )
    handoff_before = {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in (checkout / "docs/handoff").rglob("*")
        if path.is_file()
    }
    workflows_before = {
        path: (checkout / path).read_bytes()
        for path in (
            ".github/workflows/format.yml",
            ".github/workflows/lint-markdown.yml",
            ".github/workflows/validate-specs.yml",
        )
    }

    environment = {**os.environ, "PYTHONPATH": str(installed)}
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
    assert json_preview["applicable"] is True

    preview = plan_legacy_migration(checkout, distribution, "5")
    assert preview.applicable, "\n".join(
        f"{finding.code} {finding.standard_id} {finding.path} {finding.identity}"
        for finding in preview.findings
    )
    expected_actions = {action.target for action in preview.actions}
    assert {action["target"] for action in json_preview["plan"]["actions"]} == expected_actions
    assert all(target in preview_outputs[0] for target in expected_actions)
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
    assert {
        path.relative_to(checkout).as_posix(): path.read_bytes()
        for path in (checkout / "docs/handoff").rglob("*")
        if path.is_file()
    } == handoff_before
    lock = parse_lock((checkout / ".standards/lock.toml").read_bytes())
    assert lock == preview.reconciliation.next_lock
    config = parse_config((checkout / ".standards/config.toml").read_bytes())
    assert config.standards["markdown-tooling"].config["workflow_mode"] == "self-hosted"
    assert config.standards["project-spec"].config["workflow_mode"] == "self-hosted"
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

    before = _file_tree(checkout)
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
    assert _file_tree(checkout) == before

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
    patch, changed_paths, patch_digest = release_patch(patch_checkout)
    assert patch
    assert len(patch_digest) == 64
    assert ".standards/config.toml" in changed_paths
    assert ".standards/catalog.toml" in changed_paths
    assert ".standards/lock.toml" in changed_paths
    assert ".project-standards.yml" in changed_paths
    replay = Path(shutil.copytree(source_snapshot, tmp_path / "replay", symlinks=True))
    replay_release_patch(replay, patch)
    assert _file_tree(replay) == _file_tree(checkout)
    evidence = (
        _ROOT / "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
    ).read_text(encoding="utf-8")
    expected_evidence = {"release patch": patch_digest}
    for name in ("config.toml", "catalog.toml", "lock.toml"):
        expected_evidence[name] = sha256((checkout / ".standards" / name).read_bytes()).hexdigest()
    missing = {name: digest for name, digest in expected_evidence.items() if digest not in evidence}
    assert not missing, "release evidence is missing current digests:\n" + "\n".join(
        f"{name}: {digest}" for name, digest in missing.items()
    )
