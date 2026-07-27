"""Split-ownership declaration: which tool owns each overlapping formatting
concern, and the exact config assertion that keeps markdownlint and Prettier
co-satisfiable. Formalizes the Prettier-alignment rationale already documented
inline in tests/test_markdownlint_config.py's CUSTOMIZATIONS dict, and adds the
Prettier-side assertions. See docs/specs/archive/2026-07-06-markdown-tooling-
formatter-authority-design.md Component C."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

Config = dict[str, Any]  # a parsed .markdownlint.json / .prettierrc.json
Profile = Literal["predecessor", "successor"]


@dataclass(frozen=True)
class Concern:
    name: str
    owner: str  # "markdownlint" | "prettier"
    check: Callable[[Config, Config], bool]  # (markdownlint_cfg, prettier_cfg) -> holds?
    why: str


def _predecessor_table_check(markdownlint: Config, _prettier: Config) -> bool:
    value = markdownlint.get("MD060")
    return isinstance(value, dict) and cast("dict[str, object]", value).get("style") == "any"


def _successor_table_check(markdownlint: Config, _prettier: Config) -> bool:
    return markdownlint.get("MD060") is False


def _split(profile: Profile) -> list[Concern]:
    table_check: Callable[[Config, Config], bool]
    table_why: str
    if profile == "predecessor":
        table_check = _predecessor_table_check
        table_why = (
            "Prettier realigns table pipes; predecessor MD060 style 'any' accepts that output."
        )
    else:
        table_check = _successor_table_check
        table_why = "Prettier owns table layout; successor markdownlint disables MD060."

    return [
        Concern(
            "line-wrapping",
            "prettier",
            lambda ml, pr: pr.get("proseWrap") == "never" and ml.get("MD013") is False,
            "Prettier owns wrapping (proseWrap:never); MD013 off so nothing fights it.",
        ),
        Concern(
            "table-alignment",
            "prettier",
            table_check,
            table_why,
        ),
        Concern(
            "emphasis-style",
            "markdownlint",
            lambda ml, pr: (
                ml.get("MD049") == {"style": "underscore"}
                and ml.get("MD050") == {"style": "asterisk"}
            ),
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


SPLIT: list[Concern] = _split("predecessor")
SUCCESSOR_SPLIT: list[Concern] = _split("successor")


def check_conformance(
    markdownlint: Config,
    prettier: Config,
    *,
    profile: Profile = "predecessor",
) -> list[str]:
    """Return one violation string per concern whose assertion does not hold."""
    concerns = SPLIT if profile == "predecessor" else SUCCESSOR_SPLIT
    return [
        f"[{c.name}] owned by {c.owner}: {c.why}"
        for c in concerns
        if not c.check(markdownlint, prettier)
    ]
