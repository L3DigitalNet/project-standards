from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.agent_handoff.policy import (
    HandoffPolicy,
    PolicyError,
    check_document,
    check_secret_references,
    load_policy,
    measure_file,
)

POLICY_PATH = (
    Path(__file__).parents[2] / "src/project_standards/bundles/agent-handoff/resources/policy.toml"
)
MUTABLE_POLICY_PATH = Path(__file__).parents[2] / "standards/agent-handoff/resources/policy.toml"


@pytest.fixture(scope="module")
def policy() -> HandoffPolicy:
    return load_policy(POLICY_PATH)


def test_policy_contract_omits_unenforced_shape_options(policy: HandoffPolicy) -> None:
    definitions = type(policy).model_json_schema()["$defs"]

    assert {
        "max_heading_depth",
        "prefer_bullets",
        "require_overflow_pointer",
    }.isdisjoint(definitions["ShapeDefaults"]["properties"])
    assert {
        "require_pointer_for_details_over_chars",
        "append_only",
    }.isdisjoint(definitions["DocumentPolicy"]["properties"])


def test_mutable_policy_resource_matches_bundle() -> None:
    assert MUTABLE_POLICY_PATH.read_bytes() == POLICY_PATH.read_bytes()


def test_bug_profile_targets_numbered_records_only(policy: HandoffPolicy) -> None:
    documents = policy.shape.documents

    assert "docs/handoff/bugs/[0-9][0-9][0-9]-*.md" in documents
    assert "docs/handoff/bugs/*.md" not in documents


def test_size_uses_utf8_bytes(tmp_path: Path) -> None:
    path = tmp_path / "docs/handoff/state.md"
    path.parent.mkdir(parents=True)
    path.write_text("é" * 1025, encoding="utf-8")

    result = measure_file(path, cap=2048, target=1740)

    assert result.bytes == 2050
    assert result.status == "over-cap"
    assert result.over_by == 2


@pytest.mark.parametrize(
    ("size", "expected"),
    [(1740, "ok"), (1741, "over-target"), (2048, "over-target"), (2049, "over-cap")],
)
def test_size_status_boundaries(tmp_path: Path, size: int, expected: str) -> None:
    path = tmp_path / "file.md"
    path.write_bytes(b"x" * size)

    assert measure_file(path, cap=2048, target=1740).status == expected


def _state(extra: str = "") -> str:
    return (
        "**Last updated:** 2026-07-09\n\n"
        "## Current focus\n\n- Implementing policy.\n"
        f"{extra}"
        "\n## Active incidents\n\n- None.\n"
    )


def test_good_state_shape_passes(policy: HandoffPolicy) -> None:
    assert check_document("docs/handoff/state.md", _state(), policy) == ()


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ("\n## History\n\n- old\n", "invalid section"),
        ("- two\n- three\n- four\n- five\n", "max 4"),
        ("\nThis paragraph is not eager state.\n", "paragraph"),
        ("- In order to keep testing.\n", "blocked phrase"),
        (f"- {'x' * 150}\n", "max 140"),
    ],
)
def test_state_shape_rules_are_fatal(policy: HandoffPolicy, extra: str, message: str) -> None:
    findings = check_document("docs/handoff/state.md", _state(extra), policy)

    assert any(message in finding.message for finding in findings)
    assert all(finding.severity == "error" for finding in findings)


def test_overlong_bullet_reports_safe_line_measure_and_limit(policy: HandoffPolicy) -> None:
    secret = "sk-live-consumer-secret"
    bullet = f"- {secret}{'x' * 150}"
    text = _state(f"{bullet}\n")
    expected_line = text.splitlines().index(bullet) + 1

    finding = next(
        item
        for item in check_document("docs/handoff/state.md", text, policy)
        if item.limit == 140 and item.observed == len(bullet)
    )

    assert finding.line == expected_line
    assert finding.column == 1
    assert "bullet" in finding.locus.casefold()
    assert secret not in finding.message
    assert secret not in str(finding.to_dict())


def test_status_shape_is_advisory(policy: HandoffPolicy) -> None:
    text = "# Status\n\n## History\n\n" + ("narrative\n" * 70)

    findings = check_document("docs/STATUS.md", text, policy)

    assert findings
    assert all(finding.severity == "warning" for finding in findings)
    assert any("required section" in finding.message for finding in findings)


def test_todo_required_order_is_fatal(policy: HandoffPolicy) -> None:
    text = "# TODO\n\n## Agent tasks\n\n- [ ] Agent task.\n\n## User tasks\n\n- [ ] User task.\n"

    findings = check_document("docs/TODO.md", text, policy)

    assert any("required order" in finding.message for finding in findings)
    assert all(finding.severity == "error" for finding in findings)


# `docs/handoff/deployed.md` declares no `max_paragraph_chars`, so it exercises
# the `shape.defaults` fallback; `docs/handoff/architecture.md` declares 420 and
# exercises the explicit entry. Both are advisory profiles.
_OVER_BOTH_LIMITS = "# Heading\n\n" + ("x" * 430) + "\n"


def test_defaults_sourced_paragraph_limit_enriches_like_an_explicit_limit(
    policy: HandoffPolicy,
) -> None:
    defaulted = next(
        finding
        for finding in check_document("docs/handoff/deployed.md", _OVER_BOTH_LIMITS, policy)
        if finding.locus == "document paragraph"
    )
    explicit = next(
        finding
        for finding in check_document("docs/handoff/architecture.md", _OVER_BOTH_LIMITS, policy)
        if finding.locus == "document paragraph"
    )

    assert defaulted.message == "paragraph exceeds its configured character limit; max 360"
    assert defaulted.limit == 360
    assert explicit.limit == 420
    assert (defaulted.line, defaulted.column, defaulted.observed) == (3, 1, 430)
    assert (defaulted.line, defaulted.column, defaulted.observed) == (
        explicit.line,
        explicit.column,
        explicit.observed,
    )


def test_explicit_paragraph_limit_overrides_the_shape_default(policy: HandoffPolicy) -> None:
    text = "# Heading\n\n" + ("x" * 400) + "\n"

    findings = check_document("docs/handoff/architecture.md", text, policy)

    assert not [finding for finding in findings if finding.locus == "document paragraph"]


def test_paragraph_limit_reads_the_masked_view(policy: HandoffPolicy) -> None:
    # An info string never closes a fence, so the long line stays example content
    # and is exempt here exactly as it is for every other masked rule.
    text = "# Heading\n\n```text\n```python\n" + ("x" * 430) + "\n```\n"

    findings = check_document("docs/handoff/architecture.md", text, policy)

    assert not [finding for finding in findings if finding.locus == "document paragraph"]


def test_require_tables_or_bullets_ignores_fenced_structure(policy: HandoffPolicy) -> None:
    text = "# Deployed\n\n```text\n- Fenced bullet.\n| Component | State |\n```\n"

    findings = check_document("docs/handoff/deployed.md", text, policy)

    assert [finding.message for finding in findings if finding.locus == "document structure"] == [
        "document requires tables or bullets"
    ]


@pytest.mark.parametrize(
    "structure",
    ["- A real bullet.", "| Component | State |"],
)
def test_require_tables_or_bullets_accepts_unfenced_structure(
    policy: HandoffPolicy, structure: str
) -> None:
    findings = check_document("docs/handoff/deployed.md", f"# Deployed\n\n{structure}\n", policy)

    assert not [finding for finding in findings if finding.locus == "document structure"]


# `forbid_changelog` is set on deployed.md and `forbid_narrative_history` on
# STATUS.md, so each rule is exercised through the profile that declares it.
_FENCED_CHANGELOG = "# Deployed\n\n- Real bullet.\n\n```text\n## Changelog\n```\n"
_UNFENCED_CHANGELOG = "# Deployed\n\n- Real bullet.\n\n## Changelog\n\n- Entry.\n"
_FENCED_HISTORY = "# Status\n\n## Current snapshot\n\n- Short.\n\n```text\n## History\n```\n"
_UNFENCED_HISTORY = "# Status\n\n## Current snapshot\n\n- Short.\n\n## History\n\n- Old.\n"


def test_forbid_changelog_ignores_a_fenced_heading(policy: HandoffPolicy) -> None:
    findings = check_document("docs/handoff/deployed.md", _FENCED_CHANGELOG, policy)

    assert not [finding for finding in findings if "changelog" in finding.message]


def test_forbid_changelog_still_flags_an_unfenced_heading(policy: HandoffPolicy) -> None:
    finding = next(
        item
        for item in check_document("docs/handoff/deployed.md", _UNFENCED_CHANGELOG, policy)
        if "changelog" in item.message
    )

    assert finding.locus == "section heading"
    assert finding.line == _UNFENCED_CHANGELOG.splitlines().index("## Changelog") + 1


def test_forbid_narrative_history_ignores_a_fenced_heading(policy: HandoffPolicy) -> None:
    findings = check_document("docs/STATUS.md", _FENCED_HISTORY, policy)

    assert not [finding for finding in findings if "narrative history" in finding.message]


def test_forbid_narrative_history_still_flags_an_unfenced_heading(policy: HandoffPolicy) -> None:
    finding = next(
        item
        for item in check_document("docs/STATUS.md", _UNFENCED_HISTORY, policy)
        if "narrative history" in item.message
    )

    assert finding.locus == "section heading"
    assert finding.line == _UNFENCED_HISTORY.splitlines().index("## History") + 1


def test_conventions_profile_checks_quick_reference_and_entry_lengths(
    policy: HandoffPolicy,
) -> None:
    text = "## 1. Oversized\n\n" + ("x" * 1201)

    messages = [
        finding.message for finding in check_document("docs/handoff/conventions.md", text, policy)
    ]

    assert any("Quick Reference" in message for message in messages)
    assert any("entry has" in message for message in messages)


def test_conventions_entry_findings_locate_each_oversized_section(policy: HandoffPolicy) -> None:
    text = (
        "## Quick Reference\n\n- Short.\n\n"
        "## 1. First\n\n" + ("x" * 1300) + "\n\n"
        "## 2. Second\n\n- Short enough.\n\n"
        "## 3. Third\n\n" + ("y" * 1400) + "\n"
    )

    findings = [
        finding
        for finding in check_document("docs/handoff/conventions.md", text, policy)
        if finding.locus == "section entry"
    ]

    # One redacted finding per oversized section: the heading line and the
    # observed size, never the consumer-authored section name (NFR-002).
    assert [finding.message for finding in findings] == [
        "section entry has 1300 chars; max 1200",
        "section entry has 1400 chars; max 1200",
    ]
    assert [finding.line for finding in findings] == [
        text.splitlines().index("## 1. First") + 1,
        text.splitlines().index("## 3. Third") + 1,
    ]
    assert [finding.observed for finding in findings] == [1300, 1400]


def test_conventions_entry_finding_redacts_the_section_heading(policy: HandoffPolicy) -> None:
    secret = "sk-live-consumer-heading"
    text = "## Quick Reference\n\n- Short.\n\n" + f"## 1. {secret}\n\n" + ("x" * 1300) + "\n"

    findings = check_document("docs/handoff/conventions.md", text, policy)

    entry = next(finding for finding in findings if finding.locus == "section entry")
    assert entry.observed == 1300
    assert entry.limit == 1200
    assert entry.line == text.splitlines().index(f"## 1. {secret}") + 1
    assert all(secret not in finding.message for finding in findings)
    assert all(secret not in str(finding.to_dict()) for finding in findings)


def test_conventions_entry_size_excludes_fenced_examples(policy: HandoffPolicy) -> None:
    fence = "```bash\n" + ("uv run project-standards validate\n" * 60) + "```\n"
    text = (
        "## Quick Reference\n\n- Short.\n\n"
        "## 1. Worked example\n\n- Run the gate before closeout.\n\n"
        f"{fence}\n- Review the diff.\n"
    )

    findings = check_document("docs/handoff/conventions.md", text, policy)

    assert len(fence) > 1200
    assert not [finding for finding in findings if finding.locus == "section entry"]


_OVERLONG_SUMMARY_ROW = f"| 1 | {'x' * 181} |"


def test_rule_summary_cap_ignores_fenced_table_rows(policy: HandoffPolicy) -> None:
    text = (
        "## Quick Reference\n\n- Short.\n\n"
        "## 1. Worked example\n\n"
        f"```text\n{_OVERLONG_SUMMARY_ROW}\n```\n"
    )

    findings = check_document("docs/handoff/conventions.md", text, policy)

    assert not [finding for finding in findings if finding.locus == "rule summary cell"]


def test_rule_summary_cap_still_flags_an_unfenced_table_row(policy: HandoffPolicy) -> None:
    text = (
        "## Quick Reference\n\n- Short.\n\n## 1. Worked example\n\n" + _OVERLONG_SUMMARY_ROW + "\n"
    )

    finding = next(
        item
        for item in check_document("docs/handoff/conventions.md", text, policy)
        if item.locus == "rule summary cell"
    )

    assert (finding.observed, finding.limit) == (181, 180)
    assert finding.line == text.splitlines().index(_OVERLONG_SUMMARY_ROW) + 1


def test_session_profile_checks_row_and_headline(policy: HandoffPolicy) -> None:
    headline = " ".join(f"word{i}" for i in range(21))
    text = f"| 2026-07-09 | {headline} | {'x' * 221} |\n"

    messages = [
        finding.message
        for finding in check_document("docs/handoff/sessions/2026-07.md", text, policy)
    ]

    assert any("row has" in message for message in messages)
    assert any("headline has" in message for message in messages)


def test_session_row_and_headline_caps_skip_non_table_lines(policy: HandoffPolicy) -> None:
    # Prose sits above `row_max_chars` (220) but below the `shape.defaults`
    # paragraph limit (360), so the whole-document assertion below stays about
    # the row/headline caps and does not also exercise the paragraph rule.
    prose = " ".join(f"word{index}" for index in range(40))
    text = (
        "# Sessions\n\n"
        "| Date | Summary | Evidence |\n| --- | --- | --- |\n"
        "| 2026-07-09 | Short row. | commit |\n\n"
        f"{prose}\n\n"
        f"- {prose}\n\n"
        "```text\n"
        f"| 2026-07-09 | {prose} | commit |\n"
        "```\n"
    )

    assert 220 < len(prose) <= 360

    assert check_document("docs/handoff/sessions/2026-07.md", text, policy) == ()


def test_bug_profile_missing_lesson_is_advisory(policy: HandoffPolicy) -> None:
    text = "# Bug\n\n## Cause\n\n- cause\n\n## Fix\n\n- fix\n"

    findings = check_document("docs/handoff/bugs/001-test.md", text, policy)

    assert any("Lesson" in finding.message for finding in findings)
    assert all(finding.severity == "warning" for finding in findings)


@pytest.mark.parametrize(
    "text",
    [
        "-----BEGIN OPENSSH PRIVATE KEY-----\nmaterial\n",
        "access_key = AKIA1234567890ABCDEF\n",
        "password: correct-horse-battery-staple\n",
        "token = literal-token-value\n",
    ],
)
def test_literal_secret_values_are_rejected_without_echo(policy: HandoffPolicy, text: str) -> None:
    findings = check_secret_references("docs/handoff/credentials.md", text, policy)

    assert findings
    assert all(finding.code == "AH-SECRET-LITERAL" for finding in findings)
    assert not any("correct-horse" in finding.message for finding in findings)
    assert not any("literal-token" in finding.message for finding in findings)


@pytest.mark.parametrize(
    "text",
    [
        "address: OPENBAO_ADDR\n",
        "token = ${OPENBAO_TOKEN}\n",
        "credential: bao://kv/project/path\n",
        "location = secret/data/project\n",
    ],
)
def test_secret_references_are_allowed(policy: HandoffPolicy, text: str) -> None:
    assert check_secret_references("docs/handoff/credentials.md", text, policy) == ()


# Issue #94 (engine mirror of the agent-handoff 1.7 provider fix).
#
# A right-hand side that ACQUIRES a credential at runtime stores none, so it is
# not literal material. `$( ... )` was already tolerated here, but only
# incidentally: "$" is an allowed reference prefix. The backtick form is the same
# shell construct and was reported as a literal. The engine already strips
# backticks before applying the reference policy, so a reference wrapped in a
# Markdown code span was never the problem here that it was in the provider --
# the whitespace rule is what separates a command from a quoted value.


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            "TOKEN=$(grep '<credential-name>' /path/to/credential-reference)\n",
            id="dollar-paren-substitution",
        ),
        pytest.param(
            'TOKEN="$(credential-helper read env:CREDENTIAL_NAME)"\n',
            id="quoted-dollar-paren-substitution",
        ),
        pytest.param(
            "TOKEN=`credential-helper read env:CREDENTIAL_NAME`\n",
            id="backtick-substitution",
        ),
        pytest.param(
            "token: `bao kv get -field=value secret/apps/example`\n",
            id="backtick-substitution-colon-form",
        ),
        pytest.param("token: `secret/apps/example`\n", id="reference-inside-a-code-span"),
    ],
)
def test_runtime_acquisition_is_not_literal_material(policy: HandoffPolicy, text: str) -> None:
    """A command substitution or a code-span reference stores nothing (issue #94)."""
    assert check_secret_references("docs/handoff/credentials.md", text, policy) == ()


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        pytest.param(
            "token: `abc123literal`\n", "abc123literal", id="no-whitespace-span-is-not-a-command"
        ),
        pytest.param(
            "password = `s3cr3t-value`\n", "s3cr3t-value", id="no-whitespace-span-other-label"
        ),
        pytest.param(
            "TOKEN=`printf '%s' 'synth-live-7Jm9Qv2Nk4Rx8Pz6'`\n",
            "synth-live-7Jm9Qv2Nk4Rx8Pz6",
            id="printf-command-naming-no-reference",
        ),
        pytest.param(
            "password: `echo correct-horse-battery-staple`\n",
            "correct-horse-battery-staple",
            id="echo-command-naming-no-reference",
        ),
    ],
)
def test_backtick_spans_do_not_launder_literal_material(
    policy: HandoffPolicy, text: str, secret: str
) -> None:
    """Backticks must not buy an exemption, with or without internal whitespace.

    A single-token span is a quoted value, not a command invocation. A span that
    IS shaped like a command still only counts as acquisition when one of its
    tokens passes the reference policy -- a genuine retrieval names its source.
    `printf`/`echo` forms name none, so they are a literal written as a command
    argument, and without this boundary the exemption would launder any secret.
    """
    findings = check_secret_references("docs/handoff/credentials.md", text, policy)

    assert [finding.code for finding in findings] == ["AH-SECRET-LITERAL"]
    assert all(secret not in finding.message for finding in findings)


def test_runtime_acquisition_findings_keep_their_line_coordinate(policy: HandoffPolicy) -> None:
    """The mirror removes a false positive only; located reporting is unchanged."""
    text = (
        "# Credentials\n\n"
        "token = literal-token-value\n"
        "TOKEN=`credential-helper read env:SAFE`\n"
        "password: another-literal\n"
    )

    findings = check_secret_references("docs/handoff/credentials.md", text, policy)

    assert [(finding.line, finding.column) for finding in findings] == [(3, 1), (5, 1)]


def test_malformed_policy_is_controlled(tmp_path: Path) -> None:
    malformed = tmp_path / "policy.toml"
    malformed.write_text('version = "1.0"\n[shape]\nunknown = true\n', encoding="utf-8")

    with pytest.raises(PolicyError, match="invalid agent-handoff policy"):
        load_policy(malformed)


def test_policy_rejects_unknown_nested_keys(tmp_path: Path) -> None:
    text = POLICY_PATH.read_text(encoding="utf-8").replace(
        "max_paragraph_chars = 360", "max_paragraph_chars = 360\nunknown = true"
    )
    malformed = tmp_path / "policy.toml"
    malformed.write_text(text, encoding="utf-8")

    with pytest.raises(PolicyError, match="invalid agent-handoff policy"):
        load_policy(malformed)
