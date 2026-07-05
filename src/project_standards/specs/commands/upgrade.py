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
from project_standards.specs.registry import gh_slug, split_front_matter

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


# Captures the leading numeral of a heading, dotted-decimal-aware: "7. Requirements" (top
# level, trailing "." is punctuation) -> "7", and "17.1 Definition of Done" (subsection,
# no trailing punctuation before the space) -> "17.1". A naive `(\d+)\.` captures only the
# digits before the FIRST dot, which collapses every subsection of a section (17.1, 17.2,
# 17.3) to the same key as the section itself ("17") — silently merging them in _sub_blocks.
# The trailing `\.?` is optional so it eats the top-level's punctuation dot without also
# being required for the subsection form, which has no such dot before the space.
_NUM = re.compile(r"^(\d+(?:\.\d+)*)\.?(?=[ \t])")
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


# Appendices A, B, and D are all tier-variant canonical boilerplate — taken from
# the target tier, never the source. (Appendix C is Full-only, so it arrives as a
# missing unit, not a template-owned replacement.) The upgradeability precheck
# (Task 8) guarantees the source's A/B/D are canonical, so nothing author-written
# is lost by replacing them.
_TEMPLATE_OWNED = {"appendix-A", "appendix-B", "appendix-D"}

# §17.1 (Definition of Done) is tier-variant canonical boilerplate — identical across
# standard/full but simpler at light (its DoD can't reference §17.3/§18.7/§13.6, absent at
# light). Like Appendix A/B/D it is taken from the TARGET, never the source. The precheck
# (Task 8) guarantees the source's §17.1 is canonical, so replacing it loses no author bytes.
_TEMPLATE_OWNED_SUBS = {"17.1"}


def _merge_top(source_body: str, target_body: str) -> str:  # pyright: ignore[reportUnusedFunction]
    source_map = dict(_top_blocks(source_body))
    out: list[str] = []
    for key, target_text in _top_blocks(target_body):
        if key == "":
            # Preamble from source; fall back to the target's if the source has none
            # (pure-function safety — no caller precondition guarantees a source preamble).
            out.append(source_map.get("", target_text))
        elif key in source_map and key not in _TEMPLATE_OWNED:
            out.append(_reconcile_shared(source_map[key], target_text))
        else:
            out.append(target_text)  # missing unit, tier-owned appendix, or target preamble
    return "".join(out)


def _sub_blocks(block: str) -> list[tuple[str, str]]:
    starts = _heading_starts(block, "### ")  # fence-aware (Task 3)
    out: list[tuple[str, str]] = []
    intro_end = starts[0][0] if starts else len(block)
    out.append(("", block[:intro_end]))  # heading + pre-first-subsection intro filler
    for i, (pos, heading) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(block)
        out.append((_block_key(heading), block[pos:end]))
    return out


def _reconcile_shared(source_block: str, target_block: str) -> str:
    """Reconcile a shared top-level block: keep the source's authored subsections
    verbatim, insert any subsection the target has but the source lacks, and always
    take the pre-first-subsection intro and (via ``_swap_tail``) the trailing filler
    from the target — dropping stale omission/reduction notes in favor of the
    target's canonical ones. §17.1 is template-owned (see ``_TEMPLATE_OWNED_SUBS``)
    and is always taken from the target even when the source has it.
    """
    src_subs = dict(_sub_blocks(source_block))
    tgt_subs = _sub_blocks(target_block)
    if len(tgt_subs) == 1:
        # No subsection structure: keep the author body, take only the trailing filler
        # (dividers / now-stale omission notes) from the target block.
        return _swap_tail(source_block, target_block)
    out: list[str] = []
    for key, tgt_text in tgt_subs:
        if key == "":
            out.append(tgt_text)  # target heading + intro (drops stale reduction note)
        elif key in src_subs and key not in _TEMPLATE_OWNED_SUBS:
            # Author subsection BODY kept verbatim, but its trailing filler (dividers /
            # stale whole-section omission notes that ride on the last source subsection's
            # slice) is reconciled from the target — else a stale "§N omitted" note survives
            # next to a now-present section (task-5 review). This trims only lines _is_filler
            # matches (blank / "---" / a "> …tier…omitted" note). It is NOT a structural
            # invariant that a kept subsection's tail is inert: the reshape-identity precheck
            # (check_upgradeable, Task 8) refuses any source whose kept-subsection trailing
            # filler is non-canonical, so an author's own trailing divider or tier/omitted
            # blockquote yields a clean source_not_upgradeable refusal, not silent loss here.
            out.append(_swap_tail(src_subs[key], tgt_text))
        else:
            out.append(tgt_text)  # inserted subsection OR tier-variant boilerplate (e.g. §17.1)
    return "".join(out)


def _swap_tail(source_block: str, target_block: str) -> str:
    """Return the source block with its trailing filler replaced by the target's.

    Trailing filler = the maximal suffix of blank / `---` / omission-note (`> … tier …
    omitted`) lines. This is where stale whole-section omission notes live.
    """

    def split(block: str) -> tuple[str, str]:
        lines = block.splitlines(keepends=True)
        i = len(lines)
        while i > 0 and _is_filler(lines[i - 1]):
            i -= 1
        return "".join(lines[:i]), "".join(lines[i:])

    src_body, _src_tail = split(source_block)
    _tgt_body, tgt_tail = split(target_block)
    return src_body + tgt_tail


def _is_filler(line: str) -> bool:
    s = line.strip()
    if s in ("", "---"):
        return True
    return s.startswith(">") and "tier" in s and "omitted" in s


def upgrade_text(source_text: str, target_template_text: str, *, target_tier: str) -> str:
    """Splice ``source_text`` up to ``target_tier`` using ``target_template_text`` as the
    donor for missing sections and tier-owned boilerplate. Source-as-spine: the source's
    frontmatter and authored blocks are the base; the target template only fills gaps.

    Precondition: ``source_text`` is a frontmatter-bearing spec that has passed the
    upgradeability precheck (``check_upgradeable``) — its scaffolding, including each kept
    subsection's trailing filler, is canonical for its tier. The impure shell
    ``cli._run_upgrade`` enforces this (and self-validates the output) before/after calling;
    calling directly on a non-canonical source can drop trailing filler (see
    ``_reconcile_shared``) or, for frontmatter-less input, emit a spurious empty fence.
    """
    src_fm, src_body = split_front_matter(source_text)
    _tgt_fm, tgt_body = split_front_matter(target_template_text)
    merged_body = _merge_top(src_body, tgt_body)
    text = f"---\n{src_fm}\n---\n{merged_body}"  # source frontmatter preserved verbatim
    text = _set_profile(text, target_tier)
    return _rewrite_h1_suffix(text, target_tier)
