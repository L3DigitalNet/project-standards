"""Guard rails for the published ``.markdownlint.json``.

The config states every markdownlint rule explicitly (not just the customised
ones) so that a consumer who seeds their config from ours gets deterministic
linting regardless of their own editor/global markdownlint settings. These tests
pin the human-fragile invariants of that explicit config — so an accidental
hand-edit, a lost customisation, or a regression of the MD043 sentinel trap fails
CI instead of silently changing what the linter enforces.

Deliberately hermetic: no Node, no subprocess, no schema fixture (per the testing
strategy in tests/README.md). These guard *intent*; the behavioural check (the
config lints the repo cleanly) is the ``lint-markdown.yml`` CI workflow's job.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = _REPO_ROOT / ".markdownlint.json"

# The 13 deliberate deviations from markdownlint's defaults. Every other rule is
# stated at its v0.40.0 default for determinism; these are the values that carry
# intent and must not silently change. Sources: standards/markdown-tooling/README.md (§7) + the CHANGELOG.
CUSTOMIZATIONS: dict[str, Any] = {
    "MD003": {"style": "atx"},  # align headings to Prettier (ATX)
    "MD004": {"style": "dash"},  # align bullets to Prettier (-)
    "MD009": False,  # Prettier owns trailing whitespace
    "MD010": False,  # Prettier owns hard tabs
    "MD013": False,  # Prettier owns line length
    "MD024": False,  # match MADR 4.0 (allow duplicate option headings)
    "MD025": {"front_matter_title": "", "level": 1},  # frontmatter title not an H1
    "MD029": False,  # ordered-list prefix style not enforced
    "MD030": False,  # Prettier owns list-marker spacing
    "MD032": False,  # Prettier owns blanks around lists
    "MD048": {"style": "backtick"},  # align fences to Prettier (```)
    "MD049": {"style": "underscore"},  # align emphasis to Prettier (_italic_)
    "MD050": {"style": "asterisk"},  # align strong to Prettier (**bold**)
}


@pytest.fixture(scope="module")
def config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_config_is_a_nonempty_json_object(config: dict[str, Any]) -> None:
    assert isinstance(config, dict) and config


def test_default_baseline_is_true(config: dict[str, Any]) -> None:
    # Explicit baseline so any rule NOT stated (e.g. a rule added by a future
    # markdownlint version) is enabled at its default rather than silently off.
    assert config.get("default") is True


def test_md043_stays_inert(config: dict[str, Any]) -> None:
    # MD043's schema default `headings: []` is a SENTINEL: stated explicitly it means
    # "require exactly zero headings" and flags every heading in every file. `true`
    # is the correct inert form (verified at runtime). This guards that regression.
    assert config.get("MD043") is True


def test_no_rule_carries_the_md043_sentinel(config: dict[str, Any]) -> None:
    # Defensive: an empty required-headings list must never appear on any rule.
    for rule, value in config.items():
        if isinstance(value, dict):
            params = cast("dict[str, Any]", value)
            assert params.get("headings") != [], f"{rule} carries the MD043 sentinel"


@pytest.mark.parametrize("rule,value", sorted(CUSTOMIZATIONS.items()))
def test_customization_present_and_correct(config: dict[str, Any], rule: str, value: Any) -> None:
    assert config.get(rule) == value


def test_config_is_fully_explicit_not_sparse(config: dict[str, Any]) -> None:
    # The whole point of this config is that it's explicit. Guard against an
    # accidental revert to the old 13-override sparse form: v0.40.0 has 53 rules.
    rules = [k for k in config if k.startswith("MD")]
    assert len(rules) == 53, f"expected the full rule set explicitly, found {len(rules)}"
