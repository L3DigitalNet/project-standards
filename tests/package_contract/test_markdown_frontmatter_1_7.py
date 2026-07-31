"""markdown-frontmatter 1.7 registration and the issue #97 uv-strict shim fix.

The installed `new-doc-id` helper embeds two Python steps. Through 1.6 both were
started as bare `python3 -`, which the uv-strict-python shims that this project's
own guidance tells operators to deploy reject with exit 1 before any code runs.
The skill names that helper as the only sanctioned id source and the file is
lock-owned, so a consumer following both standards could not generate an id and
could not fix it locally either. 1.7 starts both steps with `uv run python3 -`.

The behavioral tests run the real script under a stand-in `python3` that refuses
a bare invocation exactly as the shim does, plus a stand-in `uv` that forwards to
the interpreter running the suite. That is what makes the 1.6 leg fail and the
1.7 leg pass for the reported reason rather than by string inspection alone.
"""

from __future__ import annotations

import re
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_PREDECESSOR = _FAMILY / "versions/1.6"
_SUCCESSOR = _FAMILY / "versions/1.7"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.7"
_PREDECESSOR_DIGEST = "sha256:cf1e2c975d5f139f1b3864090e6fcc0e45dcb895a97dd07113c0eeb7af0d0f32"
_SCRIPT = "skills/markdown-frontmatter/scripts/new-doc-id"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
        _SCRIPT,
    }
)
_ID = re.compile(r"^note-[0-9a-z]{6}-example-document$")


def _shim_path(tmp_path: Path) -> str:
    """Build a PATH whose `python3` refuses bare use and whose `uv` forwards.

    This reproduces the reported environment rather than the reported command:
    the uv-strict shim rejects `python3` outright, so any surviving bare call
    site fails here regardless of how the script is written.
    """
    bin_dir = tmp_path / "shim-bin"
    bin_dir.mkdir()
    python3 = bin_dir / "python3"
    python3.write_text(
        "#!/usr/bin/env bash\n"
        'printf "ERROR: Use \\`uv run python3 %s\\` instead of \\`python3 %s\\`\\n" '
        '"$*" "$*" >&2\n'
        "exit 1\n",
        encoding="utf-8",
    )
    uv = bin_dir / "uv"
    uv.write_text(
        f'#!/usr/bin/env bash\nif [[ "$1" == "run" ]]; then shift; fi\n'
        f'if [[ "$1" == "python3" || "$1" == "python" ]]; then shift; fi\n'
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    for executable in (python3, uv):
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return f"{bin_dir}:/usr/bin:/bin"


def _run_new_doc_id(version_root: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(version_root / _SCRIPT), "--doc-type", "note", "example document"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PATH": _shim_path(tmp_path), "HOME": str(tmp_path)},
        check=False,
    )


def test_markdown_frontmatter_1_7__predecessor__still_fails_under_the_shim(
    tmp_path: Path,
) -> None:
    """Characterize 1.6 so the 1.7 result is attributable to the fix (issue #97)."""
    result = _run_new_doc_id(_PREDECESSOR, tmp_path)

    assert result.returncode == 1
    assert "instead of" in result.stderr
    assert result.stdout == ""


def test_markdown_frontmatter_1_7__helper__generates_an_id_under_the_shim(
    tmp_path: Path,
) -> None:
    """The sanctioned id generator works in a uv-strict environment."""
    result = _run_new_doc_id(_SUCCESSOR, tmp_path)

    assert result.returncode == 0, result.stderr
    assert _ID.fullmatch(result.stdout.strip()), result.stdout


def test_markdown_frontmatter_1_7__scaffold_step__also_runs_through_uv(tmp_path: Path) -> None:
    """The second call site is the scaffold title, which only `--scaffold` reaches.

    Fixing one call site would leave this path broken, so the scaffold output is
    exercised separately instead of trusting a single invocation to cover both.
    """
    result = subprocess.run(
        [
            "/bin/bash",
            str(_SUCCESSOR / _SCRIPT),
            "--scaffold",
            "--doc-type",
            "note",
            "example document",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PATH": _shim_path(tmp_path), "HOME": str(tmp_path)},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "title: 'Example Document'" in result.stdout


def test_markdown_frontmatter_1_7__helper__has_no_bare_python_call_site() -> None:
    """No call site may regress to bare `python3 -`, including any added later."""
    text = (_SUCCESSOR / _SCRIPT).read_text(encoding="utf-8")
    call_sites = re.findall(r"(?m)^.*\bpython3 -\s*<<", text)

    assert len(call_sites) == 2
    assert all("uv run python3 -" in site for site in call_sites)


def test_markdown_frontmatter_1_7__provider_schema__binds_the_successor_identity() -> None:
    schema = (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")

    assert '"version": { "const": "1.7" }' in schema


def test_markdown_frontmatter_1_7__successor__is_complete_and_immutable() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.7"
    assert successor_manifest.payload.availability.value == "consumer"
    assert indexed["1.7"].digest == successor_integrity.aggregate_digest


def test_markdown_frontmatter_1_7__catalog_role__selects_the_successor_as_default() -> None:
    """Catalog 5 must actually select the successor these tests pin.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes the successor the default a consumer on
    `version = "latest"` resolves to.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "markdown-frontmatter"
    }

    assert roles["1.7"] == "default"
    assert roles["1.6"] == "retained"


def test_markdown_frontmatter_1_7__payload_projection__matches_complete_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


@pytest.mark.parametrize("mode", ["0755"])
def test_markdown_frontmatter_1_7__helper_artifact__keeps_its_executable_mode(mode: str) -> None:
    """The fix must not disturb the declared install mode of the helper."""
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    artifact = next(item for item in manifest.artifacts if item.id == "skill-new-doc-id")

    assert artifact.mode == mode
