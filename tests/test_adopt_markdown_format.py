from __future__ import annotations

import tomllib
from pathlib import Path

_BUNDLE = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "project_standards"
    / "bundles"
    / "markdown-tooling"
)


def test_adopt_toml_registers_format_caller() -> None:
    manifest = tomllib.loads((_BUNDLE / "adopt.toml").read_text(encoding="utf-8"))
    dests = {a["dest"]: a for a in manifest["artifact"]}
    art = dests[".github/workflows/format.yml"]
    assert art["kind"] == "workflow-caller"
    assert art["owner"] is True
    assert art["source"] == "format.caller.yml"


def test_format_caller_template_shape() -> None:
    text = (_BUNDLE / "format.caller.yml").read_text(encoding="utf-8")
    assert "workflows/format.yml@{{ref}}" in text
    assert "prettier:" not in text  # inherit the `true` default
