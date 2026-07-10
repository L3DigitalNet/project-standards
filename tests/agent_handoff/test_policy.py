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


@pytest.fixture(scope="module")
def policy() -> HandoffPolicy:
    return load_policy(POLICY_PATH)


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


def test_conventions_profile_checks_quick_reference_and_entry_lengths(
    policy: HandoffPolicy,
) -> None:
    text = "## 1. Oversized\n\n" + ("x" * 1201)

    messages = [
        finding.message for finding in check_document("docs/handoff/conventions.md", text, policy)
    ]

    assert any("Quick Reference" in message for message in messages)
    assert any("entry has" in message for message in messages)


def test_session_profile_checks_row_and_headline(policy: HandoffPolicy) -> None:
    headline = " ".join(f"word{i}" for i in range(21))
    text = f"| 2026-07-09 | {headline} | {'x' * 221} |\n"

    messages = [
        finding.message
        for finding in check_document("docs/handoff/sessions/2026-07.md", text, policy)
    ]

    assert any("row has" in message for message in messages)
    assert any("headline has" in message for message in messages)


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
