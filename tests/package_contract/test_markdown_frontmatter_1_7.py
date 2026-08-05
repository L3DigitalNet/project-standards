"""markdown-frontmatter 1.7 registration and the issue #97 uv-strict shim fix.

The installed `new-doc-id` helper embeds two Python steps. Through 1.6 both were
started as bare `python3 -`, which the uv-strict-python shims that this project's
own guidance tells operators to deploy reject with exit 1 before any code runs.
The skill names that helper as the only sanctioned id source and the file is
lock-owned, so a consumer following both standards could not generate an id and
could not fix it locally either. 1.7 starts both steps with `uv run python3 -`.

1.7 dispatches both steps through `$PYTHON_RUNNER`, which resolves to
`uv run --no-project python3 -` when uv is installed and plain `python3 -`
otherwise. The conditional is the point: an unconditional `uv run` exits 127 for
a consumer that has python3 and no uv, and a bare `uv run` (no `--no-project`)
resolves and syncs whatever project surrounds the script.

The behavioral tests run the real script under a stand-in `python3` that refuses
a bare invocation exactly as the shim does, and reach uv through the REAL uv
binary -- a forwarding stand-in would pass regardless of what the script does.
Both dispatch branches are exercised: uv-present under the rejecting shim, and
uv-absent on a PATH with no uv at all.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
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


def _real_uv() -> Path:
    """Locate the genuine uv binary, skipping any uv-strict PATH shim.

    The uv branch has to be exercised by real uv: a stand-in that forwards to the
    test interpreter would pass no matter what the script does with `--no-project`
    or whether the conditional resolves at all.
    """
    found = shutil.which("uv")
    if found is None:
        pytest.skip("uv is not installed; the uv-present branch cannot be exercised")
    resolved = Path(found).resolve()
    if resolved.parent.name == "shims":
        direct = Path.home() / ".local/bin/uv"
        if not direct.is_file():
            pytest.skip("only a uv shim is on PATH and no direct uv binary was found")
        return direct
    return resolved


def _rejecting_python3(tmp_path: Path) -> Path:
    """Write a stand-in `python3` that refuses bare use, as the uv-strict shim does."""
    bin_dir = tmp_path / "shim-bin"
    bin_dir.mkdir(exist_ok=True)
    python3 = bin_dir / "python3"
    python3.write_text(
        "#!/usr/bin/env bash\n"
        'printf "ERROR: Use \\`uv run python3 %s\\` instead of \\`python3 %s\\`\\n" '
        '"$*" "$*" >&2\n'
        "exit 1\n",
        encoding="utf-8",
    )
    python3.chmod(python3.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def _run_new_doc_id(
    version_root: Path,
    tmp_path: Path,
    *,
    path: str,
    scaffold: bool = False,
) -> subprocess.CompletedProcess[str]:
    arguments = ["--scaffold"] if scaffold else []
    # The UV_* passthrough keeps uv's interpreter-install and cache directories
    # visible to the child: hosted CI's managed interpreters live under
    # setup-uv's UV_PYTHON_INSTALL_DIR, which a PATH+HOME-only env strips.
    # Pinning UV_PYTHON to a system interpreter is NOT a substitute — against a
    # non-managed interpreter `uv run` resolves the command name `python3` from
    # PATH, straight into the rejecting shim (verified locally); only a managed
    # interpreter gets the ephemeral-environment bin prepended.
    env = {"PATH": path, "HOME": os.environ["HOME"]}
    env.update({key: value for key, value in os.environ.items() if key.startswith("UV_")})
    return subprocess.run(
        [
            "/bin/bash",
            str(version_root / _SCRIPT),
            *arguments,
            "--doc-type",
            "note",
            "example document",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        check=False,
    )


_managed_interpreter_ready = False


def _ensure_managed_interpreter() -> None:
    """Provision a uv-managed interpreter, the configuration uv-strict mandates.

    The uv branch is only shim-safe through an ephemeral environment built from
    a managed interpreter: `uv run --no-project python3` prepends that
    environment's bin, so `python3` never resolves through the PATH shim.
    Against a bare system interpreter the command name falls back to PATH — the
    self-contradictory shim-without-managed-Python configuration no real
    uv-strict setup produces, but exactly what a hosted runner has (the
    v5.12.0 release-commit `Check` failure, run 30631582570). `uv python
    install` is idempotent and honors UV_PYTHON_INSTALL_DIR, so CI provisions
    into its own setup-uv directory and a developer machine is a fast no-op.
    """
    global _managed_interpreter_ready
    if _managed_interpreter_ready:
        return
    install = subprocess.run(
        [str(_real_uv()), "python", "install"],
        capture_output=True,
        text=True,
        check=False,
    )
    if install.returncode != 0:
        pytest.skip(
            "could not provision a uv-managed interpreter for the uv-strict leg: "
            + install.stderr.strip()[:200]
        )
    _managed_interpreter_ready = True


def _uv_strict_path(tmp_path: Path) -> str:
    """uv present (real binary) with a `python3` that rejects bare invocation."""
    _ensure_managed_interpreter()
    return f"{_rejecting_python3(tmp_path)}:{_real_uv().parent}:/usr/bin:/bin"


def _no_uv_path() -> str:
    """A plain environment: a working `python3`, no uv anywhere on PATH."""
    assert shutil.which("uv", path="/usr/bin:/bin") is None, (
        "this test asserts the uv-absent branch, but uv is installed in /usr/bin"
    )
    return "/usr/bin:/bin"


def test_markdown_frontmatter_1_7__predecessor__still_fails_under_the_shim(
    tmp_path: Path,
) -> None:
    """Characterize 1.6 so the 1.7 result is attributable to the fix (issue #97)."""
    result = _run_new_doc_id(_PREDECESSOR, tmp_path, path=_uv_strict_path(tmp_path))

    assert result.returncode == 1
    assert "instead of" in result.stderr
    assert result.stdout == ""


def test_markdown_frontmatter_1_7__helper__generates_an_id_under_the_shim(
    tmp_path: Path,
) -> None:
    """uv-present branch: the sanctioned generator works in a uv-strict environment."""
    result = _run_new_doc_id(_SUCCESSOR, tmp_path, path=_uv_strict_path(tmp_path))

    assert result.returncode == 0, result.stderr
    assert _ID.fullmatch(result.stdout.strip()), result.stdout


def test_markdown_frontmatter_1_7__helper__generates_an_id_without_uv(
    tmp_path: Path,
) -> None:
    """uv-absent branch: a consumer with python3 and no uv is not broken.

    This is the regression the unconditional `uv run` introduced -- it exits 127
    here -- and it matters because this package is adopted by repositories that
    are not Python projects and have no reason to install uv.
    """
    result = _run_new_doc_id(_SUCCESSOR, tmp_path, path=_no_uv_path())

    assert result.returncode == 0, result.stderr
    assert _ID.fullmatch(result.stdout.strip()), result.stdout


@pytest.mark.parametrize(
    "environment",
    ["uv-strict", "no-uv"],
)
def test_markdown_frontmatter_1_7__scaffold_step__dispatches_in_both_environments(
    tmp_path: Path, environment: str
) -> None:
    """The second call site is the scaffold title, which only `--scaffold` reaches.

    Fixing or breaking one call site would leave this path inconsistent, so the
    scaffold output is exercised separately in both dispatch branches instead of
    trusting a single invocation to cover both.
    """
    path = _uv_strict_path(tmp_path) if environment == "uv-strict" else _no_uv_path()

    result = _run_new_doc_id(_SUCCESSOR, tmp_path, path=path, scaffold=True)

    assert result.returncode == 0, result.stderr
    assert "title: 'Example Document'" in result.stdout


def test_markdown_frontmatter_1_7__uv_branch__never_syncs_the_surrounding_project() -> None:
    """A bare `uv run` would resolve and sync the consumer project around the script.

    Generating a document id must not mutate an unrelated virtualenv, so the uv
    branch is pinned to `--no-project` by text: the behavior it prevents cannot be
    asserted from the outside without building a throwaway project to be mutated.
    """
    text = (_SUCCESSOR / _SCRIPT).read_text(encoding="utf-8")

    assert "uv run --no-project python3 -" in text
    assert re.search(r"uv run (?!--no-project)", text) is None


def test_markdown_frontmatter_1_7__helper__dispatches_every_call_site() -> None:
    """Neither call site may hardcode an interpreter, including any added later."""
    text = (_SUCCESSOR / _SCRIPT).read_text(encoding="utf-8")
    heredoc_calls = re.findall(r"(?m)^.*<<'PY'$", text)

    assert len(heredoc_calls) == 2
    assert all('"${PYTHON_RUNNER[@]}"' in call for call in heredoc_calls)
    assert "PYTHON_RUNNER=(uv run --no-project python3 -)" in text
    assert "PYTHON_RUNNER=(python3 -)" in text


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


def test_markdown_frontmatter_1_7__catalog_role__retains_predecessor() -> None:
    """Catalog 5 must retain 1.7 after selecting its successor.

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

    assert roles["1.7"] == "retained"
    assert roles["1.8"] == "retained"
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
