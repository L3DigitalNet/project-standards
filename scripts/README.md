# scripts/

Developer helpers for `project-standards`.

## `bootstrap-worktree.sh` — one-command worktree setup

Runs the whole preflight a fresh checkout or detached worktree needs before any gate: locked `uv sync`, `npm ci`, the read-only projection check, an isolated candidate-wheel build with a one-wheel assertion, extraction to `build/wheel-runtime`, the staleness stamp, and `make go-tools`. Every step re-runs rather than being skipped, so it is safe to repeat after any `src/**` or payload change. `--no-go` skips the Go toolchain.

```bash
scripts/bootstrap-worktree.sh
scripts/bootstrap-worktree.sh --no-go
```

## `wheel-runtime-stamp.sh` — candidate-wheel staleness stamp

Single authority for the content key over resolved `src/**` plus `pyproject.toml`, so the builder and the gate cannot drift. `check` exits `0` current, `1` stale or missing, `2` error; the `verify.sh` preflight calls it and refuses a stale runtime by name. The key is content-based, not mtime-based, so a `git checkout` round-trip that restores identical bytes leaves the runtime current.

```bash
scripts/wheel-runtime-stamp.sh compute | write | check
```

## `family_preflight.py` — new-family declaration-site preflight

Reports, for one catalog family id, which of the nine hand-maintained declaration sites already mention it — `declared`, `missing`, or `not applicable` per site. Run it at task-claim time so adopting a family lands in one authored pass instead of eight serial gate-driven corrections. It predicts those gates and replaces none of them: a `declared` verdict means the id appears in the right collection, never that the value is correct. Stdlib-only and free of any `project_standards` import, so it runs in a bare checkout with no environment.

```bash
uv run python scripts/family_preflight.py <family-id> [--json] [--root PATH]
```

Exit `0` every applicable site declared, `1` at least one missing, `2` unknown family id or a stale site inventory. See convention 19 for the site list and the seam-applicability rule.

## `verify.sh` — the repository release gate

Runs the repository's own verification as three concurrent lanes (statics through the non-uv path, the ordinary suite under coverage with pytest-xdist, and the compatibility matrix), then the timing-sensitive performance lane alone, then `coverage combine` and the report. `--full` runs the same lane selections one at a time (ordinary suite still at `-n 16`) for the release-prep cross-check, and stops at the first red lane by default; `--keep-going` restores the fast gate's run-every-lane behavior for `--full`, and `--fail-fast` does the reverse for the fast gate. Expects the candidate wheel runtime on `PYTHONPATH` prerequisites and refuses to start without them; see the script header for the environment it establishes.

```bash
scripts/verify.sh            # fast gate (default)
scripts/verify.sh --full     # same lanes, one at a time (release-prep cross-check)
```

## `release_prep.py` — mechanical release preparation

Performs the judgment-free subset of `meta/versioning.md` behind one command: the scoped `pyproject.toml` version bump with `uv lock`, the `CHANGELOG.md` `[Unreleased]` conversion, two reviewed-never-rewritten reference reports, and the wiring verification chain ending in `packages check-release`. The original report lists outgoing tool-release literals in its established corpus. A separate pre-mutation report derives selected package versions from `catalogs/MAJOR.toml` and lists stale current references in each selected family's root `README.md`, optional `adopt.md`, and `agent-summary.md`; those findings remain successful owner-review output, while `packages check-release` is the authoritative gate. The script refuses a dirty or non-`main` worktree so the mutations belong to the release commit. It prints, but does not execute, the mandatory pre-tag locked `uv sync`, `npm ci`, read-only projection proof, isolated candidate-wheel, full-gate, dogfood, package-contract, and release-classification sequence. Tags, publication, and MAJOR-only prose stay manual.

```bash
uv run python scripts/release_prep.py X.Y.Z [--dry-run]
```

## `check.py` — Python Tooling dogfood gate

Runs the portable Python Tooling verification sequence, stopping at the first failure and propagating its exit code:

```text
ruff format --check  →  ruff check  →  basedpyright  →  coverage run -m pytest  →  coverage report  →  pip-audit
```

Usage:

```bash
uv run python scripts/check.py
```

This byte-locked dogfood artifact remains the generic consumer gate. The repository's own gate is `verify.sh` above; CI spells out its compatibility and performance phases directly in `.github/workflows/check.yml`.

### Dogfood relationship

`scripts/check.py` is the **dogfooded copy** of the Python Tooling bundle artifact:

```text
standards/python-tooling/versions/1.10/resources/check.py  ←→  scripts/check.py
```

`test_adopt_dogfood.py` asserts that the root artifact matches the current V2 reconciliation output. If you edit either file, update the package manifest and generated integrity metadata together — the test will catch any divergence in CI.

## `build-validate-id-pyz.sh` — standalone validator bundle

Builds `dist/validate-id.pyz`, a self-contained zipapp of `validate-id` for repos that cannot `uv tool install` the package. It bundles the package source from `src/project_standards/` directly; see the script header for the PyYAML/jsonschema bundling details.
