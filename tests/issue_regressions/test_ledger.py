from __future__ import annotations

import hashlib
import subprocess
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from tests.issue_regressions import ledger as ledger_module
from tests.issue_regressions.ledger import (
    CLOSED_ISSUES,
    ConsumerOutcome,
    LedgerError,
    Outcome,
    compare_authority,
    compare_predecessor_authority,
    require_passed_outcomes,
    run_references,
    run_verified_wheel_references,
    symbol_digest,
    validate_baseline,
    validate_historical_consumer_authority,
    validate_ledger,
)

_ROOT = Path(__file__).resolve().parents[2]
_LEDGER = Path(__file__).with_name("ledger.toml")
_BASELINE = Path(__file__).with_name("baseline.toml")
_INTRODUCED_RELEASES = {
    3: "4.2.0",
    8: "5.1.1",
    **dict.fromkeys(range(9, 12), "5.2.0"),
    **dict.fromkeys(range(12, 14), "5.3.0"),
    **dict.fromkeys(range(14, 16), "5.4.0"),
    **dict.fromkeys(range(16, 20), "5.5.0"),
    **dict.fromkeys(range(20, 24), "5.6.0"),
    **dict.fromkeys(range(24, 26), "5.7.0"),
    **dict.fromkeys(range(26, 32), "5.8.0"),
    32: "5.9.0",
    **dict.fromkeys(range(35, 50), "5.9.0"),
}


def _write_proof(repo: Path, body: str = "assert True") -> str:
    proof = repo / "tests/test_proof.py"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(f"def test_proof() -> None:\n    {body}\n", encoding="utf-8")
    return "tests/test_proof.py::test_proof"


def _ledger_text(reference: str, digest: str, *, number: int = 3) -> str:
    return f"""
schema_version = "1.1"

[[issues]]
id = "GH-{number}"
number = {number}
rationale = "durable behavior contract"
introduced_release = "5.9.0"
environments = ["source"]
references = ["{reference}"]
amendments = []

[[issues.proofs]]
symbol = "{reference}"
digest = "{digest}"
"""


def test_ledger_schema_1_1_loads_canonical_introduced_release(tmp_path: Path) -> None:
    reference = _write_proof(tmp_path)
    ledger_path = tmp_path / "ledger.toml"
    ledger_path.write_text(
        _ledger_text(reference, symbol_digest(tmp_path, reference)),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Regression Test",
            "-c",
            "user.email=regression@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "seed authority",
        ],
        cwd=tmp_path,
        check=True,
    )

    ledger = validate_ledger(ledger_path, tmp_path, expected_issues=(3,))

    assert ledger.issues[0].introduced_release == "5.9.0"


@pytest.mark.parametrize(
    "introduced_release",
    [
        pytest.param(None, id="missing"),
        pytest.param("1.0", id="missing-patch"),
        pytest.param("01.0.0", id="leading-zero"),
        pytest.param("1.0.0-alpha", id="prerelease"),
        pytest.param(" 1.0.0", id="leading-space"),
    ],
)
def test_ledger_schema_1_1_rejects_noncanonical_introduced_release(
    tmp_path: Path,
    introduced_release: str | None,
) -> None:
    reference = _write_proof(tmp_path)
    text = _ledger_text(reference, symbol_digest(tmp_path, reference))
    if introduced_release is None:
        text = text.replace('introduced_release = "5.9.0"\n', "")
    else:
        text = text.replace("5.9.0", introduced_release)
    ledger_path = tmp_path / "ledger.toml"
    ledger_path.write_text(text, encoding="utf-8")

    with pytest.raises(LedgerError, match="introduced_release"):
        validate_ledger(ledger_path, tmp_path, expected_issues=(3,))


def test_seed_ledger_covers_every_closed_issue_and_resolves_every_proof() -> None:
    ledger = validate_ledger(_LEDGER, _ROOT)
    seed = tuple(row for row in ledger.issues if "baseline-wheel" in row.environments)

    assert tuple(row.number for row in seed) == CLOSED_ISSUES
    assert all(row.references and row.proofs for row in seed)


def test_candidate_ledger_covers_seed_and_current_train_with_release_history() -> None:
    ledger = validate_ledger(
        _LEDGER,
        _ROOT,
        expected_issues=ledger_module.ALL_ISSUES,
    )

    assert tuple(row.number for row in ledger.issues) == ledger_module.ALL_ISSUES
    assert {row.number: row.introduced_release for row in ledger.issues} == (_INTRODUCED_RELEASES)
    assert (
        tuple(row.number for row in ledger.issues if "baseline-wheel" in row.environments)
        == CLOSED_ISSUES
    )
    assert (
        tuple(
            row.number for row in ledger.issues if row.number in ledger_module.CURRENT_TRAIN_ISSUES
        )
        == ledger_module.CURRENT_TRAIN_ISSUES
    )


def test_environment_references_select_only_applicable_rows() -> None:
    ledger = validate_ledger(
        _LEDGER,
        _ROOT,
        expected_issues=ledger_module.ALL_ISSUES,
    )

    baseline = ledger_module.references_for_environment(ledger, "baseline-wheel")
    candidate = ledger_module.references_for_environment(ledger, "candidate-wheel")
    source = ledger_module.references_for_environment(ledger, "source")

    assert baseline
    assert set(baseline) < set(candidate)
    assert candidate == source


def test_committed_source_issue_references_all_pass() -> None:
    ledger = validate_ledger(_LEDGER, _ROOT)
    references = ledger_module.references_for_environment(ledger, "source")

    outcomes = run_references(_ROOT, references)

    require_passed_outcomes(references, outcomes)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("missing", "missing issue rows"),
        ("duplicate", "duplicate issue"),
        ("dangling", "does not resolve"),
        ("unexplained", "unexpected issue rows"),
    ],
)
def test_ledger_rejects_missing_duplicate_dangling_and_unexplained_rows(
    tmp_path: Path,
    mutation: str,
    match: str,
) -> None:
    reference = _write_proof(tmp_path)
    digest = symbol_digest(tmp_path, reference)
    text = _ledger_text(reference, digest)
    expected = (3,)
    if mutation == "missing":
        expected = (3, 8)
    elif mutation == "duplicate":
        text += _ledger_text(reference, digest).replace('schema_version = "1.1"', "")
    elif mutation == "dangling":
        text = text.replace("tests/test_proof.py::test_proof", "tests/test_proof.py::missing")
    else:
        expected = ()
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(text, encoding="utf-8")

    with pytest.raises(LedgerError, match=match):
        validate_ledger(ledger, tmp_path, expected_issues=expected)


def test_ledger_rejects_deleted_or_assertion_relaxed_proof(tmp_path: Path) -> None:
    reference = _write_proof(tmp_path)
    digest = symbol_digest(tmp_path, reference)
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(_ledger_text(reference, digest), encoding="utf-8")

    _write_proof(tmp_path, "assert 1 == 1")
    with pytest.raises(LedgerError, match="proof digest changed"):
        validate_ledger(ledger, tmp_path, expected_issues=(3,))

    (tmp_path / "tests/test_proof.py").unlink()
    with pytest.raises(LedgerError, match="does not resolve"):
        validate_ledger(ledger, tmp_path, expected_issues=(3,))


def test_ledger_rejects_helper_relaxation_when_helper_is_a_proof_symbol(tmp_path: Path) -> None:
    proof = tmp_path / "tests/test_proof.py"
    proof.parent.mkdir(parents=True)
    proof.write_text(
        "def _contract() -> bool:\n"
        "    return True\n\n"
        "def test_proof() -> None:\n"
        "    assert _contract()\n",
        encoding="utf-8",
    )
    reference = "tests/test_proof.py::test_proof"
    helper = "tests/test_proof.py::_contract"
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(
        _ledger_text(reference, symbol_digest(tmp_path, reference))
        + (
            "\n[[issues.proofs]]\n"
            f'symbol = "{helper}"\n'
            f'digest = "{symbol_digest(tmp_path, helper)}"\n'
        ),
        encoding="utf-8",
    )
    proof.write_text(
        "def _contract() -> bool:\n"
        "    return False\n\n"
        "def test_proof() -> None:\n"
        "    assert _contract()\n",
        encoding="utf-8",
    )

    with pytest.raises(LedgerError, match="proof digest changed"):
        validate_ledger(ledger, tmp_path, expected_issues=(3,))


def test_proof_digest_derives_same_module_helper_and_constant_dependencies(
    tmp_path: Path,
) -> None:
    proof = tmp_path / "tests/test_proof.py"
    proof.parent.mkdir(parents=True)
    proof.write_text(
        "EXPECTED = True\n\n"
        "def _contract() -> bool:\n"
        "    return EXPECTED\n\n"
        "def test_proof() -> None:\n"
        "    assert _contract()\n",
        encoding="utf-8",
    )
    reference = "tests/test_proof.py::test_proof"
    original = symbol_digest(tmp_path, reference)
    proof.write_text(
        "EXPECTED = False\n\n"
        "def _contract() -> bool:\n"
        "    return EXPECTED\n\n"
        "def test_proof() -> None:\n"
        "    assert _contract()\n",
        encoding="utf-8",
    )
    assert symbol_digest(tmp_path, reference) != original


def test_proof_digest_derives_module_autouse_fixture_dependencies(tmp_path: Path) -> None:
    proof = tmp_path / "tests/test_proof.py"
    proof.parent.mkdir(parents=True)
    proof.write_text(
        "import pytest\n\n"
        "EXPECTED = True\n\n"
        "@pytest.fixture(autouse=True)\n"
        "def implicit_guard() -> None:\n"
        "    assert EXPECTED\n\n"
        "def test_proof() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )
    reference = "tests/test_proof.py::test_proof"
    original = symbol_digest(tmp_path, reference)
    proof.write_text(
        proof.read_text(encoding="utf-8").replace("EXPECTED = True", "EXPECTED = False")
    )

    assert symbol_digest(tmp_path, reference) != original


def test_proof_digest_derives_usefixtures_and_conftest_dependencies(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_proof.py").write_text(
        "import pytest\n\n"
        '@pytest.mark.usefixtures("implicit_guard")\n'
        "def test_proof() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )
    conftest = tests / "conftest.py"
    conftest.write_text(
        "import pytest\n\n"
        "EXPECTED = True\n\n"
        "@pytest.fixture\n"
        "def implicit_guard() -> None:\n"
        "    assert EXPECTED\n",
        encoding="utf-8",
    )
    reference = "tests/test_proof.py::test_proof"
    original = symbol_digest(tmp_path, reference)
    conftest.write_text(
        conftest.read_text(encoding="utf-8").replace("EXPECTED = True", "EXPECTED = False"),
        encoding="utf-8",
    )

    assert symbol_digest(tmp_path, reference) != original


def test_historical_authority_rejects_self_consistent_proof_rewrite_without_amendment(
    tmp_path: Path,
) -> None:
    reference = _write_proof(tmp_path)
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(
        _ledger_text(reference, symbol_digest(tmp_path, reference)),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Regression Test",
            "-c",
            "user.email=regression@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "seed authority",
        ],
        cwd=tmp_path,
        check=True,
    )

    _write_proof(tmp_path, "assert 1 == 1")
    ledger.write_text(
        _ledger_text(reference, symbol_digest(tmp_path, reference)),
        encoding="utf-8",
    )

    with pytest.raises(LedgerError, match="amendment"):
        validate_ledger(ledger, tmp_path, expected_issues=(3,))


def test_historical_authority__missing_git_history__reports_collection_failure(
    tmp_path: Path,
) -> None:
    reference = _write_proof(tmp_path)
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(
        _ledger_text(reference, symbol_digest(tmp_path, reference)),
        encoding="utf-8",
    )

    with pytest.raises(LedgerError) as error:
        validate_ledger(ledger, tmp_path, expected_issues=(3,))

    message = str(error.value)
    assert "git log --follow --reverse --format=%H -- ledger.toml failed:" in message
    assert "not a git repository" in message
    assert "amendment" not in message


def test_historical_authority_accepts_one_complete_linear_amendment(tmp_path: Path) -> None:
    reference = _write_proof(tmp_path)
    original = symbol_digest(tmp_path, reference)
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(_ledger_text(reference, original), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Regression Test",
            "-c",
            "user.email=regression@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "seed authority",
        ],
        cwd=tmp_path,
        check=True,
    )

    _write_proof(tmp_path, "assert 1 == 1")
    current = symbol_digest(tmp_path, reference)
    amendment = (
        "amendments = [{ "
        'approved_by = "owner", '
        'date = "2026-07-26", '
        f'new_digest = "{current}", '
        f'new_symbol = "{reference}", '
        f'old_digest = "{original}", '
        f'old_symbol = "{reference}", '
        'reason = "preserve the same contract with a clearer assertion", '
        'requirement = "DR-002" }]'
    )
    ledger.write_text(
        _ledger_text(reference, current).replace("amendments = []", amendment),
        encoding="utf-8",
    )

    validate_ledger(ledger, tmp_path, expected_issues=(3,))


def test_ledger_rejects_incomplete_amendment(tmp_path: Path) -> None:
    reference = _write_proof(tmp_path)
    digest = symbol_digest(tmp_path, reference)
    ledger = tmp_path / "ledger.toml"
    ledger.write_text(
        _ledger_text(reference, digest).replace(
            "amendments = []",
            'amendments = [{ date = "2026-07-26", reason = "changed" }]',
        ),
        encoding="utf-8",
    )

    with pytest.raises(LedgerError, match="amendment"):
        validate_ledger(ledger, tmp_path, expected_issues=(3,))


@pytest.mark.parametrize(
    "status",
    ["missing", "skipped", "xfailed", "xpassed", "failed", "errored", "changed"],
)
def test_outcome_gate_rejects_every_nonpassing_state(status: str) -> None:
    reference = "tests/test_proof.py::test_proof"
    with pytest.raises(LedgerError, match=status):
        require_passed_outcomes(
            (reference,),
            {reference: Outcome(reference=reference, status=status, detail="probe")},
        )


def test_subprocess_runner_distinguishes_all_pytest_outcomes(tmp_path: Path) -> None:
    proof = tmp_path / "test_outcomes.py"
    proof.write_text(
        "import pytest\n\n"
        "def test_passed():\n"
        "    assert True\n\n"
        "def test_skipped():\n"
        "    pytest.skip('skip')\n\n"
        "@pytest.mark.xfail(reason='known')\n"
        "def test_xfailed():\n"
        "    assert False\n\n"
        "@pytest.mark.xfail(reason='known')\n"
        "def test_xpassed():\n"
        "    assert True\n\n"
        "def test_failed():\n"
        "    assert False\n\n"
        "@pytest.fixture\n"
        "def broken():\n"
        "    raise RuntimeError('setup')\n\n"
        "def test_errored(broken):\n"
        "    assert broken\n",
        encoding="utf-8",
    )
    references = (
        *(
            f"test_outcomes.py::test_{status}"
            for status in ("passed", "skipped", "xfailed", "xpassed", "failed", "errored")
        ),
        "test_outcomes.py::test_missing",
    )

    outcomes = run_references(tmp_path, references)

    assert {reference: outcome.status for reference, outcome in outcomes.items()} == {
        reference: reference.rsplit("_", 1)[-1] for reference in references
    }


def test_subprocess_runner_rejects_nonzero_session_after_passing_call(tmp_path: Path) -> None:
    (tmp_path / "test_pass.py").write_text(
        "def test_passed():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "conftest.py").write_text(
        "def pytest_sessionfinish(session):\n    session.exitstatus = 3\n",
        encoding="utf-8",
    )
    reference = "test_pass.py::test_passed"

    outcomes = run_references(tmp_path, (reference,))

    assert outcomes[reference].status == "errored"


def test_authority_guard_rejects_self_consistent_payload_and_node_pin_drift() -> None:
    captured = {
        "payloads": {"python-tooling@1.8": "sha256:old"},
        "node": {"package.json": "sha256:package", "package-lock.json": "sha256:lock"},
    }
    observed = {
        "payloads": {"python-tooling@1.8": "sha256:new"},
        "node": {"package.json": "sha256:package", "package-lock.json": "sha256:lock"},
    }
    with pytest.raises(LedgerError, match=r"python-tooling@1\.8"):
        compare_authority(captured, observed)

    observed["payloads"] = captured["payloads"]
    observed["node"]["package-lock.json"] = hashlib.sha256(b"changed").hexdigest()
    with pytest.raises(LedgerError, match=r"package-lock\.json"):
        compare_authority(captured, observed)


def test_predecessor_authority_allows_additions_but_rejects_mutation_or_deletion() -> None:
    captured = {"python-tooling@1.8": "sha256:old"}
    compare_predecessor_authority(
        captured,
        {
            "python-tooling@1.8": "sha256:old",
            "python-tooling@1.9": "sha256:new",
        },
    )

    with pytest.raises(LedgerError, match=r"python-tooling@1\.8"):
        compare_predecessor_authority(
            captured,
            {"python-tooling@1.8": "sha256:changed"},
        )
    with pytest.raises(LedgerError, match=r"python-tooling@1\.8"):
        compare_predecessor_authority(captured, {})


def test_committed_baseline_authority_matches_v5_8_0_release_and_node_pins() -> None:
    validate_ledger(_LEDGER, _ROOT)

    baseline = validate_baseline(_BASELINE, _ROOT)
    assert baseline.release == "5.8.0"
    assert baseline.tag_commit == "d007ba02531e8b268a2dee36823b33b04d4fba75"
    assert baseline.wheel_sha256 == (
        "5fe1b8c6dc2e06675365f5ac9be2bc884e83be7eeb21b2b842e8a67ab18b73f4"
    )
    assert baseline.sdist_sha256 == (
        "3549a51ffa17ce6e7f769c82c60b32f45ee70211a4e7f9316037882007a03c90"
    )
    assert tuple(outcome.standard_id for outcome in baseline.consumer_outcomes) == (
        "agent-handoff",
        "cli-documentation",
        "markdown-frontmatter",
        "markdown-tooling",
        "project-spec",
        "python-tooling",
    )
    expected_checks = {"format", "installed_workflow", "lint", "reconcile", "validate"}
    assert all(
        set(outcome.exact_checks) == expected_checks
        and set(outcome.latest_checks) == expected_checks
        for outcome in baseline.consumer_outcomes
    )
    cli_documentation = next(
        outcome
        for outcome in baseline.consumer_outcomes
        if outcome.standard_id == "cli-documentation"
    )
    assert cli_documentation.exact_checks["installed_workflow"] == "failed"
    assert set(cli_documentation.latest_checks.values()) == {"passed"}


def test_consumer_outcome_authority__committed_matrix__binds_executable_proofs() -> None:
    baseline = validate_baseline(_BASELINE, _ROOT)

    assert all(
        outcome.proof_digest == symbol_digest(_ROOT, outcome.proof_reference)
        for outcome in baseline.consumer_outcomes
    )


def test_consumer_outcome_authority_rejects_pass_to_fail_history_rewrite(
    tmp_path: Path,
) -> None:
    checks = {
        "format": "passed",
        "installed_workflow": "passed",
        "lint": "passed",
        "reconcile": "passed",
        "validate": "passed",
    }
    seed = ConsumerOutcome(
        standard_id="agent-handoff",
        predecessor="1.3",
        latest="1.4",
        proof_reference="tests/test_proof.py::test_proof",
        proof_digest="sha256:proof",
        exact_checks=checks,
        latest_checks=checks,
    )
    path = tmp_path / "baseline.toml"
    path.write_text(
        """
[[consumer_outcomes]]
standard_id = "agent-handoff"
predecessor = "1.3"
latest = "1.4"
proof_reference = "tests/test_proof.py::test_proof"
proof_digest = "sha256:proof"
amendments = []

[consumer_outcomes.exact_checks]
format = "passed"
installed_workflow = "passed"
lint = "passed"
reconcile = "passed"
validate = "passed"

[consumer_outcomes.latest_checks]
format = "passed"
installed_workflow = "passed"
lint = "passed"
reconcile = "passed"
validate = "passed"
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "baseline.toml"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Regression Test",
            "-c",
            "user.email=regression@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "seed baseline",
        ],
        cwd=tmp_path,
        check=True,
    )
    changed_checks = {**checks, "installed_workflow": "failed"}
    current = replace(seed, exact_checks=changed_checks)
    current_table: dict[str, object] = {
        "standard_id": current.standard_id,
        "predecessor": current.predecessor,
        "latest": current.latest,
        "proof_reference": current.proof_reference,
        "proof_digest": current.proof_digest,
        "amendments": [],
        "exact_checks": changed_checks,
        "latest_checks": checks,
    }

    with pytest.raises(LedgerError, match="outcome change"):
        validate_historical_consumer_authority(
            path,
            tmp_path,
            (current,),
            (current_table,),
        )


def test_consumer_outcome_authority__missing_git_history__reports_collection_failure(
    tmp_path: Path,
) -> None:
    checks = {
        "format": "passed",
        "installed_workflow": "passed",
        "lint": "passed",
        "reconcile": "passed",
        "validate": "passed",
    }
    current = ConsumerOutcome(
        standard_id="agent-handoff",
        predecessor="1.3",
        latest="1.4",
        proof_reference="tests/test_proof.py::test_proof",
        proof_digest="sha256:proof",
        exact_checks=checks,
        latest_checks=checks,
    )
    current_table: dict[str, object] = {
        "standard_id": current.standard_id,
        "predecessor": current.predecessor,
        "latest": current.latest,
        "proof_reference": current.proof_reference,
        "proof_digest": current.proof_digest,
        "amendments": [],
        "exact_checks": checks,
        "latest_checks": checks,
    }
    path = tmp_path / "baseline.toml"

    with pytest.raises(LedgerError) as error:
        validate_historical_consumer_authority(
            path,
            tmp_path,
            (current,),
            (current_table,),
        )

    message = str(error.value)
    assert "git log --follow --reverse --format=%H -- baseline.toml failed:" in message
    assert "not a git repository" in message
    assert "amendment" not in message


def test_verified_wheel_execution_binds_digest_version_and_import_origin(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "project_standards-9.9.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "project_standards/__init__.py",
            '"""Synthetic verified wheel."""\n\nMARKER = "verified-wheel"\n',
        )
        archive.writestr(
            "project_standards-9.9.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: project-standards\nVersion: 9.9.0\n",
        )
    baseline = validate_baseline(_BASELINE, _ROOT)
    synthetic = replace(
        baseline,
        release="9.9.0",
        wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
    )
    proof = tmp_path / "test_wheel.py"
    proof.write_text(
        "import project_standards\n\n"
        "def test_verified_import() -> None:\n"
        '    assert project_standards.MARKER == "verified-wheel"\n',
        encoding="utf-8",
    )
    reference = "test_wheel.py::test_verified_import"

    outcomes = run_verified_wheel_references(
        tmp_path,
        (reference,),
        baseline=synthetic,
        wheel=wheel,
    )
    require_passed_outcomes((reference,), outcomes)

    wheel.write_bytes(wheel.read_bytes() + b"tamper")
    with pytest.raises(LedgerError, match="wheel digest"):
        run_verified_wheel_references(
            tmp_path,
            (reference,),
            baseline=synthetic,
            wheel=wheel,
        )
