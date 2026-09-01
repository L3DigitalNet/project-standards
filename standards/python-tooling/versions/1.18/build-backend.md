# Build Backend Guidance

## Default

Choose `uv_build` for pure-Python packages using a `src/` layout. It keeps the build configuration small and aligns package discovery with uv-managed environments.

The rendered requirement is `uv_build>=0.11,<1.0`, so adoption needs uv 0.11 or later: an older uv is outside the bound and warns on every command that reads the build system, because uv checks whether it may build through its own in-process backend. The upper bound covers the whole pre-1.0 series rather than one minor so that an immutable payload does not go stale with uv's next release (issue #182).

## Alternatives

- Choose `hatchling` when the project needs Hatch build hooks or established Hatch metadata.
- Choose `setuptools` for compatibility with projects whose build extensions or downstream tooling require it.
- Choose `none` for a deliberately non-installable repository. This omits `[build-system]` while retaining the complete development-tooling configuration.

The selected backend owns the complete `[build-system]` table. If an existing table differs, reconciliation blocks before writing; it never silently replaces a consumer-selected backend.

Backend selection does not change the verification stack. Ruff, the selected type checker, pytest/coverage, and pip-audit remain independent development tools.
