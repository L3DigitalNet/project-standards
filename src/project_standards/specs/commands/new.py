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
