"""Installed-wrapper smoke (spec §8, codex SA-005 + SA-NEW-001): build the wheel,
install into a throwaway venv via the venv's own seeded pip, run every console
script via the installed wrapper. Slowest test in the suite alongside
test_adopt_packaging.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.projection import (
    plan_payload_projection,
    sync_payload_projection,
)

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = tuple(
    tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
)


def _venv_environment(**extra: str) -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": "", **extra}


@pytest.fixture(scope="module")
def installed_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("wheel-smoke")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp)],
        cwd=_ROOT,
        check=True,
        capture_output=True,
    )
    (wheel,) = tmp.glob("*.whl")
    venv = tmp / "venv"
    subprocess.run(["uv", "venv", "--seed", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [str(venv / "bin" / "python"), "-m", "pip", "install", "--quiet", str(wheel)],
        env=_venv_environment(),
        check=True,
        capture_output=True,
    )
    return venv


@pytest.fixture(scope="module")
def migration_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a real v5 fixture wheel with the synthetic migration payload embedded."""
    tmp = tmp_path_factory.mktemp("migration-wheel")
    source = tmp / "source"
    shutil.copytree(
        _ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            "build",
            "dist",
        ),
    )
    fixture = source / "tests/fixtures/package_contract/valid/full"
    shutil.rmtree(source / "standards")
    shutil.copytree(fixture / "standards", source / "standards")
    shutil.rmtree(source / "catalogs")
    shutil.copytree(fixture / "catalogs", source / "catalogs")
    for projection in ("catalogs", "families", "payloads"):
        shutil.rmtree(source / "src/project_standards" / projection)

    provider = source / "standards/alpha/versions/2.0/provider.py"
    original_provider = provider.read_bytes()
    recognized = (
        '["/agent_handoff", "/cli_documentation", "/markdown", '
        '"/markdown_tooling", "/python_tooling", "/spec"]'
    )
    provider.write_text(
        original_provider.decode().replace('["/alpha/enabled"]', recognized),
        encoding="utf-8",
    )
    old_provider_digest = hashlib.sha256(original_provider).hexdigest()
    new_provider_digest = hashlib.sha256(provider.read_bytes()).hexdigest()
    payload_path = provider.with_name("payload.toml")
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8").replace(
            f"sha256:{old_provider_digest}",
            f"sha256:{new_provider_digest}",
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    aggregate = validate_payload_integrity(payload_path.parent, manifest).aggregate_digest.value
    old_aggregate = "sha256:c1666aee5b8d0bbf35bf771c4539012a1c5c7fbd3f5aeb5d99bc7f0ba18b69e9"
    for path in (
        source / "standards/alpha/standard.toml",
        source / "catalogs/5.toml",
    ):
        path.write_text(
            path.read_text(encoding="utf-8").replace(old_aggregate, aggregate),
            encoding="utf-8",
        )

    pyproject = source / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'version = "4.3.0"',
            'version = "5.0.0"',
            1,
        ),
        encoding="utf-8",
    )
    assert sync_payload_projection(source, check=False) == ()
    wheel_dir = tmp / "wheel"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=source,
        check=True,
        capture_output=True,
    )
    (wheel,) = wheel_dir.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
    assert "project_standards/catalogs/5.toml" in members
    assert "project_standards/payloads/alpha/2.0/payload.toml" in members

    venv = tmp / "venv"
    subprocess.run(["uv", "venv", "--seed", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [str(venv / "bin/python"), "-m", "pip", "install", "--quiet", str(wheel)],
        env=_venv_environment(),
        check=True,
        capture_output=True,
    )
    return venv


@pytest.fixture(scope="module")
def selected_command_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the current catalog as a v5 wheel for offline public-command routing."""
    tmp = tmp_path_factory.mktemp("selected-command-wheel")
    source = tmp / "source"
    shutil.copytree(
        _ROOT,
        source,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            "build",
            "dist",
        ),
    )
    pyproject = source / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            'version = "4.3.0"',
            'version = "5.0.0"',
            1,
        ),
        encoding="utf-8",
    )
    wheel_dir = tmp / "wheel"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=source,
        check=True,
        capture_output=True,
    )
    (wheel,) = wheel_dir.glob("*.whl")
    venv = tmp / "venv"
    subprocess.run(["uv", "venv", "--seed", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [str(venv / "bin/python"), "-m", "pip", "install", "--quiet", str(wheel)],
        env=_venv_environment(),
        check=True,
        capture_output=True,
    )
    return venv


def _run(venv: Path, cmd: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = _venv_environment(NO_COLOR="1", COLUMNS="100")
    return subprocess.run([str(venv / "bin" / cmd), *args], capture_output=True, text=True, env=env)


def test_installed_wheel_matches_every_catalog_advertised_source_byte(
    installed_venv: Path,
) -> None:
    located = subprocess.run(
        [
            str(installed_venv / "bin/python"),
            "-c",
            "import pathlib, project_standards; print(pathlib.Path(project_standards.__file__).parent)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_venv_environment(),
    )
    installed_root = Path(located.stdout.strip())
    source_root = _ROOT / "src/project_standards"

    for link in plan_payload_projection(_ROOT).links:
        relative = link.destination.relative_to(source_root)
        installed = installed_root / relative
        assert installed.is_file(), relative
        assert not installed.is_symlink(), relative
        assert installed.read_bytes() == link.source.read_bytes(), relative


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_help_exits_zero(installed_venv: Path, script: str) -> None:
    proc = _run(installed_venv, script, "--help")
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("script", _SCRIPTS)
def test_wrapper_version_prints_exact_contract(installed_venv: Path, script: str) -> None:
    # The standard's contract is EXACT "<script-name> <version>" (codex CR-004): the
    # installed wrapper name is sys.argv[0], so argparse %(prog)s, the sync mains'
    # Path(sys.argv[0]).name, and cli.py's literal all resolve to the script name here.
    from project_standards._version import package_version

    proc = _run(installed_venv, script, "--version")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == f"{script} {package_version()}"


def test_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "spec", "validate", "--help")
    assert proc.returncode == 0, proc.stderr


def test_standards_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "standards", "validate-graph", "--help")
    assert proc.returncode == 0, proc.stderr


def test_control_plane_subcommands_via_wrapper(installed_venv: Path) -> None:
    init = _run(installed_venv, "project-standards", "init", "--help")
    assert init.returncode == 0, init.stderr
    assert "--migrate" in init.stdout
    assert "--apply" in init.stdout

    reconcile = _run(installed_venv, "project-standards", "reconcile", "--help")
    assert reconcile.returncode == 0, reconcile.stderr
    assert "--repair-state" in reconcile.stdout

    catalog = _run(installed_venv, "project-standards", "standards", "list", "--help")
    assert catalog.returncode == 0, catalog.stderr
    assert "--json" in catalog.stdout


def test_installed_v5_wheel_migrates_all_legacy_namespaces_offline_at_fixed_point(
    migration_venv: Path,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    shutil.copyfile(
        _ROOT / "tests/fixtures/package_compatibility/legacy/all-namespaces/.project-standards.yml",
        repo / ".project-standards.yml",
    )
    shutil.copyfile(
        _ROOT / "tests/fixtures/package_contract/valid/full/standards/alpha/versions/2.0/legacy.md",
        repo / "legacy-alpha.md",
    )
    extension = repo / "config/alpha-options.toml"
    extension.parent.mkdir()
    extension.write_text("consumer = true\n", encoding="utf-8")
    script = """
import socket
import sys
from pathlib import Path

from project_standards.cli import main

repo = Path(sys.argv[1])

def deny_network(*_args, **_kwargs):
    raise AssertionError("installed migration attempted network access")

def tree():
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

socket.socket = deny_network
assert main(["init", "--catalog", "5", "--migrate", "--apply", "--repo", str(repo)]) == 0
before = tree()
assert main(["reconcile", "--apply", "--repo", str(repo)]) == 0
assert tree() == before
"""
    result = subprocess.run(
        [str(migration_venv / "bin/python"), "-c", script, str(repo)],
        env=_venv_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not (repo / ".project-standards.yml").exists()
    assert (repo / ".standards/lock.toml").is_file()


def test_package_authoring_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "standards", "validate-packages", "--help")
    assert proc.returncode == 0, proc.stderr


def test_package_release_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "packages", "check-release", "--help")
    assert proc.returncode == 0, proc.stderr


def test_agent_handoff_nested_subcommand_via_wrapper(installed_venv: Path) -> None:
    proc = _run(installed_venv, "project-standards", "agent-handoff", "--help")
    assert proc.returncode == 0, proc.stderr


def test_selected_provider_commands_run_from_wheel_with_network_denied(
    selected_command_venv: Path,
    tmp_path: Path,
) -> None:
    script = r"""
import os
import socket
import sys
from pathlib import Path

from project_standards.cli import main
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.format_frontmatter import main as format_frontmatter
from project_standards.validate_frontmatter import main as validate_frontmatter
from project_standards.validate_id import main as validate_id
from project_standards.validate_references import main as validate_references


def deny_network(*_args, **_kwargs):
    raise AssertionError("provider command attempted network access")


socket.socket = deny_network
base = Path(sys.argv[1]).resolve()


def initialize(name, standards):
    repo = base / name
    repo.mkdir()
    assert main(["init", "--catalog", "5", "--repo", str(repo)]) == 0
    for standard in standards:
        set_standard_enabled(repo, standard, True)
    assert main(["reconcile", "--apply", "--repo", str(repo)]) == 0
    return repo


agent = initialize("agent", ["agent-handoff"])
for command in ("validate", "size-report", "shape-check", "drift-check", "legacy-report"):
    assert main(["agent-handoff", command, "--repo", str(agent), "--json"]) == 0
assert main(["agent-handoff", "upgrade", "--repo", str(agent), "--json"]) == 0

frontmatter = initialize("frontmatter", ["markdown-frontmatter"])
docs = frontmatter / "docs"
docs.mkdir()
note = docs / "note.md"
note.write_text(
    "---\n"
    "schema_version: '1.1'\n"
    "id: wrong\n"
    "title: Hello World\n"
    "description: A note.\n"
    "doc_type: note\n"
    "status: draft\n"
    "created: '2026-07-12'\n"
    "updated: '2026-07-12'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n# Hello World\n",
    encoding="utf-8",
)
os.chdir(frontmatter)
assert main(["fix", "--quiet", "docs/note.md"]) == 0
assert main(["validate", "--quiet", "docs/note.md"]) == 0
assert validate_frontmatter(["--quiet", "docs/note.md"]) == 0
assert validate_id(["--quiet", "docs/note.md"]) == 0
assert validate_references(["--quiet", "docs/note.md"]) == 0
assert format_frontmatter(["--check", "--quiet", "docs/note.md"]) == 0
standalone = docs / "standalone.md"
standalone.write_text(
    note.read_text(encoding="utf-8").replace("id: 'note-", "id: 'wrong-", 1),
    encoding="utf-8",
)
assert validate_id(["--fix", "--quiet", "docs/standalone.md"]) == 0
standalone.write_text(
    standalone.read_text(encoding="utf-8").replace("title: 'Hello World'", "title: Hello World"),
    encoding="utf-8",
)
assert format_frontmatter(["--write", "--quiet", "docs/standalone.md"]) == 0

set_standard_enabled(frontmatter, "adr", True)
config = frontmatter / ".standards/config.toml"
config.write_text(
    config.read_text(encoding="utf-8")
    + "\n[standards.adr.config]\nrequire_sections = true\n",
    encoding="utf-8",
)
assert main(["reconcile", "--apply", "--repo", str(frontmatter)]) == 0
adr = docs / "adr.md"
adr.write_text(note.read_text(encoding="utf-8").replace("doc_type: 'note'", "doc_type: 'adr'").replace(
    "id: 'note-", "id: 'adr-0001-"
), encoding="utf-8")
assert main(["validate", "--quiet", "docs/adr.md"]) == 1

spec = initialize("spec", ["project-spec"])
os.chdir(spec)
source = Path("docs/specs/example.md")
source.parent.mkdir(parents=True)
assert main(["spec", "new", "--profile", "light", "--id", "SPEC-7F3Q", str(source)]) == 0
assert main(["spec", "validate", str(source)]) == 0
assert main(["spec", "extract", "--json", str(source), "§7"]) == 0
assert main(["spec", "next", "--json", str(source), "FR"]) == 0
assert main(["spec", "lint", "--json", str(source)]) in {0, 1}
assert main([
    "spec", "upgrade", str(source), "--to", "standard", "-o", "docs/specs/standard.md"
]) == 0
assert main(["render", "project-spec", "render-workflow", "--repo", str(spec)]) == 0
"""
    result = subprocess.run(
        [str(selected_command_venv / "bin/python"), "-c", script, str(tmp_path)],
        env=_venv_environment(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
