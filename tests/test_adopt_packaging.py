"""Wheel packaging smoke test: verify bundle artifacts land inside the built wheel.

Reads the session-scoped `built_wheel` fixture (tests/conftest.py) rather than
building its own: the property under test is what the released artifact contains,
not that a build succeeds.

Verifies that the `package_data` globs in pyproject.toml include bundles/, schemas/,
and registry.json so the adopt engine works identically from a source checkout and
from a `uv tool install`-ed wheel.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


def test_wheel_contains_bundles_and_manifests(built_wheel: Path) -> None:
    names = zipfile.ZipFile(built_wheel).namelist()
    must = [
        "project_standards/bundles/_shared/editorconfig",
        "project_standards/bundles/markdown-tooling/adopt.toml",
        "project_standards/bundles/markdown-tooling/format.caller.yml",
        "project_standards/bundles/python-tooling/check.yml",
        "project_standards/bundles/markdown-frontmatter/project-standards.starter.yml",
        "project_standards/bundles/markdown-frontmatter/skills/markdown-frontmatter/SKILL.md",
        "project_standards/bundles/markdown-frontmatter/skills/markdown-frontmatter/scripts/new-doc-id",
        "project_standards/bundles/markdown-frontmatter/skills/markdown-frontmatter/agents/openai.yaml",
        "project_standards/bundles/adr/adr.template.md",
        "project_standards/bundles/cli-documentation/adopt.toml",
        "project_standards/bundles/project-spec/adopt.toml",
        "project_standards/bundles/project-spec/project-standards.spec-fragment.yml",
        "project_standards/bundles/project-spec/validate-specs.caller.yml",
        "project_standards/bundles/agent-handoff/standard.toml",
        "project_standards/bundles/agent-handoff/adopt.toml",
        "project_standards/bundles/agent-handoff/hooks/session-start/session_start.py",
        "project_standards/bundles/agent-handoff/skills/agent-handoff/SKILL.md",
        "project_standards/bundles/agent-handoff/skills/agent-handoff/agents/openai.yaml",
        "project_standards/bundles/agent-handoff/resources/policy.toml",
        "project_standards/bundles/agent-handoff/resources/legacy-migration.md",
        "project_standards/bundles/agent-handoff/resources/integration/project-config.yml",
        "project_standards/bundles/agent-handoff/resources/integration/agent-instructions.md",
        "project_standards/bundles/agent-handoff/resources/integration/claude-session-start.json",
        "project_standards/bundles/agent-handoff/resources/integration/codex-session-start.toml",
        "project_standards/bundles/agent-handoff/runtime/provenance-lock.json",
    ]
    for entry in must:
        assert any(n.endswith(entry) for n in names), entry
