from __future__ import annotations

from pathlib import Path

from project_standards.standards_graph.discovery import build_graph
from project_standards.standards_graph.validators import targets_may_overlap, validate_graph
from tests.standards_graph_helpers import write_standard


def _codes(root: Path, *, require_all_manifests: bool = False) -> set[str]:
    return {
        finding.code
        for finding in validate_graph(
            build_graph(root), require_all_manifests=require_all_manifests
        )
    }


def test_duplicate_config_namespace_is_error(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", namespaces=["markdown.frontmatter"])
    write_standard(tmp_path, "beta", namespaces=["markdown.frontmatter"])

    findings = validate_graph(build_graph(tmp_path))

    assert [(f.code, f.standard_id) for f in findings] == [
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "alpha"),
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "beta"),
    ]


def test_validate_graph_returns_multiple_findings_in_stable_order(tmp_path: Path) -> None:
    write_standard(tmp_path, "beta", namespaces=["duplicate"], adoption="copy-adopt")
    write_standard(tmp_path, "alpha", namespaces=["duplicate"], adoption="copy-adopt")

    findings = validate_graph(build_graph(tmp_path))

    assert [(finding.code, finding.standard_id) for finding in findings] == [
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "alpha"),
        ("SG-CONFIG-DUPLICATE-NAMESPACE", "beta"),
        ("SG-RESOURCE-ADOPT-MISSING", "alpha"),
        ("SG-RESOURCE-ADOPT-MISSING", "beta"),
    ]


def test_missing_manifest_is_optional_until_retrofit_gate(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha")
    missing = tmp_path / "standards" / "beta"
    missing.mkdir(parents=True)
    (missing / "README.md").write_text("# beta\n", encoding="utf-8")

    assert "SG-MANIFEST-MISSING" not in _codes(tmp_path)
    assert "SG-MANIFEST-MISSING" in _codes(tmp_path, require_all_manifests=True)


def test_adoptable_standard_requires_adopt_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "copyable", adoption="copy-adopt")

    assert "SG-RESOURCE-ADOPT-MISSING" in _codes(tmp_path)


def test_provider_schema_resources_must_exist_when_declared(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        resources={"schema": "schemas/out.json"},
        providers=[
            {
                "operation": "validate",
                "kind": "python",
                "entrypoint": "pkg.mod:validate",
                "optional": False,
                "output_schema": "missing_schema",
            }
        ],
    )

    assert "SG-PROVIDER-SCHEMA-MISSING" in _codes(tmp_path)


def test_mutating_authority_conflict_is_error(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "prettier",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "beta",
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "otherfmt",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" in _codes(tmp_path)


def test_non_mutating_authorities_do_not_conflict(tmp_path: Path) -> None:
    authority: dict[str, object] = {
        "domain": "markdown",
        "target": "**/*.md",
        "concern": "structure-lint",
        "owner": "markdownlint",
        "mutates": False,
    }
    write_standard(tmp_path, "alpha", authorities=[authority])
    write_standard(tmp_path, "beta", authorities=[{**authority, "owner": "custom-lint"}])

    assert "SG-AUTHORITY-CONFLICT" not in _codes(tmp_path)


def test_extends_relation_allows_compatible_authority_overlap(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "base",
        resources={"extension_adr": "resources/extension-adr.md"},
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "prettier",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "child",
        resources={"extension_adr": "resources/extension-adr.md"},
        extends=["base"],
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "otherfmt",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" not in _codes(tmp_path)


def test_extends_without_adr_does_not_suppress_authority_conflict(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "base",
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "prettier",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "child",
        extends=["base"],
        authorities=[
            {
                "domain": "markdown",
                "target": "**/*.md",
                "concern": "physical-formatting",
                "owner": "otherfmt",
                "mutates": True,
            }
        ],
    )

    codes = _codes(tmp_path)
    assert "SG-AUTHORITY-CONFLICT" in codes
    assert "SG-REL-EXTENDS-NO-ADR" in codes


def test_target_overlap_catches_literal_file_inside_recursive_extension_glob() -> None:
    assert targets_may_overlap("pyproject.toml", "**/*.toml") is True
    assert targets_may_overlap("README.md", "**/*.toml") is False


def test_mutating_authority_conflict_detects_literal_file_against_recursive_glob(
    tmp_path: Path,
) -> None:
    write_standard(
        tmp_path,
        "alpha",
        authorities=[
            {
                "domain": "python",
                "target": "pyproject.toml",
                "concern": "tool-config",
                "owner": "uv",
                "mutates": True,
            }
        ],
    )
    write_standard(
        tmp_path,
        "beta",
        authorities=[
            {
                "domain": "python",
                "target": "**/*.toml",
                "concern": "tool-config",
                "owner": "other-tool",
                "mutates": True,
            }
        ],
    )

    assert "SG-AUTHORITY-CONFLICT" in _codes(tmp_path)


def test_relationships_must_point_to_known_standards(tmp_path: Path) -> None:
    write_standard(
        tmp_path, "alpha", companions=["missing"], extends=["also-missing"], conflicts=["gone"]
    )

    assert "SG-REL-MISSING-STANDARD" in _codes(tmp_path)


def test_extends_cycle_is_error(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        extends=["beta"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )
    write_standard(
        tmp_path,
        "beta",
        extends=["alpha"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )

    assert "SG-REL-EXTENDS-CYCLE" in _codes(tmp_path)


def test_extends_cycle_finding_only_marks_cycle_participants(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        extends=["beta"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )
    write_standard(
        tmp_path,
        "beta",
        extends=["alpha"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )
    write_standard(tmp_path, "delta")
    write_standard(
        tmp_path,
        "gamma",
        extends=["delta"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )

    findings = validate_graph(build_graph(tmp_path))

    cycle_ids = {
        finding.standard_id for finding in findings if finding.code == "SG-REL-EXTENDS-CYCLE"
    }
    assert cycle_ids == {"alpha", "beta"}


def test_extends_requires_adr_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(tmp_path, "child", extends=["base"])

    assert "SG-REL-EXTENDS-NO-ADR" in _codes(tmp_path)


def test_extends_accepts_bundle_local_adr_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(
        tmp_path,
        "child",
        extends=["base"],
        resources={"extension_adr": "resources/extension-adr.md"},
    )

    assert "SG-REL-EXTENDS-NO-ADR" not in _codes(tmp_path)


def test_extends_requires_exact_extension_adr_resource_id(tmp_path: Path) -> None:
    write_standard(tmp_path, "base")
    write_standard(
        tmp_path,
        "child",
        extends=["base"],
        resources={"adr_notes": "resources/extension-adr.md"},
    )

    assert "SG-REL-EXTENDS-NO-ADR" in _codes(tmp_path)


def test_consumes_platform_must_not_name_standard_capability(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", provides=["markdown.format"])
    write_standard(tmp_path, "beta", consumes_platform=["markdown.format"])

    assert "SG-CAPABILITY-STANDARD-CONSUMED" in _codes(tmp_path)


def test_consumes_platform_allows_known_platform_capability(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", consumes_platform=["project-standards.validate"])

    assert "SG-CAPABILITY-PLATFORM-UNKNOWN" not in _codes(tmp_path)


def test_companion_is_advisory_not_required(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", companions=["beta"])
    write_standard(tmp_path, "beta")

    findings = validate_graph(build_graph(tmp_path))

    assert "SG-REL-MISSING-STANDARD" not in {finding.code for finding in findings}
    assert "SG-REL-EXTENDS-NO-ADR" not in {finding.code for finding in findings}


def test_missing_companion_is_reported_but_not_as_extension(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", companions=["beta"])

    findings = validate_graph(build_graph(tmp_path))
    codes = {finding.code for finding in findings}

    assert "SG-REL-MISSING-STANDARD" in codes
    assert "SG-REL-EXTENDS-NO-ADR" not in codes
