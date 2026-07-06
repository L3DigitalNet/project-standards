from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parent.parent
_REGISTRY = _REPO / "src" / "project_standards" / "schemas" / "registry.json"


def test_markdown_tooling_default_is_1_1_and_1_0_still_known() -> None:
    reg: dict[str, Any] = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    mt = reg["markdown_tooling"]
    assert mt["default"] == "1.1"
    assert set(mt["versions"]) == {"1.0", "1.1"}


def test_dogfood_config_selects_1_1() -> None:
    # CR-003: parse YAML and assert the *markdown_tooling* version specifically —
    # a substring check false-passes on the unrelated frontmatter `version: "1.1"`.
    cfg: dict[str, Any] = yaml.safe_load((_REPO / ".project-standards.yml").read_text("utf-8"))
    assert cfg["markdown_tooling"]["version"] == "1.1"
