"""Issue #63: the 1.10 lint scope must skip the same generated trees Prettier does.

The format path reaches Prettier through ``--ignore-path .gitignore``, so
Git-ignored trees never enter it. The lint path passes bare CLI globs to
markdownlint-cli2, which traverses dot directories and ``node_modules``. These
tests pin the closing of that asymmetry at three boundaries: the provider-rendered
caller, the self-hosted workflow resource, and the pinned tools themselves, using
a consumer that has both Python Tooling and Markdown Tooling enabled.
"""

from __future__ import annotations

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
    PayloadAvailability,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.issue_regressions.tool_oracle import markdownlint_findings, prettier_differences

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_V19 = _FAMILY / "versions/1.9"
_V110 = _FAMILY / "versions/1.10"

# The four trees the catalog's own tools generate. `.mypy_cache` is deliberately
# absent: mypy is not selectable in the Python Tooling option schema (issue #56).
_GENERATED_EXCLUSIONS = (
    "!.pytest_cache/**",
    "!.ruff_cache/**",
    "!.venv/**",
    "!node_modules/**",
)

# A Python consumer's generated Markdown, keyed by whether it is repository content.
_SELECTED = ("outside.md", "docs/guide.md")
_GENERATED = (
    ".pytest_cache/README.md",
    ".ruff_cache/notes.md",
    ".venv/lib/python3.14/site-packages/dep/README.md",
    "node_modules/pkg/readme.md",
)


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, overrides: JsonObject) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(overrides)


def _render(
    root: Path,
    provider_id: str,
    overrides: JsonObject,
    snapshots: JsonObject | None = None,
) -> str:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=_options(root, overrides),
            snapshots=snapshots or {},
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


def _lint_globs(root: Path, overrides: JsonObject) -> tuple[str, ...]:
    inputs = _caller_inputs(_render(root, "render-lint-caller", overrides), "lint-markdown")
    return tuple(cast("str", inputs["globs"]).splitlines())


def _write_python_consumer(root: Path) -> Path:
    """Materialize the issue's repro: selected Markdown beside generated Markdown.

    Returns the Prettier ignore file standing in for the consumer's `.gitignore`.
    The name matters: the markdownlint oracle runs under this repo's own
    `.markdownlint-cli2.jsonc`, which sets `gitignore: true`, so a fixture file
    literally named `.gitignore` would silence markdownlint-cli2 in the probe and
    make the 1.9 regression look already fixed. The bytes are what `uv sync` and a
    pytest run leave Git-ignored in such a consumer; only the filename differs.
    """
    for relative in (*_SELECTED, *_GENERATED):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # A findable violation, so a selected file always shows up in the oracle.
        path.write_text("# Title\n\n-   item\n", encoding="utf-8")
    ignore = root / "consumer.ignore"
    ignore.write_text(".venv/\n.pytest_cache/\n.ruff_cache/\nnode_modules/\n", encoding="utf-8")
    return ignore


def test_lint_caller__default_options__appends_the_generated_exclusions() -> None:
    """The rendered caller carries every generated-directory negation."""
    globs = _lint_globs(_V110, {})
    assert globs == ("**/*.md", *_GENERATED_EXCLUSIONS)
    # markdownlint-cli2 resolves its glob list in order, so a negation placed
    # before the positive pattern would be undone by it.
    assert globs.index("**/*.md") == 0


def test_lint_caller__opted_out__renders_the_1_9_scope_byte_for_byte() -> None:
    """`lint_generated_exclusions = false` is a complete escape hatch."""
    opted_out = _render(_V110, "render-lint-caller", {"lint_generated_exclusions": False})
    assert opted_out == _render(_V19, "render-lint-caller", {})


def test_lint_caller__consumer_exclusions__stay_additive_and_are_not_duplicated() -> None:
    """Issue #63's own workaround must not double-declare after the upgrade."""
    globs = _lint_globs(
        _V110,
        {
            "exclusions": [
                {"glob": ".venv/**", "applies_to": "both", "reason": "The 1.9 workaround."},
                {"glob": "vendor/**", "applies_to": "lint", "reason": "Vendored upstream docs."},
            ]
        },
    )
    assert globs.count("!.venv/**") == 1
    assert "!vendor/**" in globs
    assert set(_GENERATED_EXCLUSIONS) <= set(globs)


def test_format_caller__is_unchanged_from_1_9() -> None:
    """The fix is lint-only; Prettier already had `.gitignore` protection."""
    assert _render(_V110, "render-format-caller", {}) == _render(_V19, "render-format-caller", {})


def test_self_hosted_lint_workflow__carries_the_same_negations() -> None:
    """Self-hosted mode installs a static job, so its scope is baked in."""
    workflow = (_V110 / "resources/self-host-lint-markdown.yml").read_text(encoding="utf-8")
    raw: object = yaml.safe_load(workflow)
    assert isinstance(raw, dict)
    jobs = cast("dict[str, object]", raw)["jobs"]
    assert isinstance(jobs, dict)
    lint = cast("dict[str, object]", cast("dict[str, object]", jobs)["lint"])
    steps = lint["steps"]
    assert isinstance(steps, list)
    step = next(
        cast("dict[str, object]", raw_step)
        for raw_step in cast("list[object]", steps)
        if isinstance(raw_step, dict)
        and str(cast("dict[str, object]", raw_step).get("uses", "")).startswith(
            "DavidAnson/markdownlint-cli2-action@"
        )
    )
    inputs = cast("dict[str, object]", step["with"])
    globs = tuple(cast("str", inputs["globs"]).splitlines())
    assert globs[0] == "${{ inputs.globs || '**/*.md' }}"
    assert globs[1:] == _GENERATED_EXCLUSIONS


def test_instruction_block__publishes_the_scope_the_caller_renders() -> None:
    """An agent reading AGENTS.md must not understate what CI skips."""
    block = _render(
        _V110,
        "render-semantic",
        {},
        {
            "planned_contribution": {
                "adapter": "markdown-block",
                "scope": "block:markdown-tooling",
            }
        },
    )
    assert "Lint additionally skips generated directories:" in block
    for exclusion in _GENERATED_EXCLUSIONS:
        assert f"`{exclusion.removeprefix('!')}`" in block


def test_lint_scope__pinned_tools__matches_the_format_scope(tmp_path: Path) -> None:
    """The issue itself: the two authorities must select one effective corpus."""
    ignore = _write_python_consumer(tmp_path)

    lint_selected = markdownlint_findings(_ROOT, tmp_path, _lint_globs(_V110, {}))
    format_selected = prettier_differences(_ROOT, tmp_path, ("**/*.md",), ignore_path=ignore)

    assert lint_selected == format_selected == tuple(sorted(_SELECTED))


def test_lint_scope__1_9_regression__still_traverses_the_generated_trees(tmp_path: Path) -> None:
    """Keep the reported defect observable, so the fix cannot pass vacuously."""
    _write_python_consumer(tmp_path)

    selected = markdownlint_findings(_ROOT, tmp_path, _lint_globs(_V19, {}))

    assert selected == tuple(sorted((*_SELECTED, *_GENERATED)))


def test_payload_identity__successor_metadata__is_1_10() -> None:
    """Keep the cloned payload's declared identity aligned with its directory."""
    payload = tomllib.loads((_V110 / "payload.toml").read_text(encoding="utf-8"))
    assert payload["payload"] == {
        "standard": "markdown-tooling",
        "version": "1.10",
        "availability": "consumer",
    }


def test_family_index__records_1_10_and_leaves_1_9_immutable() -> None:
    """The staged successor is indexed by its own aggregate digest."""
    family = load_family_manifest(_FAMILY / "standard.toml")
    versions = {entry.version.value: entry for entry in family.versions}
    assert "1.10" in versions

    successor = _payload(_V110)
    assert successor.manifest.payload.availability is PayloadAvailability.CONSUMER
    assert successor.integrity.aggregate_digest == versions["1.10"].digest

    predecessor = _payload(_V19)
    assert predecessor.integrity.aggregate_digest == versions["1.9"].digest


def test_projection__successor_family_links_cover_every_payload_file() -> None:
    """The staged successor is package-visible from the wheel tree."""
    projection = _ROOT / "src/project_standards/payloads/markdown-tooling/1.10"
    source_files = {
        path.relative_to(_V110).as_posix(): path.read_bytes()
        for path in _V110.rglob("*")
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


@pytest.mark.parametrize("option", ["lint_generated_exclusions"])
def test_option_schema__declares_the_documented_opt_out(option: str) -> None:
    """The opt-out has to be a real schema option, not prose."""
    schema = tomllib.loads((_V110 / "payload.toml").read_text(encoding="utf-8"))
    assert schema["config"]["schema_resource"] == "config-schema"
    resolved = _options(_V110, {})
    assert resolved[option] is True
    assert _options(_V110, {option: False})[option] is False


def test_markdown_tooling_1_10__catalog_role__selects_the_successor_as_default() -> None:
    """Catalog 5 must actually select the successor these tests pin.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes the successor the default a consumer on
    `version = "latest"` resolves to.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "markdown-tooling"
    }

    assert roles["1.10"] == "default"
    assert roles["1.9"] == "retained"
