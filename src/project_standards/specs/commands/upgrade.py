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
from project_standards.specs.registry import gh_slug

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


_NUM = re.compile(r"^(\d+)\.")
_APX = re.compile(r"^Appendix ([A-Z]):")
# CommonMark fenced-code delimiters, mirroring validate_frontmatter._CODE_FENCE_RE /
# _CODE_FENCE_CLOSE_RE exactly (DRY across the package): a fence OPENS with up to 3 leading
# spaces + a run of >=3 of one char (`` ` `` or ``~``), optionally followed by an info string;
# it CLOSES only on the SAME marker char, length >= the opener, up to 3 spaces, and NOTHING
# but spaces/tabs after — so `` ```aaa `` inside a `` ``` `` fence is content, not a closer,
# and a 4-space-indented `` ``` `` is indented code, not a fence.
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def _block_key(heading_text: str) -> str:
    if m := _NUM.match(heading_text):
        return m.group(1)
    if m := _APX.match(heading_text):
        return f"appendix-{m.group(1)}"
    return gh_slug(heading_text)


def _heading_starts(text: str, prefix: str) -> list[tuple[int, str]]:
    """(byte offset, heading text) for each line starting with `prefix` (e.g. ``"## "``),
    skipping lines inside fenced code so example headings in a spec's own code samples are
    never mistaken for section boundaries (Codex CR-003). Fence tracking mirrors
    validate_frontmatter's ``missing_adr_sections`` loop. ``"## "`` does not match ``"### "``
    (third char differs), so each level is isolated."""
    out: list[tuple[int, str]] = []
    fence: str | None = None  # the opening run (e.g. "```" or "~~~~"), or None outside a fence
    off = 0
    for line in text.splitlines(keepends=True):
        if fence is not None:
            close = _FENCE_CLOSE.match(line)
            if close and close.group(1)[0] == fence[0] and len(close.group(1)) >= len(fence):
                fence = None
        elif opener := _FENCE_OPEN.match(line):
            fence = opener.group(1)
        elif line.startswith(prefix):
            out.append((off, line[len(prefix) :].rstrip("\n")))
        off += len(line)
    return out


def _top_blocks(body: str) -> list[tuple[str, str]]:  # pyright: ignore[reportUnusedFunction]
    starts = _heading_starts(body, "## ")
    out: list[tuple[str, str]] = []
    if not starts or starts[0][0] > 0:
        out.append(("", body[: starts[0][0] if starts else len(body)]))
    for i, (pos, heading) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        out.append((_block_key(heading), body[pos:end]))
    return out


def _present_top_keys(body: str) -> list[str]:  # pyright: ignore[reportUnusedFunction]
    return [k for k, _ in _top_blocks(body) if k and not k.startswith("appendix-")]
