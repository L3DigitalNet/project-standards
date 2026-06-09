# tests/test_precommit_hooks.py
import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_workflow_invokes_validate_references():
    wf = (REPO / ".github/workflows/validate-markdown-frontmatter.yml").read_text()
    assert "validate-references" in wf


def test_hook_entries_map_to_console_scripts():
    hooks = yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"]
    ids = {h["id"] for h in hooks}
    assert {
        "format-frontmatter-fix",
        "format-frontmatter-check",
        "validate-frontmatter",
        "validate-references",
    } <= ids
    for h in hooks:
        # entry's first token is the console-script name
        assert h["entry"].split()[0] in scripts
        assert h["language"] == "python"


def test_references_hook_runs_whole_repo():
    hooks = {h["id"]: h for h in yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())}
    assert hooks["validate-references"]["pass_filenames"] is False
