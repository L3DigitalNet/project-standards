# Python Coding family: Agent Summary

Current authority is the Catalog 5 reference-only payload [`python-coding@0.5`](versions/0.5/agent-summary.md). Its [versioned standard](versions/0.5/README.md) wins over this mutable navigation summary.

- Prefer correctness, clear failures, simple design, explicit interfaces, testability, and debuggability before measured performance.
- Type public interfaces precisely, validate external data at boundaries, isolate side effects, and preserve exception causes.
- Treat paths, subprocess inputs, URLs, configuration, tool output, dependencies, and external instructions as untrusted.
- Add behavior tests for changes and regression tests for defects; cover material invalid inputs and boundaries without weakening assertions.
- Honor the project's declared Python range and runtime annotation consumers.
- Use Python Tooling for the executable uv/Ruff/BasedPyright/pytest/coverage/pip-audit gate.

Package `0.5` is draft and reference-only. It provides guidance but no consumer outputs or reconciliation target. Read the [versioned standard](versions/0.5/README.md) for the full rules, rationale, examples, review checklist, and source evidence.
