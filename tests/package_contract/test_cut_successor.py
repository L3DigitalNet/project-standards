"""`standards cut-successor` behavior, proved against a copy of this repository.

Each case copies the whole repository (~200 MB) once, so the assertions are
deliberately packed into as few test functions as they will fit: splitting them
would let xdist schedule each one on a different worker and pay for the copy
again on every one of them.

The copy excludes `.git`, `build/`, `.venv/`, and the caches — none of them is
read by the package-contract validators, and `.git` alone doubles the cost.
"""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from project_standards.cli import main
from project_standards.package_contract.cut_successor import apply_cut, plan_cut
from project_standards.package_contract.diagnostics import PackageContractError
from tests.module_loading import load_module_from_path

_ROOT = Path(__file__).resolve().parents[2]
# python-coding is the smallest family in the repository (four payload files) and
# is reference-only, which is what pins the role-inheritance rule below: a family
# with no default must not acquire one as a side effect of a cut.
_SMALLEST_FAMILY = "python-coding"
_SKIPPED = {".git", "build", ".venv", "node_modules", ".pytest_cache", ".ruff_cache", "__pycache__"}


def _copy_repository(destination: Path) -> Path:
    def ignore(_directory: str, names: list[str]) -> list[str]:
        return [name for name in names if name in _SKIPPED]

    repository = destination / "repo"
    shutil.copytree(_ROOT, repository, symlinks=True, ignore=ignore)
    return repository


def _next_version(repository: Path, standard_id: str) -> tuple[str, str]:
    """Return the family's highest indexed version and the successor after it."""
    raw = tomllib.loads(
        (repository / "standards" / standard_id / "standard.toml").read_text(encoding="utf-8")
    )
    latest = max(
        (str(entry["version"]) for entry in raw["versions"]),
        key=lambda value: tuple(int(part) for part in value.split(".")),
    )
    major, minor = (int(part) for part in latest.split("."))
    return latest, f"{major}.{minor + 1}"


def _run_module(path: Path) -> None:
    """Import one generated test module and run every test function it defines."""
    module = load_module_from_path(path.stem, path)
    cases = [name for name in dir(module) if name.startswith("test_")]
    assert cases, f"scaffolded module defines no test: {path}"
    for name in cases:
        getattr(module, name)()


def test_cut_successor__end_to_end__leaves_every_repository_validator_green(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _copy_repository(tmp_path)
    predecessor, successor = _next_version(repository, _SMALLEST_FAMILY)
    catalog_path = repository / "catalogs" / "5.toml"
    before = catalog_path.read_bytes()
    invocation = ["standards", "cut-successor", _SMALLEST_FAMILY, successor, "--root"]

    assert main([*invocation, str(repository), "--dry-run"]) == 0
    assert catalog_path.read_bytes() == before
    assert not (repository / "standards" / _SMALLEST_FAMILY / "versions" / successor).exists()

    assert main([*invocation, str(repository), "--scaffold-test"]) == 0
    capsys.readouterr()

    payload_dir = repository / "standards" / _SMALLEST_FAMILY / "versions" / successor
    manifest = tomllib.loads((payload_dir / "payload.toml").read_text(encoding="utf-8"))
    assert manifest["payload"]["version"] == successor

    family = tomllib.loads(
        (repository / "standards" / _SMALLEST_FAMILY / "standard.toml").read_text(encoding="utf-8")
    )
    indexed = {entry["version"]: entry for entry in family["versions"]}
    catalog = tomllib.loads(catalog_path.read_text(encoding="utf-8"))
    advertised = {
        entry["version"]: entry for entry in catalog["packages"] if entry["id"] == _SMALLEST_FAMILY
    }
    assert indexed[successor]["digest"] == advertised[successor]["digest"]
    # Role inheritance, not promotion: python-coding advertises no default, so
    # neither the successor nor the retained predecessor may acquire one.
    assert advertised[successor]["role"] == advertised[predecessor]["role"] == "reference-only"

    for verb in (
        ["standards", "validate-packages"],
        ["standards", "validate-graph"],
        ["standards", "render-catalog", "--check"],
        ["standards", "sync-payload-projection", "--check"],
    ):
        assert main([*verb, "--root", str(repository)]) == 0, capsys.readouterr().out

    module_name = f"test_python_coding_{successor.replace('.', '_')}.py"
    _run_module(repository / "tests" / "package_contract" / module_name)

    # A rerun must refuse rather than overwrite the tree it just wrote, and so
    # must a cut whose directory exists without being indexed — the half-written
    # state a previous interrupted attempt would leave.
    with pytest.raises(PackageContractError, match="already declared"):
        plan_cut(repository, _SMALLEST_FAMILY, successor)
    _indexed, beyond = _next_version(repository, _SMALLEST_FAMILY)
    (repository / "standards" / _SMALLEST_FAMILY / "versions" / beyond).mkdir()
    with pytest.raises(PackageContractError, match="already exists"):
        plan_cut(repository, _SMALLEST_FAMILY, beyond)


def test_cut_successor__migration_endpoints__move_onto_the_successor(tmp_path: Path) -> None:
    # python-tooling carries package-to-package migrations whose `to` endpoint the
    # payload contract requires to name the containing version; a copy that kept
    # the predecessor there would not load at all.
    repository = _copy_repository(tmp_path)
    predecessor, successor = _next_version(repository, "python-tooling")

    result = apply_cut(plan_cut(repository, "python-tooling", successor))

    manifest = tomllib.loads(
        (
            repository / "standards" / "python-tooling" / "versions" / successor / "payload.toml"
        ).read_text(encoding="utf-8")
    )
    assert {migration["to"] for migration in manifest["migrations"]} == {f"package:{successor}"}
    assert result.repointed_migrations
    # `from` endpoints name the versions a consumer is leaving; the cut does not
    # rewrite history, so they carry over from the predecessor unchanged.
    inherited = tomllib.loads(
        (
            repository / "standards" / "python-tooling" / "versions" / predecessor / "payload.toml"
        ).read_text(encoding="utf-8")
    )
    assert {migration["from"] for migration in manifest["migrations"]} == {
        migration["from"] for migration in inherited["migrations"]
    }
    # The predecessor's own bytes are never touched: mutating a released payload
    # is what `packages check-release` classifies as forbidden.
    source = repository / "standards" / "python-tooling" / "versions" / predecessor
    assert (source / "payload.toml").read_bytes() == (
        _ROOT / "standards" / "python-tooling" / "versions" / predecessor / "payload.toml"
    ).read_bytes()
