from __future__ import annotations

import base64
import hashlib
import json
import shutil
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

import project_standards.control_plane.providers as provider_runtime
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import run as reconcile
from project_standards.control_plane.cli import run_render, validate_repository
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution, InstalledPayload
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.provider_subprocess import ProviderSubprocessOutcome
from project_standards.control_plane.providers import invoke_provider
from project_standards.package_contract import (
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.payload import JsonObject
from project_standards.package_contract.projection import sync_payload_projection

_ROOT = Path(__file__).resolve().parents[2]
COMMAND_FIXTURE_ROOT = _ROOT / "tests/fixtures/command-provider"
COMMAND_FIXTURE_STANDARD = "command-provider-fixture"
COMMAND_FIXTURE_VERSION = "1.0"
COMMAND_FIXTURE_RESOURCE = b"fixture-resource\n"


def command_provider_distribution(tmp_path: Path) -> InstalledDistribution:
    """Install the synthetic fixture through the same projected layout as a wheel."""
    repository = tmp_path / "command-provider-source"
    shutil.copytree(COMMAND_FIXTURE_ROOT / "standards", repository / "standards")
    shutil.copytree(COMMAND_FIXTURE_ROOT / "catalogs", repository / "catalogs")
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()

    installed = tmp_path / "command-provider-installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    distribution = InstalledDistribution(installed, tool_release="5.18.0")
    payload = command_provider_payload(distribution)
    # Wheel extraction does not promise executable modes. Success from this copy
    # therefore proves the integrity-checked private 0755 materialization is the path run.
    (payload.root / "bin/command-provider-fixture").chmod(0o644)
    return distribution


def command_provider_payload(distribution: InstalledDistribution) -> InstalledPayload:
    """Return the fixture payload selected from the synthetic installed catalog."""
    catalog = distribution.load_catalog(CatalogMajor("5"))
    matches = [
        payload
        for payload in catalog.payloads
        if payload.manifest.payload.standard == COMMAND_FIXTURE_STANDARD
    ]
    assert len(matches) == 1
    return matches[0]


def initialize_command_provider_repo(
    tmp_path: Path,
    distribution: InstalledDistribution,
    *,
    name: str = "command-provider-consumer",
) -> Path:
    """Initialize and enable the synthetic standard without bypassing public owners."""
    repo = tmp_path / name
    repo.mkdir()
    initialize_control_plane(repo, CatalogMajor("5"), distribution=distribution)
    set_standard_enabled(repo, COMMAND_FIXTURE_STANDARD, True)
    return repo


def reconcile_command_provider_repo(
    repo: Path,
    distribution: InstalledDistribution,
) -> None:
    """Apply the public reconciliation route and require a successful checkpoint."""
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def test_command_fixture_source_tree_is_self_consistent() -> None:
    """Pin the fixture's own catalog/family/payload digest chain.

    Rebuilding the fixture binary re-digests payload.toml and standard.toml, and
    tests/fixtures/command-provider/catalogs/5.toml has to move with them. When the
    Go 1.26.6 bump (a5b74831) advanced the first two and left the catalog behind,
    every end-to-end test below failed with the opaque runtime message "installed
    catalog disagrees with its package family index", pointing at the control plane
    instead of at the stale fixture byte. This case names the real disagreement.
    """
    repository = build_package_repository(COMMAND_FIXTURE_ROOT, catalog_major=5)
    assert validate_package_repository(repository) == ()


def test_go_fixture_runs_public_reconcile_validate_and_private_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = command_provider_distribution(tmp_path)
    payload = command_provider_payload(distribution)
    installed_binary = payload.root / "bin/command-provider-fixture"
    repo = initialize_command_provider_repo(tmp_path, distribution)
    real_run = provider_runtime.run_provider_subprocess
    materialized: list[Path] = []
    requests: list[dict[str, object]] = []

    def inspect_runner(
        argv: Sequence[str],
        request: bytes,
        *,
        timeout: float,
        environment: Mapping[str, str],
        validate_status: bool = True,
    ) -> ProviderSubprocessOutcome:
        executable = Path(argv[0])
        materialized.append(executable)
        requests.append(cast("dict[str, object]", json.loads(request)))
        assert executable != installed_binary
        assert executable.read_bytes() == installed_binary.read_bytes()
        assert stat.S_IMODE(executable.stat().st_mode) == 0o755
        assert _digest(executable.read_bytes()) == _digest(installed_binary.read_bytes())
        assert environment == {}
        return real_run(
            argv,
            request,
            timeout=timeout,
            environment=environment,
            validate_status=validate_status,
        )

    monkeypatch.setattr(provider_runtime, "run_provider_subprocess", inspect_runner)

    reconcile_command_provider_repo(repo, distribution)
    assert validate_repository(repo, distribution=distribution) == 0

    generated = repo / ".standards/command-provider-fixture.txt"
    assert generated.read_bytes() == (b"command-provider-fixture|render|fixture-resource\n")
    assert stat.S_IMODE(installed_binary.stat().st_mode) == 0o644
    assert {cast("dict[str, object]", item["input"])["operation"] for item in requests} >= {
        "render",
        "verify",
    }
    expected_resource = base64.b64encode(COMMAND_FIXTURE_RESOURCE).decode("ascii")
    for request in requests:
        assert request["schema_version"] == "1.0"
        assert request["resources"] == {"fixture-data": expected_resource}
        provider_input = cast("dict[str, object]", request["input"])
        assert provider_input["resources"] == {"fixture-data": _digest(COMMAND_FIXTURE_RESOURCE)}
    assert materialized
    assert all(not executable.exists() for executable in materialized)
    assert installed_binary.exists()


def test_go_fixture_refuses_wrong_platform_before_materialization_or_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    distribution = command_provider_distribution(tmp_path)
    repo = initialize_command_provider_repo(tmp_path, distribution)

    monkeypatch.setattr(provider_runtime, "_host_command_platform", lambda: "linux/arm64")

    def unexpected(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("unsupported platform created executable state or spawned")

    monkeypatch.setattr(provider_runtime.tempfile, "TemporaryDirectory", unexpected)
    monkeypatch.setattr(provider_runtime, "run_provider_subprocess", unexpected)

    assert (
        run_render(
            [
                COMMAND_FIXTURE_STANDARD,
                "render-fixture",
                "--repo",
                str(repo),
            ],
            distribution=distribution,
        )
        == 2
    )
    captured = capsys.readouterr()
    assert "unsupported command provider platform" in captured.err
    assert str(command_provider_payload(distribution).root) not in captured.err


def test_go_fixture_direct_result_preserves_input_resource_and_typed_effect(
    tmp_path: Path,
) -> None:
    distribution = command_provider_distribution(tmp_path)
    payload = command_provider_payload(distribution)
    repo = initialize_command_provider_repo(tmp_path, distribution)
    provider = next(item for item in payload.manifest.providers if item.id == "validate-fixture")
    snapshots = cast("JsonObject", {"nested": {"values": ["exact", 7]}})

    result = invoke_provider(
        provider_runtime.ProviderInvocation(
            repo=repo,
            payload=payload,
            standard_id=COMMAND_FIXTURE_STANDARD,
            version=payload.manifest.payload.version,
            provider_id=provider.id,
            operation=provider.operation,
            effective_config={},
            snapshots=snapshots,
        )
    )

    assert result.effect.value == "findings"
    assert len(result.findings) == 1
    output = cast("dict[str, object]", result.structured_output)
    observed = cast("dict[str, object]", output["observed"])
    assert observed["snapshots"] == snapshots
    assert observed["resource_base64"] == base64.b64encode(COMMAND_FIXTURE_RESOURCE).decode("ascii")
    assert observed["resource_digest"] == _digest(COMMAND_FIXTURE_RESOURCE)
    assert observed["environment"] == []
