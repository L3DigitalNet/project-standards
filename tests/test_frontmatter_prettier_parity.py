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


# The pre-5.8.0 doubled-apostrophe spelling: the formatter used to EMIT this, but
# Prettier (singleQuote: true, no-escape-when-possible) always rewrites it to
# `"Apple's thing"`. Deliberately NOT a fixed point — see the guard test below.
_NON_FIXED_POINT_DOC = (
    "---\n"
    "schema_version: '1.1'\n"
    "id: 'note-a3f9zk-x'\n"
    "title: 'X'\n"
    "description: 'Apple''s thing'\n"
    "doc_type: 'note'\n"
    "status: 'draft'\n"
    "created: '2026-06-08'\n"
    "updated: '2026-06-08'\n"
    "tags: []\n"
    "aliases: []\n"
    "related: []\n"
    "---\n"
    "\n"
    "# Body\n"
)


def test_prettier_harness_detects_non_fixed_point() -> None:
    """Committed mutation guard for `_run_prettier`'s `--ignore-path os.devnull` flag:
    this test is the committed mutation check for --ignore-path; if it fails with
    output==input, the harness is silently ignoring probe files again.

    `_NON_FIXED_POINT_DOC` is KNOWN not to be a fixed point: Prettier rewrites its
    doubled-apostrophe `'Apple''s thing'` to the no-escape `"Apple's thing"`. If a
    future cleanup drops `--ignore-path os.devnull`, Prettier starts treating the
    (gitignored `prettier_probe_*/`) probe directory as ignored and echoes stdin-mode
    output back byte-identical with no warning — every parity assertion in this file
    would then pass trivially. This test is the tripwire for exactly that regression:
    it fails (output == input) the moment `--ignore-path` stops doing its job."""
    _require_prettier()
    output = _run_prettier(_NON_FIXED_POINT_DOC)
    assert output != _NON_FIXED_POINT_DOC, (
        "pinned Prettier echoed the probe unchanged — the harness is silently "
        "ignoring probe files again (the --ignore-path os.devnull regression this "
        "test exists to catch)"
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
    """One FR-009 scalar class, a document carrying that class's mutual fixed point,
    and a `seed` variant used to make Direction B independently informative (T3 review
    finding #2). `cls` tags the case against `_REQUIRED_CLASSES` so TC-T3-002 can prove
    no class was silently dropped by a later edit.

    `seed` is a document identical to `doc` except the class-under-test scalar carries
    a spelling that is LEGAL YAML but NOT the formatter's canonical (minimal-escape)
    form — e.g. a double-quoted scalar where the canonical form is single-quoted.
    Direction B runs Prettier on `seed`, not `doc`: `doc` is already the formatter's
    fixed point (Direction A proves Prettier leaves it alone), so re-running Prettier
    on it and checking the formatter accepts the result again would just re-derive
    Direction A's equality. Feeding Prettier a genuinely different starting spelling
    and checking the formatter accepts Prettier's INDEPENDENTLY-CHOSEN resting spelling
    is the real cross-tool claim. `seed=None` marks a class with no non-canonical
    spelling expressible in the frontmatter grammar (currently only
    `literal_line_breaks`: a block scalar's only legal in-grammar form already is its
    canonical form), in which case Direction B falls back to reusing `doc`."""

    cls: str
    doc: str
    seed: str | None


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
    # seed: the pre-5.8.0 doubled-apostrophe single-quoted spelling (legal, non-minimal).
    CorpusCase(
        "apostrophes",
        _build({"title": '"Apple\'s"'}),
        seed=_build({"title": "'Apple''s'"}),
    ),
    # Interior double quotes → single-quoted wins (single-cost 0 < double-cost 2).
    # seed: the double-quoted spelling with both interior quotes escaped (legal, costlier).
    CorpusCase(
        "double_quotes",
        _build({"title": "'She said \"hi\"'"}),
        seed=_build({"title": '"She said \\"hi\\""'}),
    ),
    # Both quote kinds → single-quoted wins (single-cost 1 < double-cost 2); the
    # apostrophe is doubled inside single quotes.
    # seed: the double-quoted spelling with both interior quotes escaped (legal, costlier).
    CorpusCase(
        "both_quote_kinds",
        _build({"title": "'Apple''s \"pie\"'"}),
        seed=_build({"title": '"Apple\'s \\"pie\\""'}),
    ),
    # A single backslash is literal inside single quotes (no escaping) → single wins.
    # seed=None: Prettier is quote/escape-*preserving* for this value (module
    # docstring), not cost-minimizing — verified empirically that neither a
    # double-quoted-with-escaped-backslash spelling (`"a\\b"`) nor an unquoted plain
    # spelling (`a\b`) is touched by Prettier; it only forces re-emission for the
    # apostrophe-doubling trigger the `apostrophes`/`both_quote_kinds` classes exercise.
    # No legal spelling of this value converges to the canonical form under Prettier.
    CorpusCase(
        "single_backslash",
        _build({"title": r"'a\b'"}),
        seed=None,
    ),
    # Repeated backslashes stay literal inside single quotes → single wins; the
    # double-quoted form would have to escape each backslash.
    # seed=None: same empirically-verified Prettier preserving behavior as
    # `single_backslash` above — no legal alternate spelling converges.
    CorpusCase(
        "repeated_backslashes",
        _build({"title": r"'a\\b'"}),
        seed=None,
    ),
    # `\n` inside a double-quoted scalar: the newline is a control char, so the value
    # has no single-quoted spelling and must be double-quoted.
    # seed=None: verified empirically that Prettier preserves an alternate in-grammar
    # double-quoted escape spelling of the same control character verbatim (e.g. the
    # `\xNN` hex fallback instead of the `\n` mnemonic) rather than normalizing it to
    # _emit_scalar's mnemonic-preferring canonical form — Prettier does not touch
    # already-double-quoted internal escape spelling at all, only the outer quote
    # character. No legal alternate spelling converges.
    CorpusCase(
        "escaped_line_breaks",
        _build({"title": r'"line1\nline2"'}),
        seed=None,
    ),
    # Genuine multi-line text lives in a block scalar. Block scalars are OUT OF SCOPE
    # for the formatter (tokenize flags `|`/`>` as unsupported and leaves the document
    # byte-identical with an informational skip warning that does NOT fail the check
    # gate); this case verifies Prettier round-trips such a document so the formatter's
    # hands-off stance and Prettier's agree. This is the in-grammar realization of the
    # "literal line breaks" class (a raw newline cannot appear in a single-line scalar).
    # seed=None: a block scalar's only legal in-grammar spelling of this text already
    # IS its canonical form — there is no non-canonical alternative to seed with.
    CorpusCase(
        "literal_line_breaks",
        _build(description_block=["|", "  line one", "  line two"]),
        seed=None,
    ),
    # Tab is a control char → double-quoted `\t`.
    # seed=None: same empirically-verified Prettier preserving behavior as
    # `escaped_line_breaks` above — a `\xNN` hex-escape alternate spelling of the same
    # tab is left untouched by Prettier rather than normalized to the `\t` mnemonic.
    CorpusCase(
        "tabs",
        _build({"title": r'"a\tb"'}),
        seed=None,
    ),
    # Bell (U+0007) has no double-escape mnemonic → `\xNN` fallback, double-quoted.
    # seed=None: verified empirically that Prettier also preserves the `\a` mnemonic
    # spelling (legal per the YAML double-quoted escape table and accepted by PyYAML)
    # verbatim rather than normalizing it to _emit_scalar's `\xNN` fallback.
    CorpusCase(
        "control_characters",
        _build({"title": r'"a\x07b"'}),
        seed=None,
    ),
    # CJK text needs no escaping in either style → single wins on the tie.
    # seed: the double-quoted spelling of the same text (legal, non-canonical — the tie
    # resolves to single).
    CorpusCase(
        "cjk",
        _build({"title": "'你好世界'"}),
        seed=_build({"title": '"你好世界"'}),
    ),
    # A date string stays single-quoted; Prettier must NOT coerce it to a YAML date.
    # seed: the double-quoted spelling of the same date (legal, non-canonical); Prettier
    # must not coerce it to a YAML date from this spelling either.
    CorpusCase(
        "dates",
        _build({"title": "'2026-06-08'"}),
        seed=_build({"title": '"2026-06-08"'}),
    ),
    # An identifier-like number stays a quoted string; Prettier must NOT coerce it to a
    # YAML float (`1.1` is exactly the shape a YAML loader parses as a number, so this
    # case carries real risk — unlike an unambiguous string such as `v1.2.3`).
    # seed: the double-quoted spelling of the same string (legal, non-canonical);
    # Prettier must not coerce it to a number from this spelling either.
    CorpusCase(
        "identifier_like_numbers",
        _build({"title": "'1.1'"}),
        seed=_build({"title": '"1.1"'}),
    ),
    # Block-list items in BOTH accepted spellings on one list: the single-quoted
    # canonical `'plain'` and the minimal double-quoted `"Apple's"`. Neither must flip.
    # seed: both items in the OPPOSITE (legal, non-canonical) spelling — `"plain"`
    # (double-quoted; the tie resolves to single) and `'Apple''s'` (single-quoted with
    # the apostrophe doubled; double-quoted no-escape wins for this value).
    CorpusCase(
        "block_list_both_spellings",
        _build(related_block=["related:", "  - 'plain'", '  - "Apple\'s"']),
        seed=_build(related_block=["related:", '  - "plain"', "  - 'Apple''s'"]),
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

    # Direction B — Prettier's INDEPENDENTLY-PRODUCED resting spelling passes the
    # formatter check unchanged. Feeding Prettier `case.doc` here would just re-derive
    # Direction A's already-proven equality (doc is already the fixed point, so
    # Prettier would echo it back unchanged and this assertion would be trivial).
    # `case.seed` carries a legal-but-non-canonical spelling instead, so Prettier must
    # actually choose a resting spelling on its own; that choice — not a copy of
    # `doc` — is what the formatter is checked against. Classes with no expressible
    # non-canonical spelling (`seed is None`) fall back to `doc`. If the two tools
    # disagreed on this class's canonical spelling, the formatter would rewrite
    # Prettier's output here (a live fight), reddening this assertion.
    prettied = _run_prettier(case.seed if case.seed is not None else case.doc)
    _reformatted, changed_after_prettier, _ = format_text(prettied, path=None)
    assert not changed_after_prettier, (
        f"{case.cls}: formatter rewrote Prettier's independently-produced output — "
        "the two tools disagree on this class's canonical spelling"
    )
