# Build Backend Guidance

## Default

Choose `uv_build` for pure-Python packages using a `src/` layout. It keeps the build configuration small and aligns package discovery with uv-managed environments.

## Alternatives

- Choose `hatchling` when the project needs Hatch build hooks or established Hatch metadata.
- Choose `setuptools` for compatibility with projects whose build extensions or downstream tooling require it.

The selected backend owns the complete `[build-system]` table. If an existing table differs, reconciliation blocks before writing; it never silently replaces a consumer-selected backend.

Backend selection does not change the verification stack. Ruff, the selected type checker, pytest/coverage, and pip-audit remain independent development tools.
