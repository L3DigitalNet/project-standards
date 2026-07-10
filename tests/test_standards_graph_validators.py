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


def test_reference_only_standard_does_not_require_adopt_resource(tmp_path: Path) -> None:
    write_standard(tmp_path, "python-coding", adoption="reference-only")

    assert "SG-RESOURCE-ADOPT-MISSING" not in _codes(tmp_path)


def _write_artifact_manifest(root: Path, standard_id: str, body: str = "") -> str:
    relative = f"src/project_standards/bundles/{standard_id}/adopt.toml"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'[standard]\nid = "{standard_id}"\n{body}', encoding="utf-8")
    return relative


def _write_source_owned_hook_artifact(root: Path, *, canonical: str, dest: str) -> None:
    relative = _write_artifact_manifest(
        root,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        f'dest = "{dest}"\nprovenance = "source-owned"\n'
        f'canonical = "{canonical}"\n',
    )
    write_standard(
        root,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = root / "src/project_standards/bundles/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    if ".." not in Path(canonical).parts:
        canonical_path = root / canonical
        canonical_path.parent.mkdir(parents=True)
        canonical_path.write_text("hook\n", encoding="utf-8")


def test_packaged_artifact_manifest_requires_standard_manifest_link(tmp_path: Path) -> None:
    write_standard(tmp_path, "alpha", adoption="copy-adopt", resources={"adopt": "adopt.md"})
    _write_artifact_manifest(tmp_path, "alpha")

    assert "SG-ARTIFACT-MANIFEST-ORPHAN" in _codes(tmp_path)


def test_declared_artifact_manifest_must_exist(tmp_path: Path) -> None:
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest="src/project_standards/bundles/alpha/adopt.toml",
    )

    assert "SG-ARTIFACT-MANIFEST-MISSING" in _codes(tmp_path)


def test_artifact_manifest_link_must_name_own_bundle(tmp_path: Path) -> None:
    alpha = _write_artifact_manifest(tmp_path, "alpha")
    beta = _write_artifact_manifest(tmp_path, "beta")
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=beta,
    )
    write_standard(
        tmp_path,
        "beta",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=alpha,
    )

    assert "SG-ARTIFACT-MANIFEST-MISMATCH" in _codes(tmp_path)


def test_artifact_manifest_link_must_not_escape_through_symlink(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    packaged = outside / "bundles/alpha/adopt.toml"
    packaged.parent.mkdir(parents=True)
    packaged.write_text('[standard]\nid = "alpha"\n', encoding="utf-8")
    link = tmp_path / "src/project_standards/bundles/alpha"
    link.parent.mkdir(parents=True)
    link.symlink_to(packaged.parent, target_is_directory=True)
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest="src/project_standards/bundles/alpha/adopt.toml",
    )

    assert "SG-ARTIFACT-MANIFEST-ESCAPE" in _codes(tmp_path)


def test_non_adoptable_standard_must_not_link_artifact_manifest(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(tmp_path, "alpha")
    write_standard(tmp_path, "alpha", adoption="none", artifact_manifest=relative)

    assert "SG-ARTIFACT-NONADOPTABLE" in _codes(tmp_path)


def test_source_owned_artifact_must_match_canonical_source(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "seed.txt"\ndest = "seed.txt"\n'
        'provenance = "source-owned"\ncanonical = "standards/alpha/seed.txt"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    (tmp_path / "src/project_standards/bundles/alpha/seed.txt").write_text(
        "packaged\n", encoding="utf-8"
    )
    (tmp_path / "standards/alpha/seed.txt").write_text("canonical\n", encoding="utf-8")

    assert "SG-ARTIFACT-PARITY" in _codes(tmp_path)


def test_source_owned_canonical_must_not_escape_through_symlink(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "seed.txt"\ndest = "seed.txt"\n'
        'provenance = "source-owned"\ncanonical = "standards/alpha/seed.txt"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    source = tmp_path / "src/project_standards/bundles/alpha/seed.txt"
    source.write_text("same\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-canonical.txt"
    outside.write_text("same\n", encoding="utf-8")
    (tmp_path / "standards/alpha/seed.txt").symlink_to(outside)

    assert "SG-ARTIFACT-CANONICAL-MISSING" in _codes(tmp_path)


def test_generated_artifact_requires_safe_existing_canonical_source(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "generated.txt"\ndest = "generated.txt"\n'
        'provenance = "generated"\ncanonical = "../outside.txt"\ntransform = "render"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    (tmp_path / "src/project_standards/bundles/alpha/generated.txt").write_text(
        "generated\n", encoding="utf-8"
    )

    assert "SG-ARTIFACT-CANONICAL-MISSING" in _codes(tmp_path)


def test_standard_packaged_skill_must_install_project_locally(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "skills/demo/SKILL.md"\n'
        'dest = ".codex/skills/demo/SKILL.md"\nprovenance = "package-owned"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="copy-adopt",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    skill = tmp_path / "src/project_standards/bundles/alpha/skills/demo/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# demo\n", encoding="utf-8")

    assert "SG-ARTIFACT-SKILL-DEST" in _codes(tmp_path)


def test_standard_packaged_hook_must_install_under_shared_project_root(
    tmp_path: Path,
) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    canonical = tmp_path / "standards/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    canonical.write_text("hook\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)


def test_standard_packaged_hook_may_install_under_shared_project_root(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".agents/hooks/alpha/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    canonical = tmp_path / "standards/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    canonical.write_text("hook\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_standard_packaged_hook_rejects_similar_standard_destination(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".agents/hooks/alpha-other/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    canonical = tmp_path / "standards/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    canonical.write_text("hook\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)


def test_standard_packaged_hook_destination_requires_file_below_root(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".agents/hooks/alpha"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    canonical = tmp_path / "standards/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    canonical.write_text("hook\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)


def test_hook_canonical_directory_without_child_is_not_hook_source(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hook-source"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hook-source"
    canonical = tmp_path / "standards/alpha/hooks"
    packaged.write_text("not a hook path\n", encoding="utf-8")
    canonical.write_text("not a hook path\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_similar_standard_hook_canonical_is_not_owned_hook_source(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "consumer-script.py"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha-other/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/consumer-script.py"
    canonical = tmp_path / "standards/alpha-other/hooks/start/run.py"
    canonical.parent.mkdir(parents=True)
    packaged.write_text("consumer script\n", encoding="utf-8")
    canonical.write_text("consumer script\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_package_owned_hook_named_source_is_not_standard_packaged_hook(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "package-owned"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("package tooling\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_source_owned_consumer_script_is_not_standard_packaged_hook(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "scripts/run.py"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/scripts/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/scripts/run.py"
    canonical = tmp_path / "standards/alpha/scripts/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("consumer script\n", encoding="utf-8")
    canonical.write_text("consumer script\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_standard_packaged_hook_rejects_destination_traversal(tmp_path: Path) -> None:
    _write_source_owned_hook_artifact(
        tmp_path,
        canonical="standards/alpha/hooks/start/run.py",
        dest=".agents/hooks/alpha/../outside.py",
    )

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)


def test_standard_packaged_hook_accepts_normalized_destination_alias(tmp_path: Path) -> None:
    _write_source_owned_hook_artifact(
        tmp_path,
        canonical="standards/alpha/hooks/start/run.py",
        dest=".agents/hooks/alpha/./run.py",
    )

    assert "SG-ARTIFACT-HOOK-DEST" not in _codes(tmp_path)


def test_traversing_canonical_path_is_not_classified_as_hook(tmp_path: Path) -> None:
    _write_source_owned_hook_artifact(
        tmp_path,
        canonical="standards/alpha/hooks/../scripts/run.py",
        dest=".claude/hooks/run.py",
    )

    codes = _codes(tmp_path)
    assert "SG-ARTIFACT-CANONICAL-MISSING" in codes
    assert "SG-ARTIFACT-HOOK-DEST" not in codes


def test_normalized_canonical_alias_is_classified_as_hook(tmp_path: Path) -> None:
    _write_source_owned_hook_artifact(
        tmp_path,
        canonical="standards/alpha/hooks/./start/run.py",
        dest=".claude/hooks/run.py",
    )

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)


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
