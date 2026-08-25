"""Package-contract proof for the GitHub Workflow 1.4 ledger-escaping successor.

1.4 exists because `gh-workflow ledger` escaped every underscore in a table cell,
and Prettier — which owns markdown formatting in consuming repositories — rewrites
`\\_` back to `_` between two word characters. Every regeneration of a ledger
carrying a `snake_case` title therefore failed the consumer's own
`prettier --check` until someone ran `prettier --write` by hand (issue #177).

This is the first cut since 1.1 that rebuilds the committed binary, so the
assertions below are the ones that would catch the two ways such a cut goes wrong:
a payload carrying a stale binary (the version number moves, the behavior does
not), and a build script still aimed at a released version's immutable bytes. The
escaping behavior itself is pinned in the Go renderer's own tests, which is where
the rule lives.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.3"
_SUCCESSOR = _FAMILY / "versions/1.4"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.4"
_PREDECESSOR_DIGEST = "sha256:0aef4418dbb4e382d5992f93c33432aafeb43501e4501c51bd0ccd2a8464d25e"
_BUILD_SCRIPT = _ROOT / "scripts/build-gh-workflow.sh"
_TOOL_BINARY_SOURCE = "skills/github-workflow/bin/gh-workflow"
_SUCCESSOR_CHANGES = frozenset(
    {
        # Version constants every cut advances.
        "payload.toml",
        "schemas/provider-input.schema.json",
        "README.md",
        "adopt.md",
        "agent-summary.md",
        # Frontmatter `version` and the platform sentence name the package version.
        "skills/github-workflow/SKILL.md",
        # The reason for the cut: rebuilt from the fixed renderer.
        _TOOL_BINARY_SOURCE,
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def _artifacts(root: Path) -> dict[str, dict[str, str]]:
    manifest = tomllib.loads((root / "payload.toml").read_text(encoding="utf-8"))
    entries = cast("list[dict[str, str]]", manifest["artifacts"])
    return {entry["id"]: entry for entry in entries}


def test_github_workflow_1_4__successor__changes_only_the_binary_and_its_version_prose() -> None:
    """Preserve every released byte, and carry a genuinely rebuilt binary."""
    assert _SUCCESSOR.is_dir(), "the 1.4 candidate must exist before contract verification"

    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    changed = {
        relative
        for relative in predecessor_files
        if successor_files[relative].read_bytes() != predecessor_files[relative].read_bytes()
    }
    assert changed == _SUCCESSOR_CHANGES
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    # A cut that advertised a fix while shipping the predecessor's executable would
    # pass every other assertion here, so state the difference outright.
    assert (
        successor_files[_TOOL_BINARY_SOURCE].read_bytes()
        != predecessor_files[_TOOL_BINARY_SOURCE].read_bytes()
    )


def test_github_workflow_1_4__tool_binary__is_declared_and_built_for_this_version() -> None:
    """Pin the three-way contract between the committed bytes, the payload, and the build.

    `scripts/build-gh-workflow.sh` names one output path and one version stamp, and
    `make go-verify-binary` rebuilds exactly that path. Left pointing at 1.3, the
    gate would either rewrite a released payload's immutable bytes or verify a file
    this payload does not ship — both of which look green from inside the payload.
    """
    committed = _SUCCESSOR / _TOOL_BINARY_SOURCE
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"

    for artifact_id in ("tool-binary", "tool-binary-claude"):
        entry = _artifacts(_SUCCESSOR)[artifact_id]
        assert entry["source"] == _TOOL_BINARY_SOURCE
        assert entry["digest"] == digest
        assert entry["mode"] == "0755"
    assert committed.stat().st_mode & 0o777 == 0o755

    build_script = _BUILD_SCRIPT.read_text(encoding="utf-8")
    target = f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.4/{_TOOL_BINARY_SOURCE}"'
    assert target in build_script
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.4"' in build_script


def test_github_workflow_1_4__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.4"
    assert indexed["1.4"].digest == integrity.aggregate_digest
    # Published predecessor rows are immutable selectors, not moving aliases.
    assert indexed["1.3"].digest.value == _PREDECESSOR_DIGEST

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "github-workflow"
    }
    assert roles["1.3"] == "retained"
    assert roles["1.4"] == "default"
    assert "| [`github-workflow`](github-workflow/README.md) | active | 1.4 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_github_workflow_1_4__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.3."""
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml"}
        and re.search(r"(?<!\d)1\.3(?!\d)", path.read_text(encoding="utf-8"))
    }
    assert stale == set(), "1.4 payload files still reference the 1.3 predecessor"


def test_github_workflow_1_4__ledger_documentation__states_the_escaping_rule() -> None:
    """The behavior change is consumer-visible, so the payload has to describe it.

    A copied README that still claimed byte-identity with 1.1 would document the
    package as unchanged in the one release where the binary actually moved.
    """
    readme = (_SUCCESSOR / "README.md").read_text(encoding="utf-8")

    assert "byte-identical to 1.1" not in readme
    assert "From 1.4 the ledger escapes an underscore" in readme
    assert "`prettier --check`" in readme


def test_github_workflow_1_4__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
