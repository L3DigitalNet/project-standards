---
schema_version: '1.1'
id: 'template-o3uoxu-executable-first-python-layout'
title: 'Executable-First Python Repository Layout'
description: 'Draft ADR template for shipping literal Python executables from `bin/` with shared code in `lib/` and internal tooling in `scripts/`.'
doc_type: 'template'
status: 'draft'
created: '2026-08-02'
updated: '2026-08-02'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'architecture'
  - 'packaging'
  - 'python'
  - 'repository'
aliases: []
related:
  - 'standards/adr/library/README.md'
  - 'standards/adr/library/repository-organization/go-command-and-internal-package-layout.md'
  - 'standards/adr/versions/1.3/templates/adr.md'
  - 'standards/python-tooling/versions/1.10/README.md'
source:
  - 'Owner requirement, 2026-08-02'
  - 'https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html'
  - 'https://setuptools.pypa.io/en/latest/userguide/package_discovery.html'
confidence: 'high'
visibility: 'internal'
license: null
---

# ADR Library: Executable-First Python Repository Layout

## Description

This reusable draft defines a layout for a product that must ship literal, extensionless Python executables rather than only installer-generated command wrappers. Public executables live in `bin/`, their shared importable core lives in `lib/`, and unshipped developer tooling lives in `scripts/`.

Before adoption, confirm that literal executable files are a product requirement, identify the supported operating systems and installation method, select the build backend, configure tooling scope for all three Python-bearing directories, add required ADR metadata, and obtain explicit acceptance.

````markdown
# Use an executable-first Python repository layout

## Context and Problem Statement

This repository ships user-facing, extensionless Python executables as literal files. Each executable begins with `#!/usr/bin/env python3` and is intended to be usable directly after a supported installation or deployment process.

The conventional `src/<package>/` layout is the default for a Python library or for a command installed through `[project.scripts]`, where the installer generates the command wrapper. It does not express the different boundary required here: repository-maintained executable files are themselves shipped product artifacts, shared application code must remain testable independently, and developer automation must not accidentally become user-facing installed software.

This decision applies only when retaining and shipping literal `bin/` files is a deliberate product requirement. It is not the default for an ordinary pip-only CLI: when installer-generated wrappers are sufficient, use the repository's normal `src/` layout and `[project.scripts]` instead.

## Decision Drivers

- Make the public executable contract visible and reviewable as first-class repository files.
- Keep executable entrypoints small, stable, and separately testable.
- Keep shared application logic importable without invoking a process-level CLI.
- Prevent build, release, CI, and maintenance helpers from becoming shipped commands.
- Keep local checkout execution and installed execution reliable without depending on the current working directory.

## Considered Options

- Use `bin/`, `lib/`, and `scripts/` for literal shipped Python executables, shared core code, and unshipped developer tooling.
- Use a conventional `src/<package>/` layout and installer-generated `[project.scripts]` commands.
- Put application logic directly in the `bin/` executables.
- Put developer tooling and public executables together in `scripts/`.

## Decision Outcome

Chosen option: **use `bin/`, `lib/`, and `scripts/` for literal shipped Python executables, shared core code, and unshipped developer tooling**.

The canonical layout is:

```text
my-project/
├── bin/                    # [RES-G] SHIPPED: public extensionless entrypoints
│   ├── my-app
│   └── my-tool
├── lib/                    # [RES-G] SHIPPED: shared importable application package
│   └── my_app_core/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       └── utils.py
├── scripts/                # [RES-G] INTERNAL: development, build, and operations tooling
│   ├── release.py
│   ├── generate_docs.py
│   └── test_runner.sh
├── tests/                  # [RES-G] unit and integration tests
│   ├── test_core.py
│   └── test_bin.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### Strongly recommended full layout

The preceding tree is the minimum required to express this decision. The following tree is the strongly recommended default for a repository that also wants predictable homes for Project Standards packages, their compatible agent workflows, and maintained documentation. It is a layout convention, not an obligation to create empty directories or adopt every related standard.

The tags identify namespace considerations:

- `[RES-G]` — reserved by common utilities or established practices; repurposing it can conflict with ordinary tooling.
- `[RES-PS]` — reserved within the Project Standards ecosystem; use may conflict with a current or future standards package, agent skill, or managed artifact.

```text
my-project/
├── .archived/              # [RES-PS] compressed historical project artifacts
├── .project-pipeline/      # [RES-PS] transient Project Pipeline execution state
├── .scratch/               # [RES-PS] temporary local work and scratch material
├── .standards/             # [RES-PS] Project Standards desired state and lock data
├── bin/                    # SHIPPED: public extensionless entrypoints
│   ├── my-app
│   └── my-tool
├── lib/                    # SHIPPED: shared importable application package
│   └── my_app_core/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       └── utils.py
├── scripts/                # INTERNAL: development, build, and operations tooling
│   ├── release.py
│   ├── generate_docs.py
│   └── test_runner.sh
├── tests/                  # unit and integration tests
│   ├── test_core.py
│   └── test_bin.py
├── docs/                   # [RES-G] maintained project documentation
│   ├── adr/                # [RES-PS] accepted architecture decision records
│   ├── handoff/            # [RES-PS] durable Agent Handoff knowledge and state
│   ├── plans/              # [RES-PS] active implementation plans
│   ├── research/           # research reports and source-grounded findings
│   ├── resources/          # supporting files consumed by maintained documents
│   ├── references/         # maintained technical reference material
│   ├── reviews/            # design and implementation review records
│   ├── specs/              # [RES-PS] maintained project specifications
│   ├── templates/          # reusable repository document templates
│   ├── usage/              # [RES-PS] user-facing site documentation when its profile is adopted
│   └── workflows/          # reusable human and agent workflow procedures
├── pyproject.toml
├── README.md
└── LICENSE
```

The recommended tree does not make every listed directory a shipped artifact. In particular, `.archived/`, `.project-pipeline/`, `.scratch/`, and `.standards/` are repository-control locations; `scripts/` is internal tooling; and only `bin/` and `lib/` belong to the executable product distribution defined here.

The following invariants apply:

- `bin/` contains only public, shipped executable entrypoints. They are extensionless, executable in the repository, and begin on their first line with `#!/usr/bin/env python3`.
- A `bin/` entrypoint is a thin boundary: it establishes the supported import path for local checkout execution, imports a named core `main()` function, and exits with that function's result. Argument parsing, application behavior, configuration, and business logic live in `lib/<package>/`.
- `lib/` contains the shipped importable core package. Its modules can be unit-tested directly without starting a `bin/` process.
- `scripts/` contains only internal developer, CI, build, release, and operational tooling. It is not an installation target and may retain filename extensions that make its maintenance role clear.
- `tests/` covers both the core package and the observable public-executable contract, including representative process invocation.
- Tooling configuration explicitly includes the Python-bearing `bin/`, `lib/`, and `scripts/` paths. Developer tooling may be type-checked without contributing to product coverage when that boundary is declared deliberately.
- The strongly recommended full layout is an adoption guide, not a requirement to create every listed directory. A repository adds each directory only when it owns material of that type and follows the owning standard or workflow when one applies.
- The layout targets POSIX-style executable delivery. A Windows-supported product defines and tests an equivalent launcher contract; a Unix shebang alone is not a cross-platform installation strategy.

### Packaging and installation

For a wheel or pip distribution that must install the literal `bin/` files, use a backend that supports that delivery model. The following setuptools configuration is a deliberate exception to the normal `[project.scripts]` preference because the exact repository-maintained executable files are part of the product contract:

```toml
[build-system]
requires = ['setuptools>=61.0']
build-backend = 'setuptools.build_meta'

[project]
name = 'my-app'
version = '1.0.0'
description = 'CLI product tools'
dependencies = []

[tool.setuptools.packages.find]
where = ['lib']
include = ['my_app_core*']
namespaces = false

[tool.setuptools]
script-files = [
  'bin/my-app',
  'bin/my-tool',
]
```

Setuptools documents `script-files` as a legacy, discouraged mechanism and recommends `[project.scripts]` whenever generated wrappers are acceptable. Do not choose this layout merely to avoid a normal package layout. Choose it only when shipping the literal `bin/` files is a verified requirement, then prove the built wheel installs and executes those commands correctly in a clean environment.

### Entrypoint pattern

An entrypoint may make the local `lib/` package importable when executed from a checkout. It must not derive imports from the current working directory or mask the installed package after installation.

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

repository_lib = Path(__file__).resolve().parent.parent / 'lib'
if (repository_lib / 'my_app_core' / '__init__.py').is_file():
    sys.path.insert(0, str(repository_lib))

from my_app_core.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
```

### Consequences

- Good, because public commands, shared application code, and internal tooling have unmistakable ownership boundaries.
- Good, because shared logic is directly importable and testable while public commands retain their literal executable identity.
- Good, because internal scripts cannot enter a distribution through the `bin/` installation list by accident.
- Bad, because this is a deliberate exception to the conventional `src/` plus generated-console-script model and needs explicit packaging and tooling configuration.
- Bad, because raw-script installation needs a clean-environment artifact test and platform-specific launcher decisions.
- Neutral, because a repository may use a different build backend if it can preserve the same literal-executable and core-package contract.

### Confirmation

Conformance is confirmed when the repository has the three declared boundaries; every public command has the required shebang and executable mode; tests cover the core package and representative `bin/` process behavior; `scripts/` is absent from built installation artifacts; and a clean environment installed from the built wheel can run each public command without relying on the checkout or its current working directory.

## Pros and Cons of the Options

### Executable-first `bin/`, `lib/`, and `scripts/` layout

- Good, because it models literal shipped command files and their shared code separately.
- Good, because it keeps developer automation out of the public command surface.
- Bad, because it requires deliberate source-tool, packaging, and platform configuration.

### Conventional `src/` layout with `[project.scripts]`

- Good, because modern Python packaging tools generate correct environment-specific wrappers from a stable import target.
- Good, because it is the appropriate default when a product does not need literal repository-maintained executables.
- Bad, because the installed command is generated rather than the repository's `bin/` file, so it does not meet this decision's delivery contract.

### Application logic in `bin/`

- Good, because a very small one-off command has few files.
- Bad, because application behavior becomes difficult to import, reuse, and unit-test independently of process invocation.

### One `scripts/` directory for everything

- Good, because it has a superficially simple directory tree.
- Bad, because it erases the boundary between shipped user commands and internal tooling, making accidental distribution and unclear ownership more likely.

## More Information

Record why literal executable delivery is required, the supported platforms, the build backend, installation targets, command names, and the clean-environment artifact test. For repositories adopting Project Standards Python Tooling, select the backend and source roots through its declared configuration rather than overwriting managed `pyproject.toml` tables; `setuptools` is an available backend choice, and additional source roots can include the nonstandard `lib/`, `bin/`, and internal `scripts/` paths.

The setuptools documentation is the authority for package discovery and raw script-file behavior. Revisit this decision if the product can instead use installer-generated `[project.scripts]` wrappers, changes supported platforms, or no longer needs the literal executable files to be shipped.
````
