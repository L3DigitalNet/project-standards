"""Pin the Markdown Tooling 1.9 lint/format safety successor contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

import pytest

from project_standards.package_contract.catalog import load_catalog_source
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    PayloadAvailability,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_V18 = _FAMILY / "versions/1.8"
_V19 = _FAMILY / "versions/1.9"
_OBSERVED_LITERAL = _ROOT / "tests/fixtures/observed_consumers/markdownlint-literal-cjk.json"
_V18_RELEASED_DIGEST = "sha256:22ebe7b95ca82daa276746c9bf3f0688d15ce4b47314b7e4abea206df7212783"
_OBSERVED_LITERAL_DIGEST = "sha256:4c1c089d0552a6118f6a8b7d85bae1bd762da41d601d1c489bdb9143f6a2d548"
_HEADING = re.compile(r"^#{1,6} (?P<title>.+)$", flags=re.MULTILINE)
_PAIRED_DIRECTIVES = re.compile(
    r"<!-- markdownlint-disable (?P<rules>MD\d+(?: MD\d+)*) -->"
    r".*?"
    r"<!-- markdownlint-enable (?P=rules) -->",
    flags=re.DOTALL,
)
_GUIDES = (_V19 / "README.md", _V19 / "adopt.md")


def _json_object(path: Path) -> JsonObject:
    document: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return cast("JsonObject", document)


def _sections(document: str) -> tuple[tuple[str, str], ...]:
    headings = tuple(_HEADING.finditer(document))
    return tuple(
        (
            match.group("title"),
            document[
                match.end() : headings[index + 1].start()
                if index + 1 < len(headings)
                else len(document)
            ],
        )
        for index, match in enumerate(headings)
    )


@pytest.mark.parametrize(
    "relative_path",
    ("resources/markdownlint.json", "artifacts/markdownlint.json"),
)
def test_markdown_tooling_1_9__markdownlint_rule_set__disables_md060(
    relative_path: str,
) -> None:
    assert _json_object(_V19 / relative_path)["MD060"] is False


def test_markdown_tooling_1_9__normal_documented_commands__never_use_autofix() -> None:
    autofix_sections: list[str] = []
    for guide in _GUIDES:
        for title, body in _sections(guide.read_text(encoding="utf-8")):
            if "--fix" in body:
                autofix_sections.append(title)

    assert autofix_sections
    assert autofix_sections == ["Optional autofix recovery"]


def test_markdown_tooling_1_9__optional_autofix_recipe__is_explicitly_guarded() -> None:
    recovery_sections = [
        body
        for guide in _GUIDES
        for title, body in _sections(guide.read_text(encoding="utf-8"))
        if title == "Optional autofix recovery"
    ]
    assert len(recovery_sections) == 1

    recovery = recovery_sections[0]
    lowered = recovery.lower()
    assert "clean starting diff" in lowered
    assert "review" in lowered and "resulting diff" in lowered
    assert "follow-up" in lowered
    assert 'test -z "$(git status --porcelain)" && npx markdownlint-cli2 --fix' in recovery
    assert "npx prettier --check" in recovery
    lint_commands = [
        line.strip() for line in recovery.splitlines() if "npx markdownlint-cli2" in line
    ]
    assert any("--fix" in command for command in lint_commands)
    assert any("--fix" not in command for command in lint_commands)


def test_markdown_tooling_1_9__exception_guidance__uses_paired_block_directives() -> None:
    guidance = "\n".join(guide.read_text(encoding="utf-8") for guide in _GUIDES)
    pairs = tuple(_PAIRED_DIRECTIVES.finditer(guidance))

    assert pairs
    assert guidance.count("<!-- markdownlint-disable ") == len(pairs)
    assert guidance.count("<!-- markdownlint-enable ") == len(pairs)


def test_markdown_tooling_1_9__direct_migration__names_changed_lint_artifact() -> None:
    manifest = load_payload_manifest(_V19 / "payload.toml")
    migration = next(
        item
        for item in manifest.migrations
        if item.from_endpoint.value == "package:1.8" and item.to_endpoint.value == "package:1.9"
    )

    assert set(migration.affected) == {
        "artifact:markdownlint-config",
        "contribution:format-caller",
        "contribution:lint-caller",
    }


def test_markdown_tooling_1_9__safety_change__preserves_released_inputs() -> None:
    predecessor_manifest = load_payload_manifest(_V18 / "payload.toml")
    predecessor = validate_payload_integrity(_V18, predecessor_manifest)
    assert predecessor.aggregate_digest.value == _V18_RELEASED_DIGEST

    literal_bytes = _OBSERVED_LITERAL.read_bytes()
    literal_digest = "sha256:" + hashlib.sha256(literal_bytes).hexdigest()
    assert literal_digest == _OBSERVED_LITERAL_DIGEST
    assert _json_object(_OBSERVED_LITERAL)["MD060"] == {
        "style": "any",
        "aligned_delimiter": False,
    }


def test_markdown_tooling_1_9__successor__stays_retained_beside_predecessor() -> None:
    successor_manifest = load_payload_manifest(_V19 / "payload.toml")
    successor = validate_payload_integrity(_V19, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    versions = {entry.version.value: entry for entry in family.versions}

    assert successor_manifest.payload.version.value == "1.9"
    assert successor_manifest.payload.availability is PayloadAvailability.CONSUMER
    assert versions["1.9"].digest == successor.aggregate_digest

    catalog = load_catalog_source(_ROOT / "catalogs/5.toml")
    entries = [entry for entry in catalog.packages if entry.id == "markdown-tooling"]
    roles = {entry.version.value: entry.role.value for entry in entries}
    # 5.10 advanced the default to 1.10; 1.9 remains advertised as retained.
    assert roles[successor_manifest.payload.version.value] == "retained"
    assert roles[_V18.name] == "retained"
