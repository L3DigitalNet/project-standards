"""Tests for the new-family integration preflight (issue #134).

The synthetic fixture builds a family that makes all nine sites applicable at
once, so a test can remove exactly one declaration and observe exactly one
site change verdict. One test additionally runs against the live repository:
it is both the issue's acceptance criterion and the guard that keeps the site
inventory honest, because a renamed binding fails it loudly.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pytest import CaptureFixture

_REPO = Path(__file__).resolve().parent.parent


def _module() -> ModuleType:
    path = _REPO / "scripts" / "family_preflight.py"
    spec = importlib.util.spec_from_file_location("family_preflight", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


FAMILY = "demo-family"

_PAYLOAD = """
schema_version = "1.0"

[payload]
standard = "demo-family"
version = "1.0"
availability = "consumer"

[config]
schema_resource = "config-schema"

[[resources]]
id = "config-schema"
path = "config.schema.json"

[[contributions]]
id = "agents-instructions"
target = "AGENTS.md"
adapter = "markdown-block"

[[providers]]
id = "validate"
operation = "validate"
kind = "python"
phase = "validate"
effect = "findings"
"""

_SITE_SOURCES = {
    "tests/package_compatibility/matrix.py": '_MINIMAL_PACKAGE_CONFIG = {"demo-family": {}}\n',
    "tests/test_standards_composition.py": '_CATALOG_NATIVE_FAMILIES = {"demo-family"}\n',
    "tests/control_plane/test_command_resolution.py": (
        '_SEAM_FAMILIES = {"demo-family": ()}\n'
        '_DEMO_DECLARED_PATHS = (".agents/skills/demo-family/SKILL.md",)\n'
    ),
    "tests/mcp_services/test_providers.py": (
        'AUTHORITATIVE_INPUT_OWNER = {("demo-family", "validate"): "family"}\n'
    ),
    "src/project_standards/control_plane/provider_inputs.py": (
        '_DEMO_READ_PATHS = (".agents/skills/demo-family/SKILL.md",)\n'
        "\n"
        "def _dispatch(owner):\n"
        '    return owner == "demo-family"\n'
    ),
    "tests/test_repository_hygiene.py": (
        "_POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES = frozenset(\n"
        '    {"standards/demo-family/versions/1.0/bin/tool"}\n'
        ")\n"
    ),
    "tests/package_contract/test_release_consistency.py": (
        '_LIVE_SHALLOW_FAMILY_CORPUS = {"standards/demo-family/README.md"}\n'
    ),
    "tests/agent_handoff/test_selected_routing.py": (
        "def test_managed_markdown_snapshot_spans_all_packages_while_local_units_stay_local():\n"
        '    owners = ("demo-family",)\n'
        "    return owners\n"
    ),
}


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A synthetic checkout where every one of the nine sites is declared."""
    _write(
        tmp_path,
        "catalogs/5.toml",
        '[[packages]]\nid = "demo-family"\nversion = "1.0"\nrole = "default"\n',
    )
    _write(tmp_path, ".standards/config.toml", "[standards.demo-family]\nenabled = true\n")
    _write(
        tmp_path,
        f"standards/{FAMILY}/standard.toml",
        '[[versions]]\nversion = "1.0"\n',
    )
    _write(tmp_path, f"standards/{FAMILY}/versions/1.0/payload.toml", _PAYLOAD)
    _write(
        tmp_path,
        f"standards/{FAMILY}/versions/1.0/config.schema.json",
        json.dumps({"required": ["organization"], "properties": {"organization": {}}}),
    )
    executable = _write(tmp_path, f"standards/{FAMILY}/versions/1.0/bin/tool", "#!/bin/sh\n")
    executable.chmod(0o755)
    for relative, source in _SITE_SOURCES.items():
        _write(tmp_path, relative, source)
    return tmp_path


def _report(root: Path, family: str = FAMILY) -> tuple[int, list[dict[str, object]]]:
    """Run the preflight and flatten its verdicts into plain dictionaries."""
    _facts, results = _module().inspect_family(root, family)
    sites: list[dict[str, object]] = [
        {
            "number": int(result.number),
            "status": str(result.status),
            "probes": [str(probe.status) for probe in result.probes],
        }
        for result in results
    ]
    code = 1 if any(site["status"] == "missing" for site in sites) else 0
    return code, sites


def _site(sites: list[dict[str, object]], number: int) -> dict[str, object]:
    match = [item for item in sites if item["number"] == number]
    assert match, f"no site numbered {number}"
    return match[0]


def _run(root: Path, family: str = FAMILY) -> int:
    """Invoke the real entry point the way an operator would."""
    return int(_module().main([family, "--root", str(root)]))


def test_preflight__fully_declared_family__reports_every_site_declared(repo: Path) -> None:
    code, sites = _report(repo)
    assert code == 0
    assert len(sites) == 9
    assert [item["status"] for item in sites] == ["declared"] * 9


def test_preflight__removed_seam_key__reports_only_that_site_missing(repo: Path) -> None:
    """Removing one declaration must move exactly one site, not the whole report."""
    _write(
        repo,
        "tests/control_plane/test_command_resolution.py",
        '_SEAM_FAMILIES = {}\n_DEMO_DECLARED_PATHS = (".agents/skills/demo-family/SKILL.md",)\n',
    )
    code, sites = _report(repo)
    assert code == 1
    assert _site(sites, 5)["status"] == "missing"
    others = [item for item in sites if item["number"] != 5]
    assert all(item["status"] == "declared" for item in others)


def test_preflight__removed_dispatch_branch__is_distinguished_from_the_read_set(
    repo: Path,
) -> None:
    """The two probes over one module must stay independent.

    The artifact path still mentions the family, so a file-level check would
    call site 7 declared. Only the exact-match probe sees the loss.
    """
    _write(
        repo,
        "src/project_standards/control_plane/provider_inputs.py",
        '_DEMO_READ_PATHS = (".agents/skills/demo-family/SKILL.md",)\n',
    )
    code, sites = _report(repo)
    assert code == 1
    site = _site(sites, 7)
    assert site["status"] == "missing"
    assert site["probes"] == ["missing", "declared"]


def test_preflight__family_without_executables__reports_the_allowlist_not_applicable(
    repo: Path,
) -> None:
    (repo / f"standards/{FAMILY}/versions/1.0/bin/tool").chmod(0o644)
    _write(
        repo,
        "tests/test_repository_hygiene.py",
        "_POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES = frozenset()\n",
    )
    code, sites = _report(repo)
    assert code == 0
    assert _site(sites, 8)["status"] == "not applicable"


def test_preflight__plan_bound_family__treats_the_seam_sites_as_not_applicable(
    repo: Path,
) -> None:
    """A family the census gives to the executor must not be reported missing.

    This pins the real behaviour for `markdown-tooling` and `python-tooling`,
    which declare the same provider shape as a seam family and are deliberately
    absent from the seam wiring.
    """
    _write(
        repo,
        "tests/mcp_services/test_providers.py",
        'AUTHORITATIVE_INPUT_OWNER = {("demo-family", "validate"): "plan-bound"}\n',
    )
    _write(repo, "tests/control_plane/test_command_resolution.py", "_SEAM_FAMILIES = {}\n")
    _write(repo, "src/project_standards/control_plane/provider_inputs.py", "READ_PATHS = ()\n")
    code, sites = _report(repo)
    assert code == 0
    assert _site(sites, 5)["status"] == "not applicable"
    assert _site(sites, 7)["status"] == "not applicable"
    assert _site(sites, 6)["status"] == "declared"


def test_preflight__family_absent_from_the_census__still_reports_the_seam_sites(
    repo: Path,
) -> None:
    """An undecided authority must report the sites, never hide them."""
    _write(repo, "tests/mcp_services/test_providers.py", "AUTHORITATIVE_INPUT_OWNER = {}\n")
    _write(repo, "tests/control_plane/test_command_resolution.py", "_SEAM_FAMILIES = {}\n")
    code, sites = _report(repo)
    assert code == 1
    assert _site(sites, 5)["status"] == "missing"
    assert _site(sites, 6)["status"] == "missing"


def test_preflight__renamed_binding__fails_as_a_stale_inventory(repo: Path) -> None:
    """A renamed collection is a tool defect, not a missing declaration."""
    module = _module()
    _write(repo, "tests/test_standards_composition.py", "_RENAMED = {'demo-family'}\n")
    with pytest.raises(module.PreflightError, match="stale site inventory"):
        module.inspect_family(repo, FAMILY)


def test_preflight__unknown_family__exits_with_a_usage_error(
    repo: Path, capsys: CaptureFixture[str]
) -> None:
    assert _run(repo, "no-such-family") == 2
    assert "unknown family" in capsys.readouterr().err


def test_preflight__missing_declaration__exit_code_distinguishes_it_from_success(
    repo: Path, capsys: CaptureFixture[str]
) -> None:
    """Exercise the real entry point, not just the library call."""
    assert _run(repo) == 0
    capsys.readouterr()
    _write(repo, "tests/test_standards_composition.py", "_CATALOG_NATIVE_FAMILIES = set()\n")
    assert _run(repo) == 1
    assert "1 site(s) missing: 4" in capsys.readouterr().out


def test_preflight__live_repository__github_workflow_is_fully_declared(
    capsys: CaptureFixture[str],
) -> None:
    """Issue #134 acceptance criterion, and the guard against inventory rot.

    Every site inventory entry is exercised against the real tree here, so a
    renamed binding or moved file fails this test instead of silently turning
    a future family's report into false comfort.
    """
    assert _run(_REPO, "github-workflow") == 0
    assert "every applicable site is declared" in capsys.readouterr().out
