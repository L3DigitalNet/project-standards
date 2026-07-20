from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
_REGISTRY = _REPO / "src" / "project_standards" / "schemas" / "registry.json"


def test_markdown_tooling_default_is_1_1_and_1_0_still_known() -> None:
    reg: dict[str, Any] = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    mt = reg["markdown_tooling"]
    assert mt["default"] == "1.1"
    assert set(mt["versions"]) == {"1.0", "1.1"}


def test_dogfood_config_selects_markdown_tooling_v1_5() -> None:
    config = tomllib.loads((_REPO / ".standards/config.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((_REPO / ".standards/lock.toml").read_text(encoding="utf-8"))

    assert config["standards"]["markdown-tooling"]["config"]["contract_version"] == "1.1"
    assert lock["standards"]["markdown-tooling"]["resolved"] == "1.5"
