---
schema_version: '1.1'
id: 'reference-qz8r4w-build-backend'
title: 'Build Backend Mechanics'
description: 'How a PEP 517 build backend (uv_build) turns a src/ tree into installable console-script tooling, with project-standards as the worked example.'
doc_type: 'reference'
status: 'active'
created: '2026-06-09'
updated: '2026-07-05'
reviewed: null
owner: ''
consumer: 'mix'
tags:
  - 'python'
  - 'packaging'
  - 'uv'
  - 'build-backend'
  - 'release'
aliases:
  - 'uv-build-backend'
related:
  - 'meta/versioning.md'
  - 'standards/python-tooling/README.md'
source:
  - 'https://peps.python.org/pep-0517/'
  - 'https://peps.python.org/pep-0518/'
  - 'https://peps.python.org/pep-0621/'
  - 'https://docs.astral.sh/uv/concepts/build-backend/'
  - 'https://packaging.python.org/en/latest/specifications/entry-points/'
confidence: 'high'
visibility: 'internal'
license: null
---

# Build Backend Mechanics

The [Python Tooling SSOT Standard](README.md) names `uv_build` as the default build backend (§3, §6) but does not explain what a build backend _does_. This reference fills that gap: it traces how four lines of `[build-system]` turn a `src/` tree into a command a user can type, using this repository as the worked example.

Scope boundary: this document owns the **mechanism** (source tree → wheel → installed command). It does **not** define what a release number promises or how a tag is cut — that contract is owned by [`meta/versioning.md`](../../meta/versioning.md), which this document links to rather than restating.

## Table of Contents

- [Build Backend Mechanics](#build-backend-mechanics)
  - [Table of Contents](#table-of-contents)
  - [1. Building is a two-party protocol (PEP 517 / 518)](#1-building-is-a-two-party-protocol-pep-517--518)
  - [2. What `uv_build` does with a `src/` layout](#2-what-uv_build-does-with-a-src-layout)
  - [3. Two artifacts: wheel and sdist](#3-two-artifacts-wheel-and-sdist)
  - [4. The mechanism that creates a command: `entry_points.txt` → wrapper](#4-the-mechanism-that-creates-a-command-entry_pointstxt--wrapper)
  - [5. Worked example — how this repository ships its CLIs](#5-worked-example--how-this-repository-ships-its-clis)
  - [6. The zipapp fallback (no backend, deliberately constrained)](#6-the-zipapp-fallback-no-backend-deliberately-constrained)

## 1. Building is a two-party protocol (PEP 517 / 518)

Packaging is split into two roles that agree on a standard interface, so neither needs to know the other's internals:

- A **build _frontend_** is whatever the user runs — `uv build`, `uv pip install`, `uvx`, `uv sync`, or plain `pip`. It knows nothing about how a given project is laid out.
- A **build _backend_** is a library, named in `pyproject.toml`, that knows exactly how to package _this_ project.

```toml
[build-system]
requires = ["uv_build>=0.11,<0.12"]   # PEP 518: deps installed in an isolated env *to build*
build-backend = "uv_build"            # PEP 517: the module the frontend imports and calls
```

The frontend reads `requires`, installs those build-time dependencies into a throwaway environment, imports the `build-backend` module, and calls its standardised hooks — chiefly `build_wheel(...)` and `build_sdist(...)`. The backend does the packaging and returns a file. This decoupling is why a backend can be swapped (`uv_build` → `hatchling` → `setuptools`) by editing two lines, and why one `uvx` command works against any PEP 517 project.

> Build-time dependencies (`requires`) are a different set from runtime dependencies (`[project].dependencies`, e.g. `jsonschema`, `pyyaml`). `uv_build` is never installed into the consumer's runtime environment.

## 2. What `uv_build` does with a `src/` layout

**Module discovery.** By default `uv_build` expects one root module at `src/<normalized-name>/__init__.py`. The project `name` is normalised by lowercasing and replacing dots and dashes with underscores, so `project-standards` → `project_standards`. The `src/` layout is therefore not decoration — it is what the backend requires to find the package, and it ensures `import project_standards` can only resolve against the _installed_ package, never an accidental working-directory import.

**Data-file inclusion.** When building a wheel, `uv_build` includes the **entire module root**, copies `project.license-files` into the wheel's metadata, and copies `project.readme` into the metadata. Files must live under the module root (or an explicit `tool.uv.build-backend.data` directory) to ship at all. This is why this package's non-Python payload travels with the code automatically — no `MANIFEST.in`, no `package_data` glob:

```text
src/project_standards/
├── validate_frontmatter.py   cli.py   registry.py   …   ← code
├── schemas/                  ← JSON schema, read at runtime via Path(__file__).parent
├── bundles/                  ← copy-adopt scaffolds, shipped inside the package
└── py.typed                  ← PEP 561 marker: downstream type-checkers trust the package
```

## 3. Two artifacts: wheel and sdist

```console
$ uv build
$ ls dist/
project_standards-3.0.0-py3-none-any.whl   # wheel: pre-built, directly installable
project_standards-3.0.0.tar.gz             # sdist: source + metadata, built into a wheel on demand
```

The `py3-none-any` tag means "pure Python, any interpreter, any platform" — one wheel serves every consumer, and the on-demand build (§5) is cheap and identical everywhere.

## 4. The mechanism that creates a command: `entry_points.txt` → wrapper

This is the crux — the actual answer to "how does typing `validate-frontmatter` run Python?" A wheel is a zip whose metadata directory carries the recipe:

```text
project_standards-3.0.0.dist-info/
├── METADATA         # name, version, deps, readme   (from [project])
├── WHEEL            # wheel-format version, build tool
├── RECORD           # every file + hash (install manifest)
└── entry_points.txt # ← the console-script recipe, generated from [project.scripts]
```

The backend translates `[project.scripts]` verbatim into a `[console_scripts]` section (abbreviated — this repo defines seven entries, one per script):

```ini
[console_scripts]
validate-frontmatter = project_standards.validate_frontmatter:main
project-standards    = project_standards.cli:main
validate-id          = project_standards.validate_id:main
; … plus sync-vscode-colors, sync-standards-include, format-frontmatter,
; and validate-references, in the same name = module:function form.
```

**Nothing is executable yet — `entry_points.txt` is a recipe, not a program.** The launcher is materialised at **install time**: when any installer (`uv pip install`, `uv tool install`, `uv sync`) lays the wheel down, it reads `[console_scripts]` and generates a small wrapper in the environment's `bin/`:

```python
#!/path/to/.venv/bin/python
# .venv/bin/validate-frontmatter — generated by the installer, not hand-written
import sys
from project_standards.validate_frontmatter import main
if __name__ == "__main__":
    sys.exit(main())
```

The `name = module:function` grammar is load-bearing: the wrapper imports the module and calls its `main()`, which returns an `int` exit code (`0/1/2/3`) that `sys.exit` turns into the process status. Because the wrapper hardcodes the interpreter and the import target, a console script is the only invocation form that survives leaving the repository directory — the wrapper lives in `bin/`, the code lives in the installed package, and neither depends on the current directory or `PYTHONPATH`.

## 5. Worked example — how this repository ships its CLIs

This repo is configured exactly as above: `name = "project-standards"`, `build-backend = "uv_build"`, and seven `[project.scripts]` entries. The twist is distribution: **there is no PyPI package.** Per [`deployed.md`](../../docs/handoff/deployed.md), a "release" is a signed git tag, and the wheel is built _on the consumer's machine_ from that ref:

```bash
# uv clones project-standards at tag v3, sees [build-system], runs uv_build in a
# throwaway env, installs the wheel, runs the generated wrapper, then discards it:
uvx --from 'git+https://github.com/L3DigitalNet/project-standards@v4' \
  validate-frontmatter --config .project-standards.yml
```

So the build backend is not merely an artifact-publishing convenience here — **it is what makes a bare git tag executable.** Without `[build-system]`, `uvx --from git+…` could clone the repo but would have no way to produce a runnable command from it. With it, every consumer becomes its own build frontend, and the pure-Python wheel plus uv's global cache mean a given commit builds once per machine and is reused across repos. The reusable CI workflow is the same story with the `uvx`/`uv run` hidden inside the shared workflow.

What a tag _promises_, and the ritual that cuts one (immutable full tag, moving major tag, version + `uv.lock` bump, changelog), is the **release contract** — owned by [`meta/versioning.md`](../../meta/versioning.md). Read it there.

## 6. The zipapp fallback (no backend, deliberately constrained)

`scripts/build-validate-id-pyz.sh` produces a second, very different artifact: a single-file [zipapp](https://docs.python.org/3/library/zipapp.html) (`dist/validate-id.pyz`) you can copy to a host that has neither uv nor network access. It is built **without the backend** (`python -m zipapp` over a hand-staged tree), and that forces three compromises a wheel never makes, all stemming from one fact — `zipimport` can only load pure-Python modules from inside a zip:

- PyYAML's C extension is deleted (`*.so`), forcing its slower pure-Python parser.
- `jsonschema` is stubbed, not bundled — its real transitive dep `rpds-py` is a Rust extension that cannot live in a zipapp (`validate_id` imports `jsonschema` at module load but never calls it).
- Data files cannot be read from inside the zip, so the generated `__main__.py` extracts the whole archive to a tempdir at startup before importing.

That fragility is the argument _for_ the wheel/backend path restated from the opposite side: a real installer in a real environment installs C extensions normally, resolves transitive deps in full, and lets `Path(__file__).parent` point at files on disk. Reach for the `.pyz` only when "must run on a locked-down host with no package manager" is a hard requirement; otherwise the `uvx`/wheel path is strictly less work and strictly more correct.

---

**Takeaway:** the build backend is the hinge connecting "I wrote a `main()` in `src/`" to "consumers type `validate-frontmatter` after pinning a tag." It encodes the `module:function` recipe into the wheel at build time; the installer realises that recipe into a `PATH` executable at install time; and because the build runs on the consumer from a git ref, the only thing this repository ever ships is a signed, versioned tag.
