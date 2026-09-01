"""Markdown Tooling 1.16 repairs the documented Prettier gate and repins the lint action.

Issue #209: the rendered local Prettier command handed Git's whole tracked
selection to Prettier, which refuses an explicitly named symbolic link with a
non-zero status while still reporting every real file clean. Any repository that
tracks symlinks matching the selected globs therefore failed its own documented
gate on a fully clean tree. 1.16 lists the corpus with ``git ls-files -s`` and
drops index mode ``120000``, which removes only paths Prettier was already
refusing to read.

Issue #211: the self-hosted lint workflow advances to
``markdownlint-cli2-action`` v24.2.0.

The root-workflow byte-parity row below is the release-prep contract, matching
`test_markdown_tooling_1_13__root_workflows__come_from_pinned_successor_resources`:
it turns green only once the producer-mode reconcile re-renders
`.github/workflows/` from this payload. Before that it legitimately fails,
because CP-MODIFIED-MANAGED forbids advancing an installed copy ahead of the
package version this repository has selected.
"""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from pathlib import Path
from typing import cast

import pytest
import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.15"
_SUCCESSOR = _FAMILY / "versions/1.16"
_PROJECTION = _ROOT / "src/project_standards/payloads/markdown-tooling/1.16"
_PREDECESSOR_DIGEST = "sha256:aa3e3ae249cf2720355b1b33c987af11a546be4bf456c9e977903e5f9fe00f03"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "providers/markdown_tooling.py",
        "resources/self-host-lint-markdown.yml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_LINT_ACTION_PIN = (
    "DavidAnson/markdownlint-cli2-action@21c1be1b93ad9ed58fa840aacc3f279cde2a72ff # v24.2.0"
)
_SYMLINK_FILTER = r"sed -zn '/^120000 /!s/^[^\t]*\t//p'"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return InstalledPayload(_SUCCESSOR, manifest, validate_payload_integrity(_SUCCESSOR, manifest))


def _render(provider_id: str, snapshots: JsonObject | None = None) -> str:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=load_option_schema(_SUCCESSOR, payload.manifest).resolve_options({}),
            snapshots=snapshots or {},
        )
    )
    assert result.content is not None
    return result.content.decode()


def _instruction_block() -> str:
    return _render(
        "render-semantic",
        {"planned_contribution": {"adapter": "markdown-block", "scope": "block:markdown-tooling"}},
    )


def _prettier_check_command(block: str) -> str:
    """Return the one rendered Git-routed Prettier check line from the block."""
    lines = [
        line
        for line in block.splitlines()
        if line.startswith("git ls-files") and "prettier --check" in line
    ]
    assert len(lines) == 1, lines
    return lines[0]


def test_markdown_tooling_1_16__successor__preserves_1_15_and_indexes_complete_payload() -> None:
    """Only the gate prose, provider, lint workflow, and schema bytes change."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in payload_tree(_PREDECESSOR)
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    indexed = {
        entry.version.value: entry
        for entry in load_family_manifest(_FAMILY / "standard.toml").versions
    }
    assert manifest.payload.version.value == "1.16"
    assert indexed["1.16"].digest == integrity.aggregate_digest
    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "package:1.7",
        "package:1.8",
        "package:1.9",
        "package:1.10",
        "package:1.11",
        "package:1.12",
        "package:1.15",
        "legacy:v4-markdown-tooling",
    }
    assert {migration.to_endpoint.value for migration in manifest.migrations} == {"package:1.16"}
    for migration in manifest.migrations:
        # 1.16 moves both instruction blocks and the lint caller, so every inbound
        # route must relock all three or a migrating consumer keeps stale bytes.
        assert {
            "contribution:agents-instructions",
            "contribution:claude-instructions",
            "contribution:lint-caller",
        } <= set(migration.affected)


def test_markdown_tooling_1_16__instruction_block__filters_symlinks_from_the_prettier_corpus() -> (
    None
):
    """The rendered gate an agent pastes must carry the mode filter, not the old form."""
    block = _instruction_block()
    command = _prettier_check_command(block)

    assert command.startswith("git ls-files -s -z -- ")
    assert _SYMLINK_FILTER in command
    assert command.endswith("| xargs -0 -r npx prettier --check --")
    # The predecessor's unfiltered form must not survive anywhere in the block.
    assert "git ls-files -z -- ':(glob)**/*.md' ':(glob)**/*.json'" not in block

    # The markdownlint recipe is deliberately untouched: markdownlint-cli2 follows
    # a symlinked path and lints its target, so it never had the #209 defect.
    lint_lines = [line for line in block.splitlines() if "markdownlint-cli2" in line]
    assert lint_lines
    for line in lint_lines:
        assert "git ls-files -s -z" not in line


def test_markdown_tooling_1_16__rendered_selection__drops_symlinks_and_keeps_real_files(
    tmp_path: Path,
) -> None:
    """Run the rendered selection pipeline over a repository that tracks a symlink.

    This is the #209 reproduction: at 1.15 the symlink reached Prettier as an
    explicitly specified pattern and the gate exited non-zero on a clean tree.
    Only the selection half runs here, so the assertion holds without Node.

    Requires `git` and a GNU `sed` (`-z`, and `\\t` inside a bracket expression),
    which the rendered recipe already declares as its platform floor.
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/real.md").write_text("# Real\n", encoding="utf-8")
    (tmp_path / "docs/config.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs/link.md").symlink_to("real.md")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    selection = _prettier_check_command(_instruction_block()).split("| xargs", maxsplit=1)[0]
    completed = subprocess.run(
        ["sh", "-c", selection],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    selected = [entry for entry in completed.stdout.decode().split("\0") if entry]

    assert sorted(selected) == ["docs/config.json", "docs/real.md"]


@pytest.mark.parametrize("tool", ["lint", "format"])
def test_markdown_tooling_1_16__verify_without_runner_labels__reports_findings(tool: str) -> None:
    """A config that omits `runner_labels` must verify, not raise.

    The render path has always treated absent and empty alike; the verify path
    passed `config.get("runner_labels")` straight to the sequence coercion, so
    the same config rendered cleanly and then aborted `verify` with a provider
    ValueError instead of returning findings. `findings` may legitimately be
    empty here — the assertion is that the invocation completes.
    """
    payload = _payload()
    config = dict(
        load_option_schema(_SUCCESSOR, payload.manifest).resolve_options({})  # type: ignore[arg-type]
    )
    del config["runner_labels"]

    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=f"verify-{tool}",
            operation=ProviderOperation.VERIFY,
            effective_config=config,
            snapshots={},
        )
    )

    assert all(finding.code != "MT-RUNNER-LABELS-UNREACHABLE" for finding in result.findings)


def test_markdown_tooling_1_16__lint_workflow_resource__pins_the_advanced_action() -> None:
    """The SHA and its version comment must name the same release (#211)."""
    resource = _SUCCESSOR / "resources/self-host-lint-markdown.yml"
    text = resource.read_text(encoding="utf-8")
    assert f"uses: {_LINT_ACTION_PIN}" in text

    raw: object = yaml.safe_load(text)
    assert isinstance(raw, dict)
    jobs = cast("dict[str, object]", cast("dict[str, object]", raw)["jobs"])
    lint = cast("dict[str, object]", jobs["lint"])
    steps = cast("list[object]", lint["steps"])
    action = next(
        cast("dict[str, object]", step)
        for step in steps
        if isinstance(step, dict)
        and str(cast("dict[str, object]", step).get("uses", "")).startswith(
            "DavidAnson/markdownlint-cli2-action@"
        )
    )
    assert action["uses"] == _LINT_ACTION_PIN.split(" # ", maxsplit=1)[0]

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    resources = {entry.path.normalized.as_posix(): entry for entry in manifest.resources}
    assert resources["resources/self-host-lint-markdown.yml"].digest.value == _sha256(resource)


def test_markdown_tooling_1_16__root_workflows__come_from_pinned_successor_resources() -> None:
    """Red until the release-prep reconcile installs this payload; see the module docstring."""
    for resource_path, root_workflow in {
        "resources/self-host-lint-markdown.yml": _ROOT / ".github/workflows/lint-markdown.yml",
        "resources/self-host-format.yml": _ROOT / ".github/workflows/format.yml",
    }.items():
        assert (_SUCCESSOR / resource_path).read_bytes() == root_workflow.read_bytes()


def test_markdown_tooling_1_16__projection_and_catalog__stay_complete_and_default() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in payload_tree(_SUCCESSOR)
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    advertised_versions = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "markdown-tooling"
    }
    assert advertised_versions["1.15"] == "retained"
    assert advertised_versions["1.16"] == "default"
    assert (
        "| [`markdown-tooling`](markdown-tooling/README.md) | active | 1.16 | default | consumer |"
    ) in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_markdown_tooling_1_16__mutable_navigation__names_the_new_authority() -> None:
    """Family-level readers must resolve the same current payload as the index."""
    for name, expected_link in (
        ("README.md", "versions/1.16/README.md"),
        ("adopt.md", "versions/1.16/adopt.md"),
        ("agent-summary.md", "versions/1.16/agent-summary.md"),
    ):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert expected_link in content
        assert "versions/1.15/" not in content
