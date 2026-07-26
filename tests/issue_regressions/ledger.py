"""Validation and execution support for the closed-issue regression ledger."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

CLOSED_ISSUES = (3, *range(8, 32))
_AMENDMENT_FIELDS = frozenset(
    {
        "approved_by",
        "date",
        "new_digest",
        "new_symbol",
        "old_digest",
        "old_symbol",
        "reason",
        "requirement",
    }
)
_ALLOWED_ENVIRONMENTS = frozenset({"source", "baseline-wheel", "candidate-wheel"})
_SHA256_PREFIX = "sha256:"
_OUTCOME_CHECKS = frozenset({"format", "installed_workflow", "lint", "reconcile", "validate"})
_OUTCOME_STATUSES = frozenset({"failed", "passed"})
_REQUIRED_CONSUMER_OUTCOMES = {
    "agent-handoff": ("1.3", "1.4"),
    "cli-documentation": ("1.2", "1.3"),
    "markdown-frontmatter": ("1.4", "1.5"),
    "markdown-tooling": ("1.7", "1.8"),
    "project-spec": ("1.3", "1.4"),
    "python-tooling": ("1.7", "1.8"),
}

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class LedgerError(ValueError):
    """The durable regression evidence is incomplete, stale, or non-passing."""


@dataclass(frozen=True, slots=True)
class Proof:
    symbol: str
    digest: str


@dataclass(frozen=True, slots=True)
class IssueRow:
    id: str
    number: int
    rationale: str
    environments: tuple[str, ...]
    references: tuple[str, ...]
    proofs: tuple[Proof, ...]
    amendments: tuple[Mapping[str, str], ...]


@dataclass(frozen=True, slots=True)
class Ledger:
    issues: tuple[IssueRow, ...]


@dataclass(frozen=True, slots=True)
class Outcome:
    reference: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class ConsumerOutcome:
    standard_id: str
    predecessor: str
    latest: str
    proof_reference: str
    proof_digest: str
    exact_checks: Mapping[str, str]
    latest_checks: Mapping[str, str]
    amendments: tuple[Mapping[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Baseline:
    release: str
    tag_commit: str
    wheel_sha256: str
    sdist_sha256: str
    payloads: Mapping[str, str]
    node: Mapping[str, str]
    consumer_outcomes: tuple[ConsumerOutcome, ...]


@dataclass(frozen=True, slots=True)
class _VerifiedRuntime:
    root: Path
    release: str
    wheel_sha256: str


def _load_toml(path: Path) -> dict[str, object]:
    try:
        return _load_toml_text(path.read_text(encoding="utf-8"), label=str(path))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LedgerError(f"{path}: cannot load regression evidence: {exc}") from exc


def _load_toml_text(text: str, *, label: str) -> dict[str, object]:
    try:
        return cast("dict[str, object]", tomllib.loads(text))
    except tomllib.TOMLDecodeError as exc:
        raise LedgerError(f"{label}: cannot load regression evidence: {exc}") from exc


def _table(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise LedgerError(f"{label} must be a table")
    untyped = cast("dict[object, object]", value)
    if not all(isinstance(key, str) for key in untyped):
        raise LedgerError(f"{label} must be a table")
    return cast("dict[str, object]", untyped)


def _tables(value: object, *, label: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise LedgerError(f"{label} must be an array of tables")
    return tuple(_table(item, label=label) for item in cast("list[object]", value))


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LedgerError(f"{label} must be an array of strings")
    untyped = cast("list[object]", value)
    if not all(isinstance(item, str) for item in untyped):
        raise LedgerError(f"{label} must be an array of strings")
    return tuple(cast("list[str]", untyped))


def _string(table: Mapping[str, object], key: str, *, label: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{label}.{key} must be a nonempty string")
    return value


def _integer(table: Mapping[str, object], key: str, *, label: str) -> int:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise LedgerError(f"{label}.{key} must be an integer")
    return value


def _split_symbol(symbol: str) -> tuple[Path, str]:
    try:
        raw_path, name = symbol.split("::", 1)
    except ValueError as exc:
        raise LedgerError(f"proof symbol {symbol!r} must use PATH::NAME") from exc
    if not raw_path or not name or "::" in name:
        raise LedgerError(f"proof symbol {symbol!r} must name one module-level symbol")
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise LedgerError(f"proof symbol {symbol!r} escapes the repository")
    return path, name


def _parsed_module(repo: Path, relative: Path) -> ast.Module:
    path = repo / relative
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    except (OSError, SyntaxError) as exc:
        raise LedgerError(f"proof module {relative} does not resolve: {exc}") from exc


def _symbol_node(repo: Path, symbol: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    relative, name = _split_symbol(symbol)
    tree = _parsed_module(repo, relative)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise LedgerError(f"proof symbol {symbol!r} does not resolve exactly once")
    return matches[0]


def _defined_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return (node.name,)
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        return tuple(target.id for target in targets if isinstance(target, ast.Name))
    return ()


def _decorator_is_fixture(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return (isinstance(target, ast.Name) and target.id == "fixture") or (
        isinstance(target, ast.Attribute) and target.attr == "fixture"
    )


def _autouse_fixture_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and _decorator_is_fixture(decorator)
                and any(
                    keyword.arg == "autouse"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in decorator.keywords
                )
            ):
                names.add(node.name)
    return names


def _usefixtures_names(node: ast.AST) -> set[str]:
    return {
        argument.value
        for child in ast.walk(node)
        if isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == "usefixtures"
        for argument in child.args
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
    }


def _module_usefixtures_names(tree: ast.Module) -> set[str]:
    return {
        fixture
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and "pytestmark" in _defined_names(node)
        for fixture in _usefixtures_names(node)
    }


def _fixture_argument_closure(tree: ast.Module, names: set[str]) -> set[str]:
    closure = set(names)
    definitions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_decorator_is_fixture(item) for item in node.decorator_list)
    }
    pending = list(names)
    while pending:
        fixture = definitions.get(pending.pop())
        if fixture is None:
            continue
        for argument in fixture.args.args:
            if argument.arg not in closure:
                closure.add(argument.arg)
                pending.append(argument.arg)
    return closure


def _module_dependencies(
    repo: Path,
    relative: Path,
    names: set[str],
    *,
    visited: set[tuple[Path, str]],
) -> list[tuple[str, ast.AST]]:
    tree = _parsed_module(repo, relative)
    definitions = {name: node for node in tree.body for name in _defined_names(node)}
    imports: dict[str, tuple[str, str]] = {}
    imported_modules: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules[alias.asname or alias.name.split(".", 1)[0]] = alias.name

    dependencies: list[tuple[str, ast.AST]] = []
    pending = sorted(names)
    while pending:
        name = pending.pop()
        key = (relative, name)
        if key in visited:
            continue
        visited.add(key)
        node = definitions.get(name)
        if node is not None:
            dependencies.append((f"{relative}:{name}", node))
            pending.extend(
                child.id
                for child in ast.walk(node)
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
            )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                pending.extend(argument.arg for argument in node.args.args)
            continue
        imported = imports.get(name)
        if imported is not None and imported[0].startswith("tests."):
            module_path = Path(*imported[0].split(".")).with_suffix(".py")
            dependencies.extend(
                _module_dependencies(
                    repo,
                    module_path,
                    {imported[1]},
                    visited=visited,
                )
            )
            continue
        imported_module = imported_modules.get(name)
        if imported_module is not None and imported_module.startswith("tests."):
            module_path = Path(*imported_module.split(".")).with_suffix(".py")
            module_tree = _parsed_module(repo, module_path)
            dependencies.append((f"{module_path}:module", module_tree))
    return dependencies


def _fixture_dependencies(
    repo: Path,
    relative: Path,
    fixtures: set[str],
    *,
    visited: set[tuple[Path, str]],
) -> list[tuple[str, ast.AST]]:
    dependencies: list[tuple[str, ast.AST]] = []
    parent = relative.parent
    while parent == Path("tests") or Path("tests") in parent.parents:
        conftest = parent / "conftest.py"
        if (repo / conftest).is_file():
            tree = _parsed_module(repo, conftest)
            fixtures |= _autouse_fixture_names(tree)
            fixtures = _fixture_argument_closure(tree, fixtures)
            dependencies.extend(_module_dependencies(repo, conftest, fixtures, visited=visited))
        if parent == Path("tests"):
            break
        parent = parent.parent
    return dependencies


def symbol_digest(repo: Path, symbol: str) -> str:
    """Hash a proof plus its same-module, test-helper, and fixture dependencies."""
    relative, _name = _split_symbol(symbol)
    node = _symbol_node(repo, symbol)
    loaded_names = {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }
    arguments = {argument.arg for argument in node.args.args}
    tree = _parsed_module(repo, relative)
    fixtures = (
        arguments
        | _autouse_fixture_names(tree)
        | _module_usefixtures_names(tree)
        | _usefixtures_names(node)
    )
    fixtures = _fixture_argument_closure(tree, fixtures)
    visited: set[tuple[Path, str]] = set()
    dependencies: list[tuple[str, ast.AST]] = [(symbol, node)]
    dependencies.extend(
        _module_dependencies(
            repo,
            relative,
            loaded_names | fixtures,
            visited=visited,
        )
    )
    dependencies.extend(
        _fixture_dependencies(
            repo,
            relative,
            fixtures,
            visited=visited,
        )
    )
    canonical = "\n".join(
        f"{label}:{ast.dump(dependency, annotate_fields=True, include_attributes=False)}"
        for label, dependency in sorted(dependencies, key=lambda item: item[0])
    )
    return _SHA256_PREFIX + hashlib.sha256(canonical.encode()).hexdigest()


def _validate_amendments(
    raw: object,
    *,
    label: str,
) -> tuple[Mapping[str, str], ...]:
    amendments = _tables(raw, label=f"{label}.amendments")
    validated: list[Mapping[str, str]] = []
    for index, amendment in enumerate(amendments):
        missing = _AMENDMENT_FIELDS - amendment.keys()
        extra = amendment.keys() - _AMENDMENT_FIELDS
        if missing or extra:
            raise LedgerError(
                f"{label}.amendments[{index}] amendment fields invalid: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        values = {
            key: _string(amendment, key, label=f"{label}.amendments[{index}]")
            for key in sorted(_AMENDMENT_FIELDS)
        }
        if not values["old_digest"].startswith(_SHA256_PREFIX) or not values[
            "new_digest"
        ].startswith(_SHA256_PREFIX):
            raise LedgerError(f"{label}.amendments[{index}] amendment digests must be sha256")
        validated.append(values)
    return tuple(validated)


def _parse_issue(table: Mapping[str, object], repo: Path, index: int) -> IssueRow:
    label = f"issues[{index}]"
    number = _integer(table, "number", label=label)
    issue_id = _string(table, "id", label=label)
    if issue_id != f"GH-{number}":
        raise LedgerError(f"{label}.id must be GH-{number}")
    references = _strings(table.get("references"), label=f"{label}.references")
    if not references or len(references) != len(set(references)):
        raise LedgerError(f"{label}.references must be nonempty and unique")
    environments = _strings(table.get("environments"), label=f"{label}.environments")
    if not environments or not set(environments) <= _ALLOWED_ENVIRONMENTS:
        raise LedgerError(f"{label}.environments contains an unsupported environment")
    proof_tables = _tables(table.get("proofs"), label=f"{label}.proofs")
    if not proof_tables:
        raise LedgerError(f"{label}.proofs must be nonempty")
    proofs: list[Proof] = []
    for proof_index, proof_table in enumerate(proof_tables):
        proof_label = f"{label}.proofs[{proof_index}]"
        symbol = _string(proof_table, "symbol", label=proof_label)
        digest = _string(proof_table, "digest", label=proof_label)
        observed = symbol_digest(repo, symbol)
        if digest != observed:
            raise LedgerError(
                f"{proof_label} proof digest changed for {symbol}: "
                f"expected {digest}, observed {observed}"
            )
        proofs.append(Proof(symbol=symbol, digest=digest))
    proof_symbols = {proof.symbol for proof in proofs}
    missing_proofs = set(references) - proof_symbols
    if missing_proofs:
        raise LedgerError(f"{label} references lack proof symbols: {sorted(missing_proofs)}")
    for reference in references:
        _symbol_node(repo, reference)
    return IssueRow(
        id=issue_id,
        number=number,
        rationale=_string(table, "rationale", label=label),
        environments=environments,
        references=references,
        proofs=tuple(proofs),
        amendments=_validate_amendments(table.get("amendments"), label=label),
    )


def _historical_issue_tables(
    path: Path,
    repo: Path,
    current: Sequence[Mapping[str, object]],
) -> Mapping[int, Mapping[str, object]]:
    try:
        relative = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return {_integer(row, "number", label="current issue"): row for row in current}
    history = subprocess.run(
        [
            "git",
            "log",
            "--follow",
            "--reverse",
            "--format=%H",
            "--",
            relative.as_posix(),
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        return {_integer(row, "number", label="current issue"): row for row in current}
    authority: dict[int, Mapping[str, object]] = {}
    for commit in history.stdout.splitlines():
        snapshot = subprocess.run(
            ["git", "show", f"{commit}:{relative.as_posix()}"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        if snapshot.returncode != 0:
            continue
        raw = _load_toml_text(snapshot.stdout, label=f"{commit}:{relative}")
        for row in _tables(raw.get("issues"), label="historical issues"):
            number = _integer(row, "number", label="historical issue")
            authority.setdefault(number, row)
    if authority:
        return authority
    return {_integer(row, "number", label="current issue"): row for row in current}


def _validate_historical_authority(
    path: Path,
    repo: Path,
    current_rows: Sequence[IssueRow],
    current_tables: Sequence[Mapping[str, object]],
) -> None:
    historical = _historical_issue_tables(path, repo, current_tables)
    current_by_number = {row.number: row for row in current_rows}
    for number, seed in historical.items():
        current = current_by_number.get(number)
        if current is None:
            continue
        seed_references = _strings(
            seed.get("references"),
            label=f"historical issue GH-{number}.references",
        )
        seed_proofs = {
            _string(proof, "symbol", label=f"historical issue GH-{number}.proof"): _string(
                proof,
                "digest",
                label=f"historical issue GH-{number}.proof",
            )
            for proof in _tables(
                seed.get("proofs"),
                label=f"historical issue GH-{number}.proofs",
            )
        }
        current_proofs = {proof.symbol: proof.digest for proof in current.proofs}
        amendments = list(current.amendments)
        consumed: set[int] = set()
        transformed: dict[str, tuple[str, str]] = {}
        for seed_symbol, seed_digest in seed_proofs.items():
            symbol = seed_symbol
            digest = seed_digest
            while True:
                matches = [
                    index
                    for index, amendment in enumerate(amendments)
                    if index not in consumed
                    and amendment["old_symbol"] == symbol
                    and amendment["old_digest"] == digest
                ]
                if not matches:
                    break
                if len(matches) != 1:
                    raise LedgerError(f"GH-{number} amendment chain branches at {symbol} {digest}")
                match = matches[0]
                consumed.add(match)
                amendment = amendments[match]
                symbol = amendment["new_symbol"]
                digest = amendment["new_digest"]
            transformed[seed_symbol] = (symbol, digest)
            if current_proofs.get(symbol) != digest:
                raise LedgerError(
                    f"GH-{number} proof change for {seed_symbol} requires a complete amendment"
                )
        expected_references = {
            transformed[reference][0] for reference in seed_references if reference in transformed
        }
        if set(current.references) != expected_references:
            raise LedgerError(f"GH-{number} reference change requires a complete amendment")
        if set(current_proofs) != {item[0] for item in transformed.values()}:
            raise LedgerError(f"GH-{number} proof-set change requires a complete amendment")
        if len(consumed) != len(amendments):
            raise LedgerError(f"GH-{number} contains an unused or disconnected amendment")


def _historical_consumer_tables(
    path: Path,
    repo: Path,
    current: Sequence[Mapping[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    try:
        relative = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return {
            _string(row, "standard_id", label="current consumer outcome"): row for row in current
        }
    history = subprocess.run(
        [
            "git",
            "log",
            "--follow",
            "--reverse",
            "--format=%H",
            "--",
            relative.as_posix(),
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        return {
            _string(row, "standard_id", label="current consumer outcome"): row for row in current
        }
    authority: dict[str, Mapping[str, object]] = {}
    for commit in history.stdout.splitlines():
        snapshot = subprocess.run(
            ["git", "show", f"{commit}:{relative.as_posix()}"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        if snapshot.returncode != 0:
            continue
        raw = _load_toml_text(snapshot.stdout, label=f"{commit}:{relative}")
        for row in _tables(raw.get("consumer_outcomes"), label="historical consumer outcomes"):
            standard_id = _string(row, "standard_id", label="historical consumer outcome")
            authority.setdefault(standard_id, row)
    if authority:
        return authority
    return {_string(row, "standard_id", label="current consumer outcome"): row for row in current}


def _historical_outcome_checks(
    row: Mapping[str, object],
    *,
    standard_id: str,
    track: str,
) -> dict[str, str]:
    label = f"historical consumer outcome {standard_id}.{track}_checks"
    checks = _table(row.get(f"{track}_checks"), label=label)
    return {key: _string(checks, key, label=label) for key in sorted(checks)}


def validate_historical_consumer_authority(
    path: Path,
    repo: Path,
    current_rows: Sequence[ConsumerOutcome],
    current_tables: Sequence[Mapping[str, object]],
) -> None:
    historical = _historical_consumer_tables(path, repo, current_tables)
    current_by_standard = {row.standard_id: row for row in current_rows}
    for standard_id, seed in historical.items():
        current = current_by_standard.get(standard_id)
        if current is None:
            raise LedgerError(f"consumer outcome {standard_id} was removed")
        seed_versions = (
            _string(seed, "predecessor", label=f"historical consumer outcome {standard_id}"),
            _string(seed, "latest", label=f"historical consumer outcome {standard_id}"),
        )
        if (current.predecessor, current.latest) != seed_versions:
            raise LedgerError(f"consumer outcome {standard_id} version authority changed")
        for track, current_checks in (
            ("exact", current.exact_checks),
            ("latest", current.latest_checks),
        ):
            if dict(current_checks) != _historical_outcome_checks(
                seed,
                standard_id=standard_id,
                track=track,
            ):
                raise LedgerError(
                    f"consumer outcome change for {standard_id} {track} track is not allowed"
                )

        symbol = _string(
            seed,
            "proof_reference",
            label=f"historical consumer outcome {standard_id}",
        )
        digest = _string(
            seed,
            "proof_digest",
            label=f"historical consumer outcome {standard_id}",
        )
        amendments = list(current.amendments)
        consumed: set[int] = set()
        while True:
            matches = [
                index
                for index, amendment in enumerate(amendments)
                if index not in consumed
                and amendment["old_symbol"] == symbol
                and amendment["old_digest"] == digest
            ]
            if not matches:
                break
            if len(matches) != 1:
                raise LedgerError(
                    f"consumer outcome {standard_id} amendment chain branches at {symbol} {digest}"
                )
            match = matches[0]
            consumed.add(match)
            amendment = amendments[match]
            symbol = amendment["new_symbol"]
            digest = amendment["new_digest"]
        if (current.proof_reference, current.proof_digest) != (symbol, digest):
            raise LedgerError(
                f"consumer outcome {standard_id} proof change requires a complete amendment"
            )
        if len(consumed) != len(amendments):
            raise LedgerError(
                f"consumer outcome {standard_id} contains an unused or disconnected amendment"
            )


def validate_ledger(
    path: Path,
    repo: Path,
    *,
    expected_issues: Sequence[int] = CLOSED_ISSUES,
) -> Ledger:
    """Load the ledger and fail closed on coverage, reference, or proof drift."""
    raw = _load_toml(path)
    if raw.get("schema_version") != "1.0":
        raise LedgerError("unsupported ledger schema_version")
    issue_tables = _tables(raw.get("issues"), label="issues")
    rows = tuple(_parse_issue(table, repo, index) for index, table in enumerate(issue_tables))
    numbers = tuple(row.number for row in rows)
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise LedgerError(f"duplicate issue rows: {duplicates}")
    expected = set(expected_issues)
    actual = set(numbers)
    if missing := sorted(expected - actual):
        raise LedgerError(f"missing issue rows: {missing}")
    if extra := sorted(actual - expected):
        raise LedgerError(f"unexpected issue rows: {extra}")
    if numbers != tuple(sorted(numbers)):
        raise LedgerError("issue rows must be sorted by number")
    _validate_historical_authority(path, repo, rows, issue_tables)
    return Ledger(issues=rows)


def require_passed_outcomes(
    references: Sequence[str],
    outcomes: Mapping[str, Outcome],
) -> None:
    """Require one ordinary pass for every reference; no pytest soft state is green."""
    for reference in references:
        outcome = outcomes.get(reference)
        if outcome is None:
            raise LedgerError(f"missing outcome for {reference}")
        if outcome.status != "passed":
            raise LedgerError(f"{outcome.status} outcome for {reference}: {outcome.detail}")


def _aggregate_status(records: Sequence[Mapping[str, object]]) -> str:
    statuses: set[str] = set()
    for record in records:
        outcome = record.get("outcome")
        when = record.get("when")
        was_xfail = bool(record.get("wasxfail"))
        if outcome == "failed":
            statuses.add("errored" if when != "call" else "failed")
        elif outcome == "skipped":
            statuses.add("xfailed" if was_xfail else "skipped")
        elif outcome == "passed" and was_xfail:
            statuses.add("xpassed")
        elif outcome == "passed" and when == "call":
            statuses.add("passed")
    for candidate in ("errored", "failed", "xpassed", "xfailed", "skipped", "passed"):
        if candidate in statuses:
            return candidate
    return "missing"


def _run_references(
    repo: Path,
    references: Sequence[str],
    *,
    runtime: _VerifiedRuntime | None,
) -> Mapping[str, Outcome]:
    """Run proof nodes once and normalize every pytest result, including soft states."""
    runnable: list[str] = []
    normalized: dict[str, Outcome] = {}
    for reference in references:
        try:
            _symbol_node(repo, reference)
        except LedgerError as exc:
            normalized[reference] = Outcome(
                reference=reference,
                status="missing",
                detail=str(exc),
            )
        else:
            runnable.append(reference)
    if not runnable:
        return normalized

    with tempfile.TemporaryDirectory(prefix="issue-regression-outcomes-") as temp_dir:
        output = Path(temp_dir) / "outcomes.json"
        environment = os.environ.copy()
        support_root = Path(__file__).resolve().parents[2]
        path_entries = [str(support_root)]
        if runtime is not None:
            path_entries.insert(0, str(runtime.root))
        if inherited := environment.get("PYTHONPATH"):
            path_entries.append(inherited)
        environment["PYTHONPATH"] = os.pathsep.join(path_entries)
        environment["ISSUE_REGRESSION_OUTCOMES"] = str(output)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "tests.issue_regressions.outcome_plugin",
                *runnable,
            ],
            cwd=repo,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        records: list[Mapping[str, object]] = []
        if output.is_file():
            parsed: object = json.loads(output.read_text(encoding="utf-8"))
            if isinstance(parsed, list):
                items = cast("list[object]", parsed)
                records = [
                    cast("Mapping[str, object]", item) for item in items if isinstance(item, dict)
                ]
        details = (completed.stdout + completed.stderr).strip()
        run_failed = completed.returncode != 0
    aggregated = {
        reference: _aggregate_status(
            [
                record
                for record in records
                if record.get("nodeid") == reference
                or (
                    isinstance(record.get("nodeid"), str)
                    and cast("str", record["nodeid"]).startswith(reference + "[")
                )
            ]
        )
        for reference in runnable
    }
    unexplained_run_failure = run_failed and not any(
        status in {"failed", "errored"} for status in aggregated.values()
    )
    for reference in runnable:
        status = aggregated[reference]
        if unexplained_run_failure and status == "passed":
            status = "errored"
        normalized[reference] = Outcome(
            reference=reference,
            status=status,
            detail=details,
        )
    return normalized


def run_references(
    repo: Path,
    references: Sequence[str],
) -> Mapping[str, Outcome]:
    """Run proof nodes against the source checkout."""
    return _run_references(repo, references, runtime=None)


def verify_artifact_digest(path: Path, expected: str, *, label: str) -> None:
    observed = _file_sha256(path)
    if observed != expected:
        raise LedgerError(f"{label} digest mismatch: expected {expected}, observed {observed}")


@contextmanager
def _verified_wheel_runtime(
    baseline: Baseline,
    wheel: Path,
) -> Generator[_VerifiedRuntime]:
    """Extract only a digest/version-bound wheel and prove imports resolve from it."""
    verify_artifact_digest(wheel, baseline.wheel_sha256, label="wheel")
    with tempfile.TemporaryDirectory(prefix="verified-regression-wheel-") as temp_dir:
        root = Path(temp_dir)
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                relative = Path(member.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise LedgerError(f"wheel contains unsafe member {member.filename!r}")
            archive.extractall(root)
        metadata_files = tuple(root.glob("*.dist-info/METADATA"))
        if len(metadata_files) != 1:
            raise LedgerError("wheel must contain exactly one dist-info METADATA file")
        metadata = metadata_files[0].read_text(encoding="utf-8")
        if f"\nVersion: {baseline.release}\n" not in f"\n{metadata}":
            raise LedgerError(
                f"wheel metadata does not declare baseline release {baseline.release}"
            )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(root)
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json, project_standards; "
                    "from importlib.metadata import version; "
                    "print(json.dumps([project_standards.__file__, "
                    "version('project-standards')]))"
                ),
            ],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            raise LedgerError(f"wheel import probe failed: {probe.stdout}{probe.stderr}")
        imported_path, imported_version = cast("tuple[str, str]", tuple(json.loads(probe.stdout)))
        try:
            Path(imported_path).resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise LedgerError(f"wheel import escaped verified extraction: {imported_path}") from exc
        if imported_version != baseline.release:
            raise LedgerError(
                f"wheel import version mismatch: {imported_version} != {baseline.release}"
            )
        yield _VerifiedRuntime(
            root=root,
            release=baseline.release,
            wheel_sha256=baseline.wheel_sha256,
        )


def run_verified_wheel_references(
    repo: Path,
    references: Sequence[str],
    *,
    baseline: Baseline,
    wheel: Path,
) -> Mapping[str, Outcome]:
    """Verify one wheel's identity and execute every proof only inside that runtime."""
    with _verified_wheel_runtime(baseline, wheel) as runtime:
        return _run_references(repo, references, runtime=runtime)


def _flatten(mapping: Mapping[str, object], prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, value in mapping.items():
        label = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            flattened.update(_flatten(cast("Mapping[str, object]", value), label))
        else:
            flattened[label] = value
    return flattened


def compare_authority(
    captured: Mapping[str, object],
    observed: Mapping[str, object],
) -> None:
    """Compare immutable captured authority even if observed state is self-consistent."""
    captured_flat = _flatten(captured)
    observed_flat = _flatten(observed)
    for key in sorted(set(captured_flat) | set(observed_flat)):
        if captured_flat.get(key) != observed_flat.get(key):
            raise LedgerError(
                f"authority mismatch for {key}: "
                f"expected {captured_flat.get(key)!r}, observed {observed_flat.get(key)!r}"
            )


def compare_predecessor_authority(
    captured: Mapping[str, str],
    observed: Mapping[str, str],
) -> None:
    """Require every captured predecessor while permitting additive successors."""
    for key, digest in sorted(captured.items()):
        if observed.get(key) != digest:
            raise LedgerError(
                f"predecessor authority mismatch for {key}: "
                f"expected {digest!r}, observed {observed.get(key)!r}"
            )


def _file_sha256(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise LedgerError(f"cannot hash authority file {path}: {exc}") from exc
    return hashlib.sha256(content).hexdigest()


def _git_bytes(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise LedgerError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def _verify_git_baseline(baseline: Baseline, repo: Path) -> None:
    tag = f"v{baseline.release}"
    resolved = _git_bytes(repo, "rev-parse", f"{tag}^{{}}").decode().strip()
    if resolved != baseline.tag_commit:
        raise LedgerError(
            f"{tag} commit mismatch: expected {baseline.tag_commit}, observed {resolved}"
        )
    catalog_bytes = _git_bytes(repo, "show", f"{tag}:catalogs/5.toml")
    catalog = _load_toml_text(catalog_bytes.decode(), label=f"{tag}:catalogs/5.toml")
    tag_payloads = {
        f"{_string(row, 'id', label='tag catalog package')}@"
        f"{_string(row, 'version', label='tag catalog package')}": _string(
            row,
            "digest",
            label="tag catalog package",
        )
        for row in _tables(catalog.get("packages"), label="tag catalog packages")
    }
    compare_authority(baseline.payloads, tag_payloads)
    for name, expected in baseline.node.items():
        observed = hashlib.sha256(_git_bytes(repo, "show", f"{tag}:{name}")).hexdigest()
        if observed != expected:
            raise LedgerError(
                f"{tag} {name} digest mismatch: expected {expected}, observed {observed}"
            )


def validate_baseline(path: Path, repo: Path) -> Baseline:
    """Validate the committed v5.8.0 release, payload, Node, and outcome authority."""
    raw = _load_toml(path)
    if raw.get("schema_version") != "1.0":
        raise LedgerError("unsupported baseline schema_version")
    release = _string(raw, "release", label="baseline")
    payload_rows = _tables(raw.get("payloads"), label="payloads")
    payloads: dict[str, str] = {}
    for index, row in enumerate(payload_rows):
        standard_id = _string(row, "id", label=f"payloads[{index}]")
        version = _string(row, "version", label=f"payloads[{index}]")
        digest = _string(row, "digest", label=f"payloads[{index}]")
        key = f"{standard_id}@{version}"
        if key in payloads:
            raise LedgerError(f"duplicate baseline payload {key}")
        payloads[key] = digest

    catalog = _load_toml(repo / "catalogs/5.toml")
    observed_payloads = {
        f"{_string(row, 'id', label='catalog package')}@"
        f"{_string(row, 'version', label='catalog package')}": _string(
            row, "digest", label="catalog package"
        )
        for row in _tables(catalog.get("packages"), label="catalog packages")
    }
    node = {
        "package.json": _string(raw, "package_json_sha256", label="baseline"),
        "package-lock.json": _string(raw, "package_lock_sha256", label="baseline"),
    }
    compare_predecessor_authority(payloads, observed_payloads)
    compare_authority(
        {"node": node},
        {
            "node": {
                "package.json": _file_sha256(repo / "package.json"),
                "package-lock.json": _file_sha256(repo / "package-lock.json"),
            },
        },
    )

    outcome_rows = _tables(raw.get("consumer_outcomes"), label="consumer_outcomes")
    outcomes: list[ConsumerOutcome] = []
    for index, row in enumerate(outcome_rows):
        track_checks: dict[str, dict[str, str]] = {}
        for track in ("exact", "latest"):
            label = f"consumer_outcomes[{index}].{track}_checks"
            checks = _table(row.get(f"{track}_checks"), label=label)
            typed_checks = {key: _string(checks, key, label=label) for key in sorted(checks)}
            if (
                frozenset(typed_checks) != _OUTCOME_CHECKS
                or not set(typed_checks.values()) <= _OUTCOME_STATUSES
            ):
                raise LedgerError(
                    f"consumer_outcomes[{index}] {track} track must contain "
                    "the complete pass/fail check set"
                )
            track_checks[track] = typed_checks
        proof_reference = _string(
            row,
            "proof_reference",
            label=f"consumer_outcomes[{index}]",
        )
        proof_digest = _string(
            row,
            "proof_digest",
            label=f"consumer_outcomes[{index}]",
        )
        observed_proof_digest = symbol_digest(repo, proof_reference)
        if proof_digest != observed_proof_digest:
            raise LedgerError(
                f"consumer_outcomes[{index}] proof digest changed for "
                f"{proof_reference}: expected {proof_digest}, observed "
                f"{observed_proof_digest}"
            )
        outcomes.append(
            ConsumerOutcome(
                standard_id=_string(row, "standard_id", label=f"consumer_outcomes[{index}]"),
                predecessor=_string(row, "predecessor", label=f"consumer_outcomes[{index}]"),
                latest=_string(row, "latest", label=f"consumer_outcomes[{index}]"),
                proof_reference=proof_reference,
                proof_digest=proof_digest,
                exact_checks=track_checks["exact"],
                latest_checks=track_checks["latest"],
                amendments=_validate_amendments(
                    row.get("amendments"),
                    label=f"consumer_outcomes[{index}]",
                ),
            )
        )
    observed_outcomes = {
        outcome.standard_id: (outcome.predecessor, outcome.latest) for outcome in outcomes
    }
    if len(observed_outcomes) != len(outcomes):
        raise LedgerError("baseline consumer_outcomes contains a duplicate standard")
    if observed_outcomes != _REQUIRED_CONSUMER_OUTCOMES:
        raise LedgerError(
            "baseline consumer_outcomes does not match the required exact/latest matrix"
        )
    if tuple(outcome.standard_id for outcome in outcomes) != tuple(sorted(observed_outcomes)):
        raise LedgerError("baseline consumer_outcomes must be sorted by standard_id")
    validate_historical_consumer_authority(path, repo, outcomes, outcome_rows)
    baseline = Baseline(
        release=release,
        tag_commit=_string(raw, "tag_commit", label="baseline"),
        wheel_sha256=_string(raw, "wheel_sha256", label="baseline"),
        sdist_sha256=_string(raw, "sdist_sha256", label="baseline"),
        payloads=payloads,
        node=node,
        consumer_outcomes=tuple(outcomes),
    )
    _verify_git_baseline(baseline, repo)
    return baseline
