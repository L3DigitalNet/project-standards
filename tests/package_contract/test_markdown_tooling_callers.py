"""T10 Markdown caller fixed-point and permission contracts.

The 1.9 successor owns both caller workflows. These tests pin their least-
privilege shape, YAML semantics, pinned-Prettier stability, and reconciliation
atomicity without changing the released 1.8 payload or Catalog 5 default.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
import yaml

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.providers import (
    ProviderInvocation,
    ProviderResult,
    invoke_provider,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.issue_regressions.tool_oracle import prettier_differences
from tests.package_contract.helpers import copy_minimal_repository

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_V19 = _FAMILY / "versions/1.9"


def _payload() -> InstalledPayload:
    manifest = load_payload_manifest(_V19 / "payload.toml")
    return InstalledPayload(_V19, manifest, validate_payload_integrity(_V19, manifest))


def _options(**overrides: object) -> JsonObject:
    payload = _payload()
    return load_option_schema(_V19, payload.manifest).resolve_options(cast("JsonObject", overrides))


def _render(provider_id: str, config: JsonObject) -> str:
    payload = _payload()
    result = invoke_provider(
        ProviderInvocation(
            repo=_V19,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={},
        )
    )
    assert result.content is not None
    return result.content.decode()


def _installed_distribution(tmp_path: Path) -> InstalledDistribution:
    fixture = tmp_path / "distribution"
    repository = copy_minimal_repository(fixture)
    family = repository / "standards/markdown-tooling"
    shutil.copytree(_FAMILY, family)
    payload = _payload()
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-tooling"
name = "Markdown Tooling Standard"
summary = "Prettier and markdownlint with semantic editor configuration."
status = "active"

[[versions]]
version = "1.9"
payload = "versions/1.9/payload.toml"
digest = "{payload.integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "markdown-tooling"
version = "1.9"
digest = "{payload.integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _tree(root: Path) -> dict[str, tuple[str, bytes]]:
    snapshot: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", path.readlink().as_posix().encode())
        elif path.is_dir():
            snapshot[relative] = ("directory", b"")
        else:
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


def _long_options() -> JsonObject:
    return _options(
        markdown_globs=[
            "documentation/reference/components/subsystems/integrations/**/*.md",
            "documentation/guides/operators/troubleshooting/**/*.md",
        ],
        config_globs=[
            "configuration/environments/production/services/**/*.yaml",
            "configuration/environments/staging/services/**/*.json",
        ],
        exclusions=[
            {
                "glob": "documentation/reference/generated/third-party-content/**",
                "applies_to": "both",
                "reason": "Generated third-party content has a separate owner.",
            },
            {
                "glob": "configuration/environments/production/generated/**",
                "applies_to": "format",
                "reason": "Generated deployment configuration has a separate owner.",
            },
        ],
    )


@pytest.mark.parametrize(
    ("provider_id", "job_id", "workflow"),
    [
        pytest.param(
            "render-lint-caller",
            "lint-markdown",
            "lint-markdown.yml",
            id="lint",
        ),
        pytest.param("render-format-caller", "format", "format.yml", id="format"),
    ],
)
def test_t10_callers__reusable_jobs__grant_only_job_contents_read(
    provider_id: str,
    job_id: str,
    workflow: str,
) -> None:
    """TC-T10-001: each reusable call receives only its required read grant."""
    caller = cast("dict[str, object]", yaml.safe_load(_render(provider_id, _options())))
    assert "permissions" not in caller
    jobs = cast("dict[str, object]", caller["jobs"])
    job = cast("dict[str, object]", jobs[job_id])

    assert job["uses"] == f"L3DigitalNet/project-standards/.github/workflows/{workflow}@v5"
    assert job["permissions"] == {"contents": "read"}


@pytest.mark.parametrize(
    ("case", "config"),
    [
        pytest.param("short", _options(), id="short"),
        pytest.param("long", _long_options(), id="long"),
    ],
)
@pytest.mark.parametrize(
    ("provider_id", "job_id"),
    [
        pytest.param("render-lint-caller", "lint-markdown", id="lint"),
        pytest.param("render-format-caller", "format", id="format"),
    ],
)
def test_t10_callers__short_and_long_inputs__are_prettier_stable(
    tmp_path: Path,
    case: str,
    config: JsonObject,
    provider_id: str,
    job_id: str,
) -> None:
    """TC-T10-002: caller YAML is canonical before consumer formatting."""
    rendered = _render(provider_id, config)
    path = tmp_path / f"{provider_id}.yml"
    path.write_text(rendered, encoding="utf-8")

    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            (path.name,),
            config_path=_V19 / "artifacts/prettierrc.json",
        )
        == ()
    )
    parsed = cast("dict[str, object]", yaml.safe_load(rendered))
    jobs = cast("dict[str, object]", parsed["jobs"])
    inputs = cast("dict[str, object]", cast("dict[str, object]", jobs[job_id])["with"])
    markdown = cast("list[object]", config["markdown_globs"])
    exclusions = cast("list[object]", config["exclusions"])
    lint_exclusions = sorted(
        f"!{cast('dict[str, object]', item)['glob']}"
        for item in exclusions
        if cast("dict[str, object]", item)["applies_to"] in {"lint", "both"}
    )
    expected_globs = [*cast("list[str]", markdown)]
    if job_id == "lint-markdown":
        expected_globs.extend(lint_exclusions)
    else:
        expected_globs.extend(cast("list[str]", config["config_globs"]))
    assert inputs["globs"] == "\n".join(expected_globs)

    if case == "long":
        assert "      globs: |-" in rendered
        if job_id == "format":
            assert "      exclusions: |-" in rendered


@pytest.mark.parametrize(
    ("provider_id", "job_id", "config", "input_name", "expected"),
    [
        pytest.param(
            "render-lint-caller",
            "lint-markdown",
            _options(markdown_globs=['a"']),
            "globs",
            'a"',
            id="lint-include",
        ),
        pytest.param(
            "render-format-caller",
            "format",
            _options(markdown_globs=['a"']),
            "globs",
            'a"\n**/*.json\n**/*.jsonc\n**/*.yml\n**/*.yaml',
            id="format-include",
        ),
        pytest.param(
            "render-lint-caller",
            "lint-markdown",
            _options(
                exclusions=[
                    {
                        "glob": 'a"',
                        "applies_to": "lint",
                        "reason": "Separate owner.",
                    }
                ]
            ),
            "globs",
            '**/*.md\n!a"',
            id="lint-exclusion",
        ),
        pytest.param(
            "render-format-caller",
            "format",
            _options(
                exclusions=[
                    {
                        "glob": 'a"',
                        "applies_to": "format",
                        "reason": "Separate owner.",
                    }
                ]
            ),
            "exclusions",
            'a"',
            id="format-exclusion",
        ),
    ],
)
def test_t10_callers__quoted_globs__are_prettier_stable_literal_inputs(
    tmp_path: Path,
    provider_id: str,
    job_id: str,
    config: JsonObject,
    input_name: str,
    expected: str,
) -> None:
    rendered = _render(provider_id, config)
    path = tmp_path / f"{provider_id}.yml"
    path.write_text(rendered, encoding="utf-8")

    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            (path.name,),
            config_path=_V19 / "artifacts/prettierrc.json",
        )
        == ()
    )
    parsed = cast("dict[str, object]", yaml.safe_load(rendered))
    jobs = cast("dict[str, object]", parsed["jobs"])
    inputs = cast("dict[str, object]", cast("dict[str, object]", jobs[job_id])["with"])
    assert inputs[input_name] == expected


@pytest.mark.parametrize("line_break", ["\u0085", "\u2028", "\u2029"])
def test_t10_options__yaml_line_break_in_glob__fails_schema_validation(
    line_break: str,
) -> None:
    with pytest.raises(PackageContractError, match="markdown_globs"):
        _options(markdown_globs=[f"docs/{line_break}/**/*.md"])


@pytest.mark.parametrize("line_break", ["\u0085", "\u2028", "\u2029"])
def test_t10_provider_bypass__yaml_line_break_in_exclusion__fails_safely(
    line_break: str,
) -> None:
    config = _options()
    config["exclusions"] = [
        {
            "glob": f"docs/{line_break}/**",
            "applies_to": "format",
            "reason": "Separate owner.",
        }
    ]

    with pytest.raises(ControlPlaneError) as raised:
        _render("render-format-caller", config)
    assert isinstance(raised.value.__cause__, ValueError)
    assert "safe exclusion glob" in str(raised.value.__cause__)


def test_t10_successor_reconcile__long_callers__reach_clean_fixed_point(
    tmp_path: Path,
) -> None:
    """TC-T10-002: reconcile and pinned Prettier agree on exact caller bytes."""
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    long = _long_options()
    (repo / ".standards/config.toml").write_text(
        f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-tooling]
enabled = true
version = "1.9"

[standards.markdown-tooling.config]
contract_version = "1.1"
lint = true
format = true
markdown_globs = {long["markdown_globs"]!r}
config_globs = {long["config_globs"]!r}
exclusions = [
  {{ glob = "{cast("list[dict[str, object]]", long["exclusions"])[0]["glob"]}", applies_to = "both", reason = "Generated third-party content has a separate owner." }},
  {{ glob = "{cast("list[dict[str, object]]", long["exclusions"])[1]["glob"]}", applies_to = "format", reason = "Generated deployment configuration has a separate owner." }},
]

[standards.markdown-tooling.config.ci]
lint_caller = true
format_caller = true
'''.replace("'", '"'),
        encoding="utf-8",
    )

    first_request = build_planner_request(repo, distribution, frozenset())
    first = plan_reconciliation(first_request)
    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(first_request, first)).success
    callers = (
        ".github/workflows/lint-markdown.yml",
        ".github/workflows/format.yml",
    )
    assert (
        prettier_differences(
            _ROOT,
            repo,
            callers,
            config_path=_V19 / "artifacts/prettierrc.json",
        )
        == ()
    )
    before = _tree(repo)

    second_request = build_planner_request(repo, distribution, frozenset())
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in second.actions
    )
    result = apply_reconciliation(ApplyRequest(second_request, second))
    assert result.success
    assert result.applied_action_ids == ()
    assert not result.lock_written
    assert _tree(repo) == before


def test_t10_successor_planning__provider_error__preserves_complete_tree(
    tmp_path: Path,
) -> None:
    """TC-T10-002: caller rendering fails before the executor can mutate."""
    distribution = _installed_distribution(tmp_path)
    repo = tmp_path / "consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    (repo / ".standards/config.toml").write_text(
        """[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-tooling]
enabled = true
version = "1.9"
""",
        encoding="utf-8",
    )
    request = build_planner_request(repo, distribution, frozenset())

    def fail_caller(invocation: ProviderInvocation) -> ProviderResult:
        if invocation.provider_id == "render-lint-caller":
            raise ControlPlaneError("synthetic caller formatter failure")
        return invoke_provider(invocation)

    failing_request = replace(request, provider_runner=fail_caller)
    before = _tree(repo)

    with pytest.raises(ControlPlaneError, match="synthetic caller formatter failure"):
        plan_reconciliation(failing_request)

    assert _tree(repo) == before
