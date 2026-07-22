from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from project_standards.control_plane.codec import render_lock
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import PlannerRequest, plan_reconciliation
from project_standards.package_contract.projection import sync_payload_projection
from tests.control_plane.planner_helpers import resolution_request, write_payload
from tests.wheel_helpers import extract_pure_python_wheel

_ROOT = Path(__file__).resolve().parents[2]
_FULL = _ROOT / "tests/fixtures/package_contract/valid/full"


def _tree_bytes(repo: Path) -> dict[str, bytes]:
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file()
    }


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_every_adapter_converges_in_one_virtual_tree_and_second_apply_is_byte_noop(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    initial = {
        "settings.toml": b"[consumer]\nkeep = true\n\n[tool]\n",
        "settings.yml": b"consumer: true\ntool:\n  existing: true\n",
        "settings.json": b'{"consumer": true, "tool": {}}\n',
        "README.md": b"# Consumer\n\nKeep this prose.\n",
        ".editorconfig": b"root = true\n",
    }
    for relative, content in initial.items():
        (repo / relative).write_bytes(content)
    payload = write_payload(
        tmp_path / "payload",
        "declarative-toolbox",
        artifacts=[{"id": "script", "target": "tools/check.py", "content": b"pass\n"}],
        contributions=[
            {
                "id": "toml",
                "target": "settings.toml",
                "adapter": "toml",
                "scope": "key:/tool/demo",
                "content": b"[tool]\ndemo = true\n",
            },
            {
                "id": "yaml",
                "target": "settings.yml",
                "adapter": "yaml",
                "scope": "key:/tool/demo",
                "content": b"tool:\n  demo: true\n",
            },
            {
                "id": "json",
                "target": "settings.json",
                "adapter": "json",
                "scope": "key:/tool/demo",
                "content": b'{"tool":{"demo":true}}\n',
            },
            {
                "id": "markdown",
                "target": "README.md",
                "adapter": "markdown-block",
                "scope": "block:demo",
                "content": (
                    b"<!-- prettier-ignore-start -->\n\n"
                    b"<!-- BEGIN project-standards:demo -->\n"
                    b"Managed.\n"
                    b"<!-- END project-standards:demo -->\n\n"
                    b"<!-- prettier-ignore-end -->\n"
                ),
            },
            {
                "id": "editorconfig",
                "target": ".editorconfig",
                "adapter": "editorconfig",
                "scope": "property:*#indent_style",
                "content": b"[*]\nindent_style = space\n",
            },
        ],
    )
    first_request = PlannerRequest(repo, resolution_request((payload,)), (payload,))
    control = repo / ".standards"
    control.mkdir()
    (control / "lock.toml").write_bytes(render_lock(first_request.resolution.previous_lock))
    first = plan_reconciliation(first_request)

    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(first_request, first)).success
    before = _tree_bytes(repo)

    second_resolution = resolution_request((payload,), previous_lock=first.next_lock)
    second_request = PlannerRequest(repo, second_resolution, (payload,))
    second = plan_reconciliation(second_request)
    result = apply_reconciliation(ApplyRequest(second_request, second))

    assert second.applicable
    assert result.success
    assert result.applied_action_ids == ()
    assert not result.lock_written
    assert _tree_bytes(repo) == before


def test_unknown_declarative_package_needs_no_shared_source_dispatch(
    tmp_path: Path,
) -> None:
    standard_id = "previously-unknown-package"
    repo = tmp_path / "repo"
    repo.mkdir()
    payload = write_payload(
        tmp_path / "payload",
        standard_id,
        artifacts=[{"id": "marker", "target": "unknown.txt", "content": b"known\n"}],
    )

    plan = plan_reconciliation(PlannerRequest(repo, resolution_request((payload,)), (payload,)))

    assert plan.applicable
    assert plan.proposed_content("unknown.txt") == b"known\n"
    shared_sources = (_ROOT / "src/project_standards/control_plane").rglob("*.py")
    assert all(standard_id not in path.read_text(encoding="utf-8") for path in shared_sources)


def test_config_catalog_lock_and_plan_bytes_ignore_discovery_order(
    tmp_path: Path,
) -> None:
    alpha = write_payload(
        tmp_path / "alpha",
        "order-alpha",
        artifacts=[{"id": "alpha", "target": "alpha.txt", "content": b"alpha\n"}],
    )
    beta = write_payload(
        tmp_path / "beta",
        "order-beta",
        artifacts=[{"id": "beta", "target": "beta.txt", "content": b"beta\n"}],
    )
    generator = random.Random(20260711)
    baseline: tuple[bytes, bytes, bytes, bytes] | None = None

    for index in range(100):
        repo = tmp_path / f"repo-{index}"
        repo.mkdir()
        payloads = [alpha, beta]
        generator.shuffle(payloads)
        resolution = resolution_request(payloads)
        resolution_payloads = list(resolution.payloads)
        generator.shuffle(resolution_payloads)
        request = PlannerRequest(
            repo,
            replace(resolution, payloads=tuple(resolution_payloads)),
            tuple(payloads),
        )
        plan = plan_reconciliation(request)
        evidence = (
            _canonical(resolution.desired.model_dump(mode="json")),
            _canonical(resolution.catalog.model_dump(mode="json")),
            render_lock(plan.next_lock),
            _canonical(plan.to_jsonable()),
        )
        baseline = evidence if baseline is None else baseline
        assert evidence == baseline


def test_extracted_wheel_runs_offline_lifecycle_and_repairs_partial_apply(
    tmp_path: Path,
) -> None:
    project = tmp_path / "build"
    shutil.copytree(_FULL / "standards", project / "standards")
    shutil.copytree(_FULL / "catalogs", project / "catalogs")
    shutil.copytree(
        _ROOT / "src/project_standards",
        project / "src/project_standards",
        ignore=shutil.ignore_patterns("catalogs", "families", "payloads"),
    )
    (project / "pyproject.toml").write_text(
        """[project]
name = "project-standards"
version = "5.0.0"
requires-python = ">=3.14"
dependencies = ["pydantic>=2.13.4", "jsonschema>=4.23.0", "pyyaml>=6.0.2"]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
source-include = ["standards/**", "catalogs/**"]
""",
        encoding="utf-8",
    )
    assert sync_payload_projection(project, check=False) == ()
    dist = project / "dist"
    subprocess.run(
        ["uv", "build", "--sdist", "--wheel", "--out-dir", str(dist)],
        cwd=project,
        check=True,
        capture_output=True,
    )
    (wheel,) = dist.glob("*.whl")
    installed = tmp_path / "wheel-root"
    extract_pure_python_wheel(wheel, installed)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    script = r"""
import json
import socket
import sys
from pathlib import Path

def deny(*args, **kwargs):
    raise AssertionError("network construction is forbidden")

socket.socket = deny
socket.create_connection = deny

from project_standards.cli import main
from project_standards.control_plane.cli import build_planner_request, validate_repository
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.control_plane.providers import ProviderResult
from project_standards.package_contract.payload import ProviderEffect

repo = Path(sys.argv[1])
distribution = InstalledDistribution.current()
import project_standards.control_plane.planner as planner_module

def render(_invocation):
    return ProviderResult(ProviderEffect.CONTENT, content=b"[alpha]\ngenerated = true\n")

planner_module.invoke_provider = render
codes = [main(["init", "--catalog", "5", "--repo", str(repo)])]
extension = repo / ".standards/extensions/alpha/options.toml"
extension.parent.mkdir(parents=True)
extension.write_text("enabled = true\n", encoding="utf-8")
codes.append(main(["standards", "enable", "alpha", "--repo", str(repo)]))
request = build_planner_request(repo, distribution, frozenset())
plan = plan_reconciliation(request)

def interrupt(phase, identity):
    if (phase, identity) == ("published", ".editorconfig"):
        raise KeyboardInterrupt

partial = apply_reconciliation(ApplyRequest(request, plan, fault_hook=interrupt))
codes.append(main(["reconcile", "--repo", str(repo), "--apply"]))
codes.append(validate_repository(repo, distribution=distribution))
codes.append(main(["standards", "version", "alpha", "3.0", "--repo", str(repo)]))
codes.append(main(["reconcile", "--repo", str(repo), "--allow-major", "alpha@3", "--apply"]))
candidate_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
codes.append(main(["standards", "disable", "alpha", "--repo", str(repo)]))
codes.append(main(["reconcile", "--repo", str(repo), "--apply"]))
disabled_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
codes.append(main(["standards", "version", "alpha", "latest", "--repo", str(repo)]))
codes.append(main(["standards", "enable", "alpha", "--repo", str(repo)]))
codes.append(main(["reconcile", "--repo", str(repo), "--apply"]))
(repo / ".standards/lock.toml").unlink()
codes.append(main([
    "reconcile", "--repo", str(repo), "--repair-state", "--allow-major", "alpha@3", "--apply"
]))
lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
print(json.dumps({
    "codes": codes,
    "partial_success": partial.success,
    "partial_actions": list(partial.applied_action_ids),
    "candidate_resolved": candidate_lock.standards["alpha"].resolved.value,
    "candidate_track": (
        candidate_lock.accepted_tracks["alpha"].major
        if "alpha" in candidate_lock.accepted_tracks else None
    ),
    "disabled_track": (
        disabled_lock.accepted_tracks["alpha"].major
        if "alpha" in disabled_lock.accepted_tracks else None
    ),
    "resolved": lock.standards["alpha"].resolved.value,
    "accepted_major": (
        lock.accepted_tracks["alpha"].major if "alpha" in lock.accepted_tracks else None
    ),
}))
"""
    environment = {
        "HOME": str(tmp_path),
        "NO_COLOR": "1",
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(installed),
    }
    result = subprocess.run(
        [sys.executable, "-c", script, str(consumer)],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(result.stdout.splitlines()[-1])

    assert evidence == {
        "codes": [0] * 12,
        "partial_success": False,
        "partial_actions": [".editorconfig"],
        "candidate_resolved": "3.0",
        "candidate_track": 3,
        "disabled_track": 3,
        "resolved": "3.0",
        "accepted_major": 3,
    }


def test_toml_table_update_preserves_annotated_consumer_comments_end_to_end(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = repo / "settings.toml"
    settings.write_bytes(b"[consumer]\nkeep = true\n")
    initial_payload = write_payload(
        tmp_path / "payload-initial",
        "declarative-toolbox",
        contributions=[
            {
                "id": "demo",
                "target": "settings.toml",
                "adapter": "toml",
                "scope": "table:/tool/demo",
                "content": b'[tool.demo]\nvalues = ["a", "b"]\n',
            }
        ],
    )
    first_request = PlannerRequest(repo, resolution_request((initial_payload,)), (initial_payload,))
    control = repo / ".standards"
    control.mkdir()
    (control / "lock.toml").write_bytes(render_lock(first_request.resolution.previous_lock))
    first = plan_reconciliation(first_request)
    assert first.applicable, first.findings
    assert apply_reconciliation(ApplyRequest(first_request, first)).success

    annotated = settings.read_bytes().replace(
        b'values = ["a", "b"]',
        b'values = [\n  # consumer note: keep entry a\n  "a",\n  "b",\n]',
    )
    settings.write_bytes(annotated)

    updated_payload = write_payload(
        tmp_path / "payload-updated",
        "declarative-toolbox",
        contributions=[
            {
                "id": "demo",
                "target": "settings.toml",
                "adapter": "toml",
                "scope": "table:/tool/demo",
                "content": b'[tool.demo]\nvalues = ["a", "b", "c"]\n',
            }
        ],
    )
    second_resolution = resolution_request((updated_payload,), previous_lock=first.next_lock)
    second_request = PlannerRequest(repo, second_resolution, (updated_payload,))
    second = plan_reconciliation(second_request)
    assert second.applicable, second.findings
    assert apply_reconciliation(ApplyRequest(second_request, second)).success

    after = settings.read_bytes()
    assert (b'[tool.demo]\n# consumer note: keep entry a\nvalues = ["a", "b", "c"]\n') in after
    assert b"\n\n\n" not in after

    third_resolution = resolution_request((updated_payload,), previous_lock=second.next_lock)
    third_request = PlannerRequest(repo, third_resolution, (updated_payload,))
    third = plan_reconciliation(third_request)
    result = apply_reconciliation(ApplyRequest(third_request, third))
    assert third.applicable
    assert result.success
    assert result.applied_action_ids == ()
    assert settings.read_bytes() == after
