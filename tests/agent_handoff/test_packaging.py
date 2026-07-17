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

_REPO = Path(__file__).parents[2]
_SOURCE = _REPO / "standards/agent-handoff"
_BUNDLE = _REPO / "src/project_standards/bundles/agent-handoff"
_V2_MANAGED = _SOURCE / "versions/1.1/provider-resources/managed"


def _source_files() -> tuple[Path, ...]:
    return tuple(sorted(path for path in _SOURCE.rglob("*") if path.is_file()))


def _v1_source_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _source_files()
        if path.relative_to(_SOURCE).parts[0] != "versions"
        and path.name not in {"adopt.md", "standard.toml"}
    )


def test_every_standard_source_file_has_byte_identical_bundle_mirror() -> None:
    source_relatives = {path.relative_to(_SOURCE) for path in _v1_source_files()}
    bundled_relatives = {
        path.relative_to(_BUNDLE)
        for path in _BUNDLE.rglob("*")
        if path.is_file() and path.name not in {"adopt.md", "adopt.toml", "standard.toml"}
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

    assert "--repository" not in adopt
    assert "--repo ." in adopt
    assert "Agent Handoff Standard" in root_readme
    assert "[agent-handoff/]" in standards_index
    assert "project-standards agent-handoff" in package_readme


def test_repository_dogfoods_agent_handoff_v5() -> None:
    config = tomllib.loads((_REPO / ".standards/config.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((_REPO / ".standards/lock.toml").read_text(encoding="utf-8"))
    claude = (_REPO / ".claude/settings.json").read_text(encoding="utf-8")
    codex = (_REPO / ".codex/config.toml").read_text(encoding="utf-8")
    prettier_ignores = set((_REPO / ".prettierignore").read_text(encoding="utf-8").splitlines())

    assert config["standards"]["agent-handoff"] == {
        "enabled": True,
        "version": "latest",
        "config": {
            "contract_version": "1.0",
            "startup": "automatic",
            "harnesses": ["claude-code", "codex"],
        },
    }
    assert lock["standards"]["agent-handoff"]["resolved"] == "1.1"
    assert not (_REPO / ".agents/agent-handoff/manifest.json").exists()
    assert (_REPO / ".agents/hooks/agent-handoff/session_start.py").read_bytes() == (
        _V2_MANAGED / "hook.py"
    ).read_bytes()
    assert (_REPO / ".agents/skills/agent-handoff/SKILL.md").read_bytes() == (
        _V2_MANAGED / "skill.md"
    ).read_bytes()
    assert (_REPO / ".standards/packages/agent-handoff/policy.toml").read_bytes() == (
        _V2_MANAGED / "policy.toml"
    ).read_bytes()
    assert ".agents/hooks/agent-handoff/session_start.py" in claude
    assert ".agents/hooks/agent-handoff/session_start.py" in codex
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

    hook = tmp_path / ".agents/hooks/agent-handoff/session_start.py"
    assert stat.S_IMODE(hook.stat().st_mode) == 0o755
    assert main(["agent-handoff", "validate", "--repo", str(tmp_path)]) == 0


def test_wheel_contains_complete_agent_handoff_bundle(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = tmp_path.glob("*.whl")
    names = set(zipfile.ZipFile(wheel).namelist())

    for source in _v1_source_files():
        relative = source.relative_to(_SOURCE).as_posix()
        expected = f"project_standards/bundles/agent-handoff/{relative}"
        assert any(name.endswith(expected) for name in names), expected
    assert any(
        name.endswith("project_standards/bundles/agent-handoff/adopt.toml") for name in names
    )


def test_installed_wheel_adopts_and_validates_without_source_checkout(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist)],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    (wheel,) = dist.glob("*.whl")
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
