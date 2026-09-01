"""Catalog-wide proof that a provider's managed-target registry matches its payload.

A payload cut copies its predecessor's provider far more often than it rewrites one,
so the provider's own table of "targets I manage" silently outlives the declaration
it was written against. github-workflow 1.5 and agent-handoff 1.15 both shipped that
way (issue #175): the provider still expanded `agents/openai.yaml` over both skill
roots after the payload removed the `.claude/` copy and gated the `.agents/` one. A
registry entry the payload never installs fails every reconcile of a *correct*
consumer — GHW-DRIFT / AH-DRIFT, then CP-VERIFY — so the drift is invisible until a
dogfood reconcile runs, which is after the cut is frozen. This module replaces the
two per-family assertions written for those cuts (issue #194); related inventory work
is tracked in #134. Both providers carry a "Cross-file contract" comment citing their
own family's contract test as the place that pins the equality; those payload bytes
are released and immutable, so the citation stays until the next cut in each family
rewrites it — the equality now lives here, for every family at once.

Discovery rule, applied per advertised payload in `catalogs/5.toml`:

  A *managed-target registry* is any module-level `dict` in a provider module under
  `standards/<id>/versions/<v>/providers/` whose keys are all strings and at least
  one key is a declared `[[artifacts]]` target. Keying a table by installed path is
  what makes a table a claim about managed targets; the shared-key requirement is
  what separates such a table from a provider's other string-keyed configuration.
  Payloads with no provider module, or no such table, are skipped through a named
  parametrize id rather than dropped from the run.

Two boundaries of that rule are deliberate and worth knowing before extending it.
A provider that renders files the payload declares no artifact for keeps such a
table outside the rule (python-tooling's `_STATIC_TARGETS` is the live example, and
would come into scope the moment one of its paths became a declared artifact). And
a registry that mixes declared targets with paths the payload does not declare will
report every unmatched path as a phantom demand — correct for the drift this guards,
but it means a genuinely mixed table needs the rule revisited, not the finding
suppressed.

The comparison itself is shape-agnostic on purpose: families express a registry
differently (github-workflow keys a `path -> (artifact id, mode, gate)` tuple table,
agent-handoff splits `path -> resource id` from a separate gate map), so entry values
are flattened to their strings and each string is interpreted against the payload's
own vocabulary of artifact ids, resource ids, and harness gate tokens.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CATALOG = _ROOT / "catalogs/5.toml"

# The families that ship a registry today. Asserted as covered, not merely allowed:
# without it the discovery rule could stop matching anything — a rename of the
# provider table is enough — and the whole suite would pass by skipping.
_REGISTRY_FAMILIES = ("agent-handoff", "github-workflow")


@dataclass(frozen=True)
class _Declared:
    """The payload's side of the contract, indexed for comparison."""

    artifacts: dict[str, dict[str, object]]
    """Declared `[[artifacts]]` tables keyed by their installed target path."""

    artifact_ids: frozenset[str]
    resource_digests: dict[str, str]
    harness_gates: dict[str, str]
    """Target -> harness token, for artifacts gated on the `harnesses` option only.

    Gates on other options (agent-handoff's `startup` gate on the session hook) are
    excluded: those are enforced in provider code rather than recorded in a registry
    entry, so they are outside what a registry can be compared against.
    """


def _advertised() -> tuple[tuple[str, str], ...]:
    catalog = tomllib.loads(_CATALOG.read_text(encoding="utf-8"))
    packages = cast("list[dict[str, str]]", catalog["packages"])
    return tuple((package["id"], package["version"]) for package in packages)


def _payload_directory(standard_id: str, version: str) -> Path:
    return _ROOT / "standards" / standard_id / "versions" / version


def _declared(payload_directory: Path) -> _Declared:
    manifest = tomllib.loads((payload_directory / "payload.toml").read_text(encoding="utf-8"))
    artifacts = cast("list[dict[str, object]]", manifest.get("artifacts", []))
    resources = cast("list[dict[str, object]]", manifest.get("resources", []))

    harness_gates: dict[str, str] = {}
    for artifact in artifacts:
        for predicate in cast("list[dict[str, str]]", artifact.get("when_any", [])):
            if predicate.get("option") == "harnesses":
                token = predicate.get("contains") or predicate.get("equals")
                if token is not None:
                    harness_gates[cast("str", artifact["target"])] = token

    return _Declared(
        artifacts={cast("str", artifact["target"]): artifact for artifact in artifacts},
        artifact_ids=frozenset(cast("str", artifact["id"]) for artifact in artifacts),
        resource_digests={
            cast("str", resource["id"]): cast("str", resource["digest"]) for resource in resources
        },
        harness_gates=harness_gates,
    )


@cache
def _registries(payload_directory: Path) -> dict[str, dict[str, object]]:
    """Return every managed-target registry the payload's providers expose.

    Keys are `<module stem>.<attribute>` so a finding names the table a maintainer
    has to open. Providers are payload bytes rather than importable modules, so each
    is loaded from its declared path under a name unique to its payload — importing
    `standards....providers.<name>` would depend on a package layout the payload
    deliberately does not have, and two versions of one family would collide.
    """
    declared = _declared(payload_directory)
    provider_directory = payload_directory / "providers"
    if not provider_directory.is_dir():
        return {}

    found: dict[str, dict[str, object]] = {}
    for source in sorted(provider_directory.glob("*.py")):
        slug = payload_directory.relative_to(_ROOT).as_posix().replace("/", "_").replace(".", "_")
        spec = importlib.util.spec_from_file_location(f"{slug}_{source.stem}", source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous

        for attribute, value in vars(module).items():
            if attribute.startswith("__") or not isinstance(value, dict):
                continue
            table = cast("dict[object, object]", value)
            if not table or not all(isinstance(key, str) for key in table):
                continue
            keys = cast("dict[str, object]", table)
            if set(keys) & set(declared.artifacts):
                found[f"{source.stem}.{attribute}"] = keys
    return found


def _strings(value: object) -> Iterator[str]:
    """Yield every string reachable in a registry entry, whatever its shape."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in cast("dict[object, object]", value).items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, tuple | list | set | frozenset):
        for item in cast(
            "tuple[object, ...] | list[object] | set[object] | frozenset[object]", value
        ):
            yield from _strings(item)


def _findings(declared: _Declared, registries: dict[str, dict[str, object]]) -> list[str]:
    """Return one message per disagreement between the registries and the payload.

    Returning messages rather than asserting inline keeps the whole disagreement
    visible in a single failure: a stale cross product usually breaks several targets
    at once, and stopping at the first one hides how wide the drift is.
    """
    findings: list[str] = []
    managed: set[str] = set()
    for name, registry in registries.items():
        for target in registry:
            managed.add(target)
            if target not in declared.artifacts:
                findings.append(
                    f"{name} demands {target}, which the payload declares no artifact for"
                )

    # Completeness is asserted only within the top-level roots the registries already
    # reach. A provider may legitimately manage one tree and leave another (a
    # self-hosted workflow, a rendered config) to the control plane, and demanding
    # every declared target would turn that design into a failure.
    covered_roots = {target.split("/", maxsplit=1)[0] for target in managed}
    for target in sorted(declared.artifacts):
        if target.split("/", maxsplit=1)[0] in covered_roots and target not in managed:
            findings.append(f"no registry manages declared target {target}")

    for name, registry in registries.items():
        for target, entry in registry.items():
            artifact = declared.artifacts.get(target)
            if artifact is None:
                continue
            for token in _strings(entry):
                digest = declared.resource_digests.get(token)
                # A registry names either the artifact id or the provider resource
                # holding the bytes; both are checked against the artifact installed
                # at this target, so a copied row that still points at the
                # predecessor's identity fails here rather than at reconcile.
                if token == artifact["id"] or (digest is not None and digest == artifact["digest"]):
                    continue
                if digest is not None:
                    findings.append(
                        f"{name}[{target}] binds resource {token}, whose bytes are not the"
                        " artifact declared at that target"
                    )
                elif token in declared.artifact_ids:
                    findings.append(
                        f"{name}[{target}] names artifact {token}, but the payload declares"
                        f" {artifact['id']!r} at that target"
                    )

    vocabulary = set(declared.harness_gates.values())
    observed: dict[str, set[str]] = {}
    for registry in registries.values():
        for target, entry in registry.items():
            # Undeclared targets are already reported above; comparing their gates too
            # would double-report one drift and bury the phantom in a dict diff.
            if target not in declared.artifacts:
                continue
            tokens = {token for token in _strings(entry) if token in vocabulary}
            if tokens:
                observed.setdefault(target, set()).update(tokens)
    expected = {
        target: {token}
        for target, token in declared.harness_gates.items()
        if target in managed and target in declared.artifacts
    }
    if observed != expected:
        findings.append(f"harness gates {observed} do not match the declared gates {expected}")

    return findings


@pytest.mark.parametrize(
    ("standard_id", "version"),
    [pytest.param(*package, id=f"{package[0]}-{package[1]}") for package in _advertised()],
)
def test_advertised_payload__provider_registry__matches_the_declared_artifacts(
    standard_id: str, version: str
) -> None:
    payload_directory = _payload_directory(standard_id, version)
    registries = _registries(payload_directory)
    if not registries:
        pytest.skip("no provider module exposes a managed-target registry")

    assert _findings(_declared(payload_directory), registries) == []


def test_provider_registry__discovery__still_reaches_every_registry_family() -> None:
    """A discovery rule that matches nothing would let the suite pass by skipping."""
    covered = {
        standard_id
        for standard_id, version in _advertised()
        if _registries(_payload_directory(standard_id, version))
    }

    assert covered == set(_REGISTRY_FAMILIES)
    for standard_id in _REGISTRY_FAMILIES:
        versions = [version for family, version in _advertised() if family == standard_id]
        for version in versions:
            assert _registries(_payload_directory(standard_id, version)), (
                f"{standard_id} {version} must expose a discoverable registry"
            )


# The negative cases below stand in for payloads that cannot exist in the repository:
# released payload bytes are immutable, so the drift this module guards against can
# only be reproduced synthetically. Each mirrors one real or plausible cut mistake.

_SYNTHETIC = _Declared(
    artifacts={
        ".agents/skills/demo/SKILL.md": {
            "id": "skill",
            "target": ".agents/skills/demo/SKILL.md",
            "digest": "sha256:aa",
        },
        ".agents/skills/demo/agents/openai.yaml": {
            "id": "skill-openai",
            "target": ".agents/skills/demo/agents/openai.yaml",
            "digest": "sha256:bb",
            "when_any": [{"option": "harnesses", "contains": "codex"}],
        },
        ".claude/skills/demo/SKILL.md": {
            "id": "skill-claude",
            "target": ".claude/skills/demo/SKILL.md",
            "digest": "sha256:aa",
        },
    },
    artifact_ids=frozenset({"skill", "skill-openai", "skill-claude"}),
    resource_digests={"skill-source": "sha256:aa", "openai-source": "sha256:bb"},
    harness_gates={".agents/skills/demo/agents/openai.yaml": "codex"},
)

_CORRECT: dict[str, object] = {
    ".agents/skills/demo/SKILL.md": ("skill-source", None),
    ".agents/skills/demo/agents/openai.yaml": ("openai-source", "codex"),
    ".claude/skills/demo/SKILL.md": ("skill-source", None),
}


def test_findings__correct_registry__reports_nothing() -> None:
    assert _findings(_SYNTHETIC, {"demo._ARTIFACTS": dict(_CORRECT)}) == []


def test_findings__stale_cross_product__reports_the_undeclared_target() -> None:
    """The exact #175 shape: a root-by-unit expansion the payload stopped declaring."""
    registry = dict(_CORRECT)
    registry[".claude/skills/demo/agents/openai.yaml"] = ("openai-source", "codex")

    findings = _findings(_SYNTHETIC, {"demo._ARTIFACTS": registry})

    assert findings == [
        "demo._ARTIFACTS demands .claude/skills/demo/agents/openai.yaml,"
        " which the payload declares no artifact for"
    ]


def test_findings__dropped_row__reports_the_unmanaged_declared_target() -> None:
    """A row dropped from a root the registry still reaches is a gap, not a design.

    The `.agents/` copy is the one removed here because completeness is asserted per
    reached root: had the registry lost every `.claude/` row instead, that root would
    read as one the provider deliberately leaves to the control plane.
    """
    registry = dict(_CORRECT)
    del registry[".agents/skills/demo/SKILL.md"]

    assert _findings(_SYNTHETIC, {"demo._ARTIFACTS": registry}) == [
        "no registry manages declared target .agents/skills/demo/SKILL.md"
    ]


def test_findings__ungated_row__reports_the_harness_gate_disagreement() -> None:
    registry = dict(_CORRECT)
    registry[".agents/skills/demo/agents/openai.yaml"] = ("openai-source", None)

    findings = _findings(_SYNTHETIC, {"demo._ARTIFACTS": registry})

    assert len(findings) == 1
    assert findings[0].startswith("harness gates {} do not match the declared gates")


def test_findings__predecessor_bytes__reports_the_misbound_resource() -> None:
    registry = dict(_CORRECT)
    registry[".claude/skills/demo/SKILL.md"] = ("openai-source", None)

    assert _findings(_SYNTHETIC, {"demo._ARTIFACTS": registry}) == [
        "demo._ARTIFACTS[.claude/skills/demo/SKILL.md] binds resource openai-source,"
        " whose bytes are not the artifact declared at that target"
    ]
