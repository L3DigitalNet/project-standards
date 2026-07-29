"""Effect and operation refusals before any provider process exists (T4).

Covers TC-T4-002: unknown providers, unknown operations, and every mutating
effect fail before worker creation, and every approved operation leaves the
consumer filesystem byte-for-byte unchanged.

ADR 0025 fixes the approved set exactly: effect ``findings`` restricted to the
operations ``validate``, ``verify``, ``lint``, and ``drift-check``. It excludes
``semantic-review`` despite its ``findings`` effect (``SPEC-RD01 OQ-006``), the
whole ``content`` effect (no v1 tool exposes it), and the ``mutation-plan`` and
``migration-report`` effects outright. The refusal set below is therefore
*derived* from the authoritative ``ProviderOperation`` enum rather than listed,
so an operation added to the package contract later is refused by default
instead of quietly widening this surface. Nothing here asserts that the service
publishes an allowlist under any particular name (T4.2 Codex review F15,
disposition ACCEPT-PARTIAL): the set is frozen only by which genuinely declared
providers are accepted and which are refused.

The fixture declares a real ``semantic-review`` provider precisely so the
allowlist can be separated from the dispatcher's own operation/declaration
agreement check (review F2). Invoking a *mismatched* provider ID would be
refused by the dispatcher whatever the service does; invoking
``semantic-review-alpha`` under its own declared operation can only be refused
by the service's allowlist.

"Before worker creation" is proven without reaching into the service: process
creation is audited at every primitive the standard library offers, the mutating
and semantic-review fixture providers write a sentinel the instant their bytes
execute, and no child may be left behind.
"""

from __future__ import annotations

import multiprocessing.process
import os
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from project_standards.package_contract.payload import ProviderEffect, ProviderOperation
from tests.mcp_services.helpers import import_mcp_services
from tests.mcp_services.test_providers import (
    APPROVED_OPERATIONS,
    SELECTED_STANDARD,
    SELECTED_VERSION,
    assert_error_is_content_safe,
    assert_no_unreaped_children,
    build_facade,
    build_provider_distribution,
    build_provider_repo,
    mutating_provider_ran,
    require_operation,
    tree_state,
)

# Fixture providers invoked under their own declared operation whose effect —
# or whose operation, in the semantic-review case — is outside the approved set.
# alpha 2.0 declares all four, so each is a real, resolvable, integrity-checked
# declaration rather than a synthetic name.
NON_APPROVED_DECLARATIONS: tuple[tuple[str, str, ProviderEffect], ...] = (
    ("fix-alpha", "fix", ProviderEffect.MUTATION_PLAN),
    ("render-alpha", "render", ProviderEffect.CONTENT),
    ("migrate-alpha", "migrate", ProviderEffect.MIGRATION_REPORT),
    ("semantic-review-alpha", "semantic-review", ProviderEffect.FINDINGS),
)


@contextmanager
def process_creation_audit() -> Generator[list[str]]:
    """Record every standard-library process-creation call made inside the block.

    A refusal that reaches any of these has already paid for a worker, which is
    exactly what "fail before worker creation" forbids. The primitives are
    patched rather than blocked so a violation is reported as a named call
    instead of an unrelated crash.
    """
    calls: list[str] = []
    original_fork = os.fork
    original_spawn = os.posix_spawn
    original_spawnp = os.posix_spawnp
    original_popen = subprocess.Popen.__init__
    original_start = multiprocessing.process.BaseProcess.start

    def record(name: str, function: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            return function(*args, **kwargs)

        return wrapper

    monkey = pytest.MonkeyPatch()
    monkey.setattr(os, "fork", record("os.fork", original_fork))
    monkey.setattr(os, "posix_spawn", record("os.posix_spawn", original_spawn))
    monkey.setattr(os, "posix_spawnp", record("os.posix_spawnp", original_spawnp))
    monkey.setattr(subprocess.Popen, "__init__", record("subprocess.Popen", original_popen))
    monkey.setattr(
        multiprocessing.process.BaseProcess,
        "start",
        record("multiprocessing.Process.start", original_start),
    )
    try:
        yield calls
    finally:
        monkey.undo()


def test_unknown_and_mutating_effects_fail_before_worker_start(tmp_path: Path) -> None:
    """TC-T4-002 (FR-014, FR-015): nothing outside the approved set reaches a worker."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    before = tree_state(repo)
    refusals: list[tuple[str, Any]] = []
    with process_creation_audit() as spawned:
        # Each provider is invoked under the operation it actually declares, so
        # the dispatcher's own agreement check cannot stand in for the service's
        # allowlist (review F2).
        for provider_id, operation, _effect in NON_APPROVED_DECLARATIONS:
            with pytest.raises(services.ServiceError) as raised:
                invoke(
                    repo,
                    standard_id=SELECTED_STANDARD,
                    version=SELECTED_VERSION,
                    provider_id=provider_id,
                    operation=operation,
                    provider_input={},
                )
            refusals.append((provider_id, raised.value))
        for overrides in (
            {"provider_id": "no-such-provider", "operation": "validate"},
            {"provider_id": "validate-alpha", "operation": "no-such-operation"},
            {"provider_id": "validate-alpha", "operation": ""},
        ):
            with pytest.raises(services.ServiceError) as raised:
                invoke(
                    repo,
                    standard_id=SELECTED_STANDARD,
                    version=SELECTED_VERSION,
                    provider_input={},
                    **overrides,
                )
            refusals.append((str(overrides), raised.value))

    assert spawned == [], f"a worker was created for a refused request: {spawned}"
    # A mutation plan and an unapproved findings operation are never swallowed
    # and never produced: the provider bytes that would have written these
    # sentinels were not executed at all.
    assert not mutating_provider_ran(distribution)
    assert tree_state(repo) == before
    assert_no_unreaped_children()

    for label, error in refusals:
        assert_error_is_content_safe(error, repo, distribution)
        assert error.code, f"{label} carried no stable code"


def test_operation_allowlist_rejects_every_unapproved_operation(tmp_path: Path) -> None:
    """TC-T4-002: the allowlist is exactly the four ADR-approved operations."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    # Derived from the authoritative contract: every operation the package
    # contract can ever declare, minus the four the ADR approves.
    unapproved = sorted({item.value for item in ProviderOperation} - set(APPROVED_OPERATIONS))
    assert "semantic-review" in unapproved
    assert unapproved

    # The declared provider whose operation is the only unapproved one the
    # fixture can express with a matching ID.
    declared_ids = dict.fromkeys(unapproved, "validate-alpha")
    declared_ids["semantic-review"] = "semantic-review-alpha"
    declared_ids["fix"] = "fix-alpha"
    declared_ids["render"] = "render-alpha"
    declared_ids["migrate"] = "migrate-alpha"

    with process_creation_audit() as spawned:
        for operation in unapproved:
            with pytest.raises(services.ServiceError) as raised:
                invoke(
                    repo,
                    standard_id=SELECTED_STANDARD,
                    version=SELECTED_VERSION,
                    provider_id=declared_ids[operation],
                    operation=operation,
                    provider_input={},
                )
            assert_error_is_content_safe(raised.value, repo, distribution)
    assert spawned == []
    assert not mutating_provider_ran(distribution)
    assert_no_unreaped_children()

    # The complement holds: every approved operation is accepted for its own
    # declared provider, so the allowlist is neither wider nor narrower than the
    # four ADR names.
    accepted = {
        "validate": "validate-alpha",
        "verify": "verify-alpha",
        "lint": "lint-alpha",
        "drift-check": "drift-check-alpha",
    }
    assert set(accepted) == set(APPROVED_OPERATIONS)
    for operation, provider_id in accepted.items():
        result = invoke(
            repo,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id=provider_id,
            operation=operation,
            provider_input={},
        )
        assert result.operation == operation


@pytest.mark.parametrize(
    ("provider_id", "operation"),
    [
        ("validate-alpha", "validate"),
        ("verify-alpha", "verify"),
        ("lint-alpha", "lint"),
        ("drift-check-alpha", "drift-check"),
    ],
)
def test_supported_operations_never_change_the_consumer_filesystem(
    tmp_path: Path, provider_id: str, operation: str
) -> None:
    """TC-T4-002: a controlled before/after proof for every approved operation.

    The capture includes inode and change time, so a service that rewrites or
    chmods a file and restores it before returning is detected — unprivileged
    code cannot put ``st_ctime_ns`` back (T4.2 review F17, orchestrator
    substitution for a filesystem-event watcher).
    """
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    # A symlink and a non-default mode make the proof sensitive to more than
    # byte changes: a retargeted link or a chmod must also fail it.
    (repo / "link.md").symlink_to(repo / ".standards/config.toml")
    (repo / "README.md").write_text("# consumer\n", encoding="utf-8")
    (repo / "README.md").chmod(0o640)

    invoke = require_operation(facade, "invoke_read_provider")
    before = tree_state(repo)
    invoke(
        repo,
        standard_id=SELECTED_STANDARD,
        version=SELECTED_VERSION,
        provider_id=provider_id,
        operation=operation,
        provider_input={},
    )
    assert tree_state(repo) == before


def test_composite_operations_never_change_the_consumer_filesystem(tmp_path: Path) -> None:
    """TC-T4-002: the composite tools inherit the same no-write guarantee."""
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    (repo / "link.md").symlink_to(repo / ".standards/config.toml")

    validate_repo = require_operation(facade, "validate_repo")
    drift_check = require_operation(facade, "drift_check")
    before = tree_state(repo)
    validate_repo(repo)
    drift_check(repo)
    assert tree_state(repo) == before
    assert not mutating_provider_ran(distribution)


def test_provider_operations_reject_every_unsafe_root(tmp_path: Path) -> None:
    """FR-024/IR-007: root containment is decided before any provider work begins.

    ``invoke_read_provider`` is in the table alongside the composites (T4.2
    review F18): the frozen §5.5 interface must refuse the same roots, with
    otherwise valid identity arguments, and must not start a worker while doing
    so.
    """
    services = import_mcp_services()
    distribution = build_provider_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_provider_repo(tmp_path, "consumer", distribution=distribution)
    invoke = require_operation(facade, "invoke_read_provider")

    def direct(candidate: Path) -> Any:
        return invoke(
            candidate,
            standard_id=SELECTED_STANDARD,
            version=SELECTED_VERSION,
            provider_id="validate-alpha",
            operation="validate",
            provider_input={},
        )

    operations = [
        require_operation(facade, "validate_repo"),
        require_operation(facade, "drift_check"),
        direct,
    ]
    candidates = [
        Path("relative/path"),
        repo / ".." / repo.name,
        repo / "no-such-child",
        repo / ".standards/config.toml",
    ]
    with process_creation_audit() as spawned:
        for operation in operations:
            for candidate in candidates:
                with pytest.raises(services.ServiceError) as raised:
                    operation(candidate)
                assert raised.value.code
                assert str(candidate) not in raised.value.message
    assert spawned == []
    assert_no_unreaped_children()
