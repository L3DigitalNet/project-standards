"""Split-ownership declaration: which tool owns each overlapping formatting
concern, and the exact config assertion that keeps markdownlint and Prettier
co-satisfiable. Formalizes the Prettier-alignment rationale already documented
inline in tests/test_markdownlint_config.py's CUSTOMIZATIONS dict, and adds the
Prettier-side assertions. See docs/superpowers/specs/2026-07-06-markdown-tooling-
formatter-authority-design.md Component C."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Config = dict[str, Any]  # a parsed .markdownlint.json / .prettierrc.json


@dataclass(frozen=True)
class Concern:
    name: str
    owner: str  # "markdownlint" | "prettier"
    check: Callable[[Config, Config], bool]  # (markdownlint_cfg, prettier_cfg) -> holds?
    why: str


SPLIT: list[Concern] = [
    Concern(
        "line-wrapping",
        "prettier",
        lambda ml, pr: pr.get("proseWrap") == "never" and ml.get("MD013") is False,
        "Prettier owns wrapping (proseWrap:never); MD013 off so nothing fights it.",
    ),
    Concern(
        "table-alignment",
        "prettier",
        lambda ml, pr: isinstance(ml.get("MD060"), dict) and ml["MD060"].get("style") == "any",
        "Prettier realigns table pipes; MD060 style 'any' accepts that output.",
    ),
    Concern(
        "emphasis-style",
        "markdownlint",
        lambda ml, pr: ml.get("MD049") == {"style": "underscore"}
        and ml.get("MD050") == {"style": "asterisk"},
        "markdownlint pins _italic_/**bold**; Prettier's defaults agree.",
    ),
    Concern(
        "code-fence-style",
        "markdownlint",
        lambda ml, pr: ml.get("MD048") == {"style": "backtick"},
        "markdownlint pins ``` fences; Prettier emits backtick fences.",
    ),
    Concern(
        "heading-style",
        "markdownlint",
        lambda ml, pr: ml.get("MD003") == {"style": "atx"},
        "markdownlint pins ATX (#) headings; Prettier emits ATX.",
    ),
]


def check_conformance(markdownlint: Config, prettier: Config) -> list[str]:
    """Return one violation string per concern whose assertion does not hold."""
    return [
        f"[{c.name}] owned by {c.owner}: {c.why}"
        for c in SPLIT
        if not c.check(markdownlint, prettier)
    ]
