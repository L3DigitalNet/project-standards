"""Pure core for the guarded-generative `spec new` command.

Every function here is deterministic given its arguments — the date, the RNG, and
the existing-id set are injected by the cli.py shell, never read internally — so the
scaffold logic is unit-testable without a clock, RNG seed, or filesystem. The impure
file-writing shell lives in project_standards.specs.cli._run_new.
"""

from __future__ import annotations

import random
import re
from collections.abc import Container
from dataclasses import dataclass
from datetime import date

import yaml

# C0 (U+0000-U+001F) and C1 (U+007F-U+009F) control ranges. A newline or other control
# character in a flag value would corrupt the emitted frontmatter line, so reject early.
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class FieldValueError(ValueError):
    """A --title/--owner/--implementer value violates the accepted grammar (exit 2)."""


def check_field(flag: str, value: str, *, is_title: bool) -> None:
    if value == "":
        raise FieldValueError(f"--{flag} must not be empty")
    if _CONTROL.search(value):
        raise FieldValueError(f"--{flag} must not contain control characters")
    # Owner/implementer land only in YAML frontmatter (emit_scalar makes any char safe);
    # the title is ALSO substituted into the H1 Markdown code span (# `<title>` — ...),
    # where a backtick would break the span, so only --title excludes it.
    if is_title and "`" in value:
        raise FieldValueError("--title must not contain a backtick (it lands in the H1 code span)")


def emit_scalar(value: str) -> str:
    """Render a string as a single-quoted YAML scalar, matching the template style.

    Delegated to PyYAML rather than hand-quoted so apostrophes, colons, '#', backticks,
    and non-ASCII are escaped correctly. width is set very high to prevent line folding
    of long values inside a frontmatter line.
    """
    dumped = yaml.safe_dump(value, default_style="'", allow_unicode=True, width=1_000_000)
    return dumped.strip()


_ID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # base36, matching ^SPEC-[0-9A-Z]{4}$
_MINT_ATTEMPTS = 1000


class SpecIdExhausted(RuntimeError):
    """mint_spec_id could not find a free id within the attempt cap (advise --id)."""


def mint_spec_id(
    rng: random.Random, existing_ids: Container[str], *, attempts: int = _MINT_ATTEMPTS
) -> str:
    for _ in range(attempts):
        candidate = "SPEC-" + "".join(rng.choice(_ID_ALPHABET) for _ in range(4))
        if candidate not in existing_ids:
            return candidate
    raise SpecIdExhausted(
        f"could not mint a unique spec_id in {attempts} attempts; pass --id SPEC-XXXX"
    )


@dataclass(frozen=True)
class NewOptions:
    profile: str
    spec_id: str  # already resolved by the shell (minted or --id); never the sentinel
    title: str | None
    owner: str | None
    implementer: str | None


_FM_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
_H1 = re.compile(r"^(#\s+`)[^`]*(`)")


def _rewrite_frontmatter(text: str, replacements: dict[str, str]) -> str:
    """Replace whole frontmatter lines whose key is in `replacements`, inside the first
    `---`…`---` block only. Replacing the whole line drops any trailing inline comment
    (e.g. the spec_id placeholder note), which is intended."""
    out: list[str] = []
    seen_open = False
    in_fm = False
    for line in text.splitlines(keepends=True):
        if line.rstrip("\n") == "---":
            if not seen_open:
                seen_open, in_fm = True, True
            elif in_fm:
                in_fm = False
            out.append(line)
            continue
        if in_fm:
            m = _FM_KEY.match(line)
            if m and m.group(1) in replacements:
                nl = "\n" if line.endswith("\n") else ""
                out.append(replacements[m.group(1)] + nl)
                continue
        out.append(line)
    return "".join(out)


def _rewrite_h1(text: str, title: str) -> str:
    """Substitute the back-ticked name in the first `# \\`…\\` — Specification (T)` line.
    title is backtick-free by grammar (check_field), so the code span stays well-formed."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if _H1.match(line):
            lines[i] = _H1.sub(lambda m: m.group(1) + title + m.group(2), line, count=1)
            break
    return "".join(lines)


def scaffold(template_text: str, opts: NewOptions, *, today: date) -> str:
    iso = today.isoformat()
    replacements: dict[str, str] = {
        "spec_id": f"spec_id: {opts.spec_id}",
        "created": f"created: '{iso}'",
        "last_reviewed": f"last_reviewed: '{iso}'",
    }
    if opts.title is not None:
        replacements["title"] = f"title: {emit_scalar(opts.title)}"
    if opts.owner is not None:
        replacements["owner"] = f"owner: {emit_scalar(opts.owner)}"
    if opts.implementer is not None:
        replacements["implementer"] = f"implementer: {emit_scalar(opts.implementer)}"
    text = _rewrite_frontmatter(template_text, replacements)
    if opts.title is not None:
        text = _rewrite_h1(text, opts.title)
    return text
