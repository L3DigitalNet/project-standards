"""Cross-tool parity: the frontmatter formatter and the pinned Prettier must agree
on scalar quoting (issue #26). Before FR-008 the formatter single-quoted every
scalar and doubled apostrophes (`'Apple''s'`), which Prettier — under this repo's
`.prettierrc.json` `**/*.md` `singleQuote: true` override — rewrites to the
no-escape spelling `"Apple's"`; the two tools then fight forever.

This runs the real pinned Prettier binary (3.8.3, from `package-lock.json` via
`npm ci`) over a corpus spanning the full FR-009 scalar space and asserts a MUTUAL
fixed point per class: formatter output is byte-stable under Prettier (direction A),
and Prettier output passes the formatter check unchanged (direction B). A missing
Node toolchain is a task failure, not a skip.

Corpus design — why each document is already the mutual fixed point, not an
arbitrary author spelling: Prettier is a quote-style-*preserving* YAML formatter.
It keeps `'a\\b'` single-quoted and `"a\\b"` double-quoted, keeps `'123'`/`'2026'`
quoted (never coercing to a number), and forces the no-escape spelling `"Apple's"`
only when it must re-emit. The formatter, symmetrically, ACCEPTS several spellings
(`_accepted_spelling`) but EMITS one minimal-escape form (`_emit_scalar`). The two
tools therefore share exactly one fixed point per class: the formatter's minimal
emission, which Prettier preserves. Seeding the corpus with a merely-accepted-but-
non-minimal spelling (e.g. `'Apple''s'`, which the formatter keeps but Prettier
rewrites to `"Apple's"`) would not be a fixed point and would mis-report a divergence
where none exists — so every corpus document carries its class's minimal form."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from project_standards.format_frontmatter import format_text

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PRETTIER = _REPO_ROOT / "node_modules" / ".bin" / "prettier"


def _require_prettier() -> None:
    """Hard-fail (never skip) when the pinned toolchain is absent: the cross-tool
    contract is unprovable without it, and a silent skip would let a real regression
    ship green. `npm ci` installs the pinned Prettier."""
    if not _PRETTIER.exists():
        pytest.fail(
            f"pinned Prettier binary not found at {_PRETTIER}; run `npm ci` "
            "(the Node toolchain is required for this gate, never skipped)"
        )


def _run_prettier(text: str) -> str:
    """Format `text` with the pinned Prettier and return its stdout.

    The probe file MUST live INSIDE the repo tree: Prettier resolves overrides by
    matching the `**/*.md` glob against the file path relative to the config's
    directory, so an out-of-tree temp path silently falls back to base
    `singleQuote: false` and rewrites every scalar (the config lie that motivated
    the in-tree mkdtemp).

    `--ignore-path os.devnull` is LOAD-BEARING, not hygiene: Prettier 3 honors
    `.gitignore` by default, and the repo's `.gitignore` lists `prettier_probe_*/`
    (so a crashed run leaves no tracked artifact). Without this flag Prettier would
    treat every probe file as ignored and, in stdout mode, echo it back UNCHANGED
    with no warning — silently vacating the whole oracle (every parity assertion
    would pass trivially because Prettier never actually reformats). Pointing
    `--ignore-path` at an empty file disables both default ignore files for this one
    explicit probe, while config resolution (the `**/*.md` override) is unaffected.

    `check=True` turns a Prettier parse error into a test error, not a skip — per the
    FR-009 rule that a Prettier failure on a legal document is itself a divergence to
    surface, never to hide."""
    probe_dir = Path(tempfile.mkdtemp(dir=_REPO_ROOT, prefix="prettier_probe_"))
    try:
        probe = probe_dir / "frontmatter.md"
        probe.write_text(text, encoding="utf-8")
        result = subprocess.run(
            [
                str(_PRETTIER),
                "--ignore-path",
                os.devnull,
                str(probe.relative_to(_REPO_ROOT)),
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return result.stdout


# A document whose only non-canonical concern is an apostrophe-bearing scalar. The
# formatter must emit it in the quote style Prettier already prefers. Retained as the
# original issue #26 regression (TC-T1-008); the corpus below generalizes it.
_APOSTROPHE_DOC = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'note-a3f9zk-x'\n"
    'title: "Apple\'s"\n'
    "description: 'A doc.'\n"
    "doc_type: 'note'\n"
    "status: 'draft'\n"
    "created: '2026-06-08'\n"
    "updated: '2026-06-08'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n"
    "\n"  # Prettier keeps one blank line after the frontmatter fence; pre-canonical
    "# Body\n"  # body isolates the scalar-quoting parity as the only variable under test
)


def test_formatter_output_stable_under_pinned_prettier() -> None:
    """TC-T1-008: the original issue #26 fixed point — formatter output for an
    apostrophe scalar is byte-identical under the pinned Prettier."""
    _require_prettier()
    formatted, _changed, _warnings = format_text(_APOSTROPHE_DOC, path=None)
    assert _run_prettier(formatted) == formatted, (
        "pinned Prettier rewrote the formatter output — the issue #26 quoting fight "
        "is live; the emitter must produce Prettier's minimal-escape spelling"
    )


# The eight scalar keys the formatter always canonicalizes, in canonical order, with
# their default already-minimal spellings. Corpus builders override one at a time so
# the class under test is the only variable Prettier or the formatter could touch.
_BASE_SCALARS: dict[str, str] = {
    "schema_version": "'1.1'",
    "id": "'note-a3f9zk-x'",
    "title": "'X'",
    "description": "'A doc.'",
    "doc_type": "'note'",
    "status": "'draft'",
    "created": "'2026-06-08'",
    "updated": "'2026-06-08'",
}
_SCALAR_ORDER = tuple(_BASE_SCALARS)


def _build(
    scalars: dict[str, str] | None = None,
    *,
    description_block: list[str] | None = None,
    related_block: list[str] | None = None,
) -> str:
    """Assemble a structurally-canonical frontmatter document (correct key order, all
    required arrays present) so the formatter's reorder/inject/list passes are all
    no-ops and ONLY the class-under-test scalar can move. `description_block` swaps the
    `description` value for a multi-line YAML block scalar; `related_block` swaps the
    `related: []` array for an explicit block list."""
    values = dict(_BASE_SCALARS)
    if scalars:
        values.update(scalars)
    lines = ["---"]
    for key in _SCALAR_ORDER:
        if key == "description" and description_block is not None:
            lines.append(f"description: {description_block[0]}")
            lines.extend(description_block[1:])
        else:
            lines.append(f"{key}: {values[key]}")
    lines.append("tags: []")
    lines.append("aliases: []")
    lines.extend(related_block if related_block is not None else ["related: []"])
    lines += ["---", "", "# Body"]
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class CorpusCase:
    """One FR-009 scalar class and a document carrying that class's mutual fixed point.
    `cls` tags the case against `_REQUIRED_CLASSES` so TC-T3-002 can prove no class was
    silently dropped by a later edit."""

    cls: str
    doc: str


# Every scalar class FR-009 enumerates. TC-T3-002 asserts the corpus tags exactly this
# set — a required-class registry so a future edit cannot silently drop coverage.
_REQUIRED_CLASSES: frozenset[str] = frozenset(
    {
        "apostrophes",
        "double_quotes",
        "both_quote_kinds",
        "single_backslash",
        "repeated_backslashes",
        "escaped_line_breaks",
        "literal_line_breaks",
        "tabs",
        "control_characters",
        "cjk",
        "dates",
        "identifier_like_numbers",
        "block_list_both_spellings",
    }
)


# Each doc carries the class's minimal-escape (formatter-emitted, Prettier-preserved)
# spelling. The escaped-break/tab/control docs hold LITERAL backslash sequences inside
# a double-quoted scalar (`\n`, `\t`, `\x07`) — the frontmatter grammar has no way to
# hold a raw newline inside a single-line scalar, so this is the only in-grammar form
# of those characters; the block-scalar doc covers genuine multi-line text.
_CORPUS: tuple[CorpusCase, ...] = (
    # Apostrophe → double-quoted no-escape form wins (single-cost 1 > double-cost 0).
    CorpusCase("apostrophes", _build({"title": '"Apple\'s"'})),
    # Interior double quotes → single-quoted wins (single-cost 0 < double-cost 2).
    CorpusCase("double_quotes", _build({"title": "'She said \"hi\"'"})),
    # Both quote kinds → single-quoted wins (single-cost 1 < double-cost 2); the
    # apostrophe is doubled inside single quotes.
    CorpusCase("both_quote_kinds", _build({"title": "'Apple''s \"pie\"'"})),
    # A single backslash is literal inside single quotes (no escaping) → single wins.
    CorpusCase("single_backslash", _build({"title": r"'a\b'"})),
    # Repeated backslashes stay literal inside single quotes → single wins; the
    # double-quoted form would have to escape each backslash.
    CorpusCase("repeated_backslashes", _build({"title": r"'a\\b'"})),
    # `\n` inside a double-quoted scalar: the newline is a control char, so the value
    # has no single-quoted spelling and must be double-quoted.
    CorpusCase("escaped_line_breaks", _build({"title": r'"line1\nline2"'})),
    # Genuine multi-line text lives in a block scalar. Block scalars are OUT OF SCOPE
    # for the formatter (tokenize flags `|`/`>` as unsupported and leaves the document
    # byte-identical with an informational skip warning that does NOT fail the check
    # gate); this case verifies Prettier round-trips such a document so the formatter's
    # hands-off stance and Prettier's agree. This is the in-grammar realization of the
    # "literal line breaks" class (a raw newline cannot appear in a single-line scalar).
    CorpusCase(
        "literal_line_breaks",
        _build(description_block=["|", "  line one", "  line two"]),
    ),
    # Tab is a control char → double-quoted `\t`.
    CorpusCase("tabs", _build({"title": r'"a\tb"'})),
    # Bell (U+0007) has no double-escape mnemonic → `\xNN` fallback, double-quoted.
    CorpusCase("control_characters", _build({"title": r'"a\x07b"'})),
    # CJK text needs no escaping in either style → single wins on the tie.
    CorpusCase("cjk", _build({"title": "'你好世界'"})),
    # A date string stays single-quoted; Prettier must NOT coerce it to a YAML date.
    CorpusCase("dates", _build({"title": "'2026-06-08'"})),
    # An identifier-like number stays a quoted string; Prettier must NOT coerce it to
    # a YAML int/float (`'v1.2.3'` is unambiguous; `'1.1'`/`'123'` verified separately).
    CorpusCase("identifier_like_numbers", _build({"title": "'v1.2.3'"})),
    # Block-list items in BOTH accepted spellings on one list: the single-quoted
    # canonical `'plain'` and the minimal double-quoted `"Apple's"`. Neither must flip.
    CorpusCase(
        "block_list_both_spellings",
        _build(related_block=["related:", "  - 'plain'", '  - "Apple\'s"']),
    ),
)


def test_corpus_covers_required_classes() -> None:
    """TC-T3-002: the corpus tags exactly the required FR-009 class registry, so a
    future edit cannot silently drop a class (or add an untracked one)."""
    covered = {case.cls for case in _CORPUS}
    assert covered == _REQUIRED_CLASSES, (
        "corpus class coverage drifted from the required FR-009 registry: "
        f"missing={sorted(_REQUIRED_CLASSES - covered)}, "
        f"unexpected={sorted(covered - _REQUIRED_CLASSES)}"
    )


@pytest.mark.parametrize("case", _CORPUS, ids=lambda c: c.cls)
def test_corpus_class_is_prettier_fixed_point(case: CorpusCase) -> None:
    """TC-T3-001: for every FR-009 scalar class, the formatter and the pinned Prettier
    share a byte-exact fixed point, proven in both directions."""
    _require_prettier()

    # Direction A — formatter output is byte-stable under Prettier. The corpus document
    # is already the formatter's fixed point, so `format_text` must report no change
    # (a change means the document was mis-authored, not that parity failed) and
    # Prettier must leave that output untouched.
    formatted, changed, warnings = format_text(case.doc, path=None)
    assert not changed, (
        f"{case.cls}: corpus document is not the formatter's fixed point "
        f"(format_text rewrote it) — fix the corpus spelling. warnings={warnings}"
    )
    assert _run_prettier(formatted) == formatted, (
        f"{case.cls}: pinned Prettier rewrote formatter output — the issue #26 "
        "quoting fight is live for this class; _emit_scalar must match Prettier"
    )

    # Direction B — Prettier output passes the formatter check unchanged. If the two
    # tools disagreed on this class's canonical spelling, the formatter would rewrite
    # Prettier's output here (a live fight), reddening this assertion.
    prettied = _run_prettier(case.doc)
    _reformatted, changed_after_prettier, _ = format_text(prettied, path=None)
    assert not changed_after_prettier, (
        f"{case.cls}: formatter rewrote Prettier output — the two tools disagree on "
        "this class's canonical spelling"
    )
