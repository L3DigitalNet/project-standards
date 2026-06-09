# tests/test_precommit_hooks.py
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[1]


def test_workflow_invokes_validate_references():
    wf = (REPO / ".github/workflows/validate-markdown-frontmatter.yml").read_text()
    assert "validate-references" in wf
