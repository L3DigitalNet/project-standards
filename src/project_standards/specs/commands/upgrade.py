"""Pure splice core for the additive `spec upgrade` command.

Source-as-spine: the source's authored blocks are copied verbatim as raw text;
only missing canonical units and tier-owned filler come from the target-tier
template. All functions are deterministic in their arguments (no RNG, clock, or
I/O); the impure shell is project_standards.specs.cli._run_upgrade.
"""

from __future__ import annotations

import re

from project_standards.specs.commands.new import (
    _rewrite_frontmatter,  # pyright: ignore[reportPrivateUsage]
)

_TIER_WORD = {"light": "Light", "standard": "Standard", "full": "Full"}
# Line-anchored (^ + MULTILINE) with horizontal-only whitespace [ \t] so a substitution
# can only land on a real H1 heading line, never an H1-shaped example quoted inside a
# spliced source body (this module copies author source verbatim, and a spec-about-specs
# may contain such an example). count=1 in _rewrite_h1_suffix then takes the first such
# line, which is always the document's real H1.
_H1_SUFFIX = re.compile(
    r"^(#[ \t]+`[^`]*`[ \t]+—[ \t]+Specification[ \t]+\()(Light|Standard|Full)(\))",
    re.MULTILINE,
)


def _set_profile(text: str, tier: str) -> str:  # pyright: ignore[reportUnusedFunction]
    return _rewrite_frontmatter(text, {"profile": f"profile: {tier}"})


def _rewrite_h1_suffix(text: str, tier: str) -> str:  # pyright: ignore[reportUnusedFunction]
    word = _TIER_WORD[tier]
    return _H1_SUFFIX.sub(lambda m: m.group(1) + word + m.group(3), text, count=1)
