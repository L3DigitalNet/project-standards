"""T9 exclusion parity and immutable-successor guards (FR-015, FR-019).

Issue #47 reported that ``dir/**`` protected markdownlint input but not
Prettier input. The pinned 5.8.0 tools do not reproduce that divergence, so the
1.9 successor deliberately retains 1.8 provider rendering. These tests keep
the conclusion honest across the provider, reusable-workflow shell, and tool
matching boundaries instead of introducing an unobserved normalization.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import cast

import pytest
import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.catalog import load_catalog_source
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    PayloadAvailability,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.issue_regressions.tool_oracle import (
    markdownlint_findings,
    prettier_differences,
    prettier_workflow,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_V18 = _FAMILY / "versions/1.8"
_V19 = _FAMILY / "versions/1.9"
_FORMAT_WORKFLOW = _ROOT / ".github/workflows/format.yml"
_LINT_WORKFLOW = _ROOT / ".github/workflows/lint-markdown.yml"

_V18_AGGREGATE = "sha256:22ebe7b95ca82daa276746c9bf3f0688d15ce4b47314b7e4abea206df7212783"
_FORMAT_WORKFLOW_DIGEST = "901639336cf3db411a0090c660d36036c2e8bc9bffd592bec3e4c064baf7cb7a"
# The hosted lint workflow is not frozen forever: it is the self-hosted rendering
# of the current default markdown-tooling payload, so an activation that changes
# that resource changes these bytes. 1.10 (issue #63) appended the generated-tree
# negations, which narrows what every `@v5` caller lints — a loosening, and one a
# repository escapes with `lint_workflow_ownership = "consumer-owned"`. The digest
# is pinned so such a change is always a deliberate, reviewed update rather than a
# silent one; the format workflow above is genuinely unchanged since 1.8.
_LINT_WORKFLOW_DIGEST = "fdce0f2148fc9dad902b23d1027841e21443668bb062d1f0dc08ceb070172796"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, exclusion: str) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(
        {
            "exclusions": [
                {
                    "glob": exclusion,
                    "applies_to": "both",
                    "reason": "The nested fixture is consumer-owned.",
                }
            ]
        }
    )


def _render(root: Path, provider_id: str, exclusion: str) -> str:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=_options(root, exclusion),
            snapshots={},
        )
    )
    assert result.content is not None
    return result.content.decode()


def _caller_inputs(caller: str, job: str) -> dict[str, object]:
    raw: object = yaml.safe_load(caller)
    assert isinstance(raw, dict)
    jobs = cast("dict[str, object]", raw)["jobs"]
    assert isinstance(jobs, dict)
    selected = cast("dict[str, object]", jobs)[job]
    assert isinstance(selected, dict)
    inputs = cast("dict[str, object]", selected)["with"]
    assert isinstance(inputs, dict)
    return cast("dict[str, object]", inputs)


def _write_markdown_fixture(root: Path) -> tuple[str, ...]:
    paths = (
        root / "outside.md",
        root / "payload/direct.md",
        root / "payload/deep/nested.md",
    )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Title\n\n-   item\n", encoding="utf-8")
    return tuple(path.relative_to(root).as_posix() for path in paths)


def _prettier_workflow_findings(root: Path, caller: Path) -> tuple[str, ...]:
    outcome = prettier_workflow(_ROOT, root, caller)
    assert outcome.returncode in {0, 1}, outcome.output
    return tuple(
        sorted(
            line.removeprefix("[warn] ").strip()
            for line in outcome.output.splitlines()
            if line.startswith("[warn] ") and line.endswith(".md")
        )
    )


@pytest.mark.parametrize(
    ("exclusion", "expected"),
    [
        pytest.param("payload", ("outside.md",), id="directory-name"),
        pytest.param("payload/", ("outside.md",), id="directory-slash"),
        pytest.param("payload/**", ("outside.md",), id="directory-starstar"),
        pytest.param(
            r"payload\**",
            ("outside.md", "payload/deep/nested.md", "payload/direct.md"),
            id="platform-separator-is-literal",
        ),
    ],
)
def test_t9_pinned_effective_sets__provider_workflow_and_tools__remain_equal(
    tmp_path: Path,
    exclusion: str,
    expected: tuple[str, ...],
) -> None:
    """TC-T9-001: every boundary selects one non-widened effective corpus."""
    all_files = _write_markdown_fixture(tmp_path)
    lint_caller = _render(_V19, "render-lint-caller", exclusion)
    format_caller = _render(_V19, "render-format-caller", exclusion)
    lint_inputs = _caller_inputs(lint_caller, "lint-markdown")
    format_inputs = _caller_inputs(format_caller, "format")

    # The provider keeps matcher-specific negation explicit: markdownlint gets
    # a negative CLI glob, while Prettier gets a positive ignore-file pattern.
    assert lint_inputs["globs"] == f"**/*.md\n!{exclusion}"
    assert format_inputs["exclusions"] == exclusion

    ignore = tmp_path / "provider.ignore"
    ignore.write_text(f"{format_inputs['exclusions']}\n", encoding="utf-8")
    prettier_selected = prettier_differences(
        _ROOT,
        tmp_path,
        ("**/*.md",),
        ignore_path=ignore,
    )
    lint_selected = markdownlint_findings(
        _ROOT,
        tmp_path,
        tuple(cast("str", lint_inputs["globs"]).splitlines()),
    )

    caller_path = tmp_path / "format.caller.yml"
    caller_path.write_text(format_caller, encoding="utf-8")
    workflow_selected = _prettier_workflow_findings(tmp_path, caller_path)

    assert prettier_selected == lint_selected == workflow_selected == expected
    assert set(expected) <= set(all_files)


def test_t9_no_divergence_guard__nested_reinclude__matches_pinned_dialects(
    tmp_path: Path,
) -> None:
    """TC-T9-001: supported matcher negation re-includes the same nested file."""
    all_files = _write_markdown_fixture(tmp_path)
    ignore = tmp_path / "nested-reinclude.ignore"
    # gitignore syntax cannot re-include a file while its parent directory stays
    # ignored. Re-open the parent before the file; markdownlint's ordered CLI
    # globs need only the final positive file pattern.
    ignore.write_text(
        "payload/**\n!payload/deep/\n!payload/deep/nested.md\n",
        encoding="utf-8",
    )
    patterns = ("**/*.md", "!payload/**", "payload/deep/nested.md")

    prettier_selected = prettier_differences(
        _ROOT,
        tmp_path,
        ("**/*.md",),
        ignore_path=ignore,
    )
    lint_selected = markdownlint_findings(_ROOT, tmp_path, patterns)

    expected = ("outside.md", "payload/deep/nested.md")
    assert prettier_selected == lint_selected == expected
    assert set(expected) < set(all_files)


@pytest.mark.parametrize("exclusion", ["payload", "payload/", "payload/**", r"payload\**"])
def test_t9_successor_rendering__characterized_exclusion__matches_1_8_inputs(
    exclusion: str,
) -> None:
    """TC-T9-002: no reproduced divergence means no provider normalization."""
    for provider_id, job in (
        ("render-lint-caller", "lint-markdown"),
        ("render-format-caller", "format"),
    ):
        successor = _caller_inputs(_render(_V19, provider_id, exclusion), job)
        predecessor = _caller_inputs(_render(_V18, provider_id, exclusion), job)
        assert successor == predecessor


def test_t9_successor_retention__catalog_role_and_predecessor_immutable() -> None:
    """TC-T9-002: 1.9 stays advertised beside released 1.8 after 5.10 advanced the default."""
    family = load_family_manifest(_FAMILY / "standard.toml")
    versions = {entry.version.value: entry for entry in family.versions}
    assert "1.9" in versions

    successor = _payload(_V19)
    assert successor.manifest.payload.availability is PayloadAvailability.CONSUMER
    assert successor.integrity.aggregate_digest == versions["1.9"].digest

    catalog = load_catalog_source(_ROOT / "catalogs/5.toml")
    markdown_entries = [entry for entry in catalog.packages if entry.id == "markdown-tooling"]
    roles = {entry.version.value: entry.role.value for entry in markdown_entries}
    assert roles[successor.manifest.payload.version.value] == "retained"
    assert roles[_V18.name] == "retained"

    predecessor = _payload(_V18)
    assert predecessor.integrity.aggregate_digest.value == _V18_AGGREGATE


def test_t9_unmigrated_1_8_fixture__shared_v5_workflow_outcomes__stay_unchanged(
    tmp_path: Path,
) -> None:
    """TC-T9-001: an exact-1.8 caller keeps its @v5 behavior after staging 1.9."""
    _write_markdown_fixture(tmp_path)
    v18_caller = _render(_V18, "render-format-caller", "payload/**")
    v19_caller = _render(_V19, "render-format-caller", "payload/**")
    assert "@v5" in v18_caller
    assert _caller_inputs(v19_caller, "format") == _caller_inputs(v18_caller, "format")

    v18_path = tmp_path / "v18-format.caller.yml"
    v18_path.write_text(v18_caller, encoding="utf-8")
    baseline = _prettier_workflow_findings(tmp_path, v18_path)
    candidate = _prettier_workflow_findings(tmp_path, v18_path)

    assert baseline == candidate == ("outside.md",)
    assert hashlib.sha256(_FORMAT_WORKFLOW.read_bytes()).hexdigest() == _FORMAT_WORKFLOW_DIGEST
    assert hashlib.sha256(_LINT_WORKFLOW.read_bytes()).hexdigest() == _LINT_WORKFLOW_DIGEST


def test_t9_projection__successor_family_links_cover_every_payload_file() -> None:
    """TC-T9-002: the activated successor is package-visible from the wheel tree."""
    projection = _ROOT / "src/project_standards/payloads/markdown-tooling/1.9"
    source_files = {
        path.relative_to(_V19).as_posix(): path.read_bytes()
        for path in _V19.rglob("*")
        if path.is_file()
    }
    links = {
        path.relative_to(projection).as_posix(): path
        for path in projection.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert links.keys() == source_files.keys()
    for relative, link in links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_t9_payload_identity__successor_metadata__is_1_9() -> None:
    """Keep the cloned payload's declared identity aligned with its directory."""
    payload = tomllib.loads((_V19 / "payload.toml").read_text(encoding="utf-8"))
    assert payload["payload"] == {
        "standard": "markdown-tooling",
        "version": "1.9",
        "availability": "consumer",
    }
