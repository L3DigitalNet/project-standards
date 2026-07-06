from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.coherence.declaration import SPLIT, check_conformance
from tests.test_markdownlint_config import CUSTOMIZATIONS

_REPO = Path(__file__).resolve().parent.parent.parent


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_REPO / name).read_text(encoding="utf-8"))
    return data


def test_shipped_configs_conform() -> None:
    assert check_conformance(_load(".markdownlint.json"), _load(".prettierrc.json")) == []


def test_tampered_md013_is_caught() -> None:
    ml = _load(".markdownlint.json") | {"MD013": {"line_length": 80}}
    assert any("MD013" in v for v in check_conformance(ml, _load(".prettierrc.json")))


def test_tampered_prosewrap_is_caught() -> None:
    pr = _load(".prettierrc.json") | {"proseWrap": "always"}
    assert any("proseWrap" in v for v in check_conformance(_load(".markdownlint.json"), pr))


def test_declaration_agrees_with_existing_customizations() -> None:
    # Non-vacuous drift guard (CR-NEW-003): filter by Concern.owner STRUCTURALLY,
    # not by rendered strings (every violation string contains "Prettier", so a
    # string filter would always be empty). Each markdownlint-owned concern must
    # hold against the CUSTOMIZATIONS dict — if a customization drifts (e.g. MD048
    # changes), that concern's check fails and this test catches it.
    ml = dict(CUSTOMIZATIONS)
    pr = {"proseWrap": "never"}
    failing = [c.name for c in SPLIT if c.owner == "markdownlint" and not c.check(ml, pr)]
    assert failing == [], failing
