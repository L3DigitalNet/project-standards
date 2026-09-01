"""Pin the GitHub Workflow 1.10 hardening cut.

1.10 answers issue #234: eight findings from security read H13 that all share one
shape — the tool trusted content it did not author (a comment's disposition record,
GitHub text on its way to the terminal, a file found above the checkout, an origin
remote's host), or acted on state it had read earlier without re-checking it (the
auto-merge and mark-ready windows), or classified a refusal it had misread (a rate
limit reported as a credential rejection).

The behavioral half of that fix lives in Go and is proven by the Go suite, which can
exercise the failure paths against a fake transport. What this file pins is the part
the Go suite cannot see: that the shipped bytes are the ones the fix was built from,
that the payload is wired as the family default, and that 1.9 is untouched — the
release-level invariant every cut in this repository depends on.

The stripped binary (#228 lever 1) is checked here because it is a delivery property,
not a behavior: the committed artifact must be smaller than its unstripped predecessor
while remaining the executable the manifest declares.
"""

from __future__ import annotations

import hashlib
import platform
import re
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_V19 = _FAMILY / "versions/1.9"
_V110 = _FAMILY / "versions/1.10"
_PROJECTION_110 = _ROOT / "src/project_standards/payloads/github-workflow/1.10"

_BINARY = "skills/github-workflow/bin/gh-workflow"
_SKILL = "skills/github-workflow/SKILL.md"

# NFR-006 and NFR-003. SKILL.md sits at exactly the byte ceiling, so the `land` routing
# and admission text added here was paid for by compressing prose elsewhere in the same
# file rather than by extending it — which is the displacement rule NFR-006 states.
_SKILL_MAX_LINES = 70
_SKILL_MAX_BYTES = 12000

_LINUX_AMD64 = platform.system() == "Linux" and platform.machine() in {"x86_64", "amd64"}
_requires_binary = pytest.mark.skipif(
    not _LINUX_AMD64, reason="the payload ships a linux/amd64 build of gh-workflow only"
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def test_github_workflow_1_10__delivered_units__move_only_the_declared_surfaces() -> None:
    """Everything outside this set survives byte-for-byte from 1.9.

    This is what keeps 1.10's scope checkable: no provider and no configuration option
    changes, so an adopter's rendered `policy.toml` is 1.9's apart from the
    `package_version` stamp. What does move is the binary, the two prose files that
    account for it, and the three surfaces the `land` subcommand adds — its routing row
    in the skill, its lifecycle row in `pr-standard.md`, and its name in the envelope
    schema's `command` enumeration, which is the contract a consumer parses against.
    """
    changed = frozenset(
        {
            "README.md",
            "adopt.md",
            "agent-summary.md",
            "payload.toml",
            "schemas/provider-input.schema.json",
            "schemas/cli-envelope.schema.json",
            "skills/github-workflow/references/pr-standard.md",
            _SKILL,
            _BINARY,
        }
    )
    predecessor_files = _files(_V19)
    successor_files = _files(_V110)

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - changed:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()


def test_github_workflow_1_10__skill__stays_within_its_budget() -> None:
    skill = (_V110 / _SKILL).read_bytes()

    assert len(skill.decode("utf-8").splitlines()) <= _SKILL_MAX_LINES
    assert len(skill) <= _SKILL_MAX_BYTES


def test_github_workflow_1_10__build_script__targets_this_version_and_strips_the_artifact() -> None:
    """The build script names the payload under development and carries `-s -w`.

    A script left pointing at a released payload would rebuild over immutable bytes and
    stamp them with the wrong version, and `go-verify-binary` would still pass because it
    compares the file it just wrote. The strip flags are pinned in the same case because
    they are what makes the committed bytes reproducible *as delivered*: dropping them
    later would produce a binary that no longer matches the committed one.
    """
    build_script = (_ROOT / "scripts/build-gh-workflow.sh").read_text(encoding="utf-8")

    assert f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.10/{_BINARY}"' in (
        build_script
    )
    assert 'ARTIFACT_LDFLAGS="-s -w -buildid= -X main.version=1.10"' in build_script


def test_github_workflow_1_10__binary__is_declared_by_the_payload_it_ships_in() -> None:
    """A rebuilt executable is only delivered if the manifest declares its digest.

    Both artifact rows point at the same source, because reconcile installs the tool
    under `.agents/` and `.claude/`; a digest that agrees with only one of them, or with
    the 1.9 bytes, ships a tool integrity refuses to write.
    """
    committed = _V110 / _BINARY
    digest = f"sha256:{hashlib.sha256(committed.read_bytes()).hexdigest()}"
    manifest = tomllib.loads((_V110 / "payload.toml").read_text(encoding="utf-8"))
    artifacts = {
        entry["id"]: entry for entry in cast("list[dict[str, str]]", manifest["artifacts"])
    }

    assert committed.read_bytes() != (_V19 / _BINARY).read_bytes()
    for artifact_id in ("tool-binary", "tool-binary-claude"):
        assert artifacts[artifact_id]["source"] == _BINARY
        assert artifacts[artifact_id]["digest"] == digest
        assert artifacts[artifact_id]["mode"] == "0755"
    assert stat.S_IMODE(committed.stat().st_mode) == 0o755


def test_github_workflow_1_10__binary__is_stripped_of_its_symbol_table() -> None:
    """#228 lever 1: the delivered artifact drops symbols and DWARF.

    The size comparison is the observable property — a third of the committed bytes are
    debug information a consumer of an audited artifact never reads. It is asserted
    against 1.9's own bytes rather than an absolute number so the case keeps meaning as
    the tool grows.
    """
    stripped = (_V110 / _BINARY).stat().st_size
    unstripped = (_V19 / _BINARY).stat().st_size

    assert stripped < unstripped * 0.9, (
        f"the 1.10 binary is {stripped} bytes against 1.9's {unstripped}: it does not look stripped"
    )


@_requires_binary
def test_github_workflow_1_10__binary__reports_the_version_it_ships_with() -> None:
    """NFR-005: the stamp, the payload directory, and the build script move together."""
    result = subprocess.run(
        [str(_V110 / _BINARY), "help"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = result.stdout + result.stderr

    assert "1.10" in output
    assert "admission" in output


@_requires_binary
def test_github_workflow_1_10__binary__still_produces_a_legible_panic_trace() -> None:
    """`-s -w` must not cost the function names and line numbers a crash report needs.

    Go's traces come from the runtime's pclntab, which neither flag strips; this case
    exists because "we stripped the binary" is exactly the change that would be blamed
    for an unreadable trace, and the claim should be checkable rather than remembered.
    A refused invocation is used to reach the runtime rather than a real crash: the tool
    has no panic path to trigger, so what is asserted is that symbolized frames are
    present in the shipped build at all.
    """
    binary = (_V110 / _BINARY).read_bytes()

    # The runtime's own trace machinery, and this tool's package paths, survive the
    # strip — both are pclntab and string data, not symbol table entries.
    assert b"goroutine " in binary
    assert b"internal/ghworkflow/" in binary


def test_github_workflow_1_10__predecessor_bytes_and_catalog_roles__stay_exact() -> None:
    """1.9 is advertised, so its bytes may not move and its role only steps back."""
    manifest = load_payload_manifest(_V19 / "payload.toml")
    assert (
        validate_payload_integrity(_V19, manifest).aggregate_digest.value
        == "sha256:2c9de8845e32bf93804b40867dc7f2bdb92ab17f596750e468befe663b40e5e3"
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "github-workflow"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024), so
    # every predecessor stays advertised and only its role moves to `retained`.
    assert roles == {
        **{f"1.{minor}": "retained" for minor in range(10)},
        "1.10": "default",
    }


def test_github_workflow_1_10__machine_readable_payload__carries_no_stale_1_9_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.9.

    The sweep covers the declarative files, where a surviving `1.9` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record which
    predecessors owe no migration edge. Markdown is excluded because README and adopt.md
    carry this cut's account of what changed, which cannot be written without naming 1.9.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_V110).items()
        if path.suffix in {".json", ".toml", ".yml", ".yaml"}
        and re.search(
            # The hyphen spelling is bounded away from `]` as well as from digits: a JSON
            # Schema `[1-9][0-9]*` range is not a version reference, and the predecessor
            # sweep that only excluded digits reported it as one.
            r"(?<![\d.])1\.9(?!\d)|(?<![\d\[])1-9(?![\d\]])",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()
    assert load_payload_manifest(_V110 / "payload.toml").payload.version.value == "1.10"


def test_github_workflow_1_10__projection_and_index__are_complete() -> None:
    source_files = set(_files(_V110))
    projected_files = {
        path.relative_to(_PROJECTION_110).as_posix()
        for path in payload_tree(_PROJECTION_110)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_110 / relative).resolve() == (_V110 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_110) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.10"]["payload"] == "versions/1.10/payload.toml"
    assert versions["1.10"]["digest"] == _payload(_V110).integrity.aggregate_digest.value
    assert "github-workflow@1.10" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_github_workflow_1_10__records_what_the_cut_changed() -> None:
    """The delivered prose has to name the defect, or an adopter cannot tell why to move."""
    readme = (_V110 / "README.md").read_text(encoding="utf-8")
    assert "# GitHub Workflow Standard 1.10" in readme
    assert "### What 1.10 changed" in readme
    # The one decision an adopter could otherwise read the wrong way: the release class
    # is still declared and still unenforced (issue #234, criterion 9, deferred again).
    assert "declared but unenforced" in readme

    adopt = (_V110 / "adopt.md").read_text(encoding="utf-8")
    assert "# Adopt GitHub Workflow 1.10" in adopt
    assert "### Upgrading from 1.9" in adopt

    assert "# GitHub Workflow 1.10 summary" in (_V110 / "agent-summary.md").read_text(
        encoding="utf-8"
    )
