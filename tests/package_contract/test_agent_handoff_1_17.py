"""Package-contract proof for the Agent Handoff 1.17 session-start re-seal.

1.17 exists to re-seal the launcher. Its Go source hardens the session-start Git
reads — minimal environment, `-c core.fsmonitor=`, `--no-optional-locks` (issue
#235) — the binary is stamped with its own payload version so `--version` answers
the stale-launcher question (issue #229), and it is linked with `-s -w` (issue
#228). The Go behavior itself is proven in
`internal/agenthandoff/sessionstart/hook_test.go`, which runs the built
executable; this file proves the packaging half: which payload bytes moved, that
the shipped binary is the stamped one, and that the cut is wired into the family
index, catalog, and projection.

The skill-target/`payload.toml` agreement is asserted catalog-wide in
`test_provider_registry.py` (issue #194) rather than per family, so this file
proves only what is specific to the 1.17 cut.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.16"
_SUCCESSOR = _FAMILY / "versions/1.17"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.17"
_PREDECESSOR_DIGEST = "sha256:c5740e1c40ae3643f3df67014ac1458a78e9d5f1682cdcaa1adcfc2f259d28ff"
_HOOK_PATH = "hooks/session-start/session-start"
_SUCCESSOR_CHANGES = frozenset(
    {
        # Version constants every cut advances.
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
        # Documentation of the re-seal, including the launcher's stripped size.
        "README.md",
        "adopt.md",
        # The cut's reason: hardened, re-stamped, stripped launcher bytes.
        _HOOK_PATH,
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _default_agent_handoff_version() -> str:
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    defaults = [
        package["version"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff" and package["role"] == "default"
    ]
    assert len(defaults) == 1, "catalog 5 must advertise exactly one default agent-handoff package"
    return defaults[0]


def test_agent_handoff_1_17__successor__changes_only_the_launcher_and_its_documentation() -> None:
    """Preserve every runtime, template, policy, and historical byte outside the re-seal."""
    assert _SUCCESSOR.is_dir(), "the 1.17 candidate must exist before contract verification"

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

    assert (_SUCCESSOR / "resources/policy.toml").read_bytes() == (
        _PREDECESSOR / "resources/policy.toml"
    ).read_bytes()
    assert (_SUCCESSOR / "providers/agent_handoff.py").read_bytes() == (
        _PREDECESSOR / "providers/agent_handoff.py"
    ).read_bytes()
    assert (_SUCCESSOR / "skills/agent-handoff/SKILL.md").read_bytes() == (
        _PREDECESSOR / "skills/agent-handoff/SKILL.md"
    ).read_bytes()


def test_agent_handoff__default_launcher__reports_its_own_payload_version() -> None:
    """Pin the #229 rule: the shipped binary names the payload version that ships it.

    Deliberately resolved from the catalog's default rather than hardcoded to 1.17,
    so a cut that byte-copies its predecessor's launcher — the 1.14-through-1.16
    carry-forward this rule exists to prevent — fails here instead of shipping a
    `--version` that answers for an older payload. Retained versions are not
    asserted: their bytes are published and immutable.
    """
    version = _default_agent_handoff_version()
    binary = _FAMILY / "versions" / version / _HOOK_PATH
    result = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        check=True,
        text=True,
    )
    assert result.stdout.strip() == f"agent-handoff session-start {version}"


def test_agent_handoff_1_17__launcher__is_stripped_but_keeps_its_panic_table() -> None:
    """Pin the #228 lever-1 link flags on the first cut that adopts them.

    Section names are read from the ELF header rather than by running a debugger:
    the assertion is that `-s -w` removed the symbol table and DWARF while
    `.gopclntab` — the table Go panics resolve function names and lines through —
    survived, which is exactly the trade the strip policy claims.
    """
    binary = (_SUCCESSOR / _HOOK_PATH).read_bytes()
    assert b".gopclntab" in binary
    assert b".debug_info" not in binary
    assert (_SUCCESSOR / _HOOK_PATH).stat().st_size < (_PREDECESSOR / _HOOK_PATH).stat().st_size


def test_agent_handoff_1_17__identity__is_complete_and_current() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.17"
    assert indexed["1.17"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.17"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.16"] == "retained"
    assert roles["1.17"] == "default"
    assert "| [`agent-handoff`](agent-handoff/README.md) | active | 1.17 | default |" in (
        _ROOT / "standards/catalog.md"
    ).read_text(encoding="utf-8")


def test_agent_handoff_1_17__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: schema constants left pointing at 1.16."""
    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml"}
    }
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.16(?!\d)", text) and relative not in {"adopt.md", "README.md"}
    }
    assert stale == set(), "1.17 payload files still reference the 1.16 predecessor"


def test_agent_handoff_1_17__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
