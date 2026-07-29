"""Security boundary of the consumer services: explicit contained roots only (T3).

Covers TC-T3-003 (root rejection, symlink escape, prefix collision, and
unrelated/secret content exclusion) and TC-T3-004 (only authoritative paths are
read). The escape cases use real hostile filesystem layouts and are checked two
ways — the returned facts never carry a planted sentinel, and an audit of every
filesystem open performed during the call shows the secret files were never
opened at all.

Boundary reading used by these tests, from T3's stop/backtrack rule: the
approved boundary is the resolved explicit root. A symlinked root that resolves
to a real repository is in bound and must be accepted; a symlink *inside* the
control plane whose target leaves the resolved root is the escape and must be
refused without reading the target.

The audit allowlist is derived from the three authoritative control files plus
the exact paths the authoritative planner output names — never from directory
enumeration, so an implementation that recursively reads ``.standards/`` is
caught by the decoy planted there.
"""

from __future__ import annotations

import builtins
import inspect as inspect_module
import io
import json
import os
import sys
import sysconfig
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from project_standards.control_plane.catalog_refresh import CATALOG_REFRESH_BACKUP
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import reconciliation_fingerprint
from tests.mcp_services.helpers import import_mcp_services
from tests.mcp_services.test_consumer import (
    build_consumer_repo,
    build_distribution,
    build_facade,
    dumped,
    oracle_plan,
    oracle_state,
    require_operation,
    tree_state,
)

ENV_SENTINEL = "SENTINEL-ENV-TOKEN"
CREDENTIAL_SENTINEL = "SENTINEL-CREDENTIAL"
UNRELATED_SENTINEL = "SENTINEL-UNRELATED"
OUTSIDE_SENTINEL = "SENTINEL-OUTSIDE-CONTROL-PLANE"
CONTROL_DECOY_SENTINEL = "SENTINEL-CONTROL-PLANE-DECOY"
SIBLING_SENTINEL = "SENTINEL-PREFIX-SIBLING"

SECRET_FILES = {
    ".env": f"API_TOKEN={ENV_SENTINEL}\n",
    "secrets/credentials.json": f'{{"password": "{CREDENTIAL_SENTINEL}"}}\n',
    "secrets/id_rsa": f"-----BEGIN PRIVATE KEY-----\n{CREDENTIAL_SENTINEL}\n",
    ".netrc": f"machine example.com password {CREDENTIAL_SENTINEL}\n",
    "unrelated/notes.md": f"# {UNRELATED_SENTINEL}\n",
    ".git/config": f"[user]\n\ttoken = {CREDENTIAL_SENTINEL}\n",
    # Decoys inside the control plane: undeclared, never named by any
    # authoritative output, and therefore never a legitimate read.
    ".standards/private-token.toml": f'token = "{CONTROL_DECOY_SENTINEL}"\n',
    ".standards/cache/scratch.toml": f'cached = "{CONTROL_DECOY_SENTINEL}"\n',
}

# The authoritative planner enumerates and digests undeclared entries under the
# package namespace, so this file IS opened. Its digest legitimately appears in
# the preview (the authoritative schema at work, DR-004); its content never may.
NAMESPACE_ROOT = ".standards/packages"
NAMESPACE_ROGUE = f"{NAMESPACE_ROOT}/rogue/private-token"
NAMESPACE_SENTINEL = "SENTINEL-NAMESPACE-ROGUE"


def plant_unrelated_contents(repo: Path) -> None:
    """Fill one consumer repository with secret and unrelated files."""
    for relative, content in SECRET_FILES.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def plant_namespace_rogue(repo: Path) -> None:
    """Plant one undeclared secret-bearing entry in the package namespace."""
    path = repo / NAMESPACE_ROGUE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'token = "{NAMESPACE_SENTINEL}"\n', encoding="utf-8")


def runtime_prefixes() -> tuple[str, ...]:
    """Return the interpreter and library roots a test process legitimately reads."""
    candidates = {
        sys.prefix,
        sys.base_prefix,
        sysconfig.get_path("stdlib"),
        sysconfig.get_path("purelib"),
        sysconfig.get_path("platlib"),
        str(Path(__file__).resolve().parents[3]),
    }
    candidates.update(path for path in sys.path if path)
    return tuple(sorted(candidates))


class OpenAudit:
    """Record every filesystem open, listing, and read performed inside one call.

    ``os.open`` names are recorded verbatim: the control plane opens its files
    relative to a directory descriptor, so those entries are bare names while
    ``pathlib`` reads are absolute. Both forms are checked, which is what makes
    a "never opened" assertion meaningful rather than a spelling accident.
    ``io.open`` is patched alongside ``builtins.open`` because ``pathlib``
    resolves that callable through the ``io`` module, not through builtins.
    """

    def __init__(self) -> None:
        self.entries: list[str] = []

    def record(self, value: object) -> None:
        self.entries.append(str(value))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The real callables are held as ``Any``: their overloaded signatures
        # cannot be expressed through the pass-through wrappers below.
        real_os_open: Any = os.open
        real_open: Any = builtins.open
        real_io_open: Any = io.open
        real_path_open: Any = Path.open
        real_read_bytes: Any = Path.read_bytes
        real_read_text: Any = Path.read_text
        real_scandir: Any = os.scandir
        real_listdir: Any = os.listdir

        def audited_os_open(path: Any, *args: Any, **kwargs: Any) -> int:
            self.record(path)
            return real_os_open(path, *args, **kwargs)

        def audited_open(file: Any, *args: Any, **kwargs: Any) -> Any:
            self.record(file)
            return real_open(file, *args, **kwargs)

        def audited_io_open(file: Any, *args: Any, **kwargs: Any) -> Any:
            self.record(file)
            return real_io_open(file, *args, **kwargs)

        def audited_path_open(self_path: Any, *args: Any, **kwargs: Any) -> Any:
            self.record(self_path)
            return real_path_open(self_path, *args, **kwargs)

        def audited_read_bytes(self_path: Any) -> Any:
            self.record(self_path)
            return real_read_bytes(self_path)

        def audited_read_text(self_path: Any, *args: Any, **kwargs: Any) -> Any:
            self.record(self_path)
            return real_read_text(self_path, *args, **kwargs)

        def audited_scandir(path: Any = ".") -> Any:
            self.record(f"scandir:{path}")
            return real_scandir(path)

        def audited_listdir(path: Any = ".") -> Any:
            self.record(f"scandir:{path}")
            return real_listdir(path)

        monkeypatch.setattr(os, "open", audited_os_open)
        monkeypatch.setattr(builtins, "open", audited_open)
        monkeypatch.setattr(io, "open", audited_io_open)
        monkeypatch.setattr(Path, "open", audited_path_open)
        monkeypatch.setattr(Path, "read_bytes", audited_read_bytes)
        monkeypatch.setattr(Path, "read_text", audited_read_text)
        monkeypatch.setattr(os, "scandir", audited_scandir)
        monkeypatch.setattr(os, "listdir", audited_listdir)


def authoritative_allowlist(distribution: InstalledDistribution, *repos: Path) -> set[str]:
    """Return the exact root-relative paths an authoritative read may touch.

    Derived from the three required control files plus the paths the
    authoritative planner output itself names — action and precondition targets,
    namespace findings and prunes, and the declared referenced inputs recorded
    in the next lock. Directory enumeration is deliberately not used: it would
    authorize any file an implementation happened to read from inside
    ``.standards/``.

    Several repositories may be supplied because a plan reports what it reached:
    a non-applicable plan records no referenced inputs even though the planner
    resolved them, so a pristine reference repository contributes the declared
    input paths while the repository under test contributes its findings. Every
    path is root-relative, so the union applies to either root.
    """
    allowed = {
        ".",
        ".standards",
        ".standards/config.toml",
        ".standards/catalog.toml",
        ".standards/lock.toml",
        # The interrupted-refresh backup is read by the authoritative state API
        # itself, which the "exact paths already requested by authoritative
        # APIs" clause covers.
        f".standards/{CATALOG_REFRESH_BACKUP}",
    }
    for repo in repos:
        plan = oracle_plan(repo, distribution)
        allowed |= {action.target for action in plan.actions}
        allowed |= {item.target for item in plan.preconditions}
        # The authoritative planner enumerates the package namespace to report
        # undeclared durable entries, so the paths its own output names are
        # authoritative-API-requested reads.
        allowed |= {finding.path for finding in plan.findings}
        allowed |= set(plan.namespace_prunes)
        lock = cast("dict[str, Any]", plan.to_jsonable()["next_lock"])
        referenced = cast("list[dict[str, Any]]", lock["referenced_inputs"])
        allowed |= {str(item["path"]) for item in referenced}
    for relative in tuple(allowed):
        parent = PurePosixPath(relative).parent
        while str(parent) not in {".", ""}:
            allowed.add(str(parent))
            parent = parent.parent
    return allowed


def hostile_roots(tmp_path: Path, repo: Path) -> dict[str, Path]:
    """Build every root input class the service must refuse before state loading."""
    file_root = tmp_path / "file-root.txt"
    file_root.write_text("not a repository\n", encoding="utf-8")
    dangling = tmp_path / "dangling-root"
    dangling.symlink_to(tmp_path / "does-not-exist", target_is_directory=True)
    file_link = tmp_path / "file-link-root"
    file_link.symlink_to(file_root)
    return {
        "nonexistent": tmp_path / "no-such-repository",
        "file-as-root": file_root,
        "traversal": repo / ".." / repo.name,
        "dangling-symlink": dangling,
        "symlink-to-file": file_link,
        "relative": Path(repo.name),
    }


def error_fields(error: Any) -> dict[str, str]:
    """Return every public string field of one structured service error."""
    return {
        name: str(getattr(error, name) or "")
        for name in ("code", "message", "remediation", "path", "standard_id", "version", "severity")
    }


def test_repo_access_rejects_escape_and_excludes_unrelated_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-T3-003: hostile roots are refused; secrets and escapes are never returned."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)

    clean_fingerprint = reconciliation_fingerprint(oracle_plan(repo, distribution))
    plant_unrelated_contents(repo)
    # A safe symlink inside the repository must not be treated as an escape.
    (repo / "docs").mkdir()
    (repo / "docs/real.md").write_text("# real\n", encoding="utf-8")
    (repo / "docs/link.md").symlink_to(repo / "docs/real.md")
    planted_fingerprint = reconciliation_fingerprint(oracle_plan(repo, distribution))
    assert planted_fingerprint == clean_fingerprint, (
        "unrelated consumer content must not participate in the authoritative plan"
    )

    # Prefix collision: a sibling whose path shares the root's string prefix is
    # a different repository and must never be read for the root under test.
    sibling = build_consumer_repo(tmp_path, "consumer-evil", distribution=distribution)
    sibling_config = sibling / ".standards/config.toml"
    sibling_config.write_text(
        f"{sibling_config.read_text(encoding='utf-8')}# {SIBLING_SENTINEL}\n", encoding="utf-8"
    )

    # A control-plane file symlinked outside the root, the whole control
    # directory symlinked outside the root, and a nested declared input
    # symlinked outside the root: all are refused by the authoritative loader or
    # planner without reading the target.
    outside = build_consumer_repo(tmp_path, "outside-repo", distribution=distribution)
    outside_config = outside / ".standards/config.toml"
    outside_config.write_text(
        f"{outside_config.read_text(encoding='utf-8')}# {OUTSIDE_SENTINEL}\n", encoding="utf-8"
    )
    outside_secret = tmp_path / "outside-secret.toml"
    outside_secret.write_text(f'token = "{OUTSIDE_SENTINEL}"\n', encoding="utf-8")

    escaped_file = build_consumer_repo(tmp_path, "escaped-file", distribution=distribution)
    (escaped_file / ".standards/config.toml").unlink()
    (escaped_file / ".standards/config.toml").symlink_to(outside_config)
    escaped_dir = tmp_path / "escaped-dir"
    escaped_dir.mkdir()
    (escaped_dir / ".standards").symlink_to(outside / ".standards", target_is_directory=True)
    escaped_nested = build_consumer_repo(tmp_path, "escaped-nested", distribution=distribution)
    nested_input = escaped_nested / ".standards/extensions/alpha/options.toml"
    nested_input.unlink()
    nested_input.symlink_to(outside_secret)

    assert oracle_state(escaped_file).kind.value == "malformed"
    assert oracle_state(escaped_dir).kind.value == "malformed"
    # The nested declared input escapes only at planning time; state loading
    # still reports a well-formed control plane.
    assert oracle_state(escaped_nested).kind.value == "initialized"

    inbound = tmp_path / "inbound-link"
    inbound.symlink_to(repo, target_is_directory=True)

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")

    codes: set[str] = set()
    for label, hostile in hostile_roots(tmp_path, repo).items():
        with pytest.raises(services.ServiceError) as raised:
            inspect_repo(hostile)
        fields = error_fields(raised.value)
        assert fields["message"], label
        assert fields["remediation"], label
        assert fields["severity"] == "error", label
        # Content safety across every public field, not just the message.
        for name, value in fields.items():
            assert str(tmp_path) not in value, f"{label}:{name}"
            assert str(hostile) not in value, f"{label}:{name}"
            for sentinel in (ENV_SENTINEL, CREDENTIAL_SENTINEL, SIBLING_SENTINEL):
                assert sentinel not in value, f"{label}:{name}"
        codes.add(fields["code"])
        with pytest.raises(services.ServiceError):
            reconcile(hostile)
    # One rejection class, one stable code: nonexistent, non-directory,
    # traversal, relative, and unresolvable roots are the same contract failure.
    assert len(codes) == 1
    assert codes != {""}

    # An explicit root is required: a rejected root never silently degrades to
    # the process working directory, even when that directory is a valid repo.
    monkeypatch.chdir(repo)
    with pytest.raises(services.ServiceError):
        inspect_repo(tmp_path / "no-such-repository")

    # A symlinked root that resolves inside the boundary is accepted and yields
    # exactly the same normalized facts as the resolved path.
    assert inspect_repo(inbound) == inspect_repo(repo)
    assert inspect_repo(inbound).repo_root == "."

    # Escapes are reported as the authoritative classification, with no parsed
    # state and no byte of the outside target.
    for escaped in (escaped_file, escaped_dir):
        snapshot = inspect_repo(escaped)
        assert snapshot.state == "malformed"
        assert snapshot.desired_config is None
        assert snapshot.consumer_catalog is None
        assert snapshot.central_lock is None
        assert OUTSIDE_SENTINEL not in json.dumps(dumped(snapshot), sort_keys=True)

    # The nested escape is refused at planning time: no preview may be invented
    # for a repository the authoritative planner would not plan.
    with pytest.raises(services.ServiceError) as nested_refusal:
        reconcile(escaped_nested)
    nested_error = nested_refusal.value
    assert nested_error.code
    assert nested_error.message
    assert nested_error.remediation
    nested_text = json.dumps(
        {
            "snapshot": dumped(inspect_repo(escaped_nested)),
            "error": error_fields(nested_error),
        },
        sort_keys=True,
    )
    assert OUTSIDE_SENTINEL not in nested_text
    assert str(tmp_path) not in nested_text

    # Unrelated and secret consumer content is neither returned nor able to
    # perturb the authoritative fingerprint; the prefix sibling is never read.
    snapshot = inspect_repo(repo)
    preview = reconcile(repo)
    serialized = json.dumps(
        {"snapshot": dumped(snapshot), "preview": dumped(preview)}, sort_keys=True
    )
    for sentinel in (
        ENV_SENTINEL,
        CREDENTIAL_SENTINEL,
        UNRELATED_SENTINEL,
        CONTROL_DECOY_SENTINEL,
        SIBLING_SENTINEL,
    ):
        assert sentinel not in serialized
    for relative in SECRET_FILES:
        assert relative not in serialized
    assert str(tmp_path) not in serialized
    assert preview.reconciliation_fingerprint == planted_fingerprint


@pytest.mark.parametrize(
    "case",
    [
        "nonexistent",
        "file-as-root",
        "traversal",
        "dangling-symlink",
        "symlink-to-file",
        "relative",
    ],
)
def test_repo_root_rejection_is_structural_for_every_class(tmp_path: Path, case: str) -> None:
    """TC-T3-003: each root rejection class fails structurally on its own.

    The code spelling is not frozen by any binding document, so this pins what
    the contract does require per class: a stable non-empty code, populated §5.5
    error fields with no leaked path or content, and both consumer operations
    refusing before any state is loaded or any byte is written.
    """
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    assert oracle_state(repo).kind.value == "initialized"

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")
    hostile = hostile_roots(tmp_path, repo)[case]

    before = tree_state(repo)
    with pytest.raises(services.ServiceError) as raised:
        inspect_repo(hostile)
    error = raised.value
    fields = error_fields(error)
    assert fields["code"]
    assert fields["code"].strip() == fields["code"]
    assert fields["message"]
    assert fields["remediation"]
    assert fields["severity"] == "error"
    assert error.path is None or not Path(error.path).is_absolute()
    for value in fields.values():
        assert str(tmp_path) not in value
        assert str(hostile) not in value

    with pytest.raises(services.ServiceError) as preview_refusal:
        reconcile(hostile)
    assert preview_refusal.value.code == error.code
    assert tree_state(repo) == before


def test_consumer_service_reads_only_authoritative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-T3-004 (IR-005): only the declared control-plane paths are ever opened."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    sibling = build_consumer_repo(tmp_path, "consumer-evil", distribution=distribution)
    plant_unrelated_contents(repo)
    plant_unrelated_contents(sibling)
    # The package namespace is enumerated by the authoritative planner, so the
    # rogue entry there is opened and digested by contract — its content still
    # may never surface. Everything else planted above must stay untouched.
    plant_namespace_rogue(repo)
    plant_namespace_rogue(sibling)
    pristine = build_consumer_repo(tmp_path, "consumer-reference", distribution=distribution)

    assert oracle_state(repo).kind.value == "initialized"
    allowed_relative = authoritative_allowlist(distribution, repo, pristine)
    assert {
        ".standards/config.toml",
        ".standards/catalog.toml",
        ".standards/lock.toml",
        ".standards/extensions/alpha/options.toml",
        NAMESPACE_ROGUE,
    } <= allowed_relative
    assert not any(relative in allowed_relative for relative in SECRET_FILES)
    # Directory-descriptor-relative opens carry a bare name, so the permitted
    # names are exactly the segments of the permitted paths.
    allowed_names = {
        part for relative in allowed_relative for part in PurePosixPath(relative).parts
    } | {"."}
    assert "private-token.toml" not in allowed_names
    allowed_prefixes = (str(distribution.package_root), *runtime_prefixes())

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")

    audit = OpenAudit()
    with monkeypatch.context() as patched:
        audit.install(patched)
        snapshot = inspect_repo(repo)
        preview = reconcile(repo)

    # Positive control: the audit must actually have observed the authoritative
    # reads, otherwise every exclusion below would be vacuously true.
    observed = audit.entries
    assert observed
    for name in ("config.toml", "catalog.toml", "lock.toml"):
        assert any(entry.endswith(name) for entry in observed), (
            f"the open audit never saw the authoritative read of {name}"
        )

    # Enumeration is permitted only inside the package namespace the
    # authoritative planner is contracted to walk; anywhere else it would be
    # undeclared discovery of consumer content.
    enumerable = f"{NAMESPACE_ROOT}"
    repo_prefix = f"{repo}/"
    for entry in observed:
        listing = entry.startswith("scandir:")
        target = entry.removeprefix("scandir:")
        if target == str(repo) or target.startswith(repo_prefix):
            relative = PurePosixPath(target).relative_to(repo).as_posix()
            if listing:
                assert relative == enumerable or relative.startswith(f"{enumerable}/"), (
                    f"the consumer repository was enumerated outside the package namespace: "
                    f"{relative}"
                )
                continue
            assert relative in allowed_relative, f"unauthorized consumer path opened: {relative}"
        elif target.startswith("/"):
            # Any absolute read outside the repository must belong to the
            # installed distribution or the Python runtime — never the prefix
            # sibling, another repository, or an arbitrary filesystem path.
            assert target.startswith(allowed_prefixes), f"unauthorized absolute open: {target}"
        else:
            assert target in allowed_names, f"unauthorized relative open: {target}"

    results = json.dumps({"snapshot": dumped(snapshot), "preview": dumped(preview)}, sort_keys=True)
    for relative, content in SECRET_FILES.items():
        name = PurePosixPath(relative).name
        assert not any(entry.endswith(f"/{relative}") for entry in observed), relative
        assert name not in {entry.removeprefix("scandir:") for entry in observed}, relative
        assert content.strip() not in results

    # The namespace rogue IS read by the authoritative planner and its digest
    # legitimately enters the preview, but its content never does — and the
    # sibling repository's copy is never touched at all.
    assert any(entry.endswith(f"/{NAMESPACE_ROGUE}") for entry in observed)
    assert NAMESPACE_SENTINEL not in results
    assert 'token = "' not in results
    assert not any(str(sibling) in entry for entry in observed)
    assert any(
        NAMESPACE_ROGUE in str(finding.path) for finding in oracle_plan(repo, distribution).findings
    )


def test_interrupted_refresh_reads_only_the_authoritative_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fourth control file the state API reads is authorized and audited.

    Classifying an interrupted refresh requires the authoritative state API to
    read ``.standards/<catalog backup>``. That read is covered by the "exact
    paths already requested by authoritative APIs" clause, so it is authorized
    here explicitly and proven not to widen into anything else.
    """
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "interrupted", distribution=distribution)
    plant_unrelated_contents(repo)
    backup = repo / ".standards" / CATALOG_REFRESH_BACKUP
    backup.write_bytes((repo / ".standards/catalog.toml").read_bytes())
    assert oracle_state(repo).kind.value == "interrupted-refresh"

    # The repository under test cannot be planned, so the declared-path set is
    # derived from a pristine reference repository built the same way.
    pristine = build_consumer_repo(tmp_path, "reference", distribution=distribution)
    allowed_relative = authoritative_allowlist(distribution, pristine)
    assert f".standards/{CATALOG_REFRESH_BACKUP}" in allowed_relative
    allowed_names = {
        part for relative in allowed_relative for part in PurePosixPath(relative).parts
    } | {"."}
    allowed_prefixes = (str(distribution.package_root), *runtime_prefixes())

    inspect_repo = require_operation(facade, "inspect_repo")
    audit = OpenAudit()
    with monkeypatch.context() as patched:
        audit.install(patched)
        snapshot = inspect_repo(repo)

    assert snapshot.state == "interrupted-refresh"
    assert snapshot.findings
    observed = audit.entries
    assert any(entry.endswith(CATALOG_REFRESH_BACKUP) for entry in observed), (
        "the interrupted-refresh classification must read the authoritative backup"
    )
    repo_prefix = f"{repo}/"
    for entry in observed:
        target = entry.removeprefix("scandir:")
        if target == str(repo) or target.startswith(repo_prefix):
            relative = PurePosixPath(target).relative_to(repo).as_posix()
            assert relative in allowed_relative, f"unauthorized consumer path opened: {relative}"
        elif target.startswith("/"):
            assert target.startswith(allowed_prefixes), f"unauthorized absolute open: {target}"
        else:
            assert target in allowed_names, f"unauthorized relative open: {target}"

    serialized = json.dumps(dumped(snapshot), sort_keys=True)
    for sentinel in (ENV_SENTINEL, CREDENTIAL_SENTINEL, CONTROL_DECOY_SENTINEL):
        assert sentinel not in serialized
    assert str(tmp_path) not in serialized


def test_consumer_operations_require_an_explicit_absolute_root(tmp_path: Path) -> None:
    """FR-024/IR-007: ``repo_root`` is mandatory, explicit, and never cwd-relative."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    assert oracle_state(repo).kind.value == "initialized"

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")

    for operation in (inspect_repo, reconcile):
        signature = inspect_module.signature(operation)
        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            not in {inspect_module.Parameter.VAR_POSITIONAL, inspect_module.Parameter.VAR_KEYWORD}
        ]
        assert parameters, f"{operation.__name__} declares no repository root"
        assert parameters[0].default is inspect_module.Parameter.empty, (
            f"{operation.__name__} defaults its repository root; the root must be explicit"
        )
        with pytest.raises(TypeError):
            operation()
