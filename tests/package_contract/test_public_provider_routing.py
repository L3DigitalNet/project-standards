from __future__ import annotations

from pathlib import Path

from project_standards.package_contract.payload import (
    ProviderEffect,
    ProviderOperation,
    load_payload_manifest,
)

_AUTHORING = {
    ProviderOperation.FIX,
    ProviderOperation.SCAFFOLD,
    ProviderOperation.UPGRADE,
}

_PACKAGE_IDS = (
    "adr",
    "agent-handoff",
    "cli-documentation",
    "markdown-frontmatter",
    "markdown-tooling",
    "project-spec",
    "python-coding",
    "python-tooling",
    "standard-bundle-authoring",
)


def _current_payloads() -> tuple[Path, ...]:
    return tuple(sorted(Path("standards").glob("*/versions/*/payload.toml")))


def test_advertised_authoring_providers_return_executor_plans() -> None:
    providers = [
        provider
        for payload in _current_payloads()
        for provider in load_payload_manifest(payload).providers
        if provider.operation in _AUTHORING
    ]

    assert providers
    assert all(provider.effect is ProviderEffect.MUTATION_PLAN for provider in providers)
    assert all(
        isinstance(provider.entrypoint, str) and provider.entrypoint.startswith("payload:")
        for provider in providers
    )


def test_shared_command_boundary_contains_no_package_dispatch() -> None:
    shared = (
        Path("src/project_standards/control_plane/command_resolution.py"),
        Path("src/project_standards/control_plane/providers.py"),
        Path("src/project_standards/control_plane/executor.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in shared)

    for package_id in _PACKAGE_IDS:
        assert f'"{package_id}"' not in source
        assert f"'{package_id}'" not in source
