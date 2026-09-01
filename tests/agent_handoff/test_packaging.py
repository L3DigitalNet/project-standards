from __future__ import annotations

import json
import os
import stat
import subprocess
import tomllib
import zipfile
from pathlib import Path

import yaml

from project_standards.cli import main
from tests.payload_tree import payload_tree

_REPO = Path(__file__).parents[2]
_SOURCE = _REPO / "standards/agent-handoff"
_BUNDLE = _REPO / "src/project_standards/bundles/agent-handoff"
_V2_MANAGED = _SOURCE / "versions/1.2/provider-resources/managed"


def _source_files() -> tuple[Path, ...]:
    return tuple(sorted(path for path in payload_tree(_SOURCE) if path.is_file()))


def _legacy_mirrored_source_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _source_files()
        if path.relative_to(_SOURCE).parts[0] != "versions"
        and path.name not in {"README.md", "adopt.md", "agent-summary.md", "standard.toml"}
    )


def test_every_standard_source_file_has_byte_identical_bundle_mirror() -> None:
    source_relatives = {path.relative_to(_SOURCE) for path in _legacy_mirrored_source_files()}
    bundled_relatives = {
        path.relative_to(_BUNDLE)
        for path in payload_tree(_BUNDLE)
        if path.is_file()
        and path.name
        not in {"README.md", "adopt.md", "adopt.toml", "agent-summary.md", "standard.toml"}
    }

    assert source_relatives == bundled_relatives
    for relative in source_relatives:
        assert (_SOURCE / relative).read_bytes() == (_BUNDLE / relative).read_bytes(), relative


def test_every_declared_resource_resolves() -> None:
    manifest = tomllib.loads((_BUNDLE / "standard.toml").read_text(encoding="utf-8"))

    for relative in manifest["resources"].values():
        assert (_SOURCE / relative).is_file(), relative
        assert (_BUNDLE / relative).is_file(), relative


def test_skill_identity_version_and_openai_metadata_are_canonical() -> None:
    skill = (_SOURCE / "skills/agent-handoff/SKILL.md").read_text(encoding="utf-8")
    _opening, frontmatter, body = skill.split("---", maxsplit=2)
    metadata = yaml.safe_load(frontmatter)
    openai = yaml.safe_load(
        (_SOURCE / "skills/agent-handoff/agents/openai.yaml").read_text(encoding="utf-8")
    )

    assert metadata["name"] == "agent-handoff"
    assert metadata["metadata"]["version"] == "1.0"
    assert "license" not in metadata
    assert body.lstrip().startswith("# Agent Handoff")
    assert openai["interface"]["display_name"] == "Agent Handoff"
    assert "$agent-handoff" in openai["interface"]["default_prompt"]
    assert not list(_SOURCE.rglob("LICENSE*"))


def test_public_package_material_has_no_retired_runtime_dependency() -> None:
    forbidden = ("handoff-system-v3", "agent-handoff-v3", "~/projects/", "git clone")

    for path in _source_files():
        if path.name == "legacy-migration.md" or path.suffix not in {
            ".md",
            ".yaml",
            ".json",
            ".toml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(term in text for term in forbidden), path

        relative = path.relative_to(_SOURCE)
        if relative.parts[0] == "versions" and (
            "skills" in relative.parts or relative.as_posix().endswith("managed/skill.md")
        ):
            assert ".agents/agent-handoff/manifest.json" not in text, path


def test_consumer_docs_use_real_cli_flags_and_repo_indexes() -> None:
    adopt = (_SOURCE / "adopt.md").read_text(encoding="utf-8")
    root_readme = (_REPO / "README.md").read_text(encoding="utf-8")
    standards_index = (_REPO / "standards/README.md").read_text(encoding="utf-8")
    package_readme = (_REPO / "src/project_standards/README.md").read_text(encoding="utf-8")
    authoring = tomllib.loads(
        (_REPO / "standards/standard-bundle-authoring/standard.toml").read_text(encoding="utf-8")
    )
    authoring_version = authoring["versions"][-1]["version"]

    assert "--repository" not in adopt
    assert "--repo ." in adopt
    assert "Agent Handoff Standard" in root_readme
    assert "[agent-handoff/]" in standards_index
    assert "project-standards agent-handoff" in package_readme
    assert f"Standard Bundle Authoring {authoring_version} workflow" in package_readme
    assert f"versions/{authoring_version}/README.md" in package_readme


def test_repository_dogfoods_agent_handoff_v5() -> None:
    config = tomllib.loads((_REPO / ".standards/config.toml").read_text(encoding="utf-8"))
    catalog = tomllib.loads((_REPO / "catalogs/5.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((_REPO / ".standards/lock.toml").read_text(encoding="utf-8"))
    claude = (_REPO / ".claude/settings.json").read_text(encoding="utf-8")
    codex = (_REPO / ".codex/config.toml").read_text(encoding="utf-8")
    prettier_ignores = set((_REPO / ".prettierignore").read_text(encoding="utf-8").splitlines())
    default_version = next(
        package["version"]
        for package in catalog["packages"]
        if package["id"] == "agent-handoff" and package["role"] == "default"
    )

    assert config["standards"]["agent-handoff"] == {
        "enabled": True,
        "version": "latest",
        "config": {
            "contract_version": "1.0",
            "startup": "automatic",
            "harnesses": ["claude-code", "codex"],
        },
    }
    assert lock["standards"]["agent-handoff"]["resolved"] == default_version
    assert not (_REPO / ".agents/agent-handoff/manifest.json").exists()
    # 1.10 ships the launcher as a compiled binary with no provider-resource byte copy,
    # so the payload artifact source is the only thing to compare it against.
    assert (_REPO / ".agents/hooks/agent-handoff/session-start").read_bytes() == (
        _SOURCE / f"versions/{default_version}/hooks/session-start/session-start"
    ).read_bytes()
    assert (_REPO / ".agents/skills/agent-handoff/SKILL.md").read_bytes() == (
        _SOURCE / f"versions/{default_version}/provider-resources/managed/skill.md"
    ).read_bytes()
    assert (_REPO / ".standards/packages/agent-handoff/policy.toml").read_bytes() == (
        _V2_MANAGED / "policy.toml"
    ).read_bytes()
    assert ".agents/hooks/agent-handoff/session-start" in claude
    assert ".agents/hooks/agent-handoff/session-start" in codex
    assert "handoff-system-v3" not in claude + codex
    assert {"AGENTS.md", "CLAUDE.md", "docs/STATUS.md", "docs/TODO.md"} <= prettier_ignores
    assert not (_REPO / ".agents/skills/handoff-system-v3").exists()
    assert not (_REPO / ".claude/hooks/session_start.py").exists()
    assert not (_REPO / ".codex/hooks/session_start.py").exists()
    assert not (_REPO / "STATUS.md").exists()
    assert not (_REPO / "TODO.md").exists()


def test_automatic_adoption_preserves_executable_hook_mode(tmp_path: Path) -> None:
    assert (
        main(
            [
                "adopt",
                "agent-handoff",
                "--dest",
                str(tmp_path),
            ]
        )
        == 0
    )

    # 1.10 replaced the Python hook with the compiled `session-start`. The property under
    # test is unchanged: adoption must deliver the launcher executable, because the
    # harness invokes it directly and a 0644 delivery fails the session start.
    hook = tmp_path / ".agents/hooks/agent-handoff/session-start"
    assert stat.S_IMODE(hook.stat().st_mode) == 0o755
    assert main(["agent-handoff", "validate", "--repo", str(tmp_path)]) == 0


def test_wheel_contains_complete_agent_handoff_bundle(built_wheel: Path) -> None:
    names = set(zipfile.ZipFile(built_wheel).namelist())

    for bundled in payload_tree(_BUNDLE):
        if not bundled.is_file():
            continue
        relative = bundled.relative_to(_BUNDLE).as_posix()
        expected = f"project_standards/bundles/agent-handoff/{relative}"
        assert any(name.endswith(expected) for name in names), expected


def test_installed_wheel_adopts_and_validates_without_source_checkout(
    tmp_path: Path, built_wheel: Path
) -> None:
    wheel = built_wheel
    venv = tmp_path / "venv"
    environment = {**os.environ, "PYTHONPATH": ""}
    subprocess.run(["uv", "venv", "--seed", str(venv)], check=True, capture_output=True)
    subprocess.run(
        [str(venv / "bin/python"), "-m", "pip", "install", "--quiet", str(wheel)],
        env=environment,
        check=True,
        capture_output=True,
    )
    repository = tmp_path / "consumer"
    repository.mkdir()
    executable = venv / "bin/project-standards"

    adopted = subprocess.run(
        [
            str(executable),
            "adopt",
            "agent-handoff",
            "--dest",
            str(repository),
        ],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert adopted.returncode == 0, adopted.stderr

    validated = subprocess.run(
        [str(executable), "agent-handoff", "validate", "--repo", str(repository), "--json"],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["findings"] == []

    imported = subprocess.run(
        [
            str(venv / "bin/python"),
            "-c",
            "import project_standards; print(project_standards.__file__)",
        ],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(_REPO) not in imported.stdout
