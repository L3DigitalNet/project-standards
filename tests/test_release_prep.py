"""Regression tests for the release-preparation operator handoff."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import CaptureFixture

from tests.module_loading import load_module_from_path


def _release_prep_module() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "scripts" / "release_prep.py"
    # register=True: the script's frozen dataclasses resolve their string
    # annotations through `sys.modules["release_prep"]` as the class bodies
    # execute, and a missing entry aborts the load.
    return load_module_from_path("release_prep", path, register=True)


def _write_catalog(root: Path, packages: list[tuple[str, str, str]]) -> None:
    catalog = ['schema_version = "1.0"', "catalog_major = 5", ""]
    for family, version, role in packages:
        catalog.extend(
            [
                "[[packages]]",
                f'id = "{family}"',
                f'version = "{version}"',
                'digest = "sha256:test"',
                f'role = "{role}"',
                "",
            ]
        )
    (root / "catalogs").mkdir(parents=True, exist_ok=True)
    (root / "catalogs" / "5.toml").write_text("\n".join(catalog), encoding="utf-8")


def _selection_tuples(review: Any) -> list[tuple[str, str, str]]:
    return [
        (selection.family, selection.version, selection.role) for selection in review.selections
    ]


def _stub_release_flow(
    release_prep: Any,
    monkeypatch: pytest.MonkeyPatch,
    current: Any,
) -> None:
    def check_preconditions(_target: object) -> tuple[Any, Any]:
        return (current, release_prep.StepResult("preconditions", "ok", "ready"))

    def plan_changelog(_target: object, *, today: str) -> Any:
        return release_prep.ChangelogPlan("", today, "planned")

    def previous_release_tag(_target: object) -> str:
        return "v5.18.0"

    def step(*_args: object, **_kwargs: object) -> Any:
        return release_prep.StepResult("step", "planned", "none")

    def verify(*_args: object, **_kwargs: object) -> list[Any]:
        return []

    monkeypatch.setattr(release_prep, "check_preconditions", check_preconditions)
    monkeypatch.setattr(release_prep, "plan_changelog", plan_changelog)
    monkeypatch.setattr(release_prep, "_previous_release_tag", previous_release_tag)
    monkeypatch.setattr(release_prep, "bump_version", step)
    monkeypatch.setattr(release_prep, "sweep_version_references", step)
    monkeypatch.setattr(release_prep, "apply_changelog", step)
    monkeypatch.setattr(release_prep, "verify_chain", verify)


def test_print_summary__prepared_release__prints_required_pre_tag_candidate_verification(
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    current = release_prep.Version.parse("5.13.0")
    target = release_prep.Version.parse("5.13.1")
    result = release_prep.StepResult("1. preconditions", "ok", "tree clean")

    release_prep.print_summary([result], target, current, "v5.13.0")

    summary = capsys.readouterr().out
    wheel = "build/release-wheel/project_standards-5.13.1-py3-none-any.whl"
    assert "uv sync --all-groups --locked" in summary
    assert "npm ci" in summary
    assert "standards sync-payload-projection --root . --check --json" in summary
    assert "uv build --clear --wheel --out-dir build/release-wheel" in summary
    assert "rm -rf -- build/wheel-runtime" in summary
    assert f"python -m zipfile -e {wheel} build/wheel-runtime" in summary
    assert 'export PYTHONPATH="$PWD/build/wheel-runtime"' in summary
    assert "scripts/verify.sh --full" in summary
    assert "uv run project-standards validate" in summary
    assert "standards validate-packages --root . --json" in summary
    assert "standards validate-graph --root . --require-all-manifests --json" in summary
    assert "standards generate-package-schemas --root . --check --json" in summary
    assert "packages check-release --root . --baseline v5.13.0 --json" in summary
    assert summary.index("uv sync --all-groups --locked") < summary.index(
        "uv build --clear --wheel --out-dir build/release-wheel"
    )
    assert summary.index(
        "standards sync-payload-projection --root . --check --json"
    ) < summary.index("uv build --clear --wheel --out-dir build/release-wheel")
    assert summary.index(
        "standards sync-payload-projection --root . --check --json"
    ) < summary.index("git tag -as v5.13.1")
    assert summary.index("npm ci") < summary.index("scripts/verify.sh --full")
    assert summary.index("scripts/verify.sh --full") < summary.index("git tag -as v5.13.1")


def test_check_preconditions__non_main_branch__refuses_release_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()

    def git(*args: str) -> str:
        if args == ("status", "--porcelain"):
            return ""
        assert args == ("rev-parse", "--abbrev-ref", "HEAD")
        return "testing\n"

    monkeypatch.setattr(release_prep, "_git", git)
    monkeypatch.setattr(release_prep, "_current_version", lambda: release_prep.Version(5, 13, 0))

    with pytest.raises(release_prep.ReleasePrepError, match="must run on 'main'"):
        release_prep.check_preconditions(release_prep.Version(5, 13, 1))


def test_main__stale_package_reference__reports_before_release_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    (tmp_path / "catalogs").mkdir()
    (tmp_path / "catalogs" / "5.toml").write_text(
        """\
schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "adr"
version = "1.4"
digest = "sha256:old"
role = "retained"

[[packages]]
id = "adr"
version = "1.5"
digest = "sha256:new"
role = "default"
""",
        encoding="utf-8",
    )
    family = tmp_path / "standards" / "adr"
    family.mkdir(parents=True)
    family.joinpath("README.md").write_text(
        "Current consumer package: `adr@1.4`.\n",
        encoding="utf-8",
    )

    current = release_prep.Version(5, 18, 0)
    target = release_prep.Version(5, 19, 0)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    _stub_release_flow(release_prep, monkeypatch, current)

    assert release_prep.main([str(target), "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "package-version references (review; nothing was rewritten)" in output
    assert (
        "standards/adr/README.md:1: family=adr observed=1.4 expected=1.5 "
        "reason=current exact-selector"
    ) in output


def test_plan_package_version_references__catalog_roles__selects_numeric_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()
    _write_catalog(
        tmp_path,
        [
            ("candidate-only", "3.0", "candidate"),
            ("consumer", "1.8", "retained"),
            ("consumer", "1.9", "default"),
            ("consumer", "2.0", "candidate"),
            ("internal", "2.9", "internal"),
            ("internal", "2.10", "internal"),
            ("reference", "0.9", "reference-only"),
            ("reference", "0.10", "reference-only"),
        ],
    )
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    review = release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))

    assert _selection_tuples(review) == [
        ("consumer", "1.9", "default"),
        ("internal", "2.10", "internal"),
        ("reference", "0.10", "reference-only"),
    ]
    assert review.mismatches == ()


def test_plan_package_version_references__root_forms__reports_only_current_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    _write_catalog(
        tmp_path,
        [
            ("adr", "1.4", "retained"),
            ("adr", "1.5", "default"),
            ("python-coding", "0.5", "reference-only"),
            ("python-coding", "0.6", "reference-only"),
            ("standard-bundle-authoring", "2.9", "internal"),
            ("standard-bundle-authoring", "2.10", "internal"),
        ],
    )
    adr = tmp_path / "standards" / "adr"
    adr.mkdir(parents=True)
    adr.joinpath("README.md").write_text(
        """\
Current selector `adr@1.4`.
Current [standard](versions/1.4/README.md).
project-standards standards enable adr --version 1.4
The adr version `1.4` is current.
Package version `1.4` is current.
ADR 1.4 standard is current.
Selected `adr@1.5` is already current.

## Migration

The superseded package `adr@1.4` remains historical.
""",
        encoding="utf-8",
    )
    adr.joinpath("agent-summary.md").write_text(
        """\
<!-- release-consistency: historical adr -->
The old selector `adr@1.4` is preserved for comparison.
""",
        encoding="utf-8",
    )
    python_coding = tmp_path / "standards" / "python-coding"
    python_coding.mkdir(parents=True)
    python_coding.joinpath("README.md").write_text(
        "Python Coding 0.6 is the current reference-only package.\n",
        encoding="utf-8",
    )
    internal = tmp_path / "standards" / "standard-bundle-authoring"
    internal.mkdir(parents=True)
    internal.joinpath("README.md").write_text(
        "Internal package `2.10` is current; 2.9 remains advertised as released history.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    before = {
        path: path.read_bytes()
        for path in (
            tmp_path / "catalogs" / "5.toml",
            adr / "README.md",
            adr / "agent-summary.md",
            python_coding / "README.md",
            internal / "README.md",
        )
    }

    review = release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))
    result = release_prep.report_package_version_references(review)

    assert len(review.mismatches) == 6
    assert [mismatch.kind for mismatch in review.mismatches] == [
        "exact-selector",
        "versioned-link",
        "enable-command",
        "family-prose",
        "family-prose",
        "named-prose",
    ]
    assert result.status == "ok"
    assert result.detail == "6 package-version mismatch occurrence(s) reported for review"
    assert "python-coding" not in capsys.readouterr().out
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("catalog", "message"),
    [
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.05"
role = "default"
""",
            "non-canonical package version",
        ),
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.5"
role = "default"
[[packages]]
id = "adr"
version = "1.5"
role = "retained"
""",
            "duplicates package/version adr@1.5",
        ),
        (
            """\
schema_version = "1.0"
catalog_major = 5
[[packages]]
id = "adr"
version = "1.5"
role = "default"
[[packages]]
id = "adr"
version = "2.0"
role = "internal"
""",
            "ambiguous selection for adr",
        ),
    ],
)
def test_plan_package_version_references__invalid_catalog__fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    catalog: str,
    message: str,
) -> None:
    release_prep = _release_prep_module()
    (tmp_path / "catalogs").mkdir()
    (tmp_path / "catalogs" / "5.toml").write_text(catalog, encoding="utf-8")
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    with pytest.raises(release_prep.ReleasePrepError, match=message):
        release_prep.plan_package_version_references(release_prep.Version(5, 19, 0))


def test_main__missing_candidate_catalog__fails_before_bump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    current = release_prep.Version(5, 18, 0)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    _stub_release_flow(release_prep, monkeypatch, current)

    def unexpected_bump(*_args: object, **_kwargs: object) -> Any:
        pytest.fail("version bump ran before package-reference preflight")

    monkeypatch.setattr(release_prep, "bump_version", unexpected_bump)

    assert release_prep.main(["5.19.0", "--dry-run"]) == 1
    assert "cannot read candidate catalog catalogs/5.toml" in capsys.readouterr().err


def test_sweep_version_references__agent_summary_only__preserves_old_target_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    summary = tmp_path / "standards" / "adr" / "agent-summary.md"
    summary.parent.mkdir(parents=True)
    summary.write_text("Outgoing tool release 5.18.0.\n", encoding="utf-8")
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    result = release_prep.sweep_version_references(release_prep.Version(5, 18, 0))

    assert result.detail == "0 occurrence(s) of 5.18.0 reported for review"
    assert "  none" in capsys.readouterr().out


def _write_pin_tree(root: Path) -> None:
    """Materialize one line per allow-listed matcher plus the judgment sites beside them.

    Every judgment site here is a real one the v5.28.0 train had to leave alone: the
    ROADMAP heading, the UPGRADING history heading, `_BASELINE_REF`, and package prose in
    `meta/versioning.md` that names a version the catalog does not select.
    """
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "meta").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "package_contract").mkdir(parents=True, exist_ok=True)

    (root / "README.md").write_text(
        "Project Standards 5.28.0 requires Python 3.14 or newer.\n"
        'uv tool install "git+https://github.com/L3DigitalNet/project-standards@v5.28.0"\n'
        "must report `project-standards 5.28.0`.\n"
        "    rev: v5.28.0 # pre-commit requires an immutable rev\n"
        "extract build/release-wheel/project_standards-5.28.0-py3-none-any.whl\n"
        "The v5.27.0 train is history and must not move.\n",
        encoding="utf-8",
    )
    (root / "UPGRADING.md").write_text(
        "- Install or invoke the exact v5 release you intend to pin. For 5.28.0:\n"
        '  uv tool install --force "git+https://github.com/L3DigitalNet/project-standards@v5.28.0"\n'
        "  Confirm that the command reports `project-standards 5.28.0`.\n"
        "### What the 5.28.0 defaults rewrite on refresh: an authored history heading\n",
        encoding="utf-8",
    )
    (root / "docs" / "mcp-server.md").write_text(
        'uv tool install "git+https://github.com/L3DigitalNet/project-standards@v5.28.0"\n'
        "sha256sum dist/project_standards-5.28.0-py3-none-any.whl\n"
        "The version command reports `project-standards 5.28.0`.\n",
        encoding="utf-8",
    )
    (root / "meta" / "versioning.md").write_text(
        "- The **Markdown Tooling contract version** is the closed option inside the "
        "selected payload, enforced independently from package release `1.15`.\n"
        "- The **Agent Handoff contract version** is the closed option inside the "
        "selected payload, enforced independently from package release `1.16`.\n"
        "- Markdown Tooling 1.14 remains advertised as released history.\n",
        encoding="utf-8",
    )
    (root / "ROADMAP.md").write_text("## Shipped in 5.28.0\n", encoding="utf-8")
    (root / "tests" / "package_contract" / "test_current_catalog_activation.py").write_text(
        '_BASELINE_REF = "v5.28.0"\n_RELEASE_VERSION = "5.28.0"\n',
        encoding="utf-8",
    )
    _write_catalog(
        root,
        [
            ("markdown-tooling", "1.16", "default"),
            ("markdown-tooling", "1.15", "retained"),
            ("agent-handoff", "1.16", "default"),
        ],
    )


def test_plan_pins__allow_listed_sites__rewrites_pins_and_leaves_judgment_sites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    plan = release_prep.plan_pins(release_prep.Version(5, 28, 0), release_prep.Version(5, 29, 0))

    assert [(edit.path, edit.matcher, edit.observed, edit.expected) for edit in plan.edits] == [
        ("README.md", "product-prose", "5.28.0", "5.29.0"),
        ("README.md", "install-tag", "5.28.0", "5.29.0"),
        ("README.md", "version-report", "5.28.0", "5.29.0"),
        ("README.md", "precommit-rev", "5.28.0", "5.29.0"),
        ("README.md", "wheel-artifact", "5.28.0", "5.29.0"),
        ("UPGRADING.md", "upgrade-target", "5.28.0", "5.29.0"),
        ("UPGRADING.md", "install-tag", "5.28.0", "5.29.0"),
        ("UPGRADING.md", "version-report", "5.28.0", "5.29.0"),
        ("docs/mcp-server.md", "install-tag", "5.28.0", "5.29.0"),
        ("docs/mcp-server.md", "wheel-artifact", "5.28.0", "5.29.0"),
        ("docs/mcp-server.md", "version-report", "5.28.0", "5.29.0"),
        (
            "tests/package_contract/test_current_catalog_activation.py",
            "release-constant",
            "5.28.0",
            "5.29.0",
        ),
        ("meta/versioning.md", "package-contract-prose", "1.15", "1.16"),
    ]
    # ROADMAP.md is absent from the allow-list entirely, so no plan can ever name it.
    assert {path for path, _ in plan.updates} == {
        "README.md",
        "UPGRADING.md",
        "docs/mcp-server.md",
        "meta/versioning.md",
        "tests/package_contract/test_current_catalog_activation.py",
    }


def test_apply_pins__dry_run__prints_diff_and_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    before = {path: path.read_text(encoding="utf-8") for path in sorted(tmp_path.rglob("*.md"))}

    plan = release_prep.plan_pins(release_prep.Version(5, 28, 0), release_prep.Version(5, 29, 0))
    result = release_prep.apply_pins(plan, dry_run=True)

    assert result.status == "planned"
    output = capsys.readouterr().out
    assert "--- a/README.md" in output
    assert "+++ b/README.md" in output
    assert "+Project Standards 5.29.0 requires Python 3.14 or newer." in output
    assert {path: path.read_text(encoding="utf-8") for path in before} == before


def test_apply_pins__applied__rewrites_only_pinned_lines_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)
    current = release_prep.Version(5, 28, 0)
    target = release_prep.Version(5, 29, 0)

    release_prep.apply_pins(release_prep.plan_pins(current, target), dry_run=False)

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "5.28.0" not in readme
    assert "The v5.27.0 train is history and must not move." in readme
    upgrading = (tmp_path / "UPGRADING.md").read_text(encoding="utf-8")
    assert "### What the 5.28.0 defaults rewrite on refresh" in upgrading
    activation = (
        tmp_path / "tests" / "package_contract" / "test_current_catalog_activation.py"
    ).read_text(encoding="utf-8")
    assert activation == '_BASELINE_REF = "v5.28.0"\n_RELEASE_VERSION = "5.29.0"\n'
    versioning = (tmp_path / "meta" / "versioning.md").read_text(encoding="utf-8")
    assert "independently from package release `1.16`" in versioning
    assert "Markdown Tooling 1.14 remains advertised as released history." in versioning
    assert (tmp_path / "ROADMAP.md").read_text(encoding="utf-8") == "## Shipped in 5.28.0\n"

    # A second pass finds nothing: the outgoing version is gone from every allow-listed
    # site, so re-running R3 after a partial train cannot double-rewrite.
    assert release_prep.plan_pins(current, target).edits == ()


def test_plan_pins__missing_allow_listed_site__fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    (tmp_path / "docs" / "mcp-server.md").unlink()
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    with pytest.raises(release_prep.ReleasePrepError) as error:
        release_prep.plan_pins(release_prep.Version(5, 28, 0), release_prep.Version(5, 29, 0))

    assert "allow-listed pin site docs/mcp-server.md does not exist" in str(error.value)


def test_main__apply_pins_write_off_release_branch__refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    def previous_release_tag(_target: object) -> str:
        return "v5.28.0"

    def git(*_args: str) -> str:
        return "testing\n"

    monkeypatch.setattr(release_prep, "_previous_release_tag", previous_release_tag)
    monkeypatch.setattr(release_prep, "_git", git)

    assert release_prep.main(["5.29.0", "--apply-pins"]) == 1
    assert "pin rewrites must be applied on 'main'" in capsys.readouterr().err
    assert "5.29.0" not in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_main__apply_pins_dry_run__runs_no_release_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    release_prep = _release_prep_module()
    _write_pin_tree(tmp_path)
    monkeypatch.setattr(release_prep, "REPO_ROOT", tmp_path)

    def previous_release_tag(_target: object) -> str:
        return "v5.28.0"

    monkeypatch.setattr(release_prep, "_previous_release_tag", previous_release_tag)

    def unexpected(*_args: object, **_kwargs: object) -> Any:
        pytest.fail("--apply-pins ran a release step other than the pin rewrite")

    monkeypatch.setattr(release_prep, "check_preconditions", unexpected)
    monkeypatch.setattr(release_prep, "bump_version", unexpected)
    monkeypatch.setattr(release_prep, "verify_chain", unexpected)

    assert release_prep.main(["5.29.0", "--apply-pins", "--dry-run"]) == 0
    assert (
        "outgoing version taken from the previous release tag: v5.28.0" in capsys.readouterr().out
    )
