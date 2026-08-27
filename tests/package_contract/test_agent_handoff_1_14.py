"""Package-contract proof for the Agent Handoff 1.14 closeout-efficiency successor.

1.14 exists because the packaged closeout procedure was expensive to follow.
It never stated the numeric document caps, so agents discovered them by failing
validation and re-editing; validation was run unscoped, so a warning introduced
during the session was invisible among the pre-existing advisory findings that
append-only session logs accumulate; and reconstructing "what happened this
session" was left to ad-hoc Git and text searches. The cut changes packaged
prose only — `SKILL.md` (and its byte-locked provider-resource copy), `README.md`
and `adopt.md` — plus the version constants every payload cut carries.

The load-bearing test here is the caps-table check. Restating policy numbers in
prose creates a second source of truth, and a silently stale restatement is worse
than no table at all: an agent would write to a cap the validator does not
enforce, or vice versa. The test derives the expectation from this payload's own
`resources/policy.toml`, so the two cannot drift apart without a red test.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.13"
_SUCCESSOR = _FAMILY / "versions/1.14"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.14"
_PREDECESSOR_DIGEST = "sha256:324fa4d81c62da450ea29e5b06207e94379d4cbbeb59c2d8e3baee7581ab298b"
_SUCCESSOR_CHANGES = frozenset(
    {
        # Version constants every cut advances.
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
        # The closeout procedure itself, plus its byte-locked provider-resource copy.
        "skills/agent-handoff/SKILL.md",
        "provider-resources/managed/skill.md",
        # Documentation of the same change for readers who never open the skill.
        "README.md",
        "adopt.md",
        # Not a 1.14 behavior change: the launcher is byte-identical Go source rebuilt
        # under the go1.26.6 toolchain pin, which 1.13 predates. 1.14 is the newest
        # unpublished cut, so it is the only version whose copy may be rebuilt — every
        # released copy from 1.10 through 1.13 keeps its frozen bytes and its own
        # payload digest (issue #177's toolchain bump; see
        # scripts/build-agent-handoff-session-start.sh, which targets this version).
        "hooks/session-start/session-start",
    }
)

_CAPS_HEADING = "### Document caps"
# Table row label -> `shape.documents` key in this payload's policy. The bug-record
# label is a human spelling of a shell glob whose character classes would otherwise
# read as digits, and the final row covers `shape.defaults` rather than one document.
_DEFAULTS_ROW = "Any other handoff document"
_ROW_TO_POLICY_KEY = {
    "docs/handoff/state.md": "docs/handoff/state.md",
    "docs/STATUS.md": "docs/STATUS.md",
    "docs/TODO.md": "docs/TODO.md",
    "docs/handoff/deployed.md": "docs/handoff/deployed.md",
    "docs/handoff/architecture.md": "docs/handoff/architecture.md",
    "docs/handoff/conventions.md": "docs/handoff/conventions.md",
    "docs/handoff/sessions/*.md": "docs/handoff/sessions/*.md",
    "docs/handoff/bugs/NNN-slug.md": "docs/handoff/bugs/[0-9][0-9][0-9]-*.md",
}


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _skill_text() -> str:
    return (_SUCCESSOR / "skills/agent-handoff/SKILL.md").read_text(encoding="utf-8")


def _caps_rows() -> dict[str, str]:
    """Return the caps table as {row label: caps cell} for the 1.14 skill."""
    section = _skill_text().split(_CAPS_HEADING, 1)[1].split("\n## ", 1)[0]
    rows: dict[str, str] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        label = cells[0].strip("`")
        if label in {"Document", "---"}:
            continue
        rows[label] = cells[1]
    return rows


def _declared_numbers(value: object) -> set[int]:
    """Collect every integer a policy mapping declares, ignoring boolean flags."""
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    numbers: set[int] = set()
    if isinstance(value, dict):
        for item in cast("dict[str, object]", value).values():
            numbers |= _declared_numbers(item)
    elif isinstance(value, list):
        for item in cast("list[object]", value):
            numbers |= _declared_numbers(item)
    return numbers


def test_agent_handoff_1_14__successor__changes_only_the_closeout_prose() -> None:
    """Preserve every runtime, template, policy, and historical byte outside the prose."""
    assert _SUCCESSOR.is_dir(), "the 1.14 candidate must exist before contract verification"

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

    # The caps table restates policy; the policy itself must not move in this cut,
    # or consumers would silently get new enforcement under a prose-only version.
    assert (_SUCCESSOR / "resources/policy.toml").read_bytes() == (
        _PREDECESSOR / "resources/policy.toml"
    ).read_bytes()


def test_agent_handoff_1_14__caps_table__matches_the_installed_policy() -> None:
    """Pin the prose caps to `resources/policy.toml` so the restatement cannot go stale.

    Bidirectional by construction: the label map must name every `shape.documents`
    key, the table must have exactly one row per label plus the defaults row, and
    each row's integers must equal the integers that policy entry declares. A new
    policy document, a changed number, or a dropped row all fail here.
    """
    policy = tomllib.loads((_SUCCESSOR / "resources/policy.toml").read_text(encoding="utf-8"))
    shape = cast("dict[str, object]", policy["shape"])
    documents = cast("dict[str, object]", shape["documents"])

    assert set(_ROW_TO_POLICY_KEY.values()) == set(documents)

    rows = _caps_rows()
    assert set(rows) == set(_ROW_TO_POLICY_KEY) | {_DEFAULTS_ROW}

    for label, policy_key in _ROW_TO_POLICY_KEY.items():
        assert {int(number) for number in re.findall(r"\d+", rows[label])} == _declared_numbers(
            documents[policy_key]
        ), f"caps row for {label} disagrees with policy"
    assert {int(number) for number in re.findall(r"\d+", rows[_DEFAULTS_ROW])} == _declared_numbers(
        shape["defaults"]
    )


def test_agent_handoff_1_14__closeout__is_session_scoped_and_delegable() -> None:
    """Pin the three behaviors the cut exists to deliver, as the skill states them."""
    skill = _skill_text()

    assert "project-standards agent-handoff delta --repo . --since <session-start-oid>" in skill
    assert "project-standards agent-handoff validate --repo . --since <session-start-oid>" in skill
    # The bare form must survive: `--since` scopes warnings, so a full audit still
    # needs the unscoped command.
    assert "validate --repo .`" in skill
    assert "Errors are never suppressed by `--since`." in skill
    assert "Visual wrapping in an editor is not a line break" in skill
    assert "### Delegating closeout" in skill

    # Both installed trees are fed from this one source, so a prose-only cut still
    # has to keep the provider-resource copy byte-identical.
    assert (_SUCCESSOR / "provider-resources/managed/skill.md").read_bytes() == (
        _SUCCESSOR / "skills/agent-handoff/SKILL.md"
    ).read_bytes()


def test_agent_handoff_1_14__identity__is_complete_and_retained() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.14"
    assert indexed["1.14"].digest == integrity.aggregate_digest
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.14"}

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }
    assert roles["1.13"] == "retained"
    # Superseded by 1.15 but still advertised: withdrawing an advertised package is a
    # catalog-major transition (ADR 0024), so the entry stays and only the role moves.
    assert roles["1.14"] == "retained"


def test_agent_handoff_1_14__schemas__carry_no_predecessor_version_reference() -> None:
    """Guard the copied-payload failure mode: schema constants left pointing at 1.13.

    Every prior cut inherited at least one stale embedded version string that no
    per-cut assertion caught, so this derives the check from the payload manifest
    instead of naming the constants.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    successor_text = {
        relative: path.read_text(encoding="utf-8")
        for relative, path in _files(_SUCCESSOR).items()
        if path.suffix in {".json", ".toml", ".md", ".py", ".yaml"}
    }
    stale = {
        relative
        for relative, text in successor_text.items()
        if re.search(r"(?<!\d)1\.13(?!\d)", text) and relative != "adopt.md"
    }
    assert stale == set(), "1.14 payload files still reference the 1.13 predecessor"


def test_agent_handoff_1_14__payload_projection__matches_successor() -> None:
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
