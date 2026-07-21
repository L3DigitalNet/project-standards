from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
PRETTIER_PIN = "3.8.3"
MARKDOWNLINT_CLI2_PIN = "0.23.1"  # Keep aligned with markdownlint-cli2-action@v24.


def test_package_json_pins_both_tools() -> None:
    pkg = json.loads((_REPO / "package.json").read_text(encoding="utf-8"))
    dev = pkg["devDependencies"]
    assert dev["prettier"] == PRETTIER_PIN
    assert dev["markdownlint-cli2"] == MARKDOWNLINT_CLI2_PIN


def test_lockfile_agrees_with_package_json() -> None:
    lock = json.loads((_REPO / "package-lock.json").read_text(encoding="utf-8"))
    root = lock["packages"][""]["devDependencies"]
    assert root["prettier"] == PRETTIER_PIN
    assert root["markdownlint-cli2"] == MARKDOWNLINT_CLI2_PIN
    assert lock["packages"]["node_modules/markdownlint-cli2"]["version"] == MARKDOWNLINT_CLI2_PIN
